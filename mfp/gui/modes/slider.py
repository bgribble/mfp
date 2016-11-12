#! /usr/bin/env python2.6
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

        self.bind("M1DOUBLEDOWN", self.set_value, "Set fader value")
        self.bind("M1DOWN", self.drag_start, "Adjust fader or move element")
        self.bind("S-M1DOWN", self.drag_start)
        self.bind("C-M1DOWN", self.drag_start)
        self.bind("M1-MOTION", lambda: self.drag_selected(1.0),
                  "Change value (1x speed)")
        self.bind("S-M1-MOTION", lambda: self.drag_selected(0.25),
                  "Change value (1/4 speed)")
        self.bind("C-M1-MOTION", lambda: self.drag_selected(0.05),
                  "Change value (1/20 speed)")
        self.bind("M1UP", self.drag_end, "Release fader")
        self.bind("S-M1UP", self.drag_end)
        self.bind("C-M1UP", self.drag_end)
        self.bind("UP", lambda: self.change_value(0.01))
        self.bind("DOWN", lambda: self.change_value(-0.01))
        self.bind("S-UP", lambda: self.change_value(0.001))
        self.bind("S-DOWN", lambda: self.change_value(-0.001))

    def set_value(self):
        new_value = self.slider.pixpos2value(self.manager.pointer_x, self.manager.pointer_y)
        self.slider.update_value(new_value)

    def change_value(self, fraction):
        dv = fraction * abs(self.slider.max_value - self.slider.min_value)

        self.slider.update_value(self.slider.value + dv)
        return True

    def drag_start(self):
        if self.manager.pointer_obj == self.slider:
            if self.slider not in self.window.selected:
                self.window.select(self.slider)

            if (self.slider.slider_enable 
                and self.slider.point_in_slider(self.manager.pointer_x, 
                                                self.manager.pointer_y)):
                self.drag_started = True
                self.drag_start_x = self.manager.pointer_x
                self.drag_start_y = self.manager.pointer_y
                self.drag_last_x = self.manager.pointer_x
                self.drag_last_y = self.manager.pointer_y
                return True
            else:
                return False
        else:
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

        self.bind("RET", self.end_edits, "End editing")
        self.bind("s", self.toggle_scale, "Toggle scale display (on/off)")
        self.bind("o", self.toggle_orient, "Toggle orientation (vert/horiz)")
        self.bind("r", self.toggle_side, "Toggle scale side (right/left)")
        self.bind("C-[", self.set_low, "Enter lower bound")
        self.bind("C-]", self.set_hi, "Enter upper bound")
        self.bind("C-|", self.set_zero, "Enter zero point")

    def set_low(self): 
        def hud_cb(value): 
            if value is not None:
                self.slider.set_bounds(float(value), self.slider.max_value)
        self.window.get_prompted_input("Slider lower bound: ", hud_cb)
        return True 

    def set_hi(self): 
        def hud_cb(value): 
            if value is not None:
                self.slider.set_bounds(self.slider.min_value, float(value))
        self.window.get_prompted_input("Slider upper bound: ", hud_cb)
        return True 

    def set_zero(self): 
        def hud_cb(value): 
            if value is not None:
                if value != "None":
                    self.slider.set_zeropoint(float(value))
                else: 
                    self.slider.set_zeropoint(None)
        self.window.get_prompted_input("Slider zero point: ", hud_cb)
        return True 

    def toggle_scale(self):
        self.slider.set_show_scale(not self.slider.show_scale)
        self.slider.update()
        self.slider.send_params()
        return True 

    def toggle_orient(self):
        if self.slider.orientation == self.slider.HORIZONTAL:
            self.slider.set_orientation(self.slider.VERTICAL)
        else: 
            self.slider.set_orientation(self.slider.HORIZONTAL)

        self.slider.update()
        self.slider.send_params()
        return True 

    def toggle_direction(self):
        if self.slider.direction == self.slider.POSITIVE:
            self.slider.direction = self.slider.NEGATIVE
        else: 
            self.slider.direction = self.slider.POSITIVE

        self.slider.update()
        self.slider.send_params()
        return True 

    def toggle_side(self):
        if self.slider.scale_position == self.slider.RIGHT:
            self.slider.scale_position = self.slider.LEFT
        else: 
            self.slider.scale_position = self.slider.RIGHT 

        self.slider.update()
        self.slider.send_params()
        return True 

    def end_edits(self):
        self.slider.end_edit()
        return True 

class DialControlMode(SliderControlMode):
    pass

class DialEditMode(SliderEditMode):
    pass 


