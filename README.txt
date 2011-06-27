=======
 brss
=======

BRss is an 'offline' RSS reader written in Python.
It is a complete rewrite of another python RSS reader (Naufrago!),
but based on the concept of service/client. It uses the dbus library
to enable communication between the service and clients.

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
