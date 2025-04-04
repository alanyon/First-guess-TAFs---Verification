# (C) Crown copyright Met Office. All rights reserved.
# Refer to COPYRIGHT.txt of this distribution for details.
"""
extract.py
==========

This module provides functions for extracting TAFs and METARs from the
database.

------------------------------------------------------------------------
"""
import datetime
from decimal import Decimal

import numpy as np
import sqlalchemy as sql
import sqlalchemy.ext.declarative as dec
import sqlalchemy.ext.hybrid as hyb


def extract(args):
    """
    Extract TAF and METAR components from the database.
    """
    for attempt in range(0, 10):
        try:
            if args.taf_connection_string.startswith('oracle'):
                echo = 'debug' if args.sql_debug else False
            else:
                echo = args.sql_debug
            taf_engine  = sql.create_engine(args.taf_connection_string, echo=echo)

            taf_session = sql.orm.sessionmaker(bind=taf_engine)()

            metar_engine  = sql.create_engine(args.metar_connection_string,
                                                echo='debug' if args.sql_debug else False)
            metar_session = sql.orm.sessionmaker(bind=metar_engine)()

            # Get all required TAFs
            taf_comps = get_taf_comps(taf_engine, taf_session, args)

            # Get all required METARs
            metar_comps = get_metar_comps(metar_engine, metar_session, args)

            raw_tafs = get_raw_taf(taf_engine, taf_session, args)

            return taf_comps, metar_comps, raw_tafs

        except sql.exc.DatabaseError as e:
            print(e.args[0] + 'Retrying...')

    raise Exception('Failed to connect to database')


def get_taf_comps(engine, session, args):
    """
    Extract TAF components from the database.
    """
    Base = dec.declarative_base()
    metadata = sql.MetaData(bind=engine)

    class TAFComp(Base):
        """
        TAF component class, contains all the components of a TAF:
        - issue/start/end datetime (.issue_dt .start_dt .end_dt)
        - TAF length in hours (.length)
        - the numerical forecast values (.val)
        - the category the forecast value lies within (.cat)
        - the probabilty associated with the forecast value (.prob)
        - the maximum number of METARs that can be matched to the
          forecast category (.max_matches)
        """
        istaf = True
        kwargs = {'autoload':True, 'autoload_with':engine}
        if args.taf_connection_string.startswith('oracle'):
            kwargs['schema']=args.table_schema
        __table__ = sql.Table(args.taf_table, metadata, **kwargs)

        @hyb.hybrid_property
        def issue_dt(self):
            """Combine and return the TAF issue date and time"""
            return combine_date_and_time(self.issue_date, self.issue_time)

        @hyb.hybrid_property
        def start_dt(self):
            """Combine and return the TAF start date and time"""
            return combine_date_and_time(self.start_date, self.start_time)

        @hyb.hybrid_property
        def end_dt(self):
            """Combine and return the TAF end date and time"""
            return combine_date_and_time(self.end_date, self.end_time)

        @hyb.hybrid_property
        def length(self):
            """Return the TAF length in hours"""
            delta = self.end_dt - self.start_dt
            return delta.total_seconds()/3600.

        @hyb.hybrid_property
        def val(self):
            """Convert cloud base to feet and define infinite values"""
            if self.isinf:
                return float('inf')
            if self.parameter == 'CLB':
                return np.around(float(self.value) / args.ft_to_m, -1)
            return float(self.value)

        @property
        def prob(self):
            """Return the probability associated with a change group category"""
            if self.change_type in ['INIT', 'FM', 'TEMPO', 'BECMG']:
                return 1.0
            elif self.change_type.startswith('PROB30'):
                return 0.3
            elif self.change_type.startswith('PROB40'):
                return 0.4
            raise ValueError('Change type "{}" not known.'
                             .format(self.change_type))

        @hyb.hybrid_property
        def cat(self):
            """Add the visibility or cloudbase value to an object"""
            if self.parameter == 'VIS':
                return args.vis_cats.index(self.val)
            if self.parameter == 'CLB':
                return args.clb_cats.index(self.val)
            raise ValueError('"{}" is not a valid variable'.format(self.parameter))

        @hyb.hybrid_property
        def isinf(self):
            """Check value against infinite values used in database"""
            if self.parameter == 'VIS' or 'PVI':
                return self.value == 9999
            if self.parameter == 'CLB':
                return self.value == 3047
            raise ValueError('"{}" is not a valid variable'.format(self.parameter))

    # Extract every TAF between 0000Z on start_dt and 0000Z on end_dt
    start_date = args.start_dt.replace(microsecond=0, second=0, minute=0, hour=0)
    end_dt = args.end_dt + datetime.timedelta(days=args.extract_lookahead)
    end_date = end_dt.replace(microsecond=0, second=0, minute=0, hour=0)
    query = session.query(TAFComp)
    query = query.filter(TAFComp.start_date >= start_date)   \
                 .filter(TAFComp.start_date <= end_date)          \
                 .filter(TAFComp.station_id.in_(args.sitelist)) \
                 .filter(TAFComp.issue_station == 'EGRR') \
                 .filter(TAFComp.parameter.in_(('VIS', 'CLB')))
    query = query.order_by(TAFComp.issue_date)
    query = query.order_by(TAFComp.issue_time)
    query = query.order_by(TAFComp.start_date)
    query = query.order_by(TAFComp.start_time)
    query = query.order_by(TAFComp.end_date)
    query = query.order_by(TAFComp.end_time)
    query = query.order_by(TAFComp.change_type)
    query = query.order_by(TAFComp.parameter)

    comps = query.all()

    # Initialise number of matched metars and metars still available to match
    for comp in comps:
        comp.value = Decimal(comp.value)
        comp.matched_metars = 0
        comp.exact_matched_metars = 0
        comp.remaining_metars = args.metars_per_hour*comp.length
        if comp.change_type in ['INIT', 'FM']:
            comp.min_matches = 0
        elif comp.change_type.endswith('TEMPO'):
            comp.min_matches = 1
        elif comp.change_type == 'BECMG':
            comp.min_matches = 1
        elif comp.change_type.startswith('PROB'):
            comp.min_matches = args.metars_per_hour*comp.length
        comp.max_matches = args.metars_per_hour*comp.length
        if comp.change_type.endswith('TEMPO'):
            comp.max_matches /= 2.0

    return comps


def get_raw_taf(engine, session, args):
    """
    Extract the raw TAF from the database.
    """
    Base = dec.declarative_base()
    metadata = sql.MetaData(bind=engine)

    class RawTAF(Base):
        """
        Raw TAF class, contains the raw TAF text as issued by the
        Aviation Op. Met.
        """
        istaf = True
        kwargs = {'autoload':True, 'autoload_with':engine}
        if args.taf_connection_string.startswith('oracle'):
            kwargs['schema']=args.table_schema
        __table__ = sql.Table(args.rawtaf_table, metadata, **kwargs)

        @hyb.hybrid_property
        def start_dt(self):
            """Combine and return the TAF start date and time"""
            return combine_date_and_time(self.start_date, self.start_time)

    start_date = args.start_dt.replace(microsecond=0, second=0, minute=0, hour=0)
    end_dt = args.end_dt + datetime.timedelta(days=args.extract_lookahead)
    end_date = end_dt.replace(microsecond=0, second=0, minute=0, hour=0)
    query = session.query(RawTAF)
    query = query.filter(RawTAF.start_date >= start_date)   \
                 .filter(RawTAF.start_date <= end_date)          \
                 .filter(RawTAF.station_id.in_(args.sitelist)) \
                 .filter(RawTAF.issue_station == 'EGRR')
    query = query.order_by(RawTAF.issue_date)
    query = query.order_by(RawTAF.issue_time)

    rawtafs = query.all()
    for t in rawtafs: t.taf=t.taf[t.taf.find(args.sitelist[0]):]

    return rawtafs

def get_metar_comps(engine, session, args):
    """
    Extract METAR components from the database.
    """
    Base = dec.declarative_base()
    metadata = sql.MetaData(bind=engine)
    class METARComp(Base):
        """
        METAR component class, contains all the components of a METAR:
        - issue datetime (.issue_dt)
        - value (.val)
        - category it lies in (.cat)
        """
        istaf = False
        __table__ = sql.Table(args.metar_table, metadata,
                              schema=args.table_schema, autoload=True,
                              autoload_with=engine)

        def __str__(self):
            return '<{} @ {}, {}: {}>'.format(self.parameter, self.issue_dt,
                    self.station_id, self.val)

        @hyb.hybrid_property
        def issue_dt(self):
            """Issue datetime of METAR"""
            return combine_date_and_time(self.issue_date, self.issue_time)

        @hyb.hybrid_property
        def val(self):
            """Convert cloud base to feet and define infinite values"""
            if self.isinf:
                return float('inf')
            if self.parameter == 'CLB':
                return np.around(float(self.value) / args.ft_to_m, -1)
            return float(self.value)

        @hyb.hybrid_property
        def cat(self):
            """Add the visibility or cloudbase value to an object"""
            if self.parameter == 'PVI':
                return args.vis_cats.index(self.val)
            elif self.parameter == 'CLB':
                return args.clb_cats.index(self.val)
            raise ValueError('"{}" is not a valid variable'.format(self.parameter))

        @hyb.hybrid_property
        def isinf(self):
            """Check value against infinite values used in database"""
            if self.parameter == 'VIS' or 'PVI':
                return self.value == 9999
            if self.parameter == 'CLB':
                return self.value == 3047
            raise ValueError('"{}" is not a valid variable'.format(self.parameter))

    start_date = args.start_dt.replace(microsecond=0, second=0, minute=0, hour=0)
    end_dt = args.end_dt + datetime.timedelta(days=args.extract_lookahead)
    end_date = end_dt.replace(microsecond=0, second=0, minute=0, hour=0)
    query = session.query(METARComp)
    query = query.filter(METARComp.issue_date >= start_date)   \
                 .filter(METARComp.issue_date <= end_date)          \
                 .filter(METARComp.station_id.in_(args.sitelist)) \
                 .filter(METARComp.parameter.in_(('PVI', 'CLB')))

    if args.use_autometars and not args.use_specis:
        query = query.filter(METARComp.issue_origin.in_(('AUTO', 'MANL')))
    elif args.use_specis and not args.use_autometars:
        query = query.filter(METARComp.issue_origin.in_(('SPEC', 'MANL')))
    elif not args.use_specis and not args.use_autometars:
        query = query.filter(METARComp.issue_origin == 'MANL')

    query = query.order_by(METARComp.issue_date)
    query = query.order_by(METARComp.issue_time)
    query = query.order_by(sql.desc(METARComp.issue_origin))
    mcs = query.all()

    return mcs


def combine_date_and_time(date, time):
    """
    Returns a datetime instance using the year, month and day from the
    given `date` argument and assuming the `time` argument is of the
    form HHMM.
    """
    return datetime.datetime(date.year, date.month, date.day,
                             time // 100, time % 100)
