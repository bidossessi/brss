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
# our stuff
from itemlist   import ItemList
from tree       import Tree
from view       import View
from status     import Status
from alerts     import Alerts
from functions  import make_path    

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
        "next-article" : (
            GObject.SignalFlags.RUN_FIRST, 
            None,
            ()),            
        "previous-article" : (
            GObject.SignalFlags.RUN_FIRST, 
            None,
            ()),            
        "next-feed" : (
            GObject.SignalFlags.RUN_FIRST, 
            None,
            ()),            
        "previous-feed" : (
            GObject.SignalFlags.RUN_FIRST, 
            None,
            ()),            
        }

    def __repr__(self):
        return "BRss Reader"
    def __init__(self, base_path="."):
        Gtk.Window.__init__(self)
        self.__gobject_init__()
        GObject.type_register(Reader)
        try:
            self.__get_engine()
        except:
            # should we start it automitacally?
            self.quit()
            
        # ui elements
        self.tree = Tree(base_path)
        self.ilist = ItemList()
        self.ilist.set_property("height-request", 250)
        self.view = View()
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
            self.engine              = bus.get_object('com.itgears.brss', '/com/itgears/brss/Engine')
        except:
            self.quit()
        self.reate               = self.engine.get_dbus_method('create', 'com.itgears.brss')
        self.edit                = self.engine.get_dbus_method('edit', 'com.itgears.brss')
        self.update              = self.engine.get_dbus_method('update', 'com.itgears.brss')
        self.delete              = self.engine.get_dbus_method('delete', 'com.itgears.brss')
        self.get_menu_items      = self.engine.get_dbus_method('get_menu_items', 'com.itgears.brss')
        self.get_articles_for    = self.engine.get_dbus_method('get_articles_for', 'com.itgears.brss')
        self.search_for          = self.engine.get_dbus_method('search_for', 'com.itgears.brss')
        self.get_article         = self.engine.get_dbus_method('get_article', 'com.itgears.brss')
        self.toggle_starred      = self.engine.get_dbus_method('toggle_starred', 'com.itgears.brss')
        self.toggle_read         = self.engine.get_dbus_method('toggle_read', 'com.itgears.brss')
        self.count_unread        = self.engine.get_dbus_method('count_unread', 'com.itgears.brss')
        self.count_starred       = self.engine.get_dbus_method('count_starred', 'com.itgears.brss')
        self.import_opml         = self.engine.get_dbus_method('import_opml', 'com.itgears.brss')
        
    def __create__menu(self):
        ui_string = """<ui>
                   <menubar name='Menubar'>
                    <menu action='FeedMenu'>
                     <menuitem action='New feed'/>
                     <menuitem action='New category'/>
                     <menuitem action='Delete'/>
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
                     <menuitem action='NextArticle'/>
                     <menuitem action='PreviousArticle'/>
                     <menuitem action='NextFeed'/>
                     <menuitem action='PreviousFeed'/>
                    <separator />
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
                    <toolitem name='PreviousFeed' action='PreviousFeed'/>
                    <toolitem name='PreviousArticle' action='PreviousArticle'/>
                    <toolitem name='NextArticle' action='NextArticle'/>
                    <toolitem name='NextFeed' action='NextFeed'/>
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
                ('New category', "gtk-directory", 'New _category', '<alt>C', 'Adds a category'),
                ('Delete', "gtk-clear", 'Delete', 'Delete', 'Deletes a feed or a category', self.__delete),
                ('Import feeds', "gtk-redo", 'Import feeds', None, 'Imports a feedlist', self.import_feeds),
                ('Export feeds', "gtk-undo", 'Export feeds', None, 'Exports a feedlist'),
                ('Quit', "gtk-quit", '_Quit', '<control>Q', 'Quits', self.quit),
                ('EditMenu', None, 'E_dit'),
                ('Edit', "gtk-edit", '_Edit', '<control>E', 'Edits the selected element'),
                ('Preferences', "gtk-execute", '_Preferences', '<control>P', 'Shows preferences'),
                ('NetworkMenu', None, '_Network'),
                ('Update', None, '_Update', '<control>U', 'Updates the selected feed', self.__update_feed),
                ('Update all', "gtk-refresh", 'Update all', '<control>R', 'Update all feeds', self.__update_all),
                ('PreviousArticle', "gtk-go-back", 'Previous Article', '<control>b', 'Go to the previous article', self.__previous_article),
                ('NextArticle', "gtk-go-forward", 'Next Article', '<control>n', 'Go to the next article', self.__next_article),
                ('PreviousFeed', "gtk-goto-first", 'Previous Feed', '<control><shift>b', 'Go to the previous news feed', self.__previous_feed),
                ('NextFeed', "gtk-goto-last", 'Next Feed', '<control><shift>n', 'Go to the next news feed', self.__next_feed),
                ('Stop update', "gtk-stop", 'Stop', None, 'Stop update'),
                ('ViewMenu', None, '_View'),
                ('HelpMenu', None, '_Help'),
                ('About', "gtk-about", '_About', None, 'About'),
                ]
        tactions = [
                ('Search', "gtk-find", 'Search', '<control>F', 'Searchs for a term in the feeds', self.__toggle_search),
                ('FullScreen', "gtk-fullscreen", 'Fullscreen', 'F11', '(De)Activate fullscreen', self.__toggle_fullscreen),
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
        self.set_title('BRss')
        self.set_icon_from_file(make_path('icons','brss.svg'))
        #~ self.set_default_icon(get_pixbuf())
        self.alert = Alerts(self)
        self.show_all()
        

    def __connect_signals(self):    # signals
        self.connect("destroy", self.quit)
        self.connect('loaded', self.__populate_menu)
        self.connect('next-article', self.ilist.next_item)
        self.connect('previous-article', self.ilist.previous_item)
        self.connect('next-feed', self.tree.next_item)
        self.connect('previous-feed', self.tree.previous_item)
        self.connect('search-toggled', self.ilist.toggle_search)
        self.tree.connect('item-selected', self.__load_articles)
        self.tree.connect('dcall-request', self.__handle_dcall)
        self.ilist.connect('item-selected', self.__load_article)
        self.ilist.connect('item-selected', self.__update_title)
        self.ilist.connect('no-data', self.view.clear)
        self.ilist.connect('star-toggled', self.__toggle_starred)
        self.ilist.connect('read-toggled', self.__toggle_read)
        self.ilist.connect_after('star-toggled', self.tree.update_starred)
        self.ilist.connect_after('read-toggled', self.tree.update_unread)
        self.ilist.connect('dcall-request', self.__handle_dcall)
        self.ilist.connect('search-requested', self.__search_articles)
        self.ilist.connect('search-requested', self.tree.deselect)
        self.view.connect('article-loaded', self.ilist.mark_read)
        self.view.connect('link-clicked', self.__to_browser)
        self.view.connect('link-hovered', self.__status_info)
        self.engine.connect_to_signal('notice', self.status.message)
        #~ self.engine.connect_to_signal('added', self.__populate_menu)
        self.engine.connect_to_signal('added', self.status.message)
        self.engine.connect_to_signal('newitem', self.tree.insert_row)
        self.engine.connect_to_signal('feedupdate', self.tree.refresh_unread_counts)
        # might want to highlight these a bit more
        #~ self.engine.connect_to_signal('warning', self.status.message)
    
    
    #~ def import_feeds(self, *args):pass
    def import_feeds(self, *args):
        dialog = Gtk.FileChooserDialog("Open..",
                                    self,
                                    Gtk.FileChooserAction.OPEN,
                                    (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                                      Gtk.STOCK_OPEN, Gtk.ResponseType.OK))

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
            self.status.message("wait", "Importing Feeds")
            self.import_opml(filename, 
                reply_handler=self.__to_log,
                error_handler=self.__to_log)
    
    def __populate_menu(self, *args):
        menu = self.get_menu_items()
        unread = self.count_unread()
        starred = self.count_starred()
        self.tree.fill_menu(menu, unread, starred)
        
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
    def __delete(self, *args):
        self.__handle_dcall(self, 'Delete', self.tree.current_item)
    def __update_all(self, *args):
        self.__handle_dcall(self, 'Update', 'all')
    def __load_article(self, ilist, item):
        self.get_article(item, 
                reply_handler=self.view.show_article,
                error_handler=self.__to_log)
    def __handle_new(self, item):
        if item['type'] in ['feed', 'category']:
            self.tree.insert_row(item)
    def __handle_dcall(self, caller, name, item):
        if name in ['Update', 'Update all']:
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
        
        elif name in ['Delete', 'Delete Feed', 'Delete Category']:
            self.alert.question("Are you sure you want to delete this {0}".format(item['type']),
                "This action cannot be undone."
                )
            if self.alert.checksum:
                self.delete(item,
                    reply_handler=self.__populate_menu,
                    error_handler=self.__to_log)
    def __search_articles(self, caller, string):
        self.search_for(string,
                reply_handler=self.ilist.load_list,
                error_handler=self.__to_log)
    def __toggle_stop(self):
        gmap = {True:False, False: True}
        widget = self.ui.get_widget('/Toolbar/Stop')
        widget.set_sensitive(
            gmap.get(widget.get_sensitive()))
    def __toggle_search(self, *args):
        self.emit('search-toggled')
    def __update_done(self, *args):
        self.__toggle_stop()
    def __update_title(self, caller, item):
        self.set_title(item['title'])
    def __status_info(self, caller, message):
        print message
        self.status.message('info', message)
        
    def __to_log(self, *args):
        print 'Log: ', args
    
    def __to_browser(self, caller, link):
        # try the config
        print link
        # fallback to default
        self.view.link_button.set_uri(link)
        self.view.link_button.activate()
        
    def __previous_article(self, *args):
        self.emit('previous-article')
    def __next_article(self, *args):
        self.emit('next-article')
    def __previous_feed(self, *args):
        self.emit('previous-feed')
    def __next_feed(self, *args):
        self.emit('next-feed')
    
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

    #~ def do_loaded(self, *args):
        #~ print "Reader loaded"

def main():
    app = Reader()
    app.run()
    
if __name__ == '__main__':
    main()
