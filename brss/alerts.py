#!/usr/bin/env python
#-*- coding:utf-8 -*-


"""This contains some custom widgets I use."""

from gi.repository import Gtk

__version__ = "0.1"

## ALERTS

class Alerts:
    
    def __init__(self, parent):
        self.win  = parent
        self.reset_checksum()
        
    def reset_checksum(self):
        self.checksum = True
        
    def info(self, msg, mmsg=None):
        diag = Gtk.MessageDialog(
            self.win,
            Gtk.DialogFlags.MODAL|Gtk.DialogFlags.DESTROY_WITH_PARENT,
            Gtk.MessageType.INFO,
            Gtk.ButtonsType.CLOSE,
            msg
            )
        if mmsg:
            diag.format_secondary_text(mmsg)
        diag.connect('response', self.diag_response)
        diag.run()
        
    def warning(self, msg, mmsg=None):
        diag = Gtk.MessageDialog(
            self.win,
            Gtk.DialogFlags.MODAL|Gtk.DialogFlags.DESTROY_WITH_PARENT,
            Gtk.MessageType.WARNING,
            Gtk.ButtonsType.CLOSE,
            msg
            )
        if mmsg:
            diag.format_secondary_text(mmsg)
        diag.connect('response', self.diag_response)
        diag.run()

    def question(self, msg, mmsg=None):
        diag = Gtk.MessageDialog(
            self.win,
            Gtk.DialogFlags.MODAL|Gtk.DialogFlags.DESTROY_WITH_PARENT,
            Gtk.MessageType.WARNING,
            Gtk.ButtonsType.YES_NO,
            msg
            )
        if mmsg:
            diag.format_secondary_text(mmsg)
        diag.connect('response', self.diag_response)
        diag.run()

    def error(self, msg, mmsg=None):
        diag = Gtk.MessageDialog(
            self.win,
            Gtk.DialogFlags.MODAL|Gtk.DialogFlags.DESTROY_WITH_PARENT,
            Gtk.MessageType.ERROR,
            Gtk.ButtonsType.CLOSE,
            msg
            )
        if mmsg:
            diag.format_secondary_text(mmsg)
        diag.connect('response', self.diag_response)
        diag.run()
            
    def diag_response(self, dialog, response):
        """Stub. to override when needed."""
        if response == Gtk.ResponseType.CLOSE:
            pass
        elif response == Gtk.ResponseType.YES:
            pass
        elif response == Gtk.ResponseType.NO:
            #~ if hasattr(self, 'checksum'):
                self.checksum = False
        elif response == Gtk.ResponseType.CANCEL:
            #~ if hasattr(self, 'checksum'):
                self.checksum = False
        self.reset_checksum()
        dialog.destroy()
