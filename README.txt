=======
 brss
=======

BRss is an 'offline' RSS reader written in Python.
It is a complete rewrite of another python RSS reader (Naufrago!),
based on the concept of service/client. It uses the dbus library to 
enable communication between the service and clients.

Features:
---------

BRss consists of two applications:

1. brss-engine
brss-engine is a dbus service. Its main features are:
    - periodically downloads feed articles, with their images
    - notify on updates
    - transparently replaces remote image tags on article request.
    - search articles

2. brss-reader
brss-reader is a GTK+ client for brss-engine.
    - Connects to brss-engine
    - Keyboard feed and article navigation (à la Thunderbird)
    - full-screen article viewing
    - Article search engine


INSTALL:
--------
Reminder: BRss is still "alpha" software. Use at your own risks.

BRss requires the following python modules to run.

python-gobject
python-feedparser
python-sqlite3
python-dbus

How to install this modules may vary depending on your distribution.
In Archlinux run the following command as root:

# pacman -S dbus-python pygobject python2-feedparser python-pysqlite gtk3 libwebkit3 libnotify

1. Extract the archive

$ tar zxf brss-0.8.5dev.tar.gz
$ cd brss-0.8.5dev

2. Install

$ sudo python setup.py install

3. For some reason, the schema is not copied during installation, so do it manually.

$ sudo cp brss/schemas/com.itgears.BRss.gschema.xml /usr/share/glib-2.0/schemas/

4. Compile the schema folder

$ sudo glib-compile-schemas /usr/share/glib-2.0/schemas/

TODO:
-----

The following are planned, in no particular order:

    - Provide a proper install script.
    - Localization
    - Documentation
    - Gnome3 design guidelines compliance
    - Better logo and pixmaps
    - CLI interface
    - Synapse integration (for adding feeds)
    - DnD feed recategorizing
