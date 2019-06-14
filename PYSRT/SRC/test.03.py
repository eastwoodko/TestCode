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

##==============================================================================

class SyncParser(argparse.ArgumentParser):
    """A parser that displays argparse's help message by default."""

    def error(self, message):
        self.print_help()
        sys.exit(1)

##==============================================================================
class SrtCombine(object):
    '''
    SrtCombine

    '''

    DEFAULT_START_AT = "same as basefile; original .srt file will be copied to "\
        "ORIGINAL_SRT_NAME.comb.srt"

    def __init__(self, orgFname=None):

        self.SRT_DATA = []

        self.basefile = ""
        self.inputfiles = []
        self.outfile = ''

        self.encode = 'utf8'
        self.encodeYN = False

        self.parser = SyncParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)

        self.parser.add_argument("-b", "--basefile",
                        help='''기준이 되는 script. (필수 옵션)''',
                        metavar="STRING",
						required=True)

        self.parser.add_argument("-i", "--inputfiles",
                           help="""기준파일에 합쳐질 파일 리스트""",
                           metavar="STRING")

        self.parser.add_argument("-o", "--output",
                                 help="the output .srt subtitles file",
                                 default=self.DEFAULT_START_AT)

    def check_args(self, args):
        """
        Checks that command-line arguments are valid.

        """

        self.basefile = args.basefile
        input_files   = args.inputfiles

        if not os.path.isfile(self.basefile):
            print('BASEFILE : {} does not exist'.format(self.basefile))
            return None

        if not args.output or args.output == self.DEFAULT_START_AT:
            workPath = os.path.dirname(os.path.realpath(self.basefile))
            workName = os.path.basename(self.basefile)
            workList = os.path.splitext(workName)

            self.outfile="{0}/{1}.comb.srt".format(workPath, workList[0])
        else:
            self.outfile = args.output

        self.inputfiles = input_files.split(",")

        if len(self.inputfiles) < 1 or not os.path.isfile(self.inputfiles[0]):
            print('inputfiles : {} does not exist'.format(self.inputfiles))
            return None

        return self.basefile, self.inputfiles, self.outfile

    def srtWrite(self):
        idx = 0
        srtIDX = 0
        lastIdx = len(self.SRT_DATA)
        with open(self.outfile, 'w') as f_out:
            while 1:
                srtln = self.SRT_DATA[idx]
                srtIDX += 1
                srtContent = "{0}\n{1} --> {2}\n{3}\n\n".format(srtIDX,
                                                                srtTime.ms_to_str(srtln[2], True),
                                                                srtTime.ms_to_str(srtln[3], True),
                                                                srtln[4])
                srtContent = srtContent.replace("<br>", "\n")
                f_out.write(srtContent)

                idx += 1
                if idx >= lastIdx:
                    break;

        print("Writing compleate {0} !!!".format(self.outfile))

    def srtDataAppend(self, srtLine, content, srtData):
        if self.encodeYN:
            srtLine[5], srtLine[4] = convert_utf8(content)
        else:
            srtLine[4] = content

        srtData.append(srtLine)
        # print ("srtLine :: {} ".format(srtLine))

    def srtSyncParsing(self, fname, srtData):
        with open(fname) as f_in:
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
                self.srtDataAppend(SRT_Line, content, srtData)

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
        self.srtDataAppend(SRT_Line, content, srtData)

    def combineInputs(self, inputData):
        '''
        base가 짧을 경우 : inputData를 base에 추가 ?
        시간 편차가 시작점 500, 종료점 200 으로 고정 ?
        inputData가 base n과 n+1 사이에 위치한 경우 : base의 n과 n+1사이에 insert ?
        '''
        idx = 0
        iSeq = 0

        # SRT_Line = [0, 0, 0, 0, '', ''] ## Num, cnt, stime, etime, contents, lang
        while idx < len(self.SRT_DATA) and iSeq < len(inputData):
            line = self.SRT_DATA[idx]
            src = inputData[iSeq]

            subsS = line[2] - src[2]
            subsE = line[3] - src[3]

            if subsS == 0 or abs(subsS) <= 500 or abs(subsE) <= 200:
                line[4] = "{}<br>{}".format(line[4], src[4])
                idx += 1
                iSeq += 1
            elif line[2] > src[2]:
                iSeq += 1
            else:
                idx += 1

    def combine(self):
        ## basefile parse
        self.srtSyncParsing(self.basefile, self.SRT_DATA)
        # print ("{} : {}".format(self.basefile, len(self.SRT_DATA)))
        # for idx, line in enumerate(self.SRT_DATA):
        #     print ("IDX : {} ==> {}".format(idx + 1, line))

        ## inputfiles parse
        inputDatas =[]
        for inData in self.inputfiles:
            tmp = []
            self.srtSyncParsing(inData, tmp)
            inputDatas.append(tmp)

        # for idx0, iData in enumerate(inputDatas):
        #     print ("{} : {}".format(self.inputfiles[idx0], len(iData)))
        #     for idx, line in enumerate(iData):
        #         print ("IDX : {} ==> {}".format(idx, line))

        for iData in inputDatas:
            self.combineInputs(iData)

        # for idx, line in enumerate(self.SRT_DATA):
        #     print ("IDX : {} ==> {}".format(idx + 1, line))

        self.srtWrite()

##==============================================================================

if __name__ == '__main__':
    '''
python ./test.03.py -b ./Elite.S01/Élite.S01E01.1080p.NF.WEB-DL.DDP5.1.x264-MZABI_track5_\[spa\].srt \
                    -i ./Elite.S01/Élite.S01E01.1080p.NF.WEB-DL.DDP5.1.x264-MZABI_track25_\[kor\].srt,Elite.S01/Élite.S01E01.1080p.NF.WEB-DL.DDP5.1.x264-MZABI_track4_\[eng\].srt \
                    -o ./Elite.S01/Élite.S01E01.1080p.NF.WEB-DL.DDP5.1.x264-MZABI_track5_\[spa\].comb.srt

for i in {1..8}; do python ./test.03.py \
    -b ./Elite.S01/Élite.S01E0${i}.1080p.NF.WEB-DL.DDP5.1.x264-MZABI_track5_\[spa\].srt \
    -i ./Elite.S01/Élite.S01E0${i}.1080p.NF.WEB-DL.DDP5.1.x264-MZABI_track25_\[kor\].srt ; \
    done
    '''

    combine = SrtCombine()
    args = combine.parser.parse_args()
    parse = combine.check_args(args)
    if not parse:
        print('')
        combine.parser.error('Bad arguments.')

    # print ("Parsed :: {}".format(parse))
    # print ("First  :: {}".format(args))

    combine.combine()
