#!/usr/bin/env python
#-*- coding:utf-8 -*-

import logging
import os

class Logger:
    
    def __init__(self, base_path=".", path="brss.log", name="BRss", debug=False):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        logpath = os.path.join(base_path, path)
        self.usrlog  = logging.FileHandler(logpath, 'w')
        #useful for debugging
        self.console = logging.StreamHandler()
        self.console.setLevel(logging.DEBUG)
        self.usrlog.setLevel(logging.WARN)
        mfmt = logging.Formatter("%(asctime)-15s %(levelname)-8s %(message)s")
        # add formatter to ch
        self.usrlog.setFormatter(mfmt)
        # add channels to logger
        self.logger.addHandler(self.usrlog)
        self.logger.addHandler(self.console)

    def __repr__(self):
        return "Logger"
    
    def debug (self, msg):
        self.logger.debug(msg)
    def info (self, msg):
        self.logger.info(msg)
    def warning (self, msg):
        self.logger.warning(msg)
    def error (self, msg):
        self.logger.error(msg)
    def critical (self, msg):
        self.logger.critical(msg)
    def exception (self, msg):
        self.logger.exception(msg)

    def enable_debug(self, d=False):
        if d == True:
            self.usrlog.setLevel(logging.DEBUG)
        else:
            self.usrlog.setLevel(logging.WARN)
