#!/usr/bin/env python2
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

from pkg_resources import resource_filename
from datetime import date, datetime
import os
import locale
import hashlib
import time

def make_date(string):
    date = datetime.fromtimestamp(int(string))
    return date.strftime (locale.nl_langinfo(locale.D_FMT))

def make_path(type, file):
    """Return a data file path"""
    return resource_filename("brss", os.path.join(type,file))

def make_time():
    split = str(datetime.now()).split(' ')
    ds = split[0].split('-')
    ts = split[1].split(':')
    t = datetime(int(ds[0]), int(ds[1]), int(ds[2]), int(ts[0]), int(ts[1]), int(float(ts[2])))
    return time.mktime(t.timetuple())

def make_uuid(data="fast random string", add_time=True):
    if add_time:#make it REALLY unique
        data = str(make_time())+str(data)
    return hashlib.md5(data).hexdigest().encode("utf-8")
