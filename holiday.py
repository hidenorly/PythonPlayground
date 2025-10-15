#!/usr/bin/env python3
# coding: utf-8
#   Copyright 2025 hidenorly
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import argparse
import datetime
import os
import time

class TenkuraFilterUtil:
  @staticmethod
  def getYYMMDD(yymmdd):
    yy = "0"
    mm = "0"
    dd = "0"

    pos1 = yymmdd.find("/")
    pos2 = yymmdd.rfind("/")
    if pos1!=-1 and pos2!=-1:
      if pos1!=pos2:
        # found yy
        yy = yymmdd[0:pos1]
        mm = yymmdd[pos1+1:pos2]
        dd = yymmdd[pos2+1:len(yymmdd)]
      else:
        mm = yymmdd[0:pos2]
        dd = yymmdd[pos2+1:len(yymmdd)]
    else:
      dd = yymmdd

    return int(yy), int(mm), int(dd)


  @staticmethod
  def ensureYearMonth(yymmdd, refYYMMDD = "", isMMDD=False):
    if refYYMMDD=="":
      refYYMMDD = datetime.datetime.now().strftime("%Y/%m/%d")

    yy1, mm1, dd1 = TenkuraFilterUtil.getYYMMDD(yymmdd)
    yy2, mm2, dd2 = TenkuraFilterUtil.getYYMMDD(refYYMMDD)

    if dd1<dd2:
      mm1 = ( mm2 + 1 ) % 13
      if mm1 == 0:
        mm1 = mm1 + 1

    if mm1 == 0:
      mm1 = mm2

    if yy1<yy2:

      yy1 = yy2
      if mm1<mm2:
        yy1 = yy1 + 1

    result = "{:04d}".format(yy1)+"/"+"{:02d}".format(mm1)+"/"+"{:02d}".format(dd1)
    if isMMDD:
      result = "{:02d}".format(mm1)+"/"+"{:02d}".format(dd1)
    return result


  @staticmethod
  def getListOfRangedDates(fromDay, toDay, isMMDD=False):
    result = []

    fromDay = TenkuraFilterUtil.ensureYearMonth( fromDay, "" )
    toDay = TenkuraFilterUtil.ensureYearMonth( toDay, fromDay )

    fromDay = TenkuraFilterUtil.getDateTimeFromYYMMDD( fromDay )
    toDay = TenkuraFilterUtil.getDateTimeFromYYMMDD( toDay )

    theDay = fromDay
    dateFormat = "%Y/%m/%d"
    if isMMDD:
      dateFormat = "%m/%d"
    while theDay <= toDay:
      result.append( theDay.strftime( dateFormat ) )
      theDay = theDay + datetime.timedelta(days=1)

    return result

  @staticmethod
  def getListOfDates(dateOptionString):
    result = []

    commaValues = dateOptionString.split(",")
    for aValue in commaValues:
      aValue = aValue.strip()
      rangedValue = aValue.split("-")
      if len( rangedValue ) == 2:
        result.extend( TenkuraFilterUtil.getListOfRangedDates( rangedValue[0].strip(), rangedValue[1].strip() ) )
      else:
        if not aValue:
          result.append( aValue )
        else:
          result.append( TenkuraFilterUtil.ensureYearMonth( aValue, "", False ) )

    if len(result) == 0:
      result = [ dateOptionString ]

    return result

  @staticmethod
  def isMatchedDate(key, targetDateMMDDs):
    result = False
    for targetDateMMDD in targetDateMMDDs:
      if targetDateMMDD=="" or TenkuraFilterUtil.getDateTimeFromYYMMDD(key) == TenkuraFilterUtil.getDateTimeFromYYMMDD(targetDateMMDD):
        result = True
        break

    return result

  @staticmethod
  def getCleanedDateKey(dateKey):
    pos = dateKey.rfind("(")
    if pos!=-1:
      dateKey = dateKey[0:pos]
    return dateKey

  @staticmethod
  def getMaxDateYYMMDD(climbRates):
    result = ""
    score = TenkuraFilterUtil.getDateTimeFromYYMMDD("")
    foundKey = ""
    for key, arrayData in climbRates.items():
      currentScore = TenkuraFilterUtil.getDateTimeFromYYMMDD(key)
      if currentScore > score:
        score = currentScore
        foundKey = key

    if foundKey:
        maxDate = TenkuraFilterUtil.getDateTimeFromYYMMDD( foundKey )
        result = maxDate.strftime('%Y/%m/%d')

    return result

  @staticmethod
  def isYearIncluded(yymmdd):
    yymmdd = str(yymmdd)
    pos1 = yymmdd.find("/")
    pos2 = yymmdd.rfind("/")
    result = False
    if pos1!=-1 and pos2!=-1 and pos1!=pos2:
      result = True
    return result

  @staticmethod
  def getDateTimeFromYYMMDD(yymmdd):
    yymmdd = str(yymmdd)
    yymmdd = TenkuraFilterUtil.getCleanedDateKey(yymmdd)
    if yymmdd=="":
      yymmdd="1/1"

    if not TenkuraFilterUtil.isYearIncluded(yymmdd):
      yymmdd = datetime.datetime.now().strftime("%Y") + "/" + yymmdd

    return datetime.datetime.strptime(yymmdd, "%Y/%m/%d")

  @staticmethod
  def getDateRangeFilterForWeek(weeklyArrayData, startDateTime, targetDateTime):
    result = []
    currentDateTime = startDateTime
    for aData in weeklyArrayData:
      if currentDateTime == targetDateTime:
        result.append( aData )
      currentDateTime = currentDateTime + datetime.timedelta(days=1)

    return result


  @staticmethod
  def getWeekEndDates(startDateTime):
    result = []
    currentDateTime = startDateTime
    theRange = 8 if currentDateTime.weekday() == 6 else 7

    for i in range(theRange):
      weekDay = currentDateTime.weekday()
      if weekDay == 5 or weekDay == 6:
        result.append( currentDateTime )
      currentDateTime = currentDateTime + datetime.timedelta(days=1)

    return result

  @staticmethod
  def getWeekEndYYMMDD(startDateTime, isMMDD=True):
    weekendDateTimes = TenkuraFilterUtil.getWeekEndDates(startDateTime)
    result = []
    dateFormat = '%Y/%m/%d'
    if isMMDD:
      dateFormat = '%m/%d'
    for theDateTime in weekendDateTimes:
      result.append( TenkuraFilterUtil.ensureYearMonth(theDateTime.strftime( dateFormat ), "", isMMDD ))

    return result

  try:
    # pip install jpholiday
    from jpholiday import JPHoliday
    jpholiday = JPHoliday()
  except:
    pass

  @staticmethod
  def getWeekEndYYMMDDWithJpHolidays(startDateTime, isMMDD=True, search_range=2):
    weekendDateTimes = TenkuraFilterUtil.getWeekEndDates(startDateTime)
    if len(weekendDateTimes) >= 2:
      weekendDateTimes2 = set(weekendDateTimes)
      try:
        _day = datetime.datetime.now()
        if TenkuraFilterUtil.jpholiday.is_holiday( _day ):
          weekendDateTimes2.add( _day )
      except:
        pass
      for day in weekendDateTimes:
        for i in range(search_range):
          try:
            _day = day - datetime.timedelta(days=i)
            if TenkuraFilterUtil.jpholiday.is_holiday( _day ):
              weekendDateTimes2.add( _day )
            _day = day + datetime.timedelta(days=i)
            if TenkuraFilterUtil.jpholiday.is_holiday( _day ):
              weekendDateTimes2.add( _day )
          except:
            pass
      weekendDateTimes = sorted( weekendDateTimes2 )
    result = []
    dateFormat = '%Y/%m/%d'
    if isMMDD:
      dateFormat = '%m/%d'
    for theDateTime in weekendDateTimes:
      result.append( TenkuraFilterUtil.ensureYearMonth(theDateTime.strftime( dateFormat ), "", isMMDD ))

    return result

  @staticmethod
  def getDispDays(weeklyDates):
    weeklyDays = ""
    lastMonth = ""

    for aDay in weeklyDates:
      theDay = aDay
      if theDay.startswith("0"):
        theDay = theDay[1:len(theDay)]
      posMonth = theDay.find("/")
      if posMonth!=-1:
        if lastMonth == theDay[0:posMonth]:
          theDay = theDay[posMonth+1:len(theDay)]
        else:
          lastMonth = theDay[0:posMonth]
      weeklyDays = weeklyDays + "," + theDay
    if weeklyDays.startswith(","):
      weeklyDays = weeklyDays[1:len(weeklyDays)]

    return weeklyDays

  @staticmethod
  def dateSortUtil(dateString):
    dateString = TenkuraFilterUtil.ensureYearMonth(dateString)
    year, month, day = TenkuraFilterUtil.getYYMMDD(dateString)
    return int(year)*403+ int(month) * 31 + int(day)




if __name__=="__main__":
  parser = argparse.ArgumentParser(description='Parse command line options.')
  parser.add_argument('args', nargs='*', help='mountain name such as 富士山')
  parser.add_argument('-d', '--date', action='store', default='', help='specify date e.g. 2/14,2/16-2/17')
  parser.add_argument('-dw', '--dateweekend', action='store_true', help='specify if weekend (Saturday and Sunday)')
  args = parser.parse_args()

  specifiedDate = TenkuraFilterUtil.getListOfDates( args.date )
  if args.dateweekend:
    weekEndDates = TenkuraFilterUtil.getWeekEndYYMMDDWithJpHolidays( datetime.datetime.now(), False )
    specifiedDate.extend(weekEndDates)
    specifiedDate = list(set(filter(None,specifiedDate)))
    specifiedDate.sort(key=TenkuraFilterUtil.dateSortUtil)

  # ensure MM/DD for display
  result = []
  for aDay in specifiedDate:
    if aDay:
      result.append( TenkuraFilterUtil.ensureYearMonth(aDay, "", True) )
    else:
      result.append( aDay )
  specifiedDate = result


  print(str(specifiedDate))