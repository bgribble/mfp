#! /usr/bin/env python
'''
gui_app.py
GTK/clutter gui for MFP -- main thread

Copyright (c) 2010 Bill Gribble <grib@billgribble.com>
'''

import threading
import argparse
import sys
from datetime import datetime

from carp.channel import UnixSocketChannel
from carp.host import Host

from mfp import log
from mfp.utils import profile

from .singleton import Singleton
from .mfp_command import MFPCommand
from .gui_command import GUICommand


def clutter_do(func):
    def wrapped(*args, **kwargs):
        from mfp.gui_main import MFPGUI
        MFPGUI().clutter_do(lambda: func(*args, **kwargs))

    return wrapped


class MFPGUI (Singleton):
    def __init__(self, mfp_factory):
        self.call_stats = {}
        self.objects = {}
        self.mfp_factory = mfp_factory
        self.mfp = None
        self.appwin = None
        self.debug = False

        self.style_defaults = {
            'font-face': 'Cantarell,Sans',
            'font-size': 16,
            'canvas-color': 'default-canvas-color',
            'stroke-color': 'default-stroke-color',
            'fill-color': 'default-fill-color',
            'text-color': 'default-text-color',
            'stroke-color:selected': 'default-stroke-color-selected',
            'fill-color:selected': 'default-fill-color-selected',
            'text-color:selected': 'default-text-color-selected',
            'text-cursor-color': 'default-text-cursor-color'
        }

        self.clutter_thread = threading.Thread(target=self.clutter_proc)
        self.clutter_thread.start()

    def remember(self, obj):
        self.objects[obj.obj_id] = obj

    def recall(self, obj_id):
        return self.objects.get(obj_id)

    def _callback_wrapper(self, thunk):
        try:
            return thunk()
        except Exception as e:
            log.debug("Exception in GUI operation:", e)
            log.debug_traceback()
            return False

    def clutter_do_later(self, delay, thunk):
        from gi.repository import GObject
        count = self.call_stats.get("clutter_later", 0) + 1
        self.call_stats['clutter_later'] = count
        GObject.timeout_add(int(delay), self._callback_wrapper, thunk)

    def clutter_do(self, thunk):
        from gi.repository import GObject
        count = self.call_stats.get("clutter_now", 0) + 1
        self.call_stats['clutter_now'] = count
        GObject.idle_add(self._callback_wrapper, thunk, priority=GObject.PRIORITY_DEFAULT)

    def clutter_proc(self):
        try:
            from gi.repository import GObject, Gtk, GtkClutter

            # explicit init seems to avoid strange thread sync/blocking issues
            GObject.threads_init()
            GtkClutter.init([])

            # create main window
            from mfp.gui.patch_window import PatchWindow
            self.appwin = PatchWindow()
            self.mfp = self.mfp_factory()

        except Exception:
            log.error("Fatal error during GUI startup")
            log.debug_traceback()
            return

        try:
            # direct logging to GUI log console
            Gtk.main()
        except Exception as e:
            log.error("Caught GUI exception:", e)
            log.debug_traceback()
            sys.stdout.flush()

    def finish(self):
        from gi.repository import Gtk
        if self.debug:
            import yappi
            yappi.stop()
            yappi.convert2pstats(yappi.get_func_stats()).dump_stats(
                'mfp-gui-funcstats.pstats')

        log.log_func = None
        if self.appwin:
            self.appwin.quit()
            self.appwin = None
        Gtk.main_quit()


def setup_default_colors():
    from .gui.colordb import ColorDB
    ColorDB().insert('default-canvas-color',
                     ColorDB().find(0xf7, 0xf9, 0xf9, 0))
    ColorDB().insert('default-stroke-color',
                     ColorDB().find(0x1f, 0x30, 0x2e, 0xff))
    ColorDB().insert('default-stroke-color-selected',
                     ColorDB().find(0x00, 0x7f, 0xff, 0xff))
    ColorDB().insert('default-fill-color',
                     ColorDB().find(0xd4, 0xdc, 0xff, 0xff))
    ColorDB().insert('default-fill-color-selected',
                     ColorDB().find(0xe4, 0xec, 0xff, 0xff))
    ColorDB().insert('default-alt-fill-color',
                     ColorDB().find(0x7d, 0x83, 0xff, 0xff))
    ColorDB().insert('default-text-color',
                     ColorDB().find(0x1f, 0x30, 0x2e, 0xff))
    ColorDB().insert('default-light-text-color',
                     ColorDB().find(0xf7, 0xf9, 0xf9, 0xff))
    ColorDB().insert('default-text-color-selected',
                     ColorDB().find(0x00, 0x7f, 0xff, 0xff))
    ColorDB().insert('default-edit-badge-color',
                     ColorDB().find(0x74, 0x4b, 0x94, 0xff))
    ColorDB().insert('default-learn-badge-color',
                     ColorDB().find(0x19, 0xff, 0x90, 0xff))
    ColorDB().insert('default-error-badge-color',
                     ColorDB().find(0xb7, 0x21, 0x21, 0xff))
    ColorDB().insert('default-text-cursor-color',
                     ColorDB().find(0x0, 0x0, 0x0, 0x40))
    ColorDB().insert('transparent',
                     ColorDB().find(0x00, 0x00, 0x00, 0x00))


async def main():
    import gi
    gi.require_version('Gtk', '3.0')
    gi.require_version('GtkClutter', '1.0')
    gi.require_version('Clutter', '1.0')

    parser = argparse.ArgumentParser()
    parser.add_argument("-l", "--logstart", default=None,
                        help="Reference time for log messages")
    parser.add_argument("-s", "--socketpath", default="/tmp/mfp_rpcsock",
                        help="Path to Unix-domain socket for RPC")
    parser.add_argument("-d", "--debug", action="store_true",
                        help="Enable debugging behaviors")

    args = vars(parser.parse_args())
    socketpath = args.get("socketpath")
    debug = args.get('debug')

    channel = UnixSocketChannel(socket_path=socketpath)
    host = Host(
        label="MFP GUI",
    )
    await host.connect(channel)

    print("[LOG] DEBUG: GUI process starting")

    if args.get("logstart"):
        st = datetime.strptime(args.get("logstart"), "%Y-%m-%dT%H:%M:%S.%f")
        if st:
            log.log_time_base = st

    log.log_module = "gui"
    log.log_func = log.rpclog
    log.log_debug = True

    setup_default_colors()

    mfp_factory = await host.require(MFPCommand)
    print("[LOG] DEBUG: Got MFPCommand factory")
    gui = MFPGUI(mfp_factory)
    gui.debug = debug

    if debug:
        import yappi
        yappi.start()

    await host.export(GUICommand)
    print("[LOG] DEBUG: exported GUICommand factory")


def main_sync_wrapper():
    import asyncio
    asyncio.run(main())

