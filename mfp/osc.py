#! /usr/bin/env python2.7
'''
osc.py: OSC server for MFP

Copyright (c) 2012 Bill Gribble <grib@billgribble.com>
'''

from .utils import QuittableThread
from . import log
import liblo


class MFPOscManager(QuittableThread):
    def __init__(self, port):
        self.port = port
        self.server = None
        self.default_handlers = [] 

        try:
            self.server = liblo.Server(self.port)
        except Exception, err:
            print type(err), str(err)

        self.server.add_method(None, None, self.default)
        QuittableThread.__init__(self)

    def add_method(self, path, args, handler, data=None):
        if data is not None:
            self.server.add_method(path, args, handler, data)
        else:
            self.server.add_method(path, args, handler)

        # put the default method back at the end of the line 
        # there's a tiny little race condition here 
        self.server.del_method(None, None)
        self.server.add_method(None, None, self.default)

    def del_method(self, path, args):
        self.server.del_method(path, args)

    def default(self, path, args, types, src):
        print "Received unmatched OSC data:", path, args, types
        for handler, data in self.default_handlers: 
            handler(path, args, types, src, data)
        return True

    def add_default(self, handler, data=None):
        self.default_handlers.append((handler, data))

    def del_default(self, handler, data=None):
        self.default_handlers = [ h for h in self.default_handlers 
                                 if h != (handler, data) ]

    def send(self, target, path, *data):
        m = liblo.Message(path)
        m.add(*data)
        self.server.send(target, m)

    def run(self):
        from datetime import datetime
        while not self.join_req and self.server is not None:
            self.server.recv(100)
        log.debug("OSC server exiting")
