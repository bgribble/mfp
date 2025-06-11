#! /usr/bin/env python
'''
plot_control.py: PlotControl major mode

Copyright Bill Gribble <grib@billgribble.com>
'''

from mfp.gui_main import MFPGUI

from ..input_mode import InputMode


class TableControlMode (InputMode):
    def __init__(self, window, element, label):
        self.manager = window.input_mgr
        self.window = window
        self.plot = element
        self.drag_x = None

        InputMode.__init__(self, "Plot control")

    @classmethod
    def init_bindings(cls):
        cls.bind(
            "plot-click-point", cls.set_point, "Add or move plot point",
            "M1DOWN",
        )
        cls.bind(
            "plot-click-point", cls.drag_point, "Add or move plot point",
            "M1-MOTION",
        )

    def plot_limits(self):
        return (
            self.plot.plot_bounds_rect.x.min,
            self.plot.plot_bounds_rect.x.max,
            self.plot.plot_bounds_rect.y.min,
            self.plot.plot_bounds_rect.y.max
        )

    async def set_point(self):
        plt_x = self.plot.plot_mouse_x
        plt_y = self.plot.plot_mouse_y
        self.drag_x = plt_x

        x_min, x_max, y_min, y_max = self.plot_limits()

        if not plt_x or not plt_y:
            return

        if (
            (plt_x <= x_max) and
            (plt_x >= x_min) and
            (plt_y <= y_max) and
            (plt_y >= y_min)
        ):
            MFPGUI().async_task(MFPGUI().mfp.send(self.plot.obj_id, 0, (int(plt_x + 0.5), plt_y)))

    async def drag_point(self):
        plt_y = self.plot.plot_mouse_y
        plt_x = self.plot.plot_mouse_x
        if not self.plot.plot_edit_draw:
            plt_x = self.drag_x

        x_min, x_max, y_min, y_max = self.plot_limits()

        if not plt_x or not plt_y:
            return

        if (
            (plt_x <= x_max) and
            (plt_x >= x_min) and
            (plt_y <= y_max) and
            (plt_y >= y_min)
        ):
            MFPGUI().async_task(MFPGUI().mfp.send(self.plot.obj_id, 0, (int(plt_x + 0.5), plt_y)))
