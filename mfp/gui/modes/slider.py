#! /usr/bin/env python
'''
slider.py: SliderEdit and SliderControl minor modes

Copyright (c) 2012 Bill Gribble <grib@billgribble.com>
'''

from ..input_mode import InputMode


class SliderControlMode (InputMode):
    def __init__(self, window, element, descrip):
        self.manager = window.input_mgr
        self.window = window
        self.slider = element

        self.drag_started = False
        self.drag_start_x = self.manager.pointer_x
        self.drag_start_y = self.manager.pointer_y
        self.drag_last_x = self.manager.pointer_x
        self.drag_last_y = self.manager.pointer_y

        InputMode.__init__(self, descrip)

    @classmethod
    def init_bindings(cls):
        cls.cl_bind(
            "slider-set-value", cls.set_value, "Set fader value", keysym="M1DOUBLEDOWN",
        )
        cls.cl_bind(
            "slider-drag-start", cls.drag_start, "Adjust fader or move element", keysym="M1DOWN",
        )
        cls.cl_bind(
            "slider-drag-start", cls.drag_start, keysym="S-M1DOWN",
        )
        cls.cl_bind(
            "slider-drag-start", cls.drag_start, keysym="C-M1DOWN",
        )
        cls.cl_bind(
            "slider-drag-motion", lambda mode: mode.drag_selected(1.0),
            "Change value (1x speed)", keysym="M1-MOTION"
        )
        cls.cl_bind(
            "slider-drag-motion", lambda mode: mode.drag_selected(0.25),
            "Change value (1/4 speed)", keysym="S-M1-MOTION"
        )
        cls.cl_bind(
            "slider-drag-motion", lambda mode: mode.drag_selected(0.05),
            "Change value (1/20 speed)", keysym="C-M1-MOTION"
        )
        cls.cl_bind(
            "slider-drag-end", cls.drag_end, "Release fader", keysym="M1UP",
        )
        cls.cl_bind(
            "slider-drag-end", cls.drag_end, keysym="S-M1UP",
        )
        cls.cl_bind(
            "slider-drag-end", cls.drag_end, keysym="C-M1UP",
        )
        cls.cl_bind(
            "slider-value-up", lambda mode: mode.change_value(0.01), keysym="UP",
        )
        cls.cl_bind(
            "slider-value-down", lambda mode: mode.change_value(-0.01), keysym="DOWN",
        )
        cls.cl_bind(
            "slider-value-up", lambda mode: mode.change_value(0.001), keysym="S-UP",
        )
        cls.cl_bind(
            "slider-value-down", lambda mode: mode.change_value(-0.001), keysym="S-DOWN",
        )

    def set_value(self):
        new_value = self.slider.pixpos2value(self.manager.pointer_x, self.manager.pointer_y)
        self.slider.update_value(new_value)

    def change_value(self, fraction):
        dv = fraction * abs(self.slider.max_value - self.slider.min_value)

        self.slider.update_value(self.slider.value + dv)
        return True

    async def drag_start(self):
        if self.manager.pointer_obj == self.slider:
            if self.slider not in self.window.selected:
                await self.window.select(self.slider)

            if (
                self.slider.slider_enable
                and self.slider.point_in_slider(
                    self.manager.pointer_x,
                    self.manager.pointer_y
                )
            ):
                self.drag_started = True
                self.drag_start_x = self.manager.pointer_x
                self.drag_start_y = self.manager.pointer_y
                self.drag_last_x = self.manager.pointer_x
                self.drag_last_y = self.manager.pointer_y
                return True
        return False

    def drag_selected(self, delta=1.0):
        if self.drag_started is False:
            return False

        dx = self.manager.pointer_x - self.drag_last_x
        dy = self.manager.pointer_y - self.drag_last_y

        new_value = self.slider.add_pixdelta(delta * dx, -1.0 * delta * dy)

        self.drag_last_x = self.manager.pointer_x
        self.drag_last_y = self.manager.pointer_y

        self.slider.update_value(new_value)
        return True

    def drag_end(self):
        if self.drag_started:
            self.drag_started = False
            return True
        else:
            return False


class SliderEditMode (InputMode):
    def __init__(self, window, element, descrip):
        self.manager = window.input_mgr
        self.window = window
        self.slider = element

        InputMode.__init__(self, descrip)

    @classmethod
    def init_bindings(cls):
        cls.cl_bind(
            "slider-toggle-scale", cls.toggle_scale, "Toggle scale display (on/off)", keysym="s",
            menupath="Context > Params > []Toggle scale display"
        )
        cls.cl_bind(
            "slider-toggle-orient", cls.toggle_orient, "Toggle orientation (vert/horiz)", keysym="o",
            menupath="Context > Params > [x]Toggle vertical orient"
        )
        cls.cl_bind(
            "slider-toggle-side", cls.toggle_side, "Toggle scale side (right/left)", keysym="r",
            menupath="Context > Params > [x]Toggle scale on left"
        )
        cls.cl_bind(
            "slider-set-lower", cls.set_low, "Enter lower bound", keysym="C-[",
            menupath="Context > Params > Set lower bound"
        )
        cls.cl_bind(
            "slider-set-upper", cls.set_hi, "Enter upper bound", keysym="C-]",
            menupath="Context > Params > Set upper bound"
        )
        cls.cl_bind(
            "slider-set-zero", cls.set_zero, "Enter zero point", keysym="C-|",
            menupath="Context > Params > Set zero point"
        )
        cls.cl_bind(
            "slider-end-edit", cls.end_edits, "End editing", keysym="RET",
            menupath="Context > Params > End edits"
        )

    async def set_low(self):
        async def hud_cb(value):
            if value is not None:
                await self.slider.dispatch_setter("min_value", float(value))
        await self.window.cmd_get_input("Slider lower bound: ", hud_cb)
        return True

    async def set_hi(self):
        async def hud_cb(value):
            if value is not None:
                await self.slider.dispatch_setter("max_value", float(value))
        await self.window.cmd_get_input("Slider upper bound: ", hud_cb)
        return True

    async def set_zero(self):
        async def hud_cb(value):
            if value is not None:
                value = float(value)
                await self.slider.dispatch_setter("zeropoint", value)
        await self.window.cmd_get_input("Slider zero point: ", hud_cb)
        return True

    async def toggle_scale(self):
        await self.slider.dispatch_setter("show_scale", (not self.slider.show_scale))
        return True

    async def toggle_orient(self):
        from mfp.gui.slidemeter_element import SlideMeterElement
        new_orient = (
            SlideMeterElement.VERTICAL
            if self.slider.orientation == SlideMeterElement.HORIZONTAL
            else SlideMeterElement.HORIZONTAL
        )
        await self.slider.dispatch_setter("orientation", new_orient)
        return True

    async def toggle_side(self):
        from mfp.gui.slidemeter_element import SlideMeterElement
        new_side = (
            SlideMeterElement.RIGHT
            if self.slider.scale_position == SlideMeterElement.LEFT
            else SlideMeterElement.RIGHT
        )

        await self.slider.dispatch_setter("scale_position", new_side)
        return True

    async def end_edits(self):
        await self.slider.end_edit()
        return True


class DialControlMode(SliderControlMode):
    pass


class DialEditMode(SliderEditMode):
    pass
