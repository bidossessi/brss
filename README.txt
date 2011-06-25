BRSS Offline RSS Reader version 0.1
-----------------------------------

BRSS is a so-called 'offline' RSS readerheavily inspired by Naufrago!

BRSS consists of two applications:

1- ENGINE.
The BRSS engine runs in the background and publishes it's methods through
DBus. The engine downloads feed articles into a SQLite database and 
downloads remote images in a specified directories. 
When an article is requested, the engine transparently replaces all remote 
images' 'src' attributes with the local path.
The engine polls feeds at a configurable interval, and can import 
(and export) OPML files.

2- FRONTEND
BRSS also comes with a Gtk frontend that connects to a running engine, to 
show feeds and articles previously downloaded.
