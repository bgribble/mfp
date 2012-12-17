#! /usr/bin/env python2.7
'''
osc.py: OSC server for MFP

Copyright (c) 2012 Bill Gribble <grib@billgribble.com>
'''

from quittable_thread import QuittableThread
import liblo
from mfp import log


class MFPOscManager(QuittableThread):
    def __init__(self, port):
        self.port = port
        self.server = None

        try:
            self.server = liblo.Server(self.port)
        except Exception, err:
            print str(err)

        # self.server.add_method(None, None, self.default)
        QuittableThread.__init__(self)

    def add_method(self, path, args, handler, data=None):
        if data is not None:
            self.server.add_method(path, args, handler, data)
        else:
            self.server.add_method(path, args, handler)

    def del_method(self, path, args):
        self.server.del_method(path, args)

    def default(self, path, args, types, src):
        log.debug("OSC: unhandled message", path, args)

    def run(self):
        while not self.join_req and self.server is not None:
            self.server.recv(100)
        log.debug("OSC server exiting")
