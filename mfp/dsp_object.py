#! /usr/bin/env python2.6
'''
dsp_slave.py
Python main loop for DSP subprocess

Copyright (c) 2010 Bill Gribble <grib@billgribble.com>
'''

from .rpc import RPCWrapper, rpcwrap
from . import log


class DSPObject(RPCWrapper):
    objects = {}

    def __init__(self, obj_id, name, inlets, outlets, params, context_id):
        self.obj_id = obj_id
        RPCWrapper.__init__(self, obj_id, name, inlets, outlets, params, context_id)

    @rpcwrap
    def reset(self):
        pass

    @rpcwrap
    def delete(self):
        pass

    @rpcwrap
    def getparam(self, param):
        pass

    @rpcwrap
    def setparam(self, param, value):
        pass

    @rpcwrap
    def connect(self, outlet, target, inlet):
        pass

    @rpcwrap
    def disconnect(self, outlet, target, inlet):
        pass


class DSPCommand (RPCWrapper):
    @rpcwrap
    def log_to_gui(self):
        pass

    @rpcwrap
    def get_dsp_params(self):
        pass

    @rpcwrap
    def get_latency(self):
        pass

    @rpcwrap
    def ext_load(self, extension_path):
        pass

    @rpcwrap
    def reinit(self, client_name, max_bufsize, num_inputs, num_outputs):
        pass

