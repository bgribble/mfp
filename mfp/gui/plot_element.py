#! /usr/bin/env python
'''
plot_element.py
A patch element corresponding to an XY scatter or line plot
'''

from gi.repository import Clutter as clutter
import math
from patch_element import PatchElement
from mfp import MFPGUI
from mfp import log
from input_mode import InputMode
from .modes.label_edit import LabelEditMode
from .xyplot.scatterplot import ScatterPlot
from .xyplot.scopeplot import ScopePlot


class PlotElement (PatchElement):

    display_type = "plot"
    proc_type = "plot"

    # constants
    INIT_WIDTH = 320
    INIT_HEIGHT = 240
    LABEL_SPACE = 25
    label_off_x = 6
    label_off_y = 0

    def __init__(self, window, x, y, params={}):
        PatchElement.__init__(self, window, x, y)

        # display elements
        self.rect = None
        self.label = None
        self.label_text = None
        self.xyplot = None

        # display bounds
        self.x_min = 0.0
        self.x_max = 6.28
        self.y_min = -1.0
        self.y_max = 1.0

        # grab params for creation

        # create display
        self.create_display(self.INIT_WIDTH + 6, self.INIT_HEIGHT + self.LABEL_SPACE + 4)
        self.move(x, y)
        self.update()

    def create_display(self, width, height):
        self.rect = clutter.Rectangle()
        self.label = clutter.Text()

        # group
        clutter.Group.set_size(self, width, height)

        # rectangle box
        self.rect.set_border_width(2)
        self.rect.set_border_color(self.stage.color_unselected)
        self.rect.set_position(0, 0)
        self.rect.set_size(width, height)
        self.rect.set_depth(-1)
        self.rect.set_reactive(False)

        # label
        self.label.set_position(self.label_off_x, self.label_off_y)
        self.label.set_color(self.stage.color_unselected)
        self.label.connect('text-changed', self.label_changed_cb)
        self.label.set_reactive(False)

        # chart created later
        self.xyplot = None

        self.add_actor(self.label)
        self.add_actor(self.rect)
        self.set_reactive(True)

    # methods useful for interaction
    def set_bounds(self, x_min, y_min, x_max, y_max):
        self.x_min = x_min
        self.x_max = x_max
        self.y_min = y_min
        self.y_max = y_max

        self.xyplot.set_bounds(x_min, y_min, x_max, y_max)

    def update(self):
        self.draw_ports()

    def get_label(self):
        return self.label

    def label_edit_start(self):
        # FIXME set label to editing style
        pass

    def label_edit_finish(self, *args):
        t = self.label.get_text()

        if t != self.label_text:
            parts = t.split(' ', 1)
            self.obj_type = parts[0]
            if len(parts) > 1:
                self.obj_args = parts[1]

            log.debug("PlotElement: type=%s, args=%s" % (self.obj_type, self.obj_args))
            self.display_type = self.obj_type
            self.proc_type = self.obj_type

            self.create(self.proc_type, self.obj_args)

            if self.obj_type == "scatter":
                self.xyplot = ScatterPlot(self.INIT_WIDTH, self.INIT_HEIGHT)
            elif self.obj_type == "scope":
                self.xyplot = ScopePlot(self.INIT_WIDTH, self.INIT_HEIGHT)

            if self.xyplot:
                self.add_actor(self.xyplot)
                self.xyplot.set_position(3, self.LABEL_SPACE)

            if self.obj_id is None:
                log.debug("PlotElement: could not create", self.obj_type, self.obj_args)
            else:
                self.send_params()
                self.draw_ports()

        # FIXME set label to non-editing style
        self.update()

    def label_changed_cb(self, *args):
        pass

    def move(self, x, y):
        self.position_x = x
        self.position_y = y
        clutter.Group.set_position(self, x, y)

        for c in self.connections_out:
            c.draw()

        for c in self.connections_in:
            c.draw()

    def set_size(self, w, h):
        print "chart_element: set_size", w, h
        self.size_w = w
        self.size_h = h

        self.rect.set_size(w, h)
        self.rect.set_position(0, 0)
        self.xyplot.set_size(w - 4, h - self.LABEL_SPACE - 4)

        clutter.Group.set_size(self, w, h)

        self.draw_ports()

        for c in self.connections_out:
            c.draw()

        for c in self.connections_in:
            c.draw()

    def select(self):
        self.selected = True
        self.rect.set_border_color(self.stage.color_selected)

    def unselect(self):
        self.selected = False
        self.rect.set_border_color(self.stage.color_unselected)

    def delete(self):
        for c in self.connections_out + self.connections_in:
            c.delete()

        PatchElement.delete(self)

    def make_edit_mode(self):
        return LabelEditMode(self.stage, self, self.label)

    def command(self, action, data):
        if self.xyplot.command(action, data):
            return True
        elif action == "clear":
            self.xyplot.clear(data)
            return True
        elif action == "bounds":
            self.set_bounds(*data)
            return True
        elif PatchElement.command(self, action, data):
            return True

        return False

    def configure(self, params):
        if "plot_type" in params and self.xyplot is None:
            if params["plot_type"] == "scatter":
                self.xyplot = ScatterPlot(self.INIT_WIDTH, self.INIT_HEIGHT)
            elif params["plot_type"] == "signal":
                pass

            if self.xyplot:
                self.add_actor(self.xyplot)
                self.xyplot.set_position(3, self.LABEL_SPACE)

        if self.obj_args is None:
            self.label.set_text("%s" % (self.obj_type,))
        else:
            self.label.set_text("%s %s" % (self.obj_type, self.obj_args))

        if self.xyplot is not None:
            self.xyplot.configure(params)

        PatchElement.configure(self, params)
