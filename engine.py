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
import dbus
import dbus.service
import dbus.mainloop.glib
from xml.etree import ElementTree

def make_time(string=False):
    split = str(datetime.datetime.now()).split(' ')
    ds = split[0].split('-')
    ts = split[1].split(':')
    t = datetime.datetime(int(ds[0]), int(ds[1]), int(ds[2]), int(ts[0]), int(ts[1]), int(float(ts[2])))
    if string:
        return str(time.mktime(t.timetuple()))
    return time.mktime(t.timetuple())

def make_uuid(data="fast random string"):
    return hashlib.md5(str(make_time())+str(data)).hexdigest().encode("utf-8")

class Engine (dbus.service.Object):
    """ The feedengine handles web and database calls."""
    
    ## PUBLIC METHODS
    @dbus.service.method('org.itgears.brss',
                         in_signature='a{ss}')
    def add_category(self, category):
        try:
            assert self.__category_exists(category['name']) == False
            category['name'] = category['name'].encode('utf-8')
            self.__add_category(category)
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
    
    @dbus.service.method('org.itgears.brss',
                            in_signature='', out_signature='aa{ss}')
    def get_categories(self):
        cat = self.__get_all_categories()
        return cat
        
    @dbus.service.method('org.itgears.brss',
                            in_signature='a{ss}', out_signature='aa{ss}')
    def get_feeds_for(self, category):
        
        feeds = self.__get_feeds_for(category['id'])
        return feeds

    @dbus.service.method('org.itgears.brss', in_signature='a{ss}')
    def add_feed(self, feed):
        try:
            assert self.__feed_exists(feed['url']) == False
            f = feedparser.parse(feed['url'])
            # get title from feed
            if(hasattr(f.feed,'title')):
                feed['title'] = f.feed.title.encode('utf-8')
            else:
                feed['title'] = feed['url'].encode('utf-8')
            if not feed.has_key('category'):
                feed['category'] = 1
            rfeed = self.__add_feed(feed)
            self.notice('added', "New feed added: {0}".format(feed['title']))
            # update feed while we're at it
            count = self.__update_feed(rfeed, f)
            
        except AssertionError:
            self.warning("error", 'Feed already exists!')
    
    
    @dbus.service.method('org.itgears.brss', out_signature='aa{ss}')
    def search_for(self, string):
        q = 'SELECT id,read,starred,title,date,link,feed_id FROM articles WHERE title LIKE "%{0}%" OR content LIKE "%{0}%" AND ghost=0'.format(string)
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
        gmap = {False:0}
        if item == 'all': 
            count = self.__update_all()
            self.notice('new', "Feeds updated! ({0})".format(count))
            return
        elif item and item.has_key('type') and item['type'] in ['feed', 'category']:
            if item['type'] == 'feed':
                feed = self.__get_feed(item['id'])
                count = self.__update_feed(feed)
            elif item['type'] == 'category':
                count = self.__update_category(item)
            self.notice('new', "[{0}] {1} updated! ({2})".format(
                        item['type'].capitalize(), item['name'].encode('utf-8'), 
                            gmap.get(count)))
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
                query = 'SELECT id,read,starred,title,date,link,feed_id FROM articles WHERE feed_id = "'+item['id']+'" AND ghost=0 ORDER BY date DESC'
                return self.__make_articles_list(query)
            if item['type'] == 'category':
                # recurse
                feeds = self.__get_feeds_for(item['id'])
                articles = []
                for f in feeds:
                    query = 'SELECT id,read,starred,title,date,link,feed_id FROM articles WHERE feed_id = "'+f['id']+'" AND ghost=0 ORDER BY date DESC'
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
            self.get_categories()
        except:
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
        

    def __edit_category(self, category):
        try:
            assert self.__category_exists(category)
            old_category = self.__get_category(category['name'])
            # update the category
        except AssertionError:
            self.warning("error", 'Category does not exist!')

    def __edit_feed(self, feed):
        try:
            assert self.__feed_exists(feed)
            old_feed = self.__get_feed(feed['id'])
            # update the feed
        except AssertionError:
            self.warning("error", 'Feed does not exist!')

    def __update_all(self):
        count = 0
        categories = self.__get_all_categories()
        for c in categories:
            count += self.__update_category(c)
        return count
    def __update_category(self, category):
        count = 0
        feeds = self.__get_feeds_for(category['id'])
        for f in feeds:
            count += self.__update_feed(f)
        return count
    
    def __delete_category(self, category):
        feeds = self.__get_feeds_for(category['id'])
        for f in feeds:
            self.__delete_feed(f)
        q = 'DELETE FROM categories WHERE id = "{0}"'.format(category['id'])
        cursor = self.conn.cursor()        
        cursor.execute(q)
        self.conn.commit()
        cursor.close()
        
    def __update_feed(self, feed, f=None):
        cursor = self.conn.cursor()
        if not f:
            f = feedparser.parse(feed['url'])
        # update basic feed informations
        dont_parse = False
        bozo_invalid = ['urlopen', 'Document is empty'] # Custom non-wanted bozos
        if not len(f.entries) > 0: # Feed has no entries...
            cursor.execute('SELECT count(id) FROM articles WHERE feed_id = ?', [feed['id']])
            feed['count'] = cursor.fetchone()[0]
            if feed['count'] == 0: # ... and never had! Fingerprinted as invalid!
                return False
        elif hasattr(f,'bozo_exception'): # Feed HAS a bozo exception...
            for item in bozo_invalid:
                if item in str(f.bozo_exception):
                    return False
        q = 'UPDATE feeds SET name = "{0}" WHERE id = "{1}"'.format(f.feed.title.encode('utf-8'),feed['id'])
        cursor.execute(q)
        self.conn.commit()
        cursor.close()
        self.__insert_articles_for(feed, f)
        self.__clean_up_feed(feed)
        return self.__count_unread_items(feed)
    
    def __delete_feed(self, feed):
        articles = self.get_articles_for(feed)
        if articles:
            for a in articles:
                self.__delete_article(a)
        # now delete
        q = 'DELETE FROM feeds WHERE id = "{0}"'.format(feed['id'])
        cursor = self.conn.cursor()        
        cursor.execute(q)
        self.conn.commit()
        cursor.close()
    
    def __delete_article(self, art):
        # delete images first.
        cursor = self.conn.cursor()
        cursor.execute('SELECT name FROM images WHERE article_id = ?', [article['id']])
        rows = cursor.fetchall()
        if (rows is not None) and (len(rows)>0):
            for i in rows:
                filename = os.path.abspath(os.path.join(self.images_path,i[0]))
                print "Deleting ", filename
                try:
                    os.unlink(filename)
                except: pass #already gone?
        # now remove image entries in DB
        cursor.execute('DELETE FROM images WHERE article_id = ?', [article['id']])
        self.conn.commit()
        # now delete article
        cursor.execute('DELETE FROM articles WHERE id = ?', [article['id']])
        self.conn.commit()
        cursor.close()
            
    def __clean_up_feed(self, feed):
        pass
            
    
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
        query = 'SELECT id,read,starred,title,date,link,feed_id FROM articles WHERE read = 0 ORDER BY date DESC'
        # run query
        return self.__make_articles_list(query)

    def __get_starred_articles(self):
        articles = []
        query = 'SELECT id,read,starred,title,date,link,feed_id FROM articles WHERE starred = 1 ORDER BY date DESC'
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
            cat.append({'id': str(r[0]), 'name':r[1]},)
        cursor.close()
        return cat
    
    def __get_feeds_for(self, id):
        feeds = []
        cursor = self.conn.cursor()
        cursor.execute('SELECT id,name,url FROM feeds WHERE category_id = ' + id.decode('utf-8') + ' ORDER BY name ASC')
        rows = cursor.fetchall()
        for r in rows:
            f = {'id': str(r[0]), 'name':r[1], 'url':r[2]}
            f['count'] = str(self.__count_unread_items(f))
            feeds.append(f)
        cursor.close()
        return feeds

    def __add_category(self, category):
        cursor = self.conn.cursor()
        q = 'INSERT INTO categories VALUES(null, "{0}")'.format(category['name'])
        cursor.execute(q)
        self.conn.commit()
        cursor.close()
        return self.__get_category(category['name'])

    def __add_feed(self, feed):
        id = hashlib.md5(feed['url']).hexdigest().encode("utf-8")
        #~ q = 'INSERT INTO feeds VALUES(?, ?, ?, ?)', [id.decode('utf-8'), feed['title'],feed['url'], 1]
        q = 'INSERT INTO feeds VALUES("{0}", "{1}", "{2}", "{3}")'.format(id, feed['title'], feed['url'], feed['category'])
        cursor = self.conn.cursor()
        cursor.execute(q)
        self.conn.commit()
        cursor.close()
        return self.__get_feed(id)

    def __insert_articles_for(self, feed, f):
        limit = count = len(f.entries)
        if count > self.max_entries:
            limit = self.max_entries
        for i in range(0, count):
            # Check for article existence...
            (timestamp, title, content, link, uid) = self.__check_feed_item(f.entries[i])
            try:
                assert self.__article_exists(uid) == False
                ghost = 0
                if i >= limit:
                    ghost = 1
                images = self.__find_images_in_article(content)
                article = self.__insert_article(feed['id'], title,  
                            content, link, uid, timestamp, images, ghost)
                self.__fetch_remote_images_for(article)
            except AssertionError:
                #~ self.warning("error", "Article already exists")
                pass

    def __find_images_in_article(self, description):
        """
        Searches for img tags in order to identify feed body images. It also checks 
        paths to make sure all are absolute (if not, it tries to). 
        Returns a comma-separated string with all images with it's (url) path.
        """
        images = []
        rgxp = '''<img\s+[^>]*?src=["']?([^"'>]+)[^>]*?>'''
        m = re.findall(rgxp, description, re.I)
        for img in m:
            images.append(img)
        return ','.join(images)

    def __fetch_remote_images_for(self, article):
        """
        Manages entry images. It discards downloading images that are already on the
        database to save space and bandwidth per URL basis.
        """
        if not os.path.exists(self.images_path):
            os.makedirs(self.images_path)
        cursor = self.conn.cursor()
        for i in article['images'].split(","):
            cursor.execute('SELECT name FROM images WHERE url = ?', [i])
            row = cursor.fetchone()
            # not found, download
            if row is None:
                name = make_uuid(i)
                if self.__get_remote_image(i, name):
                    # add to db only AFTER we successfully retrive the image
                    cursor.execute('INSERT INTO images VALUES(null, ?, ?, ?)', [name,i,article['id']])
                    self.conn.commit()
            # found
            else:
                cursor.execute('INSERT INTO images VALUES(null, ?, ?, ?)', [row[0],i,article['id']])
                self.conn.commit()
        cursor.close()
    
    def __get_remote_image(self, src, name):
        image = os.path.join(self.images_path,name)
        try:
            web_file = urllib2.urlopen(src, timeout=10)
            local_file = open(image, 'w')
            local_file.write(web_file.read())
            local_file.close()
            web_file.close()
            return True
        except Exception, e:
            try: os.unlink(image)
            except Exception, e: print e
            return False
        
    def __get_article(self, id):
        q = 'SELECT id,title,date,link,content,images FROM articles WHERE id = "{0}"'.format(id)
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
                    'images':r[5], 
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
                    'link':r[5], 
                    'feed_id':str(r[6]), 
                }
            )
        return articles

    def __insert_article(self, f_id, title, content, link, uid, timestamp, 
                                    images, ghost):
        cursor = self.conn.cursor()
        cursor.execute (
            'INSERT INTO articles VALUES(?, ?, ?, ?, ?, 0, 0, ?, ?, ?)', 
            [
                uid.decode("utf-8"),
                title.decode("utf-8"),
                content.decode("utf-8"),
                timestamp,
                link.decode("utf-8"),
                images,
                f_id,
                ghost
            ]
        )
        self.conn.commit()
        cursor.close()
        return self.__get_article(uid)
        
    def __check_feed_item(self, feed_item):
        """Sets a default value for feed items if there's not any."""
            
        if(hasattr(feed_item,'date_parsed')):
            dp = feed_item.date_parsed
            try:
                secs = time.mktime(datetime.datetime(dp[0], dp[1], dp[2], dp[3], dp[4], dp[5], dp[6]).timetuple())
            except:
                secs = make_time()
        else:
            secs = make_time()

        if hasattr(feed_item,'title'):
            if feed_item.title is not None: title = feed_item.title.encode("utf-8")
            else: title = 'Without title'
        else: title = 'Without title'

        content = 'No content'        
        if hasattr(feed_item,'content'):
            try:
                content = feed_item.content[0].get('value').encode("utf-8")
            except:
                pass
        else:
            if hasattr(feed_item,'description'):
                if feed_item.description is not None:
                    content = feed_item.description.encode("utf-8")

        if hasattr(feed_item,'link'):
            if feed_item.link is not None: link = feed_item.link.encode("utf-8")
            else: link = 'Without link'
        else: link = 'Without link'

        if(hasattr(feed_item,'id')):
            if feed_item.id is not None and feed_item.id != '':
                id = feed_item.id.encode("utf-8")
            else:
                if title != '':
                    id = make_uuid(title)
                else:
                    id = make_uuid(content)
        else:
            if title != '':
                id = make_uuid(title)
            else:
                id = make_uuid(content)

        return (secs, title, content, link, id)    
    
    def __create_database(self):
        cursor = self.conn.cursor()
        cursor.executescript('''
            CREATE TABLE categories(id integer PRIMARY KEY, name varchar(32) NOT NULL);
            CREATE TABLE feeds(id varchar(256) PRIMARY KEY, name varchar(32) NOT NULL, url varchar(1024) NOT NULL, category_id integer NOT NULL);
            CREATE TABLE articles(id varchar(256) PRIMARY KEY, title varchar(256) NOT NULL, content text, date integer NOT NULL, link varchar(1024) NOT NULL, read INTEGER NOT NULL, starred INTEGER NOT NULL, images TEXT, feed_id integer NOT NULL, ghost integer NOT NULL);
            CREATE TABLE images(id integer PRIMARY KEY, name varchar(256) NOT NULL, url TEXT NOT NULL, article_id varchar(256) NOT NULL);
            INSERT INTO categories VALUES(null, 'General');
            ''')
        self.conn.commit()
        cursor.close()


    def __clean_up(self):
        pass
        
    def __article_exists(self, uid):
        cursor = self.conn.cursor()
        cursor.execute('SELECT id FROM articles WHERE id = ?', [uid])
        row = cursor.fetchone()
        cursor.close()
        if row:
            return True
        return False

    def __feed_exists(self, url):
        cursor = self.conn.cursor()
        cursor.execute('SELECT id FROM feeds WHERE url = ?', [url])
        row = cursor.fetchone()
        cursor.close()
        if row:
            return True
        return False

    def __category_exists(self, name):
        cursor = self.conn.cursor()
        cursor.execute('SELECT id FROM categories WHERE name = ?', [name])
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
