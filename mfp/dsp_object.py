#! /usr/bin/env python2.6
'''
dsp_slave.py
Python main loop for DSP subprocess

Copyright (c) 2010 Bill Gribble <grib@billgribble.com>
'''

from .rpc import RPCWrapper, rpcwrap
from . import log


def dprint(func):
    def inner(*args, **kwargs):
        log.debug("%s: enter" % func.__name__ )
        rv = func(*args, **kwargs)
        log.debug("%s: leave" % func.__name__ )
        return rv
    return inner


class DSPObject(RPCWrapper):
    objects = {}
    c_objects = {}

    def __init__(self, obj_id, name, inlets, outlets, params={}):
        self.obj_id = obj_id
        RPCWrapper.__init__(self, obj_id, name, inlets, outlets, params)

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
        from .mfp_command import MFPCommand
        # log to GUI
        log.log_func = lambda msg: MFPCommand().log_write(msg)
        log.debug("DSP process logging to GUI")
        return True

    @rpcwrap
    def get_dsp_params(self):
        import mfpdsp
        srate = mfpdsp.dsp_samplerate()
        blksize = mfpdsp.dsp_blocksize()
        return (srate, blksize)

    @rpcwrap
    def get_latency(self):
        import mfpdsp
        in_latency = mfpdsp.dsp_in_latency()
        out_latency = mfpdsp.dsp_out_latency()
        return (in_latency, out_latency)

    @rpcwrap
    def ext_load(self, extension_path):
        import mfpdsp
        mfpdsp.ext_load(extension_path)

    @rpcwrap
    def reinit(self, client_name, max_bufsize, num_inputs, num_outputs):
        import mfpdsp
        mfpdsp.dsp_disable()
        mfpdsp.dsp_shutdown()
        mfpdsp.dsp_startup(client_name, max_bufsize, num_inputs, num_outputs)
        mfpdsp.dsp_enable()
        
def dsp_init(pipe, client_name, max_bufsize, num_inputs, num_outputs):
    from .mfp_command import MFPCommand
    import threading
    import os
    import sys 
    import DLFCN 

    sys.setdlopenflags(DLFCN.RTLD_NOW | DLFCN.RTLD_GLOBAL)
    import mfpdsp 

    log.log_module = "dsp"
    log.debug("DSP thread started, pid =", os.getpid())

    RPCWrapper.node_id = "JACK DSP"
    DSPObject.pipe = pipe
    DSPObject.local = True
    MFPCommand.local = False

    pipe.on_finish(dsp_finish)

    # start JACK thread
    mfpdsp.dsp_startup(client_name, max_bufsize, num_inputs, num_outputs)
    mfpdsp.dsp_enable()

    # start response thread
    rt = threading.Thread(target=dsp_response)
    rt.start()

ttq = False


def dsp_response(*args):
    import mfpdsp
    from .mfp_command import MFPCommand

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
    import mfpdsp
    mfpdsp.dsp_shutdown()
    global ttq
    ttq = True
    log.log_func = None
