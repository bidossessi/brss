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
from gi.repository import Gio
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
from articlelist    import ArticleList
from tree           import Tree
from view           import View
from status         import Status
from alerts         import Alerts
from dialogs        import Dialog
from functions      import make_path, make_pixbuf
from logger         import Logger

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
        return "Reader"
    def __init__(self, base_path="."):
        Gtk.Window.__init__(self)
        self.__gobject_init__()
        GObject.type_register(Reader)
        self.log = Logger(base_path, "brss-reader.log", "BRss-Reader")

        # ui elements
        self.tree = Tree(base_path, self.log)
        self.ilist = ArticleList(self.log)
        self.ilist.set_property("height-request", 250)
        self.view = View(self.log)
        self.status = Status()
        # layout
        self.__layout_ui()
        #signals
        self.__connect_signals()
        self.__get_engine()
        self.__confs = self.get_configs()
        self.log.enable_debug(self.__confs.get('debug'))
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
        self.stop_update         = self.engine.get_dbus_method('stop_update', 'com.itgears.BRss.Engine')
        self.count_special       = self.engine.get_dbus_method('count_special', 'com.itgears.BRss.Engine')
        self.get_configs         = self.engine.get_dbus_method('get_configs', 'com.itgears.BRss.Engine')
        self.set_configs         = self.engine.get_dbus_method('set_configs', 'com.itgears.BRss.Engine')
        self.import_opml         = self.engine.get_dbus_method('import_opml', 'com.itgears.BRss.Engine')
        self.export_opml         = self.engine.get_dbus_method('export_opml', 'com.itgears.BRss.Engine')
        self.log.warning("Hiding reconnect icon!")
        self.rag.set_visible(False)
        self.ag.set_visible(True)
        self.__connect_engine_signals()
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
                     <separator/>
                     <menuitem action='Star'/>
                     <separator/>
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
                    <toolitem name='Reconnect' action='Reconnect'/>
                    <separator />
                    <toolitem name='Update all' action='Update all'/>
                    <toolitem name='Stop' action='StopUpdate'/>
                    <separator name='sep2'/>
                    <toolitem name='PreviousFeed' action='PreviousFeed'/>
                    <toolitem name='PreviousArticle' action='PreviousArticle'/>
                    <toolitem name='Star' action='Star'/>
                    <toolitem name='NextArticle' action='NextArticle'/>
                    <toolitem name='NextFeed' action='NextFeed'/>
                    <separator name='sep3'/>
                    <toolitem name='FullScreen' action='FullScreen'/>
                    <toolitem name='Find' action='Find'/>
                    <toolitem name='Preferences' action='Preferences'/>
                   </toolbar>
                  </ui>"""

        # Generate a stock image from a file (http://faq.pyGtk.org/index.py?req=show&file=faq08.012.htp)



        self.mag = Gtk.ActionGroup('MenuActions')
        mactions = [
                ('FeedMenu', None, '_Feeds'),
                ('EditMenu', None, 'E_dit'),
                ('NetworkMenu', None, '_Network'),
                ('ViewMenu', None, '_View'),
                ('HelpMenu', None, '_Help'),
                ('About', "gtk-about", '_About', None, 'About', self.__about),
        ]
        self.mag.add_actions(mactions)
        self.ag = Gtk.ActionGroup('WindowActions')
        actions = [
                ('New feed', 'feed', '_New feed', '<control><alt>n', 'Add a feed', self.__add_feed),
                ('New category', "gtk-directory", 'New _category', '<control><alt>c', 'Add a category', self.__add_category),
                ('Delete', "gtk-clear", 'Delete', 'Delete', 'Delets a feed or a category', self.__delete_item),
                ('Import feeds', "gtk-redo", 'Import feeds', None, 'Import a feedlist', self.__import_feeds),
                ('Export feeds', "gtk-undo", 'Export feeds', None, 'Export a feedlist', self.__export_feeds),
                ('Quit', "gtk-quit", '_Quit', '<control>Q', 'Quits', self.quit),
                ('Edit', "gtk-edit", '_Edit', '<control>E', 'Edit the selected element'),
                ('Star', "gtk-about", '_Star', 'x', 'Star the current article', self.__star),
                ('Preferences', "gtk-preferences", '_Preferences', '<control>P', 'Configure the engine', self.__edit_prefs),
                ('Update', None, '_Update', '<control>U', 'Update the selected feed', self.__update_feed),
                ('Update all', "gtk-refresh", 'Update all', '<control>R', 'Update all feeds', self.__update_all),
                ('PreviousArticle', "gtk-go-back", 'Previous Article', 'b', 'Go to the previous article', self.__previous_article),
                ('NextArticle', "gtk-go-forward", 'Next Article', 'n', 'Go to the next article', self.__next_article),
                ('PreviousFeed', "gtk-goto-first", 'Previous Feed', '<shift>b', 'Go to the previous news feed', self.__previous_feed),
                ('NextFeed', "gtk-goto-last", 'Next Feed', '<shift>n', 'Go to the next news feed', self.__next_feed),
                ('StopUpdate', "gtk-stop", 'Stop', None, 'StopUpdate', self.__stop_updates),
            ]
        tactions = [
                ('Find', "gtk-find", 'Find', '<control>F', 'Search for a term in the articles', self.__toggle_search),
                ('FullScreen', "gtk-fullscreen", 'Fullscreen', 'F11', '(De)Activate fullscreen', self.__toggle_fullscreen),
            ]
        self.ag.add_actions(actions)
        self.ag.add_toggle_actions(tactions)
        # break reconnect into its own group
        self.rag = Gtk.ActionGroup("Rec")
        ractions = [
                ('Reconnect', "gtk-disconnect", '_Reconnect', None, 'Try and reconnect to the feed engine', self.__reconnect),
            ]
        self.rag.add_actions(ractions)
        self.ui = Gtk.UIManager()
        self.ui.insert_action_group(self.mag, 0)
        self.ui.insert_action_group(self.ag, 0)
        self.ui.insert_action_group(self.rag, 1)
        self.ui.add_ui_from_string(ui_string)
        self.add_accel_group(self.ui.get_accel_group())

    def __reset_title(self, *args):
        self.set_title('BRss Reader')
    
    def __stop_updates(self, *args):
        self.stop_update(
            reply_handler=self.__to_log,
            error_handler=self.__to_log)
        self.ag.get_action('StopUpdate').set_sensitive(False)
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
        widget = self.ag.get_action('StopUpdate')
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
        self.connect("destroy", self.quit)
        self.show_all()
        

    def __connect_signals(self):    # signals
        self.log.debug("{0}: Connecting all signals".format(self))
        self.connect('next-article', self.ilist.next_item)
        self.connect('previous-article', self.ilist.previous_item)
        self.connect('next-feed', self.tree.next_item)
        self.connect('previous-feed', self.tree.previous_item)#TODO: implement
        self.connect('search-toggled', self.ilist.toggle_search)
        self.connect_after('no-engine', self.__no_engine)
        self.connect_after('no-engine', self.view.no_engine)
        self.tree.connect('item-selected', self.__load_articles)
        #~ self.tree.connect_after('item-selected', self.__feed_selected)
        self.tree.connect('dcall-request', self.__handle_dcall)
        self.ilist.connect('item-selected', self.__load_article)
        self.ilist.connect('item-selected', self.__update_title)
        self.ilist.connect('no-data', self.view.clear)
        self.ilist.connect('no-data', self.__reset_title)
        self.ilist.connect('star-toggled', self.__toggle_starred)
        self.ilist.connect('read-toggled', self.__toggle_read)
        self.ilist.connect_after('row-updated', self.tree.update_starred)
        self.ilist.connect_after('row-updated', self.tree.update_unread)
        self.ilist.connect('dcall-request', self.__handle_dcall)
        self.ilist.connect('search-requested', self.__search_articles)
        self.ilist.connect('search-requested', self.tree.deselect)
        self.view.connect('article-loaded', self.ilist.mark_read)
        self.view.connect('link-clicked', self.__to_browser)
        self.view.connect('link-hovered-in', self.__status_info)
        self.view.connect('link-hovered-out', self.__status_info)

    def __connect_engine_signals(self):
        self.engine.connect_to_signal('notice', self.status.message)
        self.engine.connect_to_signal('added', self.__handle_added)
        self.engine.connect_to_signal('updated', self.__handle_updated)
        self.engine.connect_to_signal('updating', self.__update_started)
        self.engine.connect_to_signal('complete', self.__update_done)
        self.engine.connect_to_signal('complete', self.tree.select_current)
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
        self.log.debug("{0}: Loading articles for feed {1}".format(self, item['name']))
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
    def __get_confs(self):
        self.get_configs(
            reply_handler=self.__set_confs,
            error_handler=self.__to_log)
    def __set_confs(self, confs):
        self.__confs = confs
        self.log.enable_debug(confs.get('debug'))

    def __edit_prefs(self, *args):
        self.__get_confs()
        kmap = {'hide-read':'bool', 'interval':'int', 'max':'int', 
            'notify':'bool', 'otf':'bool', 'debug':'bool', 
            'auto-update':'bool'}
        hmap = {
            'hide-read':'Hide Read Items', 
            'interval':'Update interval (in minutes)', 
            'max':'Maximum number of articles to keep (excluding starred)',
            'auto-update':'Allow the engine to download new articles automatically.',
            'otf':'Start downloading articles for new feeds on-the-fly',
            'notify':'Show notification on updates',
            'debug':'Enable detailed logs',
            }
        data = []
        for k,v in self.__confs.iteritems():
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
        self.__get_confs()
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
        self.log.debug("{0} Requesting update for: {1}".format(self, item))
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
    def __handle_added(self, item):
        self.log.debug("{0}: Added item: {1}".format(self, item['id']))
        if item['type'] in ['feed', 'category']:
            return self.tree.insert_row(item)
        if item['type'] == 'article':
            return self.ilist.insert_row(item)
    def __handle_updated(self, item):
        #~ self.log.debug("{0}: Updated item: {1}".format(self, item['id']))
        if item['type'] in ['feed', 'category']:
            return self.tree.update_row(item)
        if item['type'] == 'article':
            self.view.star_this(item)
            return self.ilist.update_row(item)
    def __handle_dcall(self, caller, name, item):
        if name in ['Update', 'Update all']:
            self.log.debug("updating {0}".format(item))
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
    def __toggle_in_update(self, b):
        gmap = {True:False, False:True}
        a = self.ag.get_action('StopUpdate')
        a.set_sensitive(b)
        a = self.ag.get_action('Update all')
        a.set_sensitive(gmap.get(b))
    def __toggle_search(self, *args):
        self.emit('search-toggled')
    def __star(self, *args):
        self.ilist.mark_starred()
    def __update_started(self, *args):
        self.log.debug("Toggling update status to True")
        self.__toggle_in_update(True)
    def __update_done(self, *args):
        self.log.debug("Toggling update status to False")
        self.__toggle_in_update(False)
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
        self.log.debug("Trying to open link '{0}' in browser".format(link))
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
        self.log.warning("Trying to reconnect to engine!")
        self.__get_engine()
        self.emit('loaded')
    def __no_engine(self, *args):
        self.log.warning("Lost connection with engine!")
        self.status.message('critical', "Cannot connect to the Feed Engine")
        self.log.debug("Showing reconnect icon!")
        self.rag.set_visible(True)
        self.ag.set_visible(False)
        self.__update_done()
    #~ def __feed_selected(self, caller, item):
        #~ self.status.message('info', "{0}".format(
                #~ item['name'].encode('utf-8')))
    def quit(self, *args):
        self.destroy()
        Gtk.main_quit()
    def start(self):
        Gtk.main()

    def do_loaded(self, *args):
        self.log.debug("Starting BRss Reader")
        self.__populate_menu()
        self.status.message('ok', 'Connected to engine')


class ReaderService(dbus.service.Object):
    def __init__(self, base_path):
        self.app = Reader(base_path)
        bus_name = dbus.service.BusName('com.itgears.BRss.Reader', bus = dbus.SessionBus())
        dbus.service.Object.__init__(self, bus_name, '/com/itgears/BRss/Reader')

    @dbus.service.method(dbus_interface='com.itgears.BRss.Reader')
    def show_window(self):
        self.app.present()

def run_reader(base_path):
    if dbus.SessionBus().request_name('com.itgears.BRss.Reader') != dbus.bus.REQUEST_NAME_REPLY_PRIMARY_OWNER:
        print "brss-reader already running"
        method = dbus.SessionBus().get_object('com.itgears.BRss.Reader', '/com/itgears/BRss/Reader').get_dbus_method("show_window")
        method()
    else:
        print "running brss-reader"
        service = ReaderService(base_path)
        service.app.start()

#~ class ReaderApplication(Gtk.Application):
    #~ """GApplication implementation"""
    #~ def __init__(self, base_path):
        #~ self.reader = Reader(base_path)
