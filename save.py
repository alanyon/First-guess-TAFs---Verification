# (C) Crown copyright Met Office. All rights reserved.
# Refer to COPYRIGHT.txt of this distribution for details.
"""
save.py
=======

This module provides functionality for converting results to VerPy Data
instances and saving in NetCDF format.

------------------------------------------------------------------------
"""

import copy

import numpy
from VerPy import case, data, dt, netcdf, options, parameter, station, stats


def save(tafs, args, uncertainty=False):
    """
    Create two data instances and save them to disk.
    """

    # Construct vis and clb data instances
    vis_data = None
    clb_data = None
    for taf in tafs:
        dat = to_data(taf, uncertainty)
        if taf.parameter == 'VIS':
            if vis_data is None:
                vis_data = dat
            else:
                try:
                    vis_data.concatenate(dat)
                except data.DataError:
                    print('Unable to add ', dat.summary(10))
        else:
            if clb_data is None:
                clb_data = dat
            else:
                try:
                    clb_data.concatenate(dat)
                except:
                    print('Unable to add ', dat.summary(10))

    # Create required cases
    opts = options.Options({'expids': 'MO-TAFs', 'truth': 10000, 'system': 'TAF'})
    writer = netcdf.NetCDF()

    if vis_data is None or clb_data is None:
        print('No data to save')
        return

    # Create required cases
    vis_case = case.Case(opts=opts, data=vis_data)
    clb_case = case.Case(opts=opts, data=clb_data)

    # Save cases
    if uncertainty:
        writer.write(args.verpy_vis_uncertainty_out, [vis_case],
                     overwrite=False)
        writer.write(args.verpy_clb_uncertainty_out, [clb_case],
                     overwrite=False)
    else:
        writer.write(args.verpy_vis_out, [vis_case], overwrite=False)
        writer.write(args.verpy_clb_out, [clb_case], overwrite=False)

def to_data(taf, uncertainty):
    """
    Generates a VerPy Data instance representing this TAF's RT.
    """

    # Get VerPy attributes
    stat  = stats.get_statistic(7925)
    param = parameter.get_parameter('vis' if taf.parameter == 'VIS'
                                        else 'cbh|5.0')
    date  = dt.Datetime(taf.start_dt)
    site  = station.StationDict(name=taf.station_id)
    cats  = [str(cat) for cat in taf.cats]

    # Get empty Data instance
    if uncertainty:
        probbins = list(taf.probs_uncertainty)
    else:
        probbins = list(taf.probs)
    dat = data.Data(stats=[stat], params=[param], dates=[date],
                        ob_cats=cats, fc_cats=cats, stations=[site],
                        probbins=probbins, nan_vals=True)

    # Confirm that assumed dimension order matches that of data instance
    assert (dat.dims.index('fc_cats') <
            dat.dims.index('ob_cats') <
            dat.dims.index('probbins'))

    # Reshape the value array to include parameters, etc.
    if uncertainty:
        dat.vals = taf.obs_uncertainty.reshape(dat.vals.shape)
    else:
        dat.vals = taf.obs.reshape(dat.vals.shape)

    return rel_table_to_con_table(dat)

def rel_table_to_con_table(dat):
    """
    Converts multi-cat reliability table to mulit-cat contingency table by
    mutliplying vals by probs.
    """

    con_table = copy.deepcopy(dat)
    setattr(con_table, 'probbins', None)
    con_table.dims = con_table.get_dimensions()
    # Make probs broadcastable to vals shape
    axis = dat.get_val_axis('probbins')
    probs = stats.derived._create_prob_bins(dat.vals.shape, axis, dat.probbins)
    con_table.vals = numpy.nansum(dat.vals*probs, axis=axis)

    return con_table
