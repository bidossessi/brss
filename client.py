#!/usr/bin/env python
#-*- coding:utf-8 -*-

# consumeservice.py
# consumes a method in a service on the dbus
 
import dbus
 
bus                 = dbus.SessionBus()
engine              = bus.get_object('org.itgears.brss', '/org/itgears/brss/Engine')
add_category        = engine.get_dbus_method('add_category', 'org.itgears.brss')
get_categories      = engine.get_dbus_method('get_categories', 'org.itgears.brss')
get_feeds_for       = engine.get_dbus_method('get_feeds_for', 'org.itgears.brss')
add_feed            = engine.get_dbus_method('add_feed', 'org.itgears.brss')
get_articles_for    = engine.get_dbus_method('get_articles_for', 'org.itgears.brss')
get_article         = engine.get_dbus_method('get_article', 'org.itgears.brss')
exit                = engine.get_dbus_method('exit', 'org.itgears.brss')
update              = engine.get_dbus_method('update', 'org.itgears.brss')

#~ try:
    #~ add_category({'name': 'Other category'})
    #~ cats = get_categories()
    #~ for c in cats:
        #~ feeds = get_feeds_for(c)
        #~ print feeds
        #~ c['feeds'] = feeds        
    #~ print cats
    #~ f = {'url': 'http://localhost/~b_sodonon/domestica/?feed=rss2'}
    #~ add_feed(f)
    #~ f = {'url': 'http://localhost/~b_sodonon/wordpress/?feed=rss2'}
    #~ add_feed(f)
    #~ f = {'url': 'http://localhost/~b_sodonon/marketing-dz.com/rss.php?category=home'}
    #~ add_feed(f)
    #~ fs = get_feeds_for(get_categories()[0])
    #~ f = fs[0]
    #~ exfeed = get_articles_for(f)
    #~ print exfeed
    #~ art = get_article(exfeed[0])
    #~ print art
    #~ update('all')
#~ except Exception, e:
    #~ print e
exit()
