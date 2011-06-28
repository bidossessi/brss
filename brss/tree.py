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
import pango
import os
from functions import make_path

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
        #store (type,id,name,count,stock-id, url, category_id) 
        self.store = Gtk.TreeStore(str, str, str, int, str, str, str)
        self.store.set_sort_func(2, self.__sort_type, 0)
        #~ self.store.set_default_sort_func(self.__sort_type, 0)
        self.store.set_sort_column_id(2, Gtk.SortType.ASCENDING)
        self.menuview = Gtk.TreeView()
        self.menuview.set_model(self.store)
        self.menuview.set_headers_visible(False)
        #TODO: set automatic sorting
        col = Gtk.TreeViewColumn()
        textcell = Gtk.CellRendererText()
        iconcell = Gtk.CellRendererPixbuf()
        col.pack_start(iconcell, False)
        col.pack_start(textcell, True)
        col.set_cell_data_func(textcell, self.__format_name)
        #~ self.menucol.set_cell_data_func(self.iconcell, self.__format_icon)
        col.add_attribute(iconcell, "stock-id", 4)
        col.set_sort_order(Gtk.SortType.ASCENDING)
        self.menuview.append_column(col)
        self.menuselect = self.menuview.get_selection()
        ## SPECIALS
        self.sstore = Gtk.TreeStore(str, str, str, int, str)
        self.sview = Gtk.TreeView()
        self.sview.set_model(self.sstore)
        self.sview.set_headers_visible(False)
        #TODO: set automatic sorting
        col = Gtk.TreeViewColumn()
        textcell = Gtk.CellRendererText()
        iconcell = Gtk.CellRendererPixbuf()
        col.pack_start(iconcell, False)
        col.pack_start(textcell, True)
        col.set_cell_data_func(textcell, self.__format_name)
        col.add_attribute(iconcell, "stock-id", 4)
        self.sview.append_column(col)
        self.sselect = self.sview.get_selection()
        
        # containers
        msc = Gtk.ScrolledWindow()
        msc.set_shadow_type(Gtk.ShadowType.IN)
        msc.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.NEVER)
        msc.add(self.sview)
        self.pack_start(msc, False, True, 0)
        msc = Gtk.ScrolledWindow()
        msc.set_shadow_type(Gtk.ShadowType.IN)
        msc.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        msc.add(self.menuview)
        mal = Gtk.Alignment.new(0.5, 0.5, 1, 1)
        self.pack_start(msc, True, True,0)
        self.set_property("width-request", 300)
        menu = TreeMenu(self)
        self.current_item = None
        #~ self.__setup_dnd() #FIXME: DnD is broken
        self.__setup_icons(make_path('pixmaps','brss-feed.svg'), 'feed')
        self.__setup_icons(make_path('pixmaps','logo2.svg'), 'logo')
        self.__setup_icons(make_path('pixmaps','brss-feed-missing.svg'), 'missing')
        self.__setup_icons(make_path('pixmaps','starred.svg'), 'starred')
        self.__connect_signals()
        
    def __connect_signals(self):
        self.menuselect.connect("changed", self.__selection_changed, "l")
        self.menuview.connect("row-activated", self.__row_activated)
        self.sselect.connect("changed", self.__selection_changed, "s")
        self.sview.connect("row-activated", self.__row_activated)
        
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
    

    def __sort_type(self, model, iter1, iter2, tp):
        #1. make sure that starred stays below unread:
        tp1 = model.get_value(iter1, tp)
        tp2 = model.get_value(iter2, tp)
        id1 = model.get_value(iter1, 1)
        id2 = model.get_value(iter2, 1)
        try:
            name1 = model.get_value(iter1, 2).lower()
            name2 = model.get_value(iter2, 2).lower()
        except:
            name1 = model.get_value(iter1, 2)
            name2 = model.get_value(iter2, 2)
        #3. put general on top
        if id1 == "uncategorized":
            #~ print "pushing {0} above {1}".format(name1, name2)
            return -1
        if id2 == "uncategorized":
            #~ print "pushing {1} above {0}".format(name1, name2)
            return 1
        #~ # finally sort by string
        if tp1 < tp2:
            #~ print "pushing {0} above {1}".format(name1, name2)
            return -1
        if tp1 > tp2:
            #~ print "pushing {0} below {1}".format(name1, name2)
            return -1
        if name1 < name2:
            #~ print "pushing {0} above {1}".format(name1, name2)
            return -1
        if name1 > name2:
            #~ print "pushing {0} below {1}".format(name1, name2)
            return 1
        #~ print "not comparing".format(name1, name2)     
        return 0
        #.now we can compare between text attributes
        
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
        cell.set_property("ellipsize", pango.ELLIPSIZE_END)
    
    def __format_row(self, a):
        gmap = {'feed':'missing', 'category':'gtk-directory'}
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
            gmap.get(a['id']) or gmap.get(a['type']),
            a.get('url'),
            a.get('category'),
            )
        return r
        
    def deselect(self, *args):
        self.sselect.unselect_all()
        self.menuselect.unselect_all()
        self.current_item = None

    def next_item(self, *args):
        model, iter = self.menuselect.get_selected()
        if model.get_value(iter, 0)=="category":
            #select the first child
            iter = model.iter_children(iter)
        if iter:
            niter = model.iter_next(iter)
            try: self.menuselect.select_iter(niter)
            except: pass
    
    def previous_item(self, *args): #FIXME: doesn't work
        model, iter = self.menuselect.get_selected()
        if model.get_value(iter, 0)=="category":
            #select the first child
            iter = model.iter_children(iter)
        if iter:
            s = model.get_string_from_iter(iter)
            if int(s) > 0:
                niter = model.get_iter_from_string(str(int(s)-1))
                self.menuselect.select_iter(niter)
        
    def __search(self, col, value, model=None):
        """
        Returns a path for the value we are looking for.
        """
        if not model:
            model = self.menuview.get_model()
        gmap = {0:'type', 1:'id', 2:'name', 3:'count'}
        #~ print "seaching for {0} == {1}".format(gmap.get(col), value)
        iter = model.get_iter_first()
        while iter:
            v = model.get_value(iter, col)
            if value == v:
                #~ print( "match found: {0} => {1}: {2}".format(gmap.get(col), v, model.get_value(iter, 2)))
                return iter
            elif model.iter_has_child(iter):
                citer = model.iter_children(iter)
                while citer:
                    v = model.get_value(citer, col)
                    if value == v:
                        #~ print( "match found: {0} => {1}: {2}".format(gmap.get(col), v, model.get_value(citer, 2)))
                        return citer
                    citer = model.iter_next(citer)
            iter = model.iter_next(iter)

    def refresh_unread_counts(self, item):
        # we need the increment
        print "refreshing", item['name']
        iter = self.__search(1, item['id'])
        if iter:
            ori = self.store.get_value(iter, 3) # original
            inc = item['count'] - ori
            self.__update_count(self.store, iter, 3, inc, [])
            self.__update_parent_count(iter, inc, [])
        # item is a feed
        iter = self.__search(0, 'unread')
        if iter:
            o = self.store.get_value(iter, 3) 
            self.__update_count(self.store, iter, 3, item[col], True)
    
    def __update_parent_count(self, iter, val, flags):
        if self.store.iter_parent(iter):
            self.__update_count(self.store, 
                self.store.iter_parent(iter), 3, val, flags)

    def update_starred(self, ilist, item):
        # if item['starred'] is 0, we go minus
        iter = self.__search(0, 'starred', self.sstore)
        self.__update_count(self.sstore, iter, 3, item['starred'], ['toggle'])

    def update_unread(self, ilist, item, col="read"):
        flags = ['toggle', 'invert']
        # if item['read'] is 0, we go plus
        # try to update the originating feed
        iter = self.__search(1, item['feed_id'])
        if iter:
            self.__update_count(self.store, iter, 3, item[col], flags)
            self.__update_parent_count(iter, item[col], flags)
        # now update unread
        iter = self.__search(0, 'unread', self.sstore)
        if iter:
            self.__update_count(self.sstore, iter, 3, item[col], flags)
    

    def __update_count (self, model, iter, col, var, flags):
        if 'replace' in flags:
            model.set_value(iter, col, var)
            return
        nval = ol = model.get_value(iter, col) # old value
        gmap = {}
        if 'toggle' in flags:
            gmap = {0:-1, 1:+1}# handle boolean
        if 'invert' in flags:
            gmap = {0:+1, 1:-1}# invert handling
        n = gmap.get(var) or var
        nval = ol + n # increment
        model.set_value(iter, col, nval)
        
    def make_special_folders(self, unread, starred):
        self.sstore.clear()
        u = ('unread', '0','Unread', unread, 'gtk-new')
        s = ('starred', '0', 'Starred', starred, 'gtk-about')
        self.sstore.append(None, u)
        self.sstore.append(None, s)
        self.emit('list-loaded')


    def fill_menu(self, data):
        """Load the given data into the left menuStore"""
        # return the first iter
        self.store.clear()
        if data:
            row = None
            for item in data:
                if item['type'] == 'category':
                    row = self.store.append(None, self.__format_row(item))
                if item['type'] == 'feed':
                    self.store.append(row, self.__format_row(item))
        self.menuview.expand_all()

    def insert_row(self, item):
        # start with categories:
        if item['type'] == 'category':
            self.store.append(None, self.__format_row(item))
        elif item['type'] == 'feed':
            iter = self.__search(1,item['category'])
            self.store.append(iter, self.__format_row(item))
            self.menuview.expand_row(self.store.get_path(iter), False)
    def __row_activated(self, treeview, path, col):
        item = self.__get_current(treeview.get_selection())
        
    def __selection_changed(self, selection, tg):
        item = self.__get_current(selection)
        if item:
            # emit the right signal
            self.emit('item-selected', item)
       
    
    def __get_current(self, selection):
        try:
            (model, iter) = selection.get_selected()
            path = model.get_path(iter)
            if iter:
                item = {
                    'type': model.get_value(iter, 0),
                    'id': model.get_value(iter, 1),
                    'name': model.get_value(iter, 2),
                }
                self.current_item = item
                return item
        except:pass
    
        
    def run_dialog(self, dialog_name, item):
        self.emit('dialog-request', dialog_name, item)
        
    def run_dcall(self, callback_name, item):
        self.emit('dcall-request', callback_name, item)
        
    # convenience
    def do_item_selected(self, item):
        #~ print 'Item selected: ', item
        if item['type'] in ['starred', 'unread']:
            self.menuselect.unselect_all()
        elif item['type'] in ['feed', 'category']:
            self.sselect.unselect_all()
    def do_list_loaded(self):
        iter = self.__search(0, 'unread', self.sstore)
        self.sselect.select_iter(iter)
        
class TreeMenu(Gtk.Menu):
    """
    TreeMenu extends the standard Gtk.Menu by adding methods 
    for context handling.
    """
    def __init__(self, tree):
        #~ #print "creating a ViewMenu"
        Gtk.Menu.__init__(self)
        self._dirty = True
        self._signal_ids = []
        self._tree = tree
        self._treeview = tree.menuview
        self._treeview.connect('button-release-event', self._on_event)
        self._treeview.connect('key-release-event', self._on_event)

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
        
    def _on_menuitem__activate(self, menuitem, callname, item):
        # switch dialog or direct call
        if callname in ['Edit', 'Add a Category', 'Add a Feed']:
            self._tree.run_dialog(callname, item)
        elif callname in ['Mark all as read', 'Update', 'Delete']:
            self._tree.run_dcall(callname, item)

    def _on_event(self, treeview, event):
        """Respond to mouse click or key press events in a GtkTree."""
        if event.type == Gdk.EventType.BUTTON_RELEASE:
            if event.button == 3:
                self.popup(event, self._tree.current_item)
        elif event.type == Gdk.EventType.KEY_RELEASE:
            if event.keyval == 65383: # Menu
                self.popup(event, self._tree.current_item)


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
