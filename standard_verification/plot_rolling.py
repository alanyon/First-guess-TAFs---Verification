"""
Module to create line plots of rolling scores and confusion matrices for
each airport, parameter, and score type. The line plots show how the
scores have changed over time for each TAF type, while the confusion
matrices show the distribution of forecast vs observed categories for
each TAF type.

Functions:
    main: Main function to create line plots and confusion matrices.
    conf_figure: Creates a figure of confusion matrices.
    confusion_plots: Creates confusion matrix heatmaps for each ICAO.
    get_taf_type_long: Converts short TAF type names to longer names.
    line_figure: Creates a line plot of rolling scores.
    name_cols: Renames columns to be more readable for plotting.
    sample_shades: Sample distinct hex colors from a colormap.
    score_line_plots: Creates line plots of rolling scores.

Written by Andre Lanyon, 2026.
"""
import os

import matplotlib
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib import colors

DATA_DIR = os.environ['DATA_DIR']
PLOT_DIR = os.environ['PLOT_DIR']
INFO_FILE = os.environ['INFO_FILE']
SCORES = {'gerrity': 'Gerrity Skill Scores', 'peirce_0': 'Peirce Skill Scores',
          'peirce_1': 'Peirce Skill Scores', 'peirce_2': 'Peirce Skill Scores',
          'peirce_3': 'Peirce Skill Scores', 'peirce_4': 'Peirce Skill Scores',
          'peirce_5': 'Peirce Skill Scores'}
PARAMS = {'vis': 'Visibility', 'clb': 'Cloud Base'}
TAF_CATS = {'vis': {'0': '<=300m', '1': '300-750m', '2': '800-1400m',
                    '3': '1500-4900m', '4': '5000-9000m', '5': '>=10000m'},
            'clb': {'0': '<=100ft', '1': '200-400ft', '2': '500-900ft',
                    '3': '1000-1400ft', '4': '>=1500ft'}}
TYPE_ORDER = ['manual', 'pes_obs_update_2_ml', 'pes_obs_update_1_ml', 
              'pes_no_obs_ml', 'pes_obs_update_2', 'pes_obs_update_1',
              'pes_no_obs', 'opt_obs_update_2_ml', 'opt_obs_update_1_ml', 
              'opt_no_obs_ml', 'opt_obs_update_2', 'opt_obs_update_1',
              'opt_no_obs']

# Load in airport info, mapping icaos to airport names
AIRPORT_INFO = pd.read_csv(INFO_FILE, header=0)
ICAO_DICT = pd.Series(AIRPORT_INFO.airport_name.values,
                      index=AIRPORT_INFO.icao).to_dict()

# Set plotting style
sns.set_style('darkgrid')
sns.set(font_scale=1.5)

def main():
    """
    Main function to create line plots and confusion matrices.

    Args:
        None
    Returns:
        None
    """
    # Create line plots and confusion matrices
    score_line_plots()
    confusion_plots()


def conf_figure(icao, icao_file_list, param):
    """
    Creates a figure of confusion matrices for a given ICAO and
    parameter.

    Args:
        icao (str): ICAO code for the airport
        icao_file_list (list): List of csv files for ICAO and parameter
        param (str): Parameter name ('vis' or 'clb')
    Returns:
        None
    """
    # Create figure with subplots stacked vertically
    num_files = len(icao_file_list)
    fig, axes = plt.subplots(num_files, 1, figsize=(14, 5 * num_files))

    # Handle case where there's only one file
    if num_files == 1:
        axes = [axes]

    # Loop through csv files for this ICAO
    for idx, file in enumerate(icao_file_list):

        # Load contingency table values into pandas dataframe
        ct_df = pd.read_csv(os.path.join(f'{DATA_DIR}/cts', file),
                            index_col=0)

        # Add in totals for rows and columns
        ct_df.loc['Total Obs'] = ct_df.sum()
        ct_df['Total Fcsts'] = ct_df.sum(axis=1)

        # Get parameter and TAF type from filename
        taf_type = file[12: -4]

        # Create labels
        cats = ct_df.shape[0]
        fc_labels = [TAF_CATS[param][str(i)]
                     for i in range(cats - 1)] + ['Total Obs']
        ob_labels = [TAF_CATS[param][str(i)]
                     for i in range(cats - 1)] + ['Total Fcsts']

        # Create mask: True = don't colour
        mask = np.zeros_like(ct_df, dtype=bool)
        mask[-1, :] = True       # last row (Total Obs)
        mask[:, -1] = True       # last column (Total Fcsts)

        # Ensure white background for totals
        axes[idx].set_facecolor('white')

        # Plot heatmap without totals and without numbers
        sns.heatmap(ct_df, annot=False, fmt='g', cmap='Blues', cbar=False,
                    mask=mask, ax=axes[idx], xticklabels=ob_labels,
                    yticklabels=fc_labels)

        # Add numbers to each cell with contrast logic
        nrows, ncols = ct_df.shape
        for i in range(nrows):
            for j in range(ncols):
                val = ct_df.iloc[i, j]

                # Identify totals row/column
                is_total = (i == nrows - 1) or (j == ncols - 1)

                # Always black for totals
                if is_total:
                    text_color = 'black'

                # Only apply contrast logic to non-total cells
                else:
                    max_val = ct_df.iloc[:-1, :-1].values.max()
                    threshold = max_val * 0.5
                    text_color = 'white' if val > threshold else 'black'

                # Add text to cell
                axes[idx].text(j + 0.5, i + 0.5, f"{val:g}", ha='center',
                               va='center', color=text_color)

        # Labels and title
        axes[idx].set_xticklabels(axes[idx].get_xticklabels(), rotation=0)
        axes[idx].set_xlabel('Observed Category', fontsize=25, weight='bold')
        axes[idx].set_ylabel('Forecast Category', fontsize=25, weight='bold')
        taf_type_long = get_taf_type_long(taf_type)
        axes[idx].set_title(taf_type_long, fontsize=30,  weight='bold')

        # Add black border around totals row and column
        axes[idx].add_patch(plt.Rectangle((ct_df.shape[1]-1, 0), 1,
                                           ct_df.shape[0], fill=False,
                                           edgecolor='black', lw=2))
        axes[idx].add_patch(plt.Rectangle((0, ct_df.shape[0]-1),
                                          ct_df.shape[1], 1, fill=False,
                                          edgecolor='black', lw=2))

    # Save figure
    plt.tight_layout(pad=2.0)
    fig.savefig(f'{PLOT_DIR}/{icao}_{param}_confusion.png')
    plt.close()


def confusion_plots():
    """
    Creates confusion matrix heatmaps for each ICAO, parameter, and TAF
    type.

    Args:
        None
    Returns:
        None
    """
    # Get list of csv files in DATA_DIR/cts
    files = sorted(os.listdir(f'{DATA_DIR}/cts'))

    # Group files by ICAO
    icao_files = {}
    for file in files:
        icao = file.split('_')[0]
        param = file.split('_')[2]
        if icao not in icao_files:
            icao_files[icao] = {'vis': [], 'clb': []}
        icao_files[icao][param].append(file)

    # Order file lists for each ICAO by TAF type
    for icao, param_dict in icao_files.items():
        for param in param_dict:
            param_dict[param].sort(key=lambda x: TYPE_ORDER.index(x[12: -4]))

    # Loop through each ICAO and create separate figure for each
    # parameter
    for icao, icao_file_dict in icao_files.items():
        for param, icao_file_list in icao_file_dict.items():
            conf_figure(icao, icao_file_list, param)


def get_taf_type_long(short_name):
    """
    Converts short TAF type names to longer, more readable names.

    Args:
        short_name (str): Short TAF type name
    Returns:
        long_name (str): Long TAF type name
    """
    type_map = {
        'opt_no_obs': 'Optimistic Auto TAFs\n(no obs, {})',
        'opt_obs_update_1': 'Optimistic Auto TAFs\n(obs update 1, {})',
        'opt_obs_update_2': 'Optimistic Auto TAFs\n(obs update 2, {})',
        'pes_no_obs': 'Pessimistic Auto TAFs\n(no obs, {})',
        'pes_obs_update_1': 'Pessimistic Auto TAFs\n(obs update 1, {})',
        'pes_obs_update_2': 'Pessimistic Auto TAFs\n(obs update 2, {})',
        'manual': 'Manual TAFs'
    }
    # Manual TAF name straightforward
    if 'manual' in short_name:
        return type_map['manual']

    # Determine if TAF type is with or without ML
    ml_status = 'with ML' if 'ml' in short_name else 'no ML'

    # Loop through type_map to find matching key in short_name
    for key, template in type_map.items():
        if key in short_name and key != 'manual':
            return template.format(ml_status)

    # If no match found, print a warning and return None
    print(f'Column {short_name} not recognised')
    return None


def line_figure(icao, param, score_name, param_df, palette_13):
    """
    Creates a line plot of rolling scores for a given ICAO, parameter,
    and score type.

    Args:
        icao (str): ICAO code for the airport
        param (str): Parameter name ('vis' or 'clb')
        score_name (str): Score type ('gerrity', 'peirce_0, etc)
        param_df (pd.DataFrame): Dataframe containing rolling scores
        palette_13 (list): List of 13 hex color strings for plotting
    Returns:
        None
    """
    # Default plot title
    ttl = f'{ICAO_DICT[icao]} {PARAMS[param]} {SCORES[score_name]}'

    # Filter dataframe for score
    if 'peirce' in score_name:

        # Only 5 categories for cloud base
        if param == 'clb' and score_name == 'peirce_5':
            return

        # Filter dataframe for score
        score, cat = score_name.split('_')
        score_df = param_df[['Date'] + [col for col in param_df.columns
                                        if score in col]].copy()
        score_df = score_df[['Date'] + [col for col in score_df.columns
                                        if col.endswith(cat)]]
        ttl += f' (Category: {TAF_CATS[param][cat]})'
    else:
        score = score_name
        score_df = param_df[['Date'] + [col for col in param_df.columns
                                        if score in col]].copy()

    # Convert dates
    score_df['Date'] = pd.to_datetime(score_df['Date'], format='%Y%m%d')

    # Sort columns by reverse TAF type order
    old_cols = score_df.columns.tolist()
    new_cols = ['Date']
    for taf_type in reversed(TYPE_ORDER):
        for col in old_cols:
            if taf_type in col:
                if 'ml' in col and 'ml' not in taf_type:
                    continue
                new_cols.append(col)
                break
    score_df = score_df[new_cols]

    # Give nice column names for plotting
    score_df.columns = name_cols(score_df.columns)

    # Melt dataframe for plotting
    score_df = score_df.melt(id_vars='Date', var_name='TAF Type',
                             value_name='Score')

    # Create line plot
    fig, ax = plt.subplots(figsize=(16, 8))
    sns.lineplot(data=score_df, x='Date', y='Score', hue='TAF Type',
                 palette=palette_13, ax=ax)

    # Format axes, title, legend, etc
    ax.legend(loc='upper left', bbox_to_anchor=(1.03, 1), fontsize=14)
    ax.set_xlabel('Date', fontsize=22, weight='bold')
    ax.set_ylabel('Score', fontsize=22, weight='bold')
    ax.tick_params(axis='x', labelsize=15)
    ax.tick_params(axis='y', labelsize=15)
    ax.set_title(ttl, fontsize=24, weight='bold')
    dates = score_df['Date'].sort_values().unique()
    idx = np.linspace(0, len(dates) - 1, 6, dtype=int)
    ax.set_xticks(dates[idx])
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m/%Y'))

    # Save figure
    plt.tight_layout()
    plt.savefig(f'{PLOT_DIR}/{icao}_{param}_{score_name}.png')
    plt.close(fig)


def name_cols(columns):
    """
    Renames columns to be more readable for plotting.

    Args:
        columns (list): List of column names to rename
    Returns:
        new_cols (list): List of renamed column names
    """
    # Loop through columns and rename them to be more readable
    new_cols = []
    for col in columns:

        # Keep date column as is
        if col == 'Date':
            new_cols.append(col)

        # Rename other columns
        else:
            taf_type_long = get_taf_type_long(col)
            new_cols.append(taf_type_long)

    return new_cols


def sample_shades(cmap_name, n, low=0.30, high=0.95):
    """
    Sample 'n' visually distinct hex colors from a sequential colormap,
    avoiding extremes that are too dark/light.

    Args:
        cmap_name (str): Name of the colormap to sample from
        n (int): Number of colors to sample
        low (float): Lower bound for sampling (0 to 1)
        high (float): Upper bound for sampling (0 to 1)
    Returns:
        colors (list): List of hex color strings
    """
    cmap = matplotlib.colormaps[cmap_name]
    vals = np.linspace(low, high, n)
    return [colors.to_hex(cmap(v)) for v in vals]


def score_line_plots():
    """
    Creates line plots of rolling scores for each ICAO, parameter, and
    score type.

    Args:
        None
    Returns:
        None
    """
    # Build colour palette
    blues6 = sample_shades('Blues', 6, low=0.30, high=0.95)
    reds6  = sample_shades('Reds',  6, low=0.30, high=0.95)
    green1 = ['#2ca02c']
    palette_13 = blues6 + reds6 + green1

    # Loop through csv files in DATA_DIR/stats
    for file in os.listdir(f'{DATA_DIR}/stats'):

        # Get ICAO from filename
        icao = file.split('_')[0]

        # Load file into pandas dataframe
        vdf = pd.read_csv(os.path.join(f'{DATA_DIR}/stats', file))

        # Loop through parameters
        for param in PARAMS:

            # Filter dataframe for parameter
            param_df = vdf[['Date'] + [col for col in vdf.columns
                                       if param in col]]

            # Loop through scores and plot each one
            for score_name in SCORES:
                line_figure(icao, param, score_name, param_df, palette_13)


if __name__ == "__main__":
    main()
    print('Finished')
