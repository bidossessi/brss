#!/usr/bin/env python2
# -*- coding: utf-8 -*-
#
#       view.py
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
from gi.repository import WebKit
from brss.common import make_date
    
class View (Gtk.VBox, GObject.GObject):
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
        
        "link-hovered-in" : (
            GObject.SignalFlags.RUN_FIRST, 
            None,
            (GObject.TYPE_STRING,)),
        "link-hovered-out" : (
            GObject.SignalFlags.RUN_FIRST, 
            None,
            ()),
        }

    def __init__(self, logger):
        self.log = logger
        Gtk.VBox.__init__(self, spacing=3)
        self.__gobject_init__()
        # top navi
        self.set_no_show_all(True)
        tbox = Gtk.HBox(spacing=3)
        # navigation buttons
        self.link_button = Gtk.LinkButton('', label='Article Title')
        self.link_button.set_relief(Gtk.ReliefStyle.NONE)
        tbox.pack_start(self.link_button, True, True,0)
        self.file_img = Gtk.Image().new_from_stock('gtk-file', Gtk.IconSize.BUTTON)
        tbox.pack_start(self.file_img, False, False,0)
        self.star_img = Gtk.Image().new_from_stock('gtk-about', Gtk.IconSize.BUTTON)
        tbox.pack_start(self.star_img, False, False,0)
        self.feed_img = Gtk.Image().new_from_stock('missing', Gtk.IconSize.BUTTON)
        tbox.pack_start(self.feed_img, False, False,0)
        # webkit view
        self.feedview = WebKit.WebView()
        self.feedview.set_full_content_zoom(True)
        self.feedview.connect("navigation-policy-decision-requested", self.__override_clicks)
        self.feedview.connect("hovering-over-link", self.__hover_webview)
        self.link_button.connect("enter-notify-event", self.__hover_link, "in")
        self.link_button.connect("leave-notify-event", self.__hover_link)
        # containers
        tal = Gtk.Alignment.new(0.5, 0.5, 1, 1)
        tal.show()
        tal.add(tbox)
        tbox.show()
        msc = Gtk.ScrolledWindow()
        msc.show()
        msc.set_shadow_type(Gtk.ShadowType.IN)
        msc.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        msc.add(self.feedview)
        mal = Gtk.Alignment.new(0.5, 0.5, 1, 1)
        mal.show()
        mal.add(msc)
        self.pack_start(tal, False, False,0)
        self.pack_start(mal, True, True,0)
        GObject.type_register(View)
        self.valid_links = ['file:']
        self.show()
        self.link_button.show()
        self.feedview.show()
        self.feed_img.show()
        self.file_img.show()
        self.__art_id = None
    def __repr__(self):
        return "View"

    def show_article(self, art_tuple):
        art, links = art_tuple
        self.log.debug("{0}: loading article {1}".format(self, art['id']))
        self.__art_id = art['id']
        try:
            self.log.debug('{0}: Showing feed icon {1}'.format(self, art['feed_id']))
            self.feed_img.set_from_stock(art['feed_id'], Gtk.IconSize.BUTTON)
        except:
            self.log.debug('{0}: Showing default feed icon'.format(self))
            self.feed_img.set_from_stock('missing', Gtk.IconSize.BUTTON)        
        self.star_this(art)
        self.valid_links = links
        self.valid_links.append("file:")
        self.link_button.set_label("[{0}] - {1}".format(
                make_date(art['date']),art['title'].encode('utf-8')))
        self.link_button.set_uri(art['link'])
        self.feedview.load_string(art['content'], "text/html", "utf-8", "file:")
        self.emit('article-loaded')
    
    def __hover_webview(self, caller, alt, url):
        if url:
            self.emit('link-hovered-in', url)
        else:
            self.emit('link-hovered-out')
    def __hover_link(self, button, event, io="out"):
        if io == "in":
            self.emit('link-hovered-in', button.get_uri())
        else:
            self.emit('link-hovered-out')
    def __override_clicks(self, frame, request, navigation_action, policy_decision, data=None):
        uri = navigation_action.get_uri()
        if uri in self.valid_links:
            return 0 # Let browse
        else:
            self.emit('link-clicked', uri)
            return 1 # Don't let browse
    
    def clear(self, caller):
        self.link_button.set_label("No Article")
        nd = """
        <html>
        <h1>No Article to show</h1>
        <p>The item you selected doesn't seem to have any articles available.</p>
        <p><em>If this doesn't change after a while, maybe you should check 
        your feeds' validity.</em></p>
        </html>"""
        self.feedview.load_string(nd, "text/html", "utf-8", "file:")
        #~ self.hide()
    def no_engine(self, caller):
        self.link_button.set_label("No Engine")
        nd = """
            <html>
            <head>
            <style>
            .red {color:red}
            </style>
            </head>
            <h1>The engine is not responding</h1>
            <p>For some reason, BRss' <strong class="red">Feed Engine</strong> is not responding.</p>
            <p>Please try and restart the engine.<br/>
            You can then reconnect the reader from the <strong>Feeds</strong> menu.</p>
            <p><em>Tip: You can also simply restart the reader, as it tries 
            to launch the engine at startup.</em></p>
            </html>"""
        self.feedview.load_string(nd, "text/html", "utf-8", "file:")
    def star_this(self, article):
        if article['id'] == self.__art_id:
            # starred articles feedback
            if article['starred'] == True:
                self.file_img.hide()
                self.star_img.show()
            else:
                self.file_img.show()
                self.star_img.hide()
    def do_link_hovered(self, url):
        self.log.debug("{0}: Hovered on {1}".format(self, url))
    def do_link_clicked(self, url):
        self.log.debug("{0}: Clicked on {1}".format(self, url))
