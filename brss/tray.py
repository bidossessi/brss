#!/usr/bin/env python2
# -*- coding: utf-8 -*-
#
#       tray.py
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
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GObject
import os
#~ import pynotify
import dbus
import dbus.service
import dbus.mainloop.glib
from engine import Engine

class Tray (dbus.service.Object):
    """
    This guy's job is to start the service
    """
    
    def __init__(self, base_path="."):
                
        bus_name = dbus.service.BusName('org.itgears.brss', bus=dbus.SessionBus())
        dbus.service.Object.__init__(self, bus_name, '/org/itgears/brss/Tray')

        self.engine = Engine()
        
        status = Gtk.StatusIcon().new_from_file('logo2.svg')

        menu = TrayMenu(status)
        status.connect("activate", self.exit)
    
    def run_dcall(self, callback_name):
        print callback_name   
        
    def __clean_up(self):
        self.engine.exit()
    
    
    def run(self):
        # we need to start the engine
        Gtk.main()
    
    def exit(self, *args):
        self.__clean_up()
        Gtk.main_quit()

class TrayMenu(Gtk.Menu):
    """
    FeedTreeMenu extends the standard Gtk.Menu by adding methods 
    for context handling.
    """
    def __init__(self, tray):
        #~ #print "creating a ViewMenu"
        Gtk.Menu.__init__(self)
        self._dirty = True
        self._signal_ids = []
        self._tray = tray
        self._tray.connect("popup-menu", self.popup)

    def clean(self):
        for child in self.get_children():
            self.remove(child)
        for menuitem, signal_id in self._signal_ids:
            menuitem.disconnect(signal_id)
        self._signal_ids = []

    
    def popup(self, status_icon, button, activate_time):
        self._create()
        
        popup_function = Gtk.StatusIcon.position_menu

        Gtk.Menu.popup(None, None, popup_function,
            button, activate_time, status_icon)

    def _create(self):
        if not self._dirty:
            return

        self.clean()

        for i in ['Launch Rss', 'Update Feeds', 
            'Copy Url to Clipboard']:
            
            menuitem = Gtk.MenuItem()
            menuitem.set_label(i)
            signal_id = menuitem.connect("activate",
                            self._on_menuitem__activate, i)
            self._signal_ids.append((menuitem, signal_id))
            menuitem.show()
            self.append(menuitem)
        
        self._dirty = False

    def _on_menuitem__activate(self, menuitem, callname):
        self._tray.run_dcall(callname)

        
if __name__ == '__main__':
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    session_bus = dbus.SessionBus()
    tray = Tray(base_path=".")
    tray.run()
