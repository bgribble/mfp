#! /usr/bin/env python2.6
'''
dsp_slave.py
Python main loop for DSP subprocess

Copyright (c) 2010 Bill Gribble <grib@billgribble.com>
'''
import mfpdsp
from mfp.rpc_wrapper import RPCWrapper, rpcwrap
from . import log


class DSPObject(RPCWrapper):
    objects = {}
    c_objects = {}

    def __init__(self, obj_id, name, inlets, outlets, params={}):
        self.obj_id = obj_id
        RPCWrapper.__init__(self, obj_id, name, inlets, outlets, params)
        if self.local:
            self.c_obj = mfpdsp.proc_create(name, inlets, outlets, params)
            DSPObject.objects[self.obj_id] = self.c_obj
            DSPObject.c_objects[self.c_obj] = self.obj_id

    @rpcwrap
    def reset(self):
        return mfpdsp.proc_reset(self.c_obj)

    @rpcwrap
    def delete(self):
        return mfpdsp.proc_destroy(self.c_obj)

    @rpcwrap
    def getparam(self, param):
        return mfpdsp.proc_getparam(self.c_obj, param)

    @rpcwrap
    def setparam(self, param, value):
        print "setparam:", self, param, value
        return mfpdsp.proc_setparam(self.c_obj, param, value)

    @rpcwrap
    def connect(self, outlet, target, inlet):
        return mfpdsp.proc_connect(self.c_obj, outlet, DSPObject.objects.get(target),
                                   inlet)

    @rpcwrap
    def disconnect(self, outlet, target, inlet):
        return mfpdsp.proc_disconnect(self.c_obj, outlet, DSPObject.objects.get(target),
                                      inlet)


class DSPCommand (RPCWrapper):
    @rpcwrap
    def log_to_gui(self):
        from main import MFPCommand
        # log to GUI
        log.log_func = lambda msg: MFPCommand().log_write(msg)
        log.debug("DSP process logging to GUI")
        return True

    @rpcwrap
    def get_dsp_params(self):
        srate = mfpdsp.dsp_samplerate()
        blksize = mfpdsp.dsp_blocksize()
        return (srate, blksize)

def dsp_init(pipe, num_inputs, num_outputs):
    from main import MFPCommand
    import threading
    import os

    log.log_module = "dsp"
    log.debug("DSP thread started, pid =", os.getpid())

    RPCWrapper.node_id = "JACK DSP"
    DSPObject.pipe = pipe
    DSPObject.local = True
    MFPCommand.local = False

    pipe.on_finish(dsp_finish)

    # start JACK thread
    mfpdsp.dsp_startup(num_inputs, num_outputs)
    mfpdsp.dsp_enable()

    # start response thread
    rt = threading.Thread(target=dsp_response)
    rt.start()

ttq = False


def dsp_response(*args):
    from .main import MFPCommand

    # from mfp.main import MFPCommand
    # FIXME there is a thread mess waiting just offstage
    # with multiple threads invoking send() in main process
    global ttq
    mfp = MFPCommand()
    while not ttq:
        messages = mfpdsp.dsp_response_wait()
        if messages is None:
            continue
        for m in messages:
            recip = DSPObject.c_objects.get(m[0], -1)
            mfp.send(recip, -1, (m[1], m[2]))


def dsp_finish():
    global ttq
    ttq = True
    log.log_func = None
    mfpdsp.dsp_shutdown()
