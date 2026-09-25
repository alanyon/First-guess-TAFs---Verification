'''Merge per-station stats CSVs into the combined CSVs used for plotting.

Each station job writes its stats to ``${STATS_DIR}/per_station/`` in its
own file. This script concatenates those files into the single combined
CSVs that ``plot_stats.py`` expects. It is run once, serially, after all
station jobs have finished, so there is never a simultaneous write to the
combined files.
'''
import glob
import os

# Environment constants
STATS_DIR = os.environ['STATS_DIR']
TAF_TYPES_SHORT = os.environ['TAF_TYPES_SHORT'].split()
TAF_TYPES_FNAME = '_'.join(TAF_TYPES_SHORT)
PER_STATION_DIR = os.path.join(STATS_DIR, 'per_station')


def merge(param):
    '''Concatenate all per-station CSVs for a parameter into one file.'''
    pattern = os.path.join(
        PER_STATION_DIR, f'*_{param}_stats_{TAF_TYPES_FNAME}.csv')
    files = sorted(glob.glob(pattern))

    out_file = os.path.join(
        STATS_DIR, f'{param}_stats_{TAF_TYPES_FNAME}.csv')

    # Open in write mode to overwrite any file from a previous run.
    with open(out_file, 'w', encoding='utf-8') as out:
        for fname in files:
            with open(fname, encoding='utf-8') as src:
                out.write(src.read())

    print(f'Merged {len(files)} per-station files into {out_file}')


if __name__ == '__main__':
    for param in ['vis', 'clb']:
        merge(param)
