#!/usr/bin/env python2
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
#TODO: Stopping updates
import time
import datetime
import sqlite3
import feedparser
import urllib2
import threading
import os
import re
import html5lib
import dbus
import dbus.service
import dbus.mainloop.glib
dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

from gi.repository import Gtk
from gi.repository import GLib
from gi.repository import Gdk
from gi.repository import Notify
Gdk.threads_init()

from xml.etree  import ElementTree
from Queue      import Queue

from logger     import Logger
from functions  import make_time, make_uuid, make_path
from task       import GeneratorTask

class FeedGetter(threading.Thread):
#~ class FeedGetter:
    """
    Encapsulates a feed request
    """
    def __repr__(self):
        return "FeedGetter"
    def __init__(self, feed, base_path, max_entries, interval, otf, logger):
        self.__otf = otf
        self.__max_entries = max_entries
        self.__update_interval = interval
        self.favicon_path = os.path.join(base_path, 'favicons')
        self.images_path = os.path.join(base_path, 'images')
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
            self.log.debug('OTF disabled, skipping articles for [Feed] {0}'.format(feed['name'].encode('utf-8')))
            feed['parse'] = 1
            self.result = feed
            return
        if feed.has_key('parse'):
            if feed['parse']:
                interval = self.__update_interval*60
                now = time.time()
                elapsed = now - feed['timestamp']
                if elapsed > interval:
                    feed['parse'] = 1
        else: 
            feed['parse'] = 1
        if feed['parse'] == False:
            self.log.debug('Too early to parse [Feed] {0}'.format(feed['name'].encode('utf-8')))
            self.result = feed
            return
        #parse it
        self.log.debug('Parsing [Feed] {0}'.format(feed['name'].encode('utf-8')))
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
        if hasattr(f.feed, 'link'):
            t = threading.Thread(target = self.__fetch_remote_favicon, 
                            args=(self.favicon_path, f, feed, ))
            t.start()
        if not hasattr(f, 'entries'):
            self.log.warning( "No entries found in feed {0}".format(feed['name']))
            self.result = feed
            return
        feed['fetched_count'] = limit  = len(f.entries)
        if feed['fetched_count'] > self.__max_entries:
            limit = self.__max_entries
        if hasattr(f,'bozo_exception'): # Feed HAS a bozo exception...
            for item in bozo_invalid:
                if item in str(f.bozo_exception):
                    self.log.warning( "Bozo exceptions found in feed {0}".format(feed['name']))
                    self.result = feed
                    return
        self.log.debug('Fetching articles for {0}'.format(feed['name'].encode('utf-8')))
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
                    t = threading.Thread(target = self.__fetch_remote_image, 
                                    args=(self.images_path, i, article, ))
                    t.start()
                feed['articles'].append(article)
        self.log.debug("[Feed] {0} fetched".format(feed['name'].encode('utf-8')))
        self.result = feed
    def __find_images_in_article(self, content):
        """Searches for img tags in article content."""
        images = []
        rgxp = '''<img\s+[^>]*?src=["']?([^"'>]+)[^>]*?>'''
        m = re.findall(rgxp, content, re.I)
        for img in m:
            images.append(img)
        return images
    def __fetch_remote_image(self, path, src, article):
        """Get a article image and write it to a local file."""
        time.sleep(30)##debug##
        if not os.path.exists(path):
            os.makedirs(path)
        name = make_uuid(src, False) # images with the same url get the same name
        image = os.path.join(path,name)
        if os.path.exists(image) and os.path.getsize(image) > 0: # we already have it, don't re-download
            return {'name':name, 'url':src, 'article_id':article['id']}
        try:
            web_file = urllib2.urlopen(src, timeout=10)
            local_file = open(image, 'w')
            local_file.write(web_file.read())
            local_file.close()
            web_file.close()
            article['mages'].append({'name':name, 'url':src, 'article_id':article['id']})
        except Exception, e:
            print(e)
        #if the file is empty, remove it
        if os.path.exists(image) and not os.path.getsize(image):
            os.unlink(image)
    def __fetch_remote_favicon(self, path, f, feed):
        """Find and download remote favicon for a feed."""
        time.sleep(30)##debug##
        if not os.path.exists(path):
            os.makedirs(path)
        fav = os.path.join(path,feed['id'])
        if os.path.exists(fav) and os.path.getsize(fav) > 0: # we already have it, don't re-download
            self.log.debug("Favicon available for {0}".format(feed['name']))
            return True 
        #try The naufrago way
        try:
            split = feed['url'].split("/")
            src = split[0] + '//' + split[1] + split[2] + '/favicon.ico'
            self.log.debug("Trying {0}".format(src))
            webfile = urllib2.urlopen(src, timeout=10)
            local_file = open(fav, 'w')
            local_file.write(webfile.read())
            local_file.close()
            webfile.close()
            print("Favicon found for {0}".format(feed['name']))
        except Exception, e:
            print(e)
            #alternate method
            url = f.feed['link']
            try:
                # grab some html
                tmp = html5lib.parse(urllib2.urlopen(url).read())
                rgxp = '''http.*?favicon\.ico'''
                m = re.findall(rgxp, tmp.toxml(), re.I)
                if m:
                    print("Trying {0}".format(m[0]))
                    webfile = urllib2.urlopen(m[0], timeout=10)
                    local_file = open(fav, 'w')
                    local_file.write(webfile.read())
                    local_file.close()
                    webfile.close()
                    print("Favicon found for {0}".format(feed['name']))
                else:
                    print("No favicon available for {0}".format(feed['name']))
            except Exception, e:
                print(e) 
        #if the file is empty, remove it
        if os.path.exists(fav) and not os.path.getsize(fav):
            os.unlink(fav)

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
            'timestamp':secs, 
            'title':title, 
            'content':content, 
            'url':link, 
            'id': uid, 
            'ghost': gmap.get(content) or 0,
            }
        self.log.debug('Found a new article: {0}'.format(article['id']))
        return article
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
                self.__update_feeds([item], self.__otf)
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
        if bool(self.__hide_read) == True:
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

    @dbus.service.method('com.itgears.BRss.Engine', out_signature='a{sv}')
    def get_configs(self):
        q = 'SELECT key,value FROM config'
        cursor = self.conn.cursor()
        cursor.execute(q)
        rows = cursor.fetchall()
        cursor.close()
        confs = {}
        for r in rows:
            try:
                confs[r[0]] = int(r[1])
            except:
                confs[r[0]] = r[1]
        return confs

    @dbus.service.method('com.itgears.BRss.Engine', in_signature='a{sv}')
    def set_configs(self, confs):
        for k,v in confs.iteritems():
            self.__set_config(k,v)
        self.notice('info', 'Configuration updated')
        self.log.debug(confs)
        # apply configs
        self.__auto_update = bool(confs.get('auto-update'))
        self.__set_polling(int(confs.get('interval')))
        self.__max_entries = int(confs.get('max'))
        self.__show_notif = bool(confs.get('notify'))
        self.__otf = bool(confs.get('otf'))
        self.log.enable_debug(confs.get('debug'))

        
    @dbus.service.method('com.itgears.BRss.Engine')
    def export_opml(self, filename):
        """Export feeds and categories to an OPML file."""
        opml = open(os.path.abspath(filename), 'w')
        opml.writelines('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n')
        opml.writelines('<opml version="1.0">\n')
        opml.writelines('\t<title>BRss Feed List</title>\n')
        opml.writelines('\t<head></head>\n')
        opml.writelines('\t<body>\n')
        cats = self.__get_all_categories()
        for c in cats:
            opml.writelines('\t\t<outline title="{0}" text="{0}" description="{0}" type="folder">\n'.format(
                c['name']))
            feeds = self.__get_feeds_for(c)
            for f in feeds:
                opml.writelines('\t\t\t<outline title="{0}" text="{0}" type="rss" xmlUrl="{1}"/>\n'.format(
                    f['name'].replace('&', '%26').encode('utf-8'),
                    f['url'].replace('&', '%26')))
            opml.writelines('\t\t</outline>\n')
        opml.writelines('\t</body>\n')
        opml.writelines('</opml>\n')
        opml.flush()
        opml.close()

    @dbus.service.method('com.itgears.BRss.Engine')
    def import_opml(self, filename):#FIXME: group calls
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
        self.__update_feeds(feeds, self.__otf) # on-the-fly policy
        self.notice('ok', 'Feeds imported!')
    
    @dbus.service.method('com.itgears.BRss.Engine', out_signature='aa{sv}')
    def search_for(self, string):
        """Search article contents for a string.
        returns a list of articles."""
        q = 'SELECT id,read,starred,title,date,url,feed_id FROM articles WHERE title LIKE "%{0}%" OR content LIKE "%{0}%"'.format(string)
        try:
            arts = self.__make_articles_list(q)
            if len(arts) > 0:
                self.notice('new', 'Found {0} articles matching "{1}"'.format(len(arts), string))
            else:    
                self.warning('Couldn\'t find any article matching "{0}"'.format(string))
            return arts
        except Exception, e:
            self.log.exception(e) 
            self.warning('Search for "{0}" failed!'.format(string))

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
        name = item.get('name') or item.get('id')
        self.log.debug("updated: [{0}] {1}".format(
            item['type'].capitalize(), 
            name.encode('utf-8')))

    @dbus.service.signal('com.itgears.BRss.Engine')
    def complete(self, c):
        self.notice('ok',"Updated {0} feed(s) | {1} new article(s)".format(c, self.__added_count))
        self.__notify_update(c, self.__added_count)

    @dbus.service.signal('com.itgears.BRss.Engine')
    def updating(self, c):
        self.notice('wait',"Updating {0} feed(s)".format(c))

    @dbus.service.signal('com.itgears.BRss.Engine', signature='a{sv}')
    def added(self, item):
        #TODO: This should also handle articles
        self.notice('added',"[{0}] {1} added".format(item['type'], item['name']))

    ## 6. Runners and stoppers
    @dbus.service.method('com.itgears.BRss.Engine')
    def start(self):
        Gtk.main()
        self.__update_all()

    @dbus.service.method('com.itgears.BRss.Engine')
    def exit(self):
        """Clean up and leave"""
        self.__clean_up()
        self.log.debug("Quitting {0}".format(self))
        Gtk.main_quit()
        return "Quitting"
    
    #### INTERNAL METHODS  ####
    def __repr__(self):
        return "BRssEngine"
    ## 1. initialization
    def __init__(self, base_path="."):
        self.base_path      = base_path
        self.favicon_path   = os.path.join(base_path, 'favicons')
        self.images_path    = os.path.join(base_path, 'images')
        self.db_path        = os.path.join(base_path, 'brss.db')
        self.conn           = sqlite3.connect(self.db_path, check_same_thread=False)
        self.log            = Logger(base_path, "brss-engine.log", "BRss-Engine")
        # check
        try:
            self.__get_all_categories()
        except Exception, e:
            self.log.warning("Could not find database; creating it")
            self.__init_database()
        self.__in_update        = False
        self.__last_update      = time.time()
        self.__update_interval  = self.__get_config('interval')
        self.__max_entries      = self.__get_config('max')
        self.__hide_read        = self.__get_config('hide-read')
        self.__show_notif       = self.__get_config('notify')
        self.__otf              = self.__get_config('otf')
        self.__auto_update      = self.__get_config('auto-update')
        self.__added_count      = 0
        self.log.enable_debug(self.__get_config('debug'))
        # d-bus
        bus_name = dbus.service.BusName('com.itgears.BRss.Engine', bus=dbus.SessionBus())
        dbus.service.Object.__init__(self, bus_name, '/com/itgears/BRss/Engine')
        self.__set_polling(self.__get_config('interval'))
        self.updater = GeneratorTask(
            self.__generator, 
            self.__loop_callback, 
            self.__loop_done)
        # ok, looks like we can start
        Notify.init('BRss')
        if self.__show_notif:
            self.__notify_startup()
        self.log.debug("Starting {0}".format(self))
        
    def __set_polling(self, interval):
        if self.__auto_update:
            if self.__update_interval != interval:
                self.log.debug("Timeout removed: {0}".format(GLib.source_remove(self.timeout_id)))
                self.__update_interval = interval
            self.timeout_id = GLib.timeout_add_seconds(
                    0, interval*60, self.__timed_update, None)
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
            assert self.__item_exists('articles', 'url', art['url']) == False
            cursor = self.conn.cursor()
            cursor.execute (
                'INSERT INTO articles VALUES(?, ?, ?, ?, ?, 0, 0, ?)', 
                [
                    art['id'].decode("utf-8"),
                    art['title'].decode("utf-8"),
                    art['content'].decode("utf-8"),
                    art['timestamp'],
                    art['url'].decode("utf-8"),
                    art['feed_id'],
                ]
            )
            self.conn.commit()
            cursor.close()
            #inser images
            cursor = self.conn.cursor()
            for img in art['images']:
                cursor.execute('INSERT INTO images VALUES(null, ?, ?, ?)', 
                    [img['name'],img['url'],img['article_id']])
            self.conn.commit()
            cursor.close()
            self.__added_count += 1
        except AssertionError:
            self.log.debug("article {0} already exists, skipping".format(art['id']))
    def __add_items_for(self, feed):
        if feed:
            try:
                articles = feed.pop('articles') # we don't need them here
            except KeyError:
                #~ self.notice('warning', '[Feed] {0} has no new articles, or we may be offline'.format(feed['name']))
                articles = None
            except Exception, e:
                self.log.warning("Error occured: {0}".format(e))
                
            feed['timestamp'] = time.time()
            if articles:
                feed['parse'] = 0
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
            #~ self.notice('info', "[Category] {0} edited".format(category['name'].encode('utf-8')))
        except AssertionError:
            self.warning("Category {0} doesn't exist, or is a duplicate! Aborting".format(category['name'].encode('utf-8')))
    def __edit_feed(self, feed):
        try:
            assert self.__item_exists('feeds', 'id', feed['id']) == True
            # we don't want duplicate feeds
            assert self.__item_exists('feeds', 'url', feed['url']) == True
            self.log.debug("Editing feed {0}".format(feed['id']))
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
            #~ self.notice('info', "[Feed] {0} edited".format(feed['name'].encode('utf-8')))
        except AssertionError:
            self.warning("[Feed] {0} doesn't exist, or is a duplicate! Aborting".format(feed['name'].encode('utf-8')))
    def __update_all(self):
        feeds = []
        categories = self.__get_all_categories()
        for c in categories:
            feeds.extend(self.__get_feeds_for(c))
        self.__update_feeds(feeds)
    def __update_category(self, category):
        feeds = self.__get_feeds_for(category)
        self.__update_feeds(feeds)    
    def __generator(self, flist, otf):
        self.log.debug("About to update {0} feed(s); otf: {1}".format(len(flist), otf))
        self.fcount = 0
        self.updating(len(flist))
        #~ in_q = Queue(3)
        #~ def yielder(q, c, a):
            #~ while c > 0:
                #~ thread = q.get(True)
                #~ thread.join()
                #~ a += 1
                #~ c -= 1
                #~ yield thread.get_result()
        for feed in flist:
            # let the UI know we're still busy
            name  = feed.get('name') or feed['url']
            self.notice("wait", "Updating [Feed] {0} ({1})".format(name.encode('utf-8'), self.fcount))
            f = FeedGetter(
                feed, 
                self.base_path, 
                self.__max_entries,
                self.__update_interval,
                otf,
                self.log, 
                )
            f.start()
            #~ in_q.put(f)
            # TODO: This is where you put it in the queue
            f.join()
            self.fcount += 1
            yield feed
        #~ yielder(in_q, len(flist), self.fcount)
    def __loop_callback(self, feed):
        if feed:
            self.notice("wait", "Updating [Feed] {0} ({1})".format(feed['name'].encode('utf-8'), self.fcount))
            self.__add_items_for(feed)
            self.__update_ended(feed)
        else:
            self.log.debug("Empty feed received")
    def __loop_done(self):
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
            self.notice('warning', "Category {0} deleted!".format(category['name'].encode('utf-8')))
        else:
            self.notice('warning', "All uncategorized feeds deleted!")
    def __delete_feed(self, feed):
        articles = self.get_articles_for(feed)
        if articles:
            for a in articles:
                self.__delete_article(a['id'])
        # now delete
        try:
            os.unlink(os.path.join(self.favicon_path,feed['id']))
        except Exception, e: # not there?
            self.log.exception(e) 
        q = 'DELETE FROM feeds WHERE id = "{0}"'.format(feed['id'])
        cursor = self.conn.cursor()        
        cursor.execute(q)
        self.conn.commit()
        cursor.close()    
        self.notice('warning', "[Feed] {0} deleted!".format(feed['name'].encode('utf-8')))
    def __delete_article(self, art_id):
        self.log.debug("Deleting article {0}".format(art_id))
        try:
            assert self.__item_exists('articles', 'id', art_id) == True
            # delete images first.
            q = 'SELECT name FROM images WHERE article_id = "{0}"'.format(art_id)
            cursor = self.conn.cursor()
            cursor.execute(q)
            rows = cursor.fetchall()
            if (rows is not None) and (len(rows)>0):
                for i in rows:
                    filename = os.path.join(self.images_path,i[0])
                    self.log.debug("Deleting image: {0}".format(filename))
                    try:
                        os.unlink(filename)
                    except Exception, e: 
                        self.log.exception(e) 

            # now remove image entries in DB
            q = 'DELETE FROM images WHERE article_id = "{0}"'.format(art_id)
            cursor.execute(q)
            self.conn.commit()
            # now delete article
            q = 'DELETE FROM articles WHERE id = "{0}"'.format(art_id)
            cursor.execute(q)
            self.conn.commit()
            cursor.close()        
        except AssertionError:
            self.log.debug("Article {0} doesn't exist or could not be deleted".format(art_id))

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
        if atotal > self.__max_entries:
            self.log.debug("Cropping feed {0} to the latest {1} unread articles".format(
                    feed['name'].encode('utf-8'),
                    self.__max_entries))            
            # 1. if we have more unread than max_entries, no need to keep the read
            if utotal > self.__max_entries:
                self.log.debug("Deleting all read articles")
                for r in rrows:
                    self.__delete_article(r[0])
                # now delete the excess
                diff = atotal - rtotal - self.__max_entries # the number of unread articles to delete
                self.log.debug("Deleting {0} excess unread articles".format(diff))
                for u in urows:
                    if diff > 0:
                        self.__delete_article(u[0])
                        diff -= 1
            # 2. not that many unread, so remove the excess read
            else:
                diff = atotal - self.__max_entries # the number of read articles to delete
                self.log.debug("Deleting {0} excess read articles".format(diff))
                for r in rrows:
                    if diff > 0:
                        self.__delete_article(r[0])
                        diff -= 1

    def __update_ended(self, feed):
        if feed:
            #~ a = self.__count_articles(feed)
            #~ u = self.__count_unread_articles(feed)
            self.updated(feed)
            #~ self.notice('wait', "{0} updated | {1} articles | {2} unread".format(
                        #~ feed['name'], 
                        #~ a, 
                        #~ u))
        
    def __timed_update(self, *args):
        self.log.debug("About to auto-update")
        interval = self.__update_interval*60
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
        print q
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
        cursor.execute('SELECT name,url FROM images WHERE article_id = ?', [article['id']])
        row = cursor.fetchall()
        if (row is not None) and (len(row)>0):
            for img in row:
                t = 'file://' + os.path.join(self.images_path, str(img[0]))
                article['content'] = article['content'].replace(
                        img[1], t)
                links.append(t)
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
            CREATE TABLE config(key varchar(32) PRIMARY KEY, value varchar(256) NOT NULL);
            CREATE TABLE categories(id varchar(256) PRIMARY KEY, name varchar(32) NOT NULL);
            CREATE TABLE feeds(id varchar(256) PRIMARY KEY, name varchar(32) NOT NULL, url varchar(1024) NOT NULL, category_id integer NOT NULL, timestamp integer NOT NULL, parse INTEGER NOT NULL);
            CREATE TABLE articles(id varchar(256) PRIMARY KEY, title varchar(256) NOT NULL, content text, date integer NOT NULL, url varchar(1024) NOT NULL, read INTEGER NOT NULL, starred INTEGER NOT NULL, feed_id integer NOT NULL);
            CREATE TABLE images(id integer PRIMARY KEY, name varchar(256) NOT NULL, url TEXT NOT NULL, article_id varchar(256) NOT NULL);
            INSERT INTO config VALUES('max', '10');
            INSERT INTO config VALUES('interval', '60');
            INSERT INTO config VALUES('hide-read', '0');
            INSERT INTO config VALUES('otf', '0');
            INSERT INTO config VALUES('notify', '0');
            INSERT INTO config VALUES('auto-update', '1');
            INSERT INTO config VALUES('debug', '0');
            INSERT INTO categories VALUES('uncategorized', 'Uncategorized');
            ''')
        self.conn.commit()
        cursor.close()
        
    def __notify_startup(self):
        """Send an startup notification with libnotify"""
        if not self.__show_notif:
            self.log.debug("Startup Notification suppressed")
        else:
            n = Notify.Notification.new(
                "BRss started",
                "BRss Feed Engine is running",
                make_path('icons', 'brss.svg'))
            n.show()

    def __notify_update(self, c, ac):
        if not self.__show_notif:
            self.log.debug("Update Notification suppressed")
        else:
            n = Notify.Notification.new(
                "BRss: Update report",
                "Updated {0} feeds\n{1} new article(s)\n{2} unread article(s)".format(
                    c, ac, self.__count_unread_articles()),
                make_path('icons', 'brss.svg'))
            n.show()

    def __get_config(self, key):
        q = 'SELECT value FROM config WHERE key = "{0}"'.format(key)
        cursor = self.conn.cursor()
        cursor.execute(q)
        row = cursor.fetchone()
        cursor.close()
        if row:
            try:
                return int(row[0])
            except ValueError:
                return row[0]
        return False
    
    def __set_config(self, key, value):
        q = 'UPDATE config SET value = {0} WHERE key = "{1}"'.format(value, key)
        cursor = self.conn.cursor()
        cursor.execute(q)
        self.conn.commit()
        cursor.close()
