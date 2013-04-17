#! /usr/bin/env python
'''
sendrcv.py: Bus/virtual wire objects.

Copyright (c) 2012 Bill Gribble <grib@billgribble.com>
'''

import time 
from ..quittable_thread import QuittableThread 
from ..processor import Processor
from ..main import MFPApp
from .. import Uninit


class Send (Processor):
    doc_tooltip_obj = "Send messages to a named receiver (create with 'via' GUI object)"
    doc_tooltip_inlet = ["Message to send", "Update receiver (default: initarg 0)" ]

    def __init__(self, init_type, init_args, patch, scope, name):
        Processor.__init__(self, 2, 0, init_type, init_args, patch, scope, name)

        self.dest_name = None
        self.dest_inlet = 0
        self.dest_obj = None

        # needed so that name changes happen timely 
        self.hot_inlets = [0, 1]

        initargs, kwargs = self.parse_args(init_args)
        if len(initargs) > 1:
            self.dest_inlet = initargs[1]
        if len(initargs):
            self.dest_name = initargs[0]

        self.gui_params["label"] = self.dest_name

    def method(self, message, inlet=0):
        if inlet == 0:
            self.trigger()
        else: 
            message.call(self)

    def trigger(self):
        if self.inlets[1] is not Uninit:
            self.dest_name = self.inlets[1]
            self.init_args = '"%s"' % self.dest_name 
            self.gui_params["label"] = self.dest_name
            self.dest_obj = None
            self.inlets[1] = Uninit
            if self.gui_created:
                MFPApp().gui_command.configure(self.obj_id, self.gui_params)

        if self.dest_obj is None:
            self.dest_obj = MFPApp().resolve(self.dest_name, self)

        if self.inlets[0] is not Uninit and self.dest_obj is not None:
            self.dest_obj.send(self.inlets[0], inlet=self.dest_inlet)
            self.inlets[0] = Uninit 

class SendSignal (Send):
    doc_tooltip_obj = "Send signals to the specified name"

    def __init__(self, init_type, init_args, patch, scope, name): 
        Send.__init__(self, init_type, init_args, patch, scope, name)
        
        self.dsp_inlets = [0]
        self.dsp_outlets = [0] 
        self.dsp_init("noop~")

        self.monitor_thread = QuittableThread(target=self._monitor)
        self.monitor_thread.start()

    def _monitor(self, threadobj): 
        # FIXME race between monitor and trigger method 
        while not threadobj.join_req:
            if self.dest_obj is not None and self.dest_obj.status == Processor.DELETED:
                self.dest_obj = None 

            if self.dest_obj is None and self.dest_name is not None:
                self.reconnect()
                    
            time.sleep(0.5)

    def reconnect(self): 
        self.dest_obj = MFPApp().resolve(self.dest_name, self)
        if self.dest_obj and self.dest_inlet not in self.dest_obj.dsp_inlets:
            self.dest_obj = None

        if self.dest_obj is not None:
            self.dsp_obj.connect(0, self.dest_obj.obj_id, 
                                 self.dest_obj.dsp_inlets.index(self.dest_inlet))

class MessageBus (Processor): 
    display_type = "hidden"
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
            message.call(self)

class SignalBus (Processor): 
    display_type = "hidden"
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

    bus_type = "bus" 

    def __init__(self, init_type, init_args, patch, scope, name):
        Processor.__init__(self, 2, 1, init_type, init_args, patch, scope, name)
        initargs, kwargs = self.parse_args(init_args)

        self.bus_name = self.name 
        if len(initargs):
            self.bus_name = initargs[0]

        self.gui_params["label"] = self.bus_name
        self.bus_obj = None 

        # needed so that name changes happen timely 
        self.hot_inlets = [0, 1]


    def method(self, message, inlet):
        if inlet == 0:
            self.trigger()
        else:
            message.call(self)

    def trigger(self):
        if self.inlets[1] is not Uninit: 
            self.bus_connect(self.inlets[1])
            self.inlets[1] = Uninit 

        if self.inlets[0] is not Uninit:
            self.outlets[0] = self.inlets[0]
            self.inlets[0] = Uninit 

    def onload(self, phase):
        if phase == 0:
            self.bus_connect(self.bus_name)

    def bus_connect(self, bus_name):
        if self.bus_obj is not None and self.bus_name != bus_name:
            self.bus_obj.disconnect(0, self, 0)
            self.bus_obj = None 
        self.bus_name = bus_name 

        obj = MFPApp().resolve(self.bus_name, self)
        if obj is not None:
            self.bus_obj = obj 
        else: 
            self.bus_obj = MFPApp().create(self.bus_type, "", self.patch, 
                                           self.scope, self.bus_name)
            
        if self.bus_obj and (self not in self.bus_obj.connections_out[0]):
            self.bus_obj.connect(0, self, 0)

        self.init_args = '"%s"' % self.bus_name 
        self.gui_params["label"] = self.bus_name

        if self.gui_created:
            MFPApp().gui_command.configure(self.obj_id, self.gui_params)


class RecvSignal (Recv): 
    doc_tooltip_obj = "Receive signals to the specified name"
    bus_type = "bus~"
    
    def __init__(self, init_type, init_args, patch, scope, name):
        Processor.__init__(self, 2, 1, init_type, init_args, patch, scope, name)
        initargs, kwargs = self.parse_args(init_args)

        self.gui_params["label"] = self.name
        self.bus_name = None 
        self.bus_obj = None 

        # needed so that name changes happen timely 
        self.hot_inlets = [0, 1]

        self.dsp_inlets = [0]
        self.dsp_outlets = [0]
        self.dsp_init("noop~")

        if len(initargs):
            self.bus_connect(initargs[0])


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
