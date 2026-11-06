"""
Module containing constants for use in other scripts.
"""
from datetime import datetime, timedelta
from dateutil.rrule import DAILY, rrule
import csv
import os
import json

# Import environment variables
D_DIR = os.environ['DATA_DIR']
# Period-specific outputs (pickles, plots, spreadsheets)
OUT_DIR = os.environ.get('OUT_DIR', D_DIR)
# Verification setup (standard / ml / fog); used to keep each setup's output
# filenames distinct so runs don't overwrite one another
PROFILE = os.environ.get('VERIF_PROFILE', 'standard')
# Directory for pickled bust data, kept per-profile so a fog (or ml) run
# doesn't overwrite the standard run's pickles
PICKLE_DIR = f'{OUT_DIR}/pickles' if PROFILE == 'standard' \
    else f'{OUT_DIR}/pickles_{PROFILE}'
T_STRS = os.environ['TAF_TYPES'].split()
VERIF_START = os.environ['VERIF_START']
VERIF_END = os.environ['VERIF_END']
PLOT_TITLES = os.environ['PLOT_TITLES']
TAF_TYPES = json.loads(PLOT_TITLES)
if PROFILE == 'standard':
    PLOT_TYPE_GROUPS = [
        ['o1', 'o3', 'p1', 'p3', 'mn', 'ma'],
        ['mn', 'ma'],
    ]
else:
    PLOT_TYPE_GROUPS = [list(TAF_TYPES)]

# Accepted first guess TAFs
AUTO_TAFS_LINES = []
for t_str in T_STRS:
    if 'Manual' in t_str:
        continue
    AUTO_TAFS_LINES.append(f'{D_DIR}/decodes/Output_{t_str}/acceptedTafs.csv')

# Start and end dates for verification period
START_DT = datetime.strptime(VERIF_START, '%Y%m%d')
END_DT = datetime.strptime(VERIF_END, '%Y%m%d') + timedelta(days=1)

# Days in verification period
DAYS = list(rrule(DAILY, interval=1, dtstart=START_DT, until=END_DT))

# For extracting from metdb
METDB_EMAIL = 'andre.lanyon@metoffice.gov.uk'
METDB_CACHE_DIR = '/data/users/andre.lanyon/tafs/metdb_data'

# TAF terms
TAF_TERMS = ['BECMG', 'TEMPO', 'PROB30', 'PROB40']

# Path to the shared TAF info table (issue frequencies and forecast lengths)
TAF_INFO_CSV = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            '..', 'standard_verification', 'taf_info.csv')


def _load_taf_freqs(path):
    """
    Loads TAF issue frequencies (hours between successive TAFs) keyed by
    (icao, taf_len). A TAF is only the valid/current forecast for taf_freq
    hours after issue, after which a newer TAF supersedes it. The same ICAO
    can issue multiple products of differing lengths/frequencies, so the
    forecast length is part of the key.
    """
    freqs = {}
    with open(path, newline='') as csv_file:
        for row in csv.DictReader(csv_file):
            try:
                icao = row['icao'].strip()
                taf_len = int(row['taf_len'])
                taf_freq = int(row['taf_freq'])
            except (KeyError, ValueError, AttributeError):
                continue
            freqs[(icao, taf_len)] = taf_freq
    return freqs


# Lookup used to limit bust checking to each TAF's valid (most recently
# issued) window
TAF_FREQS = _load_taf_freqs(TAF_INFO_CSV)


def find_taf_freq(freqs, icao, taf_len):
    """Return the issue frequency for the closest configured product length."""
    lengths = [length for name, length in freqs if name == icao]
    if not lengths:
        return None
    closest = min(lengths, key=lambda length: (abs(length - taf_len), length))

    return freqs[(icao, closest)]

# To convert heading into direction label (N, S, E or W)
NUM_TO_DIR = dict(zip(range(0, 370, 10), 
                      list('NNNNNEEEEEEEEESSSSSSSSSWWWWWWWWWNNNNN')))

# Wind bust types and direction strings
DIRS = ['N', 'E', 'S', 'W', 'VRB']

# String names of lists and dictionaries used to collect data
NAMES = ['wind_info', 'vis_info', 'cld_info', 'wx_info', 'all_info', 
         'wind_stats', 'vis_stats', 'cld_stats', 'wx_stats', 'all_stats', 
         'vis_cats', 'cld_cats', 'taf_lens', 'dirs_stats', 'metars_used', 
         'vis_cat_stats', 'cld_cat_stats', 'last_day']

# Dictionaries mapping short weather names to long names
W_NAMES = {'vis': 'visibility', 'wind': 'wind', 'wx': 'weather',
           'cld': 'cloud', 'all': 'all'}
P_NAMES = {'vis': 'Visibility', 'wind': 'Wind', 'wx': 'Significant Weather',
           'cld': 'Cloud Base', 'all': 'All'}

# ICAOS to use
REQ_ICAOS = [b'EGAA ', b'EGAC ', b'EGAE ', b'EGBB ', b'EGBJ ', b'EGCC ', 
             b'EGCK ', b'EGFF ', b'EGGD ', b'EGGP ', b'EGGW ', b'EGHH ', 
             b'EGHI ', b'EGKB ', b'EGKK ', b'EGLC ', b'EGLF ', b'EGLL ', 
             b'EGMC ', b'EGMD ', b'EGNH ', b'EGNJ ', b'EGNM ', b'EGNR ', 
             b'EGNT ', b'EGNV ', b'EGNX ', b'EGPA ', b'EGPB ', b'EGPC ', 
             b'EGPD ', b'EGPE ', b'EGPF ', b'EGPH ', b'EGPI ', b'EGPK ', 
             b'EGPN ', b'EGPO ', b'EGPU ', b'EGSH ', b'EGSS ', b'EGTE ',
             b'EGTK ', b'EGHQ ']
REQ_ICAO_STRS = {
    'EGAA': 'Belfast International', 'EGAC': 'Belfast City', 
    'EGAE': 'Londonderry', 'EGBB': 'Birmingham', 'EGBJ': 'Gloucester',
    'EGCC': 'Manchester Ringway', 'EGCK': 'Caenarfon', 'EGFF': 'Cardiff', 
    'EGGD': 'Bristol', 'EGGP': 'Liverpool', 'EGGW': 'Luton', 
    'EGHH': 'Bournemouth', 'EGHI': 'Southampton', 'EGKB': 'Biggin Hill', 
    'EGKK': 'Gatwick', 'EGLC': 'London City', 'EGLF': 'Farnborough',
    'EGLL': 'Heathrow', 'EGMC': 'Southend', 'EGMD': 'Lydd',
    'EGNH': 'Blackpool', 'EGNJ': 'Humberside', 'EGNM': 'Leeds Bradford', 
    'EGNR': 'Hawarden', 'EGNT': 'Newcastle', 'EGNV': 'Durham Teeside',
    'EGNX': 'East Midlands', 'EGPA': 'Kirkwall', 'EGPB': 'Sumburgh', 
    'EGPC': 'Wick', 'EGPD': 'Aberdeen', 'EGPE': 'Inverness', 'EGPF': 'Glasgow',
    'EGPH': 'Edinburgh', 'EGPI': 'Islay', 'EGPK': 'Prestwick', 
    'EGPN': 'Dundee', 'EGPO': 'Stornoway', 'EGPU': 'Tiree', 'EGSH': 'Norwich',
    'EGSS': 'Stansted', 'EGTE': 'Exeter', 'EGTK': 'Oxford', 'EGHQ': 'Newquay'}

# The fog ML experiment only covers a subset of airports; restrict to these
# when running the fog profile so busts are computed only for them.
if PROFILE == 'fog':
    FOG_ICAOS = ['EGCC', 'EGKK', 'EGLL']
    REQ_ICAO_STRS = {icao: name for icao, name in REQ_ICAO_STRS.items()
                     if icao in FOG_ICAOS}
    REQ_ICAOS = [icao for icao in REQ_ICAOS
                 if icao.decode().strip() in FOG_ICAOS]

NINE_HR_STRS = {
    'EGAC': 'Belfast City', 'EGAE': 'Londonderry', 'EGBJ': 'Gloucester',
    'EGCK': 'Caenarfon', 'EGHH': 'Bournemouth', 'EGHI': 'Southampton',
    'EGKB': 'Biggin Hill', 'EGLF': 'Farnborough', 'EGMC': 'Southend', 
    'EGMD': 'Lydd', 'EGNH': 'Blackpool', 'EGNJ': 'Humberside', 
    'EGNR': 'Hawarden', 'EGNV': 'Durham Teeside', 'EGPA': 'Kirkwall', 
    'EGPB': 'Sumburgh', 'EGPC': 'Wick', 'EGPE': 'Inverness', 'EGPI': 'Islay', 
    'EGPN': 'Dundee', 'EGPO': 'Stornoway', 'EGPU': 'Tiree', 'EGSH': 'Norwich',
    'EGTE': 'Exeter', 'EGTK': 'Oxford', 'EGHQ': 'Newquay'}

B_TYPES = ['increase', 'decrease', 'both', 'all']
WB_TYPES = ['increase', 'decrease', 'dir', 'all']
D_TYPES = ['increase', 'decrease', 'dir']

# For plotting
BUST_CATS = {'vis increase': 'Observed visibility higher', 
             'vis decrease': 'Observed visibility lower', 
             'vis all': 'Total visibility busts',
             'wx all': 'Significant weather busts', 
             'cld increase': 'Observed cloud higher', 
             'cld decrease': 'Observed cloud lower', 
             'cld all': 'Total cloud busts',
             'wind increase': 'Observed wind higher',
             'wind decrease': 'Observed wind lower',
             'wind dir': 'Wind direction busts',
             'wind all': 'Total wind busts'}
CAT_ORDER = {'Observed visibility higher': 'a',
             'Observed visibility lower': 'b',
             'Total visibility busts': 'c',
             'Significant weather busts': 'd',
             'Observed cloud higher': 'e',
             'Observed cloud lower': 'f',
             'Total cloud busts': 'g',
             'Observed wind higher': 'h',
             'Observed wind lower': 'i',
             'Wind direction busts': 'j',
             'Total wind busts': 'k'}

# Forecast category thresholds and labels, matching the categories defined
# in the standard_verification cfg files (e.g. no_p10_20_opt_all.cfg) so
# bust breakdowns line up with the sp_plots skill score breakdowns
VIS_CAT_THRESH = [350, 800, 1500, 5000, 10000]
VIS_CAT_LABELS = ['<=300m', '350-750m', '800-1400m', '1500-4900m',
                  '5000-9000m', '>=10000m']
CLD_CAT_THRESH = [200, 500, 1000, 1500]
CLD_CAT_LABELS = ['<=100ft', '200-400ft', '500-900ft', '1000-1400ft',
                  '>=1500ft']


def get_cat_label(param, value):
    """
    Returns the forecast category label a visibility (metres) or cloud base
    (feet) value falls into, using the same thresholds as the
    standard_verification cfg files.

    Args:
        param (str): 'vis' or 'cld'
        value (int): Visibility (metres) or cloud base height (feet)
    Returns:
        label (str): Category label
    """
    thresholds = VIS_CAT_THRESH if param == 'vis' else CLD_CAT_THRESH
    labels = VIS_CAT_LABELS if param == 'vis' else CLD_CAT_LABELS

    for bound, label in zip(thresholds, labels):
        if value < bound:
            return label

    return labels[-1]
