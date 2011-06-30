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
import dbus.service
import dbus.mainloop.glib
dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
import os
import subprocess
import time
# our stuff
from itemlist   import ItemList
from tree       import Tree
from view       import View
from status     import Status
from alerts     import Alerts
from dialogs    import Dialog
from functions  import make_path, make_pixbuf
from logger     import Logger

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
        "no-engine" : (
            GObject.SignalFlags.RUN_FIRST, 
            None,
            ()),            
        }

    def __repr__(self):
        return "BRssReader"
    def __init__(self, base_path="."):
        Gtk.Window.__init__(self)
        self.__gobject_init__()
        GObject.type_register(Reader)
        self.log = Logger(base_path, "brss-reader.log", "BRss-Reader")

        # ui elements
        self.tree = Tree(base_path, self.log)
        self.ilist = ItemList(self.log)
        self.ilist.set_property("height-request", 250)
        self.view = View(self.log)
        self.status = Status()
        # layout
        self.__layout_ui()
        #signals
        self.__get_engine()            
        self.__connect_signals()
        # ready to go
        self.emit('loaded')
        
    def __get_engine(self):
        # dbus
        bus                 = dbus.SessionBus()
        try:
            self.engine              = bus.get_object('com.itgears.BRss.Engine', '/com/itgears/BRss/Engine')
        except:
            self.log.critical("{0}: Couldn't get a DBus connection; quitting.".format(self))
            self.alert.error("Could not connect to Engine", 
            "BRss will now quit.\nPlease make sure that the engine is running and restart the application")
            self.quit()
        self.create               = self.engine.get_dbus_method('create', 'com.itgears.BRss.Engine')
        self.edit                = self.engine.get_dbus_method('edit', 'com.itgears.BRss.Engine')
        self.update              = self.engine.get_dbus_method('update', 'com.itgears.BRss.Engine')
        self.delete              = self.engine.get_dbus_method('delete', 'com.itgears.BRss.Engine')
        self.get_menu_items      = self.engine.get_dbus_method('get_menu_items', 'com.itgears.BRss.Engine')
        self.get_articles_for    = self.engine.get_dbus_method('get_articles_for', 'com.itgears.BRss.Engine')
        self.search_for          = self.engine.get_dbus_method('search_for', 'com.itgears.BRss.Engine')
        self.get_article         = self.engine.get_dbus_method('get_article', 'com.itgears.BRss.Engine')
        self.toggle_starred      = self.engine.get_dbus_method('toggle_starred', 'com.itgears.BRss.Engine')
        self.toggle_read         = self.engine.get_dbus_method('toggle_read', 'com.itgears.BRss.Engine')
        self.count_special       = self.engine.get_dbus_method('count_special', 'com.itgears.BRss.Engine')
        self.get_configs         = self.engine.get_dbus_method('get_configs', 'com.itgears.BRss.Engine')
        self.set_configs         = self.engine.get_dbus_method('set_configs', 'com.itgears.BRss.Engine')
        self.import_opml         = self.engine.get_dbus_method('import_opml', 'com.itgears.BRss.Engine')
        self.export_opml         = self.engine.get_dbus_method('export_opml', 'com.itgears.BRss.Engine')
        self.ag.get_action('Reconnect').set_visible(False)
        self.status.message('ok', 'Connected to engine')
        self.log.debug("{0}: Connected to feed engine {1}".format(self, self.engine))
    def __create_menu(self):
        ui_string = """<ui>
                   <menubar name='Menubar'>
                    <menu action='FeedMenu'>
                     <menuitem action='New feed'/>
                     <menuitem action='New category'/>
                     <menuitem action='Delete'/>
                     <separator/>
                     <menuitem action='Import feeds'/>
                     <menuitem action='Export feeds'/>
                     <separator />
                     <menuitem name='Reconnect' action='Reconnect'/>
                     <separator/>
                     <menuitem action='Quit'/>
                    </menu>
                    <menu action='EditMenu'>
                     <menuitem action='Edit'/>
                     <menuitem action='Find'/>
                     <menuitem action='Preferences'/>
                    </menu>
                    <menu action='NetworkMenu'>
                     <menuitem action='Update'/>
                     <menuitem action='Update all'/>
                    </menu>
                    <menu action='ViewMenu'>
                     <menuitem action='NextArticle'/>
                     <menuitem action='PreviousArticle'/>
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
                    <toolitem name='Reconnect' action='Reconnect'/>
                    <separator />
                    <toolitem name='Update all' action='Update all'/>
                    <toolitem name='Stop' action='Stop update'/>
                    <separator name='sep2'/>
                    <toolitem name='PreviousArticle' action='PreviousArticle'/>
                    <toolitem name='NextArticle' action='NextArticle'/>
                    <separator name='sep3'/>
                    <toolitem name='FullScreen' action='FullScreen'/>
                    <toolitem name='Find' action='Find'/>
                    <toolitem name='Preferences' action='Preferences'/>
                   </toolbar>
                  </ui>"""

        # Generate a stock image from a file (http://faq.pyGtk.org/index.py?req=show&file=faq08.012.htp)



        self.ag = Gtk.ActionGroup('WindowActions')
        actions = [
                ('FeedMenu', None, '_Feeds'),
                ('New feed', 'feed', '_New feed', '<control>N', 'Add a feed', self.__add_feed),
                ('New category', "gtk-directory", 'New _category', '<alt>C', 'Add a category', self.__add_category),
                ('Delete', "gtk-clear", 'Delete', 'Delete', 'Delets a feed or a category', self.__delete_item),
                ('Import feeds', "gtk-redo", 'Import feeds', None, 'Import a feedlist', self.__import_feeds),
                ('Export feeds', "gtk-undo", 'Export feeds', None, 'Export a feedlist', self.__export_feeds),
                ('Reconnect', "gtk-disconnect", '_Reconnect', None, 'Try and reconnect to the feed engine', self.__reconnect),
                ('Quit', "gtk-quit", '_Quit', '<control>Q', 'Quits', self.quit),
                ('EditMenu', None, 'E_dit'),
                ('Edit', "gtk-edit", '_Edit', '<control>E', 'Edit the selected element'),
                ('Preferences', "gtk-preferences", '_Preferences', '<control>P', 'Configure the engine', self.__edit_prefs),
                ('NetworkMenu', None, '_Network'),
                ('Update', None, '_Update', '<control>U', 'Update the selected feed', self.__update_feed),
                ('Update all', "gtk-refresh", 'Update all', '<control>R', 'Update all feeds', self.__update_all),
                ('PreviousArticle', "gtk-go-back", 'Previous Article', '<control>b', 'Go to the previous article', self.__previous_article),
                ('NextArticle', "gtk-go-forward", 'Next Article', '<control>n', 'Go to the next article', self.__next_article),
                ('PreviousFeed', "gtk-goto-first", 'Previous Feed', '<control><shift>b', 'Go to the previous news feed', self.__previous_feed),
                ('NextFeed', "gtk-goto-last", 'Next Feed', '<control><shift>n', 'Go to the next news feed', self.__next_feed),
                ('Stop update', "gtk-stop", 'Stop', None, 'Stop update'),
                ('ViewMenu', None, '_View'),
                ('HelpMenu', None, '_Help'),
                ('About', "gtk-about", '_About', None, 'About', self.__about),
                ]
        tactions = [
                ('Find', "gtk-find", 'Find', '<control>F', 'Search for a term in the articles', self.__toggle_search),
                ('FullScreen', "gtk-fullscreen", 'Fullscreen', 'F11', '(De)Activate fullscreen', self.__toggle_fullscreen),
                ]

        self.ag.add_actions(actions)
        self.ag.add_toggle_actions(tactions)
        self.ui = Gtk.UIManager()
        self.ui.insert_action_group(self.ag, 0)
        self.ui.add_ui_from_string(ui_string)
        self.add_accel_group(self.ui.get_accel_group())

    def __reset_title(self, *args):
        self.set_title('BRss Reader')

    def __layout_ui(self):
        self.log.debug("{0}: Laying out User Interface".format(self))
        self.__create_menu()
        opane = Gtk.VPaned()
        opane.pack1(self.ilist)
        opane.pack2(self.view)
        pane = Gtk.HPaned()
        pane.pack1(self.tree)
        pane.pack2(opane)
        al = Gtk.Alignment.new(0.5,0.5,1,1)
        al.set_padding(3,3,3,3)
        al.add(pane)
        box = Gtk.VBox(spacing=3)
        box.pack_start(self.ui.get_widget('/Menubar'), False, True, 0)
        box.pack_start(self.ui.get_widget('/Toolbar'), False, True, 0)
        widget = self.ui.get_widget("/Toolbar/Stop")
        widget.set_sensitive(False)
        box.pack_start(al, True, True, 0)
        box.pack_start(self.status, False, False, 0)
        self.add(box)
        self.set_property("height-request", 700)
        self.set_property("width-request", 1024)
        self.is_fullscreen = False
        self.__reset_title()
        self.set_icon_from_file(make_path('icons','brss.svg'))
        #~ self.set_default_icon(get_pixbuf())
        self.alert = Alerts(self)
        self.show_all()
        

    def __connect_signals(self):    # signals
        self.log.debug("{0}: Connecting all signals".format(self)))
        self.connect("destroy", self.quit)
        self.connect('loaded', self.__populate_menu)
        self.connect('next-article', self.ilist.next_item)
        self.connect('previous-article', self.ilist.previous_item)
        #~ self.connect('next-feed', self.tree.next_item)#TODO: implement
        #~ self.connect('previous-feed', self.tree.previous_item)#TODO: implement
        self.connect('search-toggled', self.ilist.toggle_search)
        self.connect_after('no-engine', self.__no_engine)
        self.tree.connect('item-selected', self.__load_articles)
        self.tree.connect_after('item-selected', self.__feed_selected)
        self.tree.connect('dcall-request', self.__handle_dcall)
        self.ilist.connect('item-selected', self.__load_article)
        self.ilist.connect('item-selected', self.__update_title)
        self.ilist.connect('no-data', self.view.clear)
        self.ilist.connect('no-data', self.__reset_title)
        self.ilist.connect('star-toggled', self.__toggle_starred)
        self.ilist.connect('read-toggled', self.__toggle_read)
        self.ilist.connect_after('star-toggled', self.tree.update_starred)
        self.ilist.connect_after('read-toggled', self.tree.update_unread)
        self.ilist.connect('dcall-request', self.__handle_dcall)
        self.ilist.connect('search-requested', self.__search_articles)
        self.ilist.connect('search-requested', self.tree.deselect)
        self.view.connect('article-loaded', self.ilist.mark_read)
        self.view.connect('link-clicked', self.__to_browser)
        self.view.connect('link-hovered-in', self.__status_info)
        self.view.connect('link-hovered-out', self.__status_info)
        self.engine.connect_to_signal('notice', self.status.message)
        self.engine.connect_to_signal('added', self.tree.insert_row)
        self.engine.connect_to_signal('updated', self.tree.update_row)
        # might want to highlight these a bit more
        self.engine.connect_to_signal('warning', self.status.warning)
    
    
    def __import_feeds(self, *args):
        dialog = Gtk.FileChooserDialog("Open...",
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
            self.log.debug("{0}: Trying to import from OPML file {1}".format(self, filename))
            self.status.message("wait", "Importing Feeds")
            self.import_opml(filename, 
                reply_handler=self.__to_log,
                error_handler=self.__to_log)

    def __export_feeds(self, *args):        
        dialog = Gtk.FileChooserDialog("Save...",
                                    self,
                                    Gtk.FileChooserAction.SAVE,
                                    (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                                      Gtk.STOCK_OPEN, Gtk.ResponseType.OK))

        dialog.set_default_response(Gtk.ResponseType.OK)
        dialog.set_do_overwrite_confirmation(True)
        dialog.set_current_name("brss.opml")
        filter = Gtk.FileFilter()
        filter.set_name("opml/xml")
        filter.add_pattern("*.opml")
        filter.add_pattern("*.xml")
        dialog.add_filter(filter)

        response = dialog.run()
        filename = os.path.abspath(dialog.get_filename())
        dialog.destroy()
        
        if response == Gtk.ResponseType.OK:
            self.log.debug("{0}: Trying to export to OPML file {1}".format(self, filename))
            self.export_opml(filename, 
                reply_handler=self.__to_log,
                error_handler=self.__to_log)
        
    def __populate_menu(self, *args):
        self.log.debug("{0}: Populating menu".format(self))
        self.get_menu_items(
            reply_handler=self.tree.fill_menu,
            error_handler=self.__to_log)
        self.count_special(
            reply_handler=self.tree.make_special_folders,
            error_handler=self.__to_log)
        
    def __toggle_starred(self, ilist, item):
        self.toggle_starred(item,
                reply_handler=self.__to_log,
                error_handler=self.__to_log)
    def __toggle_read(self, ilist, item):
        self.toggle_read(item,
                reply_handler=self.__to_log,
                error_handler=self.__to_log)
    def __load_articles(self, tree, item):
        self.log.debug("{0}: Loading articles for feed {1}".format(self, item['name'].encode('utf_8')))
        self.get_articles_for(item, 
                reply_handler=self.ilist.load_list,
                error_handler=self.__to_log)
    
    def __add_category(self, *args):
        args = [
        {'type':'str','name':'name', 'header':'Name' },
            ]
        d = Dialog(self, 'Add a category', args)
        r = d.run()
        item = d.response
        item['type'] = 'category'
        d.destroy()
        if r == Gtk.ResponseType.OK:
            self.__create(item)
    def __add_feed(self, *args):
        data = [
        {'type':'str','name':'url', 'header':'Link' },
            ]
        d = Dialog(self, 'Add a feed', data)
        r = d.run()
        item = d.response
        item['type'] = 'feed'
        d.destroy()
        if r == Gtk.ResponseType.OK:
            self.__create(item)
    
    def __edit_prefs(self, *args):
        confs = self.get_configs()
        kmap = {'hide-read':'bool', 'interval':'int', 'max':'int'}
        hmap = {
            'hide-read':'Hide Read Items', 
            'interval':'Update interval (in minutes)', 
            'max':'Maximum number of articles to keep'}
        data = []
        for k,v in confs.iteritems():
            data.append({
                'type':kmap.get(k),
                'name':k, 
                'header':hmap.get(k), 
                'value':v })
        d = Dialog(self, 'Edit preferences', data)
        r = d.run()
        item = d.response
        d.destroy()
        if r == Gtk.ResponseType.OK:
            self.log.debug("New configurations: {0}".format(item))
            self.set_configs(item,
                reply_handler=self.__to_log,
                error_handler=self.__to_log)
    def __about(self, *args):
        """Shows the about message dialog"""
        from brss import __version__, __maintainers__
        LICENSE = """   
            This program is free software: you can redistribute it and/or modify
            it under the terms of the GNU General Public License as published by
            the Free Software Foundation, either version 3 of the License, or
            (at your option) any later version.

            This program is distributed in the hope that it will be useful,
            but WITHOUT ANY WARRANTY; without even the implied warranty of
            MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
            GNU General Public License for more details.

            You should have received a copy of the GNU General Public License
            along with this program.  If not, see <http://www.gnu.org/licenses/>.
            """
        about = Gtk.AboutDialog()
        about.set_transient_for(self)
        about.set_program_name("BRss")
        about.set_version(__version__)
        about.set_authors(__maintainers__)
        about.set_artists(__maintainers__)
        about.set_copyright("(c) 2011 ITGears")
        about.set_license(LICENSE)
        about.set_comments("BRss is an offline DBus-based RSS reader")
        about.set_logo(make_pixbuf('brss'))
        about.run()
        about.destroy()

    def __create(self, item):
        self.log.debug("About to create item: {0}".format(item))
        self.create(item,
            reply_handler=self.__to_log,
            error_handler=self.__to_log)
    def __edit_item(self, *args):
        item = self.tree.current_item
        if item['type'] == 'category':
            args = [{'type':'str','name':'name', 'header':'Name', 'value':item['name'] },]
            d = Dialog(self, 'Edit this category', args)
        elif item['type'] == 'feed':
            args = [{'type':'str','name':'url', 'header':'link', 'value':item['url'] },]
            d = Dialog(self, 'Edit this feed', args)
        r = d.run()
        o = d.response
        for k,v in o.iteritems():
            item[k] = v
        d.destroy()
        if r == Gtk.ResponseType.OK:
            self.__edit(item)
        
    def __edit(self, item):
        self.log.debug("About to edit item: {0}".format(item))
        self.edit(item,
            reply_handler=self.__to_log,
            error_handler=self.__to_log)
    def __update(self, item):
        self.log.debug("About to update item: {0}".format(item))
        self.update(item,
            reply_handler=self.__to_log,
            error_handler=self.__to_log)
    def __update_all(self, *args):
        self.__update('all')
    def __update_feed(self, item):
        self.__update(self.tree.current_item)
    def __delete_item(self, *args):
        self.__delete(self.tree.current_item)
    def __delete(self, item):
        self.log.debug("About to delete item: {0}".format(item))
        self.alert.question("Are you sure you want to delete this {0} ?".format(item['type']),
            "All included feeds and articles will be deleted."
            )
        if self.alert.checksum:
            self.log.debug("Deletion confirm")
            self.delete(item,
                reply_handler=self.__populate_menu,
                error_handler=self.__to_log)
    def __load_article(self, ilist, item):
        self.get_article(item, 
                reply_handler=self.view.show_article,
                error_handler=self.__to_log)
    def __handle_new(self, item):
        self.log.debug("New item: {0}".format(item))
        if item['type'] in ['feed', 'category']:
            self.tree.insert_row(item)
    def __handle_dcall(self, caller, name, item):
        if name in ['Update', 'Update all']:
            self.log.debug("Running all feeds update")
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
            self.__delete(item)
        elif name in ['Edit',]:
            self.__edit_item(item)
    def __search_articles(self, caller, string):
        self.log.debug("Searching articles with: {0}".format(string.encode('utf-8')))
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
    def __status_info(self, caller, message=None):
        if message:
            self.status.message('info', message)
        else:
            self.status.clear()
    def __to_log(self, *args):
        for a in args:
            self.log.warning(a)
            if type(a) == dbus.exceptions.DBusException:
                self.emit('no-engine')
    
    def __to_browser(self, caller, link):
        self.log.debug("Trying to open link '{0}' in browser".format(item))
        orig_link = self.view.link_button.get_uri()
        self.view.link_button.set_uri(link)
        self.view.link_button.activate()
        self.view.link_button.set_uri(orig_link)
        
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
    def __reconnect(self, *args):
        self.__get_engine()
        self.__connect_signals()
    def __no_engine(self, *args):
        self.log.warning("Lost connection with engine!")
        self.status.message('error', "Cannot connect to the Feed Engine")
        self.ag.get_action('Reconnect').set_visible(True)
    def __feed_selected(self, caller, item):
        if item['type'] in ['feed', 'category']:
            self.status.message('info', "[{0}] {1}".format(
                item['type'].capitalize(),
                item['name'].encode('utf-8')))
        else:
            self.status.clear()
    def quit(self, *args):
        Gtk.main_quit()
    
    def start(self):
        Gtk.main()

    #~ def do_loaded(self, *args):
        #~ print "Reader loaded"


class ReaderService(dbus.service.Object):
    def __init__(self, appclass, base_path):
        self.app = appclass(base_path)
        bus_name = dbus.service.BusName('com.itgears.BRss.Reader', bus = dbus.SessionBus())
        dbus.service.Object.__init__(self, bus_name, '/com/itgears/BRss/Reader')

    @dbus.service.method(dbus_interface='com.itgears.BRss.Reader')
    def show_window(self):
        self.app.present()

def run_reader(appclass, base_path):
    if dbus.SessionBus().request_name('com.itgears.BRss.Reader') != dbus.bus.REQUEST_NAME_REPLY_PRIMARY_OWNER:
        print "brss-reader already running"
        method = dbus.SessionBus().get_object('com.itgears.BRss.Reader', '/com/itgears/BRss/Reader').get_dbus_method("show_window")
        method()
    else:
        print "running brss-reader"
        service = ReaderService(appclass, base_path)
        service.app.start()
