#! /usr/bin/env python2.6
'''
gui_app.py
GTK/clutter gui for MFP -- main thread

Copyright (c) 2010 Bill Gribble <grib@billgribble.com>
'''

import threading
import argparse 
from singleton import Singleton
from mfp_command import MFPCommand
from . import log

from .gui_command import GUICommand
from .rpc import RPCRemote, RPCHost

def clutter_do(func):
    def wrapped(*args, **kwargs):
        from mfp.gui_main import MFPGUI
        MFPGUI().clutter_do(lambda: func(*args, **kwargs))

    return wrapped 

def add_color_defaults(): 
    from .gui.colordb import ColorDB
    ColorDB().insert("default_field", ColorDB().find(255, 255, 255, 255))
    ColorDB().insert("default_bg", ColorDB().find(255, 255, 255, 128))
    ColorDB().insert("default_bg_edit", ColorDB().find(200, 200, 255, 128))
    ColorDB().insert("default_fg_unsel", ColorDB().find(0, 0, 0, 255))
    ColorDB().insert("default_fg_sel", ColorDB().find(255, 0, 0, 255))
    ColorDB().insert("default_txtcursor", ColorDB().find(0, 0, 0, 64))

class MFPGUI (Singleton):
    def __init__(self):
        self.objects = {}
        self.mfp = None
        self.appwin = None
        self.clutter_thread = threading.Thread(target=self.clutter_proc)
        self.clutter_thread.start()

    def remember(self, obj):
        self.objects[obj.obj_id] = obj

    def recall(self, obj_id):
        return self.objects.get(obj_id)

    def _callback_wrapper(self, thunk):
        try:
            return thunk()
        except Exception, e: 
            import traceback 
            traceback.print_exc()
            log.debug("Exception in GUI operation:", e)
            return False 

    def clutter_do_later(self, delay, thunk):
        from gi.repository import GObject
        GObject.timeout_add(int(delay), self._callback_wrapper, thunk)

    def clutter_do(self, thunk):
        from gi.repository import GObject
        GObject.idle_add(self._callback_wrapper, thunk, priority=GObject.PRIORITY_DEFAULT)

    def clutter_proc(self):
        from gi.repository import Clutter, GObject, Gtk, GtkClutter

        # explicit init seems to avoid strange thread sync/blocking issues
        GObject.threads_init()
        Clutter.threads_init()
        GtkClutter.init([])

        # load default color database 
        add_color_defaults()

        # create main window
        from mfp.gui.patch_window import PatchWindow
        self.appwin = PatchWindow()
        self.mfp = MFPCommand()

        # direct logging to GUI log console
        log.log_func = self.appwin.log_write

        try:
            Gtk.main()
        except Exception, e:
            import traceback
            traceback.print_exc()

        # finish
        log.debug("MFPGUI.clutter_proc: clutter main has quit. finishing up")

    def finish(self):
        log.debug("MFPGUI.finish() called")
        if self.appwin:
            log.log_func = None
            self.appwin.quit()
            self.appwin = None

def main(): 
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--socketpath", default="/tmp/mfp_rpcsock",
                        help="Path to Unix-domain socket for RPC") 

    args = vars(parser.parse_args())
    socketpath = args.get("socketpath")

    host = RPCHost()
    host.start()

    remote = RPCRemote(socketpath, "MFP GUI", host)
    remote.connect() 

    print "[LOG] debug: GUI process starting"

    log.log_module = "ui"
    host.subscribe(MFPCommand)
    gui = MFPGUI() 

    host.publish(GUICommand)

