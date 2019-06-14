#!/usr/bin/env python
#-*- coding: utf-8 -*-
#
# (c) 2016,2017 Eastwood Lee <eastwoodko@sptek.co.kr>
#
# This file is part of Ansible for Heimdall Cloud Node Control.
#

import argparse
# import glob2
import itertools
import logging
from logging.handlers import RotatingFileHandler
import platform
import re
import os
import sys
import time
import subprocess
# import psutil

import yaml
import json
import copy

# import requests

logging.basicConfig()

# def parse_args():
#     epilog_example = """
#     Please see the readme for complete examples.
#     """
#     parser = argparse.ArgumentParser(description='logfile shipper', epilog=epilog_example, formatter_class=argparse.RawDescriptionHelpFormatter)
#     # parser.add_argument('-d', '--debug', help='enable debug mode', dest='debug', default=False, action='store_true')
#     # parser.add_argument('-l', '--logfile', '-o', '--output', help='file to pipe output to (in addition to stdout)', default=None, dest='output')
#     # parser.add_argument('-j', '--jsonfile', action='store', dest='jsonfile', help='json files for ansible work',default='')
#     # parser.add_argument('-w', '--workfile', action='store', dest='workfile', help='Working hostlist',default='')
#     # parser.add_argument('--max-bytes', action='store', dest='max_bytes', type=int, default=64 * 1024 * 1024, help='Maximum bytes per a logfile.')
#     # parser.add_argument('--backup-count', action='store', dest='backup_count', type=int, default=1, help='Maximum number of logfiles to backup.')
#     #
#     # parser.add_argument('--ip', action='store', dest='ipaddr', help='Working Remote Host IP',default='')
#     # parser.add_argument('--actionfile', action='store', dest='actfile', help='Working Remote Host IP Action List File',default='')
#     # parser.add_argument('--inventory', action='store', dest='invfile', help='Working Remote Host IP Inventory File',default='')
#     # parser.add_argument('--type', action='store', dest='agentype', help='Working Remote Host Target Type(METRIC, LOG, CHECK)',default='')
#     # parser.add_argument('--cmd', action='store', dest='cmd', help='Working Remote Host Runnung Command',default='')
#     #
#     # parser.add_argument('--fullset', action='store', dest='fullset', help='For Working Remote Host Full Infomation',default='')
#
#     args = parser.parse_args()
#
#     return args


# ####################################### Log Seeting
# def settingLog():
#     # LOG_FORMAT = '%(asctime)-15s %(levelname)s: %(message)s'
#     # log_format = '%%(asctime)s | %%(levelname)s | %s | %%(name)s(%%(filename)s:%%(funcName)s:%%(lineno)s) | %%(message)s' % 'jsonparser'
# LOG_FORMAT_DEBUG = '%%(asctime)s | %%(levelname)-7s | %s | %%(name)s(%%(filename)s:%%(funcName)s:%%(lineno)s) | %%(message)s' % __file__
LOG_FORMAT_DEBUG = '%(asctime)s | %(levelname)s | %(filename)s:%(funcName)s:%(lineno)s | %(message)s'
LOG_FORMAT_INFO  = '%(asctime)s | %(levelname)s | %(message)s'

#     log_format = '%%(asctime)s | %%(levelname)s | %s | %%(name)s(%%(funcName)s:%%(lineno)s) | %%(message)s' % __file__
#                  '[%(asctime)s] %(levelname)-7s %(message)s'
#     ## REF :: monasca-agent-1.3.0/monasca_agent/common/util.py ==> def initialize_logging(logger_name)
#     ##     :: https://docs.python.org/2/library/logging.html
#
#     # import logging.handlers
#     # file_max_bytes = 10 * 1024 * 1024
#     # fileHandler = logging.handlers.RotatingFileHandler(filename='./log/test.log', maxBytes=file_max_bytes, backupCount=10)
#     # DEBUG:root:디버깅용 로그~~
#     # INFO:root:도움이 되는 정보를 남겨요~
#     # WARNING:root:주의해야되는곳!
#     # ERROR:root:에러!!!
#     # CRITICAL:root:심각한 에러!!
#
#     logging.basicConfig(filename = "./heimdalljsonparse.log",
#                         filemode = "a",
#                         level = logging.DEBUG,
#                         format = log_format)
def setup_custom_logger(name, args=None, output=None, formatter=None, debug=None, max_bytes=None, backup_count=None):
    logger = logging.getLogger(name)
    logger.propagate = False

    if logger.handlers:
        logger.handlers = []
    print ('argparse.Namespace : ' + str(argparse.Namespace))
    print ('args : ' + str(args))

    has_args = args is not None and type(args) == argparse.Namespace
    if debug is None:
        debug = has_args and args.debug is True

    if not logger.handlers:
        if formatter is None:
            if debug:
                formatter = logging.Formatter(LOG_FORMAT_DEBUG)
            else:
                formatter = logging.Formatter(LOG_FORMAT_INFO)

        if output is None and has_args:
            output = args.output

        if output:
            output = os.path.realpath(output)

        if output is not None:
            if has_args and backup_count is None:
                backup_count = args.backup_count

            if has_args and max_bytes is None:
                max_bytes = args.max_bytes

            if backup_count is not None and max_bytes is not None:
                assert backup_count > 0
                assert max_bytes > 0
                ch = RotatingFileHandler(output, 'a', max_bytes, backup_count)
                if formatter is not False:
                    ch.setFormatter(formatter)
                logger.addHandler(ch)
            else:
                file_handler = logging.FileHandler(output)
                if formatter is not False:
                    file_handler.setFormatter(formatter)
                logger.addHandler(file_handler)
        else:
            handler = logging.StreamHandler()

            if formatter is not False:
                handler.setFormatter(formatter)

            logger.addHandler(handler)

    if debug:
        logger.setLevel(logging.DEBUG)
        if hasattr(logging, 'captureWarnings'):
            logging.captureWarnings(True)
    else:
        logger.setLevel(logging.INFO)
        if hasattr(logging, 'captureWarnings'):
            logging.captureWarnings(False)

    # logger.debug('Logger level is {0}'.format(logging.getLevelName(logger.level)))
    logger.info('TEST INFO Args : {}'.format(args))

    return logger

##==============================================================================
def workEnvMake(fname, args=None):
    """
    Separating Working Directory & Filename
    """

    WorkEnv = [ ".", ".", ".", "." ]

    WorkEnv[0] = os.path.basename(fname)        ## FileName Only
    WorkEnv[1] = os.path.dirname(os.path.realpath(fname))
    fnameNotExt = os.path.splitext(WorkEnv[0])
    WorkEnv[2] = fnameNotExt[0]                 ## Filename not Extension

    WorkEnv[3] = WorkEnv[1] + fnameNotExt[0]

    WORK_DIR = WorkEnv[1]

    return WorkEnv, WORK_DIR

##==============================================================================
def subprocess_open(command):
    popen = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    (stdoutdata, stderrdata) = popen.communicate()
    return stdoutdata, stderrdata


def _remove_empty(array):
    return [x for x in array if x !='']

##==============================================================================

def _write_jsonData(json_file, jsonData):
    try:
        with open(json_file, 'w') as outfile:
            json.dump(jsonData, outfile)
        return True, ""
    except Exception as err:
        # log.warn("\tSave JSON data as file :: {}, err: {} => {}".format(json_file, err.errno, err.strerror))
        msg = "\tSave JSON data as file :: {}, err: {} => {}".format(json_file, err.errno, err.strerror)
        # Json to Write File :: /usr/lib/monasca/agent/conf.d/agent_extra.json, eN0: 13 => Permission denied
        return False, msg

def _read_jsonData(json_file):
    try:
        with open(json_file, 'r') as infile:
            return json.load(infile), ""
    except IOError:
        # log.warn("\tUnable to read {}".format(json_file))
        msg = "\tUnable to read {}".format(json_file)
        return {}, msg
    except Exception as err:
        # log.warn("\tRead JSON data as file :: {}, err: {} => {}".format(json_file, err.errno, err.strerror))
        msg = "\tRead JSON data as file :: {}, err: {} => {}".format(json_file, err.errno, err.strerror)
        # Json to Write File :: /usr/lib/monasca/agent/conf.d/agent_extra.json, err: 13 => Permission denied
        return {}, msg

def compare_jsonData(new, old):
    for n_vals, o_vals in zip(new.iteritems(), old.iteritems()):
        if n_vals != o_vals:
            return False
    return True

def compare_jsonData2(new, old):
    for n_vals, n_keys, o_vals, o_keys in zip(new.values(), new.keys(), old.values(), old.keys()):
        if n_vals != o_vals:
            return False, n_keys, o_keys
    return True, "", ""

def read_yamlData(yamlFile):
    msg = ""
    status = True
    yaml_config = None
    try:
        with open(yamlFile, 'r') as agent_yaml:
            yaml_config = yaml.load(agent_yaml.read())
    # except IOError as e:
    #    log.warn("I/O error({}): {} --> {}".format(e.errno, yName, e.strerror))
    #    status = False
    # except: #handle other exceptions such as attribute errors
    #    status = False
    #    log.warn("Unexpected error:", sys.exc_info()[0])
    except Exception as err:
        # log.warn("\tYAML file read error :: {}, err: {} => {}".format(yamlFile, err.errno, err.strerror))
        msg = "\tYAML file read error :: {}, err: {} => {}".format(yamlFile, err.errno, err.strerror)
        status = False

    # log.info("read_yamlData ==> {} : {}".format(yamlFile, status))
    return status, yaml_config, msg

def read_confData(confFile):
    msg = ""
    status = True
    conf_config = None
    try:
        with open(confFile, 'r') as conf_file:
            conf_config = conf_file.read()
    except Exception as err:
        # log.warn("\tRead Configuration File Error :: {}, err: {} => {}".format(confFile, err.errno, err.strerror))
        msg = "\tRead Configuration File Error :: {}, err: {} => {}".format(confFile, err.errno, err.strerror)
        status = False

    return status, conf_config, msg

def read_working(wfile):
    ''' Read the working.ini File   '''

    msg = ""
    status = True
    contents = None

    with open(wfile,'r') as f:
        contents = f.readlines()

    return status, contents, msg

##==============================================================================
class UtilsConfig():
    def __init__(self, args, logger=None):
        self.logger = logger or logging.getLogger(__name__)
        self.args = args

        self.datetimefomater = '%Y-%m-%d %H:%M:%S.%f'

        self.ErrorData = ['0','None'] ## errorCode, errorMessge
        self.WorkEnv = ['.','.','.','.'] ## filename, dir, fnameNotExt, workDir
        self.WORK_DIR = '.'

        self.datetimefomater2 =  '%Y-%m-%d_%H:%M:%S'
        self.DEBUG = args.debug                     ## Ansible DEBUG

    def setWorkEnv(self,fname):
        self.WorkEnv, self.WORK_DIR = workEnvMake(fname, self.args)
