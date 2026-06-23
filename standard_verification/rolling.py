"""
Module to extract recent TAFs (previous 90 days) and calculate
verification scores for each TAF type and airport. The scores are saved
to a CSV file for each airport.

Functions:
    main(): Main function to extract TAFs and calculate scores.
    analyse_tafs(): Analyse TAFs for a given airport and TAF type.
    calc_scores(): Calculate scores for a given airport and TAF type.
    convert_manual_tafs(): Convert manual TAFs to verification format.
    decode_tafs(): Decode TAFs for each type, create SQLite databases.
    get_tafs(): Extract TAFs for the given date range.
    update_configs_make_dirs(): Update config files, make directories.

Written by Andre Lanyon, 2026.
"""
import os
import subprocess
from datetime import datetime, timedelta

import pandas as pd

import driver as dv
import print_stats as ps
import TAFDecode_tafs as td

# Import environment variables
OUT_DIR = os.environ['OUT_DIR']
DATA_DIR = os.environ['DATA_DIR']
TAF_TYPES = os.environ['TAF_TYPES'].split()
CYCLE_DATE = os.environ['CYCLE_DATE']
INFO_FILE = os.environ['INFO_FILE']
AIRPORT_INFO = pd.read_csv(INFO_FILE, header=0)


def main():
    """
    Main function to extract TAFs, decode them, and calculate
    verification scores.

    Args:
        None
    Returns:
        None
    """
    # Remove files from previous runs
    for taf_type in TAF_TYPES:
        os.system(f'rm -f {DATA_DIR}/{taf_type}/*')
    os.system(f'rm -rf {DATA_DIR}/decodes/*')

    # Start 90 days before yesterday and end 90 days later
    end_dt = datetime.strptime(CYCLE_DATE, '%Y%m%d') - timedelta(days=1)
    start_dt = end_dt - timedelta(days=90)

    # Get TAFs for 90 day period
    all_tafs = get_tafs(start_dt, end_dt)

    # Decode TAFs
    decode_tafs(all_tafs)

    # Update config files for each TAF type
    update_configs_make_dirs(all_tafs)

    # Loop through airport info dataframe to get ICAOs
    for _, row in AIRPORT_INFO.iterrows():

        # Ignore defence TAFs
        if row['bench'] == 'defence':
            continue

        # Try to calculate scores (fails if no TAF data, hence except)
        try:
            calc_scores(row, start_dt, end_dt)
        except OSError as e:
            print(f"Error processing ICAO {row['icao']}: {e}")


def analyse_tafs(icao, start_dt, end_dt, length):
    """
    Analyse TAFs for a given airport and TAF type, and save to output
    files.

    Args:
        icao (str): ICAO code for the airport
        start_dt (datetime): Start datetime for verification period
        end_dt (datetime): End datetime for verification period
        length (str): Length of TAF (9, 24 or 30 hours)
    """
    # Loop through TAF types
    for taf_type in TAF_TYPES:

        # Define output directories and files
        out_dir = f'{DATA_DIR}/{taf_type}'
        vis_file = f'{out_dir}/{icao}_90_vis.nc'
        clb_file = f'{out_dir}/{icao}_90_clb.nc'
        config_file = f'{DATA_DIR}/{taf_type}.cfg'

        # Call driver code
        dv.main_from_params(start_dt=start_dt, end_dt=end_dt, sitelist=[icao],
                            ver_period=timedelta(hours=int(length)),
                            verpy_vis_out=vis_file, verpy_clb_out=clb_file,
                            config_file=config_file)


def calc_scores(row, start_dt, end_dt):
    """
    Calculate verification scores for a given airport and TAF type.

    Args:
        row (pd.Series): Row from dataframe containing airport info
        start_dt (datetime): Start datetime for verification period
        end_dt (datetime): End datetime for verification period
    Returns:
        None
    """
    # Define start and end strings
    start_str = start_dt.strftime('%Y%m%d')
    end_str = end_dt.strftime('%Y%m%d')

    # Get ICAO and TAF length from row
    icao = row['icao']
    length = str(row['taf_len'])

    # Analyse TAFs for each TAF type and save to output files
    analyse_tafs(icao, start_dt, end_dt, length)

    # Match TAFs of various types and calculate verification scores
    scores_df, cts_vis, cts_clb = match_verify(icao, start_str, end_str)

    # Add to csv file or create new one if it doesn't exist
    scores_file = f'{DATA_DIR}/stats/{icao}_scores.csv'
    if os.path.exists(scores_file):
        old_scores_df = pd.read_csv(scores_file)
        scores_df = pd.concat([old_scores_df, scores_df], ignore_index=True)
    scores_df.to_csv(scores_file, index=False)

    # Save contingency table values for plotting
    for taf_type in TAF_TYPES:
        ct_vis = cts_vis[taf_type]
        ct_clb = cts_clb[taf_type]
        ct_vis.to_csv(f'{DATA_DIR}/cts/{icao}_ct_vis_{taf_type}.csv')
        ct_clb.to_csv(f'{DATA_DIR}/cts/{icao}_ct_clb_{taf_type}.csv')


def convert_manual_tafs(txt_file, taf_dir):
    """
    Convert manual TAFs to verification format.

    Args:
        txt_file (str): Name of the text file containing manual TAFs
        taf_dir (str): Directory containing the text file
    Returns:
        ver_tafs (list): List of TAFs in verification format
    """
    # Read lines from manual TAF file
    with open(os.path.join(taf_dir, txt_file), 'r', encoding='utf-8') as f:
        lines = f.read().splitlines()

    # Get TAFs as single lines - each starts with TAF and ends with =
    tafs = []
    taf = ''
    for line in lines:
        if line.startswith('TAF'):
            taf = line.strip()
        elif line.endswith('='):
            taf += ' ' + line.strip()
            tafs.append(taf)
            taf = ''
        else:
            taf += ' ' + line.strip()

    # Get TAF start time from directory and filename
    taf_start = datetime.strptime(taf_dir[-8:] + txt_file[0:2], '%Y%m%d%H')

    # Get issue date by subtracting 1 hour from TAF start time
    issue_dt = taf_start - timedelta(hours=1)
    issue_date = issue_dt.strftime('%d/%m/%y')

    # Loop through TAFs and put in verification format
    ver_tafs = []
    for taf in tafs:

        # Remove 'TAF' and '='
        taf = taf.replace('TAF', '').replace('=', '').strip()

        # Get issue time
        issue_time = taf.split()[1][2:]

        # Determine TAF send time
        send_time = issue_dt.strftime("%H05")

        # Create verification TAF string
        ver_taf = (f'T {issue_time} {issue_date}                EGRR '
                   f'{send_time} 0 0 {taf}')

        # Append to list of verification TAFs
        ver_tafs.append(ver_taf)

    return ver_tafs


def decode_tafs(all_tafs):
    """
    Decode TAFs for each TAF type and create SQLite databases.

    Args:
        all_tafs (dict): Dictionary containing TAFs for each TAF type
    Returns:
        None
    """
    # Loop through TAF types
    for taf_type, tafs in all_tafs.items():

        # Make directories
        in_dir = f'{DATA_DIR}/decodes/Input_{taf_type}'
        out_dir = f'{DATA_DIR}/decodes/Output_{taf_type}'
        os.makedirs(in_dir)
        os.makedirs(out_dir)

        # Write TAFs to input file
        with open(f'{DATA_DIR}/decodes/Input_{taf_type}/tafs.txt', 'w',
                  encoding='utf-8') as f:
            f.write('\n'.join(tafs))

        # Convert TAFs to correct format and save to output directory
        with open(f'{DATA_DIR}/decodes/Output_{taf_type}/out.log', 'w',
                  encoding='utf-8') as _, \
             open(f'{DATA_DIR}/decodes/Output_{taf_type}/err.log', 'w',
                  encoding='utf-8') as _:
            td.main(in_dir, out_dir)

        # Create sql dSatabase
        taf_data = f"{out_dir}/acceptedTafs.csv"
        taf_decoded_data = f"{out_dir}/decodedTafs.csv"
        db_file = f"{DATA_DIR}/decodes/{taf_type}.db"
        sqlite_commands = "\n".join([
            f".read {DATA_DIR}/create_tables.sql",
            '.separator ","',
            f'.import "{taf_data}" taf_load',
            f'.import "{taf_decoded_data}" taf_decoded_load',
            f".read {DATA_DIR}/copy_data.sql"
        ])
        subprocess.run(["sqlite3", db_file], input=sqlite_commands, text=True,
                       check=False)


def get_tafs(taf_date, end_date):
    """
    Extract TAFs for the given date range and return them in a
    dictionary.

    Args:
        taf_date (datetime): Start date for TAF extraction
        end_date (datetime): End date for TAF extraction
    Returns:
        all_tafs (dict): Dictionary containing TAFs for each TAF type
    """
    # Create dictionary to hold TAFs
    all_tafs = {taf_type: [] for taf_type in TAF_TYPES}

    # Loop through dates from start to end
    while taf_date <= end_date:

        # Find tafs for day
        taf_dir = f'{OUT_DIR}/{taf_date.strftime("%Y%m%d")}'

        # Loop through all files in directory
        for txt_file in os.listdir(taf_dir):

            # Ignore non-txt files
            if not txt_file.endswith('.txt'):
                continue

            # Go through verification TAF files
            if 'verification' in txt_file:

                # Read TAFs from file
                with open(os.path.join(taf_dir, txt_file), 'r',
                          encoding='utf-8') as f:
                    tafs = f.read().splitlines()

                # Loop through TAFs
                for taf in tafs:

                    # Get ICAO from TAF and ignore if defence
                    icao = taf.split()[7]
                    info = AIRPORT_INFO[AIRPORT_INFO['icao'] == icao]
                    if info['bench'].values[0] == 'defence':
                        continue

                    # Add TAF to month collection
                    taf_type = txt_file[17: -4]
                    all_tafs[taf_type].append(taf)

            # Need to convert manual TAFs to correct format
            elif 'issue' in txt_file and 'UK' not in txt_file:

                # Convert to verification format and add to dictionary
                tafs = convert_manual_tafs(txt_file, taf_dir)
                all_tafs['manual'].extend(tafs)

        # Add one day to TAF date
        taf_date += timedelta(days=1)

    return all_tafs


def match_verify(icao, start_str, end_str):
    """
    Matches TAFs of various types and calculates verification scores,
    saving the results to CSV files.

    Args:
        icao (str): ICAO code for the airport
        start_str (str): Start date in YYYYMMDD format
        end_str (str): End date in YYYYMMDD format
    Returns:
        scores_df (pd.DataFrame): DataFrame containing verification scores
        cts_vis (dict): Dictionary of contingency tables for visibility
        cts_clb (dict): Dictionary of contingency tables for cloud base
    """
    gerrity_vis, peirce_vis, cts_vis = ps.main('vis', icao, start_str, end_str)
    gerrity_clb, peirce_clb, cts_clb = ps.main('clb', icao, start_str, end_str)

    # Create dataframe to hold scores
    scores = {'Date': [end_str]}
    for s_name_score, score in gerrity_vis.items():
        scores[f'gerrity_vis_{s_name_score}'] = [score]
    for s_name_score, score in gerrity_clb.items():
        scores[f'gerrity_clb_{s_name_score}'] = [score]
    for s_name_score, p_scores in peirce_vis.items():
        for ind, score in enumerate(p_scores):
            scores[f'peirce_vis_{s_name_score}_{ind}'] = [score]
    for s_name_score, p_scores in peirce_clb.items():
        for ind, score in enumerate(p_scores):
            scores[f'peirce_clb_{s_name_score}_{ind}'] = [score]
    scores_df = pd.DataFrame(scores)

    return scores_df, cts_vis, cts_clb


def update_configs_make_dirs(all_tafs):
    """
    Update config files with new data directory.

    Args:
        all_tafs (dict): Dictionary containing TAFs for each TAF type
    Returns:
        None
    """
    # Make stats directory if necessary
    stats_dir = f'{DATA_DIR}/stats'
    if not os.path.exists(stats_dir):
        os.makedirs(stats_dir)

    # Loop through TAF types
    for t_type in all_tafs:

        # Make TAF type output directory if necessary
        t_type_dir = f'{DATA_DIR}/{t_type}'
        if not os.path.exists(t_type_dir):
            os.makedirs(t_type_dir)

        # Define lines to write to config file
        lines = ['[defaults]\n',
                 (f'taf_connection_string = sqlite:///{DATA_DIR}/decodes/'
                  f'{t_type}.db\n'),
                 'metar_connection_string = oracle://:@verifyop\n',
                 'table_schema = cfsb\n',
                 'taf_table = taf_decoded_data\n',
                 'rawtaf_table = taf_data\n',
                 'metar_table = sbv_metar_decoded_data\n',
                 'extract_lookahead = 3\n',
                 'sql_debug = False\n',
                 ('vis_cats = Category.from_thresh([350, 800, 1500, 5000, '
                 '10000])\n'),
                 'clb_cats = Category.from_thresh([200, 500, 1000, 1500])\n',
                 'ft_to_m = 0.3048\n',
                 'use_autometars = True\n',
                 'use_specis = False\n',
                 'probbins = Problist([0.0, 0.3, 0.4, 0.6, 0.7, 1.0])\n',
                 'vis_verpy_str = vis\n',
                 'clb_verpy_str = cbh|5.0\n',
                 'metars_per_hour = 2\n']

        # Write lines to config file
        with open(f'{DATA_DIR}/{t_type}.cfg', 'w',
                  encoding='utf-8') as t_file:
            t_file.writelines(lines)


if __name__ == "__main__":
    main()
