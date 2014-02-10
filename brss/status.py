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


class Status (Gtk.Alignment):
    """ The feedtree handles feeds and categories management. """
    
    
    def __init__(self):
        Gtk.Alignment.__init__(self)
        self.set(0.5, 0.5, 1,1)
        self.set_padding(0,0,3,3)
        self.set_no_show_all(True)
        box = Gtk.HBox(spacing=3)
        self.ok_img = Gtk.Image().new_from_stock('gtk-apply', Gtk.IconSize.MENU)
        self.add_img = Gtk.Image().new_from_stock('gtk-add', Gtk.IconSize.MENU)
        self.info_img = Gtk.Image().new_from_stock('gtk-info', Gtk.IconSize.MENU)
        self.warning_img = Gtk.Image().new_from_stock('gtk-dialog-warning', Gtk.IconSize.MENU)
        self.error_img = Gtk.Image().new_from_stock('gtk-dialog-error', Gtk.IconSize.MENU)
        self.busy = Gtk.Spinner()
        self.status = Gtk.Statusbar()
        box.pack_start(self.ok_img, False, False, 0)
        box.pack_start(self.add_img, False, False, 0)
        box.pack_start(self.info_img, False, False, 0)
        box.pack_start(self.warning_img, False, False, 0)
        box.pack_start(self.error_img, False, False, 0)
        box.pack_start(self.busy, False, False, 0)
        box.pack_start(self.status, True, True, 0)
        self.add(box)
        self.show()
        box.show()        
        self.status.show()
        self.__hide_icons()
        self.cid = None
        self.mid = None
    
    def message(self, context, message):
        self.__hide_icons()
        self.__handle_context(context)
        self.cid = self.status.get_context_id(context)
        self.mid = self.status.push(self.cid, message)
    def warning(self, message):
        self.message("warning", message)
    def __hide_icons(self):
        self.ok_img.hide()
        self.add_img.hide()
        self.info_img.hide()
        self.warning_img.hide()
        self.error_img.hide()
        self.busy.stop()
        self.busy.hide()
    
    def __handle_context(self, context):
        """
        Show the right icon depending on the context.
        For now we have: new, error, wait
        """
        if context == "wait":
            self.busy.show()
            self.busy.start()
        if context == "ok":
            self.ok_img.show()
        if context == "info":
            self.info_img.show()
        if context in ["new", "added"]:
            self.add_img.show()
        if context == "warning":
            self.warning_img.show()
        if context == "critical":
            self.error_img.show()

    def clear(self):
        self.__hide_icons()
        self.message('clear', '')
