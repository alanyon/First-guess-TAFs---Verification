from datetime import datetime, timedelta
import os
import pandas as pd
import subprocess
import pickle

import print_stats as ps
import TAFDecode_tafs as td
import driver as dv


OUT_DIR = os.environ['OUT_DIR']
DATA_DIR = os.environ['DATA_DIR']
TAF_TYPES = os.environ['TAF_TYPES'].split()
CYCLE_DATE = os.environ['CYCLE_DATE']
# Load in airport info
INFO_FILE = os.environ['INFO_FILE']
AIRPORT_INFO = pd.read_csv(INFO_FILE, header=0)


def main():

    # Remove files from previous runs
    for taf_type in TAF_TYPES:
        os.system(f'rm -f {DATA_DIR}/{taf_type}/*')
    os.system(f'rm -rf {DATA_DIR}/decodes/*')

    # Start from Feb 2026
    end_dt = datetime.strptime(CYCLE_DATE, '%Y%m%d') - timedelta(days=1)
    start_dt = end_dt - timedelta(days=90)

    # Get TAFs for 3 month period
    all_tafs = get_tafs(start_dt, end_dt)

    with open(f'{DATA_DIR}/all_tafs.pkl', 'wb') as f:
        pickle.dump(all_tafs, f)
    with open(f'{DATA_DIR}/all_tafs.pkl', 'rb') as f:
        all_tafs = pickle.load(f)

    # Decode TAFs
    decode_tafs(all_tafs)

    # Update config files for each TAF type
    update_configs_make_dirs(all_tafs)

    # Loop through airport info dataframe to get ICAOs
    for _, row in AIRPORT_INFO.iterrows():

        # try:

        # Calculate scores and add to csv file
        calc_scores(row, start_dt, end_dt)
            
        # except Exception as e:
        #     print(f"Error processing ICAO {row['icao']}: {e}")


def calc_scores(row, start_dt, end_dt):

    start_str = start_dt.strftime('%Y%m%d')
    end_str = end_dt.strftime('%Y%m%d')

    icao = row['icao']
    length = str(row['taf_len'])

    for taf_type in TAF_TYPES:

        out_dir = f'{DATA_DIR}/{taf_type}'
        out_file = f'{out_dir}/{icao}.out'
        vis_file = f'{out_dir}/{icao}_90_vis.nc'
        clb_file = f'{out_dir}/{icao}_90_clb.nc'
        config_file = f'{DATA_DIR}/{taf_type}.cfg'
        
        # Write start timestamp
        with open(out_file, "w") as f:
            f.write(datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "\n")

        # Call driver code
        with open(out_file, "a") as f:
            dv.main_from_params(start_dt=start_dt, end_dt=end_dt, 
                                sitelist=[icao], 
                                ver_period=timedelta(hours=int(length)), 
                                verpy_vis_out=vis_file, verpy_clb_out=clb_file, 
                                config_file=config_file)

        # Write end timestamp
        with open(out_file, "a") as f:
            f.write(datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "\n")

    # Calculate scores
    gerrity_vis, peirce_vis = ps.main('vis', icao, start_str, end_str)
    gerrity_clb, peirce_clb = ps.main('clb', icao, start_str, end_str)

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

    # Add to csv file or create new one if it doesn't exist
    scores_file = f'{DATA_DIR}/stats/{icao}_scores.csv'
    if os.path.exists(scores_file):
        old_scores_df = pd.read_csv(scores_file)
        scores_df = pd.concat([old_scores_df, scores_df], ignore_index=True)
    scores_df.to_csv(scores_file, index=False)


def convert_manual_tafs(txt_file, taf_dir):

    # Read lines from manual TAF file 
    with open(os.path.join(taf_dir, txt_file), 'r') as f:
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
    taf_date_str = taf_dir[-8:]
    taf_time_str = txt_file[0:2]
    taf_start = datetime.strptime(taf_date_str + taf_time_str, '%Y%m%d%H')

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

    for taf_type, tafs in all_tafs.items():

        # Make directories
        in_dir = f'{DATA_DIR}/decodes/Input_{taf_type}'
        out_dir = f'{DATA_DIR}/decodes/Output_{taf_type}'
        os.makedirs(in_dir)
        os.makedirs(out_dir)

        # Write TAFs to input file
        with open(f'{DATA_DIR}/decodes/Input_{taf_type}/tafs.txt', 'w') as f:
            f.write('\n'.join(tafs))

        # Convert TAFs to correct format and save to output directory
        with open(f'{DATA_DIR}/decodes/Output_{taf_type}/out.log', 'w') as out_f, \
             open(f'{DATA_DIR}/decodes/Output_{taf_type}/err.log', 'w') as err_f:
            td.main(in_dir, out_dir)

        # Create sql database
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
        subprocess.run(["sqlite3", db_file], input=sqlite_commands, text=True)


def get_tafs(taf_date, end_date):

    # Create dictionary to hold TAFs
    all_tafs = {taf_type: [] for taf_type in TAF_TYPES}

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
                with open(os.path.join(taf_dir, txt_file), 'r') as f:
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


def update_configs_make_dirs(all_tafs):
    """
    Update config files with new data directory.
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
        with open(f'{DATA_DIR}/{t_type}.cfg', 'w') as t_file:
            t_file.writelines(lines)


if __name__ == "__main__":
    main()