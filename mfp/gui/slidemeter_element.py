#! /usr/bin/env python
'''
slidemeter_element.py
A patch element corresponding to a vertical or horizontal slider/meter

Copyright (c) 2012 Bill Gribble <grib@billgribble.com>
'''

import math
from abc import ABC, abstractmethod
from mfp.gui_main import MFPGUI
from .backend_interfaces import BackendInterface
from .base_element import BaseElement
from .modes.slider import SliderEditMode, SliderControlMode, DialEditMode, DialControlMode
from . import ticks


class SlideMeterElement (BaseElement):
    '''
    Vertical/horizontal slider/meter element
    Contains an optional scale
    Can be output-only or interactive
    Scale can be dB or linear
    '''
    extra_params = [
        'min_value', 'max_value', 'show_scale', 'scale',
        'scale_font_size', 'scale_position', 'orientation',
        'zeropoint'
    ]
    store_attrs = BaseElement.store_attrs + extra_params
    display_type = "slidemeter"
    proc_type = "slidemeter"

    style_defaults = {
        'font-size-scale': 8,
        'meter-color': 'default-alt-fill-color'
    }

    SCALE_SPACE = 30
    TICK_SPACE = 14
    TICK_LEN = 5
    MIN_BARSIZE = 2.0

    VERTICAL = 0x00
    HORIZONTAL = 0x01
    LEFT = 0x00
    RIGHT = 0x01

    def __init__(self, window, x, y):
        super().__init__(window, x, y)
        self.param_list.extend([*self.extra_params])

        # parameters controlling display
        self.value = 0.0
        self.min_value = 0.0
        self.max_value = 1.0
        self.scale_ticks = None
        self.show_scale = False
        self.slider_enable = True
        self.scale = ticks.LinearScale()
        self.scale_position = self.LEFT
        self.scale_font_size = 7
        self.orientation = self.VERTICAL
        self.zeropoint = None

        # value to emit when at bottom of scale, useful for dB scales
        self.slider_zero = None

        # coordinates of "hot" (meter display) area, where
        # dragging works
        self.hot_x_min = None
        self.hot_x_max = None
        self.hot_y_min = None
        self.hot_y_max = None

        # request update when value changes
        self.update_required = True

    @property
    def scale_type(self):
        return self.scale.scale_type if self.scale else 0

    def fill_interval(self):
        if self.zeropoint is None:
            return (self.min_value, self.value)

        if self.value > self.zeropoint:
            pmin = self.zeropoint
            pmax = self.value
        else:
            pmin = self.value
            pmax = self.zeropoint
        return (pmin, pmax)

    def update_value(self, value):
        if value >= self.max_value:
            value = self.max_value

        if value <= self.min_value:
            value = self.min_value

        if value != self.value:
            self.value = value
            self.redraw()
            MFPGUI().async_task(MFPGUI().mfp.send(self.obj_id, 0, self.value))

    async def set_orientation(self, orient):
        if orient != self.orientation:
            await self.set_size(self.height, self.width)
        await self.dispatch(self.action(self.SET_ORIENTATION, value=orient))

    async def set_show_scale(self, show_scale):
        if show_scale == self.show_scale:
            return

        if show_scale:
            self.show_scale = True
            if self.orientation & self.HORIZONTAL:
                await self.set_size(self.get_width(), self.get_height() + self.SCALE_SPACE)
            else:
                await self.set_size(self.get_width() + self.SCALE_SPACE, self.get_height())
        else:
            self.show_scale = False
            if self.orientation & self.HORIZONTAL:
                await self.set_size(self.get_width(), self.get_height() - self.SCALE_SPACE)
            else:
                await self.set_size(self.get_width() - self.SCALE_SPACE, self.get_height())

    async def set_bounds(self, min_val, max_val):
        self.max_value = max_val
        self.min_value = min_val
        self.scale.set_bounds(self.min_value, self.max_value)

        newval = False
        if self.value > self.max_value:
            self.value = self.max_value
            newval = True

        if self.value < self.min_value:
            self.value = self.min_value
            newval = True

        if newval:
            MFPGUI().async_task(MFPGUI().mfp.send(self.obj_id, 0, self.value))

        self.scale_ticks = None
        await self.update()
        self.send_params()

    async def set_zeropoint(self, zp):
        self.zeropoint = zp
        await self.update()
        self.send_params()

    async def configure(self, params):
        changes = False

        v = params.get("orientation")
        if (
            v is not None and v in (1, "h", "horiz", "horizontal")
            and not (self.orientation & self.HORIZONTAL)
        ):
            self.set_orientation(self.HORIZONTAL)
            changes = True
        elif (
            v is not None and v in (0, "v", "vert", "vertical")
            and (self.orientation & self.HORIZONTAL)
        ):
            self.set_orientation(self.VERTICAL)
            changes = True

        v = params.get("zeropoint")
        if v != self.zeropoint:
            self.zeropoint = v
            changes = True

        v = params.get("scale")
        if v == "linear" and not isinstance(self.scale, ticks.LinearScale):
            self.scale = ticks.LinearScale(self.min_value, self.max_value)
            changes = True
        elif v in ("log", "log10", "decade") and not isinstance(self.scale, ticks.LogScale):
            self.scale = ticks.LogScale(self.min_value, self.max_value)
            changes = True
        elif v == 'audio' and not isinstance(self.scale, ticks.AudioScale):
            self.scale = ticks.AudioScale(self.min_value, self.max_value)
            changes = True

        v = params.get("scale_position")
        if (v is not None and v in (1, "r", "R", "right") and self.scale_position != self.RIGHT):
            self.scale_position = self.RIGHT
            changes = True
        elif (v is not None and v in (0, "l", "L", "left") and self.scale_position != self.LEFT):
            self.scale_position = self.LEFT
            changes = True

        for p in ("show_scale", "slider_enable", "scale_ticks"):
            v = params.get(p)
            if v is not None and hasattr(self, p):
                changes = True
                setattr(self, p, v)

        rescale = False
        if 'min_value' in params:
            v = params['min_value']
            if v != self.min_value:
                changes = True
                rescale = True
                self.min_value = v

        if 'max_value' in params:
            v = params['max_value']
            if v != self.max_value:
                changes = True
                rescale = True
                self.max_value = v

        if rescale:
            self.scale.set_bounds(self.min_value, self.max_value)
            self.scale_ticks = None
            await self.update()

        v = params.get("value")
        if v is not None:
            if v < self.min_value:
                v = self.min_value
            if v > self.max_value:
                v = self.max_value
            if self.value != v:
                changes = True
                self.value = v

        dr = params.get("dial_radius")
        if dr is not None:
            self.dial_radius = dr

        await super().configure(params)
        if changes:
            self.redraw()

    def select(self):
        super().select()
        self.redraw()

    def unselect(self):
        super().unselect()
        self.redraw()

    async def make_edit_mode(self):
        if self.obj_id is None:
            # create the underlying var
            await self.create(self.proc_type, str(self.value))
            if self.obj_id is None:
                return None
            else:
                self.draw_ports()
        return SliderEditMode(self.app_window, self, "Fader/meter edit")

    def make_control_mode(self):
        return SliderControlMode(self.app_window, self, "Fader/meter control")


class FaderElementImpl(ABC, BackendInterface):
    pass


class FaderElement(SlideMeterElement):
    DEFAULT_W = 20
    DEFAULT_H = 100

    @classmethod
    def get_factory(cls):
        return FaderElementImpl.get_backend(MFPGUI().appwin.backend_name)


class BarMeterElementImpl(ABC, BackendInterface):
    pass


class BarMeterElement(SlideMeterElement):
    def __init__(self, window, x, y):
        super().__init__(window, x, y)

        self.slider_enable = False

    @classmethod
    def get_factory(cls):
        return BarMeterElementImpl.get_backend(MFPGUI().appwin.backend_name)


class DialElementImpl(ABC, BackendInterface):
    pass

class DialElement(SlideMeterElement):
    display_type = "dial"
    proc_type = "slidemeter"

    DEFAULT_W = 50
    DEFAULT_H = 50
    DEFAULT_R = 24

    BAR_WIDTH = 0.7
    THETA_MIN = 0.65*math.pi
    THETA_MAX = 0.35*math.pi
    DRAG_SCALE = 0.01
    MIN_WEDGE = 0.1

    def __init__(self, window, x, y):
        super().__init__(window, x, y)
        self.dial_radius = self.DEFAULT_R
        self.param_list.append('dial_radius')

    @classmethod
    def get_factory(cls):
        return DialElementImpl.get_backend(MFPGUI().appwin.backend_name)

    def set_orientation(self, orient):
        pass

    async def set_show_scale(self, show_scale):
        if show_scale == self.show_scale:
            return

        if show_scale:
            self.show_scale = True
            await self.set_size(
                2*self.dial_radius + 2.0 + 7*self.scale_font_size,
                2*self.dial_radius + 2.0 + 3*self.scale_font_size
            )
        else:
            self.show_scale = False
            await self.set_size(
                2*self.dial_radius + 2.0,
                2*self.dial_radius + 2.0
            )

    async def make_edit_mode(self):
        if self.obj_id is None:
            # create the underlying var
            await self.create(self.proc_type, str(self.value))
            if self.obj_id is None:
                return None
            self.draw_ports()
        return DialEditMode(self.app_window, self, "Dial edit")

    def make_control_mode(self):
        return DialControlMode(self.app_window, self, "Dial control")
