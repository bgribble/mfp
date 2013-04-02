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

def nsm_announce():
    print "mfp.nsm: sending announce tp", nsm_url, 
    print "/nsm/server/announce mfp :switch:progress:message:", sys.argv[0], os.getpid()

    MFPApp().osc_mgr.send(nsm_url, "/nsm/server/announce", "mfp", ":switch:progress:message:", 
                          os.path.basename(sys.argv[0]), 1, 0, os.getpid())

def nsm_error(path, nsm_errcode, message):
    print "mfp.nsm: sending error to", path, nsm_errcode, message
    MFPApp().osc_mgr.send(nsm_url, path, nsm_errcode, message)

def nsm_reply(path, message):
    MFPApp().osc_mgr.send(nsm_url, "/reply", path, message) 

def nsm_reply_handler(path, args, types, src, data):
    print "mfp.nsm: got reply:", path, args, types, src, data 
    if args[0] == "/nsm/server/announce":
        log.debug("Under session management. Server says:", args[1])
        print "mfp.nsm: got announce reply", args

def nsm_error_handler(path, args, types, src, data):
    print "nsm error:", path, args, types, src, data 
    pass

def nsm_open_handler(path, args, types, src, data):
    print "nsm open:", path, args, types, src, data 

    projectpath = args[0]
    client_id = args[2]

    log.debug("Session manager requests open of", args[0])
    if os.path.isdir(projectpath):
        MFPApp().session_load(projectpath, client_id)
    elif not os.path.exists(projectpath):
        MFPApp().session_init(projectpath, client_id)
    else:
        nsm_error(path, -9, "Could not open session")    

    nsm_reply(path, "OK")
    pass

def nsm_save_handler(path, args, types, src, data):
    print "nsm save:", path, args, types, src, data

def nsm_session_loaded(path, args, types, src, data):
    print "nsm session_loaded:", path, args, types, src, data
    pass

def init_nsm():
    global nsm_url 
    nsm_url = os.environ.get("NSM_URL")
    if nsm_url is None: 
        return False 

    MFPApp().osc_mgr.add_method("/reply", None, nsm_reply_handler, None) 
    MFPApp().osc_mgr.add_method("/error", None, nsm_error_handler, None)
    MFPApp().osc_mgr.add_method("/nsm/client/open", None, nsm_open_handler, None)
    MFPApp().osc_mgr.add_method("/nsm/client/save", None, nsm_save_handler, None)
    MFPApp().osc_mgr.add_method("/nsm/client/session_is_loaded", None, nsm_session_loaded, 
                               None)

    nsm_announce() 
    MFPApp().osc_mgr.send
