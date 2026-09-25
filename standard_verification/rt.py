# (C) Crown copyright Met Office. All rights reserved.
# Refer to COPYRIGHT.txt of this distribution for details.
"""
rt.py
=====

This module provides functionality for analysing a single TAF against
associated METARs.

------------------------------------------------------------------------
"""

import copy
from decimal import Decimal

import numpy as np


class TAF(object):
    """
    A TAF object contains all the details of a TAF
    (like issue/start/end date/time, airport, etc).
    It also contains the details of each change group (sub-section) of the TAF
    together with how the METARs are matched to these categories.
    The METAR to TAF matching process is performed such that the forecast error
    is minimised whilst still adhering to the WMO/ICAO definition of each term.
    """

    def __init__(self, init_comp, args):
        """
        """
        self.init_comp = init_comp
        self.args = args
        self.taf_comps = []
        self.metar_comps = []

        self.issue_dt = init_comp.issue_dt
        self.issue_date = init_comp.issue_date
        self.issue_time = init_comp.issue_time
        self.issue_station = init_comp.issue_station
        self.issue_origin = init_comp.issue_origin
        self.station_id = init_comp.station_id
        self.issue_status = init_comp.issue_status
        self.parameter = init_comp.parameter
        self.start_dt = init_comp.start_dt
        self.end_dt = init_comp.end_dt
        self.len = init_comp.end_dt - init_comp.start_dt

        if self.parameter == 'VIS':
            self.cats = self.args.vis_cats
        elif self.parameter == 'CLB':
            self.cats = self.args.clb_cats
        self.probs = self.args.probbins
        # Instantiate reliability table for each category
        self.obs = np.zeros((len(self.cats), len(self.cats), len(self.probs)),
                            dtype=int)

        display_format = '{}_{:%Y%m%d}_{:04d}_{:%Y%m%d_%H%M}_{}.txt'
        self.display = display_format.format(self.station_id,
                                             self.issue_date,
                                             self.issue_time,
                                             self.start_dt,
                                             self.parameter)

    def __str__(self):
        """String summary of the TAF"""
        return '<{} TAF, issued {} for {}, {} change sets, {} METARs>'.format(
            self.parameter, self.issue_dt, self.station_id, len(self.taf_comps),
            len(self.metar_comps))

    def __contains__(self, comp):
        """Uses a Logical to determine whether comp is/isn't a TAF"""
        if comp.istaf:
            return (self.issue_dt == comp.issue_dt and
                    self.issue_station == comp.issue_station and
                    self.station_id == comp.station_id and
                    self.issue_origin == comp.issue_origin and
                    self.parameter == comp.parameter and
                    self.issue_status == comp.issue_status)

        return (self.station_id == comp.station_id and
                (self.parameter == comp.parameter or
                 self.parameter == 'VIS' and
                 comp.parameter == 'PVI') and
                self.start_dt <= comp.issue_dt <= self.end_dt)

    def get_ob_times(self):
        """List of issue datetimes of the associated METARs"""
        return (mc.issue_dt for mc in self.metar_comps)

    @property
    def sections(self):
        """
        This property is a generator for TAF sections (a period where a
        single set of rules apply).

        It yields a tuple containing:
            A list of METARComp instances
            A list of TAFComp instances
            The 'main' deterministic value
        """

        if not self.metar_comps:
            raise TAFNoMETARsError('Rejecting {}. No METARs found.'.format(self))
        else:
            metardts = [metar.issue_dt for metar in self.metar_comps]
            sorted(metardts)
            for dt1, dt2 in zip([self.start_dt] + metardts[:-1], metardts):
                if (dt2 - dt1).total_seconds() > 2.*3600.:
                    raise TAFTwoHourMETARGapError(
                        "Rejecting {} because there is a METAR gap of two hours ({}, {})" \
                        .format(self, dt1, dt2))
            if (self.end_dt - metardts[-1]).total_seconds() > 3600.:
                raise TAFNoLastHrMETARsError(
                    "Rejecting {} because the final METAR {} isn't in the last hour" \
                    .format(self, metardts[-1]))

        self.remove_duplicates()

        # Keep track of the 'main' deterministic forecast
        main = self.init_comp

        # Cycle through all METAR components
        if self.args.ver_period is not None:
            cut_off = self.start_dt + self.args.ver_period
        else:
            cut_off = None
        section_metar_comps = []
        section_start = self.init_comp.start_dt

        for i, metar_comp in enumerate(self.metar_comps):

            if cut_off and metar_comp.issue_dt > cut_off:
                break

            # Check for first METAR of section
            if not i:
                section_metar_comps = [metar_comp]
                valid_comps_prev = self.valid_taf_components(metar_comp)
                continue

            # Check if METARComp belongs to the same section
            valid_comps = self.valid_taf_components(metar_comp)
            if valid_comps == valid_comps_prev:
                section_metar_comps.append(metar_comp)

            # If not, yield the section and check for change in 'main' forecast
            # category
            else:
                # N.B. 'FM' change groups should be considered here, probably
                # before the 'yield' below
                ending_changes = [vc for vc in valid_comps_prev
                                  if vc not in valid_comps]
                starting_changes = [vc for vc in valid_comps
                                    if vc not in valid_comps_prev]
                if starting_changes:
                    change_dt = starting_changes[0].start_dt
                else:
                    change_dt = ending_changes[0].end_dt
                section_length = (change_dt -
                                  section_start).total_seconds() / 3600
                yield (section_metar_comps, valid_comps_prev, main,
                       section_length)
                # Prevent the main forecast category being changes to the BECMG
                # category when another change group starts/ends during it
                for valid_comp in valid_comps_prev:
                    if (valid_comp.change_type == 'BECMG' and
                            valid_comp.end_dt == change_dt):
                        main = valid_comp
                section_metar_comps = [metar_comp]
                section_start = change_dt
                valid_comps_prev = valid_comps[:]

        # Yield final section
        if section_metar_comps:
            change_dt = self.end_dt
            section_length = (change_dt - section_start).total_seconds() / 3600
            yield section_metar_comps, valid_comps_prev, main, section_length

    def valid_taf_components(self, metar_comp):
        """
        Determines which TAFComps are valid for a given observation
        (METARComp).
        """
        valid_components = []
        for taf_comp in self.taf_comps:
            if taf_comp.start_dt <= metar_comp.issue_dt <= taf_comp.end_dt:
                valid_components.append(taf_comp)
        return valid_components

    def remove_duplicates(self):
        """
        Remove duplicate METARs with MANL prioritised over AUTO in DB extraction
        """
        metars_ = []
        for metar in self.metar_comps:
            for metar_ in metars_:
                if metar.issue_dt == metar_.issue_dt and \
                        metar.station_id == metar_.station_id and \
                        metar.parameter == metar_.parameter:
                    print("Using METAR issued {} {}, rather than {} {}.".format(
                        metar_.issue_dt, metar_.issue_origin,
                        metar.issue_dt, metar.issue_origin))
                    break
            else:
                metars_.append(metar)
        self.metar_comps = metars_

    def construct_rt(self, display_file, raw_tafs, args):
        """
        Use the METAR/TAF component matches to create a multi-category reliability table.
        Also output the matches to display_file so that they can be visualised
        by seperate python plotting code
        """
        if self.len != args.ver_period:
            print('self', self)
            print('self.len', args.ver_period)
            raise TAFWrongLengthError( \
                      'Rejecting {}. Wrong length of {}, should be {}.' \
                      .format(self, self.len, args.ver_period))

        # Only output the raw TAF if it can be found
        rawtaf_txt = ""
        for raw_taf in raw_tafs:
            if self.init_comp.start_dt == raw_taf.start_dt:
                rawtaf_txt = raw_taf.taf
                break

        taf_comp = self.init_comp

        # Cycle through each section of the TAF matching to METARs
        for metar_comps, taf_comps, main, section_length in self.sections:

            metar_comps, taf_comps = match_section(metar_comps, taf_comps, main,
                                                   self.args.metars_per_hour*section_length)

            metar_comps.sort(key=lambda x: x.issue_dt)
            for metar_comp in metar_comps:
                # If not matched with 100% prob, match remaining prob to main fc
                if metar_comp.prob < 1.:
                    metar_comp.match.append((main.cat, 1.-metar_comp.prob))

                # Populate RTs
                fc_cats, fc_probs = zip(*metar_comp.match)
                fc_cats = '/'.join([str(cat+1) for cat in fc_cats])
                fc_probs = '/'.join([str(int(prob*100))  for prob in fc_probs])
                # print(metar_comp.issue_dt, metar_comp.val, fc_cats, fc_probs, file=display_file)
                for fc_cat, prob in metar_comp.match:
                    try:
                        prob_ind = self.probs.index(prob)
                    except ValueError as e:
                        print(e)
                        msg = 'Rejecting {}. Unknown probability {}.'.format(self, prob)
                        raise TAFTooComplexError(msg)
                    self.obs[fc_cat, metar_comp.cat, prob_ind] += 1
                fc_cats, _ = zip(*metar_comp.match)
                for i, cat in enumerate(self.cats):
                    if i not in fc_cats:
                        self.obs[i, metar_comp.cat, 0] += 1


    def add_taf_comp(self, taf_comp):
        """
        Appends a TAF component from the database to the list associated
        with this TAF
        """
        self.taf_comps.append(taf_comp)

    def add_metar_comp(self, metar_comp):
        """
        Appends a METAR component from the database to the list associated
        with this TAF
        """
        self.metar_comps.append(metar_comp)


def match_pair(metar_comp, taf_comp, main, min_metar, max_metar,
               force_match=True):
    """
    Match one METAR to one TAF component
    """
    if taf_comp.matched_metars >= taf_comp.max_matches:
        return False
    if metar_comp.prob >= 1:
        return False
    if taf_comp in metar_comp.matched_groups:
        return False

    # Is TAF comp above or below main category?
    taf_comp_below_main = main.cat > taf_comp.cat
    taf_comp_above_main = taf_comp.cat > main.cat

    if taf_comp.req_matches_in_section == 1 and \
       taf_comp.exact_matched_metars == 0 and \
       taf_comp.remaining_metars == 0:
        # If METARs go up to the end of the TAF comp period
        # must ensure at least 1 is matched to TAF comp category
        fc_cat = taf_comp.cat
    elif metar_comp.cat >= taf_comp.cat and metar_comp == min_metar and \
         taf_comp.exact_matched_metars == 0 and \
         taf_comp.remaining_metars == 0:
        # Match METAR to TAF comp if it's the minimum METAR, lies above or in
        # the TAF comp category and an exact match is needed in this section
        fc_cat = taf_comp.cat
    elif metar_comp.cat <= taf_comp.cat and metar_comp == max_metar and \
         taf_comp.exact_matched_metars == 0 and \
         taf_comp.remaining_metars == 0:
        # Match METAR to TAF comp if it's the maximum METAR, lies below or in
        # the TAF comp category and an exact match is needed in this section
        fc_cat = taf_comp.cat
    elif (metar_comp.cat - taf_comp.cat) * (metar_comp.cat - main.cat) < 0:
        # If the METAR lies between TAF comp and main forecast
        # match it to the intermediate category it's in
        fc_cat = metar_comp.cat
    elif taf_comp_below_main and metar_comp.cat >= main.cat and force_match:
        # The METAR lies above the forecast range but
        # part (or all) of it must be matched to TAF comp
        # so match it to its nearest intermediate category
        fc_cat = main.cat-1
    elif taf_comp_above_main and metar_comp.cat <= main.cat and force_match:
        # The METAR lies below the forecast range but
        # part (or all) of it must be matched to TAF comp
        # so match it to its nearest intermediate category
        fc_cat = main.cat+1
    elif force_match:
        # Match this METAR to the alternative category if part (or all)
        # must be matched
        fc_cat = taf_comp.cat
    elif abs(metar_comp.cat - taf_comp.cat) < abs(metar_comp.cat - main.cat):
        # Match this METAR to the alternative category if it is a closer
        # match than the main category
        fc_cat = taf_comp.cat
    else:
        # Don't match the METAR
        return False

    matched_prob = taf_comp.prob
    if metar_comp.prob + matched_prob > 1.0:
        matched_prob = 1. - metar_comp.prob
    if matched_prob > 0:
        metar_comp.matched_groups.append(taf_comp)
        metar_comp.match.append((fc_cat, matched_prob))
        metar_comp.prob += matched_prob
        taf_comp.matched_metars += 1
        taf_comp.req_matches_in_section = taf_comp.min_matches - \
                                          taf_comp.matched_metars - \
                                          taf_comp.remaining_metars
        if taf_comp.cat == fc_cat:
            taf_comp.exact_matched_metars += 1
        return True

    return False

def match_section(metar_comps, taf_comps, main, metars_in_section):
    """
    Match the METARs to the TAF change group categories as closely as the
    WMO/ICAO definitions of the used change group terms allow.
    """
    if not metar_comps:
        return metar_comps, taf_comps

    # METARs have been used by previous TAFs so reset attributes
    for metar_comp in metar_comps:
        metar_comp.matched_groups = []
        metar_comp.match = []
        metar_comp.prob = 0.

    last_dt = max(mc.issue_dt for mc in metar_comps)
    first_dt = min(mc.issue_dt for mc in metar_comps)

    # Sort METARs and set max and min
    metar_comps.sort(key=lambda x: (x.value, x.issue_dt))
    min_metar = metar_comps[0]
    max_metar = metar_comps[-1]
    # If all METARs have the same value then use the first one for both min and max
    if min_metar.value == max_metar.value:
        max_metar = min_metar

    if not taf_comps:
        return metar_comps, taf_comps

    # Update attributes of TAF components for new section
    for taf_comp in taf_comps:
        taf_comp.remaining_metars -= metars_in_section
        taf_comp.req_matches_in_section = taf_comp.min_matches - \
                                          taf_comp.matched_metars - \
                                          taf_comp.remaining_metars

    # Create a copy of the main forecast component and reset attributes
    # as though this component only exists for the length of the section
    main_for_this_section = copy.copy(main)
    main_for_this_section.max_matches = metars_in_section
    main_for_this_section.remaining_metars = 0
    main_for_this_section.matched_metars = 0
    main_for_this_section.min_matches = 0
    main_for_this_section.req_matches_in_section = main_for_this_section.min_matches

    # Order components by prob and insert main fc for this section at beginning of list
    taf_comps.sort(key=lambda x: x.prob)
    taf_comps.insert(0, main_for_this_section)

    taf_comps_to_match = []
    for taf_comp in taf_comps:
        if taf_comp.req_matches_in_section >= len(metar_comps):
            for metar_comp in metar_comps:
                matched = match_pair(metar_comp, taf_comp, main, min_metar, max_metar)
        else:
            taf_comps_to_match.append(taf_comp)

    if len(taf_comps_to_match) <= 1:
        return metar_comps, taf_comps

    taf_comps_to_match.sort(key=lambda x: x.value)
    min_taf_comp = taf_comps_to_match[0]
    max_taf_comp = taf_comps_to_match[-1]

    # Sort METAR components by value (ascending) and date
    metar_comps.sort(key=lambda x: (x.value, x.issue_dt))
    for metar_comp in metar_comps:
        if min_taf_comp.req_matches_in_section > 0:
            if metar_comp.value < min_taf_comp.value:
                matched = match_pair(metar_comp, min_taf_comp, main, min_metar, max_metar)

    # Sort METAR components by value (descending) and date.
    metar_comps.sort(key=lambda x: (-x.value, x.issue_dt))
    for metar_comp in metar_comps:
        if max_taf_comp.req_matches_in_section > 0:
            if metar_comp.value > max_taf_comp.value:
                matched = match_pair(metar_comp, max_taf_comp, main, min_metar, max_metar)

    # Go though the next section twice, first for probabilities < 100%
    # then for 100% probabilities. Order of matching:
    #     1. Meet minium requirements for each component
    #     2. Match METARs below min comp to min comp (not exceeding max matches)
    #     3. Match METARs above max comp to max comp (not exceeding max matches)
    #     4. Match METARs to components with the same category (not exceeding max matches)

    for prob_limit in [0.5, 1.0]:

        for taf_comp in taf_comps_to_match:
            if taf_comp.prob > prob_limit:
                continue
            # Match closest METARs to each group (Sort METARs by difference from TAF comp)
            valdiffs = [abs(mc.value - taf_comp.value) for mc in metar_comps]
            catdiffs = [abs(mc.cat - taf_comp.cat) for mc in metar_comps]
            metar_comps = [mc for _, _, mc in sorted(zip(catdiffs, valdiffs, metar_comps),
                                                     key=lambda x: (x[0], x[1]))]
            for metar_comp in metar_comps:
                if taf_comp.req_matches_in_section > 0 or \
                   (taf_comp.min_matches > 0 and taf_comp.exact_matched_metars == 0 and
                    taf_comp.remaining_metars == 0):
                    matched = match_pair(metar_comp, taf_comp, main, min_metar, max_metar)

        if min_taf_comp.prob <= prob_limit:
            # Sort METARs by value (ascending) and date
            metar_comps.sort(key=lambda x: (x.value, x.issue_dt))
            for metar_comp in metar_comps:
                if metar_comp.value < min_taf_comp.value:
                    matched = match_pair(metar_comp, min_taf_comp, main, min_metar, max_metar)

        if max_taf_comp.prob <= prob_limit:
            # Sort METARs by value (descending) and date
            metar_comps.sort(key=lambda x: (-x.value, x.issue_dt))
            for metar_comp in metar_comps:
                if metar_comp.value > max_taf_comp.value:
                    matched = match_pair(metar_comp, max_taf_comp, main, min_metar, max_metar)

        msg = 'Matching METARs which are an exact match to {} {} ' \
              '(closest first)'.format(taf_comp.change_type, taf_comp.val)
        for taf_comp in taf_comps_to_match:
            if taf_comp.prob > prob_limit:
                continue

            exact_metar_comps = [mc for mc in metar_comps if mc.cat == taf_comp.cat]
            diffs = [abs(mc.value - taf_comp.value) for mc in exact_metar_comps]
            exact_metar_comps = [mc for _, mc in sorted(zip(diffs, exact_metar_comps),
                                                        key=lambda x: (x[0]))]
            for metar_comp in exact_metar_comps:
                matched = match_pair(metar_comp, taf_comp, main, min_metar, max_metar)

    # Match any remaining METARs
    if main_for_this_section == min_taf_comp:
        msg = 'Matching remaining METARs starting with highest value'
        # Sort METARs and TAF comps in descending order
        metar_comps.sort(key=lambda x: (-x.value, x.issue_dt))
        taf_comps_to_match.sort(key=lambda x: -x.value)
    else:
        msg = 'Matching remaining METARs starting with lowest value'
        # Sort METARs and TAF comps in ascending order
        metar_comps.sort(key=lambda x: (x.value, x.issue_dt))
        taf_comps_to_match.sort(key=lambda x: x.value)

    for metar_comp in metar_comps:
        for taf_comp in taf_comps_to_match:
            matched = match_pair(metar_comp, taf_comp, main, min_metar, max_metar,
                                 force_match=False)

    return metar_comps, taf_comps

class TAFTooComplexError(Exception):
    pass

class TAFNoMETARsError(Exception):
    pass

class TAFWrongLengthError(Exception):
    pass

class TAFNoLastHrMETARsError(Exception):
    pass

class TAFTwoHourMETARGapError(Exception):
    pass
