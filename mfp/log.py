import sys 
from datetime import datetime

log_time_base = datetime.now()
log_module = "main"

log_file = sys.stdout 
log_func = None 
log_debug = True 

def make_log_entry(tag, *parts):
	global log_time_base 
	
	msg = ' '.join([ str(p) for p in parts])
	dt = (datetime.now() - log_time_base).total_seconds()
	ts = "%.3f" % dt
	return "[%8s %6s] %s\n" % (ts, tag, msg)

def write_log_entry(msg):
	global log_file 
	global log_func 

	if log_func: 
		log_func(msg)
	elif log_file:
		log_file.write(msg)

def debug(* parts):
	global log_debug 
	global log_module 

	if not log_debug:
		return 
	else:
		write_log_entry(make_log_entry(log_module, *parts))

def logprint(* parts):
	write_log_entry(make_log_entry("print", * parts))

