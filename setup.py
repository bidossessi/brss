#!/usr/bin/env python2
# -*- coding: utf-8 -*-
#
#       setup.py
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
from setuptools import setup, find_packages
import os, sys, glob, platform
from brss.launcher import __version__

data_files = []
if platform.system() in ('Linux', 'SunOS'):
    applications = glob.glob("brss/applications/*")
    icons = glob.glob("brss/icons/*")
    pixmaps = glob.glob("brss/pixmaps/*")
    data_files.extend([
        ("applications", applications),
        ("icons", icons),
        ("pixmaps", pixmaps),
        ])

setup(
    name='brss',
    packages = find_packages(),
    version = __version__,
    description = "Offline DBus RSS reader",
    fullname = "BRss Offline RSS Reader",
    long_description = open('README.txt').read(),
    classifiers = [
        "Programming Language :: Python",
        "Topic :: Internet",
        "Environment :: GTK ",
        "Intended Audience :: End Users/Desktop",
        "Operating System :: POSIX",
        "Licence :: OSI Approved :: GNU General Public License (GPL)",
        ],
    author='Bidossessi SODONON',
    author_email='bidossessi.sodonon@yahoo.fr',
    zip_safe=False,
    requires=[
        'dbus',
        'sqlite3',
        'feedparser',
        'html5lib',
        'xml',
        'gi'
        ],
    entry_points = {
        'gui_scripts': ['brss-reader = brss.launcher:run_frontend'],
        'console_scripts': ['brss-engine = brss.launcher:run_engine'],
       },
    package_dir = {'brss': 'brss'},
    package_data = {},
    include_package_data = True,
    data_files = data_files
)
