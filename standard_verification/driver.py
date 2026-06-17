# (C) Crown copyright Met Office. All rights reserved.
# Refer to COPYRIGHT.txt of this distribution for details.
"""
driver.py
=========

This module provides the argument parser and main function for
analysing a sample of TAFs.
"""

import argparse
import configparser
import datetime

import extract
import numpy as np
import rt
import save


class Problist(list):
    def index(self, prob):
        for i, p in enumerate(self):
            if abs(p - prob) < 0.001:
                return i
        raise ValueError('{} is not in list'.format(prob))


class Category(object):
    def __init__(self, lbound, ubound):
        self.lbound = lbound
        self.ubound = ubound

    def __eq__(self, val):
        if np.isinf(val) and np.isinf(self.ubound):
            return True
        return self.lbound <= val < self.ubound

    def __contains__(self, val):
        return self == val

    def __str__(self):
        if np.isfinite(self.ubound):
            return "{} <= x < {}".format(self.lbound, self.ubound)
        return "x >= {}".format(self.lbound)

    def __repr__(self):
        return "<Category: {}>".format(self)

    @classmethod
    def from_thresh(cls, thresh):
        cats = []
        for i in range(len(thresh) + 1):
            if i == 0:
                lbound = 0
            else:
                lbound = thresh[i - 1]
            if i == len(thresh):
                ubound = float('inf')
            else:
                ubound = thresh[i]
            cats.append(cls(lbound, ubound))
        return cats


def get_arguments():
    parser = argparse.ArgumentParser(description='Script to form multi-'
                                     'category reliability tables for TAFs')

    parser.add_argument('start_dt', metavar='start_date_time', type=
                        lambda x: datetime.datetime.strptime(x, '%Y%m%d%H%M'))
    parser.add_argument('end_dt', metavar='end_date_time', type=
                        lambda x: datetime.datetime.strptime(x, '%Y%m%d%H%M'))
    parser.add_argument('sitelist', metavar='station', type=lambda x: [x])
    parser.add_argument('ver_period', metavar='ver_period',
                        type=lambda x: datetime.timedelta(hours=int(x)))
    parser.add_argument('verpy_vis_out', metavar='verpy_vis_out')
    parser.add_argument('verpy_clb_out', metavar='verpy_clb_out')
    parser.add_argument('config_file', metavar='config_file')

    args = parser.parse_args()
    config = configparser.ConfigParser()
    config.read(args.config_file)
    defaults = dict(config.items("defaults"))

    evalelements = ('extract_lookahead', 'sql_debug', 'vis_cats', 'clb_cats',
                    'ft_to_m', 'use_autometars', 'use_specis', 'probbins',
                    'metars_per_hour')

    for elem in defaults:
        if elem in evalelements:
            defaults[elem] = eval(defaults[elem])

    parser.set_defaults(**defaults)
    return parser.parse_args()


def match_components(args, taf_comps, metar_comps):
    tafs = []
    taf_comps_ = []
    for taf_comp in taf_comps:
        if taf_comp.change_type == 'INIT' and \
                args.start_dt <= taf_comp.start_dt <= args.end_dt and \
                taf_comp.start_dt >= taf_comp.issue_dt:
            tafs.append(rt.TAF(taf_comp, args))
        else:
            taf_comps_.append(taf_comp)
    taf_comps = taf_comps_

    tafs.sort(key=lambda x: x.issue_dt, reverse=True)
    tafs_ = []
    for taf in tafs:
        for taf_ in tafs_:
            if taf.start_dt == taf_.start_dt and \
                    taf.station_id == taf_.station_id and \
                    taf.parameter == taf_.parameter:
                if taf.station_id == 'EGLC':
                    if taf_.len >= taf.len:
                        print(f'Using longer TAF')
                        break
                else:
                    print(f'Using TAF issued {taf_.issue_dt}, '
                          f'rather than {taf.issue_dt}.')
                    break
        else:
            tafs_.append(taf)
    tafs = tafs_
    tafs.sort(key=lambda x: x.start_dt)

    for taf_comp in taf_comps:
        for taf in tafs:
            if taf_comp in taf:
                taf.add_taf_comp(taf_comp)
                break

    metar_comps.sort(key=lambda x: x.issue_dt)
    start_index = 0
    for taf in tafs:
        for metar_comp in metar_comps[start_index:]:
            if metar_comp in taf:
                taf.add_metar_comp(metar_comp)
            elif metar_comp.issue_dt < taf.start_dt:
                start_index += 1
            elif metar_comp.issue_dt > taf.end_dt:
                break

    return tafs


def main(args):
    taf_comps, metar_comps, raw_tafs = extract.extract(args)
    tafs = match_components(args, taf_comps, metar_comps)

    tafs_ = []
    failed = []
    for taf in tafs:
        try:
            taf.construct_rt(None, raw_tafs, args)
            tafs_.append(taf)
            print('Accepted: {}'.format(taf))
        except (rt.TAFTooComplexError, rt.TAFNoMETARsError,
                rt.TAFWrongLengthError, rt.TAFNoLastHrMETARsError,
                rt.TAFTwoHourMETARGapError) as err:
            print(err)
            print('Rejected: {}'.format(taf))
            failed.append(taf)

    tafs = tafs_
    save.save(tafs, args)

    print('{} TAFs processed, {} TAFs ignored'.format(len(tafs), len(failed)))
    print('Finished')


# NEW FUNCTION: call main from another script
def main_from_params(start_dt, end_dt, sitelist, ver_period,
                     verpy_vis_out, verpy_clb_out, config_file):
    args = argparse.Namespace(
        start_dt=start_dt,
        end_dt=end_dt,
        sitelist=sitelist,
        ver_period=ver_period,
        verpy_vis_out=verpy_vis_out,
        verpy_clb_out=verpy_clb_out,
        config_file=config_file
    )

    # replicate config handling
    config = configparser.ConfigParser()
    config.read(config_file)
    defaults = dict(config.items("defaults"))

    evalelements = ('extract_lookahead', 'sql_debug', 'vis_cats', 'clb_cats',
                    'ft_to_m', 'use_autometars', 'use_specis', 'probbins',
                    'metars_per_hour')

    for elem in defaults:
        if elem in evalelements:
            defaults[elem] = eval(defaults[elem])

    for key, val in defaults.items():
        setattr(args, key, val)

    return main(args)


if __name__ == '__main__':
    ARGS = get_arguments()
    main(ARGS)
