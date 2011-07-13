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
import os
from reader import ReaderApplication
from engine import Engine
from brss   import BASE_PATH, ENGINE_DBUS_KEY, ENGINE_DBUS_PATH

def check_path():
    print "Using base_path", BASE_PATH
    if not os.path.exists(BASE_PATH):
        os.makedirs(BASE_PATH)

def check_engine():
    bus = dbus.SessionBus()
    try:
        bus.get_object(ENGINE_DBUS_KEY, ENGINE_DBUS_PATH)
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
        r = ReaderApplication()
        r.run()
