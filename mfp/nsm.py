#! /usr/bin/env python
'''
nsm.py: NON session manager support

See http://non.tuxfamily.org/nsm/API.html for API details 

Copyright (c) 2013 Bill Gribble <grib@billgribble.com>
'''

from .main import MFPApp
import os, os.path
import sys 

from . import log 

nsm_url = None

# message send helpers 

def nsm_announce():
    MFPApp().osc_mgr.send(nsm_url, "/nsm/server/announce", "mfp", ":switch:progress:message:", 
                          os.path.basename(sys.argv[0]), 1, 0, os.getpid())

def nsm_error(path, nsm_errcode, message):
    MFPApp().osc_mgr.send(nsm_url, path, nsm_errcode, message)

def nsm_reply(path, message):
    MFPApp().osc_mgr.send(nsm_url, "/reply", path, message) 


# OSC handlers 

def nsm_reply_handler(path, args, types, src, data):
    print "mfp.nsm: got reply:", path, args, types, src, data 
    if args[0] == "/nsm/server/announce":
        log.debug("Under session management. Server says:", args[1])
    else: 
        print "mfp.nsm: Unhandled /reply message:", args

def nsm_error_handler(path, args, types, src, data):
    print "mfp.nsm error:", path, args, types, src, data 
    pass

def nsm_open_handler(path, args, types, src, data):
    print "mfp.nsm open:", path, args, types, src, data 

    projectpath = args[0]
    client_id = args[2]

    log.debug("Session manager requests open of", args[0])
    if os.path.isdir(projectpath):
        log.debug("Existing session found, opening")
        MFPApp().session_load(projectpath, client_id)
    elif not os.path.exists(projectpath):
        log.debug("Session not found, creating new")
        MFPApp().session_init(projectpath, client_id)
    else:
        log.debug("Error while trying to open session, signaling session manager")
        nsm_error(path, -9, "Could not open session")    

    nsm_reply(path, "OK")

def nsm_save_handler(path, args, types, src, data):
    print "mfp.nsm save:", path, args, types, src, data
    log.debug("Session manager requests session save")
    MFPApp().session_save()
    nsm_reply(path, "OK")

def nsm_loaded_handler(path, args, types, src, data):
    print "mfp.nsm loaded:", path, args, types, src, data
    #MFPApp().session_load(args[0], args[2])

# initialization

def init_nsm():
    global nsm_url 
    nsm_url = os.environ.get("NSM_URL")
    if nsm_url is None: 
        return False 

    MFPApp().osc_mgr.add_method("/reply", None, nsm_reply_handler, None) 
    MFPApp().osc_mgr.add_method("/error", None, nsm_error_handler, None)
    MFPApp().osc_mgr.add_method("/nsm/client/open", None, nsm_open_handler, None)
    MFPApp().osc_mgr.add_method("/nsm/client/save", None, nsm_save_handler, None)
    MFPApp().osc_mgr.add_method("/nsm/client/session_is_loaded", None, nsm_loaded_handler, 
                               None)

    nsm_announce() 
    MFPApp().osc_mgr.send
