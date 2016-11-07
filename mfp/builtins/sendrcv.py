#! /usr/bin/env python
'''
sendrcv.py: Bus/virtual wire objects.

Copyright (c) 2012-2015 Bill Gribble <grib@billgribble.com>
'''

from ..utils import TaskNibbler
from ..processor import Processor
from ..mfp_app import MFPApp
from .. import Uninit

from mfp import log

class Send (Processor):
    display_type = "sendvia" 
    doc_tooltip_obj = "Send messages to a named receiver (create with 'send via' GUI object)"
    doc_tooltip_inlet = ["Message to send", "Update receiver (default: initarg 0)" ]

    bus_type = "bus"

    task_nibbler = TaskNibbler()

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

        self.gui_params["label_text"] = self._mkdispname()

    def _mkdispname(self):
        nm = self.dest_name
        if self.dest_inlet:
            nm += '/{}'.format(self.dest_inlet)
        return nm

    def onload(self, phase):
        self._connect(self.dest_name, self.dest_inlet)

    def method(self, message, inlet=0):
        if inlet == 0:
            self.trigger()
        else: 
            self.inlets[inlet] = Uninit
            message.call(self)

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

    def connect(self, outlet, target, inlet, show_gui=True):
        Processor.connect(self, outlet, target, inlet, show_gui)
        if outlet == 0:
            self.dest_obj = target
            self.dest_inlet = inlet

    def _wait_connect(self):
        def recheck():
            return self._connect(self.dest_name, self.dest_inlet, False)
        Send.task_nibbler.add_task(recheck)

    def _connect(self, dest_name, dest_inlet, wait=True):
        # short-circuit if already conected 
        if (self.dest_name == dest_name and self.dest_inlet == dest_inlet
                and self.dest_obj is not None): 
            return True 

        # disconnect existing if needed 
        if self.dest_obj is not None:
            log.debug("[send] calling disconnect", self.obj_id, self.dest_obj.obj_id)
            self.disconnect(0, self.dest_obj, self.dest_inlet)
            self.dest_obj = None 
            self.dest_obj_owned = False 
        self.dest_name = dest_name 
        self.dest_inlet = dest_inlet

        # find the new endpoint
        obj = MFPApp().resolve(self.dest_name, self, True)

        if obj is None:
            # usually we create a bus if needed.  but if it's a reference to 
            # another top-level patch, no. 
            if ':' in self.dest_name or self.dest_inlet != 0:
                if wait:
                    self._wait_connect()
                return False
            else:
                self.dest_obj = MFPApp().create(self.bus_type, "", self.patch, 
                                                self.scope, self.dest_name)
                self.dest_obj_owned = True 
        else:
            self.dest_obj = obj 
            self.dest_obj_owned = False 
            
        if self.dest_obj:
            if (len(self.dest_obj.connections_in) < self.dest_inlet+1
                or [self, 0] not in self.dest_obj.connections_in[self.dest_inlet]):
                self.connect(0, self.dest_obj, self.dest_inlet, False)

        self.init_args = '"%s",%s' % (self.dest_name, self.dest_inlet) 
        self.gui_params["label_text"] = self._mkdispname()
        if self.gui_created:
            MFPApp().gui_command.configure(self.obj_id, self.gui_params)

        if self.inlets[0] is not Uninit:
            self.trigger()

        return True 

    def trigger(self):
        if self.inlets[1] is not Uninit: 
            port = 0
            if isinstance(self.inlets[1], (list,tuple)):
                (name, port) = self.inlets[1]
            else:
                name = self.inlets[1]

            self._connect(name, port)
            self.inlets[1] = Uninit 

        if self.inlets[0] is not Uninit and self.dest_obj:
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
        return "<b>Connected to:</b> %s/%s (%s)" % (
            self.dest_name, self.dest_inlet, 
            self.dest_obj.obj_id if self.dest_obj else "none") 

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
        self.last_value = Uninit
        Processor.__init__(self, 1, 1, init_type, init_args, patch, scope, name)

    def trigger(self):
        self.outlets[0] = self.last_value = self.inlets[0]
        self.inlets[0] = Uninit 
 
    def connect(self, outlet, target, inlet, show_gui=True):
        rv = Processor.connect(self, outlet, target, inlet, show_gui)
        if self.last_value is not Uninit:
            target.send(self.last_value, inlet)
        return rv

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
    display_type = "recvvia" 

    doc_tooltip_obj = "Receive messages to the specified name" 
    doc_tooltip_inlet = [ "Passthru input" ]
    doc_tooltip_outlet = [ "Passthru output" ]

    task_nibbler = TaskNibbler()

    def __init__(self, init_type, init_args, patch, scope, name):
        Processor.__init__(self, 2, 1, init_type, init_args, patch, scope, name)
        initargs, kwargs = self.parse_args(init_args)

        self.src_name = self.name 
        self.src_obj = None 
        self.src_outlet = 0

        if len(initargs) > 1:
            self.src_outlet = initargs[1]

        if len(initargs):
            self.src_name = initargs[0]
        else: 
            self.src_name = self.name

        self.gui_params["label_text"] = self._mkdispname()

        # needed so that name changes happen timely 
        self.hot_inlets = [0, 1]

        if len(initargs):
            self._connect(self.src_name, self.src_outlet)

    def _mkdispname(self):
        nm = self.src_name
        if self.src_outlet:
            nm += '/{}'.format(self.src_outlet)
        return nm

    def delete(self):
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
        self.gui_params['label_text'] = gp.get("label_text") or self._mkdispname()

    def _wait_connect(self):
        def recheck():
            ready = self._connect(self.src_name, self.src_outlet, False)
            return ready
        Recv.task_nibbler.add_task(recheck)

    def _connect(self, src_name, src_outlet, wait=True):
        src_obj = MFPApp().resolve(src_name, self, True)
        if src_obj:
            self.src_obj = src_obj
            self.src_obj.connect(self.src_outlet, self, 0, False)
            return True 
        else: 
            if wait:
                self._wait_connect()
            return False 

    def trigger(self):
        if self.inlets[1] is not Uninit:
            port = 0
            if isinstance(self.inlets[1], (tuple,list)):
                (name, port) = self.inlets[1]
            else:
                name = self.inlets[1]

            if name != self.src_name or port != self.src_outlet:
                if self.src_obj:
                    self.src_obj = None 
                self.init_args = '"%s",%s' % (name, port)
                self.src_name = name
                self.src_outlet = port
                self.gui_params["label_text"] = self._mkdispname()

                self._connect(self.src_name, self.src_outlet)
                if self.gui_created:
                    MFPApp().gui_command.configure(self.obj_id, self.gui_params)
            self.inlets[1] = Uninit

        if self.src_name and self.src_obj is None:
            self._connect(self.src_name, self.src_outlet)

        if self.inlets[0] is not Uninit:
            self.outlets[0] = self.inlets[0]
            self.inlets[0] = Uninit 

    def tooltip_extra(self):
        return "<b>Connected to:</b> %s/%s (%s)" % (
            self.src_name, self.src_outlet, 
            self.src_obj.obj_id if self.src_obj else "none") 

class RecvSignal (Recv): 
    display_type = "recvsignalvia" 
    doc_tooltip_obj = "Receive signals to the specified name"
    
    def __init__(self, init_type, init_args, patch, scope, name):
        Processor.__init__(self, 2, 1, init_type, init_args, patch, scope, name)
        initargs, kwargs = self.parse_args(init_args)

        self.src_name = None 
        self.src_obj = None 
        if len(initargs) > 1:
            self.src_outlet = initargs[1]
        else: 
            self.src_outlet = 0

        if len(initargs): 
            self.src_name = initargs[0]
        else: 
            self.src_name = self.name 

        self.gui_params["label_text"] = self._mkdispname()

        # needed so that name changes happen timely 
        self.hot_inlets = [0, 1]

        self.dsp_inlets = [0]
        self.dsp_outlets = [0]
        self.dsp_init("noop~")

        if len(initargs):
            self._connect(self.src_name, self.src_outlet)

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
