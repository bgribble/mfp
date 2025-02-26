#! /usr/bin/env python
'''
sendrcv.py: Bus/virtual wire objects.

Copyright (c) 2012-2015 Bill Gribble <grib@billgribble.com>
'''

import asyncio
import inspect
from ..processor import Processor
from ..mfp_app import MFPApp
from .. import Uninit

from mfp import log


class Send (Processor):
    display_type = "sendvia"
    doc_tooltip_obj = "Send messages to a named receiver (create with 'send via' GUI object)"
    doc_tooltip_inlet = ["Message to send", "Update receiver (default: initarg 0)"]

    bus_type = "bus"

    def __init__(self, init_type, init_args, patch, scope, name, defs=None):
        self.dest_name = None
        self.dest_inlet = 0
        self.dest_obj = None
        self.dest_obj_owned = False

        Processor.__init__(self, 2, 1, init_type, init_args, patch, scope, name, defs)

        # needed so that name changes happen timely
        self.hot_inlets = [0, 1]

        extra=defs or {}
        initargs, kwargs = self.parse_args(init_args, **extra)
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

    async def onload(self, phase):
        if phase == 0:
            await self._connect(self.dest_name, self.dest_inlet)

    async def method(self, message, inlet=0):
        if inlet == 0:
            await self.trigger()
        else:
            self.inlets[inlet] = Uninit
            rv = message.call(self)
            if inspect.isawaitable(rv):
                await rv

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

    async def connect(self, outlet, target, inlet, show_gui=True):
        await Processor.connect(self, outlet, target, inlet, show_gui)
        if outlet == 0:
            self.dest_obj = target
            self.dest_inlet = inlet

    async def _wait_connect(self):
        async def send_recheck():
            return await self._connect(self.dest_name, self.dest_inlet, False)
        conn = None
        while not conn:
            await asyncio.sleep(0.1)
            conn = await send_recheck()

    async def _connect(self, dest_name, dest_inlet, wait=True):
        # short-circuit if already conected
        if (
            self.dest_name == dest_name
            and self.dest_inlet == dest_inlet
            and self.dest_obj is not None
        ):
            return True

        # disconnect existing if needed
        if self.dest_obj is not None:
            await self.disconnect(0, self.dest_obj, self.dest_inlet)
            self.dest_obj = None
            self.dest_obj_owned = False
        self.dest_name = dest_name
        self.dest_inlet = dest_inlet

        # find the new endpoint
        obj = MFPApp().resolve(self.dest_name, self, True)

        if obj is None:
            # usually we create a bus if needed.  if it's a reference to
            # another top-level patch, create it there
            if ':' in self.dest_name:
                patch_name, rest = self.dest_name.split(':', 1)
                patch = MFPApp().patches.get(patch_name)

                if patch:
                    self.dest_obj = await MFPApp().create(
                        self.bus_type, "",
                        patch, patch.default_scope, rest
                    )
                    self.dest_obj_owned = True
                else:
                    if wait:
                        await self._wait_connect()
                    return False
            elif self.dest_inlet != 0:
                if wait:
                    await self._wait_connect()
                return False
            else:
                self.dest_obj = await MFPApp().create(
                    self.bus_type, "",
                    self.patch, self.scope, self.dest_name
                )
                self.dest_obj_owned = True
        else:
            self.dest_obj = obj
            self.dest_obj_owned = False

        if self.dest_obj:
            if (
                len(self.dest_obj.connections_in) < self.dest_inlet+1
                or [self, 0] not in self.dest_obj.connections_in[self.dest_inlet]
            ):
                await self.connect(0, self.dest_obj, self.dest_inlet, False)

        self.init_args = '"%s",%s' % (self.dest_name, self.dest_inlet)
        self.conf(label_text=self._mkdispname())

        if self.inlets[0] is not Uninit:
            await self.trigger()

        return True

    async def trigger(self):
        if self.inlets[1] is not Uninit:
            port = 0
            if isinstance(self.inlets[1], (list, tuple)):
                (name, port) = self.inlets[1]
            else:
                name = self.inlets[1]

            await self._connect(name, port)
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

    def __init__(self, init_type, init_args, patch, scope, name, defs=None):
        self.dest_name = None
        self.dest_inlet = 0
        self.dest_obj = None
        self.dest_obj_owned = False

        super().__init__(init_type, init_args, patch, scope, name, defs)

        self.dsp_inlets = [0]
        self.dsp_outlets = [0]

        # needed so that name changes happen timely
        self.hot_inlets = [0, 1]

        extra=defs or {}
        initargs, kwargs = self.parse_args(init_args, **extra)
        if len(initargs) > 1:
            self.dest_inlet = initargs[1]
        if len(initargs):
            self.dest_name = initargs[0]

        self.gui_params["label_text"] = self.dest_name

    async def setup(self):
        await self.dsp_init("noop~")


class MessageBus (Processor):
    display_type = "hidden"
    do_onload = False
    save_to_patch = False

    def __init__(self, init_type, init_args, patch, scope, name, defs=None):
        self.last_value = Uninit
        Processor.__init__(self, 1, 1, init_type, init_args, patch, scope, name, defs)

    async def trigger(self):
        self.outlets[0] = self.last_value = self.inlets[0]
        self.inlets[0] = Uninit

    async def connect(self, outlet, target, inlet, show_gui=True):
        rv = await Processor.connect(self, outlet, target, inlet, show_gui)
        if self.last_value is not Uninit:
            await target.send(self.last_value, inlet)
        return rv

    async def method(self, message, inlet=0):
        if inlet == 0:
            await self.trigger()
        else:
            self.inlets[inlet] = Uninit
            rv = message.call(self)
            if inspect.isawaitable(rv):
                await rv


class SignalBus (Processor):
    display_type = "hidden"
    do_onload = False
    save_to_patch = False

    def __init__(self, init_type, init_args, patch, scope, name, defs=None):
        Processor.__init__(self, 1, 1, init_type, init_args, patch, scope, name, defs)
        self.dsp_inlets = [0]
        self.dsp_outlets = [0]

    async def setup(self):
        await self.dsp_init("noop~")

    async def trigger(self):
        self.outlets[0] = self.inlets[0]


class Recv (Processor):
    display_type = "recvvia"

    doc_tooltip_obj = "Receive messages to the specified name"
    doc_tooltip_inlet = ["Passthru input"]
    doc_tooltip_outlet = ["Passthru output"]

    def __init__(self, init_type, init_args, patch, scope, name, defs=None):
        Processor.__init__(self, 2, 1, init_type, init_args, patch, scope, name, defs)
        extra=defs or {}
        initargs, kwargs = self.parse_args(init_args, **extra)

        self.src_name = self.name
        self.src_name_provided = False
        self.src_obj = None
        self.src_outlet = 0

        if len(initargs) > 1:
            self.src_outlet = initargs[1]

        if len(initargs):
            self.src_name_provided = True
            self.src_name = initargs[0]
        else:
            self.src_name = self.name

        self.gui_params["label_text"] = self._mkdispname()

        # needed so that name changes happen timely
        self.hot_inlets = [0, 1]

    async def onload(self, phase):
        if phase == 1 and self.src_name_provided:
            await self._connect(self.src_name, self.src_outlet)

    def _mkdispname(self):
        nm = self.src_name
        if self.src_outlet:
            nm += '/{}'.format(self.src_outlet)
        return nm

    async def method(self, message, inlet):
        if inlet == 0:
            await self.trigger()
        else:
            self.inlets[inlet] = Uninit
            rv = message.call(self)
            if inspect.isawaitable(rv):
                await rv

    def load(self, params):
        Processor.load(self, params)
        gp = params.get('gui_params', {})
        self.gui_params['label_text'] = gp.get("label_text") or self._mkdispname()

    async def _wait_connect(self):
        async def recv_recheck():
            return await self._connect(self.src_name, self.src_outlet, False)

        conn = None
        while conn is None:
            await asyncio.sleep(0.1)
            conn = await recv_recheck()

    async def _connect(self, src_name, src_outlet, wait=True):
        src_obj = MFPApp().resolve(src_name, self, True)
        if src_obj:
            self.src_obj = src_obj
            await self.src_obj.connect(self.src_outlet, self, 0, False)
            return True
        elif wait:
            await self._wait_connect()

        return False

    async def trigger(self):
        if self.inlets[1] is not Uninit:
            port = 0
            if isinstance(self.inlets[1], (tuple, list)):
                (name, port) = self.inlets[1]
            else:
                name = self.inlets[1]

            if name != self.src_name or port != self.src_outlet:
                if self.src_obj:
                    self.src_obj = None
                self.init_args = '"%s",%s' % (name, port)
                self.src_name = name
                self.src_outlet = port
                self.conf(label_text=self._mkdispname())
                await self._connect(self.src_name, self.src_outlet)
            self.inlets[1] = Uninit

        if self.src_name and self.src_obj is None:
            await self._connect(self.src_name, self.src_outlet)

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

    def __init__(self, init_type, init_args, patch, scope, name, defs=None):
        super().__init__(init_type, init_args, patch, scope, name, defs)
        extra=defs or {}
        initargs, kwargs = self.parse_args(init_args, **extra)

        self.src_name = None
        self.src_obj = None
        if len(initargs) > 1:
            self.src_outlet = initargs[1]
            self.init_connect = True
        else:
            self.src_outlet = 0
            self.init_connect = False

        if len(initargs):
            self.src_name = initargs[0]
        else:
            self.src_name = self.name

        self.gui_params["label_text"] = self._mkdispname()

        # needed so that name changes happen timely
        self.hot_inlets = [0, 1]

        self.dsp_inlets = [0]
        self.dsp_outlets = [0]

    async def setup(self):
        await self.dsp_init("noop~")
        if self.init_connect:
            await self._connect(self.src_name, self.src_outlet)

    async def _connect(self, src_name, src_outlet, wait=True):
        src_obj = MFPApp().resolve(src_name, self, True)
        if src_obj and src_obj.dsp_obj and self.dsp_obj:
            self.src_obj = src_obj
            await self.src_obj.connect(self.src_outlet, self, 0, False)
            return True
        elif wait:
            await self._wait_connect()

        return False


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
