"""
Module containing constants for use in other scripts.
"""
from datetime import datetime
from dateutil.rrule import DAILY, rrule

# Accepted first guess TAFs
D_DIR = '/data/users/alanyon/tafs/improver/verification/20230805-20241004_ml'
ALL_TAFS = f'{D_DIR}/decodes/Output_all/acceptedTafs.csv'
OLD_TAFS = f'{D_DIR}/decodes/Output_old/acceptedTafs.csv'
NEW_XG_TAFS = f'{D_DIR}/decodes/Output_new_xg/acceptedTafs.csv'
NEW_RF_TAFS = f'{D_DIR}/decodes/Output_new_rf/acceptedTafs.csv'

# Start and end dates for verification period
START_DT = datetime(2023, 8, 5)
END_DT = datetime(2024, 10, 5)

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
         'metar_dirs', 'old_dirs', 'xg_dirs', 'rf_dirs', 'man_dirs', 
         'metars_used', 'last_day']
NAMES_ALL = ['wind_info', 'vis_info', 'cld_info', 'wx_info', 'all_info', 
             'wind_stats', 'vis_stats', 'cld_stats', 'wx_stats', 'all_stats', 
             'metar_dirs', 'fg_dirs', 'man_dirs', 'metars_used', 'last_day']

# Dictionaries mapping short weather names to long names
W_NAMES = {'vis': 'visibility', 'wind': 'wind', 'wx': 'weather',
           'cld': 'cloud', 'all': 'all'}
P_NAMES = {'vis': 'Visibility', 'wind': 'Wind', 'wx': 'Significant Weather',
           'cld': 'Cloud Base', 'all': 'All'}

# ICAOS to use
REQ_ICAOS = [b'EGAA ', b'EGAC ', b'EGCC ', b'EGCK ', b'EGFF ', b'EGHH ', 
             b'EGGW ', b'EGGD ', b'EGGP ', b'EGKK ', b'EGLL ', b'EGNJ ', 
             b'EGNT ', b'EGNX ', b'EGPE ', b'EGPO ', b'EGPA ', b'EGPB ', 
             b'EGPC ', b'EGNM ', b'EGBB ', b'EGSH ', b'EGPH ', b'EGPK ', 
             b'EGSS ', b'EGPF ', b'EGPD ']
REQ_ICAO_STRS = {
    'EGAA': 'Belfast International', 'EGAC': 'Belfast City', 
    'EGCC': 'Manchester Ringway', 'EGCK': 'Caenarfon', 'EGHH': 'Bournemouth', 
    'EGFF': 'Cardiff', 'EGBB': 'Birmingham', 'EGGW': 'Luton',
    'EGGD': 'Bristol', 'EGGP': 'Liverpool', 'EGKK': 'Gatwick', 
    'EGLL': 'Heathrow', 'EGNJ': 'Humberside', 'EGNT': 'Newcastle', 
    'EGPA': 'Kirkwall', 'EGPB': 'Sumburgh', 'EGPC': 'Wick', 
    'EGNX': 'East Midlands', 'EGSH': 'Norwich', 'EGPE': 'Inverness', 
    'EGPO': 'Stornoway', 'EGNM': 'Leeds Bradford', 'EGPH': 'Edinburgh', 
    'EGPK': 'Prestwick', 'EGSS': 'Stansted', 'EGPF': 'Glasgow', 
    'EGPD': 'Aberdeen'}
# REQ_ICAOS = [b'EGLL ']
# REQ_ICAO_STRS = {'EGLL': 'Heathrow'}

# TAF type names and abbrieviations
TAF_TYPES = {'xg': 'New XGBoost', 'rf': 'New Random Forest', 'old': 'Old', 
             'man': 'Manual'}
TAF_TYPES_ALL = {'fg': 'First Guess', 'man': 'Manual'}
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
