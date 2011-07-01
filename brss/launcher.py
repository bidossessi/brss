#!/usr/bin/env python2
# -*- coding: utf-8 -*-
#
#       launcher.py
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
import time
from reader import Reader, run_reader
from engine import Engine

home = os.getenv("HOME")
BASE_PATH = os.path.join(home,'.config','brss')
def check_path():
    print "Using base_path", BASE_PATH
    if not os.path.exists(BASE_PATH):
        os.makedirs(BASE_PATH)

def check_engine():
    bus = dbus.SessionBus()
    try:
        bus.get_object('com.itgears.BRss.Engine', '/com/itgears/BRss/Engine')
    except:
        return False
    return True
    
def run_engine():
    check_path()
    session_bus = dbus.SessionBus()
    if session_bus.request_name('com.itgears.BRss.Engine') != dbus.bus.REQUEST_NAME_REPLY_PRIMARY_OWNER:
        print "engine already running"
    else:
        engine = Engine(BASE_PATH)
        engine.start()

def run_frontend():
    max = 5
    check_path()
    if not check_engine():
        subprocess.Popen(['brss-engine',])
    i = 0
    while not check_engine() and i < max:
        time.sleep(max)
        i +=1
    if check_engine():
        run_reader(Reader, BASE_PATH)
    else:
        print "Couldn't start engine"
