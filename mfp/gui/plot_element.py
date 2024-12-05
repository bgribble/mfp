#! /usr/bin/env python
'''
plot_element.py
A patch element corresponding to an XY scatter or line plot
'''


from abc import ABCMeta

from mfp import log
from mfp.gui_main import MFPGUI
from .backend_interfaces import BackendInterface
from .base_element import BaseElement
from .colordb import ColorDB
from .modes.label_edit import LabelEditMode
from .param_info import ParamInfo, DictOfRGBAColor
from .text_widget import TextWidget


class PlotElementImpl(BackendInterface, metaclass=ABCMeta):
    pass


class PlotElement (BaseElement):
    display_type = "plot"
    proc_type = "plot"

    extra_params = {
        'x_min': ParamInfo(label="X axis min value", param_type=float, null=True, show=True),
        'y_min': ParamInfo(label="Y axis min value", param_type=float, null=True, show=True),
        'x_max': ParamInfo(label="X axis max value", param_type=float, null=True, show=True),
        'y_max': ParamInfo(label="Y axis max value", param_type=float, null=True, show=True),
        'x_label': ParamInfo(label="X axis label", param_type=str, show=True),
        'y_label': ParamInfo(label="Y axis label", param_type=str, show=True),
        'plot_type': ParamInfo(label="Plot type", param_type=str, null=True, show=True),
        'plot_style': ParamInfo(label="Plot style", param_type=dict, show=False),
        'curve_label': ParamInfo(label="Curve labels", param_type=dict, show=True),
        'curve_color': ParamInfo(label="Curve colors", param_type=DictOfRGBAColor, show=True),
        'mark_type': ParamInfo(label="Mark types", param_type=dict, show=True),
        'stroke_type': ParamInfo(label="Stroke types", param_type=dict, show=True),
    }

    store_attrs = {
        **BaseElement.store_attrs, **extra_params
    }

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

        self.param_list.extend([*PlotElement.extra_params])

        # display bounds
        self.x_min = None
        self.x_max = None
        self.x_label = None

        self.y_min = None
        self.y_max = None
        self.y_label = None

        self.plot_type = "none"
        self.plot_style = {}
        self.mark_type = {}
        self.stroke_type = {}
        self.curve_label = {}
        self.curve_color = {}

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
    def get_backend(cls, backend_name):
        return PlotElementImpl.get_backend(backend_name)

    async def update(self):
        self.draw_ports()

    def get_label(self):
        return self.label

    async def label_edit_start(self):
        # FIXME set label to editing style
        pass

    async def label_edit_finish(self, *args):
        t = self.label.get_text()

        if t != self.label_text:
            parts = t.split(' ', 1)
            self.obj_type = parts[0]
            if len(parts) > 1:
                self.obj_args = parts[1]

            self.proc_type = self.obj_type
            await self.create(self.proc_type, self.obj_args)

            if self.obj_id is None:
                log.debug("PlotElement: could not create", self.obj_type, self.obj_args)
            else:
                self.send_params()
                self.draw_ports()

            # FIXME set label to non-editing style

    def label_changed_cb(self, *args):
        pass

    async def make_edit_mode(self):
        return LabelEditMode(self.app_window, self, self.label)

    async def configure(self, params):
        if self.obj_args is None:
            self.label.set_text("%s" % (self.obj_type,))
        else:
            self.label.set_text("%s %s" % (self.obj_type, self.obj_args))

        x_min = params.get('x_min', self.x_min)
        x_max = params.get('x_max', self.x_max)
        y_min = params.get('y_min', self.y_min)
        y_max = params.get('y_max', self.y_max)

        self.plot_type = params.get('plot_type', self.plot_type)

        self.set_bounds(x_min, y_min, x_max, y_max)

        for c in range(params.get("channels", 1)):
            if c not in self.curve_label:
                self.curve_label[c] = f"Curve {c}"
            if c not in self.mark_type:
                self.mark_type[c] = "default"
            if c not in self.stroke_type:
                self.stroke_type[c] = "default"
            if c not in self.curve_color:
                self.curve_color[c] = ColorDB().find(f'default-data-color-{c}')

        await super().configure(params)
