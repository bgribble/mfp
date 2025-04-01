#! /usr/bin/env python
'''
dsp_object.py
Classes to represent DSP objects

Copyright (c) 2010 Bill Gribble <grib@billgribble.com>
'''

from carp.service import apiclass


class DSPContext:
    registry = {}

    def __init__(self, node_id, context_id, context_name=""):
        self.node_id = node_id
        self.context_id = context_id
        self.context_name = context_name
        self.input_latency = 0
        self.output_latency = 0

    @classmethod
    def create(cls, node_id, context_id, context_name):
        ctxt = DSPContext(node_id, context_id, context_name)
        cls.registry[(node_id, context_id)] = ctxt
        return ctxt

    @classmethod
    def lookup(cls, node_id, context_id):
        return cls.registry.get((node_id, context_id))

    def get_latency(self):
        return (self.input_latency, self.output_latency)

    def __eq__(self, other):
        if isinstance(other, DSPContext):
            return (self.node_id == other.node_id) and (self.context_id == other.context_id)
        else:
            return False

    def __ne__(self, other):
        if isinstance(other, DSPContext):
            return (self.node_id != other.node_id) or (self.context_id != other.context_id)
        else:
            return True


@apiclass
class DSPObject:
    def reset(self):
        pass

    def delete(self):
        pass

    def getparam(self, param):
        pass

    def setparam(self, param, value):
        pass

    def setparams(self, **kwargs):
        pass

    def connect(self, outlet, target, inlet):
        pass

    def disconnect(self, outlet, target, inlet):
        pass
