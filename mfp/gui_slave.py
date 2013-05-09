#! /usr/bin/env python2.6
'''
gui_slave.py
GTK/clutter gui for MFP -- main thread

Copyright (c) 2010 Bill Gribble <grib@billgribble.com>
'''

import threading
from singleton import Singleton
from rpc_wrapper import RPCWrapper, rpcwrap
from main import MFPCommand
from . import log
from utils import profile 

def gui_init(pipe):
    import os
    log.log_module = "gui"
    log.debug("GUI thread started, pid =", os.getpid())
    pipe.on_finish(gui_finish)
    RPCWrapper.pipe = pipe
    RPCWrapper.node_id = "Clutter GUI"
    GUICommand.local = True
    MFPCommand.local = False
    MFPGUI()

def gui_finish():
    MFPGUI().finish()


def clutter_do(func):
    def wrapped(*args, **kwargs):
        from mfp.gui_slave import MFPGUI
        MFPGUI().clutter_do(lambda: func(*args, **kwargs))

    return wrapped 


class GUICommand (RPCWrapper):
    @rpcwrap
    def ready(self):
        if MFPGUI().appwin is not None and MFPGUI().appwin.ready():
            return True
        else:
            return False

    @rpcwrap
    def log_write(self, msg):
        MFPGUI().clutter_do(lambda: self._log_write(msg))
        return True

    def _log_write(self, msg):
        MFPGUI().appwin.log_write(msg)

    @rpcwrap
    def console_write(self, msg):
        MFPGUI().clutter_do(lambda: self._console_write(msg))
        return True

    def _console_write(self, msg):
        MFPGUI().appwin.console_write(msg)

    @rpcwrap
    def hud_write(self, msg):
        MFPGUI().clutter_do(lambda: self._hud_write(msg))
        return True

    def _hud_write(self, msg):
        MFPGUI().appwin.hud_write(msg)

    @rpcwrap
    def finish(self):
        MFPGUI().finish()

    @rpcwrap
    def command(self, obj_id, action, args):
        MFPGUI().clutter_do(lambda: self._command(obj_id, action, args))
        return True

    def _command(self, obj_id, action, args):
        obj = MFPGUI().recall(obj_id)
        obj.command(action, args)

    @rpcwrap
    def configure(self, obj_id, params):
        MFPGUI().clutter_do(lambda: self._configure(obj_id, params))
        return True

    def _configure(self, obj_id, params):
        obj = MFPGUI().recall(obj_id)
        obj.configure(params)

    @rpcwrap
    def create(self, obj_type, obj_args, obj_id, parent_id, params):
        MFPGUI().clutter_do(lambda: self._create(obj_type, obj_args, obj_id, parent_id, 
                                                 params))
    def _create(self, obj_type, obj_args, obj_id, parent_id, params):
        from .gui.patch_element import PatchElement
        from .gui.processor_element import ProcessorElement
        from .gui.message_element import MessageElement
        from .gui.text_element import TextElement
        from .gui.enum_element import EnumElement
        from .gui.plot_element import PlotElement
        from .gui.slidemeter_element import SlideMeterElement
        from .gui.patch_info import PatchInfo
        from .gui.via_element import SendViaElement, ReceiveViaElement
        from .gui.button_element import ToggleButtonElement
        from .gui.button_element import ToggleIndicatorElement
        from .gui.button_element import BangButtonElement

        elementtype = params.get('display_type')

        ctors = {
            'processor': ProcessorElement,
            'message': MessageElement,
            'text': TextElement,
            'enum': EnumElement,
            'plot': PlotElement,
            'slidemeter': SlideMeterElement,
            'patch': PatchInfo,
            'sendvia': SendViaElement,
            'recvvia': ReceiveViaElement,
            'toggle': ToggleButtonElement,
            'button': BangButtonElement,
            'indicator': ToggleIndicatorElement
        }
        ctor = ctors.get(elementtype)
        if ctor:
            o = ctor(MFPGUI().appwin, params.get('position_x', 0), params.get('position_y', 0))
            o.obj_id = obj_id
            o.parent_id = parent_id
            o.obj_type = obj_type
            o.obj_args = obj_args
            o.obj_state = PatchElement.OBJ_COMPLETE
            if isinstance(o, PatchElement):
                parent = MFPGUI().recall(o.parent_id)
                layer = None 
                if isinstance(parent, PatchInfo):
                    if "layername" in params:
                        layer = parent.find_layer(params["layername"])
                    if not layer: 
                        layer = MFPGUI().appwin.active_layer()
                    layer.add(o)
                    layer.group.add_actor(o)
                    o.container = layer.group
                elif isinstance(parent, PatchElement): 
                    # FIXME: don't hardcode GOP offsets 
                    xpos = params.get("position_x", 0) - parent.export_x + 2
                    ypos = params.get("position_y", 0) - parent.export_y + 20
                    o.move(xpos, ypos)
                    print "setting editable to False:", o
                    o.editable = False 

                    parent.layer.add(o)
                    parent.add_actor(o)    
                    o.container = parent 
                    
                o.configure(params)
                MFPGUI().appwin.register(o)
            else: 
                o.configure(params)

            MFPGUI().remember(o)
            o.update()

    @rpcwrap
    def connect(self, obj_1_id, obj_1_port, obj_2_id, obj_2_port):
        MFPGUI().clutter_do(lambda: self._connect(obj_1_id, obj_1_port, obj_2_id, obj_2_port))

    def _connect(self, obj_1_id, obj_1_port, obj_2_id, obj_2_port):
        from .gui.connection_element import ConnectionElement

        obj_1 = MFPGUI().recall(obj_1_id)
        obj_2 = MFPGUI().recall(obj_2_id)

        if obj_1 is None or obj_2 is None: 
            log.debug("ERROR: connect: obj_1(%s) --> %s, obj_2(%s) --> %s"
                      % (obj_1_id, obj_1, obj_2_id, obj_2))
            return None

        c = ConnectionElement(MFPGUI().appwin, obj_1, obj_1_port, obj_2, obj_2_port)
        MFPGUI().appwin.register(c)
        obj_1.connections_out.append(c)
        obj_2.connections_in.append(c)

    @rpcwrap
    def delete(self, obj_id):
        MFPGUI().clutter_do(lambda: self._delete(obj_id))

    def _delete(self, obj_id):
        from .gui.patch_info import PatchInfo
        log.debug("WARNING: untested GUI element delete!")
        obj = MFPGUI().recall(obj_id)
        if isinstance(obj, PatchInfo): 
            MFPGUI().appwin.patches.remove(obj)
            obj.obj_id = None 
            obj.delete()
        else: 
            for c in obj.connections_out:
                MFPGUI().appwin.unregister(c)
                del c

            for c in obj.connections_in:
                MFPGUI().appwin.unregister(c)
                del c

            obj.obj_id = None
            del obj

    @rpcwrap
    def load_start(self):
        MFPGUI().clutter_do(lambda: self._load_start())

    def _load_start(self):
        MFPGUI().appwin.load_start()


    @rpcwrap
    def load_complete(self):
        MFPGUI().clutter_do(lambda: self._load_complete())

    def _load_complete(self):
        MFPGUI().appwin.load_complete()

    @rpcwrap
    def clear(self):
        pass

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

    def clutter_do_later(self, delay, thunk):
        from gi.repository import GObject
        GObject.timeout_add(int(delay), thunk)

    def clutter_do(self, thunk):
        from gi.repository import GObject
        GObject.idle_add(thunk, priority=GObject.PRIORITY_DEFAULT)

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
