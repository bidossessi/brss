 #!/usr/bin/env python2
# -*- coding: utf-8 -*-
#
#       dialogs.py
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
from gi.repository import Gio
class Custom:
    def __init__(self, name, header):
        self.name = name
        self.header = header


class TextEntry(Gtk.Entry, Custom) :
    def __init__(self, name, header):
        Gtk.Entry.__init__(self)
        Custom.__init__(self, name, header)

    def set_value(self, value):
        self.set_text(value)

    def get_value(self, suppress=False):
        value = self.get_text().replace("\n","").replace("\r","")
        return value

class NumEntry(Gtk.SpinButton, Custom) :
    def __init__(self, name, header):
        a = Gtk.Adjustment.new(0, 0, 1000, 1, 10, 10)
        Gtk.SpinButton.__init__(self)
        self.set_adjustment(a)
        Custom.__init__(self, name, header)
        #~ self.set_alignment(1.0)
    
    #~ def set_value(self, value):
        #~ Gtk.SpinButton.set_value(self, value)

    def get_value(self, suppress=False):
        value = self.get_value_as_int()
        return value
        
class CheckBtn(Gtk.CheckButton, Custom) :

    def __init__(self, name, header):
        Gtk.CheckButton.__init__(self, header)
        Custom.__init__(self, name, header)

    def set_value(self, value):
        self.set_active(value)

    def get_value(self):
        return self.get_active()

class Dialog(Gtk.Dialog):
    def __init__(self, caller, title, args, settings=None):
        if settings:
            b = (
                Gtk.STOCK_CLOSE, Gtk.ResponseType.CLOSE)
        else:
            b = (
                Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                Gtk.STOCK_APPLY, Gtk.ResponseType.OK)
        Gtk.Dialog.__init__(
            self,
            flags=Gtk.DialogFlags.MODAL|Gtk.DialogFlags.DESTROY_WITH_PARENT,
            buttons=b
                )
        self.__widget_list = []
        self.__create_ui()
        self.set_title (title)
        self.set_transient_for(caller)
        for w in args:
            self.make_widget(w, settings)
        self.grid(self.__widget_list)
        self.show_all()
        
    def __create_ui(self):
        self.centeral = Gtk.Alignment.new(0.5, 0.5, 1, 1)
        self.centeral.set_padding(5,5,5,5)
        self.box = self.get_content_area()
        self.box.pack_start(self.centeral, True, True, 0)
        self.connect("response", self.on_response)
        self.response = {}
        self.set_default_response(Gtk.ResponseType.OK)


    def __make_header(self, name):
        header = Gtk.Label(name + " :")
        header.set_alignment(0, 0.5)
        return header
    
    def make_widget(self, w, settings):
        # w = {'name':?, 'type':?}
        gmap = {'bool':CheckBtn, 'str':TextEntry, 'int':NumEntry}
        widget = gmap.get(w['type'])(w['name'], w['header'])
        if settings:
            if w['type'] == 'bool':
                settings.bind(w['name'], widget, 'active',Gio.SettingsBindFlags.DEFAULT)
                widget.set_value(settings.get_boolean(w['name']))
            elif w['type'] == 'int':
                settings.bind(w['name'], widget, 'value',Gio.SettingsBindFlags.DEFAULT)
                widget.set_value(settings.get_int(w['name']))
            elif w['type'] == 'str':
                settings.bind(w['name'], widget, 'text',Gio.SettingsBindFlags.DEFAULT)
                widget.set_value(settings.get_string(w['name']))
        else:
            if w.has_key('value'):
                widget.set_value(w['value'])
        self.__widget_list.append(widget)
    
    def grid(self, widget_list):
        """
        Build a table of widgets.
        """
        box = Gtk.Table()
        box.set_col_spacings(12)
        box.set_row_spacings(5)
        lpid = 0
        tpid = 0
        
        for widget in widget_list:
            header = self.__make_header(widget.header)
            if type(widget) == CheckBtn:
                box.attach(widget, lpid, lpid+2, tpid, tpid+1, Gtk.AttachOptions.FILL|Gtk.AttachOptions.EXPAND, Gtk.AttachOptions.FILL)
            else:
                box.attach(header, lpid, lpid+1, tpid, tpid+1, Gtk.AttachOptions.FILL, Gtk.AttachOptions.FILL)
                box.attach(widget, lpid+1, lpid+2, tpid, tpid+1, Gtk.AttachOptions.FILL|Gtk.AttachOptions.EXPAND, Gtk.AttachOptions.FILL)
            tpid += 1
            widget.show()
            header.show()
        box.show()
        #~ self.centeral.add(box, True, True, 0)
        self.centeral.add(box)
    def collect_response(self):
        response = {}
        for w in self.__widget_list:
            response[w.name] = w.get_value()
        return response
    
    def on_response(self, dialog, response_id):
        if response_id == Gtk.ResponseType.OK:
            self.response = self.collect_response()
        dialog.hide()
        
def main():
    from view import View
    window = Gtk.Window()
    window.connect("destroy", Gtk.main_quit)
    window.set_default_size(600, 400)
    #~ view = 
    #~ window.add(view)
    window.show_all()
    args = [
        {'type':'str','name':'yoo', 'header':'This is a text entry' },
        {'type':'bool','name':'art', 'header':'This cool entry', 'value':True }
        ]
    d = Dialog(window, 'test', args)
    d.run()
    d.destroy()
    Gtk.main()

if __name__ == '__main__':
    main()
