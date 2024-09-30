"""
Script to count number of TAF busts, calculate statistics and output 
plots and spreadsheets.

Written by Andre Lanyon, 11/10/2023.
"""
import copy
import csv
import itertools
import os
import sys
from copy import deepcopy
from datetime import datetime, timedelta

import icaos as ic
import matplotlib.pyplot as plt
import metdb
import numpy as np
import pandas as pd
import seaborn as sns
import useful_functions as uf
import xlsxwriter
from checking import CheckTafThread
from data_retrieval import RetrieveObservations
from dateutil.rrule import DAILY, rrule
from time_functionality import ConstructTimeObject

# Set plotting style
sns.set_style('darkgrid')
sns.set(font_scale=1.5)

# Accepted first guess TAFs
DATA_DIR = ('/data/users/alanyon/tafs/improver/verification/'
            '20230805-20240805_ml')
OLD_TAFS = f'{DATA_DIR}/decodes/Output_old/acceptedTafs.csv'
NEW_TAFS = f'{DATA_DIR}/decodes/Output_new_rf/acceptedTafs.csv'
START_DT = datetime(2023, 8, 5)
END_DT = datetime(2024, 8, 5)
DAYS = list(rrule(DAILY, interval=1, dtstart=START_DT, until=END_DT))
# For extracting from metdb
METDB_EMAIL = 'andre.lanyon@metoffice.gov.uk'
# TAF terms
TAF_TERMS = ['BECMG', 'TEMPO', 'PROB30', 'PROB40']
# To convert heading into direction label (N, S, E or W)
NUM_TO_DIR = dict(zip(range(0, 370, 10),
                      list('NNNNNEEEEEEEEESSSSSSSSSWWWWWWWWWNNNNN')))
# Wind bust types and direction strings
B_TYPES = ['increase', 'decrease', 'dir']
DIRS = ['N', 'E', 'S', 'W', 'VRB']
# String names of lists and dictionaries used to collect data
NAMES = ['wind_stats', 'vis_stats', 'cld_stats', 'old_dirs', 'new_dirs',
         'is_dirs', 'metar_dirs', 'metars_used', 'wind_info', 'vis_info', 
         'cld_info', 'all_info', 'all_stats', 'last_day']
# Dictionary mapping short weather names to long names
W_NAMES = {'vis': 'visibility', 'wind': 'wind', 'wx': 'weather',
           'cld': 'cloud', 'all': 'all'}
P_NAMES = {'vis': 'Visibility', 'wind': 'Wind', 'wx': 'Significant Weather',
           'cld': 'Cloud Base', 'all': 'All'}
# ICAOS to use
REQ_ICAOS = [b'EGAA ', b'EGAC ', b'EGCC ', b'EGFF ', b'EGHH ',
             b'EGGD ', b'EGGP ', b'EGKK ', b'EGLL ', b'EGNJ ', b'EGNT ', 
             b'EGNX ', b'EGPD ', b'EGPE ', b'EGPF ', b'EGPH ', b'EGPO ', 
             b'EGSS ', b'EGNH ', b'EGNM ', b'EGNV ', b'EGSY ', b'EGBB ',
             b'EGHI ', b'EGNC ', b'EGNR ', b'EGTE ']
REQ_ICAO_STRS = {'EGAA': 'Belfast International', 'EGAC': 'Belfast City', 
                 'EGCC': 'Manchester', 'EGHH': 'Bournemouth', 'EGTE': 'Exeter',
                 'EGFF': 'Cardiff', 'EGBB': 'Birmingham',
                 'EGGD': 'Bristol', 'EGGP': 'Liverpool', 'EGKK': 'Gatwick', 
                 'EGLL': 'Heathrow', 'EGNJ': 'Humberside', 'EGNT': 'Newcastle', 
                 'EGNX': 'East Midlands', 'EGPD': 'Aberdeen', 
                 'EGPE': 'Inverness', 'EGPF': 'Glasgow', 'EGPH': 'Edinburgh', 
                 'EGPO': 'Stornoway', 'EGSS': 'Stansted', 'EGNH': 'Blackpool',
                 'EGNM': 'Leeds', 'EGNV': 'Teeside', 'EGSY': 'St Athan',
                 'EGHI': 'Southampton', 'EGNC': 'Carlisle', 'EGNR': 'Hawarden'}
# REQ_ICAOS = [b'EGLL ']
# REQ_ICAO_STRS = {'EGLL': 'Heathrow'}

# TAF type names and abbrieviations
TAF_TYPES = {'new': 'New', 'old': 'Old', 'is': 'Issued'}


def main(load_data):
    """
    Extracts TAFs and METARs and compares them, collecting bust 
    information.
    """
    # Start with empty lists/dictionaries if new data needed
    if load_data == 'yes':

        # Lists/dictionaries to collect TAFs and bust verification info
        wind_info = {icao: [] for icao in REQ_ICAO_STRS}
        vis_info = {icao: [] for icao in REQ_ICAO_STRS}
        cld_info = {icao: [] for icao in REQ_ICAO_STRS}
        all_info = {icao: [] for icao in REQ_ICAO_STRS}
        wind_stats_temp = {'old increase': 0, 'old decrease': 0, 'old dir': 0,
                           'old all': 0, 'new increase': 0, 'new decrease': 0, 
                           'new dir': 0, 'new all': 0, 'is increase': 0, 
                           'is decrease': 0, 'is dir': 0, 'is all': 0}
        stats_temp = {'old increase': 0, 'old decrease': 0, 'old both': 0,
                      'old all': 0, 'new increase': 0, 'new decrease': 0, 
                      'new both': 0, 'new all': 0, 'is increase': 0, 
                      'is decrease': 0, 'is both': 0, 'is all': 0}
        dirs_temp = {'N': 0, 'E': 0, 'S': 0, 'W': 0, 'VRB': 0}
        metars_used = {icao: 0 for icao in REQ_ICAO_STRS}
        metar_dirs = {icao: dirs_temp.copy() for icao in REQ_ICAO_STRS}
        old_dirs = {icao: {'increase': dirs_temp.copy(),
                           'decrease': dirs_temp.copy(),
                           'dir': dirs_temp.copy()}
                    for icao in REQ_ICAO_STRS}
        new_dirs = old_dirs.copy()
        is_dirs = old_dirs.copy()
        all_stats_temp = {'old wind': 0, 'old vis': 0, 'old wx': 0, 
                          'old cld': 0, 'old all': 0, 'new wind': 0, 
                          'new vis': 0, 'new wx': 0, 'new cld': 0, 
                          'new all': 0, 'is wind': 0, 'is vis': 0, 
                          'is wx': 0, 'is cld': 0, 'is all': 0}
        wind_stats = {icao: wind_stats_temp.copy() for icao in REQ_ICAO_STRS}
        vis_stats = {icao: stats_temp.copy() for icao in REQ_ICAO_STRS}
        cld_stats = {icao: stats_temp.copy() for icao in REQ_ICAO_STRS}
        all_stats = {icao: all_stats_temp.copy() for icao in REQ_ICAO_STRS}
        last_day = DAYS[0]

    # Otherwise, load pickled files
    else:
        (wind_stats, vis_stats, cld_stats,
         old_dirs, new_dirs, is_dirs, metar_dirs, metars_used,
         wind_info, vis_info, cld_info, all_info, all_stats, last_taf) = [
                uf.unpickle_data(f'{DATA_DIR}/pickles/{name}') 
                for name in NAMES
                ]

    # If either starting from scratch or picking up from loaded files, add
    # more data
    if load_data != 'no':

        # Loop though all days in period
        for day in DAYS:

            # Read in first guess TAFs file without machine learning
            with open(OLD_TAFS, 'r') as old_tafs_file:
                old_tafs_lines = old_tafs_file.readlines()

            # Determine if any TAFs in file issued on this day
            day_taf_found = False
            for o_row in old_tafs_lines:

                # Split row by ','
                o_row = o_row.split(',')

                # Get issue dt of TAF
                old_idt = datetime.strptime(o_row[10][2:16], '%H%MZ %d/%m/%y')

                if (old_idt - timedelta(hours=1)).date() == day.date():
                    print(old_idt, day)
                    day_taf_found = True
                    break

            # Move to next day if no TAFs found
            if not day_taf_found:
                continue

            # Get all TAFs and METARs for day (3 days for METARs to 
            # cover TAF periods)
            try:
                day_tafs, day_3_metars = get_day_tafs_metars(day)
            except:
                print(f'problem retrieving for day: {day}')
                continue

            # Loop through each old TAF and attempt to find equivalent new TAF
            for o_row in old_tafs_lines:

                # Split row by ','
                o_row = o_row.split(',')

                # Get issue dt of TAF
                old_idt = datetime.strptime(o_row[10][2:16], '%H%MZ %d/%m/%y')

                # if not correct day, move to next TAF
                if (old_idt - timedelta(hours=1)).date() != day.date():
                    continue

                # Get other required old TAF variables
                old_vdt = (datetime.strptime(o_row[4], '%d-%b-%y') +
                           timedelta(hours=int(o_row[5][:2])))
                old_taf = o_row[10][46:].split()
                old_icao = old_taf[0]

                # Read in first guess TAFs file with machine learning
                with open(NEW_TAFS, 'r') as new_tafs_file:
                    new_tafs_lines = new_tafs_file.readlines()

                # Find equivalent new TAF
                for n_row in new_tafs_lines:

                    # Split row by ','
                    n_row = n_row.split(',')

                    # Get required new TAF variables
                    new_vdt = (datetime.strptime(n_row[4], '%d-%b-%y') +
                               timedelta(hours=int(n_row[5][:2])))
                    new_taf = n_row[10][46:].split()
                    new_icao = new_taf[0]

                    # Continue to next iteration if wrong validity time or icao
                    if old_icao != new_icao or old_vdt != new_vdt:
                        continue

                    # Now icaos and vds must be the same
                    icao = old_icao
                    vdt = old_vdt
                    vday = vdt.date()

                    # Only need info for required ICAOs
                    if icao not in REQ_ICAO_STRS:
                        continue

                    # Get TAF validity times as python datetime objects
                    old_start, old_end = ConstructTimeObject(
                        old_taf[2], int(old_taf[2][:2]), vdt.month,
                        vdt.year).TAF()

                    # Number of METARs to expect during TAF period
                    num_float = (old_end - old_start).total_seconds() / 1800
                    num_metars = int(np.round(num_float))

                    # Look for TAFs/METARs a bit before start of TAF to 
                    # capture those issued early
                    start_time = old_start - timedelta(hours=2)
                    end_time = old_start + timedelta(hours=2)

                    # Print for info of progress
                    print(icao, start_time, end_time)

                    # Find TAF with correct timings (if no
                    # issued TAFs found, don't verify either TAF)
                    for is_taf in day_tafs[icao]:

                        # Move on to next TAF if no record or cancelled
                        if is_taf == "NoRecord" or 'CNL' in is_taf:
                            continue

                        # Check first and last hours match
                        if is_taf[2] != old_taf[2]:
                            continue

                        # Check last day matches (can be errors in 
                        # issued TAF)
                        if int(is_taf[2][5:7]) != int(old_taf[2][5:7]):
                            continue

                        # Get TAF validity time as python datetime 
                        # objects (assumes month and year same as fg TAF 
                        is_start, is_end = ConstructTimeObject(
                            is_taf[2], int(is_taf[2][:2]), vdt.month,
                            vdt.year).TAF()

                        # Move to next iteration if times don't match
                        if old_start != is_start or old_end != is_end:
                            continue

                        # Now start and end times must be the same
                        start, end = old_start, old_end

                        # Verify TAFs against METARs
                        metars = day_3_metars[icao]
                        try:
                            old_busts = CheckTafThread(icao, start, end,
                                                      old_taf, metars).run()
                            new_busts = CheckTafThread(icao, start, end,
                                                       new_taf, metars).run()   
                            is_busts = CheckTafThread(icao, start, end,
                                                      is_taf, metars).run()

                        # If any issues, move to next iteration
                        except:
                            print('Bad TAF old', old_taf)
                            print('Bad TAF new', new_taf)
                            print('Bad TAF is', is_taf)
                            print('')
                            continue

                        # Get list of METARs used for all TAF types
                        m_old = old_busts['metars_used']
                        m_new = new_busts['metars_used']
                        m_is = is_busts['metars_used']
                        metars_both = [metar for metar in m_old 
                                       if metar in m_new and metar in m_is]

                        # Update METAR wind directions dictionary
                        metar_dirs = update_metar_dirs(icao, metars_both, 
                                                       metar_dirs)

                        # Add to METARS used count
                        metars_used[icao] += num_metars

                        # Add to wind stats
                        wind_stats, old_dirs = add_stats(
                            wind_stats, icao, old_busts['wind'], 'old', 'wind', 
                            one_wx='wind', dirs_dict=old_dirs
                        )
                        wind_stats, new_dirs = add_stats(
                            wind_stats, icao, new_busts['wind'], 'new', 'wind', 
                            one_wx='wind', dirs_dict=new_dirs
                        )
                        wind_stats, is_dirs = add_stats(
                            wind_stats, icao, is_busts['wind'], 'is', 'wind', 
                            one_wx='wind', dirs_dict=is_dirs)

                        # Add to wind, vis and cld stats
                        vc_busts = {'old': old_busts, 'new': new_busts, 
                                    'is': is_busts}
                        for t_type in vc_busts:
                            vis_stats =  add_stats(
                                vis_stats, icao, 
                                vc_busts[t_type]['visibility'], t_type, 'vis', 
                                one_wx='vis')
                            cld_stats =  add_stats(
                                cld_stats, icao, vc_busts[t_type]['cloud'],
                                t_type, 'cld', one_wx='cld')

                        # Add to other stats dictionaries
                        for w_type, w_lng in W_NAMES.items():
                            all_stats = add_stats(
                                all_stats, icao, old_busts[w_lng], 'old', 
                                w_type
                            )
                            all_stats = add_stats(
                                all_stats, icao, new_busts[w_lng], 'new', 
                                w_type
                            )
                            all_stats = add_stats(
                                all_stats, icao, is_busts[w_lng], 'is', 
                                w_type
                            )

                        # Add to info dictionaries
                        info_dicts = [wind_info, vis_info, cld_info, all_info]
                        info_w_types = ['wind', 'vis', 'cld', 'all']
                        for info_dict, w_type in zip(info_dicts, info_w_types):
                            w_lng = W_NAMES[w_type]

                            # Don't bother appending info if no busts
                            if (not old_busts[w_lng] and not new_busts 
                                and not is_busts[w_lng]):
                                continue

                            # Otherwise, append info
                            info_dict[icao].append([old_taf, old_busts[w_lng],
                                                    new_taf, new_busts[w_lng],
                                                    is_taf, is_busts[w_lng]])

                        # Break for loop so only one TAF is used
                        break

            # Pickle at the end of each day
            uf.pickle_data(wind_stats, f'{DATA_DIR}/pickles/wind_stats')
            uf.pickle_data(vis_stats, f'{DATA_DIR}/pickles/vis_stats')
            uf.pickle_data(cld_stats, f'{DATA_DIR}/pickles/cld_stats')
            uf.pickle_data(old_dirs, f'{DATA_DIR}/pickles/old_dirs')
            uf.pickle_data(new_dirs, f'{DATA_DIR}/pickles/new_dirs')
            uf.pickle_data(is_dirs, f'{DATA_DIR}/pickles/is_dirs')
            uf.pickle_data(metar_dirs, f'{DATA_DIR}/pickles/metar_dirs')
            uf.pickle_data(metars_used, f'{DATA_DIR}/pickles/metars_used')
            uf.pickle_data(wind_info, f'{DATA_DIR}/pickles/wind_info')
            uf.pickle_data(vis_info, f'{DATA_DIR}/pickles/vis_info')
            uf.pickle_data(cld_info, f'{DATA_DIR}/pickles/cld_info')
            uf.pickle_data(all_info, f'{DATA_DIR}/pickles/all_info')
            uf.pickle_data(all_stats, f'{DATA_DIR}/pickles/all_stats')
            uf.pickle_data(day, f'{DATA_DIR}/pickles/last_day')

    # Get wx stats
    wx_stats = get_wx_stats(all_info)

    # Create spreadsheets
    # write_to_excel(wind_info, wind_stats, 'wind')
    # write_to_excel(all_info, all_stats, 'all')

    # Make plots
    # plot_all(all_stats, metars_used, all_info, 'old', 'new')
    # plot_all(all_stats, metars_used, all_info, 'new', 'is')
    # plot_all(all_stats, metars_used, all_info, 'old', 'is')
    summary_stats = {'Bust Type': [], 'TAF Type': [], 'Number of Busts': []}
    summary_stats = plot_param(vis_stats, 'vis', summary_stats)
    summary_stats = plot_param(cld_stats, 'cld', summary_stats)
    summary_stats = plot_param(wind_stats, 'wind', summary_stats)
    summary_stats = plot_param(wx_stats, 'wx', summary_stats)
    plot_summary(summary_stats)


def get_day_tafs_metars(day):
    """
    Extracts from metdb all TAFs for required ICAOs for specified day
    and all METARs for required ICAOs for specified day and 2 following 
    days (to cover all valid times covered by TAFs).
    """
    # Get all TAFs for day
    all_tafs = metdb.obs(
        METDB_EMAIL, 'TAFS',
        keywords=[f'PLATFORM EG',
                  f'START TIME {day.strftime("%Y%m%d/0000")}Z',
                  f'END TIME {day.strftime("%Y%m%d/2359")}Z'],
        elements=['ICAO_ID', 'TAF_RPT_TXT']
    )

    # Get METARs for all possible times TAFs cover (3 days)
    all_metars = [metdb.obs(
        METDB_EMAIL, 'METARS',
        keywords=[
            f'PLATFORM EG',
            f'START TIME {(day + timedelta(days=ind)).strftime("%Y%m%d/0000")}Z',
            f'END TIME {(day + timedelta(days=ind)).strftime("%Y%m%d/2359")}Z'
        ],
        elements=['ICAO_ID', 'MTR_RPT_TXT']
    )
    for ind in range(3)
    ]

    # Get SPECIs for all possible times TAFs cover
    all_specis = [metdb.obs(
        METDB_EMAIL, 'SPECI',
        keywords=[
            f'PLATFORM EG',
            f'START TIME {(day + timedelta(days=ind)).strftime("%Y%m%d/0000")}Z',
            f'END TIME {(day + timedelta(days=ind)).strftime("%Y%m%d/2359")}Z'
        ],
        elements=['ICAO_ID', 'MTR_RPT_TXT']
    )
    for ind in range(3)
    ]

    # Get TAFs/METARs for each required ICAO and store in dictionaries
    day_tafs, day_3_metars = {}, {}
    for icao in REQ_ICAOS:

        # Get TAFs for ICAO 
        icao_tafs = all_tafs[all_tafs['ICAO_ID'] == icao]
        icao_tafs = [str(taf['TAF_RPT_TXT'], 'utf-8').strip().split()[8:] 
                     for taf in icao_tafs]

        # Add to TAFs dictionary
        day_tafs[str(icao, 'utf-8').strip()] = icao_tafs

        # Get METARs for ICAO
        icao_metars = []
        for metars in all_metars:
            i_metars = metars[metars['ICAO_ID'] == icao]
            i_metars = [str(metar['MTR_RPT_TXT'], 'utf-8').strip().split()[8:] 
                        for metar in i_metars]
            icao_metars = icao_metars + i_metars

        # Get SPECIs for ICAO
        icao_specis = []
        for specis in all_specis:
            i_specis = specis[specis['ICAO_ID'] == icao]
            i_specis = [str(speci['MTR_RPT_TXT'], 'utf-8').strip().split()[8:] 
                        for speci in i_specis]
            icao_specis = icao_specis + i_specis

        # Combine SPECIs and METARs
        icao_metars = icao_metars + icao_specis

        # Remove METARs and SPECIs recorded as 'NoRecord'
        icao_metars = [metar for metar in icao_metars if metar != "NoRecord"]

        # Remove duplicates (e.g. for METARs with trends)
        new_icao_metars = []
        for ind, metar in enumerate(icao_metars):
            if ind == 0 or metar[1] == current_metar[1]:
                current_metar = metar
            else:
                new_icao_metars.append(current_metar)
                current_metar = metar
            if ind == len(metars) - 1:
                new_icao_metars.append(current_metar)

        # Remove AUTO term from METARs and SPECIs as it has no value
        new_icao_metars = [[ele for ele in metar if ele != 'AUTO']
                            for metar in new_icao_metars]

        # Sort list so SPECIs in time order with METARs
        new_icao_metars.sort(key=lambda x: x[1])

        # Add to METARs dictionary
        day_3_metars[str(icao, 'utf-8').strip()] = new_icao_metars

    return day_tafs, day_3_metars


def get_wx_stats(all_info):

    # Dictionary with default zero values
    wx_stats = {icao: {'old all': 0, 'new all': 0, 'is all': 0} 
                for icao in all_info}

    # Loop through icaos in all_info dictionary
    for icao in all_info:

        # Loop through all TAFs for that icao
        for taf_list in all_info[icao]:

            # Unpack list
            old_taf, old_busts, new_taf, new_busts, is_taf, is_busts = taf_list

            # Add to bust counts if any weather busts
            for old_bust in old_busts:
                if 'weather' in old_bust[0]:
                    wx_stats[icao]['old all'] += 1
            for new_bust in new_busts:
                if 'weather' in new_bust[0]:
                    wx_stats[icao]['new all'] += 1
            for is_bust in is_busts:
                if 'weather' in is_bust[0]:
                    wx_stats[icao]['is all'] += 1

    return wx_stats


def plot_dirs(old_dirs, new_dirs, is_dirs, metar_dirs):
    """
    Plots bar charts showing bust information for each TAF, separating busts
    by METAR wind direction.
    """
    # Convert raw numbers of busts to percentages of total METARs
    old_percs = get_dir_percs(copy.deepcopy(old_dirs), metar_dirs)
    new_percs = get_dir_percs(copy.deepcopy(new_dirs), metar_dirs)
    is_percs = get_dir_percs(copy.deepcopy(is_dirs), metar_dirs)

    # Make plots for each ICAO if any busts
    for icao in old_percs:

        # Don't make plots if no busts found
        if all(old_percs[icao][b_type][dir] == 0
               for b_type, dir in itertools.product(B_TYPES, DIRS)):
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
        fig.savefig(f'{PLOT_DIR}/dir_busts_{icao}.png')
        plt.close()


def get_dir_percs(taf_dirs, metar_dirs):
    """
    Divides numbers of wind busts for each type and each direction by number
    of METARs observing wind in that direction, to get perentage of busts
    when wind is observed in each direction.
    """
    for icao, b_type, w_dir in itertools.product(taf_dirs, B_TYPES, DIRS):
        if taf_dirs[icao][b_type][w_dir] != 0:
            taf_dirs[icao][b_type][w_dir] /= (0.01 * metar_dirs[icao][w_dir])

    return taf_dirs


def plot_all(stats_abs, metars, info, t_type_1, t_type_2):
    """
    Plots bar chart showing all bust information.
    """
    # Get TAF type full names
    taf_type_1 = TAF_TYPES[t_type_1]
    taf_type_2 = TAF_TYPES[t_type_2]

    # Convert absolute numbers to percentages of all METARs
    stats_perc = get_stats_percs(stats_abs, metars)
    
    # Make plots for absolute numbers, as well as percentages
    for s_type, stats in zip(['', '_perc'], [stats_abs, stats_perc]):

        # Dictionary to add stats to
        stats_dict = {'Airport': [], 'Type of Bust': [], 'Stat': []}

        # Loop through all ICAOs
        for icao in stats:

            # Ignore those with no TAFs
            if not info[icao]:
                continue

            # Get stats from dictionary and append to stats dictionary
            for bust_type in ['wind', 'vis', 'cld', 'wx']:
                stats_dict['Airport'].append(REQ_ICAO_STRS[icao])
                stats_dict['Type of Bust'].append(P_NAMES[bust_type])
                bust_stat = (stats[icao][f'{t_type_1} {bust_type}'] 
                             - stats[icao][f'{t_type_2} {bust_type}'])
                stats_dict['Stat'].append(bust_stat)

        # Create figure and axis
        fig, ax = plt.subplots(figsize=(12, 10))

        # Create bar plot
        stats_df = pd.DataFrame(stats_dict)
        bar = sns.barplot(stats_df, x='Stat', y='Airport', hue='Type of Bust')

        # Formatting, etc
        bar.set(ylabel=None)
        y_locs = ax.get_yticks()
        for ind, x_loc in enumerate(y_locs):
            if ind == 0:
                ax.axhline(x_loc - 0.5, color='k', linestyle='-', linewidth=1,
                           alpha=0.3)
            ax.axhline(x_loc + 0.5, color='k', linestyle='-', linewidth=1,
                       alpha=0.3)
        ax.axvline(0, color='k', linestyle='--')
        ax.tick_params(axis='x', length=0)
        if s_type == '_perc':
            lab = f'{taf_type_1} TAF busts % - {taf_type_2} TAF busts %'
        else:
            lab = f'{taf_type_1} TAF busts - {taf_type_2} TAF busts'
        ax.set_xlabel(lab, fontsize=15, weight='bold')
        ax.tick_params(axis='x', labelsize=15)
        sns.move_legend(ax, "upper left", bbox_to_anchor=(1, 1))
        plt.setp(bar.get_legend().get_title(), weight='bold')

        # Save and close figure
        plt.tight_layout()
        img_fname = (f'{DATA_DIR}/ml_plots/'
                     f'{t_type_1}_{t_type_2}_all_busts{s_type}.png')
        fig.savefig(img_fname)
        plt.close()


def plot_param(stats_abs, param, summary_stats):
    """
    Plots parameter-specific bar chart showing bust information.
    """
    # Titles, etc, for creating stats dataframes
    if param == 'wind':
        bust_types = [f'Observed {W_NAMES[param]} higher', 
                      f'Observed {W_NAMES[param]} lower', 
                      f'Difference in {W_NAMES[param]} direction'] * 3
        taf_types = (['Old First Guess TAFs'] * 3 
                     + ['New First Guess TAFs'] * 3 
                     + ['Manual TAFs'] * 3)
        bust_keys = ['old increase', 'old decrease', 'old dir', 'new increase', 
                     'new decrease', 'new dir', 'is increase', 'is decrease', 
                     'is dir']
    elif param == 'wx':
        bust_types = [f'Difference in significant {W_NAMES[param]}'] * 3
        taf_types = ['Old First Guess TAFs', 'New First Guess TAFs', 
                     'Manual TAFs']
        bust_keys = ['old all', 'new all', 'is all']
    else:
        bust_types = [f'Observed {W_NAMES[param]} higher', 
                      f'Observed {W_NAMES[param]} lower'] * 3
        taf_types = (['Old First Guess TAFs'] * 2 
                     + ['New First Guess TAFs'] * 2 + ['Manual TAFs'] * 2)
        bust_keys = ['old increase', 'old decrease', 'new increase', 
                     'new decrease', 'is increase', 'is decrease']

    # Add to summary_stats with number of busts to be updated in 
    # following for loop
    summary_stats['Bust Type'].extend(bust_types)
    summary_stats['TAF Type'].extend(taf_types)
    total_busts = [0 for _ in bust_types]

    # Loop through all icaos
    for icao in stats_abs:

        # Make directory if needed
        if not os.path.exists(f'{DATA_DIR}/ml_plots/{icao}'):
            os.makedirs(f'{DATA_DIR}/ml_plots/{icao}')

        # Get stats for airport
        stats = stats_abs[icao]

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
        img_fname = f'{DATA_DIR}/ml_plots/{icao}/{param}_busts.png'
        plt.tight_layout()
        fig.savefig(img_fname)
        plt.close()

    # Add to bust numbers in summary_stats
    summary_stats['Number of Busts'].extend(total_busts)

    return summary_stats


def plot_summary(summary_stats):

    """
    Plots summary bar chart showing bust information.
    """
    # Create bar plot
    fig, ax = plt.subplots(figsize=(14, 10))
    bar = sns.barplot(data=summary_stats, x='Number of Busts', y='Bust Type', 
                      hue='TAF Type')

    # Add scores on top of bars
    for ind in ax.containers:
        ax.bar_label(ind, fontsize=14)

    # Format axes, etc
    ax.legend(loc='upper left', bbox_to_anchor=(1, 0.9))
    ax.set_xlabel('Number of Busts', weight='bold')
    ax.set_ylabel('Bust Type', weight='bold')

    # Save and close figure
    plt.tight_layout()
    fig.savefig(f'{DATA_DIR}/ml_plots/summary_busts.png')
    plt.close()


def get_stats_percs(stats, metars):

    stats_perc = deepcopy(stats)
    for icao, i_stats in stats.items():
        for b_type, i_stat in i_stats.items():
            if metars[icao] != 0:
                stats_perc[icao][b_type] = i_stat / (0.01 * metars[icao])

    return stats_perc


def write_to_excel(info, stats, w_type):
    """
    Writes verification info to Excel file
    """
    # Open Excel workbook
    fname = f'{w_type}_vers.xlsx'
    workbook = xlsxwriter.Workbook(fname)

    # Create separate worksheet for each ICAO
    for icao in info:

        # Move to next iteration if no data
        if not info[icao]:
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
        worksheet.write(row_num, 0, f'{t_str} Busts for {ic.icao_dict[icao]}',
                        big_bold)
        row_num += 2

        # Get ICAO stats
        i_stats = stats[icao]

        # Headers
        worksheet.write(row_num, 0, 'Old First Guess TAFs Statistics', 
                        big_bold)
        worksheet.write(row_num, 12, 'New First Guess TAFs Statistcs', 
                        big_bold)
        worksheet.write(row_num, 24, 'Manual TAFs Statistcs', big_bold)

        # Write stats to spreadsheet
        for msg, key in zip(msgs, keys):
            row_num = write_stats(worksheet, bold, i_stats, msg, key, row_num)
        row_num += 2

        # Loop through all TAFs
        for item in info[icao]:

            # Unpack list
            old_taf, old_ver, new_taf, new_ver, is_taf, is_ver = item

            # Headers
            worksheet.write(row_num, 0, 'Old First Guess TAF', big_bold)
            worksheet.write(row_num, 12, 'New First Guess TAF', big_bold)
            worksheet.write(row_num, 24, 'Manual TAF', big_bold)
            row_num += 1

            # Add line breaks to TAFs and change to strings
            old_str, old_lines = taf_str(old_taf)
            new_str, new_lines = taf_str(new_taf)
            is_str, is_lines = taf_str(is_taf)

            # Write TAFs to spreadsheet
            worksheet.merge_range(row_num, 0, row_num + old_lines, 6, old_str,
                                  taf_format)
            worksheet.merge_range(row_num, 12, row_num + new_lines, 18, 
                                  new_str, taf_format)
            worksheet.merge_range(row_num, 24, row_num + is_lines, 30,
                                  is_str, taf_format)

            # Add to row number
            row_num += max([old_lines, new_lines, is_lines]) + 2

            # Busts header
            worksheet.write(row_num, 0, 'TAF Busts', big_bold)
            worksheet.write(row_num, 12, 'TAF Busts', big_bold)

            # Add to row number
            row_num += 1

            # Write in METARs
            if w_type == 'wind':
                old_lines = mets_wind(old_ver, worksheet, workbook, row_num, 0)
                new_lines = mets_wind(new_ver, worksheet, workbook, row_num, 12)
                is_lines = mets_wind(is_ver, worksheet, workbook, row_num, 24)
            else:
                old_lines = mets_all(old_ver, worksheet, workbook, row_num, 0)
                new_lines = mets_all(new_ver, worksheet, workbook, row_num, 12)
                is_lines = mets_all(is_ver, worksheet, workbook, row_num, 24)

            # Add to row number
            row_num += max([old_lines, new_lines, is_lines]) + 1

    # Close workbook
    workbook.close()

    # Copy Excel file to spreadsheets directory
    os.system(f'mv {fname} {DATA_DIR}/ml_plots')


def write_stats(worksheet, fmt, stats_dict, msg, key_stat, r_num):
    """
    Writes stats to spreadsheet, returning row number.
    """
    r_num += 1
    old_stat = stats_dict[f'old {key_stat}']
    old_str = f'{msg} busts: {old_stat}'
    worksheet.write(r_num, 0, old_str, fmt)
    new_stat = stats_dict[f'new {key_stat}']
    new_str = f'{msg} busts: {new_stat}'
    worksheet.write(r_num, 12, new_str, fmt)
    is_stat = stats_dict[f'is {key_stat}']
    is_str = f'{msg} busts: {is_stat}'
    worksheet.write(r_num, 24, is_str, fmt)

    return r_num


def mets_all(ver_lst, worksheet, workbook, m_row_num, col):
    """
    Writes METAR to spreadsheet in appropriate format with message containing
    bust information.
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


def taf_str(taf_lst):
    """
    Converts TAF in list format to and easily readable string.
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


def add_stats(stats, icao, ver, t_type, w_type, one_wx='', dirs_dict=False):
    """
    Adds bust stats to appropriate lists in dictionaries.
    """

    if ver:
        for item in ver:

            # For single type of weather stats
            if one_wx:
                stats[icao][f'{t_type} all'] += 1
                busts = item[0]
                metar = item[1]

            # For wind stats
            if one_wx == 'wind':

                # Get METAR direction
                w_dir = metar[2][:3]
                if w_dir.isnumeric() and int(w_dir) in NUM_TO_DIR:
                    dir_lab = NUM_TO_DIR[int(w_dir)]
                elif w_dir == 'VRB':
                    dir_lab = 'VRB'
                else:
                    dir_lab = False

                # Add to stats dictionaries
                if busts['mean increase'] or busts['gust increase']:
                    stats[icao][f'{t_type} increase'] += 1
                    if dir_lab:
                        dirs_dict[icao]['increase'][dir_lab] += 1
                if busts['mean decrease']:
                    stats[icao][f'{t_type} decrease'] += 1
                    if dir_lab:
                        dirs_dict[icao]['decrease'][dir_lab] += 1
                if busts['dir']:
                    stats[icao][f'{t_type} dir'] += 1
                    if dir_lab:
                        dirs_dict[icao]['dir'][dir_lab] += 1

            # For cld and vis stats
            elif one_wx in ['cld', 'vis']:
                stats[icao][f'{t_type} {busts}'] += 1

            # For summary of all busts stats
            else:
                stats[icao][f'{t_type} {w_type}'] += 1

    if one_wx == 'wind':
        return stats, dirs_dict

    return stats


def update_metar_dirs(icao, metars, dirs):

    # Get wind direction from METAR
    for metar in metars:
        w_dir = metar[2][:3]
        if w_dir.isnumeric() and int(w_dir) in NUM_TO_DIR:
            dir_lab = NUM_TO_DIR[int(w_dir)]
        elif w_dir == 'VRB':
            dir_lab = 'VRB'
        else:
            print('Problem with direction', metar)
            continue

        # Update direction count dictionary
        dirs[icao][dir_lab] += 1

    return dirs


if __name__ == "__main__":

    # Print time
    time_1 = uf.print_time('started')

    # Get user defined indication for whether new data is needed
    new_data = sys.argv[1]
    # new_tafs = sys.argv[2]

    # Run main function
    main(new_data)

    # Print time
    time_2 = uf.print_time('Finished')

    # Print time taken
    uf.time_taken(time_1, time_2, unit='seconds')
