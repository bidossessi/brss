#!/usr/bin/env python
#-*- coding:utf-8 -*-

import logging
import os

class Logger:
    
    def __init__(self, base_path=".", path="brss.log", name="BRss", debug=True):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        logpath = os.path.join(base_path, path)
        usrlog  = logging.FileHandler(logpath, 'w')
        console = logging.StreamHandler()
        console.setLevel(logging.DEBUG)
        if debug:
            usrlog.setLevel(logging.DEBUG)
            self.logger.addHandler(console)
        else: usrlog.setLevel(logging.WARN)
        mfmt = logging.Formatter("%(asctime)-15s %(levelname)-8s %(message)s")
        # add formatter to ch
        usrlog.setFormatter(mfmt)
        # add channels to logger
        self.logger.addHandler(usrlog)

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

    # Some code uses warn instead of warning
    # It's easier for me to add an alias here than find every line of code that uses it and change it to warning
    # This saves me some time
