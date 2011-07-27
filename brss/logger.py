#!/usr/bin/env python
#-*- coding:utf-8 -*-

from gi.repository import GLib
from gi.repository import Gio
import logging
from common       import BASE_PATH, BASE_KEY

class Logger:
    
    def __init__(self, path="brss.log", name="BRss"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        logpath = GLib.build_filenamev([BASE_PATH, path])
        self.usrlog  = logging.FileHandler(logpath, 'w')
        settings = Gio.Settings.new(BASE_KEY)
        settings.connect("changed::enable-debug", self.enable_debug)
        self.enable_debug(settings)
        # useful for debugging
        self.console = logging.StreamHandler()
        self.console.setLevel(logging.DEBUG)
        self.enable_debug(settings)
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

    def enable_debug(self, settings, key=False):
        if settings.get_boolean("enable-debug"):
            self.usrlog.setLevel(logging.DEBUG)
        else:
            self.usrlog.setLevel(logging.WARN)
