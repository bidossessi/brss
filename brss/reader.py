#!/usr/bin/env python
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
#FIXME: move to Gio.DBusConnexion/DBusProxy
import dbus
import dbus.service
import dbus.mainloop.glib
dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
import i18n
_ = i18n.language.gettext
import time
# our stuff
from articlelist    import ArticleList
from tree           import Tree
from view           import View
from status         import Status
from alerts         import Alerts
from dialogs        import Dialog
from logger         import Logger
from common      import make_path, make_pixbuf, init_dirs
from common      import BASE_KEY, BASE_PATH
from common      import ENGINE_DBUS_KEY, ENGINE_DBUS_PATH
from common      import READER_DBUS_KEY, READER_DBUS_PATH
from common      import __version__, __maintainers__

class Reader (Gtk.Window, GObject.GObject):
    """

    """
    __gsignals__ = {
        "loaded" : (
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
    def __init__(self):
        Gtk.Window.__init__(self)
        GObject.GObject.__init__(self)
        GObject.type_register(Reader)
        self.log = Logger("reader.log", "BRss-Reader")
        self.settings = Gio.Settings.new(BASE_KEY)
        self.settings.connect("changed::show-status", self.__toggle_status)

        # ui elements
        self.tree = Tree(self.log)
        self.ilist = ArticleList(self.log)
        self.ilist.set_property("height-request", 250)
        self.view = View(self.log)
        self.status = Status()
        # layout
        self.__layout_ui()
        #signals
        self.__connect_signals()
        self.__get_engine()
        # ready to go
        self.emit('loaded')

    def __check_engine(self):
        bus = dbus.SessionBus()
        try:
            engine = bus.get_object(ENGINE_DBUS_KEY, ENGINE_DBUS_PATH)
        except:
            return False
        return engine

    def __get_engine(self):
        self.engine = self.__check_engine()
        if not self.engine:
            self.log.critical("{0}: Couldn't get a DBus connection; quitting.".format(self))
            self.alert.error(_("Could not connect to Engine"),
                _("BRss will now quit.\nPlease make sure that the engine is running and restart the application"))
            self.quit()
        self.create              = self.engine.get_dbus_method('create', ENGINE_DBUS_KEY)
        self.edit                = self.engine.get_dbus_method('edit', ENGINE_DBUS_KEY)
        self.update              = self.engine.get_dbus_method('update', ENGINE_DBUS_KEY)
        self.delete              = self.engine.get_dbus_method('delete', ENGINE_DBUS_KEY)
        self.get_menu_items      = self.engine.get_dbus_method('get_menu_items', ENGINE_DBUS_KEY)
        self.get_articles_for    = self.engine.get_dbus_method('get_articles_for', ENGINE_DBUS_KEY)
        self.search_for          = self.engine.get_dbus_method('search_for', ENGINE_DBUS_KEY)
        self.get_article         = self.engine.get_dbus_method('get_article', ENGINE_DBUS_KEY)
        self.toggle_starred      = self.engine.get_dbus_method('toggle_starred', ENGINE_DBUS_KEY)
        self.toggle_read         = self.engine.get_dbus_method('toggle_read', ENGINE_DBUS_KEY)
        self.stop_update         = self.engine.get_dbus_method('stop_update', ENGINE_DBUS_KEY)
        self.count_special       = self.engine.get_dbus_method('count_special', ENGINE_DBUS_KEY)
        self.get_configs         = self.engine.get_dbus_method('get_configs', ENGINE_DBUS_KEY)
        self.set_configs         = self.engine.get_dbus_method('set_configs', ENGINE_DBUS_KEY)
        self.import_opml         = self.engine.get_dbus_method('import_opml', ENGINE_DBUS_KEY)
        self.export_opml         = self.engine.get_dbus_method('export_opml', ENGINE_DBUS_KEY)
        self.rag.set_visible(False)
        self.ag.set_visible(True)
        self.__connect_engine_signals()
        self.log.debug(_("{0}: Connected to feed engine {1}".format(self, self.engine)))
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
                     <menuitem action='Read'/>
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

        self.mag = Gtk.ActionGroup('MenuActions')
        mactions = [
                ('FeedMenu', None, _('_Feeds')),
                ('EditMenu', None, _('E_dit')),
                ('NetworkMenu', None, _('_Network')),
                ('ViewMenu', None, _('_View')),
                ('HelpMenu', None, _('_Help')),
                ('About', "gtk-about", _('_About'), None, _('About'), self.__about),
        ]
        self.mag.add_actions(mactions)
        self.ag = Gtk.ActionGroup('WindowActions')
        actions = [
                ('New feed', 'feed', _('_New feed'), '<control><alt>n', _('Add a feed'), self.__add_feed),
                ('New category', "gtk-directory", _('New _category'), '<control><alt>c', _('Add a category'), self.__add_category),
                ('Delete', "gtk-clear", _('Delete'), 'Delete', _('Delete a feed or a category'), self.__delete_item),
                ('Import feeds', "gtk-redo", _('Import feeds'), None, _('Import a feedlist'), self.__import_feeds),
                ('Export feeds', "gtk-undo", _('Export feeds'), None, _('Export a feedlist'), self.__export_feeds),
                ('Quit', "gtk-quit", _('_Quit'), '<control>Q', _('Quits'), self.quit),
                ('Edit', "gtk-edit", _('_Edit'), '<control>E', _('Edit the selected element')),
                ('Star', "gtk-about", _('_Star'), 'x', _('Star the current article'), self.__star),
                ('Read', "gtk-ok", _('_Read'), 'r', _('Toggle the current article read status'), self.__read),
                ('Preferences', "gtk-preferences", _('_Preferences'), '<control>P', _('Configure the engine'), self.__edit_prefs),
                ('Update', None, _('_Update'), '<control>U', _('Update the selected feed'), self.__update_feed),
                ('Update all', "gtk-refresh", _('Update all'), '<control>R', _('Update all feeds'), self.__update_all),
                ('PreviousArticle', "gtk-go-back", _('Previous Article'), 'b', _('Go to the previous article'), self.__previous_article),
                ('NextArticle', "gtk-go-forward", _('Next Article'), 'n', _('Go to the next article'), self.__next_article),
                ('PreviousFeed', "gtk-goto-first", _('Previous Feed'), '<shift>b', _('Go to the previous news feed'), self.__previous_feed),
                ('NextFeed', "gtk-goto-last", _('Next Feed'), '<shift>n', _('Go to the next news feed'), self.__next_feed),
                ('StopUpdate', "gtk-stop", _('Stop'), None, _('Stop the current update'), self.__stop_updates),
            ]
        tactions = [
                ('Find', "gtk-find", _('Find'), '<control>F', _('Search for a term in the articles'), self.__toggle_search),
                ('FullScreen', "gtk-fullscreen", _('Fullscreen'), 'F11', _('(De)Activate fullscreen'), self.__toggle_fullscreen),
            ]
        self.ag.add_actions(actions)
        self.ag.add_toggle_actions(tactions)
        # break reconnect into its own group
        self.rag = Gtk.ActionGroup("Rec")
        ractions = [
                ('Reconnect', "gtk-disconnect", _('_Reconnect'), None, _('Try and reconnect to the feed engine'), self.__reconnect),
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
        #setting GTK3 style
        ctx= self.ui.get_widget('/Toolbar').get_style_context()
        print "UI Context: ",ctx
        ctx.add_class(Gtk.STYLE_CLASS_PRIMARY_TOOLBAR)
        widget = self.ag.get_action('StopUpdate')
        widget.set_sensitive(False)
        box.pack_start(al, True, True, 0)
        box.pack_start(self.status, False, False, 0)
        self.add(box)
        self.set_property("height-request", 700)
        self.set_property("width-request", 1024)
        self.is_fullscreen = False
        self.__reset_title()
        self.set_icon_from_file(make_path('icons/hicolor','brss.svg'))
        self.alert = Alerts(self)
        self.connect("destroy", self.quit)
        self.show_all()
        if not self.settings.get_boolean('show-status'):
            self.status.hide()


    def __connect_signals(self):    # signals
        self.log.debug("{0}: Connecting all signals".format(self))
        self.connect('next-article', self.ilist.next_item)
        self.connect('previous-article', self.ilist.previous_item)
        self.connect('next-feed', self.tree.next_item)
        self.connect('previous-feed', self.tree.previous_item)#TODO: implement
        self.connect_after('no-engine', self.__no_engine)
        self.connect_after('no-engine', self.view.no_engine)
        self.tree.connect('item-selected', self.__load_articles)
        self.tree.connect('dcall-request', self.__handle_dcall)
        self.ilist.connect('item-selected', self.__load_article)
        self.ilist.connect('item-selected', self.__update_title)
        self.ilist.connect('no-data', self.view.clear)
        self.ilist.connect('no-data', self.__reset_title)
        self.ilist.connect('star-toggled', self.__toggle_starred)
        self.ilist.connect('read-toggled', self.__toggle_read)
        self.ilist.connect('filter-ready', self.__connect_accels)
        self.ilist.connect('list_loaded', self.__hide_search,)
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
        dialog = Gtk.FileChooserDialog(_("Open..."),
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
        filter.set_name(_("All files"))
        filter.add_pattern("*")
        dialog.add_filter(filter)

        response = dialog.run()
        filename = dialog.get_filename()
        dialog.destroy()

        if response == Gtk.ResponseType.OK:
            self.log.debug("{0}: Trying to import from OPML file {1}".format(self, filename))
            self.import_opml(filename,
                reply_handler=self.__to_log,
                error_handler=self.__to_log)

    def __export_feeds(self, *args):
        dialog = Gtk.FileChooserDialog(_("Save..."),
                                    self,
                                    Gtk.FileChooserAction.SAVE,
                                    (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                                      Gtk.STOCK_SAVE, Gtk.ResponseType.OK))

        dialog.set_default_response(Gtk.ResponseType.OK)
        dialog.set_do_overwrite_confirmation(True)
        dialog.set_current_name("brss.opml")
        filter = Gtk.FileFilter()
        filter.set_name("opml/xml")
        filter.add_pattern("*.opml")
        filter.add_pattern("*.xml")
        dialog.add_filter(filter)

        response = dialog.run()
        filename = dialog.get_filename()
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
        {'type':'str','name':'name', 'header':_('Name') },
            ]
        d = Dialog(self, _('Add a category'), args)
        r = d.run()
        item = d.response
        item['type'] = 'category'
        d.destroy()
        if r == Gtk.ResponseType.OK:
            self.__create(item)
    def __add_feed(self, *args):
        data = [
        {'type':'str','name':'url', 'header':_('Link') },
            ]
        d = Dialog(self, _('Add a feed'), data)
        r = d.run()
        item = d.response
        item['type'] = 'feed'
        d.destroy()
        if r == Gtk.ResponseType.OK:
            self.__create(item)

    def __edit_prefs(self, *args):
        kmap = {
            'hide-read':'bool',
            'update-interval':'int',
            'max-articles':'int',
            'use-notify':'bool',
            'on-the-fly':'bool',
            'enable-debug':'bool',
            'auto-update':'bool',
            'live-search':'bool',
            'auto-hide-search':'bool',
            'show-status':'bool',
            }
        hmap = {
            'hide-read':_('Hide Read Items'),
            'update-interval':_('Update interval (in minutes)'),
            'max-articles':_('Maximum number of articles to keep (excluding starred)'),
            'auto-update':_('Allow the engine to download new articles automatically.'),
            'on-the-fly':_('Start downloading articles for new feeds on-the-fly'),
            'use-notify':_('Show notification on updates'),
            'enable-debug':_('Enable detailed logs'),
            'live-search':_('Return search results as you type'),
            'auto-hide-search':_('Hide Search form on results'),
            'show-status':_('Show the bottom status bar'),
            }
        data = []
        for k,v in kmap.iteritems():
            data.append({
                'type':v,
                'name':k,
                'header':hmap.get(k),#FIXME: can this be gotten from gsettings?
                })
        d = Dialog(self, _('Edit preferences'), data, self.settings)
        r = d.run()
        d.destroy()
    def __about(self, *args):
        """Shows the about message dialog"""
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
        about.set_comments(_("BRss is an offline DBus-based RSS reader"))
        about.set_logo(make_pixbuf('brss'))
        about.run()
        about.destroy()

    def __create(self, item):
        self.log.debug("About to create item: {0}".format(item))
        self.create(item,
            reply_handler=self.__to_log,
            error_handler=self.__to_log)
    def __edit_item(self, *args):
        item = self.tree.current_item #FIXME: not good!!
        print item
        if item['type'] == 'category':
            args = [{'type':'str','name':'name', 'header':_('Name'), 'value':item['name'] },]
            d = Dialog(self, _('Edit this category'), args)
        elif item['type'] == 'feed':
            args = [{'type':'str','name':'url', 'header':_('Link'), 'value':item['url'] },]
            d = Dialog(self, _('Edit this feed'), args)
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
        self.alert.question(_("Are you sure you want to delete this {0} ?".format(item['type'])),
            _("All included feeds and articles will be deleted.")
            )
        if self.alert.checksum:
            self.log.debug("Deletion confirmed")
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
        if name in [_('Update'), _('Update all')]:
            self.log.debug("updating {0}".format(item))
            self.update(item,
                reply_handler=self.__update_done,
                error_handler=self.__to_log)
        elif name == _('Mark all as read'):
            self.ilist.mark_all_read()

        elif name == _('Open in Browser'):
            self.__to_browser(caller, item['url'])

        elif name == _('Copy Url to Clipboard'):
            self.__to_clipboard(item['url'])

        elif name in [_('Delete'), _('Delete Feed'), _('Delete Category')]:
            self.__delete(item)
        elif name == _('Edit'):
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
        # show ilist if in fullscreen
        self.ilist.toggle_search()
        if self.ilist.search_on:
            if self.is_fullscreen:
                self.ilist.show()
        else:
            if self.is_fullscreen:
                self.ilist.hide()
            else:
                self.ilist.listview.grab_focus()
    def __hide_search(self, *args):
        if not self.settings.get_boolean('live-search'):
            if self.ilist.search_on and self.settings.get_boolean('auto-hide-search'):
                w = self.ag.get_action('Find')
                if w.get_sensitive():
                    w.activate()
    def __star(self, *args):
        self.ilist.mark_starred()
    def __read(self, *args):
        self.ilist.toggle_read()
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

    def __connect_accels (self, widget):
        widget.filterentry.connect('focus-in-event', self.__toggle_accels, False)
        widget.filterentry.connect('focus-out-event', self.__toggle_accels, True)
        widget.filterentry.grab_focus()


    def __toggle_accels(self, widget, event, b):
        n   = self.ag.get_action('NextArticle')
        nf  = self.ag.get_action('NextFeed')
        p   = self.ag.get_action('PreviousArticle')
        pf  = self.ag.get_action('PreviousFeed')
        s   = self.ag.get_action('Star')
        r   = self.ag.get_action('Read')
        if b:
            self.log.debug("Toggling accels on")
            for acc in [n, nf, p, pf, s, r]:
                acc.connect_accelerator()
        else:
            self.log.debug("Toggling accels off")
            for acc in [n, nf, p, pf, s, r]:
                acc.disconnect_accelerator()

    def __toggle_status(self, settings, key=None):
        if settings.get_boolean(key):
            self.log.debug('{0}: showing the status bar'.format(self))
            self.status.show()
        else:
            self.log.debug('{0}: hiding the status bar'.format(self))
            self.status.hide()
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
        self.status.message('critical', _("Cannot connect to the Feed Engine"))
        self.log.debug("Showing reconnect icon!")
        self.rag.set_visible(True)
        self.ag.set_visible(False)
        self.__update_done()
    #~ def __feed_selected(self, caller, item):
        #~ self.status.message('info', "{0}".format(
                #~ item['name'].encode('utf-8')))
    def quit(self, *args):
        self.destroy()
    def start(self, *args):
        self.present()

    def do_loaded(self, *args):
        self.log.debug("Starting BRss Reader")
        self.__populate_menu()
        self.status.message('ok', _('Connected to engine'))


class ReaderApplication :
    """GApplication implementation"""
    def __init__(self):
        flags = Gio.ApplicationFlags.FLAGS_NONE
        key = READER_DBUS_KEY
        self.app = Gtk.Application.new(key, flags)
        self.app.register(None)

    def activate(self, app, *args):
        self.reader.start()

    def open(self, app, files, nfiles, hint):
        print files, nfiles, hint

    def log_signals(self, *args):
        print args

    def check_engine(self):
        bus = dbus.SessionBus()
        try:
            engine = bus.get_object(ENGINE_DBUS_KEY, ENGINE_DBUS_PATH)
        except:
            return False
        return True

    def run_engine(self):
        d = make_path('applications', 'brss-engine.desktop')
        info = Gio.DesktopAppInfo.new_from_filename(d)
        info.launch((), None)

    def find_engine(self):
        i = 0
        while i < 3:
            if self.check_engine():
                return True
            i += 1
            self.run_engine()
            time.sleep(5)
        return False

    def run(self):
        has_engine = self.find_engine()
        if has_engine:
            if not self.app.get_is_remote():
                self.reader = Reader()
                self.app.add_window(self.reader)
                self.app.connect('activate', self.activate, None)
                self.app.connect('open', self.open, None)
                self.app.connect('startup', self.log_signals)
                self.app.connect('command-line', self.log_signals)
                self.app.run(None)
            else:
                print (_("Another instance is already running"))
        else:
            print (_("Could not start engine. Aborting"))

def main():
    r = ReaderApplication()
    r.run()

if __name__ == '__main__':
    main()
