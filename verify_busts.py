"""
Script to count number of TAF busts, calculate statistics and output
plots and spreadsheets.

Functions:
    main: Main function calling all other functions.
    add_stats: Adds bust stats to appropriate lists in dictionaries.
    count_busts: Counts the number of busts in a TAF.
    get_common_metars: Returns list of METARs common to all TAF types.
    get_day_man_tafs_metars: Extracts manual TAFs and METARs.
    get_day_tafs: Extracts all TAFs issued on specified day.
    get_dir_percs: Gets percentages of busts in each wind direction.
    get_holders: Returns dictionaries to store data.
    get_icao_metars: Returns dictionary of METARs for specified ICAO.
    get_new_data: Extracts TAFs and METARs and compares them.
    get_row_deets: Extracts required details from row.
    get_stats_percs: Calculates percentage of busts.
    get_taf_lines: Reads in TAFs from file.
    get_taf_times: Checks if TAFs match and returns start and end times.
    mets_all: Writes METAR to spreadsheet.
    mets_wind: Writes METAR to spreadsheet.
    plot_dirs: Plots wind busts in each direction.
    plot_param: Plots busts for each parameter.
    plot_summary: Plots summary of all busts.
    taf_str: Converts TAF in list format to and easily readable string.
    t_tests: Performs t-tests on bust number distributions.
    update_infos: Updates info dictionaries.
    update_metar_dirs: Updates METAR wind directions dictionary.
    update_stats: Updates stats dictionaries.
    write_to_excel: Writes data to Excel spreadsheet.
    write_stats: Writes stats to Excel spreadsheet.

Written by Andre Lanyon, 11/10/2023.
"""
import itertools
import os
import sys
from copy import deepcopy
from datetime import datetime, timedelta

import matplotlib.pyplot as plt
import metdb
import numpy as np
import pandas as pd
import seaborn as sns
import useful_functions as uf
import xlsxwriter
from dateutil.rrule import DAILY, rrule
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm
from scipy import stats

import configs as cf
from checking import CheckTafThread
from data_retrieval import RetrieveObservations
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

    # Create spreadsheets
    # write_to_excel(holders, 'wind')
    # write_to_excel(holders, 'all')

    # Make plots
    # plot_dirs(holders)
    summary_stats = {'Bust Type': [], 'TAF Type': [], 'Number of Busts': []}
    vis_busts = plot_param(holders, 'vis', summary_stats)
    wx_busts = plot_param(holders, 'wx', summary_stats)
    cld_busts = plot_param(holders, 'cld', summary_stats)
    wind_busts = plot_param(holders, 'wind', summary_stats)
    plot_summary(summary_stats)
    # t_tests(vis_busts, cld_busts, wx_busts, wind_busts)


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
            d_key = f'{t_type}_dirs'
            if busts['mean increase'] or busts['gust increase']:
                holders[s_key][icao][f'{t_type} increase'] += 1
                if dir_lab:
                    holders[d_key][icao]['increase'][dir_lab] += 1
            if busts['mean decrease']:
                holders[s_key][icao][f'{t_type} decrease'] += 1
                if dir_lab:
                    holders[d_key][icao]['decrease'][dir_lab] += 1
            if busts['dir']:
                holders[s_key][icao][f'{t_type} dir'] += 1
                if dir_lab:
                    holders[d_key][icao]['dir'][dir_lab] += 1

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


def get_common_metars(all_busts):
    """
    Returns list of METARs common to all TAF types.

    Args:
        all_busts (list): List of busts for all TAF types
    Returns:
        common_metars (list): List of METARs common to all TAF types
    """
    # Get all relevant METARs
    all_metars = [busts['metars_used'] for busts in all_busts]

    # Get METARs common to all TAF types
    common_metars = [
        metar for metar in all_metars[0] if all(metar in m_list
                                                for m_list in all_metars)
    ]

    return common_metars


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
    # Get all TAFs for day
    all_tafs = metdb.obs(
        cf.METDB_EMAIL, 'TAFS',
        keywords=['PLATFORM EG',
                  f'START TIME {day.strftime("%Y%m%d/0000")}Z',
                  f'END TIME {day.strftime("%Y%m%d/2359")}Z'],
        elements=['ICAO_ID', 'TAF_RPT_TXT']
    )

    # Get METARs for all possible times TAFs cover (3 days)
    all_metars = [metdb.obs(
        cf.METDB_EMAIL, 'METARS',
        keywords=[
            'PLATFORM EG',
            f'START TIME {(day + timedelta(days=ind)).strftime("%Y%m%d/0000")}Z',
            f'END TIME {(day + timedelta(days=ind)).strftime("%Y%m%d/2359")}Z'
        ],
        elements=['ICAO_ID', 'MTR_RPT_TXT']
    )
    for ind in range(3)
    ]

    # Get SPECIs for all possible times TAFs cover
    all_specis = [metdb.obs(
        cf.METDB_EMAIL, 'SPECI',
        keywords=[
            'PLATFORM EG',
            f'START TIME {(day + timedelta(days=ind)).strftime("%Y%m%d/0000")}Z',
            f'END TIME {(day + timedelta(days=ind)).strftime("%Y%m%d/2359")}Z'
        ],
        elements=['ICAO_ID', 'MTR_RPT_TXT']
    )
    for ind in range(3)
    ]

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


def get_dir_percs(taf_dirs, metar_dirs):
    """
    Divides numbers of wind busts for each type and each direction by number
    of METARs observing wind in that direction, to get perentage of busts
    when wind is observed in each direction.

    Args:
        taf_dirs (dict): Dictionary of wind busts for each TAF type
        metar_dirs (dict): Dictionary of wind directions in METARs
    Returns:
        taf_dirs (dict): Dictionary of wind busts for each TAF type
    """
    for icao, b_type, w_dir in itertools.product(taf_dirs, cf.B_TYPES,
                                                 cf.DIRS):
        if taf_dirs[icao][b_type][w_dir] != 0:
            taf_dirs[icao][b_type][w_dir] /= (0.01 * metar_dirs[icao][w_dir])

    return taf_dirs


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
    metar_dirs = {icao: deepcopy(dirs_template) for icao in cf.REQ_ICAO_STRS}
    bd_dirs = {icao: {b_type: deepcopy(dirs_template) for b_type in cf.D_TYPES}
               for icao in cf.REQ_ICAO_STRS}
    im_dirs, man_dirs = (deepcopy(bd_dirs) for _ in range(2))
    metars_used = {icao: 0 for icao in cf.REQ_ICAO_STRS}
    last_day = cf.DAYS[0]

    # Collect all data into a dictionary
    holders = {
        'wind_info': wind_info, 'vis_info': vis_info, 'cld_info': cld_info,
        'wx_info': wx_info, 'all_info': all_info, 'wind_stats': wind_stats,
        'vis_stats': vis_stats, 'cld_stats': cld_stats, 'wx_stats': wx_stats,
        'all_stats': all_stats, 'metar_dirs': metar_dirs, 'bd_dirs': bd_dirs, 
        'im_dirs': im_dirs, 'man_dirs': man_dirs, 'metars_used': metars_used, 
        'last_day': last_day}

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

    # Read in first guess TAFs files
    bd_tafs_lines = get_taf_lines(cf.BD_TAFS)
    im_tafs_lines = get_taf_lines(cf.IM_TAFS)

    # Loop though all days in period
    for day in cf.DAYS:

        # Print for info of progress
        print(day)

        # If day already processed, move to next day
        if day <= holders['last_day']:
            continue

        # Update last day processed
        holders['last_day'] = day

        # Find all TAFs issued on this day
        day_bd_tafs = get_day_tafs(day, bd_tafs_lines)
        day_im_tafs = get_day_tafs(day, im_tafs_lines)

        # If no TAFs found, move to next day
        if not all([day_bd_tafs, day_im_tafs]):
            continue

        # Get all TAFs and METARs for day (3 days for METARs to cover
        # TAF periods)
        try:
            day_man_tafs, day_3_metars = get_day_man_tafs_metars(day)
        except:
            print(f'problem retrieving for day: {day}')
            continue

        # Loop through all BestData and IMPROVER TAFs
        for bd_row, im_row in itertools.product(day_bd_tafs, day_im_tafs):

            # Get required TAF variables
            bd_vdt, bd_taf, bd_icao = get_row_deets(bd_row)
            im_vdt, im_taf, im_icao = get_row_deets(im_row)

            # Continue to next iteration if wrong validity time or icao
            if not all([bd_vdt == im_vdt, bd_icao == im_icao]):
                continue

            # Now icaos and vdts must be the same
            icao = bd_icao
            vdt = bd_vdt
            vday = vdt.date()

            # Only need info for required ICAOs
            if icao not in cf.REQ_ICAO_STRS:
                continue

            # Get TAF validity times as python datetime objects
            taf_day = int(bd_taf[2][:2])
            bd_start, bd_end = ConstructTimeObject(bd_taf[2], taf_day,
                                                   vdt.month, vdt.year).TAF()

            # Number of METARs to expect during TAF period
            num_float = (bd_end - bd_start).total_seconds() / 1800
            num_metars = int(np.round(num_float))

            # Find TAF with correct timings
            for man_taf in day_man_tafs[icao]:

                # Attempt to match TAFs and get TAFs start/end times
                start, end, tafs_match = get_taf_times(man_taf, bd_taf, vdt,
                                                       bd_start, bd_end)

                # Move on if TAFs don't match
                if not tafs_match:
                    continue

                # Get all METARs valid for TAF period
                metars = [metar for vdt, metar in day_3_metars[icao]
                          if start <= vdt <= end]

                # Count busts for all TAF types
                all_busts = [count_busts(taf, metars, icao, start, end)
                             for taf in [bd_taf, im_taf, man_taf]]

                # Move on if bad TAF found
                if any(busts is None for busts in all_busts):
                    continue

                # Unpack busts
                bd_busts, im_busts, man_busts = all_busts

                # Get list of METARs used for all TAF types
                metars_all = get_common_metars(all_busts)

                # Update METAR wind directions dictionary
                update_metar_dirs(icao, metars_all, holders)

                # Add to METARS used count
                holders['metars_used'][icao] += num_metars

                # Add to all stats dictionaries
                vc_busts = {'bd': bd_busts, 'im': im_busts, 'man': man_busts}
                update_stats(holders, vc_busts, icao)

                # Add to all info dictionaries
                update_infos(holders, icao, bd_taf, bd_busts, im_taf,
                             im_busts, man_taf, man_busts)

                # Break for loop so only one TAF is used
                break

        # Pickle at the end of each day in case something breaks
        for name, data in holders.items():
            uf.pickle_data(data, f'{cf.D_DIR}/pickles/{name}')


def get_row_deets(row):
    """
    Extracts required details from row.

    Args:
        row (list): List of TAF details
    Returns:
        vdt (datetime): Validity datetime of TAF
        taf (list): TAF details
        icao (str): ICAO of TAF
    """
    # Get required details from row
    vdt = (datetime.strptime(row[4], '%d-%b-%y') +
           timedelta(hours=int(row[5][:2])))
    taf = row[10][46:].split()
    icao = taf[0]

    return vdt, taf, icao


def get_stats_percs(stats, metars):
    """
    Divides numbers of busts for each type by number of METARs to get
    percentage of busts.

    Args:
        stats (dict): Dictionary of bust numbers
        metars (dict): Dictionary of METARs
    Returns:
        stats_perc (dict): Dictionary of bust percentages
    """
    stats_perc = deepcopy(stats)
    for icao, i_stats in stats.items():
        for b_type, i_stat in i_stats.items():
            if metars[icao] != 0:
                stats_perc[icao][b_type] = i_stat / (0.01 * metars[icao])

    return stats_perc


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


def get_taf_times(man_taf, old_taf, vdt, old_start, old_end):
    """
    Checks if TAFs match and returns start and end times.

    Args:
        man_taf (str): Manual TAF to check
        old_taf (str): First guess TAF to check
        vdt (datetime): Validity datetime of TAFs
        old_start (datetime): Start time of first guess TAF
        old_end (datetime): End time of first guess TAF
    Returns:
        old_start (datetime): Start time of TAF
        old_end (datetime): End time of TAF
        tafs_match (bool): True if TAFs match
    """
    # Move on if no record or cancelled
    if man_taf == "NoRecord" or 'CNL' in man_taf:
        return False, False, False

    # Check first and last hours match
    if man_taf[2] != old_taf[2]:
        return False, False, False

    # Check last day matches (can be errors in manual TAF)
    if int(man_taf[2][5:7]) != int(old_taf[2][5:7]):
        return False, False, False

    # Get TAF validity time as python datetime objects (assumes month
    # and year same as first guess TAF)
    m_start, m_end = ConstructTimeObject(man_taf[2], int(man_taf[2][:2]),
                                         vdt.month, vdt.year).TAF()

    # Move on if times don't match
    if not all([old_start == m_start, old_end == m_end]):
        return False, False, False

    # Now TAFs are matched and start and end times must be the same
    return old_start, old_end, True


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
    # Get required data
    old_dirs = holders['old_dirs']
    new_dirs = holders['new_dirs']
    is_dirs = holders['is_dirs']
    metar_dirs = holders['metar_dirs']

    # Convert raw numbers of busts to percentages of total METARs
    old_percs = get_dir_percs(deepcopy(old_dirs), metar_dirs)
    new_percs = get_dir_percs(deepcopy(new_dirs), metar_dirs)
    is_percs = get_dir_percs(deepcopy(is_dirs), metar_dirs)

    # Make plots for each ICAO if any busts
    for icao in old_percs:

        # Don't make plots if no busts found
        if all(old_percs[icao][b_type][dir] == 0
               for b_type, dir in itertools.product(cf.B_TYPES, DIRS)):
            continue

        # Collect percentages for each direction for each TAF type
        old_data = {'N': [], 'S': [], 'E': [], 'W': [], 'VRB': []}
        new_data = {'N': [], 'S': [], 'E': [], 'W': [], 'VRB': []}
        is_data = {'N': [], 'S': [], 'E': [], 'W': [], 'VRB': []}
        for b_type in B_TYPES:
            old_data['N'].append(old_percs[icao][b_type]['N'])
            old_data['S'].append(old_percs[icao][b_type]['S'])
            old_data['E'].append(old_percs[icao][b_type]['E'])
            old_data['W'].append(old_percs[icao][b_type]['W'])
            old_data['VRB'].append(old_percs[icao][b_type]['VRB'])
            new_data['N'].append(new_percs[icao][b_type]['N'])
            new_data['S'].append(new_percs[icao][b_type]['S'])
            new_data['E'].append(new_percs[icao][b_type]['E'])
            new_data['W'].append(new_percs[icao][b_type]['W'])
            new_data['VRB'].append(new_percs[icao][b_type]['VRB'])
            is_data['N'].append(is_percs[icao][b_type]['N'])
            is_data['S'].append(is_percs[icao][b_type]['S'])
            is_data['E'].append(is_percs[icao][b_type]['E'])
            is_data['W'].append(is_percs[icao][b_type]['W'])
            is_data['VRB'].append(is_percs[icao][b_type]['VRB'])

        # Create figure and axis
        fig, axs = plt.subplots(1, 2, figsize=(15, 8))

        # Collect stats into lists to zip through
        bust_nums = [old_dirs, new_dirs, is_dirs]
        bust_percs = [old_data, new_data, is_data]
        titles = ['First guess old', 'First guess new' 'Manual']

        # Max percentage used in plots, used to ensure y-axes are the same for
        # first guess and issued TAF stats
        max_perc = max([max(percs[dir])
                        for percs, dir in itertools.product(bust_percs, DIRS)])

        # Draw bar plot for each TAF type
        for ax, percs, nums, title in zip(axs, bust_percs, bust_nums, titles):

            # Central x locations for bars
            x_locs = np.arange(3)

            # Plot bars
            rects_1 = ax.bar(x_locs - 2 * 0.19, percs['N'], 0.19,
                             color='#377eb8', label='North')
            rects_2 = ax.bar(x_locs - 1 * 0.19, percs['E'], 0.19,
                             color='#ff7f00', label='East')
            rects_3 = ax.bar(x_locs, percs['S'], 0.19, color='#f781bf',
                             label='South')
            rects_4 = ax.bar(x_locs + 1 * 0.19, percs['W'], 0.19,
                             color='#4daf4a', label='West')
            rects_5 = ax.bar(x_locs + 2 * 0.19, percs['VRB'], 0.19,
                             color='#a65628', label='Variable')

            # Formatting, etc
            ax.set_ylim(0, max_perc * 1.1)
            ax.set_xticks(x_locs)
            ax.tick_params(axis='x', length=0)
            ax.set_xticklabels(['Not strong enough', 'Too strong',
                                'Directional'])
            ax.set_ylabel('Percentage of METARs bust (%)')
            ax.legend(title='Direction in METAR')
            ax.set_title(f'{title} TAFs')
            for ind, x_loc in enumerate(x_locs):
                if ind == 0:
                    ax.axvline(x_loc - 0.5, color='k', linestyle='-',
                               linewidth=1, alpha=0.3)
                ax.axvline(x_loc + 0.5, color='k', linestyle='-', linewidth=1,
                           alpha=0.3)

            # Add number of busts above each bar
            all_rects = [rects_1, rects_2, rects_3, rects_4, rects_5]
            for rects, w_dir in zip(all_rects, DIRS):
                for rect, b_type in zip(rects, B_TYPES):
                    ax.text(rect.get_x() + rect.get_width()/1.7,
                            rect.get_height() + 0.001,
                            nums[icao][b_type][w_dir], fontsize=8, ha='center',
                            va='bottom')

        # Add figure title
        plt.suptitle(icao)

        # Save and close figure
        fig.savefig(f'{cf.PLOT_DIR}/dir_busts_{icao}.png')
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
                      'Wind direction\nbusts', 'Total\nwind busts'] * 3
        taf_types = (['BestData First Guess TAFs'] * 4
                     + ['IMPROVER First Guess TAFs'] * 4
                     + ['Manual TAFs'] * 4)
        bust_keys = ['bd increase', 'bd decrease', 'bd dir', 'bd all',
                     'im increase', 'im decrease', 'im dir', 'im all',
                     'man increase', 'man decrease', 'man dir', 'man all']
    elif param == 'wx':
        bust_types = ['Significant\nweather busts'] * 3
        taf_types = ['BestData First Guess TAFs', 'IMPROVER Guess TAFs',
                     'Manual TAFs']
        bust_keys = ['bd all', 'im all', 'man all']
    else:
        bust_types = [f'Observed\n{cf.W_NAMES[param]} higher',
                      f'Observed\n{cf.W_NAMES[param]} lower',
                      f'Total\n{cf.W_NAMES[param]} busts'] * 3
        taf_types = (['BestData First Guess TAFs'] * 3
                     + ['IMPROVER First Guess TAFs'] * 3
                     + ['Manual TAFs'] * 3)
        bust_keys = ['bd increase', 'bd decrease', 'bd all',
                     'im increase', 'im decrease', 'im all',
                     'man increase', 'man decrease', 'man all']

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
        bar = sns.barplot(data=pd_stats, x='Number of Busts', y='Bust Type',
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
    bar = sns.barplot(data=summary_stats, x='Number of Busts', y='Bust Type',
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
    fig.savefig(f'{cf.D_DIR}/plots/bust_plots/summary_busts.png')
    plt.close()


def t_tests(vis_busts, cld_busts, wx_busts, wind_busts):
    """
    Performs t-tests to determine if significant reductions in busts,
    plotting results in a heatmap style table.

    Args:
        vis_busts (dict): Dictionary of visibility busts
        cld_busts (dict): Dictionary of cloud busts
        wx_busts (dict): Dictionary of weather busts
    Returns:
        None
    """
    # Dictionary to store t-test results
    t_stats = {'Category': [], 'XGBoost T-Statistic': [],
               'XGBoost P-Value': [], 'Random Forest T-Statistic': [],
               'Random Forest P-Value': []}

    # Vis and cloud bust types
    for b_type in ['increase', 'decrease', 'dir', 'all']:

        # Get vis and cloud busts
        for w_type, busts in zip(['vis', 'cld', 'wx', 'wind'], 
                                 [vis_busts, cld_busts, wx_busts, wind_busts]):

            # Dont need to consider all bust types for vis/cld/wx
            if b_type == 'dir' and w_type != 'wind':
                continue
            if b_type != 'all' and w_type == 'wx':
                continue

            # Get vis busts for each category
            old_busts = busts[f'old {b_type}']
            xg_busts = busts[f'xg {b_type}']
            rf_busts = busts[f'rf {b_type}']

            # Perform t-tests
            old_xg_t, old_xg_p = stats.ttest_rel(xg_busts, old_busts,
                                                 alternative='less')
            old_rf_t, old_rf_p = stats.ttest_rel(rf_busts, old_busts,
                                                 alternative='less')

            # Add to t_stats dictionary
            t_stats['Category'].append(cf.BUST_CATS[f'{w_type} {b_type}'])
            t_stats['XGBoost T-Statistic'].append(old_xg_t)
            t_stats['XGBoost P-Value'].append(old_xg_p)
            t_stats['Random Forest T-Statistic'].append(old_rf_t)
            t_stats['Random Forest P-Value'].append(old_rf_p)

    # Convert stats dictionary to dataframe
    t_stats_df = pd.DataFrame(t_stats)

    # Order rows by BUST_CATS
    t_stats_df['order'] = t_stats_df['Category'].map(cf.CAT_ORDER)
    t_stats_df.sort_values('order', inplace=True)
    t_stats_df.drop('order', axis=1, inplace=True)

    # Set the Category column as the index so we can display it nicely
    t_stats_df.set_index('Category', inplace=True)

    # Create a new DataFrame where the P-values and T-statistics will be
    # normalized - to be used to create a color-coded heatmap
    norm_df = t_stats_df.copy()

    # Normalize the T-statistics for color coding (use absolute values
    # to highlight extremes)
    max_t_stat_xg = max(abs(t_stats_df['XGBoost T-Statistic']))
    max_t_stat_rf = max(abs(t_stats_df['Random Forest T-Statistic']))
    norm_df['XGBoost T-Statistic'] = -(t_stats_df['XGBoost T-Statistic'] /
                                      max_t_stat_xg)
    norm_df['Random Forest T-Statistic'] = -(
        t_stats_df['Random Forest T-Statistic'] / max_t_stat_rf
    )

    # Normalize the P-values around 0.05 for color coding
    norm_df['XGBoost P-Value'] = np.where(
        t_stats_df['XGBoost P-Value'] < 0.05,
        1 - t_stats_df['XGBoost P-Value'] / 0.05,
        -(t_stats_df['XGBoost P-Value'] - 0.05) / (1 - 0.05))
    norm_df['Random Forest P-Value'] = np.where(
        t_stats_df['Random Forest P-Value'] < 0.05,
        1 - t_stats_df['Random Forest P-Value'] / 0.05,
        -(t_stats_df['Random Forest P-Value'] - 0.05) / (1 - 0.05))

    # Create a custom colormap (red to green)
    clrs = [(0.8, 0.2, 0.2), (1, 0, 0), (0.95, 0.95, 0.95), (0.6, 1, 0.6),
            (0, 0.5, 0)]
    custom_cmap = LinearSegmentedColormap.from_list('custom_red_green', clrs)

    # Apply TwoSlopeNorm with sharp transition close to the threshold
    log_norm = TwoSlopeNorm(vmin=-1, vcenter=0.1, vmax=1)

    # Create figure and axis
    fig, ax = plt.subplots(figsize=(14, 6))

    # Create heatmap with color-coded P-values and T-statistics
    sns.heatmap(norm_df, annot=t_stats_df, cmap=custom_cmap, center=0,
                norm=log_norm, fmt='.5f', linewidths=0.5, cbar=False)

    # Edit axes labels
    labels = ax.get_xticklabels()
    for label in labels:
        # Insert \n before T- and P-
        label.set_text(label.get_text().replace(' T-',
                                                '\nT-').replace(' P-', '\nP-'))
    ax.set_xticklabels(labels, fontsize=20)
    ax.set_yticklabels(ax.get_yticklabels(), fontsize=20)

    # Remove x ticks but not labels
    ax.tick_params(axis='x', length=0)

    # Format the plot
    ax.set_ylabel('')
    plt.xticks(rotation=90)
    ax.xaxis.tick_top()

    # Save and close figure
    fig.savefig(f'{cf.D_DIR}/plots/bust_plots/t_tests.png',
                bbox_inches='tight')
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


def update_infos(holders, icao, bd_taf, bd_busts, im_taf, im_busts, man_taf, 
                 man_busts):
    """
    Updates bust information dictionaries.

    Args:
        holders (dict): Dictionaries to store data
        icao (str): ICAO of TAFs
        bd_taf (str): BestData TAF
        bd_busts (dict): BestData TAF busts
        im_taf (str): IMPROVER TAF
        im_busts (dict): IMPROVER TAF busts
        man_taf (str): Manual TAF
        man_busts (dict): Manual TAF busts
    Returns:
        None
    """
    # Add to other stats dictionaries for each weather type
    for w_type, w_lng in cf.W_NAMES.items():

        # Don't bother appending info if no busts
        if not any([bd_busts[w_lng], im_busts[w_lng], man_busts[w_lng]]):
            continue

        # Otherwise, append info
        w_info = [bd_taf, bd_busts[w_lng], im_taf, im_busts[w_lng], man_taf, 
                  man_busts[w_lng]]
        holders[f'{w_type}_info'][icao].append(w_info)


def update_metar_dirs(icao, metars, holders):
    """
    Updates METAR wind direction dictionary.

    Args:
        icao (str): ICAO of TAFs
        metars (list): List of METARs
        holders (dict): Dictionaries to store data
    Returns:
        None
    """
    # Get wind direction from METAR
    for metar in metars:
        w_dir = metar[2][:3]
        if w_dir.isnumeric() and int(w_dir) in cf.NUM_TO_DIR:
            dir_lab = cf.NUM_TO_DIR[int(w_dir)]
        elif w_dir == 'VRB':
            dir_lab = 'VRB'
        else:
            print('Problem with direction', metar)
            continue

        # Update direction count dictionary
        holders['metar_dirs'][icao][dir_lab] += 1


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

        # Headers
        worksheet.write(row_num, 0, 'Old First Guess TAFs Statistics',
                        big_bold)
        worksheet.write(row_num, 12,
                        'New First Guess TAFs (XGBoost) Statistcs',
                        big_bold)
        worksheet.write(row_num, 24,
                        'New First Guess TAFs (Random Forest) Statistcs',
                        big_bold)
        worksheet.write(row_num, 36, 'Manual TAFs Statistcs', big_bold)

        # Write stats to spreadsheet
        for msg, key in zip(msgs, keys):
            row_num = write_stats(worksheet, bold, i_stats, msg, key, row_num)
        row_num += 2

        # Loop through all TAFs
        for item in w_info[icao]:

            # Unpack list
            (old_taf, old_ver, xg_taf, xg_ver,
             rf_taf, rf_ver, man_taf, man_ver) = item

            # Headers
            worksheet.write(row_num, 0, 'Old First Guess TAF', big_bold)
            worksheet.write(row_num, 12, 'New First Guess TAF (XGBoost)',
                            big_bold)
            worksheet.write(row_num, 24, 'New First Guess TAF (Random Forest)',
                            big_bold)
            worksheet.write(row_num, 36, 'Manual TAF', big_bold)
            row_num += 1

            # Add line breaks to TAFs and change to strings
            old_str, old_lines = taf_str(old_taf)
            xg_str, xg_lines = taf_str(xg_taf)
            rf_str, rf_lines = taf_str(rf_taf)
            man_str, man_lines = taf_str(man_taf)

            # Write TAFs to spreadsheet
            worksheet.merge_range(row_num, 0, row_num + old_lines, 6, old_str,
                                  taf_format)
            worksheet.merge_range(row_num, 12, row_num + xg_lines, 18,
                                  xg_str, taf_format)
            worksheet.merge_range(row_num, 24, row_num + xg_lines, 30,
                                  xg_str, taf_format)
            worksheet.merge_range(row_num, 36, row_num + man_lines, 42,
                                  man_str, taf_format)

            # Add to row number
            row_num += max([old_lines, xg_lines, rf_lines, man_lines]) + 2

            # Busts header
            for col in [0, 12, 24, 36]:
                worksheet.write(row_num, col, 'TAF Busts', big_bold)

            # Add to row number
            row_num += 1

            # Write in METARs
            if w_type == 'wind':
                old_lines = mets_wind(old_ver, worksheet, workbook, row_num, 0)
                xg_lines = mets_wind(xg_ver, worksheet, workbook, row_num, 12)
                rf_lines = mets_wind(rf_ver, worksheet, workbook, row_num, 24)
                man_lines = mets_wind(man_ver, worksheet, workbook, row_num, 36)
            else:
                old_lines = mets_all(old_ver, worksheet, workbook, row_num, 0)
                xg_lines = mets_all(xg_ver, worksheet, workbook, row_num, 12)
                rf_lines = mets_all(rf_ver, worksheet, workbook, row_num, 24)
                man_lines = mets_all(man_ver, worksheet, workbook, row_num, 24)

            # Add to row number
            row_num += max([old_lines, xg_lines, rf_lines, man_lines]) + 1

    # Close workbook
    workbook.close()

    # Copy Excel file to ml_plots directory
    os.system(f'mv {fname} {cf.D_DIR}/ml_plots')


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
    old_stat = stats_dict[f'old {key_stat}']
    old_str = f'{msg} busts: {old_stat}'
    worksheet.write(r_num, 0, old_str, fmt)
    xg_stat = stats_dict[f'xg {key_stat}']
    xg_str = f'{msg} busts: {xg_stat}'
    worksheet.write(r_num, 12, xg_str, fmt)
    rf_stat = stats_dict[f'rf {key_stat}']
    rf_str = f'{msg} busts: {rf_stat}'
    worksheet.write(r_num, 24, rf_str, fmt)
    man_stat = stats_dict[f'man {key_stat}']
    man_str = f'{msg} busts: {man_stat}'
    worksheet.write(r_num, 36, man_str, fmt)

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
