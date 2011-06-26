#!/usr/bin/env python2
# -*- coding: utf-8 -*-
#
#       Tree.py
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
#FIXME: DnD is broken!!!
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GObject
import os
from pkg_resources import resource_filename
def mkpath(type, file):
    """Return a data file path"""
    return resource_filename("brss", os.path.join(type,file))

class Tree (Gtk.VBox, GObject.GObject):
    """ The Tree handles feeds and categories management. """
    
    __gsignals__ = {
        "list-loaded" : (
            GObject.SignalFlags.RUN_LAST, 
            None,
            ()),
        "item-selected" : (
            GObject.SignalFlags.RUN_LAST, 
            None,
            (GObject.TYPE_PYOBJECT,)),
        "feed-moved" : (
            GObject.SignalFlags.RUN_LAST, 
            None,
            (GObject.TYPE_PYOBJECT,)),
        "dcall-request" : (
            GObject.SignalFlags.RUN_LAST, 
            None,
            (GObject.TYPE_STRING, GObject.TYPE_PYOBJECT,)),
    }
    
    def __init__(self, base_path="."):
        self.favicon_path = os.path.join(base_path, 'favicons')
        self.images_path = os.path.join(base_path, 'images')
        Gtk.VBox.__init__(self, spacing=3)
        self.__gobject_init__()
        GObject.type_register(Tree)
        self.menuview = Gtk.TreeView()
        self.menuview.set_headers_visible(False)
        self.menucol = Gtk.TreeViewColumn()
        self.textcell = Gtk.CellRendererText()
        self.iconcell = Gtk.CellRendererPixbuf()
        self.menucol.pack_start(self.iconcell, False)
        self.menucol.pack_start(self.textcell, True)
        self.menucol.set_cell_data_func(self.textcell, self.__format_name)
        #~ self.menucol.set_cell_data_func(self.iconcell, self.__format_icon)
        self.menucol.add_attribute(self.iconcell, "stock-id", 4)
        self.menuview.append_column(self.menucol)
        self.menuselect = self.menuview.get_selection()
        # containers
        msc = Gtk.ScrolledWindow()
        msc.set_shadow_type(Gtk.ShadowType.IN)
        msc.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        msc.add(self.menuview)
        mal = Gtk.Alignment.new(0.5, 0.5, 1, 1)
        self.pack_start(msc, True, True,0)
        menu = TreeMenu(self)
        self.current_item = None
        #~ self.__setup_dnd() #FIXME: DnD is broken
        self.__setup_icons(mkpath('pixmaps','rss.png'), 'feed')
        self.__setup_icons(mkpath('pixmaps','logo2.svg'), 'logo')
        self.__setup_icons(mkpath('pixmaps','feed-missing.svg'), 'missing')
        self.__setup_icons(mkpath('pixmaps','starred.svg'), 'starred')
        self.__connect_signals()
        
    def __connect_signals(self):
        self.menuselect.connect("changed", self.__selection_changed)
        self.menuview.connect("row-activated", self.__row_activated)
        
    def __setup_icons(self, path, stock_id):
        try:
            assert os.path.exists(path)
            factory = Gtk.IconFactory()
            s = Gtk.IconSource()
            s.set_filename(path)
            iconset = Gtk.IconSet()
            iconset.add_source(s)
            factory.add(stock_id, iconset)
            factory.add_default()
            return True
        except: return False
        
    def __setup_dnd(self):
        target_entries = (('example', Gtk.TargetFlags.SAME_WIDGET, 1),)
        # target_entries=[(drag type string, target_flags, application integer ID used for identification purposes)]
        self.menuview.enable_model_drag_source(Gdk.EventMask.BUTTON1_MOTION_MASK, target_entries, Gdk.DragAction.MOVE)
        self.menuview.enable_model_drag_dest(target_entries, Gdk.DragAction.MOVE)
        self.menuview.connect('drag-data-received', self.__row_dragged)
    
    def __row_dragged(self, treeview, drag_context, x, y, selection_data, info, eventtime):
        model, source = treeview.get_selection().get_selected()
        target_path, drop_position = treeview.get_dest_row_at_pos(x, y)
        # only move if source is a feed and target is a category
        # move here first and let our engine know later
    
    def __get_weight(self, count):
        if count and int(count) > 0:
            return 800
        return 400
    
    def __format_icon(self, column, cell, model, iter, col):
        tp  = model.get_value(iter, 0)
        count = model.get_value(iter, 3)
        if int(count) > 0:
            cell.set_property('stock-id', model.get_value(iter, 4))
        else:
            if tp == 'feed':
                cell.set_property('stock-id', 'gtk-apply')
            elif tp == 'category':
                cell.set_property('stock-id', 'gtk-directory')
        
    def __format_name(self, column, cell, model, iter, col):
        name = model.get_value(iter, 2)
        count = model.get_value(iter, 3)
        if int(count) > 0:
           cell.set_property("text",'{0} [{1}]'.format(name, count))
        else:
           cell.set_property("text",name)
        cell.set_property("weight", self.__get_weight(int(count)))
    
    def __format_row(self, a):
        gmap = {'feed':'gtk-file', 'category':'gtk-directory'}
        # icon
        try:
            stock = self.__setup_icons(os.path.join(self.favicon_path, a['id']), a['id'])
            if stock:
                gmap[a['id']] = a['id']
        except Exception, e: print e
        r = (
            a['type'],
            a['id'],
            a['name'],
            a.get('count'),
            gmap.get(a['id']) or gmap.get(a['type'])
            )
        return r
        
    def deselect(self, *args):
        self.menuselect.unselect_all()
        self.current_item = None
        
    def update_starred(self, ilist, item):
        # if item['starred'] is 0, we go minus
        model, iter = self.__search(0, 'starred')
        self.__update_count(model, iter, 3, item['starred'])

    def update_unread(self, ilist, item):
        # if item['read'] is 0, we go plus
        model, iter = self.__search(0, 'unread')
        if model and iter:
            self.__update_count(model, iter, 3, item['read'], True)
        # now try to update the originating feed
        model, iter = self.__search(1, item['feed_id'])
        if model and iter:
            self.__update_count(model, iter, 3, item['read'], True)
            # if at all possible, update the category
            if model.iter_parent(iter):
                self.__update_count(model, model.iter_parent(iter), 3, item['read'], True)
    
    def __search(self, col, value):
        """
        Returns a path for the value we are looking for.
        """
        gmap = {0:'type', 1:'id', 2:'name', 3:'count'}
        #~ print "seaching for {0} == {1}".format(gmap.get(col), value)
        model = self.menuview.get_model()
        iter = model.get_iter_first()
        while iter:
            v = model.get_value(iter, col)
            if value == v:
                #~ print( "match found: {0} => {1}: {2}".format(gmap.get(col), v, model.get_value(iter, 2)))
                return model, iter
            elif model.iter_has_child(iter):
                citer = model.iter_children(iter)
                while citer:
                    v = model.get_value(citer, col)
                    if value == v:
                        #~ print( "match found: {0} => {1}: {2}".format(gmap.get(col), v, model.get_value(citer, 2)))
                        return model, citer
                    citer = model.iter_next(citer)
            iter = model.iter_next(iter)

    def __update_count (self, model, iter, col, var, inverse=False):
        pmap = {0:-1, 1:+1}
        if inverse:
            pmap = {0:+1, 1:-1}
        ol = model.get_value(iter, col)
        nval = ol+pmap.get(var)
        model.set_value(iter, col, nval)
        
    def __make_special_folders(self, unread, starred, store):
        u = ('unread', '','Unread', unread, 'gtk-new')
        s = ('starred', '', 'Starred', starred, 'gtk-about')
        store.append(None, u)
        store.append(None, s)


    def fill_menu(self, data, unread, starred):
        """Load the given data into the left menuStore"""
        # return the first iter
        self.menuview.set_model(None)
        store = Gtk.TreeStore(str, str, str, int, str)
        if data:
            row = None
            for item in data:
                if item['type'] == 'category':
                    row = store.append(None, self.__format_row(item))
                if item['type'] == 'feed':
                    store.append(row, self.__format_row(item))
        self.__make_special_folders(unread, starred, store)
        self.menuview.set_model(store)
        self.menuview.expand_all()
        self.emit('list-loaded')

    def __row_activated(self, treeview, path, col):
        item = self.__get_current(treeview.get_selection())
        
    def __selection_changed(self, selection):
        item = self.__get_current(selection)
        if item:
            # emit the right signal
            self.emit('item-selected', item)

    def __get_current(self, selection):
        (model, iter) = selection.get_selected()
        if iter:
            item = {
                'type': model.get_value(iter, 0),
                'id': model.get_value(iter, 1),
                'name': model.get_value(iter, 2),
            }
            self.current_item = item
            return item
    
        
    def run_dialog(self, dialog_name, item):
        self.emit('dialog-request', dialog_name, item)
        
    def run_dcall(self, callback_name, item):
        self.emit('dcall-request', callback_name, item)
        
    # convenience
    #~ def do_item_selected(self, item):
        #~ print 'Item selected: ', item
    def do_list_loaded(self):
        model, iter = self.__search(0, 'unread')
        self.menuselect.select_iter(iter)
        
class TreeMenu(Gtk.Menu):
    """
    TreeMenu extends the standard Gtk.Menu by adding methods 
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
    def _create(self, item):
        if not self._dirty:
            return

        self.clean()

        for i in ['Mark all as read', 'Update', 'Edit', 'Delete', 'sep',
                    'Add a Category', 'Add a Feed']:
            
            if i == 'sep':
                sep = Gtk.SeparatorMenuItem()
                sep.show()
                self.append(sep)
                continue
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
        elif callname in ['Mark all as read', 'Update', 'Delete']:
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
    
    def callback(ilist, item, method):
        print method(item)

    import dbus
    import dbus.mainloop.glib
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

    bus                 = dbus.SessionBus()
    engine              = bus.get_object('com.itgears.brss', '/com/itgears/brss/Engine')
    get_menu_items      = self.engine.get_dbus_method('get_menu_items', 'com.itgears.brss')
    exit                = engine.get_dbus_method('exit', 'com.itgears.brss')
    
    cats = get_menu_items()
    window = Gtk.Window()
    window.connect("destroy", Gtk.main_quit)
    window.set_default_size(400, 600)
    tree = Tree()
    window.add(tree)
    window.show_all()
    tree.fill_menu(cats)
    tree.connect('item-selected', callback, get_articles_for)
    Gtk.main()
    
    def quit():
        Gtk.main_quit()
        exit()
