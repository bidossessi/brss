#!/usr/bin/env python2
# -*- coding: utf-8 -*-
#
#       brss
#       
#       Copyright 2011 Bidossessi Sodonon <bidossessi.sodonon@yahoo.fr>
#       
#       This program is free software; you can redistribute it and/or modify
#       it under the terms of the GNU General Public License as published by
#       the Free Software Foundation; either version 2 of the License, or
#       (at your option) any later version.
#       
#       This program is distributed in the hope that it will be useful,
#       but WITHOUT ANY WARRANTY; without even the implied warranty of
#       MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#       GNU General Public License for more details.
#       
#       You should have received a copy of the GNU General Public License
#       along with this program; if not, write to the Free Software
#       Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#       MA 02110-1301, USA.
#       
#       
import dbus
import dbus.service
import dbus.mainloop.glib
dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
import subprocess
import os

from reader import Reader
from engine import Engine
from logger import Logger

__version__ = '0.1'
home = os.getenv("HOME")
BASE_PATH = os.path.join(home,'.config','brss')

def run_engine():
    session_bus = dbus.SessionBus()
    if session_bus.request_name("com.itgears.brss") != dbus.bus.REQUEST_NAME_REPLY_PRIMARY_OWNER:
        print "application already running"
    else:
        print "running BRSS Engine"
        log = Logger(BASE_PATH)
        engine = Engine(BASE_PATH, logger)

def run_frontend():
    bus                 = dbus.SessionBus()
    try:
        bus.get_object('com.itgears.brss', '/com/itgears/brss/Engine')
    except DBusException:
        subprocess.Popen(['brss-engine',])
    reader = Reader(BASE_PATH)
    reader.run()
