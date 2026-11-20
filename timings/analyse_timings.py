"""
Analyse the time taken to generate each auto TAF.

Timings are read from per-station, per-day CSV files in
${DATA_DIR}/taf_timings/<station>_<obs>/<YYYYMMDD>.csv (columns: icao, obs,
taf_start, taf_type, duration_seconds), combined into a single DataFrame and
used to create plots and summary tables in ${DATA_DIR}/timing_plots.

Usage:
    python analyse_timings.py

DATA_DIR defaults to the 20230805-20261106_test verification directory and
can be overridden with the DATA_DIR environment variable (as set by
standard_verification/setup_constants.sh).

Written by Andre Lanyon, 2026.
"""
import glob
import io
import os
from concurrent.futures import ThreadPoolExecutor

import matplotlib
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

matplotlib.use('Agg')

DATA_DIR = os.environ.get(
    'DATA_DIR',
    '/data/users/andre.lanyon/tafs/verification/20230805-20261106_test'
)
TIMINGS_DIR = os.path.join(DATA_DIR, 'taf_timings')
PLOT_DIR = os.path.join(DATA_DIR, 'timing_plots')

# Reading many small files on Lustre is latency bound, so read in parallel
N_THREADS = 32

TAF_TYPE_NAMES = {
    'p10_20_mix': 'Mix (10th/20th)',
    'p10_20_opt': 'Optimistic (10th/20th)',
    'p10_20_pes': 'Pessimistic (10th/20th)',
    'p20_30_opt': 'Optimistic (20th/30th)',
    'p20_30_pes': 'Pessimistic (20th/30th)',
    'p30_40_opt': 'Optimistic (30th/40th)',
    'p30_40_pes': 'Pessimistic (30th/40th)',
}

# TAF lengths (as in standard_verification/setup_constants.sh). EGLC has both
# a 9 hr TAF (EGLC) and a 24 hr TAF (EGLC_long). Other stations are 9 hr.
TAF_LENGTHS = {stn: '30 hr' for stn in ['EGCC', 'EGLL', 'EGKK', 'EGSS']}
TAF_LENGTHS.update({stn: '24 hr' for stn in [
    'EGAA', 'EGGP', 'EGNT', 'EGPF', 'EGNM', 'EGPD', 'EGPH', 'EGFF', 'EGNX',
    'EGBB', 'EGCN', 'EGGD', 'EGGW', 'EGPK', 'EGLC_long']})
LENGTH_ORDER = ['30 hr', '24 hr', '9 hr']
LENGTH_COLOURS = dict(zip(LENGTH_ORDER, sns.color_palette('Set1', 3)))
SEASONS = {12: 'DJF', 1: 'DJF', 2: 'DJF', 3: 'MAM', 4: 'MAM', 5: 'MAM',
           6: 'JJA', 7: 'JJA', 8: 'JJA', 9: 'SON', 10: 'SON', 11: 'SON'}
MEAN_PROPS = {'marker': 'D', 'markerfacecolor': 'white',
              'markeredgecolor': 'black', 'markersize': 5}

sns.set_theme(style='whitegrid')


def main():
    """Load timings, then create summary tables and plots."""
    os.makedirs(PLOT_DIR, exist_ok=True)
    data = load_timings()
    print(f'Loaded {len(data)} timings')

    summary_tables(data)
    plot_taf_type_stats(data)
    plot_cdf(data)
    plot_by_station(data)
    plot_station_type_heatmaps(data)
    plot_by_taf_length(data)
    plot_monthly_time_series(data)
    plot_time_of_year(data)
    plot_by_hour(data)
    plot_daily_totals(data)
    print(f'Outputs saved to {PLOT_DIR}')


def _read(fname):
    with open(fname) as fh:
        return fh.read()


def load_timings():
    """Read all timing CSVs into a single DataFrame."""
    fnames = sorted(glob.glob(os.path.join(TIMINGS_DIR, '*', '*.csv')))
    if not fnames:
        raise FileNotFoundError(f'No timing files found in {TIMINGS_DIR}')
    with ThreadPoolExecutor(N_THREADS) as executor:
        texts = list(executor.map(_read, fnames))

    # Strip headers and parse everything at once (much faster than one
    # read_csv call per file)
    header = texts[0].split('\n', 1)[0]
    body = ''.join(text.split('\n', 1)[1] for text in texts if '\n' in text)
    data = pd.read_csv(io.StringIO(f'{header}\n{body}'),
                       dtype={'icao': str, 'obs': str, 'taf_type': str,
                              'taf_start': str})
    data = data.dropna(subset=['duration_seconds'])
    data = data.rename(columns={'icao': 'station'})

    data['taf_start'] = pd.to_datetime(data['taf_start'], format='%Y%m%d%H')
    data['hour'] = data['taf_start'].dt.hour
    data['month'] = data['taf_start'].dt.month
    data['season'] = data['month'].map(SEASONS)
    data['type_name'] = data['taf_type'].map(TAF_TYPE_NAMES).fillna(
        data['taf_type'])
    data['taf_length'] = data['station'].map(TAF_LENGTHS).fillna('9 hr')
    return data


def _stats(series):
    return series.agg(['count', 'mean', 'median', lambda vals:
                       vals.quantile(0.99), 'max', 'sum']).set_axis(
        ['count', 'mean', 'median', 'p99', 'max', 'total'])


def summary_tables(data):
    """Save summary statistics and the slowest TAFs as CSV files."""
    for cols, name in [('type_name', 'taf_type'), ('station', 'station'),
                       ('taf_length', 'taf_length'), ('month', 'month'),
                       ('hour', 'start_hour'),
                       (['station', 'type_name'], 'station_taf_type')]:
        table = data.groupby(cols)['duration_seconds'].apply(_stats).unstack()
        table.round(3).to_csv(os.path.join(PLOT_DIR, f'summary_{name}.csv'))

    data.nlargest(100, 'duration_seconds').drop(
        columns=['type_name', 'season']).to_csv(
        os.path.join(PLOT_DIR, 'slowest_100_tafs.csv'), index=False)

    durations = data['duration_seconds']
    print(f'Total generation time: {durations.sum() / 3600:.1f} hours')
    print(durations.describe(percentiles=[0.5, 0.9, 0.99, 0.999]).round(3))


def _save(fig, name):
    fig.savefig(os.path.join(PLOT_DIR, name), dpi=150, bbox_inches='tight')
    plt.close(fig)


def _type_order(data):
    return [TAF_TYPE_NAMES.get(t, t) for t in sorted(data['taf_type'].unique())]


def plot_taf_type_stats(data):
    """Bar charts of mean, median, 99th percentile and max per TAF type."""
    order = _type_order(data)
    stats = (data.groupby('type_name')['duration_seconds'].apply(_stats)
             .unstack().loc[order])
    fig, axes = plt.subplots(2, 2, figsize=(16, 10), sharex=True)
    titles = {'mean': 'Mean', 'median': 'Median',
              'p99': '99th percentile', 'max': 'Maximum'}
    colours = sns.color_palette('tab10', len(order))
    for ax, (col, title) in zip(axes.flat, titles.items()):
        bars = ax.bar(order, stats[col], color=colours)
        ax.bar_label(bars, fmt='%.2f', fontsize=9)
        ax.set_title(f'{title} generation time')
        ax.set_ylabel('Seconds')
        ax.tick_params(axis='x', rotation=30)
    fig.suptitle('TAF generation time by TAF type')
    fig.tight_layout()
    _save(fig, 'taf_type_stats.png')

    fig, ax = plt.subplots(figsize=(12, 6))
    sns.boxplot(data=data, x='type_name', y='duration_seconds', order=order,
                hue='type_name', palette='tab10', showfliers=False,
                showmeans=True, meanprops=MEAN_PROPS, ax=ax)
    ax.set_xlabel('')
    ax.set_ylabel('Generation time (seconds)')
    ax.set_title('Distribution of TAF generation time by TAF type '
                 '(outliers hidden, diamonds = mean)')
    ax.tick_params(axis='x', rotation=20)
    _save(fig, 'taf_type_boxplot.png')


def plot_cdf(data):
    """Cumulative distribution of generation time per TAF type and length."""
    fig, axes = plt.subplots(1, 2, figsize=(18, 6), sharey=True)
    sns.ecdfplot(data=data, x='duration_seconds', hue='type_name',
                 hue_order=_type_order(data), palette='tab10', ax=axes[0])
    sns.ecdfplot(data=data, x='duration_seconds', hue='taf_length',
                 hue_order=LENGTH_ORDER, palette=LENGTH_COLOURS, ax=axes[1])
    for ax, title in zip(axes, ['TAF type', 'TAF length']):
        ax.set_xscale('log')
        ax.set_xlabel('Generation time (seconds, log scale)')
        ax.set_ylabel('Proportion of TAFs')
        ax.set_title(f'By {title.lower()}')
        ax.get_legend().set_title(title)
        for quant in [0.5, 0.9, 0.99]:
            ax.axhline(quant, color='grey', lw=0.8, ls='--')
    fig.suptitle('Cumulative distribution of TAF generation time')
    fig.tight_layout()
    _save(fig, 'cdf.png')


def plot_by_station(data):
    """Mean and maximum generation time per station, plus box plots."""
    stats = data.groupby('station')['duration_seconds'].apply(
        _stats).unstack().sort_values('mean', ascending=False)
    colours = stats.index.map(
        lambda stn: LENGTH_COLOURS[TAF_LENGTHS.get(stn, '9 hr')])
    handles = [plt.Rectangle((0, 0), 1, 1, color=LENGTH_COLOURS[length])
               for length in LENGTH_ORDER]

    fig, axes = plt.subplots(3, 1, figsize=(18, 14), sharex=True)
    for ax, col, title in zip(axes, ['mean', 'p99', 'max'],
                              ['Mean', '99th percentile', 'Maximum']):
        ax.bar(stats.index, stats[col], color=colours)
        ax.set_ylabel('Seconds')
        ax.set_title(f'{title} generation time')
    axes[0].legend(handles, LENGTH_ORDER, title='TAF length')
    axes[-1].tick_params(axis='x', rotation=90)
    fig.suptitle('TAF generation time by station '
                 '(all TAF types, ordered by mean)')
    fig.tight_layout()
    _save(fig, 'station_stats.png')

    fig, ax = plt.subplots(figsize=(10, 16))
    sns.boxplot(data=data, y='station', x='duration_seconds',
                order=stats.index, hue='taf_length', hue_order=LENGTH_ORDER,
                palette=LENGTH_COLOURS, dodge=False, showfliers=False,
                showmeans=True, meanprops=MEAN_PROPS, ax=ax)
    ax.set_xlabel('Generation time (seconds, outliers hidden, '
                  'diamonds = mean)')
    ax.set_ylabel('')
    ax.set_title('TAF generation time by station')
    ax.get_legend().set_title('TAF length')
    _save(fig, 'station_boxplot.png')


def plot_station_type_heatmaps(data):
    """Heatmaps of mean and max generation time per station and TAF type."""
    tables = {title: data.pivot_table(index='station', columns='type_name',
                                      values='duration_seconds',
                                      aggfunc=func)
              for title, func in [('Mean', 'mean'), ('Maximum', 'max')]}
    order = tables['Mean'].mean(axis=1).sort_values(ascending=False).index
    fig, axes = plt.subplots(1, 2, figsize=(22, 18))
    for ax, (title, table) in zip(axes, tables.items()):
        sns.heatmap(table.loc[order, _type_order(data)], annot=True,
                    fmt='.1f' if title == 'Mean' else '.0f', cmap='viridis',
                    ax=ax, cbar_kws={'label': f'{title} (seconds)'})
        ax.set_xlabel('')
        ax.set_ylabel('')
        ax.set_title(f'{title} TAF generation time (seconds)')
        ax.tick_params(axis='x', rotation=30)
    fig.tight_layout()
    _save(fig, 'heatmap_station_taf_type.png')


def plot_by_taf_length(data):
    """Generation time by TAF length, split by TAF type."""
    fig, axes = plt.subplots(1, 2, figsize=(18, 6),
                             gridspec_kw={'width_ratios': [1, 2]})
    sns.boxplot(data=data, x='taf_length', y='duration_seconds',
                order=LENGTH_ORDER, hue='taf_length', palette=LENGTH_COLOURS,
                showfliers=False, showmeans=True, meanprops=MEAN_PROPS,
                ax=axes[0])
    axes[0].set_title('Distribution (outliers hidden, diamonds = mean)')
    axes[0].set_xlabel('TAF length')
    axes[0].set_ylabel('Generation time (seconds)')

    sns.barplot(data=data, x='type_name', y='duration_seconds',
                order=_type_order(data), hue='taf_length',
                hue_order=LENGTH_ORDER, palette=LENGTH_COLOURS,
                estimator='mean', errorbar=None, ax=axes[1])
    axes[1].set_title('Mean generation time by TAF type')
    axes[1].set_xlabel('')
    axes[1].set_ylabel('Mean generation time (seconds)')
    axes[1].tick_params(axis='x', rotation=20)
    sns.move_legend(axes[1], 'upper left', bbox_to_anchor=(1, 1),
                    title='TAF length')
    fig.suptitle('TAF generation time by TAF length')
    fig.tight_layout()
    _save(fig, 'taf_length.png')


def plot_monthly_time_series(data):
    """Monthly mean and maximum generation time through the period."""
    fig, axes = plt.subplots(2, 2, figsize=(18, 10), sharex=True)
    for row, (group, order, palette) in enumerate([
            ('type_name', _type_order(data), 'tab10'),
            ('taf_length', LENGTH_ORDER, LENGTH_COLOURS)]):
        monthly = (data.set_index('taf_start')
                   .groupby([pd.Grouper(freq='MS'), group])
                   ['duration_seconds'])
        for col, (title, series) in enumerate(
                [('Mean', monthly.mean()), ('Maximum', monthly.max())]):
            ax = axes[row, col]
            sns.lineplot(data=series.rename('seconds').reset_index(),
                         x='taf_start', y='seconds', hue=group,
                         hue_order=order, palette=palette, marker='o',
                         markersize=4, ax=ax, legend=col == 1)
            ax.set_title(f'Monthly {title.lower()}')
            ax.set_xlabel('')
            ax.set_ylabel('Generation time (seconds)')
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
            ax.tick_params(axis='x', rotation=30)
        sns.move_legend(axes[row, 1], 'upper left', bbox_to_anchor=(1, 1),
                        title='TAF type' if row == 0 else 'TAF length')
    fig.suptitle('TAF generation time through the trial period')
    fig.tight_layout()
    _save(fig, 'monthly_time_series.png')


def plot_time_of_year(data):
    """Generation time by calendar month, for each TAF length."""
    month_names = pd.date_range('2000-01-01', periods=12, freq='MS').strftime(
        '%b')
    fig, axes = plt.subplots(2, 1, figsize=(16, 11), sharex=True)
    sns.boxplot(data=data, x='month', y='duration_seconds',
                hue='taf_length', hue_order=LENGTH_ORDER,
                palette=LENGTH_COLOURS, showfliers=False, showmeans=True,
                meanprops={**MEAN_PROPS, 'markersize': 4}, ax=axes[0])
    axes[0].set_title('Distribution (outliers hidden, diamonds = mean)')
    axes[0].set_ylabel('Generation time (seconds)')
    axes[0].get_legend().set_title('TAF length')

    monthly_max = data.groupby(['month', 'taf_length'])[
        'duration_seconds'].max().rename('seconds').reset_index()
    sns.barplot(data=monthly_max, x='month', y='seconds', hue='taf_length',
                hue_order=LENGTH_ORDER, palette=LENGTH_COLOURS, ax=axes[1],
                legend=False)
    axes[1].set_title('Maximum generation time')
    axes[1].set_ylabel('Generation time (seconds)')
    axes[1].set_xlabel('Month of TAF start (all years combined)')
    axes[1].set_xticks(range(12))
    axes[1].set_xticklabels(month_names)
    fig.suptitle('TAF generation time by time of year')
    fig.tight_layout()
    _save(fig, 'time_of_year.png')


def plot_by_hour(data):
    """Generation time by TAF start hour, for each TAF length."""
    fig, ax = plt.subplots(figsize=(14, 6))
    sns.boxplot(data=data, x='hour', y='duration_seconds', hue='taf_length',
                hue_order=LENGTH_ORDER, palette=LENGTH_COLOURS,
                showfliers=False, showmeans=True,
                meanprops={**MEAN_PROPS, 'markersize': 4}, ax=ax)
    ax.set_xticks(range(data['hour'].nunique()))
    ax.set_xticklabels([f'{hour:02d}Z' for hour in
                        sorted(data['hour'].unique())])
    ax.set_xlabel('TAF start hour (UTC)')
    ax.set_ylabel('Generation time (seconds, outliers hidden)')
    ax.set_title('TAF generation time by start hour (diamonds = mean)')
    ax.get_legend().set_title('TAF length')
    _save(fig, 'start_hour.png')


def plot_daily_totals(data):
    """Total generation time per day and per station cycle."""
    daily = (data.set_index('taf_start')['duration_seconds']
             .resample('D').sum(min_count=1).div(60))
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))
    ax1.plot(daily.index, daily, color='grey', lw=0.6, alpha=0.7,
             label='Daily total')
    ax1.plot(daily.index, daily.rolling(30, center=True, min_periods=15)
             .mean(), color='tab:red', lw=2, label='30-day rolling mean')
    ax1.set_ylabel('Total generation time (minutes)')
    ax1.set_title('Total daily TAF generation time '
                  '(all stations and TAF types)')
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
    ax1.legend(loc='upper right')

    # Time to generate all TAF types for one station and start time
    per_cycle = (data.groupby(['station', 'taf_start', 'taf_length'])
                 ['duration_seconds'].sum().rename('seconds').reset_index())
    sns.histplot(data=per_cycle, x='seconds', hue='taf_length',
                 hue_order=LENGTH_ORDER, palette=LENGTH_COLOURS, bins=100,
                 log_scale=(True, False), element='step', ax=ax2)
    for quant, colour in zip([0.5, 0.9, 0.99], ['k', 'tab:orange', 'r']):
        value = per_cycle['seconds'].quantile(quant)
        ax2.axvline(value, color=colour, ls='--')
        ax2.text(value, ax2.get_ylim()[1] * 0.95, f' {quant:.0%}: '
                 f'{value:.1f}s', color=colour, va='top')
    ax2.set_xlabel('Time to generate all TAF types for one station and '
                   'start time (seconds, log scale)')
    ax2.set_ylabel('Count')
    ax2.set_title('Generation time per station per cycle (all TAF types)')
    ax2.get_legend().set_title('TAF length')
    fig.tight_layout()
    _save(fig, 'daily_totals.png')


if __name__ == '__main__':
    main()
