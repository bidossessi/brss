#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#       ArticleList.py
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
# TODO: 
from gi.repository  import Gtk
from gi.repository  import Gio
from gi.repository  import Gdk
from gi.repository  import GObject
from gi.repository  import Pango
import i18n
_ = i18n.language.gettext

from common      import make_date
from common      import BASE_KEY

class ArticleList (Gtk.VBox, GObject.GObject):
    """
        The ArticleList, well, lists all available feed items for the selected
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
        "filter-ready" : (
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
        "row-updated" : (
            GObject.SignalFlags.RUN_LAST, 
            None,
            (GObject.TYPE_PYOBJECT,)),
        "item-selected" : (
            GObject.SignalFlags.RUN_LAST, 
            None,
            (GObject.TYPE_PYOBJECT,)),
        "no-more-items" : (
            GObject.SignalFlags.RUN_LAST, 
            None,
            ()),
        "dcall-request" : (
            GObject.SignalFlags.RUN_LAST, 
            None,
            (GObject.TYPE_STRING, GObject.TYPE_PYOBJECT,)),
        }
    
    def __init__(self, logger):
        self.log = logger
        #TODO: break init up 
        Gtk.VBox.__init__(self, spacing=3)
        GObject.GObject.__init__(self)
        self.settings = Gio.Settings.new(BASE_KEY)
        self.current_item   = None
        self.last_search    = None
        self.lmap = ['id','read','starred','date','title','url', 'weight', 'feed_id']
        self.store = Gtk.ListStore(str, bool, bool, int, str, str, int, str)
        self.listview = Gtk.TreeView()
        self.listview.set_model(self.store)
        self.listview.connect("row-activated", self.__row_activated)
        ## COLUMNS | store structure (id, read, starred, date, title, url, weight, feed_id)
        # read
        column = Gtk.TreeViewColumn()
        label = Gtk.Label(label=_('Read'))
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
        label = Gtk.Label(label=_('Star'))
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
        label = Gtk.Label(label=_('Date'))
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
        label = Gtk.Label(label=_('Title'))
        label.show()
        column.set_widget(label)
        column.set_resizable(True)
        cell = Gtk.CellRendererText()
        column.pack_start(cell, True)
        column.add_attribute(cell, "text", 4)
        column.add_attribute(cell, "weight", 6)
        cell.set_property("ellipsize", Pango.EllipsizeMode.END)        
        column.set_sort_column_id(4)
        self.listview.append_column(column)
        # enable quick-searching
        self.listview.set_search_column(4)
        # connect selection
        self.listselect = self.listview.get_selection()
        # containers
        self.msc = Gtk.ScrolledWindow()
        self.msc.set_shadow_type(Gtk.ShadowType.IN)
        self.msc.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.msc.add(self.listview)
        self.mal = Gtk.Alignment.new(0.5, 0.5, 1, 1)
        self.mal.add(self.msc)
        self.pack_end(self.mal, True, True,0)
        self.set_property("width-request", 600)
        menu = ArticleListMenu(self)
        self.current_item = None
        GObject.type_register(ArticleList)
        self.__lock__ = False
        self.listselect.set_select_function(self.__skip_toggles, None)
        self.search_on = False
    def __repr__(self):
        return "ArticleList"
        
    def __get_weight(self, read):
        if read and int(read) > 0:
            return 400
        return 800
    def __get_date(self, timestamp):
        try:
            return date.strftime (locale.nl_langinfo(locale.D_FMT))
        except Exception, e:
            self.log.exception(e) 
            return ""   
    def __format_date(self, column, cell, model, iter, col):
        cell.set_property('text', make_date(model.get_value(iter, 3)))
    def __format_row(self, a):
        r = (
                a['id'],
                a['read'],
                a['starred'],
                a['date'],
                a['title'],
                a['url'],
                self.__get_weight(a['read']),
                a['feed_id'],
            )
        return r
        
    def load_list(self, data):
        self.log.debug("{0}: Loading articles".format(self))
        try:
            self.listselect.disconnect_by_func(self.__selection_changed)
        except:pass
        store = self.listview.get_model()
        store.clear()
        # store structure (id, read, starred, date, title, url, weight, feed_id)
        if data:
            for art in data:
                store.append(self.__format_row(art))
            self.listview.set_model(store)
            self.emit('list-loaded')
        else:
            self.emit('no-data')
    def insert_row(self, item):
        self.log.debug("{0}: Adding row {1}".format(self, item['id']))
        iter = self.store.append(None, self.__format_row(item))

    def update_row(self, item):
        #find the item
        self.log.debug("{0}: Updating row {1}".format(self, item['id']))
        iter = self.__search(0, item['id'])
        if iter:
            changed = {}
            for k,v in item.iteritems():
                try:
                    o = self.store.get_value(iter, self.lmap.index(k))
                    if k in ['id', 'feed_id'] or o != v:
                        self.store.set_value(iter, self.lmap.index(k), v)
                        changed[k] = v
                        if k == 'read':
                            self.store.set_value(iter, self.lmap.index('weight'), self.__get_weight(v))
                except Exception, e:
                    #~ self.log.exception(e)
                    pass # we don't really care about this one 
        try:
            self.emit('row-updated', changed)
        except Exception, e:
            self.log.exception(e)
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
        ## search
        self.filterentry = Gtk.Entry()
        if self.settings.get_boolean('live-search'):
            self.filterentry.set_property("secondary-icon-stock", "gtk-clear")
            self.filterentry.connect("changed", self.__request_search)
        else:
            self.filterentry.set_property("secondary-icon-stock", "gtk-find")
            self.filterentry.connect("activate", self.__request_search)
        self.filterentry.set_property("secondary-icon-activatable", True)
        self.filterentry.set_property("secondary-icon-tooltip-text", "Clear the search")
        self.filterentry.connect("icon-press", self.__icon_pressed)            
        self.fbox = Gtk.HBox(spacing=3)
        self.fbox.pack_start(self.filterentry, True, True, 0)
        self.pack_start(self.fbox, False, False,0)
        self.fbox.show()
        self.__clear_filter()
        self.filterentry.show()
        self.search_on = True
        self.emit('filter-ready')
    
    def __hide_search(self):
        self.filterentry.destroy()
        self.fbox.destroy()
        self.search_on = False
    
    def __icon_pressed(self, entry, icon_pos, event):
        """Clears the standard filter GtkEntry."""
        if icon_pos.value_name == "GTK_ENTRY_ICON_SECONDARY":
            if event.button == 3 or event.button == 1:
                if not self.settings.get_boolean('live-search'):
                    self.__request_search(entry)
                self.__clear_filter()
    
    def __request_search(self, entry, *args):
        self.last_search = entry.get_text()
        if len(self.last_search) > 0:
            self.emit('search-requested', self.last_search)
        
    def __clear_filter(self):
        self.filterentry.set_text("")
        
    def next_item(self, *args):
        model, iter = self.listselect.get_selected()
        niter = model.iter_next(iter)
        if niter:
            try: self.__select_iter(self.listview, niter)
            except Exception, e:
                self.log.exception(e) 
        else:
            self.emit('no-more-items')
    def previous_item(self, *args):
        model, iter = self.listselect.get_selected()
        if iter:
            s = model.get_string_from_iter(iter)
            if int(s) > 0:
                niter = model.get_iter_from_string(str(int(s)-1))
                self.__select_iter(self.listview, niter)
        else:
            self.emit('no-more-items')

    def __select_iter(self, treeview, iter):
        self.log.debug("{0}: selecting an iter".format(self))
        try:
            model = treeview.get_model()
            sel = treeview.get_selection()
            path = model.get_path(iter)
            sel.select_path(path)
            treeview.scroll_to_cell(path, use_align=True)
        except Exception, e:
            self.log.exception(e)
    def __search(self, col, value):
        """
        Returns a iter for the value we are looking for.
        """
        model = self.store
        iter = model.get_iter_first()
        while iter:
            v = model.get_value(iter, col)
            if value == v:
                return iter
            iter = model.iter_next(iter)
        return None
    def __get_current(self, row=False):
        bmap = {False:"0", True:"1"}
        if row:
            self.current_item = {
                'type':'article',
                'id': row[0],
                'read': row[1],
                'starred': row[2],
                'title': row[4],
                'url': row[5],
                'feed_id': row[7],
            }
            return self.current_item
        else:
            (model, iter) = self.listselect.get_selected()
            if iter:
                self.current_item = {
                    'type':'article',
                    'id': model.get_value(iter, 0),
                    'read': bmap.get(model.get_value(iter, 1)),
                    'starred': bmap.get(model.get_value(iter, 2)),
                    'title': model.get_value(iter, 4),
                    'url': model.get_value(iter, 5),
                    'feed_id': model.get_value(iter, 7),
                }
                return self.current_item
    
    def __toggle_star(self, cell, path, model):
        self.__lock__ = True
        self.emit('star-toggled', self.__get_current(model[path]))
    
    def __toggle_read(self, cell, path, model):
        self.__lock__ = True
        self.emit('read-toggled', self.__get_current(model[path]))
    
    def __skip_toggles(self, selection, *args):
        if self.__lock__ == True:
            self.__lock__ = False
            return False
        return True
    
    def mark_read(self, *args):
        """Mark the current article as read."""
        (model, iter) = self.listselect.get_selected()
        if iter:
            path = model.get_path(iter)
            item = self.__get_current(model[path])
            item['read'] = False # forcing it
            self.emit('read-toggled', item)

    def toggle_read(self, *args):
        """Mark the current article as read."""
        (model, iter) = self.listselect.get_selected()
        if iter:
            path = model.get_path(iter)
            item = self.__get_current(model[path])
            #~ item['starred'] = False # forcing it
            self.emit('read-toggled', item)

    def mark_starred(self, *args):
        """Mark the current article as read."""
        (model, iter) = self.listselect.get_selected()
        if iter:
            path = model.get_path(iter)
            item = self.__get_current(model[path])
            #~ item['starred'] = False # forcing it
            self.emit('star-toggled', item)

    def mark_all_read(self, *args):
        """Mark the current article as read."""
        model = self.listview.get_model()
        iter = model.get_iter_first()
        while iter:
            path = model.get_path(iter)
            item = self.__get_current(model[path])
            item['read'] = False # forcing it
            self.emit('read-toggled', item)
            iter = model.iter_next(iter)

    def run_dcall(self, callback_name, item):
        self.emit('dcall-request', callback_name, item)    
    # closure
    def do_item_selected(self, item):
        self.log.debug('{0}: Item selected {1}'.format(self, item['title']))
    #~ def do_star_toggled(self, item):
        #~ self.log.debug('{0}: Star this {1}'.format(self, item['id']))
    #~ def do_read_toggled(self, item):
        #~ self.log.debug('{0}: Toggle this {1}'.format(self, item['id']))
    #~ def do_search_requested(self, item):
        #~ self.log.debug('{0}: Search for {1}'.format(self, item))
    #~ def do_no_data(self):
        #~ self.log.debug('{0}: No data found'.format(self))
    def do_list_loaded(self):
        self.listselect.connect("changed", self.__selection_changed)
        try:
            self.log.debug("{0}: selecting current article".format(self))
            iter = self.__search(0, self.current_item['id'])
            if iter:
                self.__select_iter(self.listview, iter)
            else:
                self.__select_first()
        except Exception,e:
            self.log.exception(e)
            self.__select_first()
    def __select_first(self):
            self.log.debug("{0}: selecting first article".format(self))
            iter = self.store.get_iter_first()
            self.__select_iter(self.listview, iter)

class ArticleListMenu(Gtk.Menu):
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
    def _create(self, item):
        if not self._dirty:
            return
        self.clean()
        for i in [_('Mark all as read'), _('Open in Browser'), 
            _('Copy Url to Clipboard')]:
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
