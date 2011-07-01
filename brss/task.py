#!/usr/bin/env python
#-*- coding:utf-8 -*-
"""
This module defines the basic types of models we intend to deal with.
The type of instances generated by this module are really TreeViews.
"""
import threading, thread
### FIXME: GLib is not working our for me right now
### GError: Could not locate g_thread_init: `g_thread_init': /usr/lib/libglib-2.0.so.0: undefined symbol: g_thread_init
#~ from gi.repository import GLib
#~ GLib.thread_init(None)
import gobject
gobject.threads_init()

class GeneratorTask(object):
    
    def __init__(self, generator, loop_callback, complete_callback=None):
        self.generator = generator
        self.loop_callback = loop_callback
        self.complete_callback = complete_callback

    def _start(self, *args, **kwargs):
        self._stopped = False
        for ret in self.generator(*args, **kwargs):
            if self._stopped:
                break
            gobject.idle_add(self._loop, ret)
        if self.complete_callback is not None:
            gobject.idle_add(self.complete_callback)

    def _loop(self, ret):
        if ret is None:
            ret = ()
        if not isinstance(ret, tuple):
            ret = (ret,)
        self.loop_callback(*ret)
       
    def start(self, *args, **kwargs):
        threading.Thread(target=self._start, args=args, kwargs=kwargs).start()
      
    def stop(self):
        self._stopped = True

#~ if __name__ == '__main__':
    #~ import time
    #~ class MainWindow(gtk.Window):
        #~ def __init__(self):
           #~ super(MainWindow, self).__init__()
           #~ vb = gtk.VBox()
           #~ self.add(vb)
           #~ self.progress_bar = gtk.ProgressBar()
           #~ self.res = gtk.Label()
           #~ vb.pack_start(self.progress_bar, True, True, 0)
           #~ b = gtk.Button(stock=gtk.STOCK_OK)
           #~ vb.pack_start(self.res, True, True, 0)
           #~ vb.pack_start(b, True, True, 0)
           #~ b.connect('clicked', self.on_button_clicked)
           #~ self.connect("destroy", gtk.main_quit)
           #~ self.show_all()
#~ 
        #~ def on_button_clicked(self, button):
            #~ self.target = []
            #~ data = range(10)
            #~ self.counter = 0
            #~ GeneratorTask(self.fill, self.loop_cb, self.done).start(self.target, data, self.counter)
        #~ 
        #~ def fill (self, store, data, counter):
            #~ for i in data:
                #~ counter += 1
                #~ store.append(i)
                #~ fr = counter / float(len(data))
                #~ time.sleep(1)
                #~ yield fr
#~ 
        #~ def loop_cb(self, fraction):
            #~ self.progress_bar.set_fraction(fraction)
        #~ 
        #~ def done(self):
            #~ self.res.set_text("done")
            #~ print self.target
            #~ print self.counter
#~ 
#~ 
    #~ w = MainWindow()
    #~ gtk.main()