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

TODO:
-----

The following are planned, in no particular order:

    - Move database handling to SQLAlchemy
    - Localization
    - Documentation
    - Gnome3 design guidelines compliance
    - Better logo and pixmaps
    - CLI interface
    - Synapse integration (for adding feeds)
    - DnD feed recategorizing
