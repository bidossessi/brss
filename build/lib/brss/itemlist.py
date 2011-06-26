#!/usr/bin/env python2
# -*- coding: utf-8 -*-
#
#       itemlist.py
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
from datetime import datetime
import locale

def make_date(string):
    date = datetime.fromtimestamp(int(string))
    return date.strftime (locale.nl_langinfo(locale.D_FMT))

class ItemList (Gtk.VBox, GObject.GObject):
    """
        The itemlist, well, lists all available feed items for the selected
        feed.
    """
    __gsignals__ = {
        "list-loaded" : (
            GObject.SignalFlags.RUN_LAST, 
            None,
            ()),
        "no-data" : (
            GObject.SignalFlags.RUN_LAST, 
            None,
            ()),
        "search-requested" : (
            GObject.SignalFlags.RUN_LAST, 
            None,
            (GObject.TYPE_STRING,)),
        "star-toggled" : (
            GObject.SignalFlags.RUN_LAST, 
            None,
            (GObject.TYPE_PYOBJECT,)),
        "read-toggled" : (
            GObject.SignalFlags.RUN_LAST, 
            None,
            (GObject.TYPE_PYOBJECT,)),
        "item-selected" : (
            GObject.SignalFlags.RUN_LAST, 
            None,
            (GObject.TYPE_PYOBJECT,)),
        "dcall-request" : (
            GObject.SignalFlags.RUN_LAST, 
            None,
            (GObject.TYPE_STRING, GObject.TYPE_PYOBJECT,)),
        }
    
    def __init__(self):
        Gtk.VBox.__init__(self, spacing=3)
        self.__gobject_init__()
        self.current_item = None
        ## search
        self.filterentry = Gtk.Entry()
        self.filterentry.set_property("secondary-icon-stock", "gtk-find")
        self.filterentry.set_property("secondary-icon-activatable", True)
        self.filterentry.set_property("secondary-icon-tooltip-text", "Search for...")
        self.filterentry.connect("icon-press", self.__icon_pressed)
        self.filterentry.connect("activate", self.__search_request)
        self.fbox = Gtk.HBox(spacing=3)
        self.fbox.pack_start(self.filterentry, True, True, 0)
        store = Gtk.ListStore(str, bool, bool, str, str, str, int, str)
        self.listview = Gtk.TreeView()
        self.listview.set_model(store)
        self.listview.connect("row-activated", self.__row_activated)
        ## COLUMNS | store structure (id, read, starred, date, title, url, weight, feed_id)
        # read
        column = Gtk.TreeViewColumn()
        label = Gtk.Label(label='Read')
        label.show()
        column.set_widget(label)
        column.set_fixed_width(30)
        cell = Gtk.CellRendererToggle()
        column.pack_start(cell, True)
        column.add_attribute(cell, "active", 1)
        cell.set_property('activatable', True)
        cell.connect('toggled', self.__toggle_read, self.listview.get_model())
        column.set_sort_column_id(1)
        self.listview.append_column(column)
        # starred
        column = Gtk.TreeViewColumn()
        label = Gtk.Label(label='Star')
        label.show()
        column.set_widget(label)
        column.set_fixed_width(15)
        cell = Gtk.CellRendererToggle()
        cell.set_fixed_size(15, 15)
        column.pack_start(cell, True)
        column.add_attribute(cell, "active", 2)
        cell.set_property('activatable', True)
        cell.connect('toggled', self.__toggle_star, self.listview.get_model())
        column.set_sort_column_id(2)
        self.listview.append_column(column)
        # date
        column = Gtk.TreeViewColumn()
        label = Gtk.Label(label='Date')
        label.show()
        column.set_widget(label)
        column.set_resizable(True)
        cell = Gtk.CellRendererText()
        column.pack_start(cell, True)
        column.set_cell_data_func(cell, self.__format_date)
        column.add_attribute(cell, "text", 3)
        column.add_attribute(cell, "weight", 6)
        column.set_sort_column_id(3)
        self.listview.append_column(column)
        # title
        column = Gtk.TreeViewColumn()
        label = Gtk.Label(label='Title')
        label.show()
        column.set_widget(label)
        column.set_resizable(True)
        cell = Gtk.CellRendererText()
        column.pack_start(cell, True)
        column.add_attribute(cell, "text", 4)
        column.add_attribute(cell, "weight", 6)
        column.set_sort_column_id(4)
        self.listview.append_column(column)
        # enable quick-searching
        self.listview.set_search_column(4)
        # connect selection
        self.listselect = self.listview.get_selection()
        self.listselect.connect("changed", self.__selection_changed)
        # containers
        self.msc = Gtk.ScrolledWindow()
        self.msc.set_shadow_type(Gtk.ShadowType.IN)
        self.msc.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.msc.add(self.listview)
        self.mal = Gtk.Alignment.new(0.5, 0.5, 1, 1)
        self.mal.add(self.msc)
        self.pack_start(self.fbox, False, False,0)
        self.pack_start(self.mal, True, True,0)
        menu = ItemListMenu(self)
        self.current_item = None
        GObject.type_register(ItemList)
        self.__lock__ = False
        self.listselect.set_select_function(self.__skip_toggles, None)
        self.fbox.set_no_show_all(True)
        self.search_on = False
        
    def __get_weight(self, read):
        if read and int(read) > 0:
            return 400
        return 800
    def __get_date(self, timestamp):
        try:
            return date.strftime (locale.nl_langinfo(locale.D_FMT))
        except Exception, e:
            return ""   
    def __format_date(self, column, cell, model, iter, col):
        cell.set_property('text', make_date(model.get_value(iter, 3)))
    def __format_data(self, data):
        """ Structure our data """
        llist = []
        for a in data:
            llist.append(self.__format_row(a))
        return llist

    def __format_row(self, a):
        r = (
                a['id'],
                int(a['read']),
                int(a['starred']),
                a['date'],
                a['title'],
                a['url'],
                self.__get_weight(a['read']),
                a['feed_id'],
            )
        return r
        
    def load_list(self, data):
        store = self.listview.get_model()
        store.clear()
        # store structure (id, read, starred, date, title, url, weight, feed_id)
        if data:
            l = self.__format_data(data)
            for art in l:
                store.append(art)
            self.listview.set_model(store)
            self.emit('list-loaded')
        else:
            self.emit('no-data')
    def __row_activated(self, treeview, path, col):
        item = self.__get_current(treeview.get_selection())
        
    def __selection_changed(self, selection):
        item = self.__get_current()
        if item:
            # emit the right signal
            self.emit('item-selected', item)

    def toggle_search(self, *args):
        if self.search_on == True:
            self.__hide_search()
        else: self.__show_search()
        
    def __show_search(self):
        self.fbox.show()
        self.filterentry.show()
        self.filterentry.grab_focus()
        self.search_on = True
    
    def __hide_search(self):
        self.fbox.hide()
        self.__clear_filter()
        self.search_on = False
    
    def __icon_pressed(self, entry, icon_pos, event):
        """Clears the standard filter GtkEntry."""
        if icon_pos.value_name == "GTK_ENTRY_ICON_PRIMARY":
            if event.button == 1:
                self.__clear_filter()
        if icon_pos.value_name == "GTK_ENTRY_ICON_SECONDARY":
            if event.button == 3 or event.button == 1:
                self.__request_search(entry)
    
    def __search_request(self, entry, *args):
        self.emit('search-requested', entry.get_text())
        self.__clear_filter()
        
    def __clear_filter(self):
        self.filterentry.set_text("")
        
    def next_item(self, *args):
        model, iter = self.listselect.get_selected()
        niter = model.iter_next(iter)
        try: self.listselect.select_iter(niter)
        except: pass
    
    def previous_item(self, *args):
        model, iter = self.listselect.get_selected()
        if iter:
            s = model.get_string_from_iter(iter)
            if int(s) > 0:
                niter = model.get_iter_from_string(str(int(s)-1))
                self.listselect.select_iter(niter)
                
    
    
    def __get_current(self, row=False):
        bmap = {False:"0", True:"1"}
        if row:
            item = {
                'id': row[0],
                'read': bmap.get(row[1]),
                'starred': bmap.get(row[2]),
                'title': row[4],
                'url': row[5],
                'feed_id': row[7],
            }
            self.current_item = item
            return item
        else:
            (model, iter) = self.listselect.get_selected()
            if iter:
                item = {
                    'id': model.get_value(iter, 0),
                    'read': bmap.get(model.get_value(iter, 1)),
                    'starred': bmap.get(model.get_value(iter, 2)),
                    'title': model.get_value(iter, 4),
                    'url': model.get_value(iter, 5),
                    'feed_id': model.get_value(iter, 7),
                }
                self.current_item = item
                return item
    
    def __toggle_star(self, cell, path, model):
        self.__lock__ = True
        bmap = {True:False, False:True}
        model[path][2] = bmap.get(model[path][2])
        self.emit('star-toggled', self.__get_current(model[path]))
    
    def __toggle_read(self, cell, path, model):
        self.__lock__ = True
        bmap = {True:False, False:True}
        model[path][1] = bmap.get(model[path][1])
        model[path][6] = self.__get_weight(model[path][1])
        self.emit('read-toggled', self.__get_current(model[path]))
    
    def __skip_toggles(self, selection, *args):
        if self.__lock__ == True:
            self.__lock__ = False
            return False
        return True
    
    def mark_read(self, *args):
        """Mark the current article as read."""
        (model, iter) = self.listselect.get_selected()
        path = model.get_path(iter)
        if model[path][1] == False:
            model[path][1] = True
            model[path][6] = self.__get_weight(model[path][1])
            self.emit('read-toggled', self.__get_current(model[path]))

    def mark_all_read(self, *args):
        """Mark the current article as read."""
        model = self.listview.get_model()
        iter = model.get_iter_first()
        while iter:
            path = model.get_path(iter)
            if model[path][1] == False:
                model[path][1] = True
                model[path][6] = self.__get_weight(model[path][1])
                self.emit('read-toggled', self.__get_current(model[path]))
            iter = model.iter_next(iter)

    def run_dcall(self, callback_name, item):
        self.emit('dcall-request', callback_name, item)    
    # convenience
    #~ def do_item_selected(self, item):
        #~ print 'Item selected: ', item
    #~ def do_star_toggled(self, item):
        #~ print "Star this: ", item
    #~ def do_read_toggled(self, item):
        #~ print "Toggle this: ", item
    def do_search_requested(self, item):
        print "Search for: ", item
    
    def do_list_loaded(self):
        self.listselect.select_path((0,))

class ItemListMenu(Gtk.Menu):
    """
    FeedTreeMenu extends the standard Gtk.Menu by adding methods 
    for context handling.
    """
    def __init__(self, treeview):
        #~ #print "creating a ViewMenu"
        Gtk.Menu.__init__(self)
        self._dirty = True
        self._signal_ids = []
        self._treeview = treeview
        self._treeview.connect('button-release-event', self._on_event)
        self._treeview.connect('key-release-event', self._on_event)
        self._treeview.connect('item-selected', self._monitor_instance)

    def clean(self):
        for child in self.get_children():
            self.remove(child)
        for menuitem, signal_id in self._signal_ids:
            menuitem.disconnect(signal_id)
        self._signal_ids = []

    def popup(self, event, instance):
        #~ print("{0}: menu popping up, dirty {1}".format(self, self._dirty))
        self._create(instance)
        if hasattr(event, "button"):
            Gtk.Menu.popup(self, None, None, None, None,
                       event.button, event.time)
        #~ elif hasattr(event, "keyval"):
            #~ Gtk.Menu.popup(self, None, None, None, None,
                       #~ event.keyval, event.time)

    def _create(self, item):
        if not self._dirty:
            return

        self.clean()

        for i in ['Mark all as read', 'Open in Browser', 
            'Copy Url to Clipboard']:
            
            menuitem = Gtk.MenuItem()
            menuitem.set_label(i)
            signal_id = menuitem.connect("activate",
                                        self._on_menuitem__activate,
                                        i,
                                        item)
            self._signal_ids.append((menuitem, signal_id))
            menuitem.show()
            self.append(menuitem)
        
        self._dirty = False

    def _on_menuitem__activate(self, menuitem, callname, item):
        # switch dialog or direct call
        if callname in ['Edit', 'Add a Category', 'Add a Feed']:
            self._treeview.run_dialog(callname, item)
        elif callname in ['Open in Browser', 'Copy Url to Clipboard']:
            self._treeview.run_dcall(callname, item)

    def _on_event(self, treeview, event):
        """Respond to mouse click or key press events in a GtkTree."""
        if event.type == Gdk.EventType.BUTTON_RELEASE:
            if event.button == 3:
                self.popup(event, self._treeview.current_item)
        elif event.type == Gdk.EventType.KEY_RELEASE:
            if event.keyval == 65383: # Menu
                self.popup(event, self._treeview.current_item)

    def _monitor_instance(self, treeview, item):
        self._dirty = True
        
if __name__ == '__main__':

    def convert(item, tp='feed'):
        i = {
                'type': tp,
                'id': item['id'],
                'name': item['name'],
            }
        return i
    
    def callback(ilist, item, method):
        print item
        print method(item)
    
    def dcb(*args):
        print args
        
    import dbus
    import dbus.mainloop.glib
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

    bus                 = dbus.SessionBus()
    engine              = bus.get_object('com.itgears.brss', '/com/itgears/brss/Engine')
    get_articles_for    = engine.get_dbus_method('get_articles_for', 'com.itgears.brss')
    get_article         = engine.get_dbus_method('get_article', 'com.itgears.brss')
    toggle_starred      = engine.get_dbus_method('toggle_starred', 'com.itgears.brss')
    toggle_read         = engine.get_dbus_method('toggle_read', 'com.itgears.brss')
    exit                = engine.get_dbus_method('exit', 'com.itgears.brss')

    window = Gtk.Window()
    window.connect("destroy", Gtk.main_quit)
    window.set_default_size(600, 400)
    tree = ItemList()
    window.add(tree)
    window.show_all()
    tree.load_list(exfeed)
    #~ tree.connect_after('item-selected', callback, get_article)
    tree.connect('star-toggled', callback, toggle_starred)
    tree.connect('read-toggled', callback, toggle_read)
    Gtk.main()