"""
Module containing constants for use in other scripts.
"""
from datetime import datetime
from dateutil.rrule import DAILY, rrule

# Accepted first guess TAFs
D_DIR = '/data/users/andre.lanyon/tafs/verification/20230805-20250304_test'
AUTO_TAFS_LINES = [f'{D_DIR}/decodes/Output_im_no_obs_opt/acceptedTafs.csv',
                   f'{D_DIR}/decodes/Output_im_no_obs_pes/acceptedTafs.csv',
                   f'{D_DIR}/decodes/Output_im_obs_opt/acceptedTafs.csv',
                   f'{D_DIR}/decodes/Output_im_obs_pes/acceptedTafs.csv']

# Start and end dates for verification period
START_DT = datetime(2023, 8, 5)
END_DT = datetime(2025, 3, 5)

# Days in verification period
DAYS = list(rrule(DAILY, interval=1, dtstart=START_DT, until=END_DT))

# For extracting from metdb
METDB_EMAIL = 'andre.lanyon@metoffice.gov.uk'

# TAF terms
TAF_TERMS = ['BECMG', 'TEMPO', 'PROB30', 'PROB40']

# To convert heading into direction label (N, S, E or W)
NUM_TO_DIR = dict(zip(range(0, 370, 10), 
                      list('NNNNNEEEEEEEEESSSSSSSSSWWWWWWWWWNNNNN')))

# Wind bust types and direction strings
DIRS = ['N', 'E', 'S', 'W', 'VRB']

# String names of lists and dictionaries used to collect data
NAMES = ['wind_info', 'vis_info', 'cld_info', 'wx_info', 'all_info', 
         'wind_stats', 'vis_stats', 'cld_stats', 'wx_stats', 'all_stats', 
         'dirs_stats', 'metars_used', 'last_day']

# Dictionaries mapping short weather names to long names
W_NAMES = {'vis': 'visibility', 'wind': 'wind', 'wx': 'weather',
           'cld': 'cloud', 'all': 'all'}
P_NAMES = {'vis': 'Visibility', 'wind': 'Wind', 'wx': 'Significant Weather',
           'cld': 'Cloud Base', 'all': 'All'}

# ICAOS to use
REQ_ICAOS = [b'EGAA ', b'EGAC ', b'EGAE ', b'EGBB ', b'EGBJ ', b'EGCC ', 
             b'EGCK ', b'EGFF ', b'EGGD ', b'EGGP ', b'EGGW ', b'EGHH ', 
             b'EGHI ', b'EGKA ', b'EGKB ', b'EGKK ', b'EGLF ', b'EGLL ', 
             b'EGMC ', b'EGMD ', b'EGNH ', b'EGNJ ', b'EGNM ', b'EGNR ', 
             b'EGNT ', b'EGNV ', b'EGNX ', b'EGPA ', b'EGPB ', b'EGPC ', 
             b'EGPD ', b'EGPE ', b'EGPF ', b'EGPH ', b'EGPI ', b'EGPK ', 
             b'EGPN ', b'EGPO ', b'EGPU ', b'EGSH ', b'EGSS ', b'EGTE ',
             b'EGTK ']
REQ_ICAO_STRS = {
    'EGAA': 'Belfast International', 'EGAC': 'Belfast City', 
    'EGAE': 'Londonderry', 'EGBB': 'Birmingham', 'EGBJ': 'Gloucester',
    'EGCC': 'Manchester Ringway', 'EGCK': 'Caenarfon', 'EGFF': 'Cardiff', 
    'EGGD': 'Bristol', 'EGGP': 'Liverpool', 'EGGW': 'Luton', 
    'EGHH': 'Bournemouth', 'EGHI': 'Southampton', 'EGKA': 'Shoreham',
    'EGKB': 'Biggin Hill', 'EGKK': 'Gatwick', 'EGLF': 'Farnborough',
    'EGLL': 'Heathrow', 'EGMC': 'Southend', 'EGMD': 'Lydd', 
    'EGNH': 'Blackpool', 'EGNJ': 'Humberside', 'EGNM': 'Leeds Bradford', 
    'EGNR': 'Hawarden', 'EGNT': 'Newcastle', 'EGNV': 'Durham Teeside',
    'EGNX': 'East Midlands', 'EGPA': 'Kirkwall', 'EGPB': 'Sumburgh', 
    'EGPC': 'Wick', 'EGPD': 'Aberdeen', 'EGPE': 'Inverness', 'EGPF': 'Glasgow',
    'EGPH': 'Edinburgh', 'EGPI': 'Islay', 'EGPK': 'Prestwick', 
    'EGPN': 'Dundee', 'EGPO': 'Stornoway', 'EGPU': 'Tiree', 'EGSH': 'Norwich',
    'EGSS': 'Stansted', 'EGTE': 'Exeter', 'EGTK': 'Oxford'}

# TAF type names and abbrieviations
TAF_TYPES = {'noo': 'IMPROVER Optimistic\nTAFs', 
             'nop': 'IMPROVER Pessimistic\nTAFs', 
             'oo': 'IMPROVER Optimistic\nTAFs with Obs',
             'op': 'IMPROVER Pessimistic\nTAFs with Obs', 
             'man': 'Manual TAFs'}
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
