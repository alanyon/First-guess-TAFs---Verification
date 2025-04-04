"""
Script to count number of TAF busts, calculate statistics and output
plots and spreadsheets.

Functions:
    main: Main function calling all other functions.
    add_stats: Adds bust stats to appropriate lists in dictionaries.
    count_busts: Counts the number of busts in a TAF.
    get_day_man_tafs_metars: Extracts manual TAFs and METARs.
    get_day_tafs: Extracts all TAFs issued on specified day.
    get_holders: Returns dictionaries to store data.
    get_icao_metars: Returns dictionary of METARs for specified ICAO.
    get_new_data: Extracts TAFs and METARs and compares them.
    get_taf_lines: Reads in TAFs from file.
    get_taf_times: Checks if TAFs match and returns start and end times.
    mets_all: Writes METAR to spreadsheet.
    mets_wind: Writes METAR to spreadsheet.
    plot_dirs: Plots wind busts in each direction.
    plot_param: Plots busts for each parameter.
    plot_summary: Plots summary of all busts.
    taf_str: Converts TAF in list format to and easily readable string.
    update_infos: Updates info dictionaries.
    update_stats: Updates stats dictionaries.
    write_to_excel: Writes data to Excel spreadsheet.
    write_stats: Writes stats to Excel spreadsheet.

Written by Andre Lanyon.
"""
import itertools
import os
import sys
from copy import deepcopy
from datetime import datetime, timedelta

import matplotlib.pyplot as plt
import metdb
import numpy as np
import seaborn as sns
import useful_functions as uf
import xlsxwriter

import configs as cf
from checking import CheckTafThread
from time_functionality import ConstructTimeObject

# Set plotting style
sns.set_style('darkgrid')
sns.set(font_scale=1.5)


def main(load_data):
    """
    Extracts TAFs and METARs and compares them, collecting bust
    information.

    Args:
        load_data (str): 'yes' to load from pickled files, 'no' to start
                         from scratch.
    Returns:
        None
    """
    # Get dictionaries, etc, to store data, either from pickled files or
    # create new empty ones
    holders = get_holders(load_data)

    # Get new data and add to data holders
    get_new_data(holders, load_data)

    # # Create spreadsheets
    write_to_excel(holders, 'wind')
    write_to_excel(holders, 'all')

    # Make plots
    plot_dirs(holders)
    summary_stats = {'Bust Type': [], 'TAF Type': [], 'Number of Busts': []}
    plot_param(holders, 'vis', summary_stats)
    plot_param(holders, 'wx', summary_stats)
    plot_param(holders, 'cld', summary_stats)
    plot_param(holders, 'wind', summary_stats)
    plot_summary(summary_stats)


def add_stats(holders, s_type, icao, p_busts, t_type, w_type):
    """
    Adds bust stats to appropriate lists in dictionaries.

    Args:
        holders (dict): Dictionaries to store data
        s_type (str): Type of stats to add
        icao (str): ICAO of TAF
        p_busts (dict): Dictionary of busts in TAF
        t_type (str): TAF type
        w_type (str): Weather type
    Returns:
        None
    """
    # Key for holders dictionary
    s_key = f'{s_type}_stats'

    # Get busts and METARs for para from list
    busts_metars = p_busts[cf.W_NAMES[w_type]]

    # Do not need to continue if no busts
    if not busts_metars:
        return

    for (busts, metar) in busts_metars:

        # For wind stats
        if s_type == 'wind':

            holders[s_key][icao][f'{t_type} all'] += 1

            # Get METAR direction
            w_dir = metar[2][:3]
            if w_dir.isnumeric() and int(w_dir) in cf.NUM_TO_DIR:
                dir_lab = cf.NUM_TO_DIR[int(w_dir)]
            elif w_dir == 'VRB':
                dir_lab = 'VRB'
            else:
                dir_lab = False

            # Add to stats dictionaries
            d_stats = 'dirs_stats'
            d_key = f'{t_type} dirs'
            if busts['mean increase'] or busts['gust increase']:
                holders[s_key][icao][f'{t_type} increase'] += 1
                if dir_lab:
                    holders[d_stats][d_key][icao]['increase'][dir_lab] += 1
            if busts['mean decrease']:
                holders[s_key][icao][f'{t_type} decrease'] += 1
                if dir_lab:
                    holders[d_stats][d_key][icao]['decrease'][dir_lab] += 1
            if busts['dir']:
                holders[s_key][icao][f'{t_type} dir'] += 1
                if dir_lab:
                    holders[d_stats][d_key][icao]['dir'][dir_lab] += 1

        # For cld and vis stats
        elif s_type in ['cld', 'vis']:

            holders[s_key][icao][f'{t_type} all'] += 1
            holders[s_key][icao][f'{t_type} {busts}'] += 1

        # For wx stats
        elif s_type == 'wx':

            holders[s_key][icao][f'{t_type} all'] += 1

        # For summary of all busts stats
        else:
            holders[s_key][icao][f'{t_type} {w_type}'] += 1


def count_busts(taf, metars, icao, start, end):
    """
    Counts the number of busts in a TAF by comparing it to METARs.

    Args:
        taf (str): TAF to check
        metars (list): List of METARs to check TAF against
        icao (str): ICAO of TAF
        start (datetime): Start time of TAF
        end (datetime): End time of TAF
    Returns:
        busts (dict): Dictionary of busts in TAF
    """
    # Try to find busts
    try:
        busts = CheckTafThread(icao, start, end, taf, metars).run()

    # If any issues, assume TAF is bad and print it out to check
    except:
        print('Bad TAF', taf)
        busts = None

    return busts


def day_icao_stats(holders, icao, auto_tafs, man_tafs, metars):
    """
    Gets day stats for ICAO and adds to holders dictionary.

    Args:
        holders (dict): Dictionaries to store data
        icao (str): ICAO to get stats for
        auto_tafs (list): List of lists of auto TAFs
        man_tafs (list): List of manual TAFs
        metars (list): List of METARs
    Returns:
        None
    """
    # Get TAFs for ICAO
    icao_auto_tafs = [[row for row in tafs if icao in row]
                      for tafs in auto_tafs]

    # Loop through all IMPROVER TAFs for ICAO
    for auto_taf_rows in itertools.product(*icao_auto_tafs):

        # Get required TAF variables
        a_vdts = [datetime.strptime(row[4], '%d-%b-%y') +
                  timedelta(hours=int(row[5][:2])) for row in auto_taf_rows]
        a_tafs = [row[10][46:].split() for row in auto_taf_rows]

        # Continue to next iteration if wrong validity time
        if not all(vdt == a_vdts[0] for vdt in a_vdts):
            continue

        # Now vdts must be the same
        vdt = a_vdts[0]

        # Get start and end times of auto TAFs
        a_starts, a_ends = [], []
        for taf in a_tafs:
            taf_day = int(taf[2][:2])
            a_start, a_end = ConstructTimeObject(taf[2], taf_day,
                                             vdt.month, vdt.year).TAF()
            a_starts.append(a_start)
            a_ends.append(a_end)

        # Starts and ends of all auto TAFs need to be the same
        if not all(a_start == a_starts[0] for a_start in a_starts):
            continue
        if not all(a_end == a_ends[0] for a_end in a_ends):
            continue

        # Get start and end times of TAFs must be the same
        a_start, a_end = a_starts[0], a_ends[0]

        # Find TAF with correct timings
        for man_taf in man_tafs:

            # Attempt to match TAFs and get TAFs start/end times
            start, end, match = get_taf_times(man_taf, vdt, a_start, a_end,
                                              a_tafs[0])

            # Move on if TAFs don't match
            if not match:
                continue

            # Get all METARs valid for TAF period
            v_metars = [metar for vdt, metar in metars if start <= vdt <= end]

            # Count busts for all TAF types
            all_tafs = [*a_tafs, man_taf]
            all_busts = [count_busts(taf, v_metars, icao, start, end)
                         for taf in all_tafs]

            # Move on if bad TAF found
            if any(busts is None for busts in all_busts):
                continue

            # Number of METARs expected during TAF period
            num_float = (end - start).total_seconds() / 1800
            holders['metars_used'][icao] += int(np.round(num_float))

            # Collectinto dictionaries
            vc_busts = dict(zip(cf.TAF_TYPES, all_busts))
            vc_tafs = dict(zip(cf.TAF_TYPES, all_tafs))

            # Add to all stats dictionaries
            update_stats(holders, vc_busts, icao)

            # Add to all info dictionaries
            update_infos(holders, icao, vc_tafs, vc_busts)

            # Break for loop so only one TAF is used
            break


def get_day_man_tafs_metars(day):
    """
    Extracts from metdb all manual TAFs for required ICAOs for specified
    day and all METARs for required ICAOs for specified day and two
    following days (to cover all valid times covered by TAFs).

    Args:
        day (datetime): Day to extract TAFs and METARs for
    Returns:
        day_tafs (dict): Dictionary of manual TAFs for required ICAOs
        day_3_metars (dict): Dictionary of METARs for required ICAOs
    """
    # Define start and end times to search for TAFs
    start_times = [(day + timedelta(days=ind)).strftime("%Y%m%d/0000")
                   for ind in range(3)]
    end_times = [(day + timedelta(days=ind)).strftime("%Y%m%d/2359")
                 for ind in range(3)]

    # Get all TAFs for day
    all_tafs = metdb.obs(cf.METDB_EMAIL, 'TAFS',
                         keywords=['PLATFORM EG',
                                   f'START TIME {start_times[0]}Z',
                                   f'END TIME {end_times[0]}Z'],
                         elements=['ICAO_ID', 'TAF_RPT_TXT'])

    # Get METARs for all possible times TAFs cover (3 days)
    all_metars = [metdb.obs(cf.METDB_EMAIL, 'METARS',
                            keywords=['PLATFORM EG',
                                      f'START TIME {start_time}Z',
                                      f'END TIME {end_time}Z'],
                            elements=['ICAO_ID', 'MTR_RPT_TXT'])
                  for start_time, end_time in zip(start_times, end_times)]

    # Get SPECIs for all possible times TAFs cover
    all_specis = [metdb.obs(cf.METDB_EMAIL, 'SPECI',
                            keywords=['PLATFORM EG',
                                      f'START TIME {start_time}Z',
                                      f'END TIME {end_time}Z'],
                            elements=['ICAO_ID', 'MTR_RPT_TXT'])
                  for start_time, end_time in zip(start_times, end_times)]

    # Get TAFs/METARs for each required ICAO and store in dictionaries
    day_tafs, day_3_metars = {}, {}
    for icao in cf.REQ_ICAOS:

        # Get TAFs for ICAO
        icao_tafs = all_tafs[all_tafs['ICAO_ID'] == icao]
        icao_tafs = [str(taf['TAF_RPT_TXT'], 'utf-8').strip().split()[8:]
                     for taf in icao_tafs]

        # Add to TAFs dictionary
        day_tafs[str(icao, 'utf-8').strip()] = icao_tafs

        # Get METARs and SPECIs for ICAO
        icao_metars = get_icao_metars(all_metars, icao)
        icao_specis = get_icao_metars(all_specis, icao)

        # Combine SPECIs and METARs
        icao_metars.update(icao_specis)

        # Sort list so SPECIs in time order with METARs
        new_icao_metars = sorted(icao_metars.items())

        # Add to METARs dictionary
        day_3_metars[str(icao, 'utf-8').strip()] = new_icao_metars

    return day_tafs, day_3_metars


def get_day_tafs(day, tafs_lines):
    """
    Extracts all TAFs issued on specified day from list of TAFs.

    Args:
        day (datetime): Day to extract TAFs for
        tafs_lines (list): List of TAFs
    Returns:
        day_tafs (list): List of TAFs issued on specified day
    """
    # To add TAFs to
    day_tafs = []

    # Loop through all TAFs
    for row in tafs_lines:

        # Split row by ','
        row = row.split(',')

        # Get issue dt of TAF
        idt = datetime.strptime(row[10][2:16], '%H%MZ %d/%m/%y')

        # If TAF issued on required day, add to list
        if (idt - timedelta(hours=1)).date() == day.date():
            day_tafs.append(row)

    return day_tafs


def get_holders(load_data):
    """
    Returns dictionaries to store data, either from pickled files or
    new empty ones.

    Args:
        load_data (str): 'yes' to load from pickled files, 'no' to start
                         from scratch.
    Returns:
        holders (dict): Dictionaries to store data.
    """
    # Load in pickled data if required
    if load_data != 'yes':
        return {name: uf.unpickle_data(f'{cf.D_DIR}/pickles/{name}')
                for name in cf.NAMES}

    # Otherwise, create empty dictionaries
    wind_template = {icao: [] for icao in cf.REQ_ICAO_STRS}
    wind_info, vis_info, cld_info, wx_info, all_info = (
        deepcopy(wind_template) for _ in range(5)
    )
    wind_template = {f'{t_type} {b_type}': 0 for t_type in cf.TAF_TYPES
                     for b_type in cf.WB_TYPES}
    wind_stats = {icao: deepcopy(wind_template) for icao in cf.REQ_ICAO_STRS}
    vis_cld_template = {f'{t_type} {b_type}': 0 for t_type in cf.TAF_TYPES
                        for b_type in cf.B_TYPES}
    vis_stats = {icao: deepcopy(vis_cld_template) for icao in cf.REQ_ICAO_STRS}
    cld_stats = {icao: deepcopy(vis_cld_template) for icao in cf.REQ_ICAO_STRS}
    wx_stats = {icao: {f'{t_type} all': 0 for t_type in cf.TAF_TYPES}
                for icao in cf.REQ_ICAO_STRS}
    all_template = {f'{t_type} {w_type}': 0 for t_type in cf.TAF_TYPES
                    for w_type in cf.W_NAMES}
    all_stats = {icao: deepcopy(all_template) for icao in cf.REQ_ICAO_STRS}
    dirs_template = {'N': 0, 'E': 0, 'S': 0, 'W': 0, 'VRB': 0}
    dirs_stats = {f'{t_type} dirs': {icao: {b_type: deepcopy(dirs_template)
                                     for b_type in cf.D_TYPES}
                                     for icao in cf.REQ_ICAO_STRS}
                  for t_type in cf.TAF_TYPES}
    metars_used = {icao: 0 for icao in cf.REQ_ICAO_STRS}
    last_day = cf.DAYS[0] - timedelta(days=1)

    # Collect all data into a dictionary
    holders = {
        'wind_info': wind_info, 'vis_info': vis_info, 'cld_info': cld_info,
        'wx_info': wx_info, 'all_info': all_info, 'wind_stats': wind_stats,
        'vis_stats': vis_stats, 'cld_stats': cld_stats, 'wx_stats': wx_stats,
        'all_stats': all_stats, 'dirs_stats': dirs_stats,
        'metars_used': metars_used, 'last_day': last_day}

    return holders


def get_icao_metars(all_metars, icao):
    """
    Returns dictionary of METARs for specified ICAO.

    Args:
        all_metars (list): List of METARs to check
        icao (str): ICAO to check METARs for
    Returns:
        icao_metars (dict): Dictionary of METARs for specified ICAO
    """
    # To add METARs to
    icao_metars = {}

    # Loop through all METARs
    for metars in all_metars:

        # Loop through all METARs for ICAO
        i_metars = metars[metars['ICAO_ID'] == icao]
        for metar in i_metars:

            # Convert METAR text to list
            metar_list = str(metar['MTR_RPT_TXT'], 'utf-8').strip().split()

            # Get METAR components needed for verification
            metar_comps = metar_list[8:]

            # Ignore if no record or cancelled
            if 'NoRecord' in metar_comps:
                continue

            # Remove AUTO if present
            if 'AUTO' in metar_comps:
                metar_comps.remove('AUTO')

            # Get METAR validity datetime and add to dictionary
            m_dt = ' '.join(metar_list[:2])
            metar_vdt = datetime.strptime(m_dt, '%H%MZ %d/%m/%y')
            icao_metars[metar_vdt] = metar_comps

    return icao_metars


def get_new_data(holders, load_data):
    """
    Extracts TAFs and METARs and compares them, collecting bust
    information.

    Args:
        holders (dict): Dictionaries to store data
        load_data (str): 'yes' to load from pickled files, 'no' to start
                         from scratch.
    Returns:
        None
    """
    # If last day already reached, don't need to do anything
    if holders['last_day'] == cf.END_DT or load_data == 'no':
        return

    # Read in IMPROVER TAFs files
    auto_tafs_lines = [get_taf_lines(fname) for fname in cf.AUTO_TAFS_LINES]

    # Loop though all days in period
    for day in cf.DAYS:

        # Print for info of progress
        print(day)

        # If day already processed, move to next day
        if day <= holders['last_day']:
            continue

        # Update last day processed
        holders['last_day'] = day

        # Find all IMPROVER TAFs valid on this day
        auto_tafs = [get_day_tafs(day, lines) for lines in auto_tafs_lines]

        # If no TAFs found, move to next day
        if not all(auto_tafs):
            continue

        # Get all TAFs and METARs for day (3 days for METARs to cover
        # TAF periods)
        try:
            man_tafs, metars = get_day_man_tafs_metars(day)
        except:
            print(f'problem retrieving for day: {day}')
            continue

        # Loop through required ICAOs
        for icao in cf.REQ_ICAO_STRS:

            # Get day stats for ICAO
            day_icao_stats(holders, icao, auto_tafs, man_tafs[icao],
                           metars[icao])

        # Pickle at the end of each day in case something breaks
        for name, data in holders.items():
            uf.pickle_data(data, f'{cf.D_DIR}/pickles/{name}')


def get_taf_lines(f_path):
    """
    Reads in TAFs from file and returns as list.

    Args:
        f_path (str): Path to TAFs file
    Returns:
        tafs_lines (list): List of TAFs
    """
    # Read in TAFs from txt file
    with open(f_path, 'r') as tafs_file:
        tafs_lines = tafs_file.readlines()

    return tafs_lines


def get_taf_times(man_taf, vdt, a_start, a_end, a_taf):
    """
    Checks manual TAF valid and if TAF times match, returning start and
    end times if so.

    Args:
        man_taf (str): Manual TAF to check
        vdt (datetime): Validity datetime of TAFs
        a_start (datetime): Start time of auto TAF
        a_end (datetime): End time of auto TAF
        a_taf (list): Auto TAF to check against
    Returns:
        start (datetime): Start time of TAFs
        end (datetime): End time of TAFs
        tafs_match (bool): True if TAFs match
    """
    # Move on if no record or cancelled
    if man_taf == "NoRecord" or 'CNL' in man_taf:
        return False, False, False

    # This ensures manual TAF is in correct format (sometimes there are
    # errors)
    if man_taf[2] != a_taf[2]:
        return False, False, False

    # Get TAF validity time as python datetime objects (assumes month
    # and year same as first guess TAF)
    m_start, m_end = ConstructTimeObject(man_taf[2], int(man_taf[2][:2]),
                                         vdt.month, vdt.year).TAF()

    # Return False if times don't match
    if not all([a_start == m_start, a_end == m_end]):
        return False, False, False

    # Now TAFs are matched and start and end times must be the same
    start, end = a_start, a_end

    return start, end, True


def mets_all(ver_lst, worksheet, workbook, m_row_num, col):
    """
    Writes METAR to spreadsheet in appropriate format with message containing
    bust information.

    Args:
        ver_lst (list): List of busts
        worksheet (obj): Worksheet object
        workbook (obj): Workbook object
        m_row_num (int): Row number in spreadsheet
        col (int): Column number in spreadsheet
    Returns:
        new_lines (int): Number of new lines added to spreadsheet
    """
    # For keeping track of rows in spreadsheet
    new_lines = 0

    # Loop through each bust in list
    for bust in ver_lst:

        # Unpack list
        bust_types, metar = bust

        # Join ypes of bust together
        msg = ' and '.join(bust_types)

        # Colour METAR based on bust type
        if 'wind' in msg:
            if msg == 'wind':
                colour = 'red'
            elif 'visibility'in msg:
                colour = 'orange'
            elif 'weather' in msg:
                colour = 'gold'
            elif 'cloud' in msg:
                colour = 'green'
        elif 'visibility' in msg:
            if msg == 'visibility':
                colour = 'lime'
            elif 'weather' in msg:
                colour = 'cyan'
            elif 'cloud' in msg:
                colour = 'blue'
        elif 'weather' in msg:
            if msg == 'weather':
                colour = 'blueviolet'
            elif 'cloud' in msg:
                colour = 'magenta'
        elif 'cloud' in msg:
            colour = 'purple'

        # Create format
        b_form = workbook.add_format({'bold': True, 'font_color': colour})

        # Convert METAR to string and add bust type message
        metar_str = msg + ' - ' + ' '.join(metar)

        # Add METAR to spreadsheet
        worksheet.write(m_row_num, col, metar_str, b_form)

        # Add to row number and new_lines vrb
        m_row_num += 1
        new_lines += 1

    return new_lines


def mets_wind(ver_lst, worksheet, workbook, m_row_num, col):
    """
    Writes METAR to spreadsheet in appropriate format with message containing
    bust information.

    Args:
        ver_lst (list): List of busts
        worksheet (obj): Worksheet object
        workbook (obj): Workbook object
        m_row_num (int): Row number in spreadsheet
        col (int): Column number in spreadsheet
    Returns:
        new_lines (int): Number of new lines added to spreadsheet
    """
    # For keeping track of rows in spreadsheet
    new_lines = 0

    # Loop through each bust in list
    for bust in ver_lst:

        # Unpack list
        bust_types, metar = bust

        # Colour METAR based on bust type
        if bust_types['mean increase'] or bust_types['gust increase']:
            if bust_types['dir']:
                colour = 'purple'
                msg = 'Increase/dir - '
            else:
                colour = 'red'
                msg = 'Increase - '
        elif bust_types['mean decrease']:
            if bust_types['dir']:
                colour = 'green'
                msg = 'Decrease/dir - '
            else:
                colour = 'gold'
                msg = 'Decrease - '
        elif bust_types['dir']:
            colour = 'blue'
            msg = 'Dir - '
        else:
            colour = None
            msg = 'Unknown - '

        # Create format
        if colour:
            fmt = workbook.add_format({'bold': True, 'font_color': colour})
        else:
            fmt = workbook.add_format({'bold': True})

        # Convert METAR to string and add bust type message
        metar_str = msg + ' '.join(metar)

        # Add METAR to spreadsheet
        worksheet.write(m_row_num, col, metar_str, fmt)

        # Add to row number and new_lines vrb
        m_row_num += 1
        new_lines += 1

    return new_lines


def plot_dirs(holders):
    """
    Plots bar charts showing bust information for each TAF, separating busts
    by METAR wind direction.

    Args:
        holders (dict): Dictionaries of data
    Returns:
        None
    """
    # Make plots for each ICAO
    for icao in cf.REQ_ICAO_STRS:

        # Get required data
        dirs_data = {'TAF Type': [], 'Number of Busts': [], 'Direction': []}
        for t_type, t_name in cf.TAF_TYPES.items():
            d_stats = holders['dirs_stats'][f'{t_type} dirs'][icao]['dir']
            for wdir, num in d_stats.items():
                dirs_data['TAF Type'].append(t_name)
                dirs_data['Number of Busts'].append(num)
                dirs_data['Direction'].append(wdir)

        # Create bar plot
        fig, ax = plt.subplots(figsize=(10, 10))
        sns.barplot(data=dirs_data, x='Number of Busts', y='TAF Type',
                    hue='Direction')

        # Add scores on top of bars
        for ind in ax.containers:
            ax.bar_label(ind, fontsize=14)

        # Format axes, etc
        ax.legend(loc='upper left', bbox_to_anchor=(1, 1),
                  title='Wind\nDirection')
        ax.set_xlabel('Number of Busts', weight='bold')
        ax.set_ylabel('Bust Type', weight='bold')

        # Save and close figure
        img_fname = f'{cf.D_DIR}/plots/{icao}/dir_busts.png'
        plt.tight_layout()
        fig.savefig(img_fname)
        plt.close()


def plot_param(holders, param, summary_stats):
    """
    Plots parameter-specific bar chart showing bust information.

    Args:
        holders (dict): Dictionaries to store data
        param (str): Parameter to plot
        summary_stats (dict): Dictionary to store summary stats
    Returns:
        t_busts (dict): Dictionary of bust numbers
    """
    # Get stats dictionary
    stats_abs = holders[f'{param}_stats']

    # Titles, etc, for creating stats dataframes
    if param == 'wind':
        bust_types = ['Observed\nwind higher', 'Observed\nwind lower',
                      'Wind direction\nbusts', 'Total\nwind busts'] * 5
        taf_types = sum([[p_label] * 4 for p_label in cf.TAF_TYPES.values()],
                        [])
        bust_keys = sum([[f'{t_type} increase', f'{t_type} decrease',
                          f'{t_type} dir', f'{t_type} all']
                         for t_type in cf.TAF_TYPES], [])
    elif param == 'wx':
        bust_types = ['Significant\nweather busts'] * 5
        taf_types = cf.TAF_TYPES.values()
        bust_keys = [f'{t_type} all' for t_type in cf.TAF_TYPES]
    else:
        bust_types = [f'Observed\n{cf.W_NAMES[param]} higher',
                      f'Observed\n{cf.W_NAMES[param]} lower',
                      f'Total\n{cf.W_NAMES[param]} busts'] * 5
        taf_types = sum([[p_label] * 3 for p_label in cf.TAF_TYPES.values()],
                        [])
        bust_keys = sum([[f'{t_type} increase', f'{t_type} decrease',
                          f'{t_type} all'] for t_type in cf.TAF_TYPES], [])

    # Add to summary_stats with number of busts to be updated in
    # following for loop
    summary_stats['Bust Type'].extend(bust_types)
    summary_stats['TAF Type'].extend(taf_types)
    total_busts = [0 for _ in bust_types]

    # Loop through all icaos
    for ind, icao in enumerate(stats_abs):

        # Only get stats from required ICAOs
        if icao not in cf.REQ_ICAO_STRS:
            continue

        # Make directory if needed
        if not os.path.exists(f'{cf.D_DIR}/plots/{icao}'):
            os.makedirs(f'{cf.D_DIR}/plots/{icao}')

        # Get stats for airport
        stats = stats_abs[icao]

        # Add to or create t_busts dictionary
        if ind == 0:
            t_busts = {b_key: [busts] for b_key, busts in stats.items()}
        else:
            for b_key, busts in stats.items():
                t_busts[b_key].append(busts)

        # Get bust numbers for icao
        icao_busts = [stats[b_key] for b_key in bust_keys]

        # Update total bust numbers
        total_busts = [x + y for x, y in zip(total_busts, icao_busts)]

        # Create dataframe from stats
        pd_stats = {'Bust Type': bust_types, 'TAF Type': taf_types,
                    'Number of Busts': icao_busts}

        # Create bar plot
        fig, ax = plt.subplots(figsize=(14, 6))
        sns.barplot(data=pd_stats, x='Number of Busts', y='Bust Type',
                    hue='TAF Type')

        # Add scores on top of bars
        for ind in ax.containers:
            ax.bar_label(ind, fontsize=14)

        # Format axes, etc
        ax.legend(loc='upper left', bbox_to_anchor=(1, 1))
        ax.set_xlabel('Number of Busts', weight='bold')
        ax.set_ylabel('Bust Type', weight='bold')

        # Save and close figure
        img_fname = f'{cf.D_DIR}/plots/{icao}/{param}_busts.png'
        plt.tight_layout()
        fig.savefig(img_fname)
        plt.close()

    # Add to bust numbers in summary_stats
    summary_stats['Number of Busts'].extend(total_busts)

    return t_busts


def plot_summary(summary_stats):
    """
    Plots summary bar chart showing bust information.

    Args:
        summary_stats (dict): Dictionary of summary stats
    Returns:
        None
    """
    # Create bar plot
    fig, ax = plt.subplots(figsize=(14, 14))
    sns.barplot(data=summary_stats, x='Number of Busts', y='Bust Type',
                hue='TAF Type')

    # Add scores on top of bars
    for ind in ax.containers:
        ax.bar_label(ind, fontsize=14)

    # Format axes, etc
    ax.legend(loc='upper left', bbox_to_anchor=(1, 1))
    ax.set_xlabel('Number of Busts', weight='bold')
    ax.set_ylabel('Bust Type', weight='bold')

    # Save and close figure
    plt.tight_layout()
    fig.savefig(f'{cf.D_DIR}/plots/summary_busts.png')
    plt.close()


def taf_str(taf_lst):
    """
    Converts TAF in list format to and easily readable string.

    Args:
        taf_lst (list): List of TAF details
    Returns:
        stringy_taf (str): TAF as a string
        num_lines (int): Number of lines in TAF
    """
    # variables to update
    new_taf = []
    num_lines = 0

    # Loop through each TAF elemant
    for ind, ele in enumerate(taf_lst):

        # Add line breaks and spaces before certain TAF terms and append
        # new strings to new_taf list
        if ele in cf.TAF_TERMS:
            if 'PROB' not in taf_lst[ind -1]:
                new_taf.append(f'\n    {ele}')
                num_lines += 1
            else:
                new_taf.append(ele)
        else:
            new_taf.append(ele)

    # Create string from list
    stringy_taf = ' '.join(new_taf)

    return stringy_taf, num_lines


def update_infos(holders, icao, vc_tafs, vc_busts):
    """
    Updates bust information dictionaries.

    Args:
        holders (dict): Dictionaries to store data
        icao (str): ICAO of TAFs
        vc_tafs (dict): Dictionary of TAFs
        vc_busts (dict): Dictionary of busts
    Returns:
        None
    """
    # Add to other stats dictionaries for each weather type
    for w_type, w_lng in cf.W_NAMES.items():

        # Don't bother appending info if no busts
        if not any(busts[w_lng] for busts in vc_busts.values()):
            continue

        # Otherwise, append info
        w_info = {t_type: [vc_tafs[t_type], vc_busts[t_type][w_lng]]
                  for t_type in cf.TAF_TYPES}
        holders[f'{w_type}_info'][icao].append(w_info)
        # w_info = sum([[taf, busts[w_lng]]
        #               for taf, busts in zip(all_tafs, all_busts)], [])
        # holders[f'{w_type}_info'][icao].append(w_info)


def update_stats(holders, vc_busts, icao):
    """
    Updates bust statistics dictionaries.

    Args:
        holders (dict): Dictionaries to store data
        vc_busts (dict): Dictionary of busts
        icao (str): ICAO of TAFs
    Returns:
        None
    """
    # Loop through all TAF types and weather types
    for (t_type, p_busts), w_type in itertools.product(vc_busts.items(),
                                                       cf.W_NAMES):

        # Add to 'wind', 'vis', 'cld' and 'wx' dictionaries
        add_stats(holders, w_type, icao, p_busts, t_type, w_type)

        # Add to 'all' dictionaries
        add_stats(holders, 'all', icao, p_busts, t_type, w_type)


def write_to_excel(holders, w_type):
    """
    Writes verification info to Excel file.

    Args:
        holders (dict): Dictionaries of data
        w_type (str): Type of weather to write to Excel file
    Returns:
        None
    """
    # Get required data
    w_stats = holders[f'{w_type}_stats']
    w_info = holders[f'{w_type}_info']

    # Open Excel workbook
    fname = f'{w_type}_vers.xlsx'
    workbook = xlsxwriter.Workbook(fname)

    # Create separate worksheet for each ICAO
    for icao in w_info:

        # Move to next iteration if no data
        if not w_info[icao]:
            continue

        # Otherwise, create worksheet
        worksheet = workbook.add_worksheet(icao)

        # Define formats for filling cells
        taf_format = workbook.add_format({'text_wrap':'true'})
        bold = workbook.add_format({'bold': True})
        big_bold = workbook.add_format({'bold': True, 'underline': True,
                                        'font_size': 14})

        # Variables specific to weather type
        if w_type == 'wind':
            msgs = ['Total number of wind', 'Increased wind', 'Decreased wind',
                    'Directional wind']
            keys = ['all', 'increase', 'decrease', 'dir']
        else:
            msgs = ['Total', 'Total wind', 'Total visibility',
                    'Total significant weather', 'Total cloud busts']
            keys = ['all', 'wind', 'vis', 'wx', 'cld']

        # For keeping track of rows to write to
        row_num = 0

        # Title
        t_str = w_type.capitalize()
        worksheet.write(row_num, 0,
                        f'{t_str} Busts for {cf.REQ_ICAO_STRS[icao]}',
                        big_bold)
        row_num += 2

        # Get ICAO stats
        i_stats = w_stats[icao]

        # Titles
        for ind, title in enumerate(cf.TAF_TYPES.values()):
            worksheet.write(row_num, ind * 12,
                            f'{title.replace("\n", " ")} Statistics', big_bold)

        # Write stats to spreadsheet
        for msg, key in zip(msgs, keys):
            row_num = write_stats(worksheet, bold, i_stats, msg, key, row_num)
        row_num += 2

        # Loop through all TAFs
        for item in w_info[icao]:

            # Add header for each TAF type
            for ind, t_type in enumerate(item):
                worksheet.write(row_num, ind * 12,
                                cf.TAF_TYPES[t_type].replace('\n', ' '),
                                big_bold)

            # Add to row number
            row_num += 1

            # Add TAF for each TAF type
            all_lines = []
            for ind, (t_type, (taf, _)) in enumerate(item.items()):

                # Change TAF format to add to worksheet
                t_taf, lines = taf_str(taf)
                all_lines.append(lines)

                # Write TAF to spreadsheet
                worksheet.merge_range(row_num, ind * 12, row_num + lines,
                                      ind * 12 + 6, t_taf, taf_format)

            # Add to row number
            row_num += max(all_lines) + 2

            # Busts header
            for ind in range(len(item)):
                worksheet.write(row_num, ind * 12, 'TAF Busts', big_bold)

            # Add to row number
            row_num += 1

            # Add METARs for each TAF type
            all_lines = []
            for ind, (t_type, (_, ver)) in enumerate(item.items()):
                if w_type == 'wind':
                    all_lines.append(mets_wind(ver, worksheet, workbook,
                                               row_num, ind * 12))
                else:
                    all_lines.append(mets_all(ver, worksheet, workbook,
                                              row_num, ind * 12))

            # Add to row number
            row_num += max(all_lines) + 2

    # Close workbook
    workbook.close()

    # Copy Excel file to ml_plots directory
    os.system(f'mv {fname} {cf.D_DIR}/plots')


def write_stats(worksheet, fmt, stats_dict, msg, key_stat, r_num):
    """
    Writes stats to spreadsheet, returning row number.

    Args:
        worksheet (xlsxwriter.worksheet): Worksheet to write to
        fmt (xlsxwriter.format): Format to write in
        stats_dict (dict): Dictionary of stats
        msg (str): Message to write
        key_stat (str): Key to access stats
        r_num (int): Row number to write to
    Returns:
        r_num (int): Updated row number
    """
    r_num += 1
    for ind, t_type in enumerate(cf.TAF_TYPES):
        t_stat = stats_dict[f'{t_type} {key_stat}']
        t_str = f'{msg} busts: {t_stat}'
        worksheet.write(r_num, ind * 12, t_str, fmt)

    return r_num


if __name__ == "__main__":

    # Print time
    time_1 = uf.print_time('started')

    # Get user defined indication for whether new data is needed
    new_data = sys.argv[1]

    # Run main function
    main(new_data)

    # Print time
    time_2 = uf.print_time('Finished')

    # Print time taken
    uf.time_taken(time_1, time_2, unit='seconds')
