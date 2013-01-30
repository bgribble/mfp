#! /usr/bin/env python
'''
oscutils.py -- Open Sound Control builtins for MFP 

Copyright (c) 2013 Bill Gribble <grib@billgribble.com>
'''

from ..processor import Processor 
from ..main import MFPApp 
from ..bang import Uninit 

class OSCPacket(object):
    def __init__(self, payload):
        self.payload = payload 


class OSCIn (Processor):
    def __init__(self, init_type, init_args, patch, scope, name):
        self.path = None 
        self.types = None 
        self.handler = None 
        self.learning = False 

        Processor.__init__(self, 1, 1, init_type, init_args, patch, scope, name)

        initargs, kwargs = self.parse_args(init_args) 
        if len(initargs) > 0:
            self.path = initargs[0] 
        if len(initargs) > 1:
            self.types = initargs[1]

    def trigger(self):
        need_update = False 
        if isinstance(self.inlets[0], OSCPacket): 
            self.outlets[0] = self.inlets[0].payload
            self.inlets[0] = Uninit 
        elif isinstance(self.inlets[0], dict):
            path = self.inlets[0].get("path")
            if path: 
                self.path = path
                need_update = True 
            types = self.inlets[0].get("types")
            if types: 
                self.types = types
                need_update = True 
        
        if need_update: 
            if self.handler is not None:
                MFPApp().osc_mgr.del_method(self.handler, self.types)
                self.handler = None 
            self.handler = MFPApp().osc_mgr.add_method(self.path, self.types, self._handler)

    def _handler(self, path, args, types, src, data):
        if types[0] == 's':
            self.send(OSCPacket(self.patch.parse_obj(args[0])))
        else:
            self.send(OSCPacket(args[0]))
    
    def _learn_handler(self, path, args, types, src, data):
        MFPApp().osc_mgr.del_default(self._learn_handler)
        self.path = path
        self.types = types 
        MFPApp().osc_mgr.add_method(self.path, self.types, self._handler)
        self._handler(path, args, types, src, data)

    def learn(self):
        self.learning = True 
        MFPApp().osc_mgr.add_default(self._learn_handler)

class OSCOut (Processor): 
    def __init__(self, init_type, init_args, patch, scope, name):
        self.host = None 
        self.port = None 
        self.path = None 

        Processor.__init__(self, 3, 0, init_type, init_args, patch, scope, name)

        initargs, kwargs = self.parse_args(init_args) 
        if len(initargs) > 0:
            parts = initargs[0].split(":")
            self.host = parts[0]
            if len(parts) > 1:
                self.port = int(parts[1])
        if len(initargs) > 1:
            self.path = initargs[1]

    def trigger(self):
        if self.inlets[2] is not Uninit:
            self.path = self.inlets[2]
            self.inlets[2] = Uninit 
        if self.inlets[1] is not Uninit:
            if isinstance(self.inlets[1], str): 
                parts = self.inlets[1].split(":")
                self.host = parts[0]
                if len(parts) > 1:
                    self.port = int(parts[1])
            elif isinstance(self.inlets[1], (float, int)):
                self.port = int(self.inlets[1])

            self.inlets[1] = Uninit 
        MFPApp().osc_mgr.send((self.host, self.port), self.path, self.inlets[0])
        self.inlets[0] = Uninit 

def register():
    MFPApp().register("osc_in", OSCIn)
    MFPApp().register("osc_out", OSCOut)

