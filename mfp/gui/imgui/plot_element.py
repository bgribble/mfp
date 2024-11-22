"""
imgui/plot_element.py -- imgui backend for x/y plot elements, using implot

Copyright (c) Bill Gribble <grib@billgribble.com>
"""

from datetime import datetime

from flopsy import mutates
from mfp.gui_main import MFPGUI
from mfp import log
from .base_element import ImguiBaseElementImpl
from ..plot_element import (
    PlotElement,
    PlotElementImpl
)


class ImguiPlotElementImpl(PlotElementImpl, ImguiBaseElementImpl, PlotElement):
    backend_name = "clutter"

    def __init__(self, window, x, y):
        super().__init__(window, x, y)

        # create display
        width = self.INIT_WIDTH + self.WIDTH_PAD
        height = self.INIT_HEIGHT + self.LABEL_SPACE + self.HEIGHT_PAD

        self.width = width
        self.height = height
        self.plot_type = "none"
        self.plot_style = {}

    async def set_size(self, width, height, **kwargs):
        await super().set_size(width, height, **kwargs)

    # methods useful for interaction
    @mutates('x_min', 'x_max', 'y_min', 'y_max')
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
        """
        signal the main app when the draw is complete (to unlock the
        shared mem area for writing)
        """
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
            #else:
            #    clutter_do_later(self.min_interval-delta_msec, thunk)
        else:
            thunk()

    def command(self, action, data):
        # not sure where this is used
        #if self.xyplot.command(action, data):
        #    return True
        if action == "clear":
            return True
        if action == "bounds":
            return True
        if super().command(action, data):
            return True

        return False
