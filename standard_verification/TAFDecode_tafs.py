'''
----------------------------------------------------------------------------
Script: TAFDecode_tafs.py
----------------------------------------------------------------------------
Description:
    Script to decode TAFs into CSV format for SQL ingestion
Current Owner:
    CVC System Manager
Language:
    python
History:
Date     Ticket Comment
-------- ------ -------
08/04/11     73 Initial version. MT
03/07/20    252 Conversion to python3. CEB
-------- ------ End History
----------------------------------------------------------------------------
Input/syntax:
    -i INPUTDIR     Defaults to ./../Download/Output (relative to script)
    -o OUTPUTDIR    Defaults to ./Output (relative to script)
Uses:
(c) Crown copyright Met Office. All rights reserved.
For further details please refer to the file COPYRIGHT.txt
which you should have received as part of this distribution.
End of header --------------------------------------------------------------
'''
import re, datetime, sys, time, getopt
from TAFDecode_env import *
#-----------------------------------------------------------------------------
# Driver
#-----------------------------------------------------------------------------
def main():
  '''main() is driver of this script and is called
  automatically when the script is read interactively.'''
 
  # Read arguments to determine input and output directories
  inputDir=outputDir=None
 
  opts,args = getopt.getopt(sys.argv[1:], "i:o:")
  for o,v in opts:
    if o == '-i':
        inputDir=v
    if o == '-o':
        outputDir=v
 
  # Give defaults if not passed as arguments
  if inputDir is None:
    inputDir  = os.path.dirname(sys.argv[0])+'/../Download/Output'
  if outputDir is None:
    outputDir = os.path.dirname(sys.argv[0])+'/Output'
   
  # Input file
  tafenv_inputfile  = inputDir+'/tafs.txt'
  # Output files
  tafenv_csvOutput  = outputDir+'/decodedTafs.csv'
  tafenv_goodOutput = outputDir+'/acceptedTafs.csv'
  tafenv_badOutput  = outputDir+'/rejectedTafs.txt'
  tafenv_monitor    = outputDir+'/monitorTafs.txt'
 
  # Read input
  inputLines  = readInputFile(tafenv_inputfile)
 
  # Init variables
  acceptTafs  = []
  rejectTafs  = []
  warnedTafs  = []
  ignored     = 0
  numClusters = 0
 
  # Cycle through TAFs
  for i,line in enumerate(inputLines):
    try:
      # Attempt to create the TAF
      tempTaf = taf(line)
      # Gather warnings
      for warn in tempTaf.warnings:
        warnedTafs.append((i,line,warn))
      acceptTafs.append(tempTaf)
      # Increment number of clusters
      numClusters += len(tempTaf.clusters)
   
    # Reject a TAF           
    except TafError as value:
      rejectTafs.append((i,line,str(value)))
    # Ignore a TAF
    except TafIgnore:
      ignored += 1
   
  # Deal with making output here
  csvOutput  = open(tafenv_csvOutput, 'w')
  goodOutput = open(tafenv_goodOutput,'w')
  badOutput  = open(tafenv_badOutput, 'w')
  printGood(acceptTafs,goodOutput,csvOutput)
  printDuff(rejectTafs,badOutput)
  printWarn(warnedTafs)
  printSummary("TAF",len(inputLines),len(rejectTafs),len(warnedTafs),len(acceptTafs),ignored,numClusters)
  csvOutput.close()
  goodOutput.close()
  badOutput.close()
 
  # print("\n\n"+sys.argv[0]+" has finished at "+str(time.ctime()))
  # print("and has used "+str(time.clock())+" seconds of processor time.")
 
 
#-----------------------------------------------------------------------------
# TAF class
#-----------------------------------------------------------------------------
class taf(object):
  '''Each taf object is fully defined on initialisation.
  That is, the creation of cluster objects and the
  parsing of the taf ('line') is handled in __init__
  and the only function expected to be called
  externally is tafToCsv() for extracting the formatted
  data.'''
 
  def __init__(self,line):
    '''line - the string of the unprocessed TAF.'''
   
    # Assign input
    self.line      = line
    self.header    = line[0:50]
    self.body      = line[59:].split()
   
    # List storing any warning messages
    self.warnings  = []
   
    # This is True when the issue date is prior to
    # 5th November 2008 (different datetime string)
    self.compat = False
   
    # Check body for cancellations
    for el in self.body:
      if regNilCnl.search(el):
        raise TafIgnore()
   
    # Deal with header
    self.validateHeader()
    self.calcIssueTime()
    self.calcStartEndTime()
    self.calcStations()
    self.calcCorAmd()
    # Deal with body
    self.clusterBody()
    self.gatherWarnings()
  #---------------------------------------------------------------------------
  def validateHeader(self):
    '''Ensures format of header matches the regHeader
    regular expression. If not, raises TafError.
    Also raises TafIgnore exception if the taf's
    corrected or ammended flags are non-zero.'''
   
    if not regHeader.search(self.header):
      raise TafError("Incorrect header format")
     
  #---------------------------------------------------------------------------
  def calcIssueTime(self):
    try:
      self.issueTime = datetime.datetime(int(self.header[14:16]) + 2000, \
                                         int(self.header[11:13]),        \
                                         int(self.header[8:10]),         \
                                         int(self.header[2:4]),          \
                                         int(self.header[4:6]))
    except:
      raise TafError("Incorrect issue datetime in header")
   
    # Check to enable compatibility mode
    if self.issueTime < datetime.datetime(2008,11,5,0,0):
      self.compat = True
  #---------------------------------------------------------------------------
  def calcStartEndTime(self):
    # Check if date strings are able to be parsed
    if self.compat:
      try:
        self.startTime,self.endTime = \
          calcDate(self.issueTime,self.body[0],True)
      except:
        raise TafError("Compatibility mode: datetime string not parsed ("+self.body[0]+")")
    else:
      try:
        self.startTime = calcDate(self.issueTime,self.body[0][0:4])
        self.endTime   = calcDate(self.issueTime,self.body[0][5:9])
      except:
        raise TafError("Incorrect TAF datetime string ("+self.body[0]+")")
   
    # Do secondary checks on datetimes
    if self.startTime > self.endTime:
      raise TafError("Start datetime ahead of end datetime")
    elif self.issueTime  > self.startTime + datetime.timedelta(hours=1):
      raise TafError("Issue datetime ahead of start of forecast")
    elif self.startTime > self.issueTime + datetime.timedelta(hours=10):
      raise TafError("Start of forecast more than 10 hours ahead of issue time")
  #---------------------------------------------------------------------------
  def calcStations(self):
    self.issueStation = self.header[32:36]
    if not regStation.match(self.issueStation):
      raise TafError("Invalid or missing issuing station ID") 
    self.station      = self.header[46:50]
    if not regStation.match(self.station):
      raise TafError("Invalid or missing station ID") 
    #if self.station not in civilList and self.station not in defenceList:
    #  self.warnings.append("Station "+self.station+" not found. Applying civil rules.")
  #---------------------------------------------------------------------------
  def calcCorAmd(self):
    '''See if original (ORG), corrected (COR), ammended (AMD)
    or both corrected and ammended (BOT)'''
   
    if   int(self.header[42]) != 0 and int(self.header[44]) == 0:
      self.status = 'COR'
    elif int(self.header[42]) == 0 and int(self.header[44]) != 0:
      self.status = 'AMD'
    elif int(self.header[42]) != 0 and int(self.header[44]) != 0:
      self.status = 'BOT'
    else:
      self.status = 'ORG'
   
    # Ignore any non-defence TAFs which aren't original
    if self.station not in defenceList and self.status != 'ORG':
      raise TafIgnore()
  #---------------------------------------------------------------------------
  def clusterBody(self):
    self.clusters=[]
    a = 0
    for i in range(a,len(self.body)+1):
      if i == len(self.body) or \
        (regChange.match(self.body[i]) and not regChange.match(self.body[i-1])):
       
        b = i - 1
        self.clusters.append( \
          cluster(self.body[a:i],self.issueTime,self.startTime,self.endTime,self.station,self.compat))
        a = i
       
  #---------------------------------------------------------------------------
  def gatherWarnings(self):
    for clust in self.clusters:
      for warn in clust.warnings:
        self.warnings.append(warn)
  #---------------------------------------------------------------------------
  def toCsv(self):
    '''Function to return a multiline string comprising of
    CSV output.
    The output lines are:
    issue date, issue time, issue station, start date,
    start time, end date, end time, station, change variable,
    variable, value
    '''
    ret = ''
    retHead  = self.issueTime.strftime('%d-%b-%y,%H%M')+","
    retHead += self.issueStation+","
    retHead += "MANL," # Space for future FORECASTER or AUTO keywords
    for cluster in self.clusters:
      for var in cluster.getVariables():
        ret += retHead
        ret += cluster.startTime.strftime('%d-%b-%y,%H%M')+","
        ret += cluster.endTime.strftime('%d-%b-%y,%H%M')+","
        ret += self.station+","
        ret += self.status+","
        ret += cluster.changeVar+","
        ret += var[0]+","+str(var[1])+",\n"
    ret = ret[0:-1]
    return ret
  #---------------------------------------------------------------------------
 
  def toHead(self):
    '''Function to return a single string consisting of the
    original TAF preceded by a CSV header.'''
   
    ret  = self.issueTime.strftime('%d-%b-%y,%H%M')+","
    ret += self.issueStation+","
    ret += "MANL," # Space for future FORECASTER or AUTO keyword
    ret += self.clusters[0].startTime.strftime('%d-%b-%y,%H%M')+","
    ret += self.clusters[0].endTime.strftime('%d-%b-%y,%H%M')+","
    ret += self.station+","
    ret += self.status+","
    ret += self.line
    return ret
#-----------------------------------------------------------------------------
# Cluster class
#-----------------------------------------------------------------------------
class cluster(object):
 
  def __init__(self,line,issueTime,startTime,endTime,station,compat):
    self.line     = line
    self.station  = station
    self.warnings = []
    self.compat   = compat
   
    if (len(line) < 3 and not regFM.match(line[0])) or \
       (len(line) < 2 and     regFM.match(line[0])):
        raise TafError('Cluster too short - abrupt ending')
   
    # Initialise variables
    self.windspeed  = None
    self.winddirect = None
    self.gustspeed  = None
    self.cavok      = None
    self.visibility = None
    self.visUnit    = 'm'
    self.cloud      = []
    self.cumulo     = False
    self.weather    = ''
    self.skyobsc    = False
    self.vvgiven    = False
   
    # Find change variable
    a = 1 # start of cluster
    if line[0] == "PROB30" or line[0] == "PROB40":
      if line[1] == "TEMPO":
        self.changeVar = line[0]+" "+line[1]
        a = 2
      else:
        self.changeVar = line[0]
    elif line[0] == "BECMG" or line[0] == "TEMPO":
      self.changeVar = line[0]
    elif line[0] == "FM":
      self.changeVar = "FM"
      self.warnings.append("Space found between FM and datetime string.")
    elif regFM.match(line[0]):
      line.insert(1,line[0][2:])
      self.changeVar = "FM"
    else:
      self.changeVar = "INIT"
      a = 0
   
    # Parse start and end datetimes (compatibility differences)
    if self.compat:                                     # compatibility mode
      if self.changeVar == "FM":                        # datetime following FM
        if not regComFMstr.match(line[a]):
          raise TafError( \
          "Valid datetime string (FMnnnn) expected where ("+line[a]+") found")
        else:
          try:
            self.startTime = calcDate(issueTime,line[a][0:4])
            self.endTime   = endTime
          except:
            raise TafError("Error in datetime string ("+line[a]+") found")
      else:                                             # regular datetime string
        if not regComDTstr.match(line[a]):
          raise TafError( \
          "Valid datetime string (nnnn[nn]) expected where ("+line[a]+") found")
        else:
          try:
            self.startTime,self.endTime = \
              calcDate(startTime,line[a],True)
          except:
            raise TafError("Error in datetime string ("+line[a]+") found")     
    else:                                               # non-compatibility mode
      if self.changeVar == "FM":                        # datetime following FM
        if not regDTFMstr.match(line[a]):
          raise TafError( \
          "Valid datetime string (FMnnnnnn) expected where ("+line[a]+") found")
        else:
          try:
            self.startTime = calcDate(issueTime,line[a][0:4])
            self.endTime   = endTime
          except:
            raise TafError("Error in datetime string ("+line[a]+") found")
      else:                                             # regular datetime string
        if not regDTstr.match(line[a]):
          raise TafError( \
          "Valid datetime string (nnnn/nnnn) expected where ("+line[a]+") found")
        else:
          try:
            self.startTime = calcDate(issueTime,line[a][0:4])
            self.endTime   = calcDate(issueTime,line[a][5:9])
          except:
            raise TafError("Error in datetime string ("+line[a]+") found")
    # Check datetimes are valid
    if self.startTime > self.endTime:
      raise TafError("Start datetime ahead of end datetime ("+line[a]+")")
    if issueTime > self.startTime + datetime.timedelta(hours=1):
      raise TafError("Issue datetime ahead of start of changeset ("+line[a]+")")
    if self.startTime < startTime or self.endTime > endTime:
      raise TafError("Changeset not within initial forecast datetimes ("+line[a]+")")
    timeDelta = self.endTime - self.startTime
    if self.changeVar == "BECMG" and timeDelta.seconds > 14400:
      self.warnings.append("BECMG lasting for more than 4 hours.")
   
    # Cycle through all elements of 'line'
    a += 1
    while a < len(line):
      # Wind
      if regWind.match(line[a]):
        match = regWind.match(line[a]).group
        if self.windspeed:
          raise TafError("More than one instance of wind in a cluster")
        self.winddirect = match(1)
        self.windspeed  = int(match(2))
        # Check for gustspeeds
        if match(3):
          self.gustspeed = int(match(3)[1:])
        # Convert to MPS
        self.windspeed = convertWinds(self.windspeed,match(4))
        if self.gustspeed:
          self.gustspeed = convertWinds(self.gustspeed,match(4))
      # CAVOK
      elif line[a]=="CAVOK":
        if self.cavok:
          raise TafError("More than one instance of CAVOK in a cluster")
        self.cavok = True
      # Visibility
      elif regVis.match(line[a]):
        match = regVis.match(line[a]).group
        if self.visibility:
          raise TafError("More than one instance of visibility in a cluster")
        self.visibility = int(match(1))
      elif line[a]=="P6SM":
        if self.visibility:
          raise TafError("More than one instance of visibility in a cluster")
        self.visibility = 9999
      # Vis (Miles)
      elif regVisMile.match(line[a]):
        match = regVisMile.match(line[a]).group
        if self.visibility:
          raise TafError("More than one instance of visibility in a cluster")
        # Determine SM or NM
        if match(3) == 'SM':
          conv = smileToM
          self.visUnit = 'sm'
        else:
          conv = nmileToM
          self.visUnit = 'nm'
        # Determine integer or fraction
        if match(2):
          self.visibility = int((float(match(1))/int(match(2)))*conv)
        else:
          self.visibility = int(int(match(1))*conv)
        # 9999 is maximum vis
        if self.visibility > 9999: self.visibility = 9999
      # Cloud
      elif regCloud.match(line[a]):
        match = regCloud.match(line[a]).group
        self.cloud.append((match(1),match(2)))
        # Check for cumulo nimbus
        if match(3)=='CB':
          if self.cumulo:
            raise TafError("More than one instance of cumulo nimbus in a cluster")
          else:
            self.cumulo = True
      # Vertical visibility
      elif regVV.match(line[a]):
        match = regVV.match(line[a]).group
        if self.cloud:
          raise TafError("Vertical visibility given in conjunction with other cloud base")
        if match(1) == "///":
          self.vvgiven = True
          self.cloud.append(("VV","000"))
        else:
          self.cloud.append(("VV",match(1)))
      # No Sig Cloud / Sky Clear
      elif line[a]=="NSC":
        self.cloud.append(("NSC",9999))
      elif line[a]=="SKC":
        self.cloud.append(("SKC",9999))
      # Max temperature
      elif regMaxT.match(line[a]):
        pass
      # Min temperature
      elif regMinT.match(line[a]):
        pass
      # Turbulence
      elif regTurb.match(line[a]):
        pass
      # Weather
      elif regWeather.match(line[a]):
        match = regWeather.match(line[a]).group
        if match(1) == "VC":
          self.warnings.append("TAFs should not contain vicinity weather ("+match(0)+")")
        else:
          try:
            self.skyobsc = max(self.skyobsc,validateWeather(match(1),match(2)))
          except:
            raise TafError('Invalid string found ('+match(0)+')')
      # Element invalid
      else:
        raise TafError("Invalid element found ("+line[a]+")")
       
      a += 1
   
    # Validity checks on cluster
    if self.changeVar == "INIT":
      if self.windspeed is None:
        raise TafError("No wind given on initial forecast")
      if (not self.cavok) and not (self.visibility and self.cloud):
        raise TafError("Missing visibility or significant cloud (or CAVOK) in initial forecast")
    if self.cavok and self.visibility is not None:
      raise TafError("CAVOK given in conjunction with visibility")
    if self.cavok and self.cloud:
      raise TafError("CAVOK given in conjunction with signigicant cloud")
    # Check vis has correct resolution
    if self.visUnit == 'm':
      err,msg = testVisRes(self.visibility)
      if err: raise TafError(msg)
    # Check gust > mean + 5mps
    err,msg = testGstSpd(self.windspeed,self.gustspeed)
    if err: self.warnings.append(msg)
   
    # Define CAVOK
    if self.cavok:
      self.visibility = 9999
      self.cloud = [('NSC',9999)]
     
    # Reduce clouds to single cloudbase and cloud amount pair
    if self.cloud:
      if self.vvgiven and not self.skyobsc:
        self.cloud = None
      elif self.station in defenceList:
        self.cloud = reduceClouds(self.cloud,3)
      else:
        self.cloud = reduceClouds(self.cloud,5)
 
  #---------------------------------------------------------------------------
  def getVariables(self):
    ret = []
   
    if self.windspeed  : ret.append(('WSP',self.windspeed ))
    if self.winddirect and self.winddirect != "VRB":
                         ret.append(('WDR',self.winddirect))
    if self.gustspeed  : ret.append(('GSP',self.gustspeed ))
    if self.visibility : ret.append(('VIS',self.visibility))
    if self.cloud      : 
                         ret.append(('CLA',self.cloud[0]  ))
                         ret.append(('CLB',self.cloud[1]  ))
    if self.cumulo     : ret.append(('CBS',1              ))
       
    return ret
#-----------------------------------------------------------------------------
# Errors
#-----------------------------------------------------------------------------
class TafError(Exception):
  '''Exception to indicate the TAF is incorrect.'''
  pass
 
class TafIgnore(Exception):
  '''Exception to indicate the TAF is corrected,
  ammended, cancelled or null and no furthur
  processing is required.'''
  pass
#-----------------------------------------------------------------------------
# Invoke driver when called interactively
if __name__ == '__main__':
  main()