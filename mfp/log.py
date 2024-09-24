import asyncio
import inspect
import sys
import string
import threading
from datetime import datetime

log_time_base = datetime.now()
log_module = "main"

log_thread = None
log_loop = None
log_file = sys.stdout
log_quiet = False
log_raw = False
log_func = None
log_debug = True
log_force_console = False
log_verbose = False

ts_trans = str.maketrans("0123456789", "xxxxxxxxxx")


def make_log_entry(tag, *parts):

    msg = ' '.join([str(p) for p in parts])
    if log_quiet and not log_verbose and tag != "print":
        return None

    if log_raw and not log_verbose:
        return msg + '\n'

    dt = (datetime.now() - log_time_base).total_seconds()
    ts = "%.3f" % dt
    leader = "[%8s %6s]" % (ts, tag)

    if leader[:12].translate(ts_trans) == msg[:12].translate(ts_trans):
        if msg[-1] != '\n':
            msg = msg + '\n'
        return msg
    return "%s %s\n" % (leader, msg)


def write_log_entry(msg, level=0):
    logged = False
    if msg and log_func:
        rv = log_func(msg, level)
        if inspect.isawaitable(rv):
            current_thread = threading.get_ident()
            if current_thread == log_thread:
                asyncio.create_task(rv)
            else:
                asyncio.run_coroutine_threadsafe(rv, log_loop)

        logged = True

    if log_file and msg and ((not logged) or log_force_console):
        log_file.write(msg)


def rpclog(msg, level):
    levels = {0: "DEBUG", 1: "WARNING", 2: "ERROR", 3: "FATAL"}
    if msg:
        print("[LOG] %s: %s" % (levels.get(level, "DEBUG"), msg))
        sys.stdout.flush()


def error(* parts, **kwargs):
    if "module" in kwargs:
        module = kwargs["module"]
    else:
        module = log_module

    write_log_entry(make_log_entry(module, *parts), level=2)


def warning(* parts, **kwargs):
    if "module" in kwargs:
        module = kwargs["module"]
    else:
        module = log_module

    write_log_entry(make_log_entry(module, *parts), level=1)


def info(* parts, **kwargs):
    if "module" in kwargs:
        module = kwargs["module"]
    else:
        module = log_module

    write_log_entry(make_log_entry(module, *parts), level=0)


def debug(*parts, **kwargs):
    if "module" in kwargs:
        module = kwargs["module"]
    else:
        module = log_module

    if not log_debug:
        return
    else:
        write_log_entry(make_log_entry(module, *parts), level=0)


def debug_traceback(exc=None):
    import traceback
    if exc:
        tb = traceback.format_exception(exc)
        for l in tb:
            debug(l)
    else:
        tb = traceback.format_stack()
        for l in tb[:-2]:
            debug(l)


def logprint(*parts):
    write_log_entry(make_log_entry("print", *parts))
