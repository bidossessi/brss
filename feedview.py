#!/usr/bin/env python2
# -*- coding: utf-8 -*-
#
#       feedview.py
#       
#       Copyright 2011 Bidossessi Sodonon <b_sodonon@sysadmin.colourball.com>
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
#~ import webkit

class FeedView (Gtk.VBox, GObject.GObject):
    """
        The feedview displays the currently selected feed item.
        It redirects clicks to the user's preferred browser and
        allows a basic navigation between feed itmes
    """
    __gsignals__ = {
        "article-loaded" : (
            GObject.SignalFlags.RUN_FIRST, 
            None,
            ()),
        "link-clicked" : (
            GObject.SignalFlags.RUN_FIRST, 
            None,
            (GObject.TYPE_STRING,)),
        }

    def __init__(self):
        Gtk.VBox.__init__(self, spacing=3)
        self.__gobject_init__()
        # top navi
        tbox = Gtk.HBox(spacing=3)
        # navigation buttons
        self.link_button = Gtk.LinkButton('', label='Space holder')
        tbox.pack_start(self.link_button, True, True,0)
        # webkit view
        #~ self.feedview = webkit.WebView()
        self.feedview = Gtk.Label()
        self.feedview.set_line_wrap(True)
        self.feedview.set_ellipsize(Pango.EllipsizeMode.END)
        #~ self.feedview.set_full_content_zoom(True)
        #~ self.webview.connect("navigation-policy-decision-requested", self.navigation_requested)
        #~ self.webview.connect("hovering-over-link", self.__hover_link)

        # containers
        tal = Gtk.Alignment.new(0.5, 0.5, 1, 1)
        tal.add(tbox)
        msc = Gtk.ScrolledWindow()
        msc.set_shadow_type(Gtk.ShadowType.IN)
        msc.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        #~ msc.add(self.feedview)
        mal = Gtk.Alignment.new(0.5, 0.5, 1, 1)
        mal.add(msc)
        self.pack_start(tal, False, False,0)
        #~ self.pack_start(mal, True, True,0)
        self.pack_start(self.feedview, True, True,0)
        GObject.type_register(FeedView)

    def show_article(self, art):
        self.link_button.set_label(art['title'])
        self.link_button.set_uri(art['link'])
        self.feedview.set_text(art['content'])
        self.emit('article-loaded')
    
    def __hover_link(self, *args):
        print args

if __name__ == '__main__':
    def convert(item, tp='feed'):
        i = {
                'type': tp,
                'id': item['id'],
                'name': item['name'],
            }
        return i

    def convert2(item):
        i = {
                'id': item['id'],
                'title': item['title'],
                'url': item['link']
            }
        return i

    def callback(ilist, item, method):
        print method(item)
        
    import dbus
    import dbus.mainloop.glib
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

    bus                 = dbus.SessionBus()
    engine              = bus.get_object('org.naufrago.feedengine', '/org/naufrago/feedengine')
    get_categories      = engine.get_dbus_method('get_categories', 'org.naufrago.feedengine')
    get_feeds_for       = engine.get_dbus_method('get_feeds_for', 'org.naufrago.feedengine')
    get_articles_for    = engine.get_dbus_method('get_articles_for', 'org.naufrago.feedengine')
    get_article         = engine.get_dbus_method('get_article', 'org.naufrago.feedengine')
    exit                = engine.get_dbus_method('exit', 'org.naufrago.feedengine')

    cats = get_categories()
    for c in cats:
        feeds = get_feeds_for(c)
        #~ print feeds
        c['feeds'] = feeds        
    f = cats[0]['feeds'][1]
    exfeed = get_articles_for(convert(f, 'feed'))
    art = get_article(convert2(exfeed[0]))
    window = Gtk.Window()
    window.connect("destroy", Gtk.main_quit)
    window.set_default_size(1200, 400)
    view = FeedView()
    window.add(view)
    window.show_all()
    view.show_article(art)
    Gtk.main()

