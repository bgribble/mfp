#! /usr/bin/env python
'''
gui_main.py
Gui for MFP -- main thread

Copyright (c) Bill Gribble <grib@billgribble.com>
'''

import argparse
import asyncio

from datetime import datetime

import gbulb

from carp.channel import UnixSocketChannel
from carp.host import Host
from flopsy import Store

from mfp import log
from mfp.utils import AsyncTaskManager

from mfp.gui.colordb import ColorDB, RGBAColor
from mfp.gui.param_info import ParamInfo, ListOfInt
from .singleton import Singleton
from .mfp_command import MFPCommand
from .gui_command import GUICommand

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('GtkClutter', '1.0')
gi.require_version('Clutter', '1.0')


class MFPGUI (Singleton):
    def __init__(self):
        super().__init__()

        self.call_stats = {}
        self.objects = {}
        self.mfp = None
        self.debug = False
        self.async_task = AsyncTaskManager()
        self.backend_name = None

        self.style_vars = {
            'autoplace-dx': ParamInfo(label="X offset for autoplace", param_type=float),
            'axis-color': ParamInfo(label="Plot axis color", param_type=RGBAColor),
            'badge-edit-color': ParamInfo(label="Badge color (edit)", param_type=RGBAColor),
            'badge-error-color': ParamInfo(label="Badge color (error)", param_type=RGBAColor),
            'badge-learn-color': ParamInfo(label="Badge color (learn)", param_type=RGBAColor),
            'badge-size': ParamInfo(label="Badge size", param_type=float),
            'border': ParamInfo(label="Draw border", param_type=bool),
            'canvas-color': ParamInfo(label="Canvas background color", param_type=RGBAColor),
            'draw-ports': ParamInfo(label="When to draw inlet/outlet ports", param_type=str),
            'fill-color': ParamInfo(label="Element fill color", param_type=RGBAColor),
            'fill-color:debug': ParamInfo(label="Element fill color (debug)", param_type=RGBAColor),
            'fill-color:selected':ParamInfo(label="Element fill color (selected)", param_type=RGBAColor),
            'font-face': ParamInfo(label="Font faces", param_type=str),
            'font-size': ParamInfo(label="Font size", param_type=float),
            'padding': ParamInfo(label="Element padding", param_type=dict),
            'porthole-border': ParamInfo(label="Inlet/outlet padding", param_type=float),
            'porthole-color': ParamInfo(label="Inlet/outlet color", param_type=RGBAColor),
            'porthole-color:selected': ParamInfo(label="Inlet/outlet color (selected)", param_type=RGBAColor),
            'porthole-height': ParamInfo(label="Inlet/outlet port width", param_type=float),
            'porthole-width': ParamInfo(label="Inlet/outlet port width", param_type=float),
            'porthole-minspace': ParamInfo(label="Inlet/outlet min space", param_type=float),
            'stroke-color': ParamInfo(label="Element outline color", param_type=RGBAColor),
            'stroke-color:debug': ParamInfo(label="Element outline color (debug)", param_type=RGBAColor),
            'stroke-color:selected': ParamInfo(label="Element outline color (selected)", param_type=RGBAColor),
            'stroke-color:hover': ParamInfo(label="Element outline color (hover)", param_type=RGBAColor),
            'text-color': ParamInfo(label="Text color", param_type=RGBAColor),
            'text-color:selected': ParamInfo(label="Text color (selected)", param_type=RGBAColor),
            'text-cursor-color': ParamInfo(label="Text cursor color", param_type=RGBAColor),
        }


        self.style_defaults = {
            'canvas-color': ColorDB().find('default-canvas-color'),
            'fill-color': ColorDB().find('default-fill-color'),
            'fill-color:selected': ColorDB().find('default-fill-color-selected'),
            'fill-color:debug': ColorDB().find('default-fill-color-debug'),
            'font-face': 'Cantarell,Sans',
            'font-size': 16,
            'porthole-color': ColorDB().find('default-stroke-color'),
            'porthole-color:selected': ColorDB().find('default-stroke-color-selected'),
            'stroke-color': ColorDB().find('default-stroke-color'),
            'stroke-color:selected': ColorDB().find('default-stroke-color-selected'),
            'stroke-color:hover': ColorDB().find('default-stroke-color-hover'),
            'stroke-color:debug': ColorDB().find('default-stroke-color-debug'),
            'text-color': ColorDB().find('default-text-color'),
            'text-color:selected': ColorDB().find('default-text-color-selected'),
            'text-cursor-color': ColorDB().find('default-text-cursor-color'),
        }
        self.appwin = None

    def remember(self, obj):
        self.objects[obj.obj_id] = obj

    def recall(self, obj_id):
        return self.objects.get(obj_id)

    def finish(self):
        if self.debug:
            import yappi
            yappi.stop()
            yappi.convert2pstats(
                yappi.get_func_stats()
            ).dump_stats('mfp-gui-funcstats.pstats')

        log.log_func = None
        if self.appwin:
            self.appwin.quit()
            self.appwin = None


def setup_default_colors():
    from .gui.colordb import ColorDB
    ColorDB().insert('default-canvas-color',
                     ColorDB().find(0xf7, 0xf9, 0xf9, 0))
    ColorDB().insert('default-stroke-color',
                     ColorDB().find(0x1f, 0x30, 0x2e, 0xff))
    ColorDB().insert('default-stroke-color-selected',
                     ColorDB().find(0x00, 0x7f, 0xff, 0xff))
    ColorDB().insert('default-stroke-color-hover',
                     ColorDB().find(0x00, 0x20, 0x40, 0x0d))
    ColorDB().insert('default-stroke-color-debug',
                     ColorDB().find(0x3f, 0xbf, 0x7f, 0xff))
    ColorDB().insert('default-fill-color',
                     ColorDB().find(0xd4, 0xdc, 0xff, 0xff))
    ColorDB().insert('default-fill-color-selected',
                     ColorDB().find(0xe4, 0xec, 0xff, 0xff))
    ColorDB().insert('default-fill-color-debug',
                     ColorDB().find(0xcd, 0xf8, 0xec, 0xff))
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
    from mfp.gui.app_window import AppWindow
    parser = argparse.ArgumentParser()
    parser.add_argument("-l", "--logstart", default=None,
                        help="Reference time for log messages")
    parser.add_argument("-s", "--socketpath", default="/tmp/mfp_rpcsock",
                        help="Path to Unix-domain socket for RPC")
    parser.add_argument("-d", "--debug", action="store_true",
                        help="Enable debugging behaviors")
    parser.add_argument("-b", "--backend", default="clutter",
                        help="UI framework to use")
    args = vars(parser.parse_args())
    socketpath = args.get("socketpath")
    debug = args.get('debug')
    backend = args.get('backend')

    log.log_module = "gui"
    log.log_func = log.rpclog
    log.log_debug = True

    if args.get("logstart"):
        st = datetime.strptime(args.get("logstart"), "%Y-%m-%dT%H:%M:%S.%f")
        if st:
            log.log_time_base = st

    log.debug("UI starting")

    channel = UnixSocketChannel(socket_path=socketpath)
    host = Host(
        label="MFP GUI",
    )
    def _exception(exc, tbinfo, traceback):
        log.error(f"[carp] Exception: {tbinfo}")
        for ll in traceback.split('\n'):
            log.error(ll)

    host.on("exception", _exception)

    await host.connect(channel)

    # set up Flopsy store manager
    Store.setup_asyncio()

    MFPCommandFactory = await host.require(MFPCommand)
    mfp_connection = await MFPCommandFactory()

    from mfp.gui import backends  # noqa

    ColorDB.backend_name = backend

    setup_default_colors()

    gui = MFPGUI()
    gui.mfp = mfp_connection
    gui.debug = debug
    gui.backend_name = backend

    gui.appwin = AppWindow.build()

    if debug:
        import yappi
        yappi.start()

    await host.export(GUICommand)
    await host.wait_for_completion()
    await channel.close()


async def main_error_wrapper():
    main_task = asyncio.create_task(main())
    try:
        await main_task
    except Exception as e:
        import traceback
        print(f"[LOG] ERROR: GUI process failed with {e}")
        tb = traceback.format_exc()
        for ll in tb.split("\n"):
            print(f"[LOG] ERROR: {ll}")
    ex = main_task.exception()
    if ex:
        print(f"[LOG] ERROR: quit: task exited with exception {ex}")
    else:
        print("[LOG] ERROR: quit: task exited normally")


def main_sync_wrapper():
    gbulb.install(gtk=True)
    asyncio.run(main_error_wrapper())
