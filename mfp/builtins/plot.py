#! /usr/bin/env python
'''
plot.py: Stub for graphical plot I/O

Copyright (c) Bill Gribble <grib@billgribble.com>
'''

import inspect
from datetime import datetime
from ..processor import Processor
from ..mfp_app import MFPApp
from .. import Bang, Uninit
from ..method import MethodCall

from .buffer import BufferInfo
from mfp import log


class Scope (Processor):
    doc_tooltip_obj = "Scope-style signal display (requires a buffer~)"
    doc_tooltip_inlet = [ "Config/buffer info input" ]
    doc_tooltip_outlet = [ "Buffer control output" ]

    display_type = "plot"

    def __init__(self, init_type, init_args, patch, scope, name, defs=None):
        self.buffer = None
        self.retrig_value = True
        self.need_buffer_send = False

        if init_args is not None:
            log.debug("scope: Does not accept init args")

        self.gui_params = dict(plot_type="scope")
        Processor.__init__(self, 1, 1, init_type, init_args, patch, scope, name, defs)

    async def trigger(self):
        if isinstance(self.inlets[0], BufferInfo):
            self.buffer = self.inlets[0]
            if self.gui_created:
                await MFPApp().gui_command.command(self.obj_id, "buffer", self.buffer)
                self.need_buffer_send = False
            else:
                self.need_buffer_send = True
        elif self.inlets[0] == 1:
            pass
        elif self.inlets[0] == 0:
            if self.gui_created:
                await self.grab()

        if self.buffer is None:
            self.outlets[0] = MethodCall("bufinfo")

        if self.gui_created and self.buffer and self.need_buffer_send:
            self.need_buffer_send = False
            MFPApp().gui_command.command(self.obj_id, "buffer", self.buffer)

    def range(self, minval, maxval):
        self.gui_params['y_min'] = minval
        self.gui_params['y_max'] = maxval

    def set_retrig(self, value):
        self.retrig_value = value

    def draw_complete(self):
        self.outlets[0] = self.retrig_value

    async def grab(self):
        await MFPApp().gui_command.command(self.obj_id, "grab", None)


class Scatter (Processor):
    doc_tooltip_obj = "Scatter plot for non-signal data points"
    doc_tooltip_inlet = []
    doc_tooltip_outlet = ["Data recorder output"]

    display_type = "plot"

    def __init__(self, init_type, init_args, patch, scope, name, defs=None):
        self.points = {}
        self.time_base = None

        extra=defs or {}
        initargs, kwargs = patch.parse_args(init_args, **extra)
        if len(initargs) > 0:
            channels = initargs[0]
        else:
            channels = 1
        self.hot_inlets = list(range(channels))
        self.gui_params = dict(plot_type=init_type, channels=channels)

        self.doc_tooltip_inlet = []
        for i in range(channels):
            self.doc_tooltip_inlet.append("Curve %d data/config input" % i)

        Processor.__init__(self, channels, 1, init_type, init_args, patch, scope, name, defs)

    async def method(self, message, inlet):
        # magic inlet argument makes messages simpler
        if inlet != 0:
            message.kwargs['inlet'] = inlet
        rv = message.call(self)
        if inspect.isawaitable(rv):
            await rv

    def _time(self):
        if self.time_base is None:
            return 0
        return (datetime.now() - self.time_base).total_seconds()

    def _chartconf(self, action, data=None):
        if self.gui_created:
            MFPApp().async_task(MFPApp().gui_command.command(self.obj_id, action, data))
        return True

    async def trigger(self):
        points = {}

        def _normalize_and_add(val):
            v = None
            if isinstance(val, tuple):
                v = val
            elif isinstance(val, complex):
                v = (val.real, val.imag)
            elif isinstance(val, (float, int)):
                v = (self._time(), val)
            if v is not None:
                cpts = self.points.setdefault(i, [])
                cpts.append(v)
                cpts = points.setdefault(i, [])
                cpts.append(v)
            return v

        for i, val in zip(range(len(self.inlets)), self.inlets):
            if val == Bang:
                self.outlets[0] = self.points[i]

            elif isinstance(val, list):
                for elt in val:
                    _normalize_and_add(elt)
            else:
                _normalize_and_add(val)

            self.inlets[i] = Uninit

        if points != {}:
            self._chartconf('add', points)

    # methods that the object responds to
    def roll(self, *args, **kwargs):
        '''Start the plot roll function.'''
        if self.time_base is None:
            self.time_base = datetime.now()
        return self._chartconf('roll', self._time())

    def stop(self, *args, **kwargs):
        '''Stop the plot roll'''
        return self._chartconf('stop', self._time())

    def reset(self, *args, **kwargs):
        '''Reset time base for items with no X'''
        self.time_base = datetime.now()
        return self._chartconf('reset', self._time())

    def clearall(self, *args, **kwargs):
        '''Clear all data points'''
        self.points = {}
        return self._chartconf('clear')

    def clear(self, inlet=0):
        '''Clear a single curve's points'''
        if inlet is not None and inlet in self.points:
            del self.points[inlet]
        return self._chartconf('clear', inlet)

    def style(self, **kwargs):
        '''Set style parameters for a curve'''
        inlet = str(kwargs.get('inlet', 0))
        style = self.gui_params.get('style', {})
        instyle = style.setdefault(inlet, {})
        for k, v in kwargs.items():
            if k != 'inlet':
                instyle[k] = v
        self.conf(style=style)
        return True

    def bounds(self, x_min, y_min, x_max, y_max):
        '''Set viewport boundaries in plot coordinates'''
        return self._chartconf('bounds', (x_min, y_min, x_max, y_max))


class Table (Processor):
    doc_tooltip_obj = "Tabular values"
    doc_tooltip_inlet = ["Point to get/set or command"]
    doc_tooltip_outlet = ["Point or slice output"]

    display_type = "plot"

    def __init__(self, init_type, init_args, patch, scope, name, defs=None):
        extra=defs or {}
        initargs, kwargs = patch.parse_args(init_args, **extra)
        if len(initargs) > 0:
            self.num_points = initargs[0]
        else:
            self.num_points = 0
        self.points = [0 for p in range(self.num_points)]
        if self.num_points <= 20:
            plot_type = "bars"
            edit_draw = False
        else:
            plot_type = "scatter"
            edit_draw = True

        self.gui_params = dict(
            plot_type=plot_type,
            plot_editable=True,
            plot_edit_draw=edit_draw,
            channels=1,
            x_min=0,
            x_max=self.num_points
        )

        Processor.__init__(self, 1, 1, init_type, init_args, patch, scope, name, defs)

    async def method(self, message, inlet):
        # magic inlet argument makes messages simpler
        if inlet != 0:
            message.kwargs['inlet'] = inlet
        rv = message.call(self)
        if inspect.isawaitable(rv):
            await rv

    def _chartconf(self, action, data=None):
        if self.gui_created:
            MFPApp().async_task(MFPApp().gui_command.command(self.obj_id, action, data))
        return True

    async def trigger(self):
        point = None
        val = self.inlets[0]
        if val == Bang:
            self.outlets[0] = self.points
        elif isinstance(val, int):
            self.outlets[0] = self.points[val]
        elif isinstance(val, (list, tuple)):
            point = [v for v in val]
            if point[0] >= len(self.points):
                point[0] = len(self.points) - 1
            self.points[point[0]] = point[1]
        elif isinstance(val, slice):
            self.outlets[0] = self.points[val]
        self.inlets[0] = Uninit

        if point is not None:
            self._chartconf('replace', point)

    def save_state(self):
        return dict(
            num_points=self.num_points,
            points=[p for p in self.points]
        )

    def restore_state(self, state):
        if "num_points" in state:
            new_size = state['num_points']
            if new_size > self.num_points:
                self.points.extend([0] * (new_size - self.num_points))
            elif new_size < self.num_points:
                self.points[new_size-self.num_points:] = []
            self.num_points = new_size

        if "points" in state:
            self.points = state['points']
            self._chartconf(
                "set",
                {0: list(enumerate(state['points']))},
            )

    # methods that the object responds to
    def clear(self, inlet=0):
        '''Clear a single curve's points'''
        if inlet is not None and inlet in self.points:
            del self.points[inlet]
        return self._chartconf('clear', inlet)

    def style(self, **kwargs):
        '''Set style parameters for a curve'''
        inlet = str(kwargs.get('inlet', 0))
        style = self.gui_params.get('style', {})
        instyle = style.setdefault(inlet, {})
        for k, v in kwargs.items():
            if k != 'inlet':
                instyle[k] = v
        self.conf(style=style)
        return True

    def bounds(self, x_min, y_min, x_max, y_max):
        '''Set viewport boundaries in plot coordinates'''
        return self._chartconf('bounds', (x_min, y_min, x_max, y_max))


def register():
    MFPApp().register("scatter", Scatter)
    MFPApp().register("bars", Scatter)
    MFPApp().register("histogram", Scatter)
    MFPApp().register("scope", Scope)
    MFPApp().register("table", Table)
