"""
Creates scatter plots comaparing TAF verification scores.
"""
import csv
import math
import os
import sys
from datetime import datetime
from itertools import cycle, islice
import seaborn as sns

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# Set plotting style
sns.set_style('darkgrid')
sns.set(font_scale=1.5)

# Import environment variables
STATS_DIR = os.environ['STATS_DIR']
COMBS = os.environ['COMBS'].split()
ALL_TAFS = os.environ['ALL_TAFS'].split()
TAF_30HR = os.environ['TAF_30HR'].split()
TAF_24HR = os.environ['TAF_24HR'].split()
TAF_9HR = os.environ['TAF_9HR'].split()
START = os.environ['VERIF_START']
END = os.environ['VERIF_END']

# Define other constants
PARAMS = {'vis': 'Visibility', 'clb': 'Cloud base'}
TAF_TYPES = {'bd': 'BestData', 'im': 'IMPROVER', 'is': 'Manual'}
NUM_CATS = {'vis': 6, 'clb': 5}
SCORES = {'g': 'Gerrity', 'sp': 'Peirce', 'bp': 'Peirce'}
TARGETS = {'clb_9': 0.517, 'clb_24': 0.468, 'clb_30': 0.457, 'vis_9': 0.426,
           'vis_24': 0.345, 'vis_30': 0.366}
MARKERS = ['o', 'v', 'P', 'X', 's', 'p', '*', 'D']
SIZES = [50, 50, 60, 50, 50, 60, 80, 40]
ICAO_DICT = {
    'EGAA': 'Belfast International', 'EGAC': 'Belfast City', 
    'EGBB': 'Birmingham', 'EGCC': 'Manchester', 'EGCN': 'Doncaster', 
    'EGFF': 'Cardiff', 'EGGD': 'Bristol', 'EGGP': 'Liverpool',
    'EGKK': 'Gatwick', 'EGLL': 'Heathrow', 'EGNJ': 'Humberside', 
    'EGNT': 'Newcastle', 'EGNX': 'East Midlands', 'EGPD': 'Aberdeen', 
    'EGPE': 'Inverness', 'EGPF': 'Glasgow', 'EGPH': 'Edinburgh', 
    'EGPO': 'Stornoway', 'EGSS': 'Stansted', 'EGHH': 'Bournemouth',
    'EGNH': 'Blackpool', 'EGNM': 'Leeds', 'EGNV': 'Teeside',
    'EGHI': 'Southampton', 'EGNC': 'Carlisle', 'EGNR': 'Hawarden',
    'EGSY': 'St Athan', 'EGTE': 'Exeter'
}


def main(req_obs, unc):
    """
    Creates plots comparing verification scores from manually produced
    TAFs to those of first guess TAFs
    """
    # Make directories if needed
    for p_dir in ['rl_plots', 'scatter_plots']:
        if not os.path.exists(f'{STATS_DIR}/{p_dir}'):
            os.makedirs(f'{STATS_DIR}/{p_dir}')

    # Get random set of colours to assign to the airports
    color_dict = get_color_dict()

    # For collecting all stats
    all_stats = {}

    # Get stats from csv files
    for param in PARAMS:
        
        # Empty lists to append stats to
        stats_dict = get_stats(param, unc, req_obs)

        rel_freq_plot(param, stats_dict)

        all_stats[param] = stats_dict

        # Make plots for all combinations of TAF types
        for comb in COMBS:

            # Scatter plots showing Gerrity and Peirce scores for all airports
            make_plot(param, color_dict, stats_dict, 'g', unc, comb)
            make_plot(param, color_dict, stats_dict, 'bp', unc, comb)
            make_plot(param, color_dict, stats_dict, 'sp', unc, comb,
                      cat='all')

            # Make scatter plot showing TAF length specific Gerrity scores
            for length in [9, 24, 30]:
                make_plot(param, color_dict, stats_dict, 'g', unc, comb,
                          length=length)

            # Make scatter plots showing Peirce scores
            for cat in range(1, NUM_CATS[param] + 1):
                make_plot(param, color_dict, stats_dict, 'sp', unc, comb,
                          cat=cat)


def get_stats(param, unc, req_obs):
    """
    Collects stats from a csv file.
    """
    # Define stats file
    stats_file = f'{STATS_DIR}/{param}_stats{unc}.csv'

    # Dictionary to add stats to
    stats_dict = {}

    # Open csv file
    with open(stats_file, encoding='utf-8') as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=',')

        # Collect appropriate stats from each row
        for row in csv_reader:

            # Check if TAF in list of good TAFs
            if row[0] not in ALL_TAFS:
                continue

            # Get first part of key to add to dictionary depending on TAF type
            if row[2] == 'BestData':
                f_key = 'bd'
            elif row[2] == 'Improver':
                f_key = 'im'
            elif row[2] == 'Operational':
                f_key = 'is'

            # Add airport to stats dictionary if necessary
            if row[0] not in stats_dict:
                stats_dict[row[0]] = {}

            # Look for Gerrity skill scores and add to dictionary if found
            if row[1] == 'gerrity':
                stats_dict = add_gerrity(stats_dict, row, f_key)

            # Look for Peirce skill scores and add to dictionary if found
            elif row[1] == 'big_peirce':
                stats_dict = add_big_peirce(stats_dict, row, f_key)

            # Look for Peirce skill scores and add to dictionary if found
            elif row[1] == 'peirce':
                stats_dict = add_small_peirce(stats_dict, row, f_key)

            # Look for relative frequencies and add to dictionary if found
            elif row[1] == 'freqs':
                stats_dict = add_freqs(stats_dict, row, f_key, NUM_CATS[param])

            # Look for contingency table values and add to dictionary if found
            elif row[1] == 'ctvals':
                stats_dict = add_cts(stats_dict, row, f_key, NUM_CATS[param])
            
                # Check that airport has sufficient data (should be same
                # number of obs in both types of TAF so only need to check one)
                if f_key == 'im':
                    stats_dict = check_obs(stats_dict, row, req_obs)

    # Remove airports with insufficient data
    stats_dict = {key: value for key, value in stats_dict.items()
                  if value['enough_obs']}

    # Return the dictionary of stats
    return stats_dict


def add_gerrity(stats_dict, row, f_key):
    """
    Adds Gerrity skill score to appropriate parts of stats dictionary.
    """
    # Add for all TAFs
    stats_dict[row[0]][f'g_{f_key}'] = float(row[3])

    # Add length-specific keys and values as well
    if row[0] in TAF_9HR:
        stats_dict[row[0]][f'g_{f_key}_9'] = float(row[3])
    else:
        stats_dict[row[0]][f'g_{f_key}_9'] = np.nan
    if row[0] in TAF_24HR:
        stats_dict[row[0]][f'g_{f_key}_24'] = float(row[3])
    else:
        stats_dict[row[0]][f'g_{f_key}_24'] = np.nan
    if row[0] in TAF_30HR:
        stats_dict[row[0]][f'g_{f_key}_30'] = float(row[3])
    else:
        stats_dict[row[0]][f'g_{f_key}_30'] = np.nan

    return stats_dict


def add_small_peirce(stats_dict, row, f_key):
    """
    Adds Peirce skill score to appropriate parts of stats dictionary.
    """
    # Add score for each category
    for ind, p_score in enumerate(row[3:]):
        stats_dict[row[0]][f'sp_{f_key}_{ind+1}'] = float(p_score)

    return stats_dict


def add_big_peirce(stats_dict, row, f_key):
    """
    Adds Peirce skill score to appropriate parts of stats dictionary.
    """
    # Add score to dictionary
    stats_dict[row[0]][f'bp_{f_key}'] = float(row[3])

    return stats_dict


def add_freqs(stats_dict, row, f_key, num_cats):
    """
    Adds relative frequencies to appropriate parts of stats dictionary.
    """
    # Add relative frequency for each category, for forecasts and observations
    stats_dict[row[0]][f'rf_{f_key}_fcast'] = [float(rf)
                                               for rf in row[3: 3 + num_cats]]
    stats_dict[row[0]][f'rf_{f_key}_ob'] = [float(rf)
                                               for rf in row[3 + num_cats:]]

    return stats_dict


def add_cts(stats_dict, row, f_key, ncs):
    """
    Adds contingency values to appropriate parts of stats dictionary.
    """
    # Get contingency values for each TAF category
    ct_vals = [[float(ct) for ct in row[3 + ind * ncs: 3 + ind * ncs + ncs]]
               for ind in range(ncs)]

    # Add to stats dictionary
    stats_dict[row[0]][f'ct_{f_key}'] = ct_vals

    return stats_dict


def check_obs(stats_dict, row, req_obs):
    """
    Checks number of matched obs to determine whether there is sufficient data
    for verification.
    """
    # Get number of matched obs from contingency table
    num_obs = sum([float(ct) for ct in row[3:]])
    if math.isnan(num_obs):
        num_obs = 0

    # Number of required obs depends on TAF length
    if row[0] in TAF_30HR:
        l_req_obs = req_obs[0]
    elif row[0] in TAF_24HR:
        l_req_obs = req_obs[1]
    elif row[0] in TAF_9HR:
        l_req_obs = req_obs[2]
    enough_obs = bool(num_obs >= l_req_obs)

    # print(row[0], int(num_obs))

    # If not enough data, print message
    if not enough_obs:
        print(f'Not enough obs for {row[0]} - {int(num_obs)} available, '
              f'{int(l_req_obs)} required')

    # Add bool to dictionary based on whether number of obs meets requirements
    stats_dict[row[0]]['enough_obs'] = enough_obs

    return stats_dict


def make_plot(param, color_dict, stats_dict, score, unc, comb, length='',
              cat=''):
    """
    Creates a scatter plot.
    """
    # Define title, fname and keys for extracting data from stats dictionary
    title, fname, key_1, key_2 = get_strings(score, param, length, cat, unc,
                                             comb)

    # Extract data from stats dictionary
    airports, stats_1, stats_2 = extract_data(stats_dict, key_1, key_2, cat,
                                              param)

    # Set axes limits for plots
    lim_min, lim_max, lim_diff = set_lims(stats_1, stats_2)

    # Define figure and axes
    fig, ax = plt.subplots()

    # Set axes limits
    ax.set_xlim(lim_min, lim_max)
    ax.set_ylim(lim_min, lim_max)

    # Plot text, lines and shading depending on type of plot
    if length:
        ax = add_length_detail(ax, param, length, lim_min, lim_max, lim_diff,
                               comb)
    else:
        ax = add_detail(ax, lim_min, lim_max, lim_diff, comb)

    # Plot scatter points for each airport
    for stat_1, stat_2, airport in zip(stats_1, stats_2, airports):
        label = ICAO_DICT[airport]
        ax.scatter(stat_1, stat_2, color=color_dict[airport]['colour'],
                   s=color_dict[airport]['size'],
                   marker=color_dict[airport]['marker'], label=label,
                   edgecolor='black', linewidth=1)

    # Set titles, legend, etc
    ax.set_title(title, fontsize=20, weight='bold')
    ax.set_xlabel(f'Scores based on {TAF_TYPES[comb[:2]]} TAFs', fontsize=14)
    ax.set_ylabel(f'Scores based on {TAF_TYPES[comb[2:]]} TAFs', fontsize=14)
    ax.legend(loc='upper center', ncol=2, fontsize=12, 
              bbox_to_anchor=(1.45, 1.0))

    # Save and close figure
    fig.savefig(fname, bbox_inches='tight')
    plt.close()


def rel_freq_plot(param, stats_dict):

    # For collecting stats
    plot_stats = {'Relative Frequency': [], 'Type': [], 'TAF Category': []}

    # For checking observed frequencies are the same for all TAF types
    obs_frqs = {}

    # Loop though TAF types (BestData, IMPROVER, manual)
    for t_type_ind, taf_type in enumerate(TAF_TYPES):

        # Get stats for each airport
        for icao_ind, (icao, stats) in enumerate(stats_dict.items()):

            # Get forecast frequencies for each category
            fcst_rf = stats[f'rf_{taf_type}_fcast']

            # Observed frequencies should be the same for all TAF types 
            # so only use once but assert that they are the same
            obs_rf = stats[f'rf_{taf_type}_ob']
            if icao in obs_frqs:
                for ob_frq_1, ob_frq_2 in zip(obs_rf, obs_frqs[icao]):
                    assert abs(ob_frq_1 - ob_frq_2) <= 0.0000001
            else:
                obs_frqs[icao] = obs_rf

            # Add icao stats to total stats (if necessary for observed)
            if icao_ind == 0:
                if t_type_ind == 0:
                    total_obs_rf = obs_rf
                total_fcst_rf = fcst_rf
            else:
                if t_type_ind == 0:
                    total_obs_rf = [a + b for a, b in zip(obs_rf, 
                                                          total_obs_rf)]
                total_fcst_rf = [a + b for a, b in zip(obs_rf, total_fcst_rf)]

        # Define TAF categories (6 for vis, 5 for cloud)
        cats = np.arange(1, len(total_fcst_rf) + 1)

        # Get mean forecastrelative frequencies and add to stats dict
        mean_fcst_rfs = np.array(total_fcst_rf) / len(stats_dict)
        for frf, cat in zip(mean_fcst_rfs, cats):
            plot_stats['Relative Frequency'].append(frf)
            plot_stats['Type'].append(f'{TAF_TYPES[taf_type]} forecast')
            plot_stats['TAF Category'].append(cat)

        # Add mean observed relative frequencies if necessary
        if t_type_ind == 0:
            mean_obs_rfs = np.array(total_obs_rf) / len(stats_dict)
            for orf, cat in zip(mean_obs_rfs, cats):
                plot_stats['Relative Frequency'].append(orf)
                plot_stats['Type'].append('Observed')
                plot_stats['TAF Category'].append(cat)
                

    # Create figure and axis
    fig, ax = plt.subplots(figsize=(12, 6))

    # Create bar plots
    hue_order = [f'{t_type} forecast' for t_type in TAF_TYPES.values()]
    hue_order.append('Observed')
    rf_bar = sns.barplot(plot_stats, x='TAF Category', y='Relative Frequency', 
                         hue='Type', hue_order=hue_order)

    # Formatting, etc
    ax.set_title(PARAMS[param])
    ax.tick_params(axis='x', labelsize=15)
    sns.move_legend(ax, "upper left", bbox_to_anchor=(1, 1))
    ax.set_yscale('log')
    plt.setp(rf_bar.get_legend().get_title(), weight='bold')

    # Save and close figure
    plt.tight_layout()
    fig.savefig(f'{STATS_DIR}/rl_plots/{param}_mean_rel_freqs.png')
    plt.close()


def get_strings(score, param, length, cat, unc, comb):
    """
    Determines strings to use for plot titles and fnames, as well as keys to
    use for extracting data from stats dictionary.
    """
    # Extra strings to add to filenames, keys and titles
    k_extra, t_extra, f_extra = '', '', ''
    if length:
        k_extra += f'_{length}'
        t_extra += f' - {length} hr TAFs'
        f_extra += f'_{length}hr'
    if cat:
        if cat != 'all':
            k_extra += f'_{cat}'
            t_extra += f' - category {cat}'
        else:
            t_extra += '\nMean of all categories'
        f_extra += f'_cat_{cat}'
    if unc:
        t_extra += ' (uncertainty)'

    # keys to use for extracting info from stats dictionary
    key_1 = f'{score}_{comb[:2]}{k_extra}'
    key_2 = f'{score}_{comb[2:]}{k_extra}'

    # Plot title and fname
    title = f'{PARAMS[param]} {SCORES[score]} Skill Scores{t_extra}'
    imdir = 'scatter_plots'
    fname = (f'{STATS_DIR}/{imdir}/{param}_{comb}_{score}_scatter'
             f'{f_extra}{unc}.png')

    return title, fname, key_1, key_2


def extract_data(stats_dict, key_1, key_2, cat, param):
    """
    Extracts required data from stats dictionary.
    """
    # Create dataframe from data
    if cat == 'all':
        stats_df = pd.DataFrame(
            {'airports': stats_dict.keys(),
             'stats_1': [np.mean([key[f'{key_1}_{cat}']
                                  for cat in range(1, NUM_CATS[param] + 1)
                                  if str(key[f'{key_1}_{cat}']) != 'nan'])
                         for key in stats_dict.values()],
             'stats_2': [np.mean([key[f'{key_2}_{cat}']
                                  for cat in range(1, NUM_CATS[param] + 1)
                                  if str(key[f'{key_2}_{cat}']) != 'nan'])
                         for key in stats_dict.values()]}
            )
    else:
        stats_df = pd.DataFrame(
            {'airports': stats_dict.keys(),
             'stats_1': [key[key_1] for key in stats_dict.values()],
             'stats_2': [key[key_2] for key in stats_dict.values()]}
            )

    # Only include stats with no nans
    stats_df = stats_df.dropna()

    # Get values out of dataframe and return
    return [stats_df[col] for col in ['airports', 'stats_1', 'stats_2']]


def set_lims(x_vals, y_vals):
    """
    Defines axes limits based on the range of the data.
    """
    # Determine min/max x and y values, subtracting/adding 10%
    min_x, min_y = [np.min(vals) - 0.1 for vals in [x_vals, y_vals]]
    max_x, max_y = [np.max(vals) + 0.1 for vals in [x_vals, y_vals]]

    # Define limits from these values
    lim_min = max([min([min_x, min_y]), -1])
    lim_max = min([max([max_x, max_y]), 1])
    lim_diff = lim_max - lim_min

    return lim_min, lim_max, lim_diff


def add_length_detail(ax, param, length, lim_min, lim_max, lim_diff, comb):
    """
    Adds text, lines and shading to TAF length plots.
    """
    # Add dashed target lines, shading and text for CAA targets
    target = TARGETS[f'{param}_{length}']
    ax.axhline(y=target, linestyle='--', alpha=0.5)
    ax.axhspan(lim_min, target, alpha=0.03, color='r')
    ax.axhspan(target, lim_max, alpha=0.05, color='g')
    ax.text(0.09, target + 0.025, target, color='blue',
            transform=ax.get_yaxis_transform(), ha='right', va='top')
    ax.axvline(x=target, linestyle='--', alpha=0.5)
    ax.axvspan(lim_min, target, alpha=0.03, color='r')
    ax.axvspan(target, lim_max, alpha=0.05, color='g')
    ax.text(target - 0.01, 0.07, target, color='blue', rotation=90,
            transform=ax.get_xaxis_transform(), ha='center', va='center')

    # Positions for extra text
    positions = [.02, .9, .8, .78, .95, .02, .03, .8, .11, .02]
    (xtl, ytl1, ytl2, xtr, ytr,
     xbl, ybl, xbr, ybr1, ybr2) = [lim_min + pos * lim_diff
                                   for pos in positions]

    # Add extra text
    ax.text(xtl, ytl1, f'{TAF_TYPES[comb[:2]]}\nTAFs below', color='r')
    ax.text(xtl, ytl2, f'{TAF_TYPES[comb[2:]]}\nTAFs above', color='g')
    ax.text(xtr, ytr, 'Both above', color='g')
    ax.text(xbl, ybl, 'Both below', color='r')
    ax.text(xbr, ybr1, f'{TAF_TYPES[comb[2:]]}\nTAFs below', color='r')
    ax.text(xbr, ybr2, f'{TAF_TYPES[comb[:2]]}\nTAFs above', color='g')

    return ax


def add_detail(ax, lim_min, lim_max, lim_diff, comb):
    """
    Adds text, lines and shading to plots.
    """
    # Array of axes limits
    lims = np.array([lim_min, lim_max])

    # Plot x=y line
    ax.plot(lims, lims)

    # Add shading
    ax.fill_between(lims, lims, lim_min, color='red', alpha=0.05)
    ax.fill_between(lims, lims, lim_max, color='green', alpha=0.05)

    # Positions for extra text
    positions = [.05, .85, .68, .05]
    fgx, fgy, isx, isy = [lim_min + pos * lim_diff for pos in positions]

    # Add extra text
    ax.text(fgx, fgy, f'{TAF_TYPES[comb[2:]]} TAF\nscores higher', c='green',
            fontsize=15)
    ax.text(isx, isy, f'{TAF_TYPES[comb[:2]]} TAF\nscores higher', c='red',
            fontsize=15)

    return ax


def get_color_dict():
    """
    Assigns a random colour to each airport
    """
    # List to collect airport ICAOs
    airports = []

    # Open one of the csv files (doesn't matter which)
    stats_file = f'{STATS_DIR}/vis_stats.csv'
    with open(stats_file, encoding='utf-8') as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=',')

        # Collect all airport ICAOs
        for row in csv_reader:
            if row[0] not in airports:
                airports.append(row[0])

    # Number of unique colours needed
    num_clrs = len(airports)

    # Get list of random unique colours using rainbow colormap
    cmap = plt.get_cmap('gist_rainbow')
    colours = [cmap(1. * ind / num_clrs) for ind in range(num_clrs)]

    # Get lists of markers and marker sizes
    marks = list(islice(cycle(MARKERS), num_clrs))
    m_sizes = list(islice(cycle(SIZES), num_clrs))

    # Get colour dictionary assigning a colour and marker to each airport
    color_dict = {air: {'colour': c, 'marker': m, 'size': s}
                  for air, c, m, s in zip(airports, colours, marks, m_sizes)}

    return color_dict


def calc_min_obs(s_str, e_str):
    """
    Calculates minimum number of matched observations required,
    based on length of verification period and TAF length.
    """
    # Convert date strings to datetime objects
    sdt, edt = [datetime.strptime(d_str, '%Y%m%d') for d_str in [s_str, e_str]]

    # Get number of days between start and end of verification period
    vdays = (edt - sdt).days

    # Average of 1 TAFs per day required (2 obs per hour expected)
    min_obs_30hr =  1 * 2 * 30 * vdays
    min_obs_24hr =  1 * 2 * 24 * vdays
    min_obs_9hr =  1 * 2 * 9 * vdays

    # TESTING ===================================
    # min_obs_30hr =  0
    # min_obs_24hr =  0
    # min_obs_9hr =  0
    

    return min_obs_30hr, min_obs_24hr, min_obs_9hr


if __name__ == '__main__':

    # Get min number of matched required to ensure enough data for verification
    min_obs = calc_min_obs(START, END)

    # Run for normal scores and uncertainty-penalising scores
    main(min_obs, '')
    # main(min_obs, '_unc')

    print('Finished')
