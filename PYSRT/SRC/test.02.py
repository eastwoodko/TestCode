#!/usr/bin/env python
#-*- coding: utf-8 -*-

import traceback
import argparse
import sys
import os
import chardet
import re

from collections import namedtuple
try:
    sys.path.append('.')
    from utils import time as srtTime
    from utils import utils as myUtils
except ImportError:
    SRCPATH=os.path.dirname(os.path.abspath(__file__))
    sys.path.append(SRCPATH)
    import utils.time as srtTime
    import utils.utils as myUtils

def convert_utf8(str):
    ret = chardet.detect(str)
    chset = ret['encoding']  ##.lower()

    retUTF8 = str
    if chset == 'ascii' :
        return chset, retUTF8

    try:
        # retUTF8 = str.decode(chset).encode('utf8')
        retUTF8 = unicode(str,'euc-kr').encode('utf-8')
    except Exception as e:
        # print ("ERROR::01::{0}".format(traceback.format_exc()))
        try:
            if chset == None or chset == "TIS-620":
                retUTF8 = unicode(str,'cp949').encode('utf-8')
            else:
                retUTF8 = unicode(str,chset).encode('utf-8')
        except Exception as e:
            # print ("ERROR::02::{0} :: {1}".format(traceback.format_exc(),retUTF8))
            retUTF8 = str

    # print ("ORG [{2}]===>> chset [{0}] ===> UTF8 [{1}]".format(chset, retUTF8, str))
    return chset, retUTF8

def convert_encode(str, encode='utf-8'):
    ret = chardet.detect(str)
    chset = ret['encoding']

    retUTF8 = str
    if chset == 'ascii' or chset == None or chset.lower() == encode.lower():
        return chset, retUTF8

    try:
        retUTF8 = str.decode(chset).encode(encode)
    except Exception as e:
        # print ("ERROR::01::{0}".format(traceback.format_exc()))
        try:
            if chset == None or chset == "TIS-620":
                retUTF8 = unicode(str,'cp949').encode('utf-8')
            else:
                retUTF8 = unicode(str,chset).encode('utf-8')
        except Exception as e:
            # print ("ERROR::02::{0} :: {1}".format(traceback.format_exc(),retUTF8))
            retUTF8 = str

    # print ("ORG [{2}]===>> chset [{0}] ===> UTF8 [{1}]".format(chset, retUTF8, str))
    return chset, retUTF8


def convert_srtTime(inputtime):
    error = None

    offset_ok = re.match('(\d{1,2}:)?(\d{1,2}:)?\d+(,\d{1,3})?$', inputtime)

    if not offset_ok:
        # print('{} is not a valid offset, format is [HH:][MM:]SS[,sss], see help'
        #       'dialog for some examples'.format(inputtime))
        error = True
    else:
        offset = re.search('((\d{1,2}):)?((\d{1,2}):)?(\d+)(,(\d{1,3}))?', inputtime)
# 시분초,m
# 0 ---search result : 01:02:45,010
# 1 ---search result : 01:
# 2 ---search result : 01
# 3 ---search result : 02:
# 4 ---search result : 02
# 5 ---search result : 45
# 6 ---search result : ,010
# 7 ---search result : 010
# 분초,m
# ---search result : 02:45,010
# ---search result : 02:
# ---search result : 02
# ---search result : None
# ---search result : None
# ---search result : 45
# ---search result : ,010
# ---search result : 010

# 초, m
# ---search result : 45,010
# ---search result : None
# ---search result : None
# ---search result : None
# ---search result : None
# ---search result : 45
# ---search result : ,010
# ---search result : 010

# 초 only :: re.match('^\d+(,(\d{1,3}))?$'
# ---search result : 45
# ---search result : None
# ---search result : None
# ---search result : None
# ---search result : None
# ---search result : 45
# ---search result : None
# ---search result : None

        def nsafe(x): return offset.group(x) if offset.group(x) else "0"
        if offset.group(2) != None and offset.group(4) != None:
            hours = nsafe(2)
            minutes = nsafe(4)
        else:
            hours = "0"
            minutes = nsafe(2)

        # the ljust call is because we want e.g. '2.5' to be interpreted as
        # 2 seconds, 500 millis
        # minutes, seconds, millis = (nsafe(3), nsafe(4), nsafe(6).ljust(3, '0'))
        seconds, millis = (nsafe(5), nsafe(7).ljust(3, '0'))

        if re.match('^\d+(,(\d{1,3}))?$', inputtime):
            # format is seconds(,millis), convert to minutes
            secs = int(seconds)
            minutes = str(secs // 60)
            seconds = str(secs % 60)
            # print ("Result (sec Only):: {},{},{}".format(minutes, seconds, millis))

    if error:
        return None

    # print ("Result :: {}:{}:{},{}".format(hours, minutes, seconds, millis))

    return hours, minutes, seconds, millis



class SyncParser(argparse.ArgumentParser):
    """A parser that displays argparse's help message by default."""

    def error(self, message):
        self.print_help()
        sys.exit(1)

class SrtTimeSync(object):
    '''
1
00:00:26,951 --> 00:00:28,176
"Eres...

===>
36870 -> 40957

1
00:00:36,870 --> 00:00:40,957
"Eres...
    '''

    DEFAULT_START_AT = "same as input; original .srt file will be copied to "\
        "ORIGINAL_SRT_NAME_orig.srt"

    def __init__(self, orgFname=None):

        self.SRT_DATA = []
        self.start_offset = None
        self.adjustTime = 0

        self.orgFname = ''
        self.syncFname = ''

        self.encode = 'utf8'
        self.encodeYN = False

        self.parser = SyncParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)

        self.parser.add_argument("-aj", "--adjust_time",
                           help='''make subtitles appear later.
                        ADJUST format is

                           B [mm:]SS[,sss]. (Backword : -)
                           F [mm:]SS[,sss]. (Forward or None : +)

                        Examples: "1:23,456" (subs delayed of 1 minute, 23
                        seconds, 456 milliseconds)''',
                        metavar="STRING")

        self.parser.add_argument("-s", "--start_at",
                           help="""make the first subtitle appear at a specific
                           time. The script will show a list of lines taken
                           from the .srt file to choose what's the first line
                           to be displayed at TIME.""",
                           metavar="TIME")

        self.parser.add_argument("-c", "--convert_to",
                                 help="convert to .srt subtitles file",
                                 metavar='utf-8')

        self.parser.add_argument("-o", "--output",
                                 help="the output .srt subtitles file",
                                 default=self.DEFAULT_START_AT)

        self.parser.add_argument("input_file", type=str,
                                 help="the .srt subtitles file")



    def setFilename(self, fname):
        self.orgFName = fname

        workPath = os.path.dirname(os.path.realpath(fname))
        workName = os.path.basename(fname)
        workList = os.path.splitext(workName)

        self.syncFname="{0}/{1}.fixed.srt".format(workPath, workList[0])

        return self.syncFname

    def srtDataAppend(self, srtLine, content):
        if self.encodeYN:
            srtLine[5], srtLine[4] = convert_utf8(content)
        else:
            srtLine[4] = content

        self.SRT_DATA.append(srtLine)
        # print ("srtLine :: {} ".format(srtLine))


    def srtSyncParsing(self):
        with open(self.orgFname) as f_in:
             lines = filter(None, (line.rstrip() for line in f_in))

        idx = 0
        content = ''

        SRT_Line = [0, 0, 0, 0, '', ''] ## Num, cnt, stime, etime, contents, lang

        time00 = ''
        lang = ''

        SRT_Line[0] = 0
        SRT_Line[1] = 1

        for idx, line in enumerate(lines[1:],1):
            checkNum = line.isdigit()
            # print ("{0},[{2}], {1}".format(idx, line, checkNum))

            if checkNum:
                self.srtDataAppend(SRT_Line, content)

                SRT_Line = [0, 0, 0, 0, '', '']     ## 이것이 없으면 맨 마지막 자료만 들어감.
                SRT_Line[0] = idx
                SRT_Line[1] = line

                content = ''
            else:
                tmp = line.split(" --> ")
                try:
                    tData = [convert_srtTime(tmp[0])]
                except:
                    tData = [None]

                if tData != [None]:
                    SRT_Line[2] = srtTime.timestamp_to_ms(srtTime.TIMESTAMP.match(tmp[0]).groups()) ## stime
                    SRT_Line[3] = srtTime.timestamp_to_ms(srtTime.TIMESTAMP.match(tmp[1]).groups()) ## etime
                else:
                    if content != '':
                        content = "{}<br>{}".format(content, line)
                    else:
                        content = line

        ## End For
        ## last data process
        self.srtDataAppend(SRT_Line, content)

        # for idx, line in enumerate(self.SRT_DATA):
        #      print ("IDX : {} ==> {}".format(idx, line))

    def srtSync(self):
        self.srtSyncParsing()

    def srtFirstWrite(self):
        # self.syncFname, self.SRT_DATA
        idx = 0
        srtIDX = 0
        lastIdx = len(self.SRT_DATA)
        with open(self.syncFname, 'w') as f_out:
            while 1:
                srtln = self.SRT_DATA[idx]
                srtIDX += 1
                srtContent = "{0}\n{1} --> {2}\n{3}\n\n".format(srtIDX,
                                                                srtTime.ms_to_str(srtln[2] + self.adjustTime, True),
                                                                srtTime.ms_to_str(srtln[3] + self.adjustTime, True),
                                                                srtln[4])
                srtContent = srtContent.replace("<br>", "\n")
                f_out.write(srtContent)

                idx += 1
                if idx >= lastIdx:
                    break;

    def check_args(self, args):
        """
        Checks that command-line arguments are valid.

        """

        input_file = args.input_file
        convert_opt = args.convert_to
        input_offset = args.start_at
        input_adjust = args.adjust_time
        input_adjustTime = 0
        minutes = 0
        seconds = 0
        millis = 0

        if not os.path.isfile(input_file):
            print('{} does not exist'.format(input_file))
            return None
        else:
            if not args.output or args.output == self.DEFAULT_START_AT:
                output_subs = self.setFilename(input_file)
            else:
                output_subs = args.output

        if convert_opt is not None:
            self.encode = convert_opt
            self.encodeYN = True

        if input_offset is not None:
            try:
                hours, minutes, seconds, millis = convert_srtTime(input_offset)
            except:
                return None

            # print ("{}, {},{},{}".format(hours, minutes, seconds, millis))

        if input_adjust is not None:
            if input_adjust[0].isdigit():
                try:
                    hours, minutes, seconds, millis = convert_srtTime(input_adjust)
                except:
                    return None
            else:
                tmp = [True if x.isdigit() else False for x in input_adjust[:]]
                ## [False, False, True, True, False, True, True, False, True, True, True]
                ## [False, True, True, False, True, True, False, True, True, True]
                for idx,x in enumerate(tmp):
                    if x:
                        try:
                            hours, minutes, seconds, millis = convert_srtTime(input_adjust[idx:])
                            if "b" in input_adjust or "B" in input_adjust:
                                # print "Backword ::",type(minutes), minutes, seconds, millis
                                # input_adjustTime = "-{0:02d}:{1:02d},{2:03d}".format(int(minutes), int(seconds), int(millis))
                                input_adjustTime = -((int(minutes) * 60 + int(seconds)) * 1000 + int(millis))
                            else:
                                # print "Forword ::",minutes, seconds, millis
                                # input_adjustTime = "+{0:02d}:{1:02d},{2:03d}".format(int(minutes), int(seconds), int(millis))
                                input_adjustTime = (int(minutes) * 60 + int(seconds)) * 1000 + int(millis)
                        except Exception as e:
                            # print ("{}".format(e))
                            return None
                        break;

        return input_file, output_subs, input_offset, input_adjustTime

    def srtWrite(self):
        self.srtFirstWrite()
        print("Writing compleate {0} !!!".format(self.syncFname))

    def syncsrt(self):
        args = self.parser.parse_args()
        parsed = self.check_args(args)

        if not parsed:
            print('')
            self.parser.error('Bad arguments.')

        # print("Args Checking ===> {0}".format(parsed))
        self.orgFname, self.syncFname, self.start_offset, self.adjustTime = parsed
        # print("Args Checking After ===> {},{},{},{}".format(self.orgFname, self.syncFname, self.start_offset, self.adjustTime))

        self.srtSync()
        self.srtWrite()
        print("synchronization compleate {0} !!!".format(self.orgFname))

##------------------------------------------------------------ end Class Smi2Srt

def converting_test(fname):
    with open(fname) as f_in:
         lines = filter(None, (line.rstrip() for line in f_in))

    for ln in lines:
        chset, retUTF8 = convert_utf8(ln)
        print ("ORG [{2}]===>> chset [{0}] ===> UTF8 [{1}]".format(chset, retUTF8, ln))

if __name__ == '__main__':
    '''
python ./test.02.py -s "01:45,010" -aj '-01,450'  ./Travelers1x01-Travelers.utf8.srt
for i in /opt/PYSRT/Data/smi2/*.smi; do python ./test.01.py "$i"; done

$ python ./test.02.py -s 0:01,234 -aj "+01,450"  ./Travelers1x01-Travelers.utf8.srt
First :: ['./test.02.py', '-s', '0:01,234', '-aj', '+01,450', './Travelers1x01-Travelers.utf8.srt']
Args Checking ===> ('./Travelers1x01-Travelers.utf8.srt', './Travelers1x01-Travelers.utf8.srt', '0', '01', '234', '+01,450')
$


$ python ./test.02.py -s 0:01,234 -aj "-01,450"  ./Travelers1x01-Travelers.utf8.srt
==> parsing ERROR.....


$ python ./test.02.py -h
usage: test.02.py [-h] [-aj STRING] [-s TIME] [-c utf-8] [-o OUTPUT]
                  input_file

positional arguments:
  input_file            the .srt subtitles file

optional arguments:
  -h, --help            show this help message and exit
  -aj STRING, --adjust_time STRING
                        make subtitles appear later. ADJUST format is B
                        [mm:]SS[,sss]. (Backword : -) F [mm:]SS[,sss].
                        (Forward or None : +) Examples: "1:23,456" (subs
                        delayed of 1 minute, 23 seconds, 456 milliseconds)
                        (default: None)
  -s TIME, --start_at TIME
                        make the first subtitle appear at a specific time. The
                        script will show a list of lines taken from the .srt
                        file to choose what's the first line to be displayed
                        at TIME. (default: None)
  -c utf-8, --convert_to utf-8
                        convert to .srt subtitles file (default: None)
  -o OUTPUT, --output OUTPUT
                        the output .srt subtitles file (default: same as
                        input; original .srt file will be copied to
                        ORIGINAL_SRT_NAME_orig.srt)

    '''
    # print ("First :: {}".format(sys.argv))

    converting = SrtTimeSync()
    converting.syncsrt()
