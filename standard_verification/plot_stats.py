"""
Creates plots comaparing TAF verification scores.

Functions:
    main: Main function
    add_big_peirce: Adds Peirce skill score to stats dictionary
    add_cts: Adds contingency values to stats dictionary
    add_detail: Adds text, lines and shading to plots
    add_freqs: Adds relative frequencies to stats dictionary
    add_gerrity: Adds Gerrity skill score to stats dictionary
    add_length_detail: Adds text, lines and shading to TAF length plots
    add_small_peirce: Adds Peirce skill score to stats dictionary
    calc_min_obs: Calculates min number of matched observations required
    check_obs: Checks whether there is sufficient data for verification
    do_t_tests: Performs t-tests to determine statistical significance
    extract_data: Extracts required data from stats dictionary
    get_color_dict: Assigns a random colour to each airport
    get_icao_dict: Creates dictionary mapping ICAOs to airport names
    get_stats: Collects stats from a csv file
    get_strings: Determines strings to use for plot titles and fnames
    make_plot: Creates a scatter plot
    rel_freq_plot: Creates a plot showing relative frequencies
    set_lims: Sets limits for axes
    sp_box_plot: Creates a box plot for Peirce skill scores

Written by Andre Lanyon.
"""
import csv
import math
import json
import os
from datetime import datetime
from itertools import cycle, islice

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

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
TAF_TYPES = os.environ['TAF_TYPES'].split()
TAF_TYPES_SHORT = os.environ['TAF_TYPES_SHORT'].split()
PLOT_TITLES = os.environ.get('PLOT_TITLES')
TAF_TYPES_PLOT = json.loads(PLOT_TITLES)
ML_FACTOR = float(os.environ['ML_FACTOR'])

# Define other constants
PARAMS = {'vis': 'Visibility', 'clb': 'Cloud'}
TAF_TYPES_DICT = dict(zip(TAF_TYPES_SHORT, TAF_TYPES))
TAF_TYPES_INV = {v: k for k, v in TAF_TYPES_DICT.items()}
TAF_TYPES_FNAME = '_'.join(TAF_TYPES_SHORT)
NUM_CATS = {'vis': 6, 'clb': 5}
# Category labels for contingency tables (match config thresholds:
# vis_cats [350, 800, 1500, 5000, 10000], clb_cats [200, 500, 1000, 1500])
TAF_CATS = {
    'vis': ['<350m', '350-800m', '800-1500m', '1500-5000m', '5000-10000m',
            '>=10000m'],
    'clb': ['<200ft', '200-500ft', '500-1000ft', '1000-1500ft', '>=1500ft'],
}
SCORES = {'g': 'Gerrity', 'sp': 'Peirce', 'bp': 'Peirce'}
TARGETS = {
    'vis_9': [0.426, 'blue', '9-hr visibility target'],
    'vis_24': [0.345, 'orange', '24-hr visibility target'],
    'vis_30': [0.366, 'purple', '30-hr visibility target'],
    'clb_9': [0.517, 'red', '9-hr cloud target'],
    'clb_24': [0.468, 'green', '24-hr cloud target'],
    'clb_30': [0.457, 'brown', '30-hr cloud target'],
}
MARKERS = ['o', 'v', 'P', 'X', 's', 'p', '*', 'D']
SIZES = [50, 50, 60, 50, 50, 60, 80, 40]


def main(req_obs, unc):
    """
    Creates plots comparing verification scores from manually produced
    TAFs to those of first guess TAFs

    Args:
        req_obs (list): List of required number of observations for each
                        TAF length
        unc (str): String to add to filenames if uncertainty is included
    """
    # Make directories if needed
    for p_dir in ['rl_plots', 'scatter_plots', 'g_plots', 'sp_plots',
                  'airport_plots', 'confusion_plots']:
        if not os.path.exists(f'{STATS_DIR}/{p_dir}'):
            os.makedirs(f'{STATS_DIR}/{p_dir}')

    # Get dictionary mapping ICAOs to airport names
    icao_dict = get_icao_dict()

    # Get random set of colours to assign to the airports
    color_dict = get_color_dict()

    # For collecting all stats
    all_stats = {}

    # Get stats from csv files
    for param in PARAMS:

        # Empty lists to append stats to
        stats_dict = get_stats(param, unc, req_obs)

        sp_box_plot(stats_dict, param)

        rel_freq_plot(param, stats_dict)

        all_stats[param] = stats_dict

    # Combined visibility + cloud scatter plots: one figure per TAF-type
    # combination, with both parameters side by side sharing a single legend
    for comb in COMBS:

        # Scatter plots showing Gerrity scores for all airports
        make_plot(color_dict, all_stats, 'g', unc, comb, icao_dict)

    # Create Gerrity score box plots
    g_box_plot(all_stats)

    # One summary figure per airport (Gerrity and Peirce skill scores for
    # visibility and cloud base, comparing all TAF types)
    for icao in sorted(set(all_stats['vis']) & set(all_stats['clb'])):
        airport_plot(all_stats, icao, icao_dict, unc)
        confusion_plot(all_stats, icao, icao_dict, unc)


def add_big_peirce(stats_dict, row, f_key):
    """
    Adds Peirce skill score to appropriate parts of stats dictionary.

    Args:
        stats_dict (dict): Dictionary of stats
        row (list): List of values from csv file
        f_key (str): Key to use for dictionary
    Returns:
        stats_dict (dict): Updated dictionary of stats
    """
    # Add score to dictionary
    stats_dict[row[0]][f'bp_{f_key}'] = float(row[3])

    return stats_dict


def add_cts(stats_dict, row, f_key, ncs):
    """
    Adds contingency values to appropriate parts of stats dictionary.

    Args:
        stats_dict (dict): Dictionary of stats
        row (list): List of values from csv file
        f_key (str): Key to use for dictionary
        ncs (int): Number of contingency stats per category
    Returns:
        stats_dict (dict): Updated dictionary of stats
    """
    # Get contingency values for each TAF category
    ct_vals = [[float(ct) for ct in row[3 + ind * ncs: 3 + ind * ncs + ncs]]
               for ind in range(ncs)]

    # Add to stats dictionary
    stats_dict[row[0]][f'ct_{f_key}'] = ct_vals

    return stats_dict


def add_detail(ax, lim_min, lim_max, lim_diff, comb):
    """
    Adds text, lines and shading to plots.

    Args:
        ax (matplotlib.axes): Axis to add text, lines and shading to
        lim_min (float): Minimum value for axes
        lim_max (float): Maximum value for axes
        lim_diff (float): Difference between min and max values
        comb (str): Combination of TAF types being verified
    Returns:
        ax (matplotlib.axes): Updated axis
    """
    # Array of axes limits
    lims = np.array([lim_min, lim_max])

    # Plot x=y line
    ax.plot(lims, lims)

    # Add shading
    ax.fill_between(lims, lims, lim_min, color='green', alpha=0.05)
    ax.fill_between(lims, lims, lim_max, color='red', alpha=0.05)

    # Add corner annotations in axes-fraction coordinates with alignment so
    # the text always stays inside the plot regardless of its length
    ax.text(0.03, 0.97, f'{TAF_TYPES_PLOT[comb[2:]]}\nScores Higher',
            c='red', fontsize=13, weight='bold', transform=ax.transAxes,
            ha='left', va='top')
    ax.text(0.97, 0.03, f'{TAF_TYPES_PLOT[comb[:2]]}\nScores Higher',
            c='green', fontsize=13, weight='bold', transform=ax.transAxes,
            ha='right', va='bottom')

    return ax


def add_freqs(stats_dict, row, f_key, num_cats):
    """
    Adds relative frequencies to appropriate parts of stats dictionary.

    Args:
        stats_dict (dict): Dictionary of stats
        row (list): List of values from csv file
        f_key (str): Key to use for dictionary
        num_cats (int): Number of TAF categories
    Returns:
        stats_dict (dict): Updated dictionary of stats
    """
    # Add relative frequency for each category
    stats_dict[row[0]][f'rf_{f_key}_fcast'] = [float(rf)
                                               for rf in row[3: 3 + num_cats]]
    stats_dict[row[0]][f'rf_{f_key}_ob'] = [float(rf)
                                               for rf in row[3 + num_cats:]]

    return stats_dict


def add_gerrity(stats_dict, row, f_key):
    """
    Adds Gerrity skill score to appropriate parts of stats dictionary.

    Args:
        stats_dict (dict): Dictionary of stats
        row (list): List of values from csv file
        f_key (str): Key to use for dictionary
    Returns:
        stats_dict (dict): Updated dictionary of stats
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


def add_length_detail(ax, param, length, lim_min, lim_max, lim_diff, comb):
    """
    Adds text, lines and shading to TAF length plots.

    Args:
        ax (matplotlib.axes): Axis to add text, lines and shading to
        param (str): Parameter being verified
        length (int): Length of TAFs being verified
        lim_min (float): Minimum value for axes
        lim_max (float): Maximum value for axes
        lim_diff (float): Difference between min and max values
        comb (str): Combination of TAF types being verified
    Returns:
        ax (matplotlib.axes): Updated axis
    """
    # Add dashed target lines, shading and text for CAA targets
    target = TARGETS[f'{param}_{length}'][0]
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
    ax.text(xtl, ytl1, f'{TAF_TYPES_DICT[comb[:2]]}\nTAFs below', color='r')
    ax.text(xtl, ytl2, f'{TAF_TYPES_DICT[comb[2:]]}\nTAFs above', color='g')
    ax.text(xtr, ytr, 'Both above', color='g')
    ax.text(xbl, ybl, 'Both below', color='r')
    ax.text(xbr, ybr1, f'{TAF_TYPES_DICT[comb[2:]]}\nTAFs below', color='r')
    ax.text(xbr, ybr2, f'{TAF_TYPES_DICT[comb[:2]]}\nTAFs above', color='g')

    return ax


def add_small_peirce(stats_dict, row, f_key):
    """
    Adds Peirce skill score to appropriate parts of stats dictionary.

    Args:
        stats_dict (dict): Dictionary of stats
        row (list): List of values from csv file
        f_key (str): Key to use for dictionary
    Returns:
        stats_dict (dict): Updated dictionary of stats
    """
    # Add score for each category
    for ind, p_score in enumerate(row[3:]):
        stats_dict[row[0]][f'sp_{f_key}_{ind+1}'] = float(p_score)

    return stats_dict


def calc_min_obs(s_str, e_str):
    """
    Calculates minimum number of matched observations required, based on
    length of verification period and TAF length.

    Args:
        s_str (str): Start date of verification period
        e_str (str): End date of verification period
    Returns:
        min_obs_30hr (int): Minimum matched obs required for 30hr TAFs
        min_obs_24hr (int): Minimum matched obs required for 24hr TAFs
        min_obs_9hr (int): Minimum matched obs required for 9hr TAFs
    """
    # Convert date strings to datetime objects
    sdt, edt = [datetime.strptime(d_str, '%Y%m%d') for d_str in [s_str, e_str]]

    # Get number of days between start and end of verification period
    vdays = (edt - sdt).days * 0.2

    # Average of 2 TAFs per day required (2 obs per hour expected)
    min_obs_30hr =  2 * 2 * 30 * vdays * ML_FACTOR
    min_obs_24hr =  2 * 2 * 24 * vdays * ML_FACTOR
    min_obs_9hr =  2 * 2 * 9 * vdays * ML_FACTOR

    return min_obs_30hr, min_obs_24hr, min_obs_9hr


def check_obs(stats_dict, row, req_obs, total_tafs):
    """
    Checks number of matched obs to determine whether there is
    sufficient data for verification.

    Args:
        stats_dict (dict): Dictionary of stats
        row (list): List of values from csv file
        req_obs (list): List of required number of observations for each
                        TAF length
        total_tafs (int): Total number of TAFs used in verification
    Returns:
        stats_dict (dict): Updated dictionary of stats
    """
    # Get number of matched obs from contingency table
    num_obs = sum(float(ct) for ct in row[3:])
    if math.isnan(num_obs):
        num_obs = 0

    # Number of required obs depends on TAF length
    if row[0] in TAF_30HR:
        l_req_obs = req_obs[0]
        num_tafs = num_obs / 60
    elif row[0] in TAF_24HR:
        l_req_obs = req_obs[1]
        num_tafs = num_obs / 48
    elif row[0] in TAF_9HR:
        l_req_obs = req_obs[2]
        num_tafs = num_obs / 18
    enough_obs = bool(num_obs >= l_req_obs)

    # If not enough data, print message
    if not enough_obs:
        print(f'Not enough obs for {row[0]} - {int(num_obs)} available, '
              f'{int(l_req_obs)} required')
    else:
        print(f'{row[0]} has enough obs ({int(num_obs)})')
        print(f'  Number of TAFs: {int(num_tafs)}')
        total_tafs += num_tafs

    # Add bool to dictionary based on whether number of obs meets requirements
    stats_dict[row[0]]['enough_obs'] = enough_obs

    return stats_dict, total_tafs


def extract_data(stats_dict, key_1, key_2, cat, param):
    """
    Extracts required data from stats dictionary.

    Args:
        stats_dict (dict): Dictionary of stats
        key_1 (str): Key to use for extracting data from stats dict
        key_2 (str): Key to use for extracting data from stats dict
        cat (int): Category of TAFs to plot
        param (str): Parameter to verify
    Returns:
        airports (list): List of airport ICAO codes
        stats_1 (list): List of scores based on first TAF type
        stats_2 (list): List of scores based on second TAF type
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


def get_color_dict():
    """
    Assigns a random colour to each airport.

    Args:
        None
    Returns:
        color_dict (dict): Dictionary of colours to use for each airport
    """
    # List to collect airport ICAOs
    airports = []

    # Open one of the csv files (doesn't matter which)
    stats_file = f'{STATS_DIR}/vis_stats_{TAF_TYPES_FNAME}.csv'
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


def get_icao_dict():
    """
    Creates a dictionary mapping ICAO codes to airport names.

    Args:
        None
    Returns:
        icao_dict (dict): Dictionary mapping ICAO codes to airport names
    """
    # Load in airport info
    airport_info = pd.read_csv('taf_info.csv', header=0)

    # Create dictionary mapping ICAO codes to airport names
    icao_dict = pd.Series(airport_info.airport_name.values,
                          index=airport_info.icao).to_dict()

    return icao_dict


def get_stats(param, unc, req_obs):
    """
    Collects stats from a csv file.

    Args:
        param (str): Parameter to verify
        unc (str): String to add to filenames if uncertainty is included
        req_obs (list): List of required number of observations for each
                        TAF length
    """
    # Define stats file
    stats_file = f'{STATS_DIR}/{param}_stats_{TAF_TYPES_FNAME}{unc}.csv'


    # Dictionary to add stats to
    stats_dict = {}

    # For calculating total number of TAFs used
    total_tafs = 0

    # Open csv file
    with open(stats_file, encoding='utf-8') as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=',')

        # Collect appropriate stats from each row
        for row in csv_reader:

            # Check if TAF in list of good TAFs
            if row[0] not in ALL_TAFS:
                continue

            # Only collect for required TAF types
            if row[2] not in TAF_TYPES_INV:
                continue

            # Get first part of key to add to dictionary
            f_key = TAF_TYPES_INV[row[2]]

            # Add airport to stats dictionary if necessary
            if row[0] not in stats_dict:
                stats_dict[row[0]] = {}

            # Look for Gerrity skill scores, add to dictionary if found
            if row[1] == 'gerrity':
                stats_dict = add_gerrity(stats_dict, row, f_key)

            # Look for Peirce skill scores, add to dictionary if found
            elif row[1] == 'big_peirce':
                stats_dict = add_big_peirce(stats_dict, row, f_key)

            # Look for Peirce skill scores, add to dictionary if found
            elif row[1] == 'peirce':
                stats_dict = add_small_peirce(stats_dict, row, f_key)

            # Look for relative frequencies, add to dictionary if found
            elif row[1] == 'freqs':
                stats_dict = add_freqs(stats_dict, row, f_key, NUM_CATS[param])

            # Look for contingency tbl vals, add to dictionary if found
            elif row[1] == 'ctvals':
                stats_dict = add_cts(stats_dict, row, f_key, NUM_CATS[param])

                # Check that airport has sufficient data (should be same
                # number of obs in both types of TAF so only need to
                # check one)
                if f_key == 'ma':
                    stats_dict, total_tafs = check_obs(stats_dict, row, 
                                                       req_obs, total_tafs)

    # Remove airports with insufficient data
    stats_dict = {key: value for key, value in stats_dict.items()
                  if value['enough_obs']}
    
    print('\n-------------------------------------')
    print(f'Total number of {param} TAFs used: {total_tafs}')
    print('-------------------------------------\n')

    # Return the dictionary of stats
    return stats_dict


def get_strings(score, param, length, cat, unc, comb):
    """
    Determines strings to use for plot titles and fnames, as well as
    keys to use for extracting data from stats dictionary.

    Args:
        score (str): Score to plot
        param (str): Parameter to verify
        length (int): Length of TAFs to plot
        cat (int): Category of TAFs to plot
        unc (str): String to add to filenames if uncertainty is included
        comb (str): Combination of TAF types to plot
    Returns:
        title (str): Title for plot
        fname (str): Filename for plot
        key_1 (str): Key to use for extracting data from stats dict
        key_2 (str): Key to use for extracting data from stats dict
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


def make_plot(color_dict, all_stats, score, unc, comb, icao_dict,
              length='', cat=''):
    """
    Creates a combined scatter plot with visibility and cloud base shown
    side by side on the same figure, sharing a single legend.

    Args:
        color_dict (dict): Dictionary of colours to use for each airport
        all_stats (dict): Dictionary of stats keyed by parameter
        score (str): Score to plot
        unc (str): String to add to filenames if uncertainty is included
        comb (str): Combination of TAF types to plot
        icao_dict (dict): Dictionary mapping ICAO codes to airport names
        length (int): Length of TAFs to plot
        cat (int): Category of TAFs to plot
    Returns:
        None
    """
    # One subplot per parameter (visibility and cloud base) side by side
    fig, axes = plt.subplots(1, 2, figsize=(16, 7))

    for ax, param in zip(axes, PARAMS):

        stats_dict = all_stats[param]

        # Define title and keys for extracting data from stats dict
        title, _, key_1, key_2 = get_strings(score, param, length, cat, unc,
                                              comb)

        # Extract data from stats dictionary
        airports, stats_1, stats_2 = extract_data(stats_dict, key_1, key_2,
                                                  cat, param)

        # Set axes limits for plots
        lim_min, lim_max, lim_diff = set_lims(stats_1, stats_2)
        ax.set_xlim(lim_min, lim_max)
        ax.set_ylim(lim_min, lim_max)

        # Plot text, lines and shading depending on type of plot
        if length:
            add_length_detail(ax, param, length, lim_min, lim_max, lim_diff,
                              comb)
        else:
            add_detail(ax, lim_min, lim_max, lim_diff, comb)

        # Plot scatter points for each airport
        for stat_1, stat_2, airport in zip(stats_1, stats_2, airports):
            label = icao_dict[airport]
            ax.scatter(stat_1, stat_2, color=color_dict[airport]['colour'],
                       s=color_dict[airport]['size'],
                       marker=color_dict[airport]['marker'], label=label,
                       edgecolor='black', linewidth=1)

        # Set titles and axis labels
        ax.set_title(title, fontsize=18, weight='bold')
        ax.set_xlabel(f'Scores Based on {TAF_TYPES_PLOT[comb[:2]]}',
                      fontsize=14, weight='bold')
        ax.set_ylabel(f'Scores Based on {TAF_TYPES_PLOT[comb[2:]]}',
                      fontsize=14, weight='bold')

    # Build a single shared legend covering every airport from both subplots
    handles_labels = {}
    for ax in axes:
        for handle, lbl in zip(*ax.get_legend_handles_labels()):
            handles_labels.setdefault(lbl, handle)
    fig.legend(list(handles_labels.values()), list(handles_labels.keys()),
               loc='center left', bbox_to_anchor=(1.0, 0.5), ncol=2,
               fontsize=11)

    # Filename for the combined figure
    f_extra = ''
    if length:
        f_extra += f'_{length}hr'
    if cat:
        f_extra += f'_cat_{cat}'
    fname = (f'{STATS_DIR}/scatter_plots/{comb}_{score}_scatter'
             f'{f_extra}{unc}.png')

    # Save and close figure
    fig.tight_layout()
    fig.savefig(fname, bbox_inches='tight')
    plt.close()


def airport_plot(all_stats, icao, icao_dict, unc):
    """
    Creates a single summary figure for one airport.

    The figure has a 2x2 layout: rows are the parameters (visibility and
    cloud base) and columns show (left) the overall Gerrity skill score and
    (right) the Peirce skill score for each TAF category. Bars are coloured
    by TAF type, with a single shared legend.

    Args:
        all_stats (dict): Dictionary of stats keyed by parameter
        icao (str): ICAO code of the airport to plot
        icao_dict (dict): Dictionary mapping ICAO codes to airport names
        unc (str): String to add to filenames if uncertainty is included
    Returns:
        None
    """
    # Consistent colour per TAF type, matching the overall Gerrity and
    # Peirce box plots (seaborn's default "deep" palette, in the same
    # op -> pe -> ma order used there)
    taf_types = list(TAF_TYPES_PLOT.items())
    n_types = len(taf_types)
    palette = sns.color_palette('deep', n_types)
    width = 0.8 / n_types

    # 2 rows (parameters) x 2 columns (overall Gerrity, per-category Peirce)
    fig, axes = plt.subplots(2, 2, figsize=(15, 10))

    for row, param in enumerate(PARAMS):

        i_stats = all_stats[param][icao]
        ncats = NUM_CATS[param]

        # Left column: overall Gerrity skill score, one bar per TAF type
        ax = axes[row, 0]
        xg = np.arange(n_types)
        for i, (short, name) in enumerate(taf_types):
            val = i_stats.get(f'g_{short}', np.nan)
            ax.bar(xg[i], val, 0.6, label=name, color=palette[i],
                   edgecolor='black', linewidth=0.6)
        ax.axhline(0, color='grey', linewidth=0.8)
        ax.set_xticks(xg)
        ax.set_xticklabels([])
        ax.set_xlabel('TAF Type', weight='bold')
        ax.set_ylabel('Gerrity Skill Score', weight='bold')
        ax.set_title(f'{PARAMS[param]} \u2013 Overall Gerrity Skill',
                     weight='bold', fontsize=14)

        # Right column: Peirce skill score for each TAF category
        ax = axes[row, 1]
        cats = np.arange(1, ncats + 1)
        xc = np.arange(ncats)
        for i, (short, name) in enumerate(taf_types):
            vals = [i_stats.get(f'sp_{short}_{c}', np.nan) for c in cats]
            ax.bar(xc + (i - (n_types - 1) / 2) * width, vals, width,
                   label=name, color=palette[i], edgecolor='black',
                   linewidth=0.6)
        ax.axhline(0, color='grey', linewidth=0.8)
        ax.set_xticks(xc)
        ax.set_xticklabels([str(c) for c in cats])
        ax.set_xlabel('TAF Category', weight='bold')
        ax.set_ylabel('Peirce Skill Score', weight='bold')
        ax.set_title(f'{PARAMS[param]} \u2013 Peirce Skill by Category',
                     weight='bold', fontsize=14)

    # Single shared legend for all subplots
    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, loc='lower center', ncol=n_types,
               fontsize=13, title='TAF Type', bbox_to_anchor=(0.5, -0.01))

    # Overall title using the airport name
    airport_name = icao_dict.get(icao, icao)
    fig.suptitle(f'{airport_name} ({icao}) \u2013 TAF Verification Skill '
                 'Scores', weight='bold', fontsize=18)

    # Save and close figure
    fig.tight_layout(rect=[0, 0.03, 1, 0.96])
    fname = f'{STATS_DIR}/airport_plots/{icao}_scores{unc}.png'
    fig.savefig(fname, bbox_inches='tight')
    plt.close()


def confusion_plot(all_stats, icao, icao_dict, unc):
    """
    Creates contingency-table (confusion-matrix) heatmaps for one airport.

    One figure is produced per parameter (visibility and cloud base), with
    the contingency table for each TAF type stacked vertically. Rows are
    forecast categories, columns are observed categories, with marginal
    totals. Ported from the rolling branch's confusion-matrix style but
    sourcing values from the stats dictionary.

    Args:
        all_stats (dict): Dictionary of stats keyed by parameter
        icao (str): ICAO code of the airport to plot
        icao_dict (dict): Dictionary mapping ICAO codes to airport names
        unc (str): String to add to filenames if uncertainty is included
    Returns:
        None
    """
    airport_name = icao_dict.get(icao, icao)
    taf_types = list(TAF_TYPES_PLOT.items())

    for param in PARAMS:

        stats_dict = all_stats[param]
        if icao not in stats_dict:
            continue
        i_stats = stats_dict[icao]
        cat_labels = TAF_CATS[param]

        # One subplot per TAF type, stacked vertically
        fig, axes = plt.subplots(len(taf_types), 1,
                                 figsize=(9, 7 * len(taf_types)))
        if len(taf_types) == 1:
            axes = [axes]

        for ax, (short, name) in zip(axes, taf_types):

            ct = i_stats.get(f'ct_{short}')
            if ct is None:
                ax.axis('off')
                continue

            # Forecast (rows) vs observed (columns) contingency table.
            # add_cts stores values indexed [observed][forecast], so the
            # transpose gives forecast-by-observed.
            mat = np.array(ct).T
            ct_df = pd.DataFrame(mat, index=cat_labels, columns=cat_labels)

            # Add marginal totals
            ct_df.loc['Total Obs'] = ct_df.sum()
            ct_df['Total Fcsts'] = ct_df.sum(axis=1)

            fc_labels = cat_labels + ['Total Obs']
            ob_labels = cat_labels + ['Total Fcsts']

            # Mask the totals row/column so they are not colour-shaded
            mask = np.zeros_like(ct_df, dtype=bool)
            mask[-1, :] = True
            mask[:, -1] = True
            ax.set_facecolor('white')

            # Plot heatmap (colour only the main table)
            sns.heatmap(ct_df, annot=False, cmap='Blues', cbar=False,
                        mask=mask, ax=ax, xticklabels=ob_labels,
                        yticklabels=fc_labels)

            # Annotate every cell, choosing text colour for contrast
            nrows, ncols = ct_df.shape
            max_val = ct_df.iloc[:-1, :-1].values.max()
            for i in range(nrows):
                for j in range(ncols):
                    val = ct_df.iloc[i, j]
                    is_total = (i == nrows - 1) or (j == ncols - 1)
                    if is_total:
                        text_color = 'black'
                    else:
                        text_color = 'white' if val > max_val * 0.5 \
                            else 'black'
                    ax.text(j + 0.5, i + 0.5, f'{val:.0f}', ha='center',
                            va='center', color=text_color)

            # Labels and title
            ax.set_xticklabels(ax.get_xticklabels(), rotation=45, ha='right')
            ax.set_yticklabels(ax.get_yticklabels(), rotation=0)
            ax.set_xlabel('Observed Category', fontsize=14, weight='bold')
            ax.set_ylabel('Forecast Category', fontsize=14, weight='bold')
            ax.set_title(name, fontsize=16, weight='bold')

            # Black border around the totals row and column
            ax.add_patch(plt.Rectangle((ct_df.shape[1] - 1, 0), 1,
                                       ct_df.shape[0], fill=False,
                                       edgecolor='black', lw=2))
            ax.add_patch(plt.Rectangle((0, ct_df.shape[0] - 1),
                                       ct_df.shape[1], 1, fill=False,
                                       edgecolor='black', lw=2))

        fig.suptitle(f'{airport_name} ({icao}) \u2013 {PARAMS[param]} '
                     'Contingency Tables', fontsize=18, weight='bold')
        fig.tight_layout(rect=[0, 0, 1, 0.99])
        fname = (f'{STATS_DIR}/confusion_plots/{icao}_{param}_confusion'
                 f'{unc}.png')
        fig.savefig(fname)
        plt.close()


def rel_freq_plot(param, stats_dict):
    """
    Creates a bar plot showing the mean relative frequencies of each TAF
    category for each TAF type.

    Args:
        param (str): Parameter to verify
        stats_dict (dict): Dictionary of stats
    Returns:
        None
    """
    # For collecting stats
    plot_stats = {'Relative Frequency': [], 'Type': [], 'TAF Category': []}

    # For checking observed frequencies are the same for all TAF types
    obs_frqs = {}

    # Loop though TAF types (BestData, IMPROVER, manual)
    for t_type_ind, taf_type in enumerate(TAF_TYPES_DICT):

        # Get stats for each airport
        for icao_ind, (icao, i_stats) in enumerate(stats_dict.items()):

            # Get forecast frequencies for each category
            fcst_rf = i_stats[f'rf_{taf_type}_fcast']

            # Observed frequencies should be the same for all TAF types
            # so only use once but assert that they are the same
            obs_rf = i_stats[f'rf_{taf_type}_ob']
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
            plot_stats['Type'].append(f'{TAF_TYPES_DICT[taf_type]} forecast')
            plot_stats['TAF Category'].append(cat)

        # Add mean observed relative frequencies if necessary
        if t_type_ind == 0:
            mean_obs_rfs = np.array(total_obs_rf) / len(stats_dict)
            for orf, cat in zip(mean_obs_rfs, cats):
                plot_stats['Relative Frequency'].append(orf)
                plot_stats['Type'].append('Observed')
                plot_stats['TAF Category'].append(cat)

    # Just plot obs freqs
    plot_stats = pd.DataFrame(plot_stats)
    plot_stats = plot_stats[plot_stats['Type'] == 'Observed']

    # Create figure and axis
    fig, ax = plt.subplots(figsize=(8, 6))

    # Create bar plots
    # hue_order = [f'{t_type} forecast' for t_type in TAF_TYPES_DICT.values()]
    # hue_order.append('Observed')
    # rf_bar = sns.barplot(plot_stats, x='TAF Category', y='Relative Frequency',
    #                      hue='Type', hue_order=hue_order)
    rf_bar = sns.barplot(plot_stats, x='TAF Category', y='Relative Frequency')
    # Formatting, etc
    ax.set_title(f'{PARAMS[param]} Observed Category Frequencies', 
                 weight='bold', fontsize=20)
    ax.tick_params(axis='x', labelsize=15)
    ax.set_xlabel('TAF Category', weight='bold', fontsize=15)
    ax.set_ylabel('Relative Frequency', weight='bold', fontsize=15)
    # sns.move_legend(ax, "upper left", bbox_to_anchor=(1, 1))
    ax.set_yscale('log')
    # plt.setp(rf_bar.get_legend().get_title(), weight='bold')

    # Save and close figure
    plt.tight_layout()
    fig.savefig(f'{STATS_DIR}/rl_plots/{param}_mean_rel_freqs.png')
    plt.close()


def set_lims(x_vals, y_vals):
    """
    Defines axes limits based on the range of the data.

    Args:
        x_vals (list): List of x values
        y_vals (list): List of y values
    Returns:
        lim_min (float): Minimum value for axes
        lim_max (float): Maximum value for axes
        lim_diff (float): Difference between min and max values
    """
    # Determine min/max x and y values, subtracting/adding 10%
    min_x, min_y = [np.min(vals) - 0.1 for vals in [x_vals, y_vals]]
    max_x, max_y = [np.max(vals) + 0.1 for vals in [x_vals, y_vals]]

    # Define limits from these values
    lim_min = max([min([min_x, min_y]), -1])
    lim_max = min([max([max_x, max_y]), 1])
    lim_diff = lim_max - lim_min

    return lim_min, lim_max, lim_diff


def sp_box_plot(stats_dict, param):
    """
    Creates box plot showing Peirce Skill Scores for each TAF category
    for each airport.

    Args:
        stats_dict (dict): Dictionary of stats
        param (str): Parameter to verify
    Returns:
        plot_stats (pd.DataFrame): DataFrame of Peirce Skill Scores for
                                   each category
    """
    # Create figure and axis
    fig, ax = plt.subplots(figsize=(12, 6))

    # For collecting stats
    t_stats = {cat: {t_type: [] for t_type in TAF_TYPES_PLOT.values()}
               for cat in range(1, NUM_CATS[param] + 1)}
    p_stats = {'Peirce Skill Score': [], 'Category': [], 'TAF Type': []}

    # Loop through each airport
    for icao in stats_dict:

        # Loop through TAF categories
        for cat in range(1, NUM_CATS[param] + 1):

            # Get scores for all TAF types
            sp_scores = {t_name: stats_dict[icao][f'sp_{taf_type}_{cat}'] 
                         for taf_type, t_name in TAF_TYPES_PLOT.items()}

            # Continue to next category if any scores are NaN
            if any([math.isnan(score) for score in sp_scores.values()]):
                continue

            # Loop though TAF types and add to dictionaries
            for t_name, sp_score in sp_scores.items():
                t_stats[cat][t_name].append(sp_score)
                p_stats['Peirce Skill Score'].append(sp_score)
                p_stats['Category'].append(cat)
                p_stats['TAF Type'].append(t_name)

    # Create dataframe from data
    plot_stats = pd.DataFrame(p_stats)

    # Remove rows with XGBoost
    plot_stats = plot_stats[~plot_stats['TAF Type'].str.contains('XGBoost')]

    # Create figure and axis
    fig, ax = plt.subplots(figsize=(12, 6))

    # Create box plot
    sp_box = sns.boxplot(data=plot_stats, x='Category', y='Peirce Skill Score',
                         hue='TAF Type', showfliers=False, ax=ax)

    # Add vertical lines separating categories
    for cat in range(1, NUM_CATS[param]):
        ax.axvline(cat - 0.5, color='white', linestyle='--', alpha=0.5)

    # Formatting, etc
    ax.set_title(f'{PARAMS[param]} Peirce Skill Scores', weight='bold')
    ax.set_xlabel('TAF Category', weight='bold')
    ax.set_ylabel('Peirce Skill Score', weight='bold')
    ax.tick_params(axis='x', labelsize=15)
    sns.move_legend(ax, "upper left", bbox_to_anchor=(1, 1))
    plt.setp(sp_box.get_legend().get_title(), weight='bold')

    # Save and close figure
    plt.tight_layout()
    fig.savefig(f'{STATS_DIR}/sp_plots/{param}_sp_box_plot_{TAF_TYPES_FNAME}'
                '.png')
    plt.close()

    return t_stats


def g_box_plot(all_stats):
    """
    Creates box plot showing Peirce Skill Scores for each TAF category
    for each airport.

    Args:
        stats_dict (dict): Dictionary of stats
    Returns:
        plot_stats (pd.DataFrame): DataFrame of Peirce Skill Scores for
                                   each category
    """
    # Create figure and axis
    fig, ax = plt.subplots(figsize=(12, 6))

    # For collecting stats
    t_stats = {'vis': {t_type: [] for t_type in TAF_TYPES_PLOT.values()},
               'clb': {t_type: [] for t_type in TAF_TYPES_PLOT.values()}}
    p_stats = {'Sharpe GSS': [], 'Parameter': [], 'TAF Type': []}

    # Loop through parameters
    for param in PARAMS:

        # Get parameter stats dict
        stats_dict = all_stats[param]

        # Loop through each airport
        for icao in stats_dict:

            # Get scores for all TAF types
            g_scores = {t_name: stats_dict[icao][f'g_{taf_type}'] 
                        for taf_type, t_name in TAF_TYPES_PLOT.items()}
            
            # Continue to next ICAO if any scores are NaN
            if any([math.isnan(score) for score in g_scores.values()]):
                continue

            # Loop though TAF types and add to dictionaries
            for t_name, g_score in g_scores.items():
                t_stats[param][t_name].append(g_score)
                p_stats['Sharpe GSS'].append(g_score)
                p_stats['Parameter'].append(PARAMS[param])
                p_stats['TAF Type'].append(t_name)

    # Create dataframe from data
    plot_stats = pd.DataFrame(p_stats)

    # Remove rows with XGBoost
    plot_stats = plot_stats[~plot_stats['TAF Type'].str.contains('XGBoost')]

    # Create figure and axis
    fig, ax = plt.subplots(figsize=(12, 8))

    # Create box plot
    g_box = sns.boxplot(data=plot_stats, x='Parameter', 
                        y='Sharpe GSS', hue='TAF Type', ax=ax)

    # Add vertical line separating parameter
    ax.axvline(0.5, color='white', linestyle='--', alpha=0.5)

    # Add dashed target lines, shading and text for CAA targets
    target_handles = []
    for t_type, target_vals in TARGETS.items():
        target, colour, label = target_vals
        if 'vis' in t_type: 
            handle = ax.axhline(y=target, xmin=0, xmax=0.5, linestyle='--', 
                                color=colour, alpha=0.7, label=label)
        else:
            handle = ax.axhline(y=target, xmin=0.5, xmax=1, linestyle='--', 
                                color=colour, alpha=0.7, label=label)
        target_handles.append(handle)

    # Add target lines to legend
    handles, labels = ax.get_legend_handles_labels()
    handles += target_handles
    # labels += [TARGETS[t_type][2] for t_type in TARGETS]
    ax.legend(handles=handles, labels=labels, loc='upper center', ncol=2, 
              fontsize=10, bbox_to_anchor=(1.45, 1.0))

    # Formatting, etc
    ax.set_xlabel('Parameter', weight='bold')
    ax.set_ylabel('Gerrity Skill Score', weight='bold')
    ax.tick_params(axis='x', labelsize=15)
    sns.move_legend(ax, "upper left", bbox_to_anchor=(1, 1))
    plt.setp(g_box.get_legend().get_title(), weight='bold')

    # Save and close figure
    plt.tight_layout()
    fig.savefig(f'{STATS_DIR}/g_plots/g_box_plot_{TAF_TYPES_FNAME}.png')
    plt.close()

    return t_stats


if __name__ == '__main__':

    # Get min number of matched required to ensure enough data for verification
    min_obs = calc_min_obs(START, END)

    # Run for normal scores and uncertainty-penalising scores
    main(min_obs, '')
    # main(min_obs, '_unc')

    print('Finished')