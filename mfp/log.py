import sys
from datetime import datetime

log_time_base = datetime.now()
log_module = "main"

log_file = sys.stdout
log_func = None
log_debug = True
log_force_console = False 

def make_log_entry(tag, *parts):
    global log_time_base

    msg = ' '.join([str(p) for p in parts])
    dt = (datetime.now() - log_time_base).total_seconds()
    ts = "%.3f" % dt
    return "[%8s %6s] %s\n" % (ts, tag, msg)


def write_log_entry(msg, level=0):
    global log_file
    global log_func

    logged = False 
    if log_func:
        log_func(msg, level)
        logged = True 

    if log_file and ((not logged) or log_force_console):
        log_file.write(msg)


def error(* parts, **kwargs):
    global log_module
    if kwargs.has_key("module"):
        module = kwargs["module"]
    else: 
        module = log_module 

    write_log_entry(make_log_entry(module, *parts), level=2)

def warning(* parts, **kwargs):
    global log_module
    if kwargs.has_key("module"):
        module = kwargs["module"]
    else: 
        module = log_module 

    write_log_entry(make_log_entry(module, *parts), level=1)

def info(* parts, **kwargs):
    global log_module
    if kwargs.has_key("module"):
        module = kwargs["module"]
    else: 
        module = log_module 

    write_log_entry(make_log_entry(module, *parts), level=0)

def debug(* parts, **kwargs):
    global log_debug
    global log_module

    if kwargs.has_key("module"):
        module = kwargs["module"]
    else: 
        module = log_module 

    if not log_debug:
        return
    else:
        write_log_entry(make_log_entry(module, *parts))


def logprint(* parts):
    write_log_entry(make_log_entry("print", * parts))
