#! /usr/bin/env python
'''
slidemeter_element.py
A patch element corresponding to a vertical or horizontal slider/meter

Copyright (c) Bill Gribble <grib@billgribble.com>
'''

import math
from abc import ABCMeta
from flopsy import Action, mutates, saga

from mfp import log
from mfp.gui_main import MFPGUI
from mfp.gui.colordb import ColorDB
from .backend_interfaces import BackendInterface
from .base_element import BaseElement, ParamInfo
from .modes.slider import SliderEditMode, SliderControlMode, DialEditMode, DialControlMode
from . import ticks


class SlideMeterElement (BaseElement):
    '''
    Vertical/horizontal slider/meter element
    Contains an optional scale
    Can be output-only or interactive
    Scale can be dB or linear
    '''
    extra_params = {
        'min_value': ParamInfo(label="Min value", param_type=float, show=True),
        'max_value': ParamInfo(label="Max value", param_type=float, show=True),
        'bar_width': ParamInfo(label="Meter width", param_type=float, show=True),
        'bar_height': ParamInfo(label="Meter height", param_type=float, show=True),
        'show_scale': ParamInfo(label="Show scale", param_type=bool, show=True),
        'scale_type': ParamInfo(
            label="Scale type", 
            param_type=str, 
            choices=lambda _: [
                ("Linear", "linear"),
                ("Log", "log"),
                ("Audio", "audio")
            ],
            show=True
        ),
        'scale_position': ParamInfo(
            label="Scale position",
            choices=lambda _: [("Left/top", "left"), ("Right/bottom", "right")],
            param_type=str,
            show=True
        ),
        'orientation': ParamInfo(
            label="Orientation", 
            choices=lambda _: [("Vertical", "vertical"), ("Horizontal", "horizontal")],
            param_type=str, 
            show=True
        ),
        'zeropoint': ParamInfo(label="Zero point", param_type=float, show=True),
    }

    store_attrs = {
        **BaseElement.store_attrs, **extra_params
    }
    display_type = "slidemeter"
    proc_type = "slidemeter"
    help_patch = "slider.help.mfp"

    style_defaults = {
        'scale-font-size': 8,
        'padding': dict(top=0, bottom=0, left=0, right=0)
    }

    SCALE_SPACE = 30
    TICK_SPACE = 14
    TICK_LEN = 5
    MIN_BARSIZE = 2.0

    VERTICAL = "vertical"
    HORIZONTAL = "horizontal"
    LEFT = "left"
    RIGHT = "right"

    def __init__(self, window, x, y):
        super().__init__(window, x, y)
        self.param_list.extend([*self.extra_params])

        type(self).style_defaults['meter-color'] = ColorDB().find('default-alt-fill-color')

        # parameters controlling display
        self.value = 0.0
        self.min_value = 0.0
        self.max_value = 1.0
        self.bar_width = 24
        self.bar_height = 100
        self.scale_ticks = None
        self.show_scale = False
        self.slider_enable = True
        self.scale = ticks.LinearScale()
        self.scale_type = "linear"
        self.scale_position = self.LEFT
        self.scale_font_size = 7
        self.orientation = SlideMeterElement.VERTICAL
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

    def get_width(self):
        return self.width

    def get_height(self):
        return self.height

    def scale_format(self, value):
        marks = {
            1: "k", 2: "M", 3: "G", -1: "m", -2: "u", -3: "n"
        }

        if not value:
            return f"{value:>3.3g}"

        expo = math.floor(math.log10(abs(value)))
        bucket = int(expo / 3)
        mark = marks.get(bucket)
        if mark:
            mant = value / 10**(3*bucket)
            fval = f"{mant:3.3g}{mark}"
        else:
            fval = f"{value:>3.3g}"
        return fval

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

    def add_pixdelta(self, dx, dy):
        if self.orientation == SlideMeterElement.VERTICAL:
            delta = dy / float(self.hot_y_max - self.hot_y_min)
        else:
            delta = dx / float(self.hot_x_max - self.hot_x_min)

        scalepos = self.scale.fraction(self.value) + delta
        return self.scale.value(scalepos)

    def update_value(self, value):
        if value >= self.max_value:
            value = self.max_value

        if value <= self.min_value:
            value = self.min_value

        if value != self.value:
            self.value = value
            # FIXME
            MFPGUI().async_task(self.update())
            MFPGUI().async_task(MFPGUI().mfp.send(self.obj_id, 0, self.value))

    @saga("scale_type")
    async def scale_type_changed(self, action, state_diff, previous):
        if self.scale_type == "linear" and not isinstance(self.scale, ticks.LinearScale):
            self.scale = ticks.LinearScale()
        elif self.scale_type == "log" and not isinstance(self.scale, ticks.DecadeScale):
            self.scale = ticks.DecadeScale()
        elif self.scale_type == "audio" and not isinstance(self.scale, ticks.AudioScale):
            self.scale = ticks.AudioScale()
        self.scale_ticks = None
        self.scale.set_bounds(self.min_value, self.max_value)
        yield None

    @saga("orientation", "show_scale")
    async def shape_changed(self, action, state_diff, previous):
        height = self.height
        width = self.width
        if "orientation" in state_diff:
            old, new = state_diff.get("orientation")
            if new != old:
                yield Action(self, self.SET_WIDTH, dict(value=height))
                yield Action(self, self.SET_HEIGHT, dict(value=width))

        if "show_scale" in state_diff:
            if self.show_scale:
                if self.orientation == SlideMeterElement.HORIZONTAL:
                    height = self.height + self.SCALE_SPACE
                else:
                    width = self.width + self.SCALE_SPACE
            else:
                if self.orientation == SlideMeterElement.HORIZONTAL:
                    height = self.height - self.SCALE_SPACE
                else:
                    width = self.width - self.SCALE_SPACE

            if width != self.width:
                yield Action(self, self.SET_WIDTH, dict(value=width))
            if height != self.height:
                yield Action(self, self.SET_HEIGHT, dict(value=height))

    @saga("min_value", "max_value")
    async def bounds_changed(self, action, state_diff, previous):
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

        # FIXME -- needed?
        await self.update()
        self.send_params()

    @saga('zeropoint', 'bar_width', 'bar_height', 'scale_type', 'orientation', 'show_scale')
    async def params_changed(self, action, state_diff, previous):
        await self.update()
        self.send_params()

    async def configure(self, params):
        changes = False

        v = params.get("orientation")
        if (
            v is not None and v in (1, "h", "horiz", "horizontal")
            and not (self.orientation == SlideMeterElement.HORIZONTAL)
        ):
            self.orientation = SlideMeterElement.HORIZONTAL
            changes = True
        elif (
            v is not None and v in (0, "v", "vert", "vertical")
            and (self.orientation == SlideMeterElement.HORIZONTAL)
        ):
            self.orientation = SlideMeterElement.VERTICAL
            changes = True

        v = params.get("zeropoint")
        if v != self.zeropoint:
            self.zeropoint = v
            changes = True

        v = params.get("scale")
        if v == "linear" and not isinstance(self.scale, ticks.LinearScale):
            self.scale_type = v
            self.scale = ticks.LinearScale(self.min_value, self.max_value)
            self.scale_ticks = None
            changes = True
        elif v in ("log", "log10", "decade") and not isinstance(self.scale, ticks.LogScale):
            self.scale_type = v
            self.scale = ticks.LogScale(self.min_value, self.max_value)
            self.scale_ticks = None
            changes = True
        elif v == 'audio' and not isinstance(self.scale, ticks.AudioScale):
            self.scale_type = v
            self.scale = ticks.AudioScale(self.min_value, self.max_value)
            self.scale_ticks = None
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
            await self.update()

    def select(self):
        super().select()

    def unselect(self):
        super().unselect()

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


class FaderElementImpl(BackendInterface, metaclass=ABCMeta):
    pass


class FaderElement(SlideMeterElement):
    DEFAULT_W = 20
    DEFAULT_H = 100

    @classmethod
    def get_backend(cls, backend_name):
        return FaderElementImpl.get_backend(backend_name)


class BarMeterElementImpl(BackendInterface, metaclass=ABCMeta):
    pass


class BarMeterElement(SlideMeterElement):
    DEFAULT_W = 20
    DEFAULT_H = 100

    def __init__(self, window, x, y):
        super().__init__(window, x, y)

        self.slider_enable = False

    @classmethod
    def get_backend(cls, backend_name):
        return BarMeterElementImpl.get_backend(backend_name)


class DialElementImpl(BackendInterface, metaclass=ABCMeta):
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
    def get_backend(cls, backend_name):
        return DialElementImpl.get_backend(backend_name)

    def p2r(self, r, theta):
        x = (self.width / 2.0) + r * math.cos(theta)
        y = (self.height / 2.0) + r * math.sin(theta)
        return (x, y)

    def r2p(self, x, y):
        dx = x - self.width/2.0
        dy = y - self.height/2.0
        theta = math.atan2(dy, dx)
        r = (x*x + y*y)**0.5
        return (r, theta)

    def add_pixdelta(self, dx, dy):
        delta = 0.01 * dy

        scalepos = self.scale.fraction(self.value) + delta
        return self.scale.value(scalepos)

    def val2theta(self, value):
        scale_fraction = self.scale.fraction(value)
        if scale_fraction > 1.0:
            scale_fraction = 1.0
        elif scale_fraction < 0:
            scale_fraction = 0
        theta = self.THETA_MIN + scale_fraction * (2*math.pi-(self.THETA_MIN-self.THETA_MAX))
        return theta

    @mutates('show_scale')
    async def set_show_scale(self, show_scale):
        if show_scale == self.show_scale:
            return

        if show_scale:
            self.show_scale = True
            await self.set_size(
                2*self.dial_radius + 2.0 + 6*self.scale_font_size,
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
