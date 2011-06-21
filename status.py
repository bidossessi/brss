#!/usr/bin/env python2
# -*- coding: utf-8 -*-
#
#       status.py
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


class Status (Gtk.HBox):
    """ The feedtree handles feeds and categories management. """
    
    
    def __init__(self):
        Gtk.HBox.__init__(self, spacing=3)
        self.set_no_show_all(True)
        self.ok_img = Gtk.Image().new_from_stock('gtk-yes', Gtk.IconSize.MENU)
        self.warning_img = Gtk.Image().new_from_stock('gtk-dialog-warning', Gtk.IconSize.MENU)
        self.error_img = Gtk.Image().new_from_stock('gtk-dialog-error', Gtk.IconSize.MENU)
        self.busy = Gtk.Spinner()
        self.status = Gtk.Statusbar()
        self.pack_start(self.ok_img, False, False, 0)
        self.pack_start(self.warning_img, False, False, 0)
        self.pack_start(self.error_img, False, False, 0)
        self.pack_start(self.busy, False, False, 0)
        self.pack_start(self.status, True, True, 0)
        self.show()
        self.status.show()
        self.__hide_icons()
        
    
    def message(self, context, message):
        self.__hide_icons()
        self.__handle_context(context)
        cid = self.status.get_context_id(context)
        self.status.push(cid, message)
    
    def __hide_icons(self):
        self.ok_img.hide()
        self.warning_img.hide()
        self.error_img.hide()
        self.busy.stop()
        self.busy.hide()
    
    def __handle_context(self, context):
        """
        Show the right icon depending on the context.
        For now we have: new, db-error, wait
        """
        if context == "wait":
            self.busy.show()
            self.busy.start()
        if context == "new":
            self.ok_img.show()
        if context == "warning":
            self.warning_img.show()
        if context == "db-error":
            self.error_img.show()
