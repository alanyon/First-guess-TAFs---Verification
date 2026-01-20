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
    taf_str: Converts TAF in list format to and easily readable string.
    update_infos: Updates info dictionaries.
    update_stats: Updates stats dictionaries.

Written by Andre Lanyon.
"""
import itertools
import sys
from copy import deepcopy
from datetime import datetime, timedelta

import metdb
import pandas as pd
import numpy as np
import seaborn as sns
import useful_functions as uf
from taf_monitor.checking import CheckTafThread
from taf_monitor.time_functionality import ConstructTimeObject

import configs as cf
import plots_and_spreadsheets as ps

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
    stats = {'Month': [], 'Visibility Busts': [], 
             'Cloud Busts': [], 'Wind Busts': [], 'Weather Busts': [], 
             'Number of METARs': [], 'Number of Amends': [], 
             'Number of Corrections': []}

    # Get new data and add to data holders
    get_new_data(stats)

    # Create directories if necessary
    ps.create_dirs()


def add_cats(holders, s_type, icao, cats, t_type, w_type):
    """
    Adds bust stats to appropriate lists in dictionaries.

    Args:
        holders (dict): Dictionaries to store data
        s_type (str): Type of stats to add
        icao (str): ICAO of TAF
        cats (dict): Dictionary of cats covered in TAF
        t_type (str): TAF type
        w_type (str): Weather type
    Returns:
        None
    """
    # Key for holders dictionary
    s_key = f'{s_type}_cats'

    # Get busts and METARs for para from list
    w_cats = cats[cf.W_NAMES[w_type]]

    # Extend list of categories covered
    holders[s_key][icao][t_type].extend(w_cats)
    
    
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
    
    # Loop through all busts and METARs
    for (busts, metar, _) in busts_metars:

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

            # Add bust type
            for bust in busts:
                if f'{t_type} {bust}' in holders[s_key][icao]:
                    holders[s_key][icao][f'{t_type} {bust}'] += 1
                else:
                    holders[s_key][icao][f'{t_type} {bust}'] = 1

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
        busts, cats_covered = CheckTafThread(icao, start, end, taf, 
                                             metars).run()

    # If any issues, assume TAF is bad and print error out to check
    except Exception as e:
        print(f'Error: {e}')
        busts, cats_covered = None, None
        print(f'Problem with TAF: {taf}')

    return busts, cats_covered


def day_icao_stats(month_stats, icao, man_tafs, metars):
    """
    Gets day stats for ICAO and adds to holders dictionary.

    Args:
        holders (dict): Dictionaries to store data
        icao (str): ICAO to get stats for
        man_tafs (list): List of manual TAFs with month and year info
        metars (list): List of METARs
    Returns:
        None
    """
    # Find TAF with correct timings
    for taf_info in man_tafs:

        # Get TAF and validity datetime
        taf = taf_info['taf']
        day = taf_info['day']
        month = taf_info['month']
        year = taf_info['year']
        amend = taf_info['amend']
        correction = taf_info['correction']

        # Add to amends and corrections counts
        if amend:
            month_stats['num_amends'] += 1
            continue
        if correction:
            month_stats['num_corrections'] += 1
            continue

        # Get start and end times of TAF
        start, end = ConstructTimeObject(taf[2], day, month, year).TAF()

        # Get all METARs valid for TAF period
        v_metars = [metar for vdt, metar in metars if start <= vdt <= end]

        # Count busts
        busts, _ = count_busts(taf, v_metars, icao, start, end)

        # Move on if bad TAF found
        if busts is None:
            continue

        for w_type in ['wind', 'visibility', 'cloud', 'weather', 'all']:
            month_stats[f'{w_type}_busts'] += len(busts[w_type])


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
                         elements=['ICAO_ID', 'TAF_RPT_TXT', 'YR', 'MON', 
                                   'DAY', 'FCST_BGN_DAY', 'AMND_NUM', 
                                   'COR_NUM'])

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

        # Get TAFs and validity datetimes
        tafs_infos = get_tafs_infos(icao_tafs, icao)

        # Add to TAFs dictionary
        day_tafs[str(icao, 'utf-8').strip()] = tafs_infos

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
            metar_comps = metar_list[8:]

            # Ignore if format wrong
            if 'EG' not in metar_comps[0]:
                continue

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


def get_new_data(stats):
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
    # Loop though all days in period
    month_stats = {'visibility_busts': 0, 'cloud_busts': 0, 'wind_busts': 0,
                   'weather_busts': 0, 'all_busts': 0, 'num_metars': 0, 
                   'num_amends': 0, 'num_corrections': 0}
    current_month = cf.DAYS[0].strftime('%Y-%m')
    for day in cf.DAYS:

        # Print for info of progress
        print(day)

        month = day.strftime('%Y-%m')
        if month != current_month:
            stats['Month'].append(current_month)
            stats['Visibility Busts'].append(month_stats['visibility_busts'])
            stats['Cloud Busts'].append(month_stats['cloud_busts'])
            stats['Wind Busts'].append(month_stats['wind_busts'])
            stats['Weather Busts'].append(month_stats['weather_busts'])
            stats['Number of METARs'].append(month_stats['num_metars'])
            stats['Number of Amends'].append(month_stats['num_amends'])
            stats['Number of Corrections'].append(month_stats['num_corrections'])
            current_month = month
            month_stats = {'visibility_busts': 0, 'cloud_busts': 0,
                           'wind_busts': 0, 'weather_busts': 0, 'all_busts': 0, 
                           'num_metars': 0, 'num_amends': 0, 
                           'num_corrections': 0}
            
            # Pickle stats so far
            print(stats)
            uf.pickle_data(stats, f'{cf.D_DIR}/stats.pkl')

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
            day_icao_stats(month_stats, icao, man_tafs[icao], metars[icao])

    print(stats)


def get_taf_length(taf):
    """
    Returns the length of the TAF (base conditions plus change groups).

    Args:
        taf (str): TAF to check
    Returns:
        taf_length (int): Length of TAF
    """
    # Initialise count
    count = 1

    # Loop through TAF elements
    for ind, ele in enumerate(taf):

        # These indicate a new change group
        if ele in ['BECMG', 'PROB30', 'PROB40']:
            count += 1

        # TEMPO can indicate new change group only if not preceded by
        # PROB30 or PROB40
        elif ele == 'TEMPO' and taf[ind - 1] not in ['PROB30', 'PROB40']:
            count += 1

    return count


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


def get_tafs_infos(tafs, icao):

    tafs_infos = []
    for taf in tafs:

        # Get TAF elements
        taf_list = str(taf['TAF_RPT_TXT'], 'utf-8').strip().split()
        taf_elmts = taf_list[taf_list.index(str(icao, 'utf-8').strip()):]

        # Get issue day of TAF
        issue_day = datetime(year=taf['YR'], month=taf['MON'],
                             day=taf['DAY'])

        # Get validity day of TAF (carefully with month changeovers)
        if taf['FCST_BGN_DAY'] < taf['DAY']:
            v_day = issue_day + timedelta(days=1)
        else:
            v_day = issue_day

        # Define month and year of TAF start and add to list
        taf_info = {'taf': taf_elmts, 'day': taf['FCST_BGN_DAY'],
                    'month': v_day.month, 'year': v_day.year, 
                    'amend': bool(taf['AMND_NUM']), 
                    'correction': bool(taf['COR_NUM'])}
        tafs_infos.append(taf_info)

    return tafs_infos


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


def update_stats(holders, vc_busts, vc_cats, icao):
    """
    Updates bust statistics dictionaries.

    Args:
        holders (dict): Dictionaries to store data
        vc_busts (dict): Dictionary of busts
        vc_cats (dict): Dictionary of categories covered
        icao (str): ICAO of TAFs
    Returns:
        None
    """
    # Loop through all TAF types and weather types
    for t_type, w_type in itertools.product(cf.TAF_TYPES, cf.W_NAMES):

        # Define busts and cats
        p_busts = vc_busts[t_type]
        cats = vc_cats[t_type]

        # Add to 'wind', 'vis', 'cld' and 'wx' dictionaries
        add_stats(holders, w_type, icao, p_busts, t_type, w_type)

        # Add to 'all' dictionaries
        add_stats(holders, 'all', icao, p_busts, t_type, w_type)

        # Add to 'vis_cats' dictionary
        if w_type in ['vis', 'cld']:
            add_cats(holders, w_type, icao, cats, t_type, w_type)


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
