'''Module for printing stats extracted from TAF NetCDF files'''
import csv
import glob
import os
import sys

import numpy as np
import VerPy as ver
import xarray

# Environment constants
STATS_DIR = os.environ['STATS_DIR']
DATA_DIR = os.environ['DATA_DIR']
TAF_TYPES = os.environ['TAF_TYPES'].split()
VERIF_START = os.environ['VERIF_START']
VERIF_END = os.environ['VERIF_END']


def print_ct(con_table):
    '''Pretty print contingency table'''
    cats = con_table.shape[0]

    line = '='*10 + ' ' + '='*((cats+1)*13)

    # Determine total FCs and forecast and observed frequencies
    total_fcs = con_table.sum(axis=1)
    total_obs = con_table.sum(axis=0)
    total_all = con_table.sum()
    fcs_freqs = total_fcs / total_all
    obs_freqs = total_obs / total_all
    # Header
    print(line)
    print(' ' * 11 + ''.join([f'OB cat {i+1}     ' for i in range(cats)]) +
          'Total')
    print(line)

    # Rows
    for i in range(cats):
        print(f'FC cat {i + 1}   ' +
              ''.join([f'{val:<13}' for val in np.round(con_table[i], 2)]) +
              f'{np.round(total_fcs[i]):<13}')

    # Totals
    print(line)
    print('Total      ' +
          ''.join([f'{val:<13}' for val in np.round(total_obs, 2)]) +
          f'{np.round(total_all):<13}')
    print(line)

    return fcs_freqs, obs_freqs

def main(param, station, unc):
    '''Extract data, equalize and mean before printing'''

    # Concatenate monthly files together
    source_list = []
    for taf_type in TAF_TYPES:
        datadir = f'{DATA_DIR}/{taf_type}'
        source = os.path.join(datadir, '{}_*_{}{}.nc'.format(station,
                                                             param.lower(),
                                                             unc))
        new_source = os.path.join(datadir, '{}_{}.nc'.format(station,
                                                             param.lower(),
                                                             unc))

        dsr = xarray.open_mfdataset(source)
        dsr.to_netcdf(new_source)
        source_list.append(new_source)

    opts = {
        'jobid' : 'Extract_TAFs',
        'expids': 'MO-TAFs',
        'type'  : 'netcdf',
        'truth' : 10000,
        'source': source_list,
        'start' : VERIF_START,
        'end'   : VERIF_END}

    subjobs = ver.job.run('.', opts)

    cases = subjobs[0].cases

    # Fill in missing TAFs with NaNs
    for case in cases:
        dts = ver.dt.get_all_datetimes(ver.dt.Datetime(VERIF_START),
                                       ver.dt.Datetime(VERIF_END),
                                       range(0, 2400, 100))
        if not np.all(dts == case.data.dates):
            # Find missing datetimes
            old_dts = case.data.dates
            axis = case.data.get_val_axis('dates')
            for i, d in enumerate(dts):
                if d not in old_dts:
                    case.data.vals = np.insert(case.data.vals, i, np.nan, axis)
            # Update the instance's dates
            case.data.dates = dts

    # Equalize
    cases = ver.data.equalize(cases)

    for case, taf_type in zip(cases, TAF_TYPES):

        print('')
        print('TAF type: ', taf_type)
        print('Station is ', station)
        print('Param is ', param.lower())
        print('')

        # Mean over all dates
        case.data.mean_all_dates()

        # Print table
        ct_vals = np.squeeze(case.data.vals)
        fcs_freqs, obs_freqs = print_ct(ct_vals)

        # Calculate Gerrity, Peirce and Accuracy
        req_stats = [ver.stats.get_statistic(stat) for stat in [7987, 7988]]

        cat_stats = ver.stats.derived.calc_stats(case.data, req_stats)

        big_peirce, gerrity = list(cat_stats.vals.flatten())

        print('')
        print('Gerrity score is ', np.round(gerrity, 2))
        print('Big peirce score is ', np.round(big_peirce, 2))

        # Get Peirce skill scores for each category
        case.data = convert_to_1vsAll_2x2(case.data)
        req_stats = [ver.stats.get_statistic(7908)]
        peirce = ver.stats.derived.calc_stats(case.data, req_stats)
        peirce_vals = list(peirce.vals.flatten())
        print('Small peirce scores are ', np.round(peirce_vals, 2))
        print('Mean small peirce score is', np.round(np.mean(peirce_vals), 2))

        # Lists for csv file
        gerrity_scores = [station, 'gerrity', taf_type, gerrity]
        big_peirce_scores = [station, 'big_peirce', taf_type, big_peirce]
        peirce_scores = [station, 'peirce', taf_type] + peirce_vals
        freqs = ([station, 'freqs', taf_type] +
                 [fcs_freq for fcs_freq in fcs_freqs] +
                 [obs_freq for obs_freq in obs_freqs])
        ct_vals_list = ([station, 'ctvals', taf_type] +
                        [val for val in ct_vals.flatten('F')])

        # Write stats to csv file
        stats_file = '{}/{}_stats{}.csv'.format(STATS_DIR, param.lower(), unc)
        open_stats_file = open(stats_file, 'a')
        with open_stats_file:

            writer = csv.writer(open_stats_file)
            writer.writerows([gerrity_scores, big_peirce_scores, peirce_scores,
                              freqs, ct_vals_list])


def convert_to_1vsAll_2x2(dat):
    """
    Function to convert nxn contingency tables to 2x2 contingency tables.
    """
    index = [list(range(x)) for x in dat.vals.shape]
    ob_axis = dat.get_val_axis('ob_cats')
    fc_axis = dat.get_val_axis('fc_cats')
    stat_axis = dat.get_val_axis('stats')
    new_vals = []
    new_thresh = []
    nthresh = len(dat.ob_cats)
    for j, cat in enumerate(dat.ob_cats):
        # Hits
        index[ob_axis] = [j]
        index[fc_axis] = [j]
        hits = np.nansum(dat.vals[np.ix_(*index)],
                            axis=(ob_axis, fc_axis), keepdims=True)
        # False Alarms
        index[ob_axis] = [x for x in range(nthresh) if x != j]
        index[fc_axis] = [j]
        false_alarms = np.nansum(dat.vals[np.ix_(*index)],
                                    axis=(ob_axis, fc_axis), keepdims=True)
        # Misses
        index[ob_axis] = [j]
        index[fc_axis] = [x for x in range(nthresh) if x != j]
        misses = np.nansum(dat.vals[np.ix_(*index)],
                              axis=(ob_axis, fc_axis), keepdims=True)
        # Correct Rejections
        index[ob_axis] = [x for x in range(nthresh) if x != j]
        index[fc_axis] = [x for x in range(nthresh) if x != j]
        correct_rej = np.nansum(dat.vals[np.ix_(*index)],
                                   axis=(ob_axis, fc_axis), keepdims=True)

        con2x2 = np.concatenate([hits, false_alarms, misses, correct_rej],
                                   axis=stat_axis)
        new_vals.append(np.squeeze(con2x2, axis=(ob_axis, fc_axis)))
        new_thresh.append(cat)

    dat.ob_cats = None
    dat.fc_cats = None
    dat.thresh = new_thresh
    dat.dims = dat.get_dimensions()
    thresh_axis = dat.get_val_axis('thresh')
    statclass = dat.stats[0]['class']['code']
    dat.stats = [ver.stats.get_statistic(statclass*1000 + i)
                 for i in (921, 922, 923, 924)]
    dat.vals = np.stack(new_vals, axis=thresh_axis)

    return dat


if __name__ == '__main__':

    station = sys.argv[1]
    for param in ['VIS', 'CLB']:
        main(param, station, '')
        # main(param, station, '_unc')
