#! /usr/bin/env python
'''
sendrcv.py: Bus/virtual wire objects.

Copyright (c) 2012 Bill Gribble <grib@billgribble.com>
'''

import time 
from ..utils import QuittableThread 
from ..processor import Processor
from ..mfp_app import MFPApp
from ..patch import Patch
from .. import Uninit

from mfp import log 
class Send (Processor):
    display_type = "sendvia" 
    doc_tooltip_obj = "Send messages to a named receiver (create with 'send via' GUI object)"
    doc_tooltip_inlet = ["Message to send", "Update receiver (default: initarg 0)" ]

    bus_type = "bus"
    
    def __init__(self, init_type, init_args, patch, scope, name):
        self.dest_name = None
        self.dest_inlet = 0
        self.dest_obj = None
        self.dest_obj_owned = False 

        Processor.__init__(self, 2, 1, init_type, init_args, patch, scope, name)

        # needed so that name changes happen timely 
        self.hot_inlets = [0, 1]

        initargs, kwargs = self.parse_args(init_args)
        if len(initargs) > 1:
            self.dest_inlet = initargs[1]
        if len(initargs):
            self.dest_name = initargs[0]

        self.gui_params["label_text"] = self.dest_name

    def method(self, message, inlet=0):
        if inlet == 0:
            self.trigger()
        else: 
            self.inlets[inlet] = Uninit
            message.call(self)

    def onload(self, phase):
        self._connect(self.dest_name)

    def load(self, params):
        Processor.load(self, params)
        gp = params.get('gui_params', {})
        self.gui_params['label_text'] = gp.get("label_text") or self.dest_name

    def save(self): 
        prms = Processor.save(self)
        conns = prms['connections']
        if conns and self.dest_obj: 
            pruned = [] 
            for objid, port in conns[0]:
                if objid != self.dest_obj.obj_id:
                    pruned.append([objid, port])
            conns[0] = pruned
            
        return prms

    def _connect(self, dest_name):
        if self.dest_name == dest_name and self.dest_obj is not None: 
            return 

        if self.dest_obj is not None and self.dest_name != dest_name:
            self.dest_obj.disconnect(0, self, 0)
            self.dest_obj = None 
            self.dest_obj_owned = False 
        self.dest_name = dest_name 

        obj = MFPApp().resolve(self.dest_name, self, True)
        if (obj is not None 
            and ((isinstance(obj, Patch) and self.scope == obj.default_scope) 
                 or obj.scope == self.scope 
                 or self.dest_name in ("patch", "app")
                 or "." in self.dest_name)):
            self.dest_obj = obj 
            self.dest_obj_owned = False 
        else: 
            self.dest_obj = MFPApp().create(self.bus_type, "", self.patch, 
                                            self.scope, self.dest_name)
            self.dest_obj_owned = True 
            self.dest_name = self.dest_obj.name
            
        if self.dest_obj and ((self, 0) not in self.dest_obj.connections_in[0]):
            self.connect(0, self.dest_obj, 0, False)

        self.init_args = '"%s"' % self.dest_name 
        self.gui_params["label_text"] = self.dest_name
        if self.gui_created:
            MFPApp().gui_command.configure(self.obj_id, self.gui_params)

    def trigger(self):
        if self.inlets[1] is not Uninit: 
            self._connect(self.inlets[1])
            self.inlets[1] = Uninit 

        if self.inlets[0] is not Uninit:
            self.outlets[0] = self.inlets[0]
            self.inlets[0] = Uninit 

    def assign(self, patch, scope, name):
        pret = Processor.assign(self, patch, scope, name)
        if self.dest_obj_owned and self.dest_obj: 
            buscon = self.dest_obj.connections_out[0]
            self.dest_obj.assign(patch, scope, self.dest_obj.name)
            for obj, port in buscon: 
                self.dest_obj.disconnect(0, obj, 0)
        return pret

    def tooltip_extra(self):
        return "<b>Connected to:</b> %s" % self.dest_name

class SendSignal (Send):
    doc_tooltip_obj = "Send signals to the specified name"
    display_type = "sendsignalvia"
    bus_type = "bus~"

    def __init__(self, init_type, init_args, patch, scope, name): 
        self.dest_name = None
        self.dest_inlet = 0
        self.dest_obj = None
        self.dest_obj_owned = False 

        Processor.__init__(self, 2, 1, init_type, init_args, patch, scope, name)
        
        self.dsp_inlets = [0]
        self.dsp_outlets = [0] 
        self.dsp_init("noop~")

        # needed so that name changes happen timely 
        self.hot_inlets = [0, 1]

        initargs, kwargs = self.parse_args(init_args)
        if len(initargs) > 1:
            self.dest_inlet = initargs[1]
        if len(initargs):
            self.dest_name = initargs[0]

        self.gui_params["label_text"] = self.dest_name


class MessageBus (Processor): 
    display_type = "hidden"
    do_onload = False 
    save_to_patch = False 

    def __init__(self, init_type, init_args, patch, scope, name):
        Processor.__init__(self, 1, 1, init_type, init_args, patch, scope, name)

    def trigger(self):
        self.outlets[0] = self.inlets[0]
        self.inlets[0] = Uninit 

    def method(self, message, inlet=0):
        if inlet == 0:
            self.trigger()
        else: 
            self.inlets[inlet] = Uninit
            message.call(self)

class SignalBus (Processor): 
    display_type = "hidden"
    do_onload = False 
    save_to_patch = False 

    def __init__(self, init_type, init_args, patch, scope, name):
        Processor.__init__(self, 1, 1, init_type, init_args, patch, scope, name)
        self.dsp_inlets = [0]
        self.dsp_outlets = [0]
        self.dsp_init("noop~")

    def trigger(self):
        self.outlets[0] = self.inlets[0]

class Recv (Processor):
    doc_tooltip_obj = "Receive messages to the specified name" 
    doc_tooltip_inlet = [ "Passthru input" ]
    doc_tooltip_outlet = [ "Passthru output" ]

    do_onload = False 

    def __init__(self, init_type, init_args, patch, scope, name):
        Processor.__init__(self, 2, 1, init_type, init_args, patch, scope, name)
        initargs, kwargs = self.parse_args(init_args)

        self.src_name = self.name 
        self.src_obj = None 
        if len(initargs):
            self.src_name = initargs[0]
        else: 
            self.src_name = self.name

        self.gui_params["label_text"] = self.src_name

        # needed so that name changes happen timely 
        self.hot_inlets = [0, 1]

        self.monitor_thread = QuittableThread(target=self._monitor)
        self.monitor_thread.start()

    def _monitor(self, threadobj): 
        # FIXME race between monitor and trigger method 
        while not threadobj.join_req:
            if self.src_obj is not None and self.src_obj.status == Processor.DELETED:
                self.src_obj.disconnect(0, self, 0)
                self.src_obj = None 

            if not len(self.connections_in[0]): 
                self.src_obj = None 

            if self.src_obj is None and self.src_name is not None:
                self._connect(self.src_name)
                    
            time.sleep(0.25)

    def delete(self):
        self.monitor_thread.join_req = True
        Processor.delete(self)

    def method(self, message, inlet):
        if inlet == 0:
            self.trigger()
        else:
            self.inlets[inlet] = Uninit
            message.call(self)

    def load(self, params):
        Processor.load(self, params)
        gp = params.get('gui_params', {})
        self.gui_params['label_text'] = gp.get("label_text") or self.src_name

    def _connect(self, src_name):
        src_obj = MFPApp().resolve(src_name, self, True)
        if src_obj:
            self.src_obj = src_obj
            self.init_args = '"%s"' % src_name 
            self.gui_params["label_text"] = src_name
            self.src_name = src_name 
            self.src_obj.connect(0, self, 0, False)

            if self.gui_created:
                MFPApp().gui_command.configure(self.obj_id, self.gui_params)

    def trigger(self):
        if self.inlets[1] is not Uninit:
            if self.inlets[1] != self.src_name:
                if self.src_obj:
                    self.src_obj = None 
                self._connect(self.inlets[1])
            self.inlets[1] = Uninit

        if self.src_name and self.src_obj is None:
            self._connect(self.src_name)

        if self.inlets[0] is not Uninit:
            self.outlets[0] = self.inlets[0]
            self.inlets[0] = Uninit 

    def tooltip_extra(self):
        return "<b>Connected to:</b> %s" % self.src_name

class RecvSignal (Recv): 
    doc_tooltip_obj = "Receive signals to the specified name"
    
    def __init__(self, init_type, init_args, patch, scope, name):
        Processor.__init__(self, 2, 1, init_type, init_args, patch, scope, name)
        initargs, kwargs = self.parse_args(init_args)

        self.src_name = None 
        self.src_obj = None 
        if len(initargs): 
            self.src_name = initargs[0]
        else: 
            self.src_name = self.name 

        self.gui_params["label_text"] = self.src_name

        # needed so that name changes happen timely 
        self.hot_inlets = [0, 1]

        self.dsp_inlets = [0]
        self.dsp_outlets = [0]
        self.dsp_init("noop~")

        if len(initargs):
            self._connect(initargs[0])

        self.monitor_thread = QuittableThread(target=self._monitor)
        self.monitor_thread.start()

    def _monitor(self, threadobj): 
        # FIXME race between monitor and trigger method 
        while not threadobj.join_req:
            if self.src_obj is not None and self.src_obj.status == Processor.DELETED:
                self.src_obj = None 

            if self.src_obj is None and self.src_name is not None:
                self._connect(self.src_name)
                    
            time.sleep(0.25)
def register():
    MFPApp().register("send", Send)
    MFPApp().register("recv", Recv)
    MFPApp().register("s", Send)
    MFPApp().register("r", Recv)
    MFPApp().register("send~", SendSignal)
    MFPApp().register("recv~", RecvSignal)
    MFPApp().register("s~", SendSignal)
    MFPApp().register("r~", RecvSignal)
    MFPApp().register("bus", MessageBus)
    MFPApp().register("bus~", SignalBus)
