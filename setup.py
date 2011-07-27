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
#~ import os, sys, glob, platform

#~ from distutils.core import setup
from distutils import cmd
from distutils.command.install_data import install_data as _install_data
from distutils.command.build import build as _build
 
import msgfmt
import os, sys, glob, platform

from brss.common import __version__, __maintainers__

DATA = [
        ("applications", glob.glob("brss/applications/*")),
        ("icons/hicolor", glob.glob("brss/icons/hicolor/*")),
        ("pixmaps", glob.glob("brss/pixmaps/*")),
        ("glib-2.0/schemas", glob.glob("brss/schemas/*"))
        ]

class build_trans(cmd.Command):
    description = 'Compile .po files into .mo files'
    def initialize_options(self):
        pass
 
    def finalize_options(self):
        pass
 
    def run(self):
        po_dir = os.path.join(os.path.dirname(os.curdir), 'brss', 'po')
        for path, names, filenames in os.walk(po_dir):
            for f in filenames:
                if f.endswith('.po'):
                    lang = f[:len(f) - 3]
                    src = os.path.join(path, f)
                    dest_path = os.path.join('brss', 'locale', lang, 'LC_MESSAGES')
                    dest = os.path.join(dest_path, 'brss.mo')
                    if not os.path.exists(dest_path):
                        os.makedirs(dest_path)
                    if not os.path.exists(dest):
                        print 'Compiling %s' % src
                        msgfmt.make(src, dest)
                    else:
                        src_mtime = os.stat(src)[8]
                        dest_mtime = os.stat(dest)[8]
                        if src_mtime > dest_mtime:
                            print 'Compiling %s' % src
                            msgfmt.make(src, dest)

class build(_build):
    sub_commands = _build.sub_commands + [('build_trans', None)]
    def run(self):
        _build.run(self)

class install_data(_install_data):
 
    def run(self):
        for lang in os.listdir('brss/locale/'):
            lang_dir = os.path.join('locale', lang, 'LC_MESSAGES')
            lang_file = os.path.join('brss', 'locale', lang, 'LC_MESSAGES', 'brss.mo')
            self.data_files.append( (lang_dir, [lang_file]) )
        _install_data.run(self)

cmdclass = {
    'build': build,
    'build_trans': build_trans,
    'install_data': install_data,
}

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
    author=__maintainers__,
    author_email='bidossessi.sodonon@yahoo.fr',
    zip_safe=False,
    entry_points = {
        'gui_scripts': ['brss-reader = brss:run_reader'],
        'console_scripts': ['brss-engine = brss:run_engine'],
       },
    package_dir             = {'brss': 'brss'},
    package_data            = {},
    include_package_data    = True,
    data_files              = DATA,
    cmdclass                = cmdclass,

)
