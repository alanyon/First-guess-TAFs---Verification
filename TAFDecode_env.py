'''
----------------------------------------------------------------------------
Script: TAFDecode_env.py
----------------------------------------------------------------------------
Description:
    Contains rules and shared code used for decoding TAFs and METARs.
Current Owner:
    CVC System Manager
Language:
    python
History:
Date     Ticket Comment
-------- ------ -------
08/04/11     73 Initial version. MT
11/11/11     80 Additions for storing weather types, temperatures and QNH. MT
07/06/13    118 Use binary operator for accumulating weather types. MT
20/12/13    130 Additions for storing weather qualifiers. MT
06/04/18    169 Allow some additional METAR strings previously rejected. RJD
03/07/20    252 Conversion to python3. CEB
-------- ------ End History
----------------------------------------------------------------------------
Input/syntax:
    Not callable directly
Uses:
    None
(c) Crown copyright Met Office. All rights reserved.
For further details please refer to the file COPYRIGHT.txt
which you should have received as part of this distribution.
End of header --------------------------------------------------------------
'''
import re, sys, datetime, calendar, os
#-----------------------------------------------------------------------------
# Conversion constants
#-----------------------------------------------------------------------------
knotToMps  = 1852/3600.0
kmhToMps   = 1/3.6
oktaToDec  = 0.125
ftToM      = 0.3048
smileToM   = 1609.344
nmileToM   = 1852
hinchToMil = .338639
#-----------------------------------------------------------------------------
# Read stationlists
#-----------------------------------------------------------------------------
# listdir     = os.path.dirname(sys.argv[0])+'/../Listfiles'
defenceList = {}
# reader = open(listdir+'/DefSQI.lst','r')
# for line in reader:
#   defenceList[line.strip().split(' ')[0]] = True
# reader.close()
# reader = open(listdir+'/DefOther.lst','r')
# for line in reader:
#   defenceList[line.strip().split(' ')[0]] = True
# reader.close()


# NOTE: currently, the rules exist as 'defence' or
#       'not-defence', thus only the defence site-
#       lists are currently read. This must be
#       extended if other groups of stations
#       require individual rules applied to them.
#-----------------------------------------------------------------------------
def readInputFile(inputFile):
  '''Reads the file passed in and returns as an array
  of strings. Trailing newlines are removed.'''
 
  reader = open(inputFile,'r', newline='\n')
  inputLines = []
  for line in reader:
    inputLines.append(line.strip())
  reader.close()
  return inputLines
 
#-----------------------------------------------------------------------------
# Regular expressions
#-----------------------------------------------------------------------------
# Note: Pre-compiling the regular expressions
# in this way is said to greatly improve
# performance if they're used multiple times.
regHeader  = re.compile('^T \d{4}Z \d\d\/\d\d\/\d\d .{14} [A-Z]{4} \d{4} \d \d [A-Z]{4}$')
regMHeader = re.compile('^M \d{4}Z \d\d\/\d\d\/\d\d .{14} [A-Z]{4} \d{4} \d \d [A-Z]{4} \d{6}Z$')
regTailSep = re.compile('(BECMG|TEMPO|NOSIG)')
regNil     = re.compile('^(NIL)$')
regNilCnl  = re.compile('^(NIL|CNL)$')
regChange  = re.compile('^(TEMPO|PROB\d0|BECMG|FM)')
regFM      = re.compile('^FM\d{4}00$')
regStation = re.compile('^[A-Z]{4}$')
regDTstr   = re.compile('^\d{4}\/\d{4}$')
regComDTstr= re.compile('^(\d{4}|\d{6})$')
regDTFMstr = re.compile('^\d{4}00$')
regComFMstr= re.compile('^\d{2}00$')
regWind    = re.compile('^(\d{3}|VRB)(\d{2}|\d{3})(G\d{2}|G\d{3})?(KT|KMH|MPS)$')
regWindDir = re.compile('^\d{3}V\d{3}$')
regVis     = re.compile('^(\d{4})$')
regVisNDV  = re.compile('^(\d{4})(?:NDV)?$')
regVisMin  = re.compile('^(\d{4})(N|NE|E|SE|S|SW|W|NW)$')
regVisMile = re.compile('^(\d\d?)\/?(\d\d?)?(SM|NM)$')
regVRunway = re.compile('^R.+\/(P?\d{4}V)?P?\d{4}(N|U|D)?$')
regCloud   = re.compile('^(FEW|SCT|BKN|OVC)(\d{3})(CB|TCU)?$')
regMCloud  = re.compile('^(FEW|SCT|BKN|OVC)(\d{3})(?:TCU|\/\/\/)?$')
regCloudCB = re.compile('^(FEW|SCT|BKN|OVC)(\d{3})CB$')
regAutoCB  = re.compile('^\/{6}CB?$')
regVV      = re.compile('^VV(\/\/\/|\d{3})$')
regMaxT    = re.compile('^TXM?(\d\d)\/(\d\d\d\d)Z$')
regMinT    = re.compile('^TNM?(\d\d)\/(\d\d\d\d)Z$')
regAirDewT = re.compile('^(M?)(\d\d|\/\/)\/(M?)(\d\d|\/\/)$')
regPres    = re.compile('^(Q|A)([0-9/]{4})$')
regPRunway = re.compile('^(R.+\/[0-9/]{6}|\d\d.{6}|RESN|R\d\d\/\d\d)$')
regTurb    = re.compile('^(5\d{5})$')
regWeather = re.compile('^(\+|\-|RE|VC)?([A-Z]+)$')
regCol     = re.compile('^(?:BLACK)?(BLU|GRN|WHT|AMB|YLO1|YLO2|RED)$')
regBlack   = re.compile('^BLACK$')
regWS1     = re.compile('^WS$')
regWS2     = re.compile('^RW?Y?\d\d\d?(R|L)?$')
regErrMod  = re.compile('^(FBL|MOD|HVY)$')
regRemark  = re.compile('^RMK$')
regMMisc   = re.compile('^(\/+|\d\d\/\/\/|AO2|CIG|SNOCLO|CLR|NILSIG|\/{6}TCU|(R|W)\/\/\/\w{1}\d{1})$')
#-----------------------------------------------------------------------------
# Valid weather types
#-----------------------------------------------------------------------------
# Define weathers (numerical values determined from BUFR flag-tables 020193
# and 020194)
weathers_plus = {'DZ'     : [0,    2**0],
                 'RA'     : [0,    2**1],
                 'SN'     : [0,    2**2],
                 'SG'     : [0,    2**3],
                 'PL'     : [0,    2**5],
                 'DS'     : [0,    2**19],
                 'SS'     : [0,    2**18],
                 'FZDZ'   : [2**6, 2**0],
                 'FZRA'   : [2**6, 2**1],
                 'SHGR'   : [2**4, 2**6],
                 'SHGS'   : [2**4, 2**7],
                 'SHRA'   : [2**4, 2**1],
                 'SHSN'   : [2**4, 2**2],
                 'TSGR'   : [2**5, 2**6],
                 'TSGS'   : [2**5, 2**7],
                 'TSPL'   : [2**5, 2**5],
                 'TSRA'   : [2**5, 2**1],
                 'TSSN'   : [2**5, 2**2],
                 'FZUP'   : [2**6, 0],
                 'GS'     : [0,    2**7],
                 'SHRAGS' : [2**4, 2**1 + 2**7],
                 'SHRAGR' : [2**4, 2**1 + 2**6],
                 'SHSNGS' : [2**4, 2**2 + 2**7],
                 'FZBCFG' : [2**1 + 2**6, 2**9],
                 'FZBR'   : [2**6, 2**8]}
weathers      = {'IC'     : [0,    2**4],
                 'FG'     : [0,    2**9],
                 'BR'     : [0,    2**8],
                 'SA'     : [0,    2**13],
                 'DU'     : [0,    2**12],
                 'HZ'     : [0,    2**14],
                 'FU'     : [0,    2**10],
                 'VA'     : [0,    2**11],
                 'SQ'     : [0,    2**16],
                 'PO'     : [0,    2**15],
                 'FC'     : [0,    2**17],
                 'TS'     : [2**5, 0],
                 'BCFG'   : [2**1, 2**9],
                 'BLDU'   : [2**3, 2**12],
                 'BLSA'   : [2**3, 2**13],
                 'BLSN'   : [2**3, 2**2],
                 'DRDU'   : [2**2, 2**12],
                 'DRSA'   : [2**2, 2**13],
                 'DRSN'   : [2**2, 2**2],
                 'FZFG'   : [2**6, 2**9],
                 'MIFG'   : [2**0, 2**9],
                 'PRFG'   : [2**7, 2**9],
                 'NSW'    : [0,    0],
                 'UP'     : [0,    0]}
weathers_vc   = {'FG'     : [0,    2**9],
                 'PO'     : [0,    2**15],
                 'FC'     : [0,    2**17],
                 'DS'     : [0,    2**19],
                 'SS'     : [0,    2**18],
                 'TS'     : [2**5, 0],
                 'SH'     : [2**4, 0],
                 'BLSN'   : [2**3, 2**2],
                 'BLSA'   : [2**3, 2**13],
                 'BLDU'   : [2**3, 2**12],
                 'VA'     : [0,    2**11]}
weathers_re   = {'FZDZ'   : [2**6, 2**0],
                 'FZRA'   : [2**6, 2**1],
                 'DZ'     : [0,    2**0],
                 'SHRA'   : [2**4, 2**1],
                 'RA'     : [0,    2**1],
                 'SHSN'   : [2**4, 2**2],
                 'SN'     : [0,    2**2],
                 'SG'     : [0,    2**3],
                 'GR'     : [0,    2**6],
                 'SHGR'   : [2**4, 2**6],
                 'SHGS'   : [2**4, 2**7],
                 'SHRAGS' : [2**4, 2**1 + 2**7],
                 'BLSN'   : [2**3, 2**2],
                 'SS'     : [0,    2**18],
                 'TS'     : [2**5, 0],
                 'DS'     : [0,    2**19],
                 'TSRA'   : [2**5, 2**1],
                 'TSSN'   : [2**5, 2**2],
                 'TSPL'   : [2**5, 2**5],
                 'TSGR'   : [2**5, 2**6],
                 'TSGS'   : [2**5, 2**7],
                 'TSRAGS' : [2**5, 2**1 + 2**7],
                 'FC'     : [0,    2**17],
                 'VA'     : [0,    2**11],
                 'PL'     : [0,    2**5],
                 'UP'     : [0,    0]}
# Add all of 'weathers_plus' to 'weathers'
for weath in weathers_plus.keys():
  weathers[weath] = weathers_plus[weath]
# Weather considered to be 'obscuring'
obscuringWeather = {'FG'  :True,
                    'BR'  :True,
                    'HZ'  :True,
                    'FZFG':True,
                    'MIFG':True,
                    'PRFG':True}
#-----------------------------------------------------------------------------
# Output functions
#-----------------------------------------------------------------------------
def printGood(accepts,goodOutput,csvOutput):
  '''Prints SQL formatted CSV files of correctly parsed TAF/METARs.
 
  goodOutput - csv header followed by whole taf/metar string
  csvOutput  - Full csv'''
 
  for line in accepts:
    print(line.toHead(), file=goodOutput)
    print(line.toCsv(), file=csvOutput)
   
#-----------------------------------------------------------------------------
def printDuff(rejects,badOutput):
  '''Prints original TAF/METAR text of duff TAF/METARs to badOutput and
  prints the corresponding error messages to stdout.'''
  print(('=-'*30)+'\n\tErrors\n'+('=-'*30)+'\n', file=sys.stderr)
  if not rejects:
    print('No errors given\n')
  else:
    for i,line,msg in rejects:
      print("["+str(i)+"] Error: "+msg, file=sys.stderr)
      print(line+"\n", file=sys.stderr)
      print(line, file=badOutput)
#-----------------------------------------------------------------------------
def printWarn(warned):
  '''Prints any warnings generated by the parsing of TAF/METARSs
  to standard error.'''
 
  print(('=-'*30)+'\n\tWarnings\n'+('=-'*30)+'\n', file=sys.stderr)
  if not warned:
    print('No warnings given\n', file=sys.stderr)
  else:
    for i,line,msg in warned:
      print("["+str(i)+"] Warning: "+msg, file=sys.stderr)
      print(line+"\n", file=sys.stderr)
#-----------------------------------------------------------------------------
def printSummary(title,tot,duff,warn,good,ignored,clusters=None):
  '''Prints, to standard out, a short summary of the completed
  process.''' 
 
  # Calculate percentages
  percGood    = str(((good*1000)//tot)/10.0)
  percDuff    = str(((duff*1000)//tot)/10.0)
  percIgnored = str(((ignored*1000)//tot)/10.0)
 
  print(('=-'*30)+'\n\tSummary\n'+('=-'*30)+'\n')
  print(tot,title+"s in file...")
  print("..."+str(good)+" written to output.\n")
  print(warn,"warnings generated.\n")
  print(ignored,"ignored (corrected, amended, missing or cancelled).\n")
  if clusters is not None:
    print(clusters,"clusters parsed from",good,title+"s.\n")
  print("Number of "+title+"s:")
  print("\tAccepted:\t"+str(good)+"\t("+percGood+"%)")
  print("\tRejected:\t"+str(duff)+"\t("+percDuff+"%)")
  print("\tIgnored:\t"+str(ignored)+"\t("+percIgnored+"%)")
#-----------------------------------------------------------------------------
# Calculate datetime
#-----------------------------------------------------------------------------
def calcDate(baseDT,string,compat=False):
  '''Turns 'string', of format DDHH, into a valid
  datetime object. A datetime 'baseDT' is used
  to determine month and year.
 
  Errors that may be generated by this function
  are NOT CAUGHT and should be handled by the
  caller.
 
  In compatibility mode, a datetime string of
  format [DD]HHHH is expected and the funtion
  returns both a starttime and endtime from this.'''
  if compat:
    smon = emon = baseDT.month
    syea = eyea = baseDT.year
    monl = calendar.monthrange(syea,smon)[1]
    if len(string) == 6:
      sday = eday = int(string[0:2])
      shr  = int(string[2:4])
      ehr  = int(string[4:6])
    else:
      sday = eday = baseDT.day
      shr  = int(string[0:2])
      ehr  = int(string[2:4])
      if shr < baseDT.hour:
        sday += 1
        eday += 1
   
    # See if end date is greater than start date
    if ehr <= shr:
      eday += 1
    elif ehr == 24:
      ehr = 0
      eday += 1
   
    # See if months need incrementing from that of base
    if sday < baseDT.day and sday < 5 and baseDT.day >25:
      smon += 1
      emon += 1
    # See if end month needs incrementing from that of start month
    elif eday > monl:
      emon += 1
      eday -= monl
   
    # See if start year needs incrementing
    if smon > 12:
      smon -= 12
      syea += 1
    # See if end year needs incrementing
    if emon > 12:
      emon -= 12
      eyea += 1
     
    return datetime.datetime(syea,smon,sday,shr),\
           datetime.datetime(eyea,emon,eday,ehr)
   
  else:
    month = baseDT.month
    year  = baseDT.year
    monl  = calendar.monthrange(year,month)[1]
    day   = int(string[0:2])
    hour  = int(string[2:4])
    # Some TAFs have hour = 24, causing date functions to fail
    if hour == 24:
      hour = 0
      day += 1
    # Check if this has caused an increment in month
    if day > monl:
      day -= monl
      month += 1
    # Or see if month needs incrementing from that of base otherwise
    elif day < baseDT.day and day < 5 and baseDT.day > 25:
      month += 1
    # See if year needs incrementing from that of base
    if month > 12:
      month -= 12
      year   += 1
    return datetime.datetime(year,month,day,hour)
#-----------------------------------------------------------------------------
# Reduce cloud tuples
#-----------------------------------------------------------------------------
def reduceClouds(clouds,covThresh):
  '''Turns array of cloud tuples into single tuple. The resulting
  tuple need not be a forecasted pair of cloud amount and cloud base.
  Rather, it is the GREATEST CLOUD AMOUNT LOWER THAN 1500FT and the
  LOWEST CLOUD BASE WITH A COVERING MORE THAN 5 (civil) OR 3
  (defence). That is:
 
    * maximum coverage of all tuples whos corresponding base is
      less than 1500ft
    * minimum base of all tuples whos corresponding coverage is
      more that 5 (civil) or 3 (defence) (although this function
      has a second argument as the covering threshold).
 
  A covering of 'VV' is treated as 'OVC' (mapped to 8 oktas) and
  it is treated in the same way as a cloud tuple (with '///'
  previously being converted to a 'height' of 0).
  '''
 
  maxCov = 0
  minBse = 9999
 
  # Error if there are no clouds to cycle through
  if not clouds: assert False
 
  # Cycle through cloud coverage and cloud base tuples
  for cldCov, cldBse in clouds:
    cldBse = int(cldBse)*100
   
    # Translate the coverage keywords to an okta
    # covering. Throw an error if passed something
    # other than these.
    if   cldCov == 'NSC': newCov = 0
    elif cldCov == 'NCD': newCov = 0
    elif cldCov == 'SKC': newCov = 0
    elif cldCov == 'FEW': newCov = 1
    elif cldCov == 'SCT': newCov = 3
    elif cldCov == 'BKN': newCov = 5
    elif cldCov == 'OVC': newCov = 8
    elif cldCov == 'VV' : newCov = 8
    else: assert False
   
    # Take maximum of cloud coverages with corresponding
    # cloud base above 1500ft
    if cldBse < 1500:
      maxCov = max(maxCov,newCov)
   
    # Take maximum of cloud bases when corresponding
    # coverage is above threshold
    if newCov >= covThresh:
      minBse = min(minBse,cldBse)
 
  # Finally, convert coverage and base to SI units
  maxCov *= oktaToDec
  minBse  = int(minBse*ftToM)
  return (maxCov,minBse)
#-----------------------------------------------------------------------------
# Validate weather and detect obscuring weather
#-----------------------------------------------------------------------------
def validateWeather(prefix,string,retCodes=False):
  '''Serves two purposes:
 
  Firstly:
  If retCodes is False, returns True if weather string
  contains a sky-obscuring type (e.g. fog, defined above).
  If retCodes is True, returns the binary sum of the two
  columns of numbers in the weather dictionaries,
  representing the descriptors (qualifiers) and
  phenomena.
 
  Secondly:
  Checks to see if a string is comprised of elements in
  global dictionaries 'weathers' and 'weathers_plus'.
  The dictionary chosen depends on prefix.
 
  E.g.
  With a dictionary {'AB':True,'BC':True,'DEFG':True},
    string 'DEFGAB' would pass
    string 'ABC' would raise Exception'''
  if prefix=='+':
    weathDict = weathers_plus
  elif prefix=='RE':
    weathDict = weathers_re
  elif prefix=='VC':
    weathDict = weathers_vc
  else:
    weathDict = weathers
 
  validString = False
  skyObscured = False
  weatherNumb = 0
  descripNumb = 0
 
  while True:
    if string in obscuringWeather.keys(): skyObscured = True
    if string in weathDict.keys():
      descripNumb |= weathDict[string][0]
      weatherNumb |= weathDict[string][1]
      validString  = True
      break
    elif len(string) > 4:
      if string[0:2] in obscuringWeather.keys(): skyObscured = True
      if string[0:4] in obscuringWeather.keys(): skyObscured = True
      if string[0:4] in weathDict.keys():
        descripNumb |= weathDict[string[0:4]][0]
        weatherNumb |= weathDict[string[0:4]][1]
        string = string[4:]
        continue
      elif string[0:2] in weathDict.keys():
        descripNumb |= weathDict[string[0:2]][0]
        weatherNumb |= weathDict[string[0:2]][1]
        string = string[2:]
        continue
    elif len(string) > 2:
      if string[0:2] in obscuringWeather.keys(): skyObscured = True
      if string[0:2] in weathDict.keys():
        descripNumb |= weathDict[string[0:2]][0]
        weatherNumb |= weathDict[string[0:2]][1]
        string = string[2:]
        continue
    # If a 'continue' is not reached, then the string is invalid
    break
 
  if not validString:
    raise Exception
  if retCodes:
    return descripNumb, weatherNumb
  else:
    return skyObscured
#-----------------------------------------------------------------------------
# Validation functions
#-----------------------------------------------------------------------------
def testVisRes(vis):
  if vis:
      if (0    <= vis < 800  and vis%50   != 0) or \
         (800  <= vis < 5000 and vis%100  != 0) or \
         (5000 <= vis < 9999 and vis%1000 != 0) :
        return True, "Visibility has incorrect resolution ("+str(vis)+")"
 
  return False,"" # No error
 
#-----------------------------------------------------------------------------
def testMinVis(minVis,vis):
  if vis != minVis:
    if minVis >= 5000:
      return True,"Minimum visibility not less than 5km"
    elif minVis >= 1500 and minVis >= vis/2:
      return True,"Minimum visibility not less than 1.5km and not less than half prevailing visibility"
 
  return False,"" # No error
#-----------------------------------------------------------------------------
def testGstSpd(wsp,gsp):
  if gsp:
    if gsp < wsp + 5:
      return True, "Gust speed less than 5mps greater than mean wind " + \
                   "(WSP: %.1fmps, GSP: %.1fmps)" % (wsp, gsp)
 
  return False, "" # No error
   
#-----------------------------------------------------------------------------
def convertWinds(oldWind,unit):
  if unit == "MPS":
    return float(oldWind)
  elif unit == "KT":
    return round(oldWind * knotToMps,1)
  elif unit == "KMH":
    return round(oldWind * kmhToMps, 1)
  else:
    assert False
#-----------------------------------------------------------------------------