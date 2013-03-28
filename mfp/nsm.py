#! /usr/bin/env python
'''
nsm.py: NON session manager support

See http://non.tuxfamily.org/nsm/API.html for API details 

Copyright (c) 2013 Bill Gribble <grib@billgribble.com>
'''

import os


def nsm_announce(nsm_url):
    from .main import MFPApp
    print "nsm: sending announce tp", nsm_url, "/nsm/server/announce"
    MFPApp().osc_mgr.send(nsm_url, "/nsm/server/announce", 
                          "mfp", ":switch:progress:message:", 
                          os.environ.get("_"), 1, 0, os.getpid())

def nsm_reply_handler(path, args, types, src, data):
    print "nsm: got reply:", path, args, types, src, data 
    if args[1] == "/nsm/server/announce":
        print "nsm: got announce reply", args

def nsm_error_handler(path, args, types, src, data):
    print "nsm error:", path, args, types, src, data 
    pass

def nsm_open_handler(path, args, types, src, data):
    print "nsm open:", path, args, types, src, data 
    pass

def nsm_save_handler(path, args, types, src, data):
    print "nsm save:", path, args, types, src, data
    pass

def nsm_session_loaded(path, args, types, src, data):
    print "nsm session_loaded:", path, args, types, src, data
    pass

def init_nsm():
    from .main import MFPApp
    nsm_url = os.environ.get("NSM_URL")
    if nsm_url is None: 
        return False 

    MFPApp().osc_mgr.add_method("/reply", None, nsm_reply_handler, None) 
    MFPApp().osc_mgr.add_method("/error", None, nsm_error_handler, None)
    MFPApp().osc_mgr.add_method("/nsm/client/open", None, nsm_open_handler, None)
    MFPApp().osc_mgr.add_method("/nsm/client/save", None, nsm_save_handler, None)
    MFPApp().osc_mgr.add_method("/nsm/client/session_is_loaded", None, nsm_session_loaded, 
                               None)

    nsm_announce(nsm_url) 
    MFPApp().osc_mgr.send
