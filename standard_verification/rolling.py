"""
Module to extract AUTOTAFs and calculate rolling verification scores for
each airport over a 36-month window. Scores are saved to a CSV file per
airport.

The work is split into two entry points so the expensive per-station
scoring can be fanned out into parallel Cylc jobs:
    ``python rolling.py prepare``        - run-once shared setup
    ``python rolling.py station <ICAO>`` - score a single airport

Functions:
    prepare(): Run-once shared setup (extract, decode, write configs).
    verify_station(): Score a single airport (the parallel unit of work).
    get_date_range(): Derive the verification period from the cycle date.
    analyse_tafs(): Analyse TAFs for a given airport and TAF type.
    calc_scores(): Calculate scores for a given airport and TAF type.
    decode_tafs(): Incrementally decode source files into SQLite.
    get_taf_sources(): Find archive and recent AUTOTAF source files.
    update_configs_make_dirs(): Update config files, make directories.

Written by Andre Lanyon, 2026.
"""
import argparse
import os
import sqlite3
import shutil
import subprocess
from datetime import datetime, timedelta

import pandas as pd

import driver as dv
import print_stats as ps
import TAFDecode_tafs as td

# Directory containing this script (and the SQL files it depends on)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Import environment variables
OUT_DIR = os.environ['OUT_DIR']
DATA_DIR = os.environ['DATA_DIR']
CACHE_DIR = os.path.join(DATA_DIR, 'rolling_36m_autotaf')
ARCHIVE_DIR = os.environ['ARCHIVE_DIR']
TAF_TYPES = os.environ['TAF_TYPES'].split()
CYCLE_DATE = os.environ['CYCLE_DATE']
INFO_FILE = os.environ['INFO_FILE']
AIRPORT_INFO = pd.read_csv(INFO_FILE, header=0)
ps.OUT_DIR = CACHE_DIR


def get_date_range():
    """
    Derive the verification period from the cycle date.

    The period ends the day before the cycle date and starts three calendar
    years earlier. Both the prepare and per-station steps derive the range
    from CYCLE_DATE so they always agree without having to pass dates between
    jobs.

    Args:
        None
    Returns:
        start_dt (datetime): Start datetime for the verification period
        end_dt (datetime): End datetime for the verification period
    """
    end_dt = datetime.strptime(CYCLE_DATE, '%Y%m%d') - timedelta(days=1)
    start_dt = (pd.Timestamp(end_dt) - pd.DateOffset(years=3)).to_pydatetime()
    return start_dt, end_dt


def prepare():
    """
    Run-once shared setup: extract and decode the TAFs and write the
    config files/directories that every per-station job reads.

    This is the serial part of the workflow; the expensive per-station
    scoring is fanned out into parallel jobs (see verify_station).

    Args:
        None
    Returns:
        None
    """
    # Determine the verification period
    start_dt, end_dt = get_date_range()

    # Add only new TAF source files to the persistent decoded database.
    source_files = get_taf_sources(start_dt, end_dt)
    decode_tafs(source_files, start_dt)

    # Update config files for each TAF type and make output directories
    update_configs_make_dirs()

    # Ensure the contingency table directory the station jobs write to
    # exists before any of them run
    os.makedirs(f'{CACHE_DIR}/cts', exist_ok=True)


def verify_station(icao):
    """
    Calculate verification scores for a single airport. This is the unit
    of work that is fanned out into parallel Cylc jobs.

    Args:
        icao (str): ICAO code for the airport to verify
    Returns:
        None
    """
    # Determine the verification period (matches the prepare step)
    start_dt, end_dt = get_date_range()

    # Select verifiable airports, ignoring defence TAFs and the duplicate
    # long London City row (the verification code can't deal with two
    # TAFs sharing an ICAO)
    stations = AIRPORT_INFO[
        (AIRPORT_INFO['bench'] != 'defence')
        & (AIRPORT_INFO['airport_name'] != 'London City (long)')]

    # Find this station's row
    matches = stations[stations['icao'] == icao]
    if matches.empty:
        raise SystemExit(f'ICAO {icao} is not a verifiable station')
    row = matches.iloc[0]

    # Try to calculate scores (fails if no TAF data, hence except)
    try:
        calc_scores(row, start_dt, end_dt)
    except OSError as e:
        print(f'Error processing ICAO {icao}: {e}')


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
        out_dir = f'{CACHE_DIR}/{taf_type}'
        vis_file = f'{out_dir}/{icao}_90_vis.nc'
        clb_file = f'{out_dir}/{icao}_90_clb.nc'
        config_file = (os.path.join(SCRIPT_DIR, 'Manual.cfg')
                   if taf_type == 'manual'
                   else f'{CACHE_DIR}/{taf_type}.cfg')

        # Remove any stale NetCDF from a previous run: VerPy writes with
        # overwrite=False, so leftover files would break a rerun (e.g. a
        # Cylc retry of this station)
        for stale in (vis_file, clb_file):
            if os.path.exists(stale):
                os.remove(stale)

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
    scores_file = f'{CACHE_DIR}/stats/{icao}_scores.csv'
    if os.path.exists(scores_file):
        old_scores_df = pd.read_csv(scores_file)
        scores_df = pd.concat([old_scores_df, scores_df], ignore_index=True)
    scores_df = merge_score_history(scores_df)
    scores_df.to_csv(scores_file, index=False)

    # Save contingency table values for plotting
    for taf_type in TAF_TYPES:
        ct_vis = cts_vis[taf_type]
        ct_clb = cts_clb[taf_type]
        ct_vis.to_csv(f'{CACHE_DIR}/cts/{icao}_ct_vis_{taf_type}.csv')
        ct_clb.to_csv(f'{CACHE_DIR}/cts/{icao}_ct_clb_{taf_type}.csv')


def merge_score_history(scores):
    """Keep one row per window end, retaining latest non-null scores."""
    value_columns = [column for column in scores.columns if column != 'Date']
    return scores.groupby('Date', sort=True, as_index=False).agg(
        {column: lambda values: (values.dropna().iloc[-1]
                                 if values.notna().any() else float('nan'))
         for column in value_columns})


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


def get_taf_sources(start_dt, end_dt):
    """Return historical and recent AUTOTAF source files."""
    source_files = [
        os.path.join(ARCHIVE_DIR, name)
        for name in sorted(os.listdir(ARCHIVE_DIR))
        if name.endswith('_no_p10_20_mix_all.txt')
        and not name.startswith('EGLC_long_')]

    taf_date = start_dt - timedelta(days=1)
    while taf_date <= end_dt:
        taf_dir = os.path.join(OUT_DIR, taf_date.strftime('%Y%m%d'))
        if os.path.isdir(taf_dir):
            names = sorted(os.listdir(taf_dir))
            source_files.extend(
                os.path.join(taf_dir, name)
                for name in names
                if name.endswith('_verification_mix_no_obs.txt'))
        taf_date += timedelta(days=1)

    if not source_files:
        raise FileNotFoundError('No AUTOTAF source files were found')
    return source_files


def decode_tafs(source_files, start_dt):
    """Incrementally decode source files into a persistent SQLite cache."""
    decodes_dir = os.path.join(CACHE_DIR, 'decodes')
    os.makedirs(decodes_dir, exist_ok=True)
    db_file = os.path.join(decodes_dir, 'autotaf.db')

    cached_sources = {}
    if os.path.exists(db_file):
        try:
            with sqlite3.connect(db_file) as connection:
                cached_sources = {
                    source: (size, mtime_ns)
                    for source, size, mtime_ns in connection.execute(
                        'SELECT source, size, mtime_ns FROM processed_sources')}
        except sqlite3.Error:
            os.remove(db_file)

    source_stats = {}
    for source in source_files:
        stat_result = os.stat(source)
        source_stats[source] = (stat_result.st_size, stat_result.st_mtime_ns)

    changed = any(
        source in cached_sources and cached_sources[source] != source_stats[source]
        for source in source_files)
    rebuild = not os.path.exists(db_file) or changed
    if rebuild:
        if os.path.exists(db_file):
            os.remove(db_file)
        cached_sources = {}

    pending_sources = [
        source for source in source_files
        if source not in cached_sources]

    if pending_sources:
        in_dir = os.path.join(decodes_dir, 'Input_autotaf')
        out_dir = os.path.join(decodes_dir, 'Output_autotaf')
        stage_db = os.path.join(decodes_dir, 'autotaf_stage.db')
        shutil.rmtree(in_dir, ignore_errors=True)
        shutil.rmtree(out_dir, ignore_errors=True)
        if os.path.exists(stage_db):
            os.remove(stage_db)
        os.makedirs(in_dir)
        os.makedirs(out_dir)

        with open(os.path.join(in_dir, 'tafs.txt'), 'w',
                  encoding='utf-8') as output:
            for source in pending_sources:
                with open(source, 'r', encoding='utf-8') as taf_file:
                    shutil.copyfileobj(taf_file, output)
                    output.write('\n')

        with open(os.path.join(out_dir, 'out.log'), 'w',
                  encoding='utf-8') as _, \
             open(os.path.join(out_dir, 'err.log'), 'w',
                  encoding='utf-8') as _:
            td.main(in_dir, out_dir)

        taf_data = os.path.join(out_dir, 'acceptedTafs.csv')
        taf_decoded_data = os.path.join(out_dir, 'decodedTafs.csv')
        sqlite_commands = '\n'.join([
            f'.read {SCRIPT_DIR}/create_tables.sql',
            '.separator ","',
            f'.import "{taf_data}" taf_load',
            f'.import "{taf_decoded_data}" taf_decoded_load',
            f'.read {SCRIPT_DIR}/copy_data.sql'
        ])
        subprocess.run(['sqlite3', '-bail', stage_db], input=sqlite_commands,
                       text=True, check=True)

        with sqlite3.connect(db_file) as connection:
            cache_schema = os.path.join(SCRIPT_DIR, 'cache_tables.sql')
            with open(cache_schema, 'r', encoding='utf-8') as schema_file:
                connection.executescript(schema_file.read())
            connection.execute('ATTACH DATABASE ? AS stage', (stage_db,))
            connection.execute(
                'INSERT OR REPLACE INTO taf_data SELECT * FROM stage.taf_data')
            connection.execute(
                'INSERT OR REPLACE INTO taf_decoded_data '
                'SELECT * FROM stage.taf_decoded_data')
            connection.executemany(
                'INSERT OR REPLACE INTO processed_sources '
                '(source, size, mtime_ns) VALUES (?, ?, ?)',
                [(source, *source_stats[source]) for source in pending_sources])
            connection.commit()
        os.remove(stage_db)

    with sqlite3.connect(db_file) as connection:
        for table in ('taf_data', 'taf_decoded_data'):
            connection.execute(
                f'DELETE FROM {table} WHERE start_date < ?',
                (start_dt.strftime('%Y-%m-%d'),))
        connection.commit()


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
    gerrity_vis, peirce_vis, cts_vis = ps.calc_scores('vis', icao, start_str,
                                                      end_str)
    gerrity_clb, peirce_clb, cts_clb = ps.calc_scores('clb', icao, start_str,
                                                      end_str)

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


def update_configs_make_dirs():
    """
    Update config files and create output directories.
    """
    # Make stats directory if necessary
    stats_dir = f'{CACHE_DIR}/stats'
    if not os.path.exists(stats_dir):
        os.makedirs(stats_dir)

    # Loop through TAF types
    for t_type in TAF_TYPES:

        # Make TAF type output directory if necessary
        t_type_dir = f'{CACHE_DIR}/{t_type}'
        if not os.path.exists(t_type_dir):
            os.makedirs(t_type_dir)

        if t_type == 'manual':
            continue

        # Define lines to write to config file
        lines = ['[defaults]\n',
                 (f'taf_connection_string = sqlite:///{CACHE_DIR}/decodes/'
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
        with open(f'{CACHE_DIR}/{t_type}.cfg', 'w',
                  encoding='utf-8') as t_file:
            t_file.writelines(lines)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Rolling TAF verification (prepare or per-station).')
    subparsers = parser.add_subparsers(dest='mode', required=True)
    subparsers.add_parser('prepare', help='Run the shared preparation step')
    station_parser = subparsers.add_parser(
        'station', help='Verify a single station')
    station_parser.add_argument('icao', help='ICAO code of the station')

    cli_args = parser.parse_args()
    if cli_args.mode == 'prepare':
        prepare()
    elif cli_args.mode == 'station':
        verify_station(cli_args.icao)
