import sys 
from datetime import datetime

log_time_base = datetime.now()
log_module = "main"

log_file = sys.stdout 
log_func = None 
log_debug = True 

def debug(* parts):
	global log_time_base 
	global log_module
	global log_file 
	global log_func 
	global log_debug 

	if not log_debug:
		return 

	msg = ' '.join([ str(p) for p in parts])
	dt = (datetime.now() - log_time_base).total_seconds()
	ts = "%.3f" % dt
	logentry = "[%8s %6s] %s" % (ts, log_module, msg)

	if log_func: 
		log_func(logentry)
	elif log_file:
		log_file.write(logentry + "\n")


	return 

def logprint(* parts):
	global log_time_base 
	global log_module
	global log_file 
	global log_func 
	global log_debug 

	if not log_debug:
		return 

	msg = ' '.join([ str(p) for p in parts])
	dt = (datetime.now() - log_time_base).total_seconds()
	logentry = "[%.3f print] %s" % (dt, msg)

	if log_func: 
		log_func(logentry)
	elif log_file:
		log_file.write(logentry + "\n")

	return 
