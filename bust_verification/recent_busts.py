"""
Script to count number of TAF busts, calculate statistics and output
spreadsheets.

Functions:
    main: Main function calling all other functions.
    find_busts: Finds busts in TAFs for specified ICAO.
    get_auto_tafs: Reads in Auto TAFs from file.
    get_icao_metars: Gets sorted METARs and SPECIs for specified ICAO.
    get_icao_tafs: Gets TAFs for specified ICAO and TAF start.
    get_metars: Returns dictionary of METARs or SPECIs.
    get_tafs_metars: Extracts TAFs and METARs from MetDB.
    mets_all: Writes METAR to spreadsheet with message.
    taf_str: Converts TAF in list format to and easily readable string.
    update_html: Updates html file displaying bust output.
    update_infos: Updates bust information dictionaries.
    update_stats: Updates bust statistics dictionaries.
    write_to_excel: Writes verification info to Excel file.
    write_stats: Writes stats to spreadsheet, returning row number.

Written by Andre Lanyon.
"""
import itertools
import os
import pickle
import subprocess
from copy import deepcopy
from datetime import datetime, timedelta

import metdb
import pandas as pd
import xlsxwriter
from taf_monitor.checking import CheckTafThread
from taf_monitor.time_functionality import ConstructTimeObject

# Define constants
CYCLE_TIME = os.environ['CYCLE_TIME']
OUTDIR = os.environ['OUTDIR']
DATADIR = os.environ['DATADIR']
METDB_EMAIL = 'andre.lanyon@metoffice.gov.uk'
TAF_INFO_CSV = ('/home/users/andre.lanyon/first_guess_tafs/'
                'First-guess-TAFs---Verification/standard_verification/'
                'taf_info.csv')
TAF_TYPES = {'auto': 'Auto TAFs (no ML)', 'auto_ml': 'Auto TAFs (with ML)',
             'auto_ml_up_1': 'Auto TAFs (with ML) - Obs Update 1', 
             'auto_ml_up_2': 'Auto TAFs (with ML) - Obs Update 2', 
             'man': 'Manual', }
WB_TYPES = ['increase', 'decrease', 'dir', 'all']
B_TYPES = ['increase', 'decrease', 'both', 'all']
D_TYPES = ['increase', 'decrease', 'dir']
W_NAMES = {'vis': 'visibility', 'wind': 'wind', 'wx': 'weather',
           'cld': 'cloud', 'all': 'all'}
NUM_TO_DIR = dict(zip(range(0, 370, 10),
                      list('NNNNNEEEEEEEEESSSSSSSSSWWWWWWWWWNNNNN')))
TAF_TERMS = ['BECMG', 'TEMPO', 'PROB30', 'PROB40']


def main():
    """
    Main function calling all other functions.
    """
    # Get dictionaries, etc
    holders, icao_dict = get_dicts()

    # Extract TAFs and METARs for day
    all_metars, all_specis, man_tafs, taf_start_dt = get_tafs_metars()

    # Define TAF directory
    taf_dir = f'{OUTDIR}/output/{taf_start_dt.strftime("%Y%m%d")}'

    # Loop through TAF hours
    for taf_hr in ['00', '03', '06', '09', '12', '15', '18', '21']:

        # Read Auto TAFs from txt files
        auto_tafs = get_auto_tafs(taf_dir, taf_hr, 'no_obs')
        auto_tafs_ml = get_auto_tafs(taf_dir, taf_hr, 'no_obs_ml')
        auto_tafs_ml_up_1 = get_auto_tafs(taf_dir, taf_hr, 'obs_update_1_ml')
        auto_tafs_ml_up_2 = get_auto_tafs(taf_dir, taf_hr, 'obs_update_2_ml')

        # Loop through required ICAOs
        for icao in icao_dict:

            # Get TAFs for ICAO and start time
            icao_tafs = get_icao_tafs(icao, auto_tafs, auto_tafs_ml, 
                                      auto_tafs_ml_up_1, auto_tafs_ml_up_2,
                                      man_tafs)

            # Move on if no TAFs found
            if not icao_tafs:
                continue

            # Get METARs and SPECIs for ICAO
            metars, start, end = get_icao_metars(all_metars, all_specis, icao,
                                                 taf_start_dt, icao_tafs)

            # Move on if no METARs found
            if not metars:
                continue

            # Collect bust information
            icao_busts = find_busts(icao_tafs, icao, start, end, metars)

            # Move on if bad TAF found
            if icao_busts is None:
                continue

            # Add to all stats dictionaries
            update_stats(holders, icao_busts, icao)

            # Add to all info dictionaries
            update_infos(holders, icao, icao_tafs, icao_busts)

    # Write data to Excel files
    for icao in icao_dict:
        write_to_excel(holders, icao, taf_dir)

    # Update HTML file
    date_str = taf_start_dt.strftime('%Y%m%d')
    html_file = f'{OUTDIR}/html/busts.html'
    update_html(date_str, html_file)

    # Store stats in pickle file for later use
    with open(f'{DATADIR}/{date_str}.pkl', 'wb') as f:
        pickle.dump(holders, f)


def find_busts(tafs, icao, start, end, metars):
    """
    Finds busts in TAFs for specified ICAO.

    Args:
        tafs (dict): Dictionary of TAFs
        icao (str): ICAO of TAFs
        start (datetime): Start datetime of TAF validity
        end (datetime): End datetime of TAF validity
        metars (list): List of METARs for ICAO
    Returns:
        busts (dict): Dictionary of busts
    """
    # To store busts
    icao_busts = {}

    # Loop through each TAF type
    for taf_type, taf in tafs.items():

        # Try to find busts and store in dictionary
        try:
            busts, _ = CheckTafThread(icao, start, end, taf, metars).run()
            icao_busts[taf_type] = busts

        # If any issues, assume TAF is bad and print error out to check
        except Exception as e:
            print(f'Error: {e}')
            print(f'Problem with TAF: {taf}')
            icao_busts = None
            return icao_busts

    return icao_busts


def get_auto_tafs(taf_dir, taf_hr, auto_type):
    """
    Reads in Auto TAFs from file.

    Args:
        taf_dir (str): Directory for TAFs
        taf_hr (str): TAF hour to read
        auto_type (str): Specifies type of Auto TAFs to read
    Returns:
        auto_tafs (list): List of Auto TAF lines
    """
    # Define filename
    fname = f'{taf_dir}/{taf_hr}Z_verification_{auto_type}.txt'

    # Get lines from Auto TAF files
    if os.path.exists(fname):
        with open(fname, 'r', encoding='utf-8') as taf_file:
            auto_tafs = taf_file.readlines()
    else:
        auto_tafs = []

    return auto_tafs


def get_dicts():
    """
    Returns dictionaries to store data and airports info dictionary.

    Args:
        None
    Returns:
        holders (dict): Dictionaries to store data.
        icao_dict (dict): Dictionary mapping ICAO codes to airport names
    """
    # Load in airport info
    airport_info = pd.read_csv(TAF_INFO_CSV, header=0)

    # Create dictionary mapping ICAO codes to airport names
    icao_dict = pd.Series(airport_info.airport_name.values,
                          index=airport_info.icao).to_dict()

    # Otherwise, create empty dictionaries
    all_info = {icao: [] for icao in icao_dict}
    all_template = {f'{t_type} {w_type}': 0 for t_type in TAF_TYPES
                    for w_type in W_NAMES}
    all_stats = {icao: deepcopy(all_template) for icao in icao_dict}

    # Collect all data into a dictionary
    holders = {'all_info': all_info, 'all_stats': all_stats}

    return holders, icao_dict


def get_icao_metars(all_metars, all_specis, icao, taf_start_dt, icao_tafs):
    """
    Gets sorted METARs and SPECIs for specified ICAO.

    Args:
        all_metars (list): List of METARs to check
        all_specis (list): List of SPECIs to check
        icao (str): ICAO to check METARs for
        taf_start_dt (datetime): Start datetime for TAFs
        icao_tafs (dict): Dictionary of TAFs for ICAO
    Returns:
        metars (list): List of METARs for specified ICAO (or None)
        start (datetime): Start datetime for TAFs
        end (datetime): End datetime for TAFs
    """
    # Get TAF start and end times
    month, year = taf_start_dt.month, taf_start_dt.year
    man_time = icao_tafs['man'][2]
    start, end = ConstructTimeObject(man_time, int(man_time[:2]),
                                     month, year).TAF()
    # Get METARs and SPECIs for ICAO
    icao_metars = get_metars(all_metars, icao, start, end)
    icao_specis = get_metars(all_specis, icao, start, end)

    if not icao_metars and not icao_specis:
        return None, start, end

    # Combine SPECIs and METARs
    icao_metars.update(icao_specis)

    # Sort list so SPECIs in time order with METARs
    new_icao_metars = sorted(icao_metars.items())
    metars = [metar for _, metar in new_icao_metars]

    return metars, start, end


def get_icao_tafs(icao, auto_tafs, auto_tafs_ml, auto_tafs_ml_up_1, 
                  auto_tafs_ml_up_2, man_tafs):
    """
    Gets TAFs for specified ICAO and TAF start time.

    Args:
        icao (str): ICAO to get TAFs for
        auto_tafs (list): List of Auto TAFs without ML
        auto_tafs_ml (list): List of Auto TAFs with ML
        auto_tafs_ml_up_1 (list): List of Auto TAFs with ML - Update 1
        auto_tafs_ml_up_2 (list): List of Auto TAFs with ML - Update 2
        man_tafs (list): List of manual TAFs
    Returns:
        matched_tafs (dict): Dictionary of matched TAFs (or None)
    """
    # Get Auto TAFs for ICAO
    icao_auto_tafs = [row for row in auto_tafs if icao in row]
    icao_auto_tafs_ml = [row for row in auto_tafs_ml if icao in row]
    icao_auto_tafs_ml_up_1 = [row for row in auto_tafs_ml_up_1 if icao in row]
    icao_auto_tafs_ml_up_2 = [row for row in auto_tafs_ml_up_2 if icao in row]

    # Return None if no Auto TAFs found
    if any([not icao_auto_tafs, not icao_auto_tafs_ml, 
            not icao_auto_tafs_ml_up_1, not icao_auto_tafs_ml_up_2]):
        return None

    # Should only be one Auto TAF per ICAO per TAF start time
    icao_auto_taf = icao_auto_tafs[0][46:].split()
    icao_auto_taf_ml = icao_auto_tafs_ml[0][46:].split()
    icao_auto_taf_ml_up_1 = icao_auto_tafs_ml_up_1[0][46:].split()
    icao_auto_taf_ml_up_2 = icao_auto_tafs_ml_up_2[0][46:].split()

    # Get manual TAFs for ICAO
    icao_man_tafs = [str(row['TAF_RPT_TXT'], 'utf-8').strip().split()
                     for row in man_tafs
                     if str(row['ICAO_ID'], 'utf-8').strip() == icao]

    # Loop through manual TAFs to find the one with the correct
    # start time
    for man_taf in icao_man_tafs:

        # Get rid of stuff at start
        man_taf = man_taf[man_taf.index(icao):]

        # Move on if no record or cancelled
        if man_taf == "NoRecord" or 'CNL' in man_taf:
            continue

        # If start and finish times match, consider TAFs matched
        if (man_taf[2] == icao_auto_taf[2] == icao_auto_taf_ml[2] == 
            icao_auto_taf_ml_up_1[2] == icao_auto_taf_ml_up_2[2]):

            # Collect into dictionary and return
            matched_tafs = {'auto': icao_auto_taf, 'auto_ml': icao_auto_taf_ml,
                            'auto_ml_up_1': icao_auto_taf_ml_up_1,
                            'auto_ml_up_2': icao_auto_taf_ml_up_2,
                            'man': man_taf}
            return matched_tafs

    # If no manual TAF found, return None
    return None


def get_metars(all_metars, icao, start, end):
    """
    Returns dictionary of METARs or SPECIs for specified ICAO.

    Args:
        all_metars (list): List of METARs to check
        icao (str): ICAO to check METARs for
        start (datetime): Start datetime for TAFs
        end (datetime): End datetime for TAFs
    Returns:
        icao_metars (dict): Dictionary of METARs for specified ICAO
    """
    # To add METARs to
    icao_metars = {}

    # Get METARs for ICAO
    i_metars = [metar for metar in all_metars
                if str(metar['ICAO_ID'], 'utf-8').strip() == icao]

    # Loop through all METARs
    for metar in i_metars:

        # Convert METAR text to list
        metar_list = str(metar['MTR_RPT_TXT'], 'utf-8').strip().split()

        # Get METAR components needed for verification
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

        # Get METAR validity datetime and add to dictionary if in period
        m_dt = ' '.join(metar_list[:2])
        metar_vdt = datetime.strptime(m_dt, '%H%MZ %d/%m/%y')
        if start <= metar_vdt <= end:
            icao_metars[metar_vdt] = metar_comps

    return icao_metars


def get_tafs_metars():
    """
    Extracts TAFs and METARs from MetDB for specified day.

    Args:
        None
    Returns:
        all_metars (list): List of METARs
        all_specis (list): List of SPECIs
        all_tafs (list): List of TAFs
        taf_start_dt (datetime): Start datetime for TAFs
    """
    # Make TAF start 48 hours ago in order to cover TAFs up to 30 hours
    # for the whole day
    cycle_dt = datetime.strptime(CYCLE_TIME, '%Y%m%d%H')
    taf_start_dt = cycle_dt - timedelta(hours=48)
    taf_day_start = (taf_start_dt - timedelta(hours=2)).strftime("%Y%m%d/%H00")
    taf_day_end = taf_start_dt.strftime("%Y%m%d/2200")
    met_db_start = taf_start_dt.strftime('%Y%m%d/%H00')
    met_db_end = cycle_dt.strftime('%Y%m%d/%H00')

    # Get METARs for all possible times TAFs cover (3 days)
    all_metars = metdb.obs(METDB_EMAIL, 'METARS',
                           keywords=['PLATFORM EG',
                                     f'START TIME {met_db_start}Z',
                                     f'END TIME {met_db_end}Z'],
                           elements=['ICAO_ID', 'MTR_RPT_TXT'])

    # Get SPECIs for all possible times TAFs cover
    all_specis = metdb.obs(METDB_EMAIL, 'SPECI',
                           keywords=['PLATFORM EG',
                                     f'START TIME {met_db_start}Z',
                                     f'END TIME {met_db_end}Z'],
                           elements=['ICAO_ID', 'MTR_RPT_TXT'])

    # Get all TAFs for day
    all_tafs = metdb.obs(METDB_EMAIL, 'TAFS',
                         keywords=['PLATFORM EG',
                                   f'START TIME {taf_day_start}Z',
                                   f'END TIME {taf_day_end}Z'],
                         elements=['ICAO_ID', 'TAF_RPT_TXT'])

    return all_metars, all_specis, all_tafs, taf_start_dt


def mets_all(ver_lst, worksheet, workbook, m_row_num, col, type_workbook_lst):
    """
    Writes METAR to spreadsheet in appropriate format with message containing
    bust information.

    Args:
        ver_lst (list): List of busts
        worksheet (obj): Worksheet object
        workbook (obj): Workbook object
        m_row_num (int): Row number in spreadsheet
        col (int): Column number in spreadsheet
        type_workbook_lst (list): List of workbook objects
    Returns:
        new_lines (int): Number of new lines added to spreadsheet
    """
    # For keeping track of rows in spreadsheet
    new_lines = 0

    # Loop through each bust in list
    for bust in ver_lst:

        # Unpack list
        bust_types, metar, _,  = bust

        # Join ypes of bust together
        msg = ' and '.join(bust_types)

        # Colour METAR based on bust type using a mapping approach
        colour_map = {
            'wind': 'red',
            'wind and visibility': 'orange',
            'wind and weather': 'gold',
            'wind and cloud': 'green',
            'visibility': 'lime',
            'visibility and weather': 'cyan',
            'visibility and cloud': 'blue',
            'weather': 'blueviolet',
            'weather and cloud': 'magenta',
            'cloud': 'purple'
        }
        colour = colour_map.get(msg, 'black')

        # Create formats
        b_form = workbook.add_format({'bold': True, 'font_color': colour})
        t_b_form = type_workbook_lst[0].add_format({'bold': True, 
                                                    'font_color': colour})
        
        # Convert METAR to string and add bust type message
        metar_str = msg + ' - ' + ' '.join(metar)

        # Add METAR to spreadsheets
        worksheet.write(m_row_num, col, metar_str, b_form)
        type_workbook_lst[1].write(m_row_num, 0, metar_str, t_b_form)

        # Add to row number and new_lines vrb
        m_row_num += 1
        new_lines += 1

    return new_lines


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
        if ele in TAF_TERMS:
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


def update_html(date, fname):
    """
    Updates html file displaying bust output.

    Args:
        date (str): Date of TAFs
        fname (str): Filename of html file to update
    Returns:
        None
    """
    # Read in existing file, getting 2 lists of lines from the file, split
    # where an extra line is required
    with open(fname, 'r', encoding='utf-8') as file:
        lines = file.readlines()
    first_lines = lines[:-79]
    last_lines = lines[-79:]

    # Edit html file and append/edit the required lines
    first_lines[-1] = first_lines[-1].replace(' selected="selected"', '')
    first_lines.append('                    <option selected="selected" '
                       f'value="{date}">{date}</option>\n')
    last_lines[-67] = last_lines[-67].replace(last_lines[-67][31:39], date)
    last_lines[-55] = last_lines[-55].replace(last_lines[-55][31:39], date)
    last_lines[-43] = last_lines[-43].replace(last_lines[-43][31:39], date)
    last_lines[-31] = last_lines[-31].replace(last_lines[-31][31:39], date)
    last_lines[-19] = last_lines[-19].replace(last_lines[-19][31:39], date)

    # Concatenate the lists together
    new_lines = first_lines + last_lines

    # Re-write the lines to a new file
    with open(fname, 'w', encoding='utf-8') as o_file:
        for line in new_lines:
            o_file.write(line)


def update_infos(holders, icao, icao_tafs, icao_busts):
    """
    Updates bust information dictionaries.

    Args:
        holders (dict): Dictionaries to store data
        icao (str): ICAO of TAFs
        icao_tafs (dict): Dictionary of TAFs
        icao_busts (dict): Dictionary of busts
    Returns:
        None
    """
    # Don't bother appending info if no busts
    if any(busts['all'] for busts in icao_busts.values()):

        # Otherwise, append info
        w_info = {t_type: [icao_tafs[t_type], icao_busts[t_type]['all']]
                    for t_type in TAF_TYPES}
        holders['all_info'][icao].append(w_info)


def update_stats(holders, icao_busts, icao):
    """
    Updates bust statistics dictionaries.

    Args:
        holders (dict): Dictionaries to store data
        icao_busts (dict): Dictionary of busts
        icao (str): ICAO of TAFs
    Returns:
        None
    """
    # Loop through all TAF types and weather types
    for t_type, w_type in itertools.product(TAF_TYPES, W_NAMES):

        # Get busts and METARs for para from list
        busts_metars = icao_busts[t_type][W_NAMES[w_type]]

        # Loop through all busts and METARs
        holders['all_stats'][icao][f'{t_type} {w_type}'] += len(busts_metars)


def write_to_excel(holders, icao, taf_dir):
    """
    Writes verification info to Excel file.

    Args:
        holders (dict): Dictionaries of data
        icao (str): ICAO of TAFs
        taf_dir (str): Directory for TAFs
    Returns:
        None
    """
    # Get required data
    w_stats = holders['all_stats'][icao]
    w_info = holders['all_info'][icao]

    if not w_info:
        return

    # Open Excel workbook
    fname = f'{icao}.xlsx'
    workbook = xlsxwriter.Workbook(fname)

    # Create worksheet
    worksheet = workbook.add_worksheet(icao)

    # Create workbooks for each TAF type
    type_workbooks = {}
    for t_type in TAF_TYPES:
        t_fname = f'{icao}_{t_type}.xlsx'
        type_workbook = xlsxwriter.Workbook(t_fname)
        t_taf_format = type_workbook.add_format({'text_wrap': True})
        t_bold = type_workbook.add_format({'bold': True})
        t_big_bold = type_workbook.add_format({'bold': True, 'underline': True,
                                               'font_size': 14})
        type_worksheet = type_workbook.add_worksheet(icao)
        type_workbooks[t_type] = [type_workbook, type_worksheet, t_fname,
                                  t_taf_format, t_bold, t_big_bold]


    # Define formats for filling cells
    taf_format = workbook.add_format({'text_wrap': True})
    bold = workbook.add_format({'bold': True})
    big_bold = workbook.add_format({'bold': True, 'underline': True,
                                    'font_size': 14})

    # Variables specific to weather type
    msgs = ['Total', 'Total wind', 'Total visibility',
            'Total significant weather', 'Total cloud busts']
    keys = ['all', 'wind', 'vis', 'wx', 'cld']

    # For keeping track of rows to write to
    row_num = 0

    # Titles
    for ind, (t_type, title) in enumerate(TAF_TYPES.items()):
        worksheet.write(row_num, ind * 12, f'{title} Statistics', big_bold)
        type_workbooks[t_type][1].write(row_num, 0, f'{title} Statistics', 
                                        type_workbooks[t_type][5])

    # Write stats to spreadsheet
    for msg, key in zip(msgs, keys):
        row_num = write_stats(worksheet, bold, w_stats, msg, key, row_num, 
                              type_workbooks)
    row_num += 2

    # Loop through all TAFs
    for item in w_info:

        # Add header for each TAF type
        for ind, t_type in enumerate(item):
            worksheet.write(row_num, ind * 12, TAF_TYPES[t_type], big_bold)
            type_workbooks[t_type][1].write(row_num, 0, TAF_TYPES[t_type], 
                                            type_workbooks[t_type][5])

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
            type_workbooks[t_type][1].merge_range(row_num, 0, row_num + lines,
                                                  6, t_taf, 
                                                  type_workbooks[t_type][3])

        # Add to row number
        row_num += max(all_lines) + 2

        # Busts header
        for ind, (t_type, (taf, _)) in enumerate(item.items()):
            worksheet.write(row_num, ind * 12, 'TAF Busts', big_bold)
            type_workbooks[t_type][1].write(row_num, 0, 'TAF Busts', 
                                            type_workbooks[t_type][5])

        # Add to row number
        row_num += 1

        # Add METARs for each TAF type
        all_lines = []
        for ind, (t_type, (_, ver)) in enumerate(item.items()):
            all_lines.append(mets_all(ver, worksheet, workbook, row_num, 
                                      ind * 12, type_workbooks[t_type]))

        # Add to row number
        row_num += max(all_lines) + 2

    # Close workbooks
    workbook.close()
    for t_type in TAF_TYPES:
        type_workbooks[t_type][0].close()

    # Copy big Excel file to TAF output directory
    srd_dir = f'{taf_dir}/bust_spreadsheets'
    if not os.path.exists(srd_dir):
        os.makedirs(srd_dir)

    # Convert small Excel files  to pdf and move to TAF output directory
    for t_type in TAF_TYPES:
        subprocess.run(['libreoffice', '--headless', '--convert-to', 'pdf', 
                        type_workbooks[t_type][2], '--outdir', srd_dir])

    # Remove all Excel files    
    os.system(f'rm *.xlsx')


def write_stats(worksheet, fmt, stats_dict, msg, key_stat, r_num, 
                type_workbooks):
    """
    Writes stats to spreadsheet, returning row number.

    Args:
        worksheet (xlsxwriter.worksheet): Worksheet to write to
        fmt (xlsxwriter.format): Format to write in
        stats_dict (dict): Dictionary of stats
        msg (str): Message to write
        key_stat (str): Key to access stats
        r_num (int): Row number to write to
        type_workbooks (dict): Dictionary of workbooks for each TAF type
    Returns:
        r_num (int): Updated row number
    """
    r_num += 1
    for ind, t_type in enumerate(TAF_TYPES):
        t_stat = stats_dict[f'{t_type} {key_stat}']
        t_str = f'{msg} busts: {t_stat}'
        worksheet.write(r_num, ind * 12, t_str, fmt)
        type_workbooks[t_type][1].write(r_num, 0, t_str, 
                                        type_workbooks[t_type][4])

    return r_num


if __name__ == "__main__":
    main()
