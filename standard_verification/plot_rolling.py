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
import json
import os
from datetime import datetime, timezone

import matplotlib
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib import colors
from matplotlib.lines import Line2D

DATA_DIR = os.environ['DATA_DIR']
CACHE_DIR = os.path.join(DATA_DIR, 'rolling_36m_autotaf')
PLOT_DIR = os.environ['PLOT_DIR']
INFO_FILE = os.environ['INFO_FILE']
SCORES = {'gerrity': 'Gerrity Skill Score',
          'peirce_0': 'Peirce Skill Score',
          'peirce_1': 'Peirce Skill Score',
          'peirce_2': 'Peirce Skill Score',
          'peirce_3': 'Peirce Skill Score',
          'peirce_4': 'Peirce Skill Score',
          'peirce_5': 'Peirce Skill Score'}
PARAMS = {'vis': 'Visibility', 'clb': 'Cloud Base'}
TAF_CATS = {'vis': {'0': '<=300m', '1': '300-750m', '2': '800-1400m',
                    '3': '1500-4900m', '4': '5000-9000m', '5': '>=10000m'},
            'clb': {'0': '<=100ft', '1': '200-400ft', '2': '500-900ft',
                    '3': '1000-1400ft', '4': '>=1500ft'}}
TYPE_ORDER = ['autotaf', 'manual']
CAA_TARGETS = {
    9: {'vis': 0.408, 'clb': 0.521},
    24: {'vis': 0.357, 'clb': 0.467},
    30: {'vis': 0.366, 'clb': 0.458}}
CAA_AIRPORT_GROUPS = {
    '9h_north': {
        'hours': 9, 'label': '9-hour North',
        'airports': ('EGAC', 'EGAE', 'EGNS', 'EGNV', 'EGPA', 'EGPB',
                     'EGPE', 'EGPO')},
    '24h_north': {
        'hours': 24, 'label': '24-hour North',
        'airports': ('EGAA', 'EGNM', 'EGNT', 'EGPD', 'EGPF', 'EGPH',
                     'EGPK')},
    '9h_south': {
        'hours': 9, 'label': '9-hour South',
        'airports': ('EGHH', 'EGHI', 'EGHQ', 'EGMC', 'EGNJ', 'EGSH',
                     'EGTE', 'EGLC')},
    '24h_south': {
        'hours': 24, 'label': '24-hour South',
        'airports': ('EGBB', 'EGGD', 'EGFF', 'EGGP', 'EGGW', 'EGNX')},
    '30h_south': {
        'hours': 30, 'label': '30-hour South',
        'airports': ('EGCC', 'EGKK', 'EGLL', 'EGSS')}}
CAA_MEDIAN_EXCLUSIONS = {9: {'EGNS'}}
HOUR_COLORS = {9: '#7b7f00', 24: '#263b83', 30: '#e87800'}

# Load verifiable airport info, mapping ICAOs to display names.
AIRPORT_INFO = pd.read_csv(INFO_FILE, header=0)
AIRPORT_INFO = AIRPORT_INFO[
    (AIRPORT_INFO['bench'] != 'defence')
    & (AIRPORT_INFO['airport_name'] != 'London City (long)')]
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
    # Create per-airport and TAF-length group scores, then confusion matrices.
    histories = load_score_histories()
    score_line_plots(histories)
    group_score_plots(histories)
    median_score_plots(histories)
    confusion_plots()
    write_manifest()


def conf_figure(icao, icao_file_list, param, normalize=True):
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
    if not icao_file_list:
        return

    files_by_type = {
        file.rsplit('_', 1)[-1][:-4]: file for file in icao_file_list}
    taf_types = [taf_type for taf_type in TYPE_ORDER
                 if taf_type in files_by_type]
    if not taf_types:
        return

    matrices = {}
    for taf_type in taf_types:
        matrix = pd.read_csv(
            os.path.join(CACHE_DIR, 'cts', files_by_type[taf_type]),
            index_col=0).to_numpy(dtype=float)
        matrices[taf_type] = np.nan_to_num(matrix)
    count_max = max(matrix.max(initial=0) for matrix in matrices.values())

    fig, axes = plt.subplots(
        1, len(taf_types), figsize=(7.2 * len(taf_types), 8),
        squeeze=False)
    for ax, taf_type in zip(axes[0], taf_types):
        counts = matrices[taf_type]
        if normalize:
            observed_totals = counts.sum(axis=0)
            values = np.divide(
                counts * 100, observed_totals,
                out=np.zeros_like(counts), where=observed_totals != 0)
            annotations = True
            vmax = 100
            colorbar_label = 'Cases within observed category (%)'
            number_format = '.0f'
        else:
            values = counts
            annotations = np.vectorize(format_count)(values)
            vmax = max(1, count_max)
            colorbar_label = 'Cases'
            number_format = ''
        category_labels = [TAF_CATS[param][str(i)]
                           for i in range(counts.shape[0])]
        sns.heatmap(
            values, annot=annotations, fmt=number_format,
            annot_kws={'fontsize': 9}, cmap='YlGnBu', vmin=0,
            vmax=vmax, linewidths=0.5, linecolor='white', square=True, ax=ax,
            xticklabels=category_labels, yticklabels=category_labels,
            cbar_kws={'label': colorbar_label})
        ax.set_xlabel('Observed category')
        ax.set_ylabel('Forecast category')
        ax.set_title(get_taf_type_long(taf_type), weight='bold')
        ax.tick_params(axis='x', labelrotation=30)
        ax.tick_params(axis='y', labelrotation=0)

    fig.suptitle(f'{ICAO_DICT.get(icao, icao)} ({icao}) | {PARAMS[param]}',
                 x=0.06, ha='left', weight='bold', fontsize=17)
    caption = ('Each observed-category column is normalized to 100%.'
               if normalize else
               'Counts use k=1,000 and M=1,000,000; probability-weighted values may be fractional.')
    fig.text(0.5, 0.025, caption, ha='center', color='#52616b')
    fig.tight_layout(rect=(0, 0.13, 1, 0.93))
    suffix = 'confusion' if normalize else 'confusion_counts'
    fig.savefig(os.path.join(PLOT_DIR, f'{icao}_{param}_{suffix}.png'),
                dpi=160)
    plt.close(fig)


def format_count(value):
    value = float(value)
    if abs(value) >= 1_000_000:
        return f'{value / 1_000_000:.1f}M'.replace('.0M', 'M')
    if abs(value) >= 1_000:
        return f'{value / 1_000:.1f}k'.replace('.0k', 'k')
    if value.is_integer():
        return f'{value:,.0f}'
    return f'{value:,.1f}'


def confusion_plots():
    """
    Creates confusion matrix heatmaps for each ICAO, parameter, and TAF
    type.

    Args:
        None
    Returns:
        None
    """
    # Plot only the current comparison, not legacy TAF type outputs.
    files = sorted(file for file in os.listdir(f'{CACHE_DIR}/cts')
                   if file.endswith(('_autotaf.csv', '_manual.csv')))

    # Group files by ICAO
    icao_files = {}
    for file in files:
        icao = file.split('_')[0]
        param = file.split('_')[2]
        if icao not in icao_files:
            icao_files[icao] = {'vis': [], 'clb': []}
        icao_files[icao][param].append(file)

    # Loop through each ICAO and create separate figure for each
    # parameter
    for icao, icao_file_dict in icao_files.items():
        for param, icao_file_list in icao_file_dict.items():
            conf_figure(icao, icao_file_list, param, normalize=True)
            conf_figure(icao, icao_file_list, param, normalize=False)


def get_taf_type_long(short_name):
    """
    Converts short TAF type names to longer, more readable names.

    Args:
        short_name (str): Short TAF type name
    Returns:
        long_name (str): Long TAF type name
    """
    type_map = {
        'autotaf': 'AUTOTAF',
        'opt_no_obs': 'Optimistic Auto TAFs\n(no obs, {})',
        'opt_obs_update_1': 'Optimistic Auto TAFs\n(obs update 1, {})',
        'opt_obs_update_2': 'Optimistic Auto TAFs\n(obs update 2, {})',
        'pes_no_obs': 'Pessimistic Auto TAFs\n(no obs, {})',
        'pes_obs_update_1': 'Pessimistic Auto TAFs\n(obs update 1, {})',
        'pes_obs_update_2': 'Pessimistic Auto TAFs\n(obs update 2, {})',
        'manual': 'Manual TAFs'
    }
    if 'autotaf' in short_name:
        return type_map['autotaf']

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

    # No TAF type columns matched for this param/score combination, or
    # there are no rows at all; skip rather than crash on an empty frame
    if score_df.columns.tolist() == ['Date'] or score_df.empty:
        print(f'No data for {icao} {param} {score_name}, skipping plot')
        return

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


SOURCE_STYLES = {
    'autotaf': {'color': '#007F86', 'linestyle': '-',
                'marker': 'o', 'markersize': 3},
    'manual': {'color': '#D55E00', 'linestyle': '--',
               'marker': 'D', 'markersize': 4}
}
GROUPS = {9: '9h', 24: '24h', 30: '30h'}


def last_non_null(values):
    valid = values.dropna()
    return valid.iloc[-1] if not valid.empty else np.nan


def read_score_history(path):
    scores = pd.read_csv(path)
    if scores['Date'].duplicated().any():
        value_columns = [column for column in scores.columns if column != 'Date']
        scores = scores.groupby('Date', sort=True, as_index=False).agg(
            {column: last_non_null for column in value_columns})
    scores['Date'] = pd.to_datetime(scores['Date'], format='%Y%m%d')
    return scores.sort_values('Date')


def load_score_histories():
    histories = {}
    stats_dir = os.path.join(CACHE_DIR, 'stats')
    for file in sorted(os.listdir(stats_dir)):
        if not file.endswith('_scores.csv'):
            continue
        icao = file[:-len('_scores.csv')]
        if icao in ICAO_DICT:
            histories[icao] = read_score_history(os.path.join(stats_dir, file))
    return histories


def score_line_plots(histories):
    os.makedirs(PLOT_DIR, exist_ok=True)
    for icao, scores in histories.items():
        for param in PARAMS:
            skill_figures(icao, param, scores)


def skill_figures(icao, param, scores):
    """Create Gerrity and all-category Peirce figures for one station."""
    gerrity_columns = [f'gerrity_{param}_{taf_type}'
                       for taf_type in TYPE_ORDER
                       if f'gerrity_{param}_{taf_type}' in scores]
    hours = int(AIRPORT_INFO.loc[AIRPORT_INFO.icao == icao,
                                 'taf_len'].iloc[0])
    target = CAA_TARGETS.get(hours, {}).get(param)
    if gerrity_columns:
        fig, ax = plt.subplots(figsize=(12, 6.5))
        for taf_type in TYPE_ORDER:
            column = f'gerrity_{param}_{taf_type}'
            if column in scores:
                ax.plot(scores['Date'], scores[column], linewidth=2,
                        label=get_taf_type_long(taf_type),
                        **SOURCE_STYLES[taf_type])
        ax.set_title('Gerrity Skill Score', loc='left', weight='bold')
        targets = [] if target is None else [target]
        format_skill_axis(ax, [scores[column] for column in gerrity_columns],
                          targets)
        if target is not None:
            ax.axhline(target, color='#687780', linestyle=':', linewidth=1.5,
                       label=f'CAA target ({target:.3f})')
        ax.legend(title='Forecast source / target', frameon=False,
                  loc='upper left', bbox_to_anchor=(1.02, 1))
        fig.suptitle(f'{ICAO_DICT[icao]} ({icao}) | {PARAMS[param]}',
                     x=0.08, ha='left', weight='bold', fontsize=17)
        fig.tight_layout(rect=(0, 0, 0.78, 0.92))
        fig.savefig(os.path.join(PLOT_DIR, f'{icao}_{param}_gerrity.png'),
                    dpi=160)
        plt.close(fig)

    categories = list(TAF_CATS[param].items())
    columns = 2
    rows = (len(categories) + columns - 1) // columns
    fig, axes = plt.subplots(rows, columns, figsize=(14, 4 * rows),
                             sharex=True, sharey=False, squeeze=False)
    for ax, (category, label) in zip(axes.flat, categories):
        category_index = int(category)
        score_columns = [f'peirce_{param}_{taf_type}_{category_index}'
                         for taf_type in TYPE_ORDER
                         if f'peirce_{param}_{taf_type}_{category_index}'
                         in scores]
        has_values = any(scores[column].notna().any()
                 for column in score_columns)
        if not has_values:
            ax.text(0.5, 0.5, 'No valid scores in this window',
                transform=ax.transAxes, ha='center', va='center',
                color='#687780')
        for taf_type in TYPE_ORDER:
            score_column = f'peirce_{param}_{taf_type}_{category_index}'
            if score_column in scores:
                ax.plot(scores['Date'], scores[score_column], linewidth=1.8,
                        label=get_taf_type_long(taf_type),
                        **SOURCE_STYLES[taf_type])
                valid_scores = scores[['Date', score_column]].dropna()
                if not valid_scores.empty:
                    latest = valid_scores.iloc[-1]
                    ax.annotate(
                        f'{latest[score_column]:+.3f}',
                        xy=(latest['Date'], latest[score_column]),
                        xytext=(6, 0), textcoords='offset points',
                        color=SOURCE_STYLES[taf_type]['color'],
                        fontsize=8, va='center', clip_on=False)
        ax.margins(x=0.18)
        ax.set_title(f'Category {category_index + 1}: {label}',
                     loc='left', weight='bold')
        format_skill_axis(ax, [scores[column] for column in score_columns])
    for ax in list(axes.flat)[len(categories):]:
        ax.set_visible(False)
    legend_handles = [
        Line2D([0], [0], label=get_taf_type_long(taf_type),
               **SOURCE_STYLES[taf_type], linewidth=2)
        for taf_type in TYPE_ORDER]
    fig.legend(handles=legend_handles, title='Forecast source', frameon=False,
               loc='center left', bbox_to_anchor=(0.81, 0.5))
    fig.suptitle(f'{ICAO_DICT[icao]} ({icao}) | {PARAMS[param]} Peirce Skill',
                 x=0.08, ha='left', weight='bold', fontsize=17)
    fig.tight_layout(rect=(0, 0, 0.8, 0.93))
    fig.savefig(os.path.join(PLOT_DIR, f'{icao}_{param}_peirce.png'), dpi=160)
    plt.close(fig)


def format_skill_axis(ax, score_columns, reference_values=()):
    values = pd.concat(
        [*score_columns, pd.Series(reference_values, dtype=float)],
        ignore_index=True).dropna()
    if values.empty:
        lower, upper = -1.05, 1.05
    else:
        minimum, maximum = values.min(), values.max()
        padding = max((maximum - minimum) * 0.2, 0.015)
        lower = max(-1, minimum - padding)
        upper = min(1, maximum + padding)
        if upper - lower < 0.04:
            midpoint = (upper + lower) / 2
            lower, upper = max(-1, midpoint - 0.02), min(1, midpoint + 0.02)
    ax.set_ylim(lower, upper)
    if lower <= 0 <= upper:
        ax.axhline(0, color='#687780', linewidth=1, linestyle='--')
    ax.set_ylabel('Skill score')
    ax.set_xlabel('Verification window end date')
    ax.grid(axis='y', color='#d7e0e2', linewidth=0.8)
    ax.spines[['top', 'right']].set_visible(False)
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=6))
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))


def plot_group_series(ax, histories, station_codes, param, metric,
                      station_colors, category=None):
    score_columns = []
    for icao in station_codes:
        scores = histories[icao]
        for taf_type in TYPE_ORDER:
            suffix = '' if category is None else f'_{category}'
            column = f'{metric}_{param}_{taf_type}{suffix}'
            if column not in scores or not scores[column].notna().any():
                continue
            ax.plot(
                scores['Date'], scores[column],
                color=station_colors[icao][taf_type],
                linestyle=SOURCE_STYLES[taf_type]['linestyle'],
                linewidth=0.9 if taf_type == 'autotaf' else 1.1,
                marker='.' if taf_type == 'autotaf' else 'D',
                markersize=2.5 if taf_type == 'autotaf' else 3.5,
                alpha=0.78)
            score_columns.append(scores[column])
    return score_columns


def add_group_legends(fig, station_codes, station_colors, target=None):
    source_handles = [
        Line2D([0], [0], color='#3f4d53',
               linestyle=SOURCE_STYLES[taf_type]['linestyle'], linewidth=2,
               label=get_taf_type_long(taf_type))
        for taf_type in TYPE_ORDER]
    if target is not None:
        source_handles.append(Line2D(
            [0], [0], color='#687780', linestyle=':', linewidth=2,
            label=f'CAA target ({target:.3f})'))
    source_legend = fig.legend(
        handles=source_handles,
        title='Source style / target' if target is not None else 'Source style',
        frameon=False,
        loc='upper left', bbox_to_anchor=(0.81, 0.9))
    fig.add_artist(source_legend)
    for taf_type, x_anchor in (('autotaf', 0.02), ('manual', 0.40)):
        style = SOURCE_STYLES[taf_type]
        handles = [
            Line2D([0], [0], color=station_colors[icao][taf_type],
                   linestyle=style['linestyle'], marker=style['marker'],
                   markersize=4, linewidth=2, label=icao)
            for icao in station_codes]
        legend = fig.legend(
            handles=handles, title=get_taf_type_long(taf_type),
            frameon=False, loc='lower left',
            bbox_to_anchor=(x_anchor, 0.005), ncol=3, fontsize=8)
        fig.add_artist(legend)


def group_score_plots(histories):
    station_groups = [
        (hours, group_code, f'{hours}-hour TAF',
         [icao for icao in histories
          if int(AIRPORT_INFO.loc[AIRPORT_INFO.icao == icao,
                                  'taf_len'].iloc[0]) == hours])
        for hours, group_code in GROUPS.items()]
    for group_code, group in CAA_AIRPORT_GROUPS.items():
        hours = group['hours']
        stations = [
            icao for icao in group['airports']
            if icao in histories and icao in ICAO_DICT
            and int(AIRPORT_INFO.loc[AIRPORT_INFO.icao == icao,
                                     'taf_len'].iloc[0]) == hours]
        station_groups.append((hours, f'caa_{group_code}', group['label'],
                               stations))

    for hours, group_code, group_label, stations in station_groups:
        if not stations:
            continue
        group_title = f'{group_label} airports (n={len(stations)})'
        blues = sample_shades('Blues', len(stations), low=0.35)
        reds = sample_shades('Reds', len(stations), low=0.35)
        station_colors = {icao: {'autotaf': blue, 'manual': red}
                          for icao, blue, red in zip(stations, blues, reds)}
        legend_rows = (len(stations) + 2) // 3
        legend_bottom = min(0.38, max(0.16, 0.04 * legend_rows + 0.04))
        for param in PARAMS:
            fig, ax = plt.subplots(figsize=(14, 8 + 0.24 * legend_rows))
            score_columns = plot_group_series(
                ax, histories, stations, param, 'gerrity', station_colors)
            if score_columns:
                target = CAA_TARGETS[hours][param]
                ax.set_title('Gerrity Skill Score by airport', loc='left',
                             weight='bold')
                format_skill_axis(ax, score_columns, [target])
                ax.axhline(target, color='#687780', linestyle=':',
                           linewidth=1.5)
                add_group_legends(fig, stations, station_colors, target)
                fig.suptitle(f'{group_title} | {PARAMS[param]}', x=0.08,
                             ha='left', weight='bold', fontsize=17)
                fig.tight_layout(rect=(0, legend_bottom, 0.78, 0.92))
                fig.savefig(os.path.join(
                    PLOT_DIR, f'group_{group_code}_{param}_gerrity.png'),
                    dpi=160)
            plt.close(fig)

            categories = list(TAF_CATS[param].items())
            ncols = 2
            nrows = (len(categories) + ncols - 1) // ncols
            fig, axes = plt.subplots(nrows, ncols,
                                     figsize=(15, 3.8 * nrows +
                                              0.24 * legend_rows),
                                     sharex=True, sharey=False, squeeze=False)
            has_data = False
            for ax, (category, label) in zip(axes.flat, categories):
                score_columns = plot_group_series(
                    ax, histories, stations, param, 'peirce', station_colors,
                    category=int(category))
                ax.set_title(f'Category {int(category) + 1}: {label}',
                             loc='left', weight='bold')
                if not score_columns:
                    ax.text(0.5, 0.5, 'No valid scores in this group',
                            transform=ax.transAxes, ha='center', va='center',
                            color='#687780')
                    continue
                has_data = True
                format_skill_axis(ax, score_columns)
            for ax in list(axes.flat)[len(categories):]:
                ax.set_visible(False)
            if has_data:
                add_group_legends(fig, stations, station_colors)
                fig.suptitle(f'{group_title} | {PARAMS[param]} Peirce Skill',
                             x=0.08, ha='left', weight='bold', fontsize=17)
                fig.tight_layout(rect=(0, legend_bottom, 0.78, 0.93))
                fig.savefig(os.path.join(
                    PLOT_DIR, f'group_{group_code}_{param}_peirce.png'),
                    dpi=160)
            plt.close(fig)


def median_score_plots(histories):
    """Plot rolling medians for the CAA airport groups and their targets."""
    os.makedirs(PLOT_DIR, exist_ok=True)
    for param in PARAMS:
        fig, ax = plt.subplots(figsize=(14, 7))
        median_columns = []
        target_values = []

        for hours in GROUPS:
            station_codes = sorted({
                icao for group in CAA_AIRPORT_GROUPS.values()
                if group['hours'] == hours
                for icao in group['airports']
                if icao not in CAA_MEDIAN_EXCLUSIONS.get(hours, set())
                and icao in histories and icao in ICAO_DICT
                and int(AIRPORT_INFO.loc[AIRPORT_INFO.icao == icao,
                                         'taf_len'].iloc[0]) == hours})
            length_columns = []
            for taf_type in TYPE_ORDER:
                column = f'gerrity_{param}_{taf_type}'
                station_scores = [
                    histories[icao].set_index('Date')[column].rename(icao)
                    for icao in station_codes
                    if column in histories[icao]
                    and histories[icao][column].notna().any()]
                if not station_scores:
                    continue
                median = pd.concat(station_scores, axis=1).median(axis=1)
                median = median.dropna().sort_index()
                if median.empty:
                    continue
                label = f'Median {hours}-hour {get_taf_type_long(taf_type)}'
                ax.plot(
                    median.index, median.values, color=HOUR_COLORS[hours],
                    linestyle=SOURCE_STYLES[taf_type]['linestyle'],
                    marker=SOURCE_STYLES[taf_type]['marker'], markersize=3,
                    linewidth=2, label=label)
                median_columns.append(median)
                length_columns.append(median)

            if length_columns:
                target = CAA_TARGETS[hours][param]
                ax.axhline(
                    target, color=HOUR_COLORS[hours], linestyle=':',
                    linewidth=1.5,
                    label=f'{hours}-hour CAA target ({target:.3f})')
                target_values.append(target)

        if not median_columns:
            plt.close(fig)
            continue
        format_skill_axis(ax, median_columns, target_values)
        ax.legend(title='Median scores / CAA targets', frameon=False,
                  loc='upper left', bbox_to_anchor=(1.02, 1), fontsize=9)
        fig.suptitle(f'CAA Airport Median Gerrity Skill Score | '
                     f'{PARAMS[param]}', x=0.08, ha='left', weight='bold',
                     fontsize=17)
        fig.tight_layout(rect=(0, 0, 0.76, 0.92))
        fig.savefig(os.path.join(
            PLOT_DIR, f'median_{param}_gerrity.png'), dpi=160)
        plt.close(fig)


def write_manifest():
    """Publish the station list and rolling window used by the plots."""
    cycle_date = os.environ.get('CYCLE_DATE')
    window = {}
    if cycle_date:
        window_end = pd.Timestamp(cycle_date) - pd.Timedelta(days=1)
        window_start = window_end - pd.DateOffset(years=3)
        window = {
            'window_start': window_start.strftime('%Y-%m-%d'),
            'window_end': window_end.strftime('%Y-%m-%d')}

    station_codes = sorted(
        file[:-len('_scores.csv')]
        for file in os.listdir(os.path.join(CACHE_DIR, 'stats'))
        if file.endswith('_scores.csv')
        and file[:-len('_scores.csv')] in ICAO_DICT)
    manifest = {
        'generated_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        **window,
        'stations': [
            {'icao': icao, 'name': ICAO_DICT[icao]}
            for icao in station_codes]}

    os.makedirs(PLOT_DIR, exist_ok=True)
    path = os.path.join(PLOT_DIR, 'rolling_ver_plots.json')
    temporary_path = f'{path}.tmp'
    with open(temporary_path, 'w', encoding='utf-8') as manifest_file:
        json.dump(manifest, manifest_file)
    os.replace(temporary_path, path)


if __name__ == "__main__":
    main()
    print('Finished')
