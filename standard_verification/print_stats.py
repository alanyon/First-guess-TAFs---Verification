'''Module for printing stats extracted from TAF NetCDF files'''
import os

import numpy as np
import VerPy as ver
import xarray
import pandas as pd

# Environment constants
DATA_DIR = os.environ['DATA_DIR']
PLOT_DIR = os.environ['PLOT_DIR']
TAF_TYPES = os.environ['TAF_TYPES'].split()
TAF_TYPES_SHORT = os.environ['TAF_TYPES_SHORT'].split()
TAF_TYPES_FNAME = '_'.join(TAF_TYPES_SHORT)
CYCLE_DATE = os.environ['CYCLE_DATE']

TAF_CATS = {'vis': {0: '<=300m', 1: '300-750m', 2: '800-1400m',
                    3: '1500-4900m', 4: '5000-9000m', 5: '>=10000m'},
            'clb': {0: '<=100ft', 1: '200-400ft', 2: '500-900ft',
                    3: '1000-1400ft', 4: '>=1500ft'}}


def main(param, station, start, end):
    '''Extract data, equalize and mean before printing'''
  
    # Concatenate monthly files together
    source_list = []
    for taf_type in TAF_TYPES:
        datadir = f'{DATA_DIR}/{taf_type}'
        source = os.path.join(datadir, '{}_*_{}.nc'.format(station, param))
        new_source = os.path.join(datadir, '{}_{}.nc'.format(station, param))

        dsr = xarray.open_mfdataset(source)
        dsr.to_netcdf(new_source)
        source_list.append(new_source)

    opts = {
        'jobid' : 'Extract_TAFs',
        'expids': 'MO-TAFs',
        'type'  : 'netcdf',
        'truth' : 10000,
        'source': source_list,
        'start' : start,
        'end'   : end}

    subjobs = ver.job.run('.', opts)

    cases = subjobs[0].cases

    # Fill in missing TAFs with NaNs
    for case in cases:
        dts = ver.dt.get_all_datetimes(ver.dt.Datetime(start),
                                       ver.dt.Datetime(end),
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

    gerrity_scores = {}
    peirce_scores = {}
    cts = {}

    for case, taf_type in zip(cases, TAF_TYPES):

        # Mean over all dates
        case.data.mean_all_dates()

        # Save contingency table values for plotting
        ct_vals = np.squeeze(case.data.vals)

        # Convert to DataFrame
        cats = ct_vals.shape[0]
        df_ct = pd.DataFrame(ct_vals, 
                             index=[f'FC_cat_{i+1}' for i in range(cats)],
                             columns=[f'OB_cat_{i+1}' for i in range(cats)])
        cts[taf_type] = df_ct

        # Calculate Gerrity, Peirce and Accuracy
        req_stats = [ver.stats.get_statistic(stat) for stat in [7987, 7988]]

        cat_stats = ver.stats.derived.calc_stats(case.data, req_stats)

        big_peirce, gerrity = list(cat_stats.vals.flatten())

        # Get Peirce skill scores for each category
        case.data = convert_to_1vsAll_2x2(case.data)
        req_stats = [ver.stats.get_statistic(7908)]
        peirce = ver.stats.derived.calc_stats(case.data, req_stats)
        peirce_vals = list(peirce.vals.flatten())

        gerrity_scores[taf_type] = gerrity
        peirce_scores[taf_type] = peirce_vals

    return gerrity_scores, peirce_scores, cts


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

