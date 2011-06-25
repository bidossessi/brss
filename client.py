#!/usr/bin/env python
#-*- coding:utf-8 -*-

# consumeservice.py
# consumes a method in a service on the dbus
 
import dbus
import dbus.mainloop.glib
dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

bus                 = dbus.SessionBus()
engine              = bus.get_object('com.itgears.brss', '/com/itgears/brss/Engine')
add_category        = engine.get_dbus_method('add_category', 'com.itgears.brss')
get_categories      = engine.get_dbus_method('get_categories', 'com.itgears.brss')
get_feeds_for       = engine.get_dbus_method('get_feeds_for', 'com.itgears.brss')
add_feed            = engine.get_dbus_method('add_feed', 'com.itgears.brss')
get_articles_for    = engine.get_dbus_method('get_articles_for', 'com.itgears.brss')
get_article         = engine.get_dbus_method('get_article', 'com.itgears.brss')
exit                = engine.get_dbus_method('exit', 'com.itgears.brss')
update              = engine.get_dbus_method('update', 'com.itgears.brss')
get_menu_items      = engine.get_dbus_method('get_menu_items', 'com.itgears.brss')

def log(*args):
    print args
    
#~ try:
    #~ add_category({'name': 'Other category'})
    #~ f = {'url': 'http://localhost/~b_sodonon/domestica/?feed=rss2'}
    #~ add_feed(f)
    #~ f = {'url': 'http://localhost/~b_sodonon/wordpress/?feed=rss2'}
    #~ add_feed(f)
    #~ f = {'url': 'http://localhost/~b_sodonon/marketing-dz.com/rss.php?category=home'}
    #~ add_feed(f)
    #~ update('all'),
        #~ reply_handler=log,
        #~ error_handler=log)
    #~ print get_menu_items()
#~ except Exception, e:
    #~ print e
exit()
