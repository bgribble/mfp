#! /usr/bin/env python
'''
main.py: main routine for mfp

Copyright (c) 2010-2016 Bill Gribble <grib@billgribble.com>
'''

import asyncio
import math
import random
import re
import string
import sys
import os
import argparse
import threading

from datetime import datetime, timedelta

from .evaluator import Evaluator, LazyExpr
from .utils import QuittableThread
from .bang import Bang, Uninit
from .method import MethodCall
from .midi import NoteOn, NoteOff, NotePress, MidiCC, MidiUndef, MidiPitchbend, MidiPgmChange
from .builtins.file import EOF

from .mfp_app import MFPApp, StartupError

from . import log
from . import builtins
from . import utils


mfp_banner = "MFP - Music For Programmers, version %s"

mfp_footer = """
To report bugs or download source:

    http://github.com/bgribble/mfp

Copyright (c) 2009-2023 Bill Gribble <grib@billgribble.com>

MFP is free software, and you are welcome to redistribute it
under certain conditions.  See the file COPYING for details.
"""


def version():
    import pkg_resources
    vers = pkg_resources.require("mfp")[0].version
    return vers


def add_evaluator_defaults():
    # default names known to the evaluator
    Evaluator.bind_global("math", math)
    Evaluator.bind_global("random", random)
    Evaluator.bind_global("os", os)
    Evaluator.bind_global("sys", sys)
    Evaluator.bind_global("re", re)
    Evaluator.bind_global("string", string)

    Evaluator.bind_global("datetime", datetime)
    Evaluator.bind_global("timedelta", timedelta)

    Evaluator.bind_global("Bang", Bang)
    Evaluator.bind_global("Uninit", Uninit)
    Evaluator.bind_global("MethodCall", MethodCall)
    Evaluator.bind_global("LazyExpr", LazyExpr)

    Evaluator.bind_global("EOF", EOF)

    Evaluator.bind_global("NoteOn", NoteOn)
    Evaluator.bind_global("NoteOff", NoteOff)
    Evaluator.bind_global("NotePress", NotePress)
    Evaluator.bind_global("MidiCC", MidiCC)
    Evaluator.bind_global("MidiPgmChange", MidiPgmChange)
    Evaluator.bind_global("MidiPitchbend", MidiPitchbend)
    Evaluator.bind_global("MidiUndef", MidiUndef)

    Evaluator.bind_global("builtins", builtins)
    Evaluator.bind_global("app", MFPApp())


def exit_sighandler(signum, frame):
    log.log_force_console = True
    log.debug("Received terminating signal %s, exiting" % signum)
    sys.exit(-signum)


def test_imports():
    try:
        import gi
        gi.require_version('Gtk', '3.0')
        gi.require_version('GtkClutter', '1.0')
        gi.require_version('Clutter', '1.0')
        import simplejson  # noqa: F401
        import numpy  # noqa: F401
        import nose  # noqa: F401
        from gi.repository import Clutter, GObject, Gtk, Gdk, GtkClutter, Pango  # noqa: F401
        import posix_ipc  # noqa: F401
    except Exception:
        import traceback
        traceback.print_exc()
        print()
        print("FATAL: Required package not installed.  Please run 'waf install_deps'")
        print()
        sys.exit(-1)


async def main():
    description = mfp_banner % version()

    parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
                                     description=description, epilog=mfp_footer)

    parser.add_argument("patchfile", nargs='*',
                        help="Patch files to load")
    parser.add_argument("-f", "--init-file", action="append",
                        default=[utils.homepath(".mfp/mfprc.py")],
                        help="Python source file to exec at launch")
    parser.add_argument("-p", "--patch-path", action="append",
                        default=[os.getcwd()],
                        help="Search path for patch files")
    parser.add_argument("-l", "--init-lib", action="append", default=[],
                        help="Extension library (*.so) to load at launch")
    parser.add_argument("-L", "--lib-path", action="append", default=[],
                        help="Search path for extension libraries")
    parser.add_argument("-i", "--inputs", default=2, type=int,
                        help="Number of JACK audio input ports")
    parser.add_argument("-o", "--outputs", default=2, type=int,
                        help="Number of JACK audio output ports")
    parser.add_argument("--midi-ins", default=1, type=int,
                        help="Number of MIDI input ports")
    parser.add_argument("--midi-outs", default=1, type=int,
                        help="Number of MIDI output ports")
    parser.add_argument("-u", "--osc-udp-port", default=5555, type=int,
                        help="UDP port to listen for OSC (default: 5555)")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Log all messages to console")
    parser.add_argument("--verbose-remote", action="store_true",
                        help="Log all child console output")
    parser.add_argument("--max-bufsize", default=2048,
                        help="Maximum JACK buffer size to support (default: 2048 frames)")
    parser.add_argument("--no-gui", action="store_true",
                        help="Do not launch the GUI engine")
    parser.add_argument("--no-dsp", action="store_true",
                        help="Do not launch the DSP engine")
    parser.add_argument("--no-default", action="store_true",
                        help="Do not create a default patch")
    parser.add_argument("--no-restart", action="store_true",
                        help="Do not restart DSP engine if it crashes")
    parser.add_argument("--no-onload", action="store_true",
                        help="Do not run onload/loadbang functions")
    parser.add_argument("--help-builtins", action="store_true",
                        help="Display help on builtin objects and exit")
    parser.add_argument("-s", "--socket-path", default="/tmp/mfp_rpcsock",
                        help="Path to create Unix-domain socket for RPC")
    parser.add_argument("-d", "--debug", action="store_true",
                        help="Enable debugging behaviors")

    # batch mode options
    parser.add_argument("-b", "--batch", action="store_true",
                        help="Run in batch mode")
    parser.add_argument("-a", "--args", default='',
                        help="Batch mode patch arguments")
    parser.add_argument("-I", "--batch-input", default=None,
                        help="Batch mode input file")
    parser.add_argument("-e", "--batch-eval", action="store_true",
                        help="Call eval() on input before sending")

    args = vars(parser.parse_args())

    # test imports to make sure everything is installed properly
    test_imports()

    # create the app object
    app = MFPApp()

    # configure some things from command line
    app.no_gui = args.get("no_gui") or args.get("help_builtins") or args.get("help")
    app.no_dsp = args.get("no_dsp") or args.get("help_builtins") or args.get("help")

    app.no_default = args.get("no_default")
    app.no_restart = args.get("no_restart")
    app.no_onload = args.get("no_onload")
    app.dsp_inputs = args.get("inputs")
    app.dsp_outputs = args.get("outputs")
    app.midi_inputs = args.get("midi_ins")
    app.midi_outputs = args.get("midi_outs")
    app.osc_port = args.get("osc_udp_port")
    app.searchpath = ':'.join(args.get("patch_path"))
    app.extpath = ':'.join(args.get("lib_path"))
    app.max_blocksize = args.get("max_bufsize")
    app.socket_path = args.get("socket_path")
    app.debug = args.get("debug")

    log.log_thread = threading.get_ident()
    log.log_loop = asyncio.get_event_loop()

    if args.get('batch'):
        app.batch_mode = True
        app.batch_args = args.get("args")
        app.batch_input_file = args.get("batch_input")
        app.batch_eval = args.get("batch_eval", False)
        app.no_gui = True
        log.log_quiet = True

    if args.get("verbose"):
        log.log_verbose = True
        log.log_force_console = True

    if args.get("verbose_remote"):
        app.debug_remote = True

    if app.no_gui:
        log.debug("Not starting GUI services")

    if app.no_dsp:
        log.debug("Not starting DSP engine")

    if app.no_default:
        log.debug("Not creating default patch")

    # launch processes and threads
    import signal
    signal.signal(signal.SIGTERM, exit_sighandler)

    try:
        await app.setup()
    except (StartupError, KeyboardInterrupt, SystemExit):
        log.debug("Setup did not complete properly, exiting")
        await app.finish()
        return

    # ok, now start configuring the running system
    add_evaluator_defaults()
    builtins.register()

    for libname in args.get("init_lib"):
        app.load_extension(libname)

    evaluator = Evaluator()

    pyfiles = args.get("init_file", [])
    for f in pyfiles:
        fullpath = utils.find_file_in_path(f, app.searchpath)
        log.debug("initfile: Looking for", f)
        if not fullpath:
            log.debug("initfile: Cannot find file %s, skipping" % f)
            continue

        try:
            os.stat(fullpath)
        except OSError:
            log.debug("initfile: Error accessing file", fullpath)
            continue
        try:
            evaluator.exec_file(fullpath)
        except Exception as e:
            log.debug("initfile: Exception while loading initfile", f)
            log.debug(e)

    if app.debug:
        import yappi
        yappi.start()

    if args.get("help"):
        log.log_debug = None
        log.log_file = None
        parser.print_help()
        await app.finish()
    elif args.get("help_builtins"):
        log.log_debug = None
        log.log_file = None
        await app.open_file(None)
        for name, factory in sorted(app.registry.items()):
            if hasattr(factory, 'doc_tooltip_obj'):
                print("%-12s : %s" % ("[%s]" % name, factory.doc_tooltip_obj))
            else:
                try:
                    o = factory(name, None, app.patches['default'], None, "")
                    print("%-12s : %s" % ("[%s]" % name, o.doc_tooltip_obj))
                except Exception as e:
                    import traceback
                    print("(caught exception trying to create %s)" % name, e)
                    traceback.print_exc()
                    print("%-12s : No documentation found" % ("[%s]" % name,))
        await app.finish()
    else:
        patchfiles = args.get("patchfile")
        if app.batch_mode:
            try:
                if len(patchfiles) == 1:
                    app.batch_obj = patchfiles[0]
                    await app.exec_batch()
                else:
                    log.debug("Batch mode requires exactly one input file")
            finally:
                await app.finish()

        else:
            # create initial patch
            if len(patchfiles):
                for p in patchfiles:
                    await app.open_file(p)
            elif not app.no_default:
                await app.open_file(None)
            # allow session management
            app.session_management_setup()

        try:
            await QuittableThread.await_all()
        except (KeyboardInterrupt, SystemExit):
            log.log_force_console = True
            await app.finish()

        for thread in app.leftover_threads:
            thread.join()

    if app.debug:
        import yappi
        yappi.stop()
        yappi.convert2pstats(yappi.get_func_stats()).dump_stats('mfp-main-funcstats.pstats')


def main_sync_wrapper():
    import asyncio
    asyncio.run(main())
