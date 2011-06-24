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
from gi.repository import Gtk
from gi.repository import GObject
import time
import datetime
import sqlite3
import feedparser
import htmlentitydefs
import hashlib
import urllib2
import threading
import os
import hashlib
import re
import html5lib
import dbus
import dbus.service
import dbus.mainloop.glib
from xml.etree import ElementTree

def make_time():
    split = str(datetime.datetime.now()).split(' ')
    ds = split[0].split('-')
    ts = split[1].split(':')
    t = datetime.datetime(int(ds[0]), int(ds[1]), int(ds[2]), int(ts[0]), int(ts[1]), int(float(ts[2])))
    return time.mktime(t.timetuple())

def make_uuid(data="fast random string", add_time=True):
    if add_time:#make it REALLY unique
        data = str(make_time())+str(data)
    return hashlib.md5(data).hexdigest().encode("utf-8")

class Engine (dbus.service.Object):
    """ The feedengine handles web and database calls."""
    
    ## PUBLIC METHODS
    @dbus.service.method('org.itgears.brss',
                         in_signature='a{ss}')
    def add_category(self, category):
        try:
            assert self.__item_exists('categories', 'name', category['name']) == False
            category['name'] = category['name'].encode('utf-8')
            category['id'] = make_uuid(category['name'])
            self.__insert_category(category)
            self.notice('added', "New category added: {0}".format(category['name']))
        except AssertionError:
            self.warning("error", 'Category already exists!')

    @dbus.service.method('org.itgears.brss',
                         in_signature='a{ss}')
    def edit(self, item):
        if item and item.has_key('type'):
            if item['type'] == 'feed':
                self.__edit_feed(item)
            elif item['type'] == 'category':
                self.__edit_category(item)
    
    @dbus.service.method('org.itgears.brss')
    def import_opml(self, filename):
        f = open(os.path.abspath(filename), 'r')
        tree = ElementTree.parse(f)
        current_category = '1'
        cursor = self.conn.cursor()
        for node in tree.getiterator('outline'):
            name = node.attrib.get('text').replace('[','(').replace(']',')')
            url = node.attrib.get('xmlUrl')
            if url: # isolate feed
                self.add_feed({'url':url, 'category':current_category})
            else: # category
                if len(node) is not 0:
                    self.add_category({'name':name})
                    current_category = self.__get_category(name)['id']
        self.notice('added', 'Feeds imported!')
    
    @dbus.service.method('org.itgears.brss', out_signature='aa{ss}')
    def get_menu_items(self):
        menu = [] 
        cat = self.__get_all_categories()
        for c in cat:
            feeds = self.__get_feeds_for(c['id']) or []
            for f in feeds:
                c['count'] = str(int(c['count'])+int(f['count']))
            menu.append(c)
            if feeds:
                menu.extend(feeds)
        return menu
                
        
    @dbus.service.method('org.itgears.brss',
                            in_signature='a{ss}', out_signature='aa{ss}')
    def get_feeds_for(self, category):
        
        feeds = self.__get_feeds_for(category['id'])
        return feeds

    @dbus.service.method('org.itgears.brss', in_signature='a{ss}')
    def add_feed(self, feed):
        try:
            assert self.__item_exists('feeds', 'url', feed['url']) == False
            rfeed = self.__add_feed(feed)
            self.notice('added', "New feed added: {0}".format(feed['name']))            
        except AssertionError:
            self.warning("error", 'Feed already exists!')
    
    
    @dbus.service.method('org.itgears.brss', out_signature='aa{ss}')
    def search_for(self, string):
        q = 'SELECT id,read,starred,title,date,url,feed_id FROM articles WHERE title LIKE "%{0}%" OR content LIKE "%{0}%"'.format(string)
        try:
            arts = self.__make_articles_list(q)
            if len(arts) > 0:
                self.notice('new', 'Found {0} articles matching "{1}"'.format(len(arts), string))
            else:    
                self.notice('warning', 'Couldn\'t find any article matching "{0}"'.format(string))
            return arts
        except Exception, e:
            self.warning('warning', 'Search for "{0}" failed!'.format(string))
            raise e

    @dbus.service.method('org.itgears.brss')
    def update(self, item=None):
        if item == 'all': 
            t, u, s = self.__update_all()
            self.notice('new', "Feeds updated! (total:{0}, unread:{1}, starred:{2})".format(t, u, s))
            return
        elif item and item.has_key('type') and item['type'] in ['feed', 'category']:
            if item['type'] == 'feed':
                feed = self.__get_feed(item['id'])
                t, u, s = self.__update_feed(feed)
            elif item['type'] == 'category':
                t, u, s = self.__update_category(item)
            self.notice('new', "[{0}] {1} updated! (total:{2}, unread:{3}, starred:{4})".format(
                        item['type'].capitalize(), item['name'].encode('utf-8'), 
                            t, u, s))
        else:
            self.notice('new', "Nothing to update")
    
    @dbus.service.method('org.itgears.brss')
    def delete(self, item=None):
        if not item:
            return
        if item and item.has_key('type') and item['type'] in ['feed', 'category']:
            if item['type'] == 'feed':
                feed = self.__get_feed(item['id'])
                self.__delete_feed(feed)
            elif item['type'] == 'category':
                self.__delete_category(item)
            self.notice('warning', "[{0}] {1} deleted!".format(
                        item['type'].capitalize(), item['name'].encode('utf-8')))
        else:
            self.notice('new', "Nothing to do")
        
    @dbus.service.method('org.itgears.brss', in_signature='a{ss}', 
                        out_signature='aa{ss}')
    def get_articles_for(self, item):
        if item and item.has_key('type'):
            if item['type'] == 'feed':
                query = 'SELECT id,read,starred,title,date,url,feed_id FROM articles WHERE feed_id = "'+item['id']+'" ORDER BY date DESC'
                return self.__make_articles_list(query)
            if item['type'] == 'category':
                # recurse
                feeds = self.__get_feeds_for(item['id'])
                articles = []
                for f in feeds:
                    query = 'SELECT id,read,starred,title,date,url,feed_id FROM articles WHERE feed_id = "'+f['id']+'" ORDER BY date DESC'
                    articles.extend(self.__make_articles_list(query))
                return articles
            # special cases
            if item['type'] == 'unread':
                return self.__get_unread_articles()
            if item['type'] == 'starred':
                return self.__get_starred_articles()
                
    @dbus.service.method('org.itgears.brss', in_signature='a{ss}',
                        out_signature='(a{ss}as)')
    def get_article(self, item):
        article = self.__get_article(item['id'])
        # check policy first
        return self.__swap_image_tags(article)
    
    @dbus.service.method('org.itgears.brss', in_signature='a{ss}')
    def toggle_starred(self, item):
        self.__toggle_article('starred', item)
    @dbus.service.method('org.itgears.brss', in_signature='a{ss}')
    def toggle_read(self, item):
        self.__toggle_article('read', item)
    
    @dbus.service.method('org.itgears.brss')
    def count_unread(self):
        return self.__count_unread_items()
    
    @dbus.service.method('org.itgears.brss')
    def count_starred(self):
        return self.__count_starred_items()
    
    @dbus.service.signal('org.itgears.brss', signature='ss')
    def warning (self, wtype, message):
        print '{0}: {1}'.format(wtype, message)
    
    @dbus.service.signal('org.itgears.brss', signature='ss')
    def notice (self, wtype, message):
        print '{0}: {1}'.format(wtype, str(message))
    
    ## INTERNAL METHODS
    def __init__(self, base_path="."):
        self.db_path = os.path.abspath(os.path.join(base_path, 'feed.db'))
        self.favicon_path = os.path.abspath(os.path.join(base_path, 'favicons'))
        self.images_path = os.path.abspath(os.path.join(base_path, 'images'))
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        # check
        try:
            self.__get_all_categories()
        except Exception, e:
            print e
            self.__create_database()
        self.max_entries = 10;
        # d-bus
        bus_name = dbus.service.BusName('org.itgears.brss', bus=dbus.SessionBus())
        dbus.service.Object.__init__(self, bus_name, '/org/itgears/brss/Engine')
    
    def __toggle_article(self, col, item):
        # get original state
        q = 'UPDATE articles set {0} = {1} WHERE id = "{2}"'.format(col, item[col], item['id'])
        cursor = self.conn.cursor()
        cursor.execute(q)
        self.conn.commit()
        cursor.close()
        

    def __edit_feed(self, feed):
        try:
            assert self.__feed_exists(feed)
            old_feed = self.__get_feed(feed['id'])
            # update the feed
        except AssertionError:
            self.warning("error", 'Feed does not exist!')

    def __update_all(self):
        total = unread = starred = 0
        categories = self.__get_all_categories()
        for c in categories:
            t, u, s = self.__update_category(c)
            total += t
            unread += u
            starred += s
        return total, unread, starred
    
    def __update_category(self, category):
        total = unread = starred = 0
        feeds = self.__get_feeds_for(category['id'])
        for f in feeds:
            t, u, s = self.__update_feed(f)
            total += t
            unread += u
            starred += s
        return total, unread, starred
    
    def __delete_category(self, category):
        feeds = self.__get_feeds_for(category['id'])
        for f in feeds:
            self.__delete_feed(f)
        q = 'DELETE FROM categories WHERE id = "{0}"'.format(category['id'])
        cursor = self.conn.cursor()        
        cursor.execute(q)
        self.conn.commit()
        cursor.close()
        
    def __fetch_feed_and_items(self, feed, f=None):
        # this should run in a thread
        if not f:
            f = feedparser.parse(feed['url'])
        # update basic feed informations
        bozo_invalid = ['urlopen', 'Document is empty'] # Custom non-wanted bozos
        if hasattr(f.feed, 'link'):
            self.__fetch_remote_favicon(f.feed.link, feed)
        if not hasattr(f, 'entries'):
            print "No entries found"
            return False
        feed['fetched_count'] = limit  = len(f.entries)
        if feed['fetched_count'] > self.max_entries:
            limit = self.max_entries
        if hasattr(f,'bozo_exception'): # Feed HAS a bozo exception...
            for item in bozo_invalid:
                if item in str(f.bozo_exception):
                    return False
        #get articles
        feed['articles'] = []
        print "adding articles ----- "
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
                    local_image = self.__fetch_remote_image(i, article['id'])
                    if local_image:
                        article['images'].append(local_image)
                feed['articles'].append(article)
        return feed
        
    def __update_feed(self, feed):
        time.sleep(10)
        total = unread = starred = 0
        feed = self.__fetch_feed_and_items(feed)
        if feed:
            return self.__insert_items_for(feed)
        return 0, 0, 0
        
    def __insert_items_for(self, feed):
        cursor = self.conn.cursor()
        # verify that feed has (ever had) entries
        cursor.execute('SELECT count(id) FROM articles WHERE feed_id = ?', [feed['id']])
        c = cursor.fetchone()[0]
        if feed['fetched_count'] == 0 and c == 0: # ... and never had! Fingerprinted as invalid!
            return False
        q = 'UPDATE feeds SET name = "{0}" WHERE id = "{1}"'.format(feed['name'],feed['id'])
        cursor.execute(q)
        self.conn.commit()
        cursor.close()
        for art in feed['articles']:
            self.__insert_article(art)
        return self.__clean_up_feed(feed) # returns (total, unread, starred)
    
    def __delete_feed(self, feed):
        articles = self.get_articles_for(feed)
        if articles:
            for a in articles:
                self.__delete_article(a['id'])
        # now delete
        try:
            os.unlink(os.path.join(self.favicon_path,feed['id']))
        except: # not there?
            pass
        q = 'DELETE FROM feeds WHERE id = "{0}"'.format(feed['id'])
        cursor = self.conn.cursor()        
        cursor.execute(q)
        self.conn.commit()
        cursor.close()
    
    def __delete_article(self, art_id):
        # delete images first.
        cursor = self.conn.cursor()
        cursor.execute('SELECT name FROM images WHERE article_id = ?', [art_id])
        rows = cursor.fetchall()
        if (rows is not None) and (len(rows)>0):
            for i in rows:
                filename = os.path.abspath(os.path.join(self.images_path,i[0]))
                print "Deleting ", filename
                try:
                    os.unlink(filename)
                except: pass #already gone?
        # now remove image entries in DB
        cursor.execute('DELETE FROM images WHERE article_id = ?', [art_id])
        self.conn.commit()
        # now delete article
        cursor.execute('DELETE FROM articles WHERE id = ?', [art_id])
        self.conn.commit()
        cursor.close()
            
    def __clean_up_feed(self, feed):
        """
        This is where old feeds are removed.
        We only keep the last `max_entries` articles.
        """
        q = 'SELECT id FROM articles WHERE feed_id = "{0}" ORDER BY date DESC'.format(feed['id'])
        cursor = self.conn.cursor()
        cursor.execute(q)
        rows = cursor.fetchall()
        cursor.close()
        total = len(rows)
        if total > self.max_entries:
            i = 0
            while i <= total:
                if i > self.max_entries:
                    self.__delete_article(rows[i])
                i += 1                    
        return (0, self.__count_unread_items(feed), self.__count_starred_items(feed))
    

    def __count_unread_items(self, feed=None):
        if feed:
            q = 'SELECT COUNT(id) FROM articles WHERE feed_id = "{0}" AND read = 0'.format(feed['id'])
        else:
            q = 'SELECT COUNT(id) FROM articles WHERE read = 0'
        cursor = self.conn.cursor()
        cursor.execute(q)
        c = cursor.fetchone()
        return c[0]

    def __count_starred_items(self, feed=None):
        if feed:
            q = 'SELECT COUNT(id) FROM articles WHERE feed_id = "{0}" AND starred = 1'.format(feed['id'])
        else:
            q = 'SELECT COUNT(id) FROM articles WHERE starred = 1'
        cursor = self.conn.cursor()
        cursor.execute(q)
        c = cursor.fetchone()
        return c[0]
        
    def __get_unread_articles(self):
        articles = []
        query = 'SELECT id,read,starred,title,date,url,feed_id FROM articles WHERE read = 0 ORDER BY date DESC'
        # run query
        return self.__make_articles_list(query)

    def __get_starred_articles(self):
        articles = []
        query = 'SELECT id,read,starred,title,date,url,feed_id FROM articles WHERE starred = 1 ORDER BY date DESC'
        # run query
        return self.__make_articles_list(query)
        
    def __get_feed(self, feed_id):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM feeds WHERE id = ?', [feed_id])
        row = cursor.fetchone()
        cursor.close()
        return {'id': row[0], 'name':row[1], 'url':row[2], 'category':row[3]}

    def __get_category(self, name):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM categories WHERE name = ?', [name])
        row = cursor.fetchone()
        cursor.close()
        return {'id': row[0], 'name':row[1]}
    
    def __get_all_categories(self):
        cat = []
        cursor = self.conn.cursor()
        cursor.execute('SELECT id,name FROM categories ORDER BY name ASC')
        rows = cursor.fetchall()
        for r in rows:
            cat.append({'type':'category','id': r[0], 'name':r[1], 'count':'0'},)
        cursor.close()
        return cat
    
    def __get_feeds_for(self, cid):
        feeds = []
        q = 'SELECT id,name,url, category_id FROM feeds WHERE category_id = "{0}" ORDER BY name ASC'.format(cid)
        cursor = self.conn.cursor()
        cursor.execute(q)
        rows = cursor.fetchall()
        for r in rows:
            f = {'type':'feed', 'id': r[0], 'name':r[1].encode('utf-8'), 'url':r[2], 'category_id':str(r[3])}
            f['count'] = str(self.__count_unread_items(f))
            feeds.append(f)
        cursor.close()
        return feeds

    def __insert_category(self, category):
        try:
            assert self.__item_exists('categories', 'name', category['name']) == False
            cursor = self.conn.cursor()
            q = 'INSERT INTO categories VALUES("{0}", "{1}")'.format(category['id'], category['name'])
            cursor.execute(q)
            self.conn.commit()
            cursor.close()
            return self.__get_category(category['name'])
        except AssertionError, e:
            print "category {0} already exists, skipping".format(category['name'])

    def __add_feed(self, feed):
        f = feedparser.parse(feed['url'])
        # get title from feed
        if(hasattr(f.feed,'title')):
            feed['name'] = f.feed.title.encode('utf-8')
        else:
            feed['name'] = feed['url'].encode('utf-8')
        if not feed.has_key('category'):
            feed['category'] = '1'
        feed['id'] = make_uuid(feed['url'])
        self.__insert_feed(feed)
        feed = self.__fetch_feed_and_items(feed, f) # web
        if feed:
            return self.__update_feed(feed) # database
        
    def __insert_feed(self, feed):
        try:
            assert self.__item_exists('feeds', 'id', feed['id']) == False
            q = 'INSERT INTO feeds VALUES("{0}", "{1}", "{2}", "{3}")'.format(
                feed['id'], feed['name'], feed['url'], feed['category'])
            cursor = self.conn.cursor()
            cursor.execute(q)
            self.conn.commit()
            cursor.close()
        except AssertionError, e:
            print "feed {0} already exists, skipping".format(feed['name'])
            
    def __find_images_in_article(self, content):
        """
        Searches for img tags in order to identify feed body images. It also checks 
        paths to make sure all are absolute (if not, it tries to). 
        """
        images = []
        rgxp = '''<img\s+[^>]*?src=["']?([^"'>]+)[^>]*?>'''
        m = re.findall(rgxp, content, re.I)
        for img in m:
            images.append(img)
        return images

    def __fetch_remote_images_for(self, article):
        """
        Manages entry images. It discards downloading images that are already on the
        database to save space and bandwidth per URL basis.
        """
        if not os.path.exists(self.images_path):
            os.makedirs(self.images_path)
        cursor = self.conn.cursor()
        for i in article['images']:
            cursor.execute('SELECT name FROM images WHERE url = ?', [i])
            row = cursor.fetchone()
            # not found, download
            if row is None:
                name = self.__get_remote_image(i)
                if name:
                    # add to db only AFTER we successfully retrive the image
                    cursor.execute('INSERT INTO images VALUES(null, ?, ?, ?)', [name,i,article['id']])
                    self.conn.commit()
            # found
            else:
                cursor.execute('INSERT INTO images VALUES(null, ?, ?, ?)', [row[0],i,article['id']])
                self.conn.commit()
        cursor.close()
    
    def __fetch_remote_image(self, src, article_id):
        if not os.path.exists(self.images_path):
            os.makedirs(self.images_path)
        name = make_uuid(src, False) # images with the same url get the same name
        image = os.path.join(self.images_path,name)
        if os.path.exists(image): # we already have it, don't re-download
            return {'name':name, 'url':src, 'article_id':article_id}
        try:
            web_file = urllib2.urlopen(src, timeout=10)
            local_file = open(image, 'w')
            local_file.write(web_file.read())
            local_file.close()
            web_file.close()
            return {'name':name, 'url':src, 'article_id':article_id}
        except Exception, e:
            print "Couldn't get remote file: ", e  
    
    def __fetch_remote_favicon(self, url, feed):
        if not os.path.exists(self.favicon_path):
            os.makedirs(self.favicon_path)
        fav = os.path.join(self.favicon_path,feed['id'])
        if os.path.exists(fav): # we already have it, don't re-download
            print "favicon available for {0}".format(feed['name'])
            return True 
        try:
            # grab some html
            tmp = html5lib.parse(urllib2.urlopen(url))
            rgxp = '''http.*?favicon\.ico'''
            m = re.findall(rgxp, tmp.toxml(), re.I)
            if m:
                webfile = urllib2.urlopen(m[0])
                local_file = open(fav, 'w')
                local_file.write(webfile.read())
                local_file.close()
                webfile.close()
                print "favicon found for {0}".format(feed['name'])
            else:
                print "No favicon available for {0}".format(feed['name'])
        except Exception, e:
            print "Couldn't get favicon for {0}: {1}".format(feed['name'], e)  

    def __get_article(self, id):
        q = 'SELECT id,title,date,url,content FROM articles WHERE id = "{0}"'.format(id)
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
                }

    def __swap_image_tags(self, article):
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
        """Convenience function."""
        articles = []
        cursor = self.conn.cursor()
        cursor.execute(q)
        rows = cursor.fetchall()
        cursor.close()
        for r in rows:
            articles.append(
                {
                    'id':str(r[0]), 
                    'read':str(r[1]), 
                    'starred':str(r[2]),
                    'title':r[3], 
                    'date':str(r[4]), 
                    'url':r[5], 
                    'feed_id':str(r[6]), 
                }
            )
        return articles

    def __insert_article(self, art):
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
        except AssertionError, e:
            print "article {0} already exists, skipping".format(art['id'])
        
    def __check_feed_item(self, feed_item):
        """Sets a default value for feed items if there's not any."""
        gmap = {'no-content':1}
        try:
            dp = feed_item.date_parsed
            secs = time.mktime(datetime.datetime(dp[0], dp[1], dp[2], dp[3], dp[4], dp[5], dp[6]).timetuple())
        except:
            secs = make_time()
        
        title = 'Without title'
        if hasattr(feed_item,'title'):
            if feed_item.title is not None: title = feed_item.title.encode("utf-8")
            else: title = 'Without title'

        content = 'no-content'        
        if hasattr(feed_item,'content'):
            try:
                content = feed_item.content[0].get('value').encode("utf-8")
            except:
                pass
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
        return {
            'timestamp':secs, 
            'title':title, 
            'content':content, 
            'url':link, 
            'id': uid, 
            'ghost': gmap.get(content) or 0,
            }    
    
    def __create_database(self):
        cursor = self.conn.cursor()
        cursor.executescript('''
            CREATE TABLE categories(id varchar(256) PRIMARY KEY, name varchar(32) NOT NULL);
            CREATE TABLE feeds(id varchar(256) PRIMARY KEY, name varchar(32) NOT NULL, url varchar(1024) NOT NULL, category_id integer NOT NULL);
            CREATE TABLE articles(id varchar(256) PRIMARY KEY, title varchar(256) NOT NULL, content text, date integer NOT NULL, url varchar(1024) NOT NULL, read INTEGER NOT NULL, starred INTEGER NOT NULL, feed_id integer NOT NULL);
            CREATE TABLE images(id integer PRIMARY KEY, name varchar(256) NOT NULL, url TEXT NOT NULL, article_id varchar(256) NOT NULL);
            INSERT INTO categories VALUES('1', 'General');
            ''')
        self.conn.commit()
        cursor.close()


    def __clean_up(self):
        pass

    def __item_exists(self, table, key, value):
        q = 'SELECT id FROM {0} WHERE {1} = "{2}"'.format(table, key, value)
        cursor = self.conn.cursor()
        cursor.execute(q)
        row = cursor.fetchone()
        cursor.close()
        if row:
            return True
        return False

    def run(self):
        Gtk.main()

    @dbus.service.method('org.itgears.brss')
    def exit(self):
        """Clean up and leave"""
        self.__clean_up()
        Gtk.main_quit()
        return "Quitting"
    
if __name__ == '__main__':
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    session_bus = dbus.SessionBus()
    # initiate engine
    #~ engine = Engine(".", True)
    engine = Engine(base_path=".")
    engine.run()
