#! /usr/bin/env python
'''
plot_element.py
A patch element corresponding to an XY scatter or line plot
'''

from gi.repository import Clutter as clutter
from .base_element import BaseElement
from mfp import log
from mfp.mfp_app import MFPApp
from mfp.gui_main import MFPGUI
from .modes.label_edit import LabelEditMode
from .text_widget import TextWidget
from .xyplot.scatterplot import ScatterPlot
from .xyplot.scopeplot import ScopePlot

from datetime import datetime


class PlotElement (BaseElement):
    display_type = "plot"
    proc_type = "plot"

    # constants
    INIT_WIDTH = 320
    INIT_HEIGHT = 240
    LABEL_SPACE = 25
    WIDTH_PAD = 6
    HEIGHT_PAD = 4
    label_off_x = 6
    label_off_y = 0

    style_defaults = {
        'axis-color': 'default-alt-fill-color'
    }

    def __init__(self, window, x, y, params={}):
        BaseElement.__init__(self, window, x, y)

        self.param_list.extend(['x_min', 'x_max', 'y_min', 'y_max',
                                'plot_style', 'plot_type'])

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

        self.min_interval = 75
        self.last_draw = None

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
        else:
            return {}

    @property
    def plot_type(self):
        if isinstance(self.xyplot, ScatterPlot):
            return "scatter"
        elif isinstance(self.xyplot, ScopePlot):
            return "scope"
        else:
            return "none"

    def set_size(self, width, height):
        BaseElement.set_size(self, width, height)
        self.rect.set_size(width, height)
        if self.xyplot:
            self.xyplot.set_size(width-self.WIDTH_PAD, height-self.LABEL_SPACE-self.WIDTH_PAD)

    def create_display(self, width, height):
        self.rect = clutter.Rectangle()
        self.label = TextWidget.build(self)

        # group
        clutter.Group.set_size(self, width, height)

        # rectangle box
        self.rect.set_border_width(2)
        self.rect.set_border_color(self.get_color('stroke-color'))
        self.rect.set_position(0, 0)
        self.rect.set_size(width, height)
        self.rect.set_depth(-1)
        self.rect.set_reactive(False)

        # label
        self.label.set_position(self.label_off_x, self.label_off_y)
        self.label.set_color(self.get_color('text-color'))
        self.label.set_font_name(self.get_fontspec())
        self.label.signal_listen('text-changed', self.label_changed_cb)
        self.label.set_reactive(False)

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
            if (delta_msec > self.min_interval):
                thunk()
            else:
                MFPGUI().clutter_do_later(self.min_interval-delta_msec, thunk)
        else:
            thunk()

    def update(self):
        self.draw_ports()

    def get_label(self):
        return self.label

    def label_edit_start(self):
        # FIXME set label to editing style
        pass

    async def label_edit_finish(self, *args):
        t = self.label.get_text()

        if t != self.label_text:
            parts = t.split(' ', 1)
            self.obj_type = parts[0]
            if len(parts) > 1:
                self.obj_args = parts[1]

            log.debug("PlotElement: type=%s, args=%s" % (self.obj_type, self.obj_args))
            self.proc_type = self.obj_type
            await self.create(self.proc_type, self.obj_args)

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

    def select(self):
        BaseElement.select(self)
        self.rect.set_border_color(self.app_window.color_selected)

    def unselect(self):
        BaseElement.unselect(self)
        self.rect.set_border_color(self.app_window.color_unselected)

    async def make_edit_mode(self):
        return LabelEditMode(self.app_window, self, self.label)

    def command(self, action, data):
        if self.xyplot.command(action, data):
            return True
        elif action == "clear":
            self.xyplot.clear(data)
            return True
        elif action == "bounds":
            self.set_bounds(*data)
            return True
        elif BaseElement.command(self, action, data):
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

        if self.obj_args is None:
            self.label.set_text("%s" % (self.obj_type,))
        else:
            self.label.set_text("%s %s" % (self.obj_type, self.obj_args))

        x_min = params.get('x_min', self.x_min)
        x_max = params.get('x_max', self.x_max)
        y_min = params.get('y_min', self.y_min)
        y_max = params.get('y_max', self.y_max)

        self.set_bounds(x_min, y_min, x_max, y_max)

        if self.xyplot is not None:
            self.xyplot.configure(params)

        BaseElement.configure(self, params)
