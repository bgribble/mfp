import sys 
from datetime import datetime

log_time_base = datetime.now()
log_module = "main"

log_file = sys.stdout 

def debug(* parts):
	global log_time_base 
	global log_module
	global log_file 
	msg = ' '.join([ str(p) for p in parts])
	dt = (datetime.now() - log_time_base).total_seconds()
	log_file.write("[%.3f %s] %s\n" % (dt, log_module, msg))
	return 
