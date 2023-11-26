#! /usr/bin/env python
'''
plot_element.py
A patch element corresponding to an XY scatter or line plot
'''


from abc import ABC

from mfp import log
from mfp.gui_main import MFPGUI
from .backend_interfaces import BackendInterface
from .base_element import BaseElement
from .modes.label_edit import LabelEditMode
from .text_widget import TextWidget


class PlotElementImpl(ABC, BackendInterface):
    pass


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

    def __init__(self, window, x, y, params=None):
        if params is None:
            params = {}

        super().__init__(window, x, y)

        self.param_list.extend(['x_min', 'x_max', 'y_min', 'y_max',
                                'plot_style', 'plot_type'])

        # display bounds
        self.x_min = 0.0
        self.x_max = 6.28
        self.y_min = -1.0
        self.y_max = 1.0

        self.min_interval = 75
        self.last_draw = None

        # label
        self.label_text = None
        self.label = TextWidget.build(self)
        self.label.set_position(self.label_off_x, self.label_off_y)
        self.label.set_color(self.get_color('text-color'))
        self.label.set_font_name(self.get_fontspec())
        self.label.signal_listen('text-changed', self.label_changed_cb)
        self.label.set_reactive(False)

    @classmethod
    def get_factory(cls):
        return PlotElementImpl.get_backend(MFPGUI().appwin.backend_name)

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

    async def make_edit_mode(self):
        return LabelEditMode(self.app_window, self, self.label)

    def configure(self, params):
        if self.obj_args is None:
            self.label.set_text("%s" % (self.obj_type,))
        else:
            self.label.set_text("%s %s" % (self.obj_type, self.obj_args))

        x_min = params.get('x_min', self.x_min)
        x_max = params.get('x_max', self.x_max)
        y_min = params.get('y_min', self.y_min)
        y_max = params.get('y_max', self.y_max)

        self.set_bounds(x_min, y_min, x_max, y_max)

        super().configure(params)
