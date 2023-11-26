"""
clutter/plot_element.py -- clutter backend for x/y plot elements

Copyright (c) Bill Gribble <grib@billgribble.com>
"""

from datetime import datetime
from gi.repository import Clutter

from mfp.gui_main import MFPGUI
from mfp.mfp_app import MFPApp
from mfp import log

from .base_element import ClutterBaseElementBackend
from ..plot_element import (
    PlotElement,
    PlotElementImpl
)
from .xyplot.scatterplot import ScatterPlot
from .xyplot.scopeplot import ScopePlot


class ClutterPlotElementImpl(PlotElement, PlotElementImpl, ClutterBaseElementBackend):
    backend_name = "clutter"

    def __init__(self, window, x, y):
        super().__init__(window, x, y)


        # display elements
        self.rect = None
        self.xyplot = None

        # create display
        width = self.INIT_WIDTH + self.WIDTH_PAD
        height = self.INIT_HEIGHT + self.LABEL_SPACE + self.HEIGHT_PAD
        self.create_display(width, height)
        self.set_size(width, height)
        self.move(x, y)
        self.update()

    @property
    def plot_style(self):
        if self.xyplot:
            return self.xyplot.save_style()
        return {}

    @property
    def plot_type(self):
        if isinstance(self.xyplot, ScatterPlot):
            return "scatter"
        if isinstance(self.xyplot, ScopePlot):
            return "scope"
        return "none"

    def set_size(self, width, height):
        super().set_size(width, height)
        self.rect.set_size(width, height)
        if self.xyplot:
            self.xyplot.set_size(width-self.WIDTH_PAD, height-self.LABEL_SPACE-self.WIDTH_PAD)

    def create_display(self, width, height):
        self.rect = Clutter.Rectangle()

        # group
        self.group.set_size(width, height)

        # rectangle box
        self.rect.set_border_width(2)
        self.rect.set_border_color(self.get_color('stroke-color'))
        self.rect.set_position(0, 0)
        self.rect.set_size(width, height)
        self.rect.set_depth(-1)
        self.rect.set_reactive(False)

        # chart created later
        self.xyplot = None

        self.group.add_actor(self.rect)
        self.group.set_reactive(True)

    # methods useful for interaction
    def set_bounds(self, x_min, y_min, x_max, y_max):
        update = False

        if x_min != self.x_min:
            self.x_min = x_min
            update = True
        if x_max != self.x_max:
            self.x_max = x_max
            update = True
        if y_min != self.y_min:
            self.y_min = y_min
            update = True
        if y_max != self.y_max:
            self.y_max = y_max
            update = True

        if update:
            self.xyplot.set_bounds(x_min, y_min, x_max, y_max)
            self.send_params()

    def draw_complete_cb(self):
        def thunk():
            self.last_draw = datetime.now()
            MFPGUI().mfp.send_methodcall.task(
                self.obj_id, 0, "draw_complete"
            )

        if self.last_draw is not None:
            time_since_last = datetime.now() - self.last_draw
            delta_msec = time_since_last.total_seconds() * 1000.0
            if delta_msec > self.min_interval:
                thunk()
            else:
                MFPGUI().clutter_do_later(self.min_interval-delta_msec, thunk)
        else:
            thunk()

    def select(self):
        super().select()
        self.rect.set_border_color(self.app_window.color_selected)

    def unselect(self):
        super().unselect()
        self.rect.set_border_color(self.app_window.color_unselected)

    def command(self, action, data):
        if self.xyplot.command(action, data):
            return True
        if action == "clear":
            self.xyplot.clear(data)
            return True
        if action == "bounds":
            self.set_bounds(*data)
            return True
        if super().command(action, data):
            return True

        return False

    def configure(self, params):
        if "plot_type" in params and self.xyplot is None:
            if params["plot_type"] == "scatter":
                self.xyplot = ScatterPlot(self, self.INIT_WIDTH, self.INIT_HEIGHT)
            elif params["plot_type"] == "scope":
                self.xyplot = ScopePlot(self, self.INIT_WIDTH, self.INIT_HEIGHT,
                                        MFPApp().samplerate)
                self.xyplot.draw_complete_cb = self.draw_complete_cb
            if self.xyplot:
                self.group.add_actor(self.xyplot)
                self.xyplot.set_position(3, self.LABEL_SPACE)

        if self.xyplot is not None:
            self.xyplot.configure(params)

        super().configure(params)
