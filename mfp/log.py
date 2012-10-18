
from datetime import datetime

log_time_base = datetime.now()
log_module = "main"

def debug(* parts):
	global log_time_base 
	global log_module
	msg = ' '.join([ str(p) for p in parts])
	dt = (datetime.now() - log_time_base).total_seconds()
	print "[%.3f %s] %s" % (dt, log_module, msg)
