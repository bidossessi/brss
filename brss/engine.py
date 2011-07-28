#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#       engine.py
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
#TODO: Moving async code to GAsyncResult/GAsyncReadyCallback
# if it's possible to nest async operations, then generator
# becomes the top async function, with loop_done its callback.
# Feedgetter can the drop the threading and become an async with
# loop_callback its... callback.
#
#TODO: move to GDBus

import time
import datetime
import sqlite3
import feedparser
import threading
import os
import re
import dbus
import dbus.service
import dbus.mainloop.glib
dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

from gi.repository import Gio
from gi.repository import GObject
from gi.repository import GLib
from gi.repository import Gdk
from gi.repository import Notify
GObject.threads_init()
Gdk.threads_init()

from xml.etree  import ElementTree
import i18n
_ = i18n.language.gettext

from logger     import Logger
from task       import GeneratorTask
from common  import make_time, make_uuid, make_path, init_dirs
from common  import BASE_KEY, BASE_PATH
from common  import DB_PATH, FAVICON_PATH, IMAGES_PATH
from common  import ENGINE_DBUS_KEY, ENGINE_DBUS_PATH

class FeedGetter(threading.Thread):
    """
    Encapsulates a feed request
    """
    def __repr__(self):
        return "FeedGetter"
    def __init__(self, feed, otf, logger):
        self.__otf = otf
        self.settings = Gio.Settings.new(BASE_KEY)
        self.feed = feed
        self.result = None
        self.log = logger
        threading.Thread.__init__(self)
    
    def run(self):
        """Start the getter."""
        self.__fetch_feed_and_items(self.feed)
    def get_result(self):
        """Return getter results."""
        return self.result        
    def __fetch_feed_and_items(self, feed):
        """
        Fetch informations and articles for a feed.
        Returns the feed.
        """
        if not feed.has_key('category'):
            feed['category'] = 'uncategorized'
        if not feed.has_key('name'):
            feed['name'] = feed['url'].encode('utf-8')
        if not feed.has_key('id'):
            feed['id'] = make_uuid(feed['url'])
        if not self.__otf:
            self.log.debug('OTF disabled, skipping articles for [Feed] {0}'.format(feed['url']))
            feed['parse'] = 1
            self.result = feed
            return
        if feed.has_key('parse'):
            if not feed['parse']:
                interval = self.settings.get_int('update-interval')*60
                now = time.time()
                elapsed = now - feed['timestamp']
                self.log.debug("Elapsed: {0}, interval: {1}".format(elapsed, interval))
                if elapsed > interval:
                    feed['parse'] = True
        else: 
            feed['parse'] = True
        if feed['parse'] == False:
            self.log.debug('Too early to parse [Feed] {0}'.format(feed['url']))
            self.result = feed
            return
        #parse it
        self.log.debug('Parsing [Feed] {0}'.format(feed['url']))
        try:
            f = feedparser.parse(feed['url'])# this can take quite a while
            self.log.debug('[Feed] {0} parsed'.format(feed))
        except Exception, e:
            self.log.exception(e) 
            self.result = feed
            return
        # update basic feed informations
        # get (or set default) infos from feed
        if(hasattr(f.feed,'title')):
            feed['name'] = f.feed.title.encode('utf-8')
        bozo_invalid = ['urlopen', 'Document is empty'] # Custom non-wanted bozos
        t = threading.Thread(target = self.__fetch_remote_favicon, 
                            args=(f.feed, feed, ))
        t.start()
        if not hasattr(f, 'entries'):
            self.log.warning( "No entries found in feed {0}".format(feed['name']))
            self.result = feed
            return
        feed['fetched_count'] = limit  = len(f.entries)
        if feed['fetched_count'] > self.settings.get_int('max-articles'):
            limit = self.settings.get_int('max-articles')
        if hasattr(f,'bozo_exception'): # Feed HAS a bozo exception...
            for item in bozo_invalid:
                if item in str(f.bozo_exception):
                    self.log.warning( "Bozo exceptions found in feed {0}".format(feed['name']))
                    self.result = feed
                    return
        self.log.debug('Fetching articles for {0}'.format(feed['url']))
        #get articles
        feed['articles'] = []
        for i in range(0, feed['fetched_count']):
            # Check for article existence...
            article = self.__check_feed_item(f.entries[i])
            # flag ghost if limit exceeded
            if i >= limit:
                article['ghost'] = 1
            article['feed_id'] = feed['id']
            # no ghosts allowed from here
            if article['ghost'] == 0:
                # get images
                remote_images = self.__find_images_in_article(article['content'])
                article['images'] = []
                for i in remote_images:
                    self.__fetch_remote_image(i, article)
                feed['articles'].append(article)
        self.log.debug("[Feed] {0} fetched".format(feed['url']))
        self.result = feed
    def __find_images_in_article(self, content):
        """Searches for img tags in article content."""
        images = []
        rgxp = '''<img\s+[^>]*?src=["']?([^"'>]+)[^>]*?>'''
        m = re.findall(rgxp, content, re.I)
        for img in m:
            images.append(img)
        return images
    def __fetch_remote_image(self, src, article):
        """Get a article image and write it to a local file."""
        self.log.debug('Fetching remote image {0}'.format(src))
        name = make_uuid(src, False) # images with the same url get the same name
        img = Gio.file_new_for_path(GLib.build_filenamev([IMAGES_PATH,name]))
        webimg = Gio.file_new_for_uri(src)
        flags = Gio.FileCopyFlags.NONE
        if not webimg.query_exists(None):
            return False # no remote file, don't bother
        try:
            if img.query_exists(None):
                webinf = webimg.query_info("*", Gio.FileQueryInfoFlags.NONE, None)
                inf = img.query_info("*", Gio.FileQueryInfoFlags.NONE, None)
                if inf.get_size() == webinf.get_size(): # we already have it, don't re-download
                    self.log.debug('Remote image {0} already fetched'.format(src))
                    article['images'].append({'id':name, 'url':src, 'article_id':article['id']})
                    return True
                else:
                    flags = Gio.FileCopyFlags.OVERWRITE
            if webimg.copy(img, flags, None, 
                        self.__log_progress, src):
                article['images'].append({'id':name, 'url':src, 'article_id':article['id']})
                return True
            return False
        except Exception, e:
            self.log.exception(e)
            return False
    def __fetch_remote_favicon(self, parsed_feed, feed):
        """Find and download remote favicon for a feed."""
        self.log.debug('Fetching favicon for {0}'.format(feed['name']))
        img = Gio.file_new_for_path(GLib.build_filenamev([FAVICON_PATH,feed['id']]))
        split = feed['url'].split("/")
        nsrc = split[0] + '//' + split[1] + split[2] + '/favicon.ico'
        webimg = Gio.file_new_for_uri(nsrc)
        flags = Gio.FileCopyFlags.NONE
        if not webimg.query_exists(None):
            #alternate method
            if parsed_feed.has_key('link'):        
                url = parsed_feed['link']
                page = Gio.file_new_for_uri(url)
                dis = Gio.DataInputStream.new(page.read(None))
                while True:
                    line, size = dis.read_line(None)
                    tag = '''<link.*?icon'''
                    rgxp = '''<link\s+[^>]*?href=["']?([^"'>]+)[^>]*?>'''
                    lmt = '''head>'''
                    #~ info = GLib.MatchInfo() #FIXME: MemoryError
                    #~ link = GLib.RegEx(tag) #FIXME: MemoryError                    
                    #~ if link.match(line):#FIXME: MemoryError
                        #~ href = GLib.RegEx(rgxp)#FIXME: MemoryError
                        #~ if href.match(line, 0, info):#FIXME: MemoryError
                            #~ nsrc = info.fetch(0)#FIXME: MemoryError
                            #~ webimg = Gio.file_new_for_uri(nsrc)#FIXME: MemoryError
                            #~ info.free()#FIXME: MemoryError
                            #~ link.free()#FIXME: MemoryError
                            #~ href.free()#FIXME: MemoryError
                    if re.match(tag, line):
                        m = re.findall(rgxp, line, re.I)
                        if m:
                            webimg = Gio.file_new_for_uri(m[0])
                        break
                    if re.match(lmt, line):break # don't go beyond <head/>
                dis.free()
                page.free()
            if not webimg.query_exists(None):
                self.log.debug("No favicon available for {0}".format(feed['name']))
                return False # don't bother
        try:
            if img.query_exists(None):
                webinf = webimg.query_info("*", Gio.FileQueryInfoFlags.NONE, None)
                inf = img.query_info("*", Gio.FileQueryInfoFlags.NONE, None)
                if inf.get_size() == webinf.get_size(): # we already have it, don't re-download
                    self.log.debug('Remote image {0} already fetched'.format(nsrc))
                    return True
                else:
                    flags = Gio.FileCopyFlags.OVERWRITE
            if webimg.copy(img, flags, None, 
                        self.__log_progress, nsrc):
                self.log.debug("Favicon found for {0}".format(feed['name']))
            else:
                self.log.debug("No favicon available for {0}".format(feed['name']))
        except Exception, e:
            self.log.exception(e)
        return False
    def __check_feed_item(self, feed_item):
        """
        Pre-format a feed article for database insertion.
        Sets a default value if there's not any.
        """
        gmap = {'no-content':1}
        try:
            dp = feed_item.date_parsed
            secs = time.mktime(datetime.datetime(dp[0], dp[1], dp[2], dp[3], dp[4], dp[5], dp[6]).timetuple())
        except Exception, e:
            self.log.exception(e) 
            secs = make_time()
        title = 'Without title'
        if hasattr(feed_item,'title'):
            if feed_item.title is not None: title = feed_item.title.encode("utf-8")
            else: title = 'Without title'
        content = 'no-content'        
        if hasattr(feed_item,'content'):
            try:
                content = feed_item.content[0].get('value').encode("utf-8")
            except Exception, e:
                self.log.exception(e) 
        else:
            if hasattr(feed_item,'description'):
                if feed_item.description is not None:
                    content = feed_item.description.encode("utf-8")
        link = 'Without link'
        if hasattr(feed_item,'link'):
            if feed_item.link is not None: link = feed_item.link.encode("utf-8")
            else: link = 'Without link'
        uid = make_uuid(content+link+title, False) # if
        #article ready
        article =  {
            'date':secs, 
            'title':title, 
            'content':content, 
            'url':link, 
            'id': uid, 
            'ghost': gmap.get(content) or 0,
            }
        self.log.debug('Found a new article: {0}'.format(article['id']))
        return article

    def __log_progress(self, size, total, name):
        perc = (size/total)*100
        self.log.debug("Getting {0}: {1}%".format(name, perc))
        
class Engine (dbus.service.Object):
    """ 
    The feed engine provides DBus Feed and Category CRUD services.
    It tries as much as possible to rely on atomic procedures to
    simplify the feed handling process.
    """
    
    #### DBUS METHODS ####
    ## 1. CRUD
    @dbus.service.method('com.itgears.BRss.Engine')
    def create(self, item):
        """Add a feed or category."""
        if not item:
            return
        if item and item.has_key('type') and item['type'] in ['feed', 'category']:
            if item['type'] == 'feed':
                self.__update_feeds([item], self.settings.get_boolean('on-the-fly'))
            elif item['type'] == 'category':
                self.__add_category(item)
    @dbus.service.method('com.itgears.BRss.Engine')
    def edit(self, item):
        """Edit a feed or category."""
        if not item:
            return
        if item and item.has_key('type') and item['type'] in ['feed', 'category']:
            if item['type'] == 'feed':
                self.__update_feeds(item)
            elif item['type'] == 'category':
                self.__edit_category(item)    
    @dbus.service.method('com.itgears.BRss.Engine')
    def stop_update(self):
        self.log.debug("Trying to stop update")
        self.updater.stop()

    @dbus.service.method('com.itgears.BRss.Engine')
    def update(self, item=None):
        """Update All/Category/Feed."""
        if item == 'all': 
            self.__update_all()
        elif item and item.has_key('type') and item['type'] in ['feed', 'category']:
            if item['type'] == 'feed':
                feed = self.__get_feed(item['id'])
                self.__update_feeds([feed])
            elif item['type'] == 'category':
                self.__update_category(item)
    @dbus.service.method('com.itgears.BRss.Engine')
    def delete(self, item=None):
        """Delete All/Category/Feed."""
        if not item:
            return
        if item.has_key('type') and item['type'] in ['feed', 'category']:
            if item['type'] == 'feed':
                feed = self.__get_feed(item['id'])
                self.__delete_feed(feed)
            elif item['type'] == 'category':
                self.__delete_category(item)
    ## 2. Menu
    @dbus.service.method('com.itgears.BRss.Engine', out_signature='aa{sv}')
    def get_menu_items(self):
        """Return an ordered list of categories and feeds."""
        self.log.debug("Building menu items")
        menu = [] 
        cat = self.__get_all_categories()
        for c in cat:
            feeds = self.__get_feeds_for(c) or []
            for f in feeds:
                c['count'] = c['count'] + f['count']
            menu.append(c)
            if feeds:
                menu.extend(feeds)
        return menu
    ## 3. Articles list
    @dbus.service.method('com.itgears.BRss.Engine', out_signature='aa{sv}')
    def get_articles_for(self, item):
        """
        Get all articles for a feed or category.
        Returns a  list of articles.
        """
        # policy:
        if self.settings.get_boolean('hide-read'):
            self.log.debug("Fetching unread articles for [Feed] {0}".format(item['name'].encode('utf-8')))
            x = 'AND read = 0'
        else:
            self.log.debug("Fetching all articles for [Feed] {0}".format(item['name'].encode('utf-8')))
            x = ''
        if item and item.has_key('type'):
            if item['type'] == 'feed':
                query = 'SELECT id,read,starred,title,date,url,feed_id FROM articles WHERE feed_id = "{0}" {1} ORDER BY date ASC'.format(item['id'], x)
                return self.__make_articles_list(query)
            if item['type'] == 'category':
                # recurse
                feeds = self.__get_feeds_for(item)
                articles = []
                for f in feeds:
                    query = 'SELECT id,read,starred,title,date,url,feed_id FROM articles WHERE feed_id = "{0}" {1} ORDER BY date ASC'.format(f['id'], x)
                    articles.extend(self.__make_articles_list(query))
                return articles
            # special cases
            if item['type'] == 'unread':
                return self.__get_unread_articles()
            if item['type'] == 'starred':
                return self.__get_starred_articles()
    ## 4. Article
    @dbus.service.method('com.itgears.BRss.Engine', in_signature='a{sv}',
                        out_signature='(a{sv}as)')
    def get_article(self, item):
        """Returns a full article."""
        article = self.__get_article(item['id'])
        # check policy first
        return self.__swap_image_tags(article)

        
    @dbus.service.method('com.itgears.BRss.Engine')
    def export_opml(self, filename):
        """Export feeds and categories to an OPML file."""
        opml = Gio.file_new_for_path(filename)
        fos = opml.create(Gio.FileCreateFlags.NONE, None, None)
        dos = Gio.DataOutputStream(fos)
        dos.put_string('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n', None, None)
        dos.put_string('<opml version="1.0">\n', None, None)
        dos.put_string('\t<title>BRss Feed List</title>\n', None, None)
        dos.put_string('\t<head></head>\n', None, None)
        dos.put_string('\t<body>\n', None, None)
        cats = self.__get_all_categories()
        for c in cats:
            dos.put_string('\t\t<outline title="{0}" text="{0}" description="{0}" type="folder">\n'.format(
                c['name']), None, None)
            feeds = self.__get_feeds_for(c)
            for f in feeds:
                dos.put_string('\t\t\t<outline title="{0}" text="{0}" type="rss" xmlUrl="{1}"/>\n'.format(
                    f['name'].replace('&', '%26'),#.encode('utf-8'),
                    f['url'].replace('&', '%26')), None, None)
            dos.put_string('\t\t</outline>\n', None, None)
        dos.put_string('\t</body>\n', None, None)
        dos.put_string('</opml>\n', None, None)
        fos.flush()
        fos.close()
        fos.free()
        

    @dbus.service.method('com.itgears.BRss.Engine')
    def import_opml(self, filename):
        """Import feeds and categories from an OPML file."""
        f = open(os.path.abspath(filename), 'r')
        tree = ElementTree.parse(f)
        current_category = 'uncategorized'
        cursor = self.conn.cursor()
        feeds = []
        cats = []
        for node in tree.getiterator('outline'):
            name = node.attrib.get('text').replace('[','(').replace(']',')')
            url = node.attrib.get('xmlUrl')
            if url: # isolate feed
                feeds.append({'type':'feed','url':url, 'category':current_category})
            else: # category
                if len(node) is not 0:
                    c = self.__get_category(name)
                    if not c:
                        c = {'type':'category','name':name, 'id':make_uuid(name)}
                    current_category = c['id']
                    cats.append(c)
        #ok now create
        for c in cats:
            self.__add_category(c)
        self.__update_feeds(feeds, self.settings.get_boolean('on-the-fly')) # on-the-fly policy
        self.notice('ok', _('Feeds imported!'))
        self.__update_all()
    
    @dbus.service.method('com.itgears.BRss.Engine', out_signature='aa{sv}')
    def search_for(self, string):
        """Search article contents for a string.
        returns a list of articles."""
        q = 'SELECT id,read,starred,title,date,url,feed_id FROM articles WHERE title LIKE "%{0}%" OR content LIKE "%{0}%"'.format(string)
        try:
            arts = self.__make_articles_list(q)
            if len(arts) > 0:
                self.notice('new', _('Found {0} articles matching "{1}"'.format(len(arts), string)))
            else:    
                self.warning(_('Couldn\'t find any article matching "{0}"'.format(string)))
            return arts
        except Exception, e:
            self.log.exception(e) 
            self.warning(_('Search for "{0}" failed!'.format(string)))

    @dbus.service.method('com.itgears.BRss.Engine', in_signature='a{sv}')
    def toggle_starred(self, item):
        """Toggle the starred status of an article"""
        self.updated(self.__toggle_article('starred', item))
    @dbus.service.method('com.itgears.BRss.Engine', in_signature='a{sv}')
    def toggle_read(self, item):
        """Toggle the starred status of an article"""
        self.updated(self.__toggle_article('read', item))

    @dbus.service.method('com.itgears.BRss.Engine')
    def count_special(self):
        """
        Count all unread articles.
        Return a string.
        """
        u = self.__count_unread_articles() 
        s = self.__count_starred_items()
        return u, s

    ## 5. Signals
    @dbus.service.signal('com.itgears.BRss.Engine', signature='s')
    def warning (self, message):
        """
        Emit a warning signal of type 'wtype' with 'message'.
        """
        self.log.warning(message)

    @dbus.service.signal('com.itgears.BRss.Engine', signature='ss')
    def notice (self, wtype, message):
        """
        Emit a notice signal of type 'wtype' with 'message'.
        """
        self.log.info(message)

    @dbus.service.signal('com.itgears.BRss.Engine', signature='a{sv}')
    def updated(self, item):
        pass
    @dbus.service.signal('com.itgears.BRss.Engine')
    def complete(self, c):
        self.notice('ok',_("Updated {0} feed(s) | {1} new article(s)".format(c, self.__added_count)))
        self.__notify_update(c, self.__added_count)

    @dbus.service.signal('com.itgears.BRss.Engine')
    def updating(self, c):
        self.notice('wait',_("Updating {0} feed(s)".format(c)))

    @dbus.service.signal('com.itgears.BRss.Engine', signature='a{sv}')
    def added(self, item):
        #TODO: This should also handle articles
        self.notice('added',_("[{0}] {1} added".format(item['type'], item['name'])))

    ## 6. Runners and stoppers
    @dbus.service.method('com.itgears.BRss.Engine')
    def start(self):
        GObject.MainLoop().run()
        self.__update_all()

    @dbus.service.method('com.itgears.BRss.Engine')
    def exit(self):
        """Clean up and leave"""
        self.__clean_up()
        self.log.debug("Quitting {0}".format(self))
        GObject.MainLoop().quit()
        return "Quitting"
    
    #### INTERNAL METHODS  ####
    def __repr__(self):
        return "BRssEngine"
    ## 1. initialization
    def __init__(self):
        self.conn           = sqlite3.connect(DB_PATH, check_same_thread=False)
        self.log            = Logger("engine.log", "BRss-Engine")
        # check
        try:
            self.__get_all_categories()
        except Exception, e:
            self.log.warning("Could not find database; creating it")
            self.__init_database()
        self.__in_update        = False
        self.__last_update      = time.time()
        self.settings = Gio.Settings.new(BASE_KEY)
        self.settings.connect("changed::update-interval", self.__set_polling)
        self.__added_count      = 0
        self.__deleted_feeds    = []
        self.timeout_id         = None
        # d-bus
        bus_name = dbus.service.BusName(ENGINE_DBUS_KEY, bus=dbus.SessionBus())
        dbus.service.Object.__init__(self, bus_name, ENGINE_DBUS_PATH)
        self.__set_polling(self.settings)
        self.updater = GeneratorTask(
            self.__loop_generator, 
            self.__loop_callback, 
            self.__loop_done)
        # ok, looks like we can start
        Notify.init('BRss')
        if self.settings.get_boolean('use-notify'):
            self.__notify_startup()
        self.log.debug("Starting {0}".format(self))
        
    def __set_polling(self, settings, key=None):
        # GSettings style
        if settings.get_boolean('auto-update'):
            if self.timeout_id:
                self.log.debug("Timeout removed: {0}".format(GLib.source_remove(self.timeout_id)))
            interval = settings.get_int('update-interval')
            self.timeout_id = GLib.timeout_add_seconds(
                    0, 
                    interval*60, 
                    self.__timed_update, 
                    None)
            self.log.debug('New timeout: {0} minutes, id: {1}'.format( interval, self.timeout_id))
            
    def __repr__(self):
        return "Engine"
    ## Create (*C*RUD)
    def __add_category(self, category):
        try:
            category['name'] = category['name'].encode('utf-8')
            category['id'] = category.get('id') or make_uuid(category['name'])
            assert self.__item_exists('categories', 'name', category['name']) == False
            cursor = self.conn.cursor()
            q = 'INSERT INTO categories VALUES("{0}", "{1}")'.format(category['id'], category['name'])
            cursor.execute(q)
            self.conn.commit()
            cursor.close()
            self.added(category) #allows autoinserting
        except AssertionError:
            self.log.debug('Category {0} already exists! Aborting'.format(category['name']))
    def __add_feed(self, feed):
        try:
            assert self.__item_exists('feeds', 'url', feed['url']) == False
            q = 'INSERT INTO feeds VALUES("{0}", "{1}", "{2}", "{3}", "{4}", "{5}")'.format(
                feed['id'], feed['name'], feed['url'], feed['category'], feed['timestamp'], feed['parse'])
            cursor = self.conn.cursor()
            cursor.execute(q)
            self.conn.commit()
            cursor.close()
            self.added(feed)#allows autoinserting
        except AssertionError:
            self.log.debug('[Feed] {0} already exists! Aborting'.format(feed['name']))
    def __add_article(self, art):
        try:
            self.log.debug("inserting [Article] {0}".format(art['id']))
            assert self.__item_exists('articles', 'url', art['url']) == False
            cursor = self.conn.cursor()
            cursor.execute (
                'INSERT INTO articles VALUES(?, ?, ?, ?, ?, 0, 0, ?, ?)', 
                [
                    art['id'].decode("utf-8"),
                    art['title'].decode("utf-8"),
                    art['content'].decode("utf-8"),
                    art['date'],
                    art['url'].decode("utf-8"),
                    art['feed_id'],
                    art['timestamp'],
                ]
            )
            self.conn.commit()
            cursor.close()
            #inser images
            self.__added_count += 1
        except AssertionError:
            self.log.debug("article {0} already exists, skipping".format(art['id']))
        for img in art['images']:
            self.__add_image(img)
    def __add_image(self, img):
        cursor = self.conn.cursor()
        try:
            self.log.debug("Inserting image {0}".format(img['url']))
            assert self.__item_exists('images', 'url', img['url']) == False
            cursor.execute(
                'INSERT INTO images VALUES(?, ?)', 
                [
                    img['id'].decode('utf-8'),
                    img['url'].decode('utf-8'),
                ]
            )
            self.conn.commit()
        except AssertionError:
            self.log.debug("image {0} already exists, skipping".format(img['url']))
        try:
            id = make_uuid(img['id']+img['article_id'], False)
            assert self.__item_exists('images_pool', 'id', id) == False
            cursor.execute(
                'INSERT INTO images_pool VALUES(?, ?, ?)', 
                [
                    id.decode('utf-8'),
                    img['id'].decode('utf-8'),
                    img['article_id'].decode('utf8')
                ]
            )
            self.conn.commit()
            cursor.close()
        except AssertionError:
            self.log.debug("image {0} already linked to article {1}, skipping".format(
                img['url'], img['article_id']))
    def __add_items_for(self, feed):
        if feed and not feed['url'] in self.__deleted_feeds:
            try:
                articles = feed.pop('articles') # we don't need them here
            except KeyError:
                articles = None
            except Exception, e:
                self.log.warning("Error occured: {0}".format(e))
                
            feed['timestamp'] = time.time()
            if articles:
                feed['parse'] = 0
            else:
                feed['parse'] = 1                
            if self.__item_exists('feeds', 'id', feed['id']):
                self.__edit_feed(feed)
            # else create if it doesn't
            else:
                self.__add_feed(feed)
            cursor = self.conn.cursor()
            # verify that feed has (ever had) entries
            cursor.execute('SELECT count(id) FROM articles WHERE feed_id = ?', [feed['id']])
            c = cursor.fetchone()[0]
            if feed.has_key('fetched_count') and feed['fetched_count'] == 0 and c == 0: # ... and never had! Fingerprinted as invalid!
                self.warning('[Feed] {0} seems to be invalid'.format(feed['name']))
                return False
            # update feed data
            q = 'UPDATE feeds SET name = "{0}", timestamp = "{1}" WHERE id = "{2}"'.format(
                feed['name'],feed['timestamp'],feed['id'])
            cursor.execute(q)
            self.conn.commit()
            cursor.close()
            if articles:
                for art in articles:
                    art['timestamp'] = feed['timestamp']
                    self.__add_article(art)
            self.__clean_up_feed(feed) # returns (total, unread, starred)

    ## Retreive (C*R*UD)
    def __get_feed(self, feed_id):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM feeds WHERE id = ?', [feed_id])
        row = cursor.fetchone()
        cursor.close()
        try:
            return {'type':'feed','id': row[0], 'name':row[1], 'url':row[2], 'category':row[3]}
        except Exception, e: 
            self.log.warning(e)
            return None
    def __get_category(self, name):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM categories WHERE name = ?', [name])
        row = cursor.fetchone()
        cursor.close()
        try:
            return {'type':'category','id': row[0], 'name':row[1], 'count':'0'}
        except Exception, e: 
            self.log.warning(e)
            return None
    def __get_all_categories(self):
        self.log.debug("Getting all categories")        
        cat = []
        cursor = self.conn.cursor()
        cursor.execute('SELECT id,name FROM categories ORDER BY name ASC')
        rows = cursor.fetchall()
        for r in rows:
            cat.append({'type':'category','id': r[0], 'name':r[1], 'count':0, 'url':'none', 'category':r[0]},)
        cursor.close()
        return cat
    def __get_feeds_for(self, c):
        self.log.debug("Getting feeds for category: {0}".format(c['name'].encode('utf-8')))                
        feeds = []
        q = 'SELECT id,name,url,category_id,timestamp,parse FROM feeds WHERE category_id = "{0}" ORDER BY name ASC'.format(c['id'])
        cursor = self.conn.cursor()
        cursor.execute(q)
        rows = cursor.fetchall()
        for r in rows:
            f = {'type':'feed', 'id': r[0], 'name':r[1].encode('utf-8'), 'url':r[2], 
                'category':r[3], 'timestamp':r[4], 'parse':r[5]}
            f['count'] = self.__count_unread_articles(f)
            feeds.append(f)
        cursor.close()
        return feeds
    def __get_article(self, id):
        self.log.debug("Fetching [Article] {0}".format(id))
        q = 'SELECT id,title,date,url,content, starred,feed_id FROM articles WHERE id = "{0}"'.format(id)
        # run query
        cursor = self.conn.cursor()
        cursor.execute(q)
        r = cursor.fetchone()
        cursor.close()
        return  {
                    'id':str(r[0]), 
                    'title':r[1], 
                    'date':str(r[2]),
                    'link':r[3], 
                    'content':r[4], 
                    'starred':r[5], 
                    'feed_id':r[6], 
                }
    
    ## Update (CR*U*D)
    def __edit_category(self, category):
        try:
            assert self.__item_exists('categories', 'id', category['id']) == True
            # we don't want duplicate category names
            assert self.__item_exists('categories', 'name', category['name']) == True
            # update in database
            self.log.debug("Editing category {0}".format(category['id']))
            q = 'UPDATE categories SET name = "{0}"WHERE id = "{1}"'.format(
                category['name'], 
                category['id'])
            cursor = self.conn.cursor()
            cursor.execute(q)
            self.conn.commit()
            cursor.close()
            category['count'] = self.__count_unread_articles(category)
            self.updated(category)
        except AssertionError:
            self.warning(_("Category {0} doesn't exist, or is a duplicate! Aborting".format(category['name'].encode('utf-8'))))
    def __edit_feed(self, feed):
        try:
            assert self.__item_exists('feeds', 'id', feed['id']) == True
            # we don't want duplicate feed urls
            assert self.__item_exists('feeds', 'url', feed['url']) == True
            self.log.debug("Editing feed {0}".format(feed['url']))
            # update in database
            q = 'UPDATE feeds SET name = "{0}", url = "{1}", timestamp = "{2}", parse = "{3}" WHERE id = "{4}"'.format(
                feed['name'], 
                feed['url'], 
                feed['timestamp'],
                feed['parse'],
                feed['id'])
            cursor = self.conn.cursor()
            cursor.execute(q)
            self.conn.commit()
            cursor.close()
            #~ self.updated(feed)
            #~ self.notice('info', "[Feed] {0} edited".format(feed['url']))
        except AssertionError:
            self.warning(_("[Feed] {0} doesn't exist, or is a duplicate! Aborting".format(feed['url'])))
    def __update_all(self):
        feeds = []
        categories = self.__get_all_categories()
        for c in categories:
            feeds.extend(self.__get_feeds_for(c))
        self.__update_feeds(feeds)
    def __update_category(self, category):
        feeds = self.__get_feeds_for(category)
        self.__update_feeds(feeds)    
    def __loop_generator(self, flist, otf):
        self.log.debug("About to update {0} feed(s); otf: {1}".format(len(flist), otf))
        self.fcount = 0
        self.updating(len(flist))
        for feed in flist:
            # let the UI know we're still busy
            name  = feed.get('name') or feed['url']
            f = FeedGetter(
                feed, 
                otf,
                self.log, 
                )
            f.start()
            f.join()
            yield f.get_result()
    def __loop_callback(self, feed=None):
        self.fcount += 1
        if feed and feed.has_key('id'):
            self.log.debug("Inserting [Feed] {0} ({1})".format(feed['url'], self.fcount))
            self.__add_items_for(feed)
            self.__update_ended(feed)
        else:
            self.log.debug("Empty feed received")
    def __loop_done(self, *args):
        # count the number of updated feeds if possible
        self.complete(self.fcount)        
        self.__in_update = False
    def __update_feeds(self, feed_list, otf=True):
        self.__in_update    = True
        self.__last_update  = time.time()
        self.__added_count  = 0
        self.updater.start(feed_list, otf)
    ## Delete (CRU*D*)
    def __delete_category(self, category):
        feeds = self.__get_feeds_for(category)
        for f in feeds:
            self.__delete_feed(f)
        if not category['id'] == 'uncategorized':
            q = 'DELETE FROM categories WHERE id = "{0}"'.format(category['id'])
            cursor = self.conn.cursor()        
            cursor.execute(q)
            self.conn.commit()
            cursor.close()
            self.notice('warning', _("Category {0} deleted!".format(category['name'].encode('utf-8'))))
        else:
            self.notice('warning', _("All uncategorized feeds deleted!"))
    def __delete_feed(self, feed):
        articles = self.get_articles_for(feed)
        if articles:
            for a in articles:
                self.__delete_article(a['id'])
        # now delete
        try:
            favicon = Gio.file_new_for_path(GLib.build_filenamev([FAVICON_PATH,feed['id']]))
            favicon.delete(None)
        except Exception, e: # not there?
            self.log.exception(e) 
        q = 'DELETE FROM feeds WHERE id = "{0}"'.format(feed['id'])
        cursor = self.conn.cursor()        
        cursor.execute(q)
        self.conn.commit()
        cursor.close()    
        self.__deleted_feeds.append(feed['url'])
        self.notice('warning', _("[Feed] {0} deleted!".format(feed['url'])))
    def __delete_article(self, art_id):
        self.log.debug("Deleting article {0}".format(art_id))
        try:
            assert self.__item_exists('articles', 'id', art_id) == True
            # delete images first.
            self.__delete_images(art_id)
            cursor = self.conn.cursor()
            # now delete article
            q = 'DELETE FROM articles WHERE id = "{0}"'.format(art_id)
            cursor.execute(q)
            self.conn.commit()
            cursor.close()        
        except AssertionError:
            self.log.debug("Article {0} doesn't exist or could not be deleted".format(art_id))
    def __delete_images(self, art_id):
        cursor = self.conn.cursor()
        q = 'SELECT DISTINCT image_id FROM images_pool WHERE article_id = "{0}"'.format(art_id)
        cursor.execute(q)
        imgs = cursor.fetchall()
        if imgs:
            for i in imgs:
                #confirm if we still have refs to this image
                q = 'SELECT COUNT(id) from images_pool WHERE image_id = "{0}"'.format(i[0])
                cursor.execute(q)
                c = cursor.fetchone()
                if c and c[0] == 1:
                    img = Gio.file_new_for_path(GLib.build_filenamev([IMAGES_PATH,i[0]]))
                    self.log.debug("No more reference to image {0}, deleting from filesystem".format(img.get_path()))
                    try:
                        img.delete(None)
                        # now remove image entry
                        q = 'DELETE FROM images WHERE id = "{0}"'.format(i[0])
                        cursor.execute(q)
                        self.conn.commit()
                    except Exception, e: 
                        self.log.exception(e) 
        # remove article images from pool
        q = 'DELETE FROM images_pool WHERE article_id = "{0}"'.format(art_id)
        cursor.execute(q)
        self.conn.commit()
        cursor.close()

    ## Convenience functions
    def __clean_up_feed(self, feed):
        """
        This is where old feeds are removed.
        We only keep the last `max_entries` articles.
        """
        self.log.debug("Cleaning up feed {0}".format(feed['name']))
        q = 'SELECT id FROM articles WHERE feed_id = "{0}" and starred = 0 ORDER BY date DESC'.format(feed['id'])
        u = 'SELECT id FROM articles WHERE feed_id = "{0}" and starred = 0 and read = 0 ORDER BY date DESC'.format(feed['id'])
        r = 'SELECT id FROM articles WHERE feed_id = "{0}" and starred = 0 and read = 1 ORDER BY date DESC'.format(feed['id'])
        cursor = self.conn.cursor()
        cursor.execute(q)
        allrows = cursor.fetchall()
        atotal = len(allrows)
        cursor.close()
        cursor = self.conn.cursor()
        cursor.execute(u)
        urows = cursor.fetchall()
        utotal = len(urows)
        cursor.close()
        cursor = self.conn.cursor()
        cursor.execute(r)
        rrows = cursor.fetchall()
        rtotal = len(rrows)
        cursor.close()
        #~ if atotal > self.__max_entries:
        if atotal > self.settings.get_int('max-articles'):
            self.log.debug("Cropping feed {0} to the latest {1} unread articles".format(
                    feed['id'],
                    self.settings.get_int('max-articles')))            
            # 1. if we have more unread than max_entries, no need to keep the read
            if utotal > self.settings.get_int('max-articles'):
                self.log.debug("Deleting all read articles")
                for r in rrows:
                    self.__delete_article(r[0])
                # now delete the excess
                diff = atotal - rtotal - self.settings.get_int('max-articles')
                self.log.debug("Deleting {0} excess unread articles".format(diff))
                for u in urows:
                    if diff > 0:
                        self.__delete_article(u[0])
                        diff -= 1
            # 2. not that many unread, so remove the excess read
            else:
                diff = atotal - self.settings.get_int('max-articles')
                self.log.debug("Deleting {0} excess read articles".format(diff))
                for r in rrows:
                    if diff > 0:
                        self.__delete_article(r[0])
                        diff -= 1

    def __update_ended(self, feed):
        if feed:
            feed['count'] = self.__count_unread_articles(feed)
            self.notice('wait', _('Updated [Feed] {0}'.format(feed['url'])))
            self.updated(feed)
        
    def __timed_update(self, *args):
        if self.settings.get_boolean('auto-update'):
            self.log.debug("About to auto-update")
            interval = self.settings.get_int('auto-update')*60
            elapsed = time.time() - self.__last_update
            if elapsed > interval and not self.__in_update:
                self.log.debug("Running auto-update")
                self.__update_all()
            else:
                self.log.debug("Not auto-updating")
            return True
    
    def __toggle_article(self, col, item):
        """Toggles the state of an article column.
        Returns the current state
        """
        bmap = {True:False, False:True}
        item[col] = bmap.get(item[col])
        self.log.debug("Toggling {0}: {1} on {2}".format(col, item[col], item['id']))
        q = 'UPDATE articles set {0} = {1} WHERE id = "{2}"'.format(col, int(item[col]), item['id'])
        cursor = self.conn.cursor()
        cursor.execute(q)
        self.conn.commit()
        cursor.close()
        return item
    def __count_articles(self, item=None):
        if item and item.has_key('type'):
            if item['type'] == 'category':
                feeds = self.__get_feeds_for(item)
                c = 0
                for f in feeds:
                    c += self.__count_unread_articles(f)
                return c
            elif item['type'] == 'feed':
                q = 'SELECT COUNT(id) FROM articles WHERE feed_id = "{0}"'.format(item['id'])
        else:
            q = 'SELECT COUNT(id) FROM articles'
        cursor = self.conn.cursor()
        cursor.execute(q)
        c = cursor.fetchone()
        return c[0]
    def __count_unread_articles(self, item=None):
        if item and item.has_key('type'):
            if item['type'] == 'category':
                feeds = self.__get_feeds_for(item)
                c = 0
                for f in feeds:
                    c += self.__count_unread_articles(f)
                return c
            elif item['type'] == 'feed':
                q = 'SELECT COUNT(id) FROM articles WHERE feed_id = "{0}" AND read = 0'.format(item['id'])
        else:
            q = 'SELECT COUNT(id) FROM articles WHERE read = 0'
        cursor = self.conn.cursor()
        cursor.execute(q)
        c = cursor.fetchone()
        return c[0]
    def __count_starred_items(self, item=None):
        if item  and item.has_key('type'):
            if item['type'] == 'category':
                feeds = self.__get_feeds_for(item)
                c = 0
                for f in feeds:
                    c += self.__count_starred_items(f)
                return c
            elif item['type'] == 'feed':
                q = 'SELECT COUNT(id) FROM articles WHERE feed_id = "{0}" AND starred = 1'.format(item['id'])
        else:
            q = 'SELECT COUNT(id) FROM articles WHERE starred = 1'
        cursor = self.conn.cursor()
        cursor.execute(q)
        c = cursor.fetchone()
        return c[0]
    def __get_unread_articles(self):
        articles = []
        query = 'SELECT id,read,starred,title,date,url,feed_id FROM articles WHERE read = 0 ORDER BY date ASC'
        # run query
        return self.__make_articles_list(query)
    def __get_starred_articles(self):
        articles = []
        query = 'SELECT id,read,starred,title,date,url,feed_id FROM articles WHERE starred = 1 ORDER BY date ASC'
        # run query
        return self.__make_articles_list(query)
    def __swap_image_tags(self, article):
        """
        Replace images remote src with local src.
        Returns the transformed article.
        """
        links = []
        cursor = self.conn.cursor()
        q = 'SELECT p.image_id,i.url FROM images_pool p JOIN images i ON p.image_id = i.id WHERE p.article_id = "{0}"'.format(article['id'].decode('utf-8'))
        #~ print q
        cursor.execute(q)
        row = cursor.fetchall()
        if (row is not None) and (len(row)>0):
            self.log.debug("Swapping image tags for [Article] {0}".format(article['id']))
            for i in row:
                img = Gio.file_new_for_path(GLib.build_filenamev([IMAGES_PATH, str(i[0])]))
                article['content'] = article['content'].replace(
                        i[1], img.get_uri())
                links.append(img.get_uri())
            return article, links
        else:
            return article, ['valid']
    def __make_articles_list(self, q):
        """
        Executes the give articles query and formats the resulting
        articles into a list of dictionaries.
        """
        articles = []
        cursor = self.conn.cursor()
        cursor.execute(q)
        rows = cursor.fetchall()
        cursor.close()
        for r in rows:
            articles.append(
                {
                    'type':'article',
                    'id':r[0], 
                    'read':r[1], 
                    'starred':r[2],
                    'title':r[3], 
                    'date':r[4], 
                    'url':r[5], 
                    'feed_id':r[6], 
                }
            )
        return articles
    def __clean_up(self):
        self.log.debug("Cleaning up active connections")
    def __item_exists(self, table, key, value):
        """
        Verify if an item exists in the database.
        Returns a bool of it existence.
        """
        q = 'SELECT id FROM {0} WHERE {1} = "{2}"'.format(table, key, value)
        cursor = self.conn.cursor()
        cursor.execute(q)
        row = cursor.fetchone()
        cursor.close()
        if row:
            return True
        return False
    def __init_database(self):
        """Create database and set the least intrusive default configurations."""
        self.log.info("Initializing database")
        cursor = self.conn.cursor()
        cursor.executescript('''
            CREATE TABLE categories(
                id varchar(256) PRIMARY KEY, 
                name varchar(32) NOT NULL);
            CREATE TABLE feeds(
                id varchar(256) PRIMARY KEY, 
                name varchar(32) NOT NULL, 
                url varchar(1024) NOT NULL, 
                category_id integer NOT NULL, 
                timestamp integer NOT NULL, 
                parse INTEGER NOT NULL);
            CREATE TABLE articles(
                id varchar(256) PRIMARY KEY, 
                title varchar(256) NOT NULL, 
                content text, 
                date integer NOT NULL, 
                url varchar(1024) NOT NULL, 
                read INTEGER NOT NULL, 
                starred INTEGER NOT NULL, 
                feed_id integer NOT NULL, 
                timestamp integer NOT NULL);
            CREATE TABLE images_pool(
                id varchar(256) PRIMARY KEY, 
                image_id varchar(256) NOT NULL, 
                article_id varchar(256) NOT NULL);
            CREATE TABLE images(
                id varchar(256) PRIMARY KEY, 
                url TEXT NOT NULL);
            ''')
        self.conn.commit()
        cursor.execute("INSERT INTO categories(id,name) VALUES('uncategorized',{0})".format(_('Uncategorized')).decode('utf-8'))
        self.conn.commit()
        cursor.close()
        
    def __notify_startup(self):
        """Send an startup notification with libnotify"""
        if not self.settings.get_boolean('use-notify'):
            self.log.debug("Startup Notification suppressed")
        else:
            n = Notify.Notification.new(
                _("BRss started"),
                _("BRss Feed Engine is running"),
                make_path('icons', 'brss-engine.svg'))
            n.show()

    def __notify_update(self, c, ac):
        if not self.settings.get_boolean('use-notify'):
            self.log.debug("Update Notification suppressed")
        else:
            n = Notify.Notification.new(
                _("BRss: Update report"),
                _("Updated {0} feeds\n{1} new article(s)\n{2} unread article(s)".format(
                    c, ac, self.__count_unread_articles())),
                make_path('icons', 'brss-engine.svg'))
            n.show()

def main():
    init_dirs()
    session_bus = dbus.SessionBus()
    if session_bus.request_name(ENGINE_DBUS_KEY) != dbus.bus.REQUEST_NAME_REPLY_PRIMARY_OWNER:
        print "Engine already running"
    else:
        engine = Engine()
        engine.start()

if __name__ == '__main__':
	main()
