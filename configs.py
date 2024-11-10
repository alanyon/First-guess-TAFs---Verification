"""
Module containing constants for use in other scripts.
"""
from datetime import datetime
from dateutil.rrule import DAILY, rrule

# Accepted first guess TAFs
D_DIR = '/data/users/alanyon/tafs/verification/imp_vs_bd_20230804-20240804'
IMP_TAFS = f'{D_DIR}/decodes/Output_im/acceptedTafs.csv'

# Start and end dates for verification period
START_DT = datetime(2023, 8, 4)
END_DT = datetime(2024, 8, 5)

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
B_TYPES = ['increase', 'decrease', 'dir']
DIRS = ['N', 'E', 'S', 'W', 'VRB']

# String names of lists and dictionaries used to collect data
NAMES = ['wind_info', 'vis_info', 'cld_info', 'wx_info', 'all_info', 
         'wind_stats', 'vis_stats', 'cld_stats', 'wx_stats', 'all_stats', 
         'metar_dirs', 'imp_dirs', 'man_dirs', 'metars_used', 'last_day']

# Dictionaries mapping short weather names to long names
W_NAMES = {'vis': 'visibility', 'wind': 'wind', 'wx': 'weather',
           'cld': 'cloud', 'all': 'all'}
P_NAMES = {'vis': 'Visibility', 'wind': 'Wind', 'wx': 'Significant Weather',
           'cld': 'Cloud Base', 'all': 'All'}

# ICAOS to use
REQ_ICAOS = [b'EGAA ', b'EGAC ', b'EGAE ', b'EGCC ', b'EGCK ', b'EGFF ', 
             b'EGHH ', b'EGGW ', b'EGKB ', b'EGLF ', b'EGMC ', b'EGMD ',
             b'EGGD ', b'EGGP ', b'EGKK ', b'EGLL ', b'EGNJ ', b'EGNT ', 
             b'EGNX ', b'EGPE ', b'EGPO ', b'EGPA ', b'EGPB ', b'EGPC ',
             b'EGNH ', b'EGNM ', b'EGNV ', b'EGSY ', b'EGBB ', b'EGPN ',
             b'EGHI ', b'EGNC ', b'EGTE ', b'EGPI ', b'EGSH ', b'EGTK ',
             b'EGPH ', b'EGPK ', b'EGSS ', b'EGPF ', b'EGPD ']
REQ_ICAO_STRS = {
    'EGAA': 'Belfast International', 'EGAC': 'Belfast City', 
    'EGAE': 'Londonderry', 'EGCC': 'Manchester', 'EGCK': 'Caenarfon',
    'EGHH': 'Bournemouth', 'EGTE': 'Exeter', 'EGFF': 'Cardiff', 
    'EGBB': 'Birmingham', 'EGGW': 'Luton', 'EGKB': 'Biggin Hill',
    'EGGD': 'Bristol', 'EGGP': 'Liverpool', 'EGKK': 'Gatwick', 
    'EGLF': 'Farnborough', 'EGLL': 'Heathrow', 'EGNJ': 'Humberside', 
    'EGNT': 'Newcastle', 'EGMC': 'Southend', 'EGMD': 'Lydd', 
    'EGPA': 'Kirkwall', 'EGPB': 'Sumburgh', 'EGPC': 'Wick', 'EGPI': 'Islay',
    'EGPN': 'Dundee', 'EGNX': 'East Midlands', 'EGSH': 'Norwich',
    'EGTK': 'Oxford', 'EGPE': 'Inverness', 'EGPO': 'Stornoway', 
    'EGNH': 'Blackpool', 'EGNM': 'Leeds', 'EGNV': 'Teeside', 
    'EGSY': 'St Athan', 'EGHI': 'Southampton', 'EGNC': 'Carlisle',
    'EGPH': 'Edinburgh', 'EGPK': 'Prestwick', 'EGSS': 'Stansted', 
    'EGPF': 'Glasgow', 'EGPD': 'Aberdeen'}
# REQ_ICAOS = [b'EGLL ']
# REQ_ICAO_STRS = {'EGLL': 'Heathrow'}

# TAF type names and abbrieviations
TAF_TYPES = {'imp': 'IMPROVER', 'man': 'Manual'}
B_TYPES = ['increase', 'decrease', 'both', 'all']
WB_TYPES = ['increase', 'decrease', 'dir', 'all']
D_TYPES = ['increase', 'decrease', 'dir']
