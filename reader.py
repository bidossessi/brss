#!/usr/bin/env python2
# -*- coding: utf-8 -*-
#
#       reader.py
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
from gi.repository import Pango
from gi.repository import GObject
import dbus
import dbus.mainloop.glib
dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
import os
import webbrowser
# our stuff
from itemlist   import ItemList
from feedtree   import FeedTree
from feedview   import FeedView
from status     import Status

class Reader (Gtk.Window, GObject.GObject):
    """
        
    """
    __gsignals__ = {
        "loaded" : (
            GObject.SignalFlags.RUN_FIRST, 
            None,
            ()),
        "search-toggled" : (
            GObject.SignalFlags.RUN_FIRST, 
            None,
            ()),
        "next-item" : (
            GObject.SignalFlags.RUN_FIRST, 
            None,
            ()),            
        "previous-item" : (
            GObject.SignalFlags.RUN_FIRST, 
            None,
            ()),            
        }

    def __init__(self):
        Gtk.Window.__init__(self)
        self.__gobject_init__()
        GObject.type_register(Reader)
        
        try:
            self.__get_engine()
        except:
            # should we start it automitacally?
            self.quit()
            
        # ui elements
        self.tree = FeedTree()
        self.ilist = ItemList()
        self.ilist.set_property("height-request", 250)
        self.view = FeedView()
        self.status = Status()
        # layout
        self.__layout_ui()
        #signals
        self.__connect_signals()
        # ready to go
        self.emit('loaded')
        
    def __get_engine(self):
        # dbus
        bus                 = dbus.SessionBus()
        try:
            self.engine              = bus.get_object('org.naufrago.feedengine', '/org/naufrago/feedengine')
        except:
            self.quit()
        self.add_category        = self.engine.get_dbus_method('add_category', 'org.naufrago.feedengine')
        self.get_categories      = self.engine.get_dbus_method('get_categories', 'org.naufrago.feedengine')
        self.get_feeds_for       = self.engine.get_dbus_method('get_feeds_for', 'org.naufrago.feedengine')
        self.add_feed            = self.engine.get_dbus_method('add_feed', 'org.naufrago.feedengine')
        self.get_articles_for    = self.engine.get_dbus_method('get_articles_for', 'org.naufrago.feedengine')
        self.update              = self.engine.get_dbus_method('update', 'org.naufrago.feedengine')
        self.get_article         = self.engine.get_dbus_method('get_article', 'org.naufrago.feedengine')
        self.toggle_starred      = self.engine.get_dbus_method('toggle_starred', 'org.naufrago.feedengine')
        self.toggle_read         = self.engine.get_dbus_method('toggle_read', 'org.naufrago.feedengine')
        self.count_unread        = self.engine.get_dbus_method('count_unread', 'org.naufrago.feedengine')
        self.count_starred       = self.engine.get_dbus_method('count_starred', 'org.naufrago.feedengine')
        self.import_opml         = self.engine.get_dbus_method('import_opml', 'org.naufrago.feedengine')
        
    def __create__menu(self):
        ui_string = """<ui>
                   <menubar name='Menubar'>
                    <menu action='FeedMenu'>
                     <menuitem action='New feed'/>
                     <menuitem action='New category'/>
                     <menuitem action='Delete feed'/>
                     <menuitem action='Delete category'/>
                     <separator/>
                     <menuitem action='Import feeds'/>
                     <menuitem action='Export feeds'/>
                     <separator/>
                     <menuitem action='Quit'/>
                    </menu>
                    <menu action='EditMenu'>
                     <menuitem action='Edit'/>
                     <menuitem action='Search'/>
                     <menuitem action='Preferences'/>
                    </menu>
                    <menu action='NetworkMenu'>
                     <menuitem action='Update'/>
                     <menuitem action='Update all'/>
                    </menu>
                    <menu action='ViewMenu'>
                     <menuitem action='FullScreen'/>
                    </menu>
                    <menu action='HelpMenu'>
                     <menuitem action='About'/>
                    </menu>
                   </menubar>
                   <toolbar name='Toolbar'>
                    <toolitem name='New feed' action='New feed'/>
                    <toolitem name='New category' action='New category'/>
                    <separator name='sep1'/>
                    <toolitem name='Update all' action='Update all'/>
                    <toolitem name='Stop' action='Stop update'/>
                    <separator name='sep2'/>
                    <toolitem name='Previous' action='Previous'/>
                    <toolitem name='Next' action='Next'/>
                    <separator name='sep3'/>
                    <toolitem name='FullScreen' action='FullScreen'/>
                    <toolitem name='Search' action='Search'/>
                    <toolitem name='Preferences' action='Preferences'/>
                   </toolbar>
                  </ui>"""

        # Generate a stock image from a file (http://faq.pyGtk.org/index.py?req=show&file=faq08.012.htp)



        ag = Gtk.ActionGroup('WindowActions')
        actions = [
                ('FeedMenu', None, '_Feeds'),
                ('New feed', 'feed', '_New feed', '<control>N', 'Adds a feed'),
                ('New category', "Gtk-directory", 'New _category', '<alt>C', 'Adds a category'),
                ('Delete feed', "Gtk-clear", 'Delete feed', None, 'Deletes a feed'),
                ('Delete category', "Gtk-cancel", 'Delete category', None, 'Deletes a category'),
                ('Import feeds', "Gtk-redo", 'Import feeds', None, 'Imports a feedlist', self.import_feeds),
                ('Export feeds', "Gtk-undo", 'Export feeds', None, 'Exports a feedlist'),
                ('Quit', "Gtk-quit", '_Quit', '<control>Q', 'Quits', self.quit),
                ('EditMenu', None, 'E_dit'),
                ('Edit', "Gtk-edit", '_Edit', '<control>E', 'Edits the selected element'),
                ('Preferences', "Gtk-execute", '_Preferences', '<control>P', 'Shows preferences'),
                ('NetworkMenu', None, '_Network'),
                ('Update', None, '_Update', '<control>U', 'Updates the selected feed', self.__update_feed),
                ('Update all', "Gtk-refresh", 'Update all', '<control>R', 'Update all feeds', self.__update_all),
                ('Previous', "Gtk-go-back", 'Previous Article', '<control>b', 'Go to the previous article', self.__previous),
                ('Next', "Gtk-go-forward", 'Next Article', '<control>n', 'Go to the next article', self.__next),
                ('Stop update', "Gtk-stop", 'Stop', None, 'Stop update'),
                ('ViewMenu', None, '_View'),
                ('HelpMenu', None, '_Help'),
                ('About', "Gtk-about", '_About', None, 'About'),
                ]
        tactions = [
                ('Search', "Gtk-find", 'Search', '<control>F', 'Searchs for a term in the feeds', self.__search),
                ('FullScreen', "Gtk-fullscreen", 'Fullscreen', 'F11', '(De)Activate fullscreen', self.__toggle_fullscreen),
                ]

        ag.add_actions(actions)
        ag.add_toggle_actions(tactions)
        self.ui = Gtk.UIManager()
        self.ui.insert_action_group(ag, 0)
        self.ui.add_ui_from_string(ui_string)
        self.add_accel_group(self.ui.get_accel_group())

    def __layout_ui(self):
        self.__create__menu()
        opane = Gtk.VPaned()
        opane.pack1(self.ilist)
        opane.pack2(self.view)
        pane = Gtk.HPaned()
        pane.pack1(self.tree)
        pane.pack2(opane)
        box = Gtk.VBox(spacing=3)
        box.pack_start(self.ui.get_widget('/Menubar'), False, True, 0)
        box.pack_start(self.ui.get_widget('/Toolbar'), False, True, 0)
        widget = self.ui.get_widget("/Toolbar/Stop")
        widget.set_sensitive(False)
        box.pack_start(pane, True, True, 0)
        box.pack_start(self.status, False, False, 0)
        self.add(box)
        self.set_property("height-request", 700)
        self.set_property("width-request", 1024)
        self.is_fullscreen = False
        self.set_title('DBus RSS')
        self.set_icon_from_file('logo2.svg')
        self.show_all()
        

    def __connect_signals(self):    # signals
        self.connect("destroy", self.quit)
        self.connect('loaded', self.__populate_menu)
        self.connect('next-item', self.ilist.next_item)
        self.connect('previous-item', self.ilist.previous_item)
        self.connect('search-toggled', self.ilist.toggle_search)
        self.tree.connect('item-selected', self.__load_articles)
        self.tree.connect('dcall-request', self.__handle_dcall)
        self.ilist.connect('item-selected', self.__load_article)
        self.ilist.connect('star-toggled', self.__toggle_starred)
        self.ilist.connect('read-toggled', self.__toggle_read)
        self.ilist.connect_after('star-toggled', self.tree.update_starred)
        self.ilist.connect_after('read-toggled', self.tree.update_unread)
        self.ilist.connect('dcall-request', self.__handle_dcall)
        self.view.connect('article-loaded', self.ilist.mark_read)
        self.view.connect('link-clicked', self.__to_browser)
        self.engine.connect_to_signal('notice', self.status.message)
        # might want to highlight these a bit more
        #~ self.engine.connect_to_signal('warning', self.status.message)
    
    
    #~ def import_feeds(self, *args):pass
    def import_feeds(self, *args):
        dialog = Gtk.FileChooserDialog("Open..",
                                    self,
                                    Gtk.FileChooserAction.OPEN,
                                    (Gtk.STOCK_OPEN, Gtk.ResponseType.OK,
                                    Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL))

        dialog.set_default_response(Gtk.ResponseType.OK)

        filter = Gtk.FileFilter()
        filter.set_name("opml/xml")
        filter.add_pattern("*.opml")
        filter.add_pattern("*.xml")
        dialog.add_filter(filter)

        filter = Gtk.FileFilter()
        filter.set_name("All files")
        filter.add_pattern("*")
        dialog.add_filter(filter)

        response = dialog.run()
        filename = os.path.abspath(dialog.get_filename())
        dialog.destroy()

        if response == Gtk.ResponseType.OK:
            dialog.hide()
            self.import_opml(filename, 
                reply_handler=self.__populate_menu,
                error_handler=self.__to_log)
    
    def __populate_menu(self, *args):
        cats = self.get_categories()
        for c in cats:
            feeds = self.get_feeds_for(c)
            c['feeds'] = feeds
        unread = self.count_unread()
        starred = self.count_starred()
        self.tree.fill_menu(cats, int(unread), int(starred))
        
    def __toggle_starred(self, ilist, item):
        self.toggle_starred(item)
    def __toggle_read(self, ilist, item):
        self.toggle_read(item)
    def __load_articles(self, tree, item):
        self.get_articles_for(item, 
                reply_handler=self.ilist.load_list,
                error_handler=self.__to_log)
    
    def __update_feed(self, *args):
        self.__handle_dcall(self, 'Update', self.tree.current_item)
    def __update_all(self, *args):
        self.__handle_dcall(self, 'Update', 'all')
    def __load_article(self, ilist, item):
        self.get_article(item, 
                reply_handler=self.view.show_article,
                error_handler=self.__to_log)

    def __delete_item(self, tree, item):
        self.delete_item(item,
                reply_handler=self.__populate_menu,
                error_handler=self.__to_log)

    def __handle_dcall(self, caller, name, item):
        #~ print "{0}: {1}".format(name, item)
        if name in ['Update', 'Update all']:
            if item == 'all':
                self.status.message("wait", "Updating all Feeds")
            else:
                self.status.message("wait", "Updating {0}".format(item['name']))
            self.__toggle_stop()
            self.update(item,
                reply_handler=self.__update_done,
                error_handler=self.__to_log)
        elif name in ['Mark all as read']:
            self.ilist.mark_all_read()
        
        elif name in ['Open in Browser']:
            self.__to_browser(caller, item['url'])
        
        elif name in ['Copy Url to Clipboard']:
            self.__to_clipboard(item['url'])
    
    def __toggle_stop(self):
        gmap = {True:False, False: True}
        widget = self.ui.get_widget('/Toolbar/Stop')
        widget.set_sensitive(
            gmap.get(widget.get_sensitive()))
    
    def __search(self, *args):
        self.emit('search-toggled')
    
    def __update_done(self, *args):
        self.__toggle_stop()
        
    def __to_log(self, *args):
        print 'Log: ', args
    
    def __to_browser(self, caller, link):
        # try the config
        print link
        # fallback to default
        self.view.link_button.set_uri(link)
        self.view.link_button.activate()
        
    def __previous(self, *args):
        self.emit('previous-item')
    def __next(self, *args):
        self.emit('next-item')
    
    def __to_clipboard(self, link):
        clipboard = Gtk.Clipboard()
        clipboard.set_text(link.encode("utf8"), -1)
        clipboard.store()

    def __toggle_fullscreen(self, *args):
        if self.is_fullscreen == True:
            self.ilist.show()
            self.tree.show()
            self.unfullscreen()
            self.is_fullscreen = False
        else:
            self.ilist.hide()
            self.tree.hide()
            self.fullscreen()
            self.is_fullscreen = True
    
    def quit(self, *args):
        Gtk.main_quit()
    
    def run(self):
        Gtk.main()
        
if __name__ == '__main__':
    
    app = Reader()
    app.run()
