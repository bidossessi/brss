#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#       functions.py
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

from gi.repository import Gio

from datetime import date, datetime
import locale
import hashlib
import time
import sys
from gi.repository import GdkPixbuf
from gi.repository import GLib

__version__         = '0.9'
__authors__         = ["Bidossessi SODONON"]
__maintainers__     = ["Bidossessi SODONON"]
__documenters__     = ["Bidossessi SODONON"]
__artists__         = ["Bidossessi SODONON"]

BASE_KEY            = 'com.itgears.BRss'
ENGINE_DBUS_KEY     = 'com.itgears.BRss.Engine'
ENGINE_DBUS_PATH    = '/com/itgears/BRss/Engine'
READER_DBUS_KEY     = 'com.itgears.BRss.Reader'
READER_DBUS_PATH    = '/com/itgears/BRss/Reader'
BASE_PATH           = GLib.build_filenamev([GLib.get_user_config_dir(),'brss'])
FAVICON_PATH        = GLib.build_filenamev([BASE_PATH, 'favicons'])
IMAGES_PATH         = GLib.build_filenamev([BASE_PATH, 'images'])
DB_PATH             = GLib.build_filenamev([BASE_PATH, 'brss.db'])
base_dir            = Gio.file_new_for_path(BASE_PATH)
favicon_dir         = Gio.file_new_for_path(FAVICON_PATH)
images_dir          = Gio.file_new_for_path(IMAGES_PATH)

def init_dirs():
    try:
        base_dir.make_directory(None)
    except:pass
    try:favicon_dir.make_directory(None)
    except:pass
    try:images_dir.make_directory(None)
    except:pass

def make_date(string):
    date = datetime.fromtimestamp(int(string))
    return date.strftime (locale.nl_langinfo(locale.D_FMT))

def make_path(type, filename):
    """Return a data opml path"""
    return GLib.build_filenamev([sys.prefix, 'share', type, filename])

def make_time():
    split = str(datetime.now()).split(' ')
    ds = split[0].split('-')
    ts = split[1].split(':')
    t = datetime(int(ds[0]), int(ds[1]), int(ds[2]), int(ts[0]), int(ts[1]), int(float(ts[2])))
    return time.mktime(t.timetuple())

def get_pixmap(fname):
    """Returns a pixmap file included with brss"""
    return make_path("pixmaps", fname)

def make_pixbuf(name='brss', size=128):
    return GdkPixbuf.Pixbuf.new_from_file_at_size(
        get_pixmap("{0}.svg".format(name)), size, size)

def make_uuid(data="fast random string", add_time=True):
    if add_time: #make it REALLY unique
        data = str(make_time())+str(data)
    return hashlib.md5(data).hexdigest().encode("utf-8")
