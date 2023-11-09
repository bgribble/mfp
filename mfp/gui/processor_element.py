#! /usr/bin/env python
'''
processor_element.py
A patch element corresponding to a signal or control processor
'''

from gi.repository import Clutter
import cairo
from .text_widget import TextWidget
from .colordb import ColorDB
from .modes.label_edit import LabelEditMode
from ..gui_main import MFPGUI

from .clutter.base_element import ClutterBaseElementBackend

class ProcessorElement (ClutterBaseElementBackend):
    display_type = "processor"
    proc_type = None

    # constants
    label_off_x = 3
    label_off_y = 0

    def __init__(self, window, x, y, params={}):
        super().__init__(window, x, y)

        self.param_list.extend([
            "show_label",
            "export_x",
            "export_y",
            "export_w",
            "export_h"
        ])
        self.show_label = params.get("show_label", True)

        # display elements
        self.texture = None
        self.label = None
        self.label_text = None
        self.export_x = None
        self.export_y = None
        self.export_w = None
        self.export_h = None
        self.export_created = False

        # create display
        self.create_display()
        self.set_size(35, 25)
        self.move(x, y)

        self.obj_state = self.OBJ_HALFCREATED

        self.update()

    def create_display(self):
        # box
        self.texture = Clutter.Canvas.new()
        self.group.set_content(self.texture)
        self.texture.connect("draw", self.draw_cb)
        self.texture.set_size(35, 25)

        # label
        self.label = TextWidget.get_factory()(self)
        self.label.set_position(self.label_off_x, self.label_off_y)
        self.label.set_color(self.get_color('text-color'))
        self.label.set_font_name(self.get_fontspec())
        self.label.signal_listen('text-changed', self.label_changed_cb)
        self.label.set_reactive(False)

        if not self.show_label:
            self.label.hide()

        self.group.set_reactive(True)

    def update(self):
        if self.show_label or self.obj_state == self.OBJ_HALFCREATED:
            label_width = self.label.get_property('width') + 14
        else:
            label_width = 0

        box_width = self.export_w or 0

        new_w = None
        num_ports = max(self.num_inlets, self.num_outlets)
        port_width = (num_ports * self.get_style('porthole_minspace')
                      + 2*self.get_style('porthole_border'))

        new_w = max(35, port_width, label_width, box_width)

        self.set_size(new_w, self.texture.get_property('height'))

    def draw_cb(self, texture, ct, width, height):
        lw = 2.0

        w = width - lw
        h = height - lw

        # clear the drawing area
        ct.save()
        ct.set_operator(cairo.OPERATOR_CLEAR)
        ct.paint()
        ct.restore()

        ct.set_line_width(lw)
        ct.set_antialias(cairo.ANTIALIAS_NONE)
        ct.translate(lw/2.0, lw/2.0)
        ct.move_to(0, 0)
        ct.line_to(0, h)
        ct.line_to(w, h)
        ct.line_to(w, 0)
        ct.line_to(0, 0)
        ct.close_path()

        # fill to paint the background
        color = ColorDB().normalize(self.get_color('fill-color'))
        ct.set_source_rgba(color.red, color.green, color.blue, color.alpha)
        ct.fill_preserve()

        # stroke to draw the outline
        color = ColorDB().normalize(self.get_color('stroke-color'))
        ct.set_source_rgba(color.red, color.green, color.blue, color.alpha)

        if self.obj_state == self.OBJ_COMPLETE:
            ct.set_dash([])
        else:
            ct.set_dash([8, 4])
        ct.set_line_width(lw)
        ct.stroke()
        return True

    def get_label(self):
        return self.label

    def label_edit_start(self):
        self.obj_state = self.OBJ_HALFCREATED
        if not self.show_label:
            self.label.show()
        self.update()

    async def label_edit_finish(self, widget, text=None):
        if text is not None:
            parts = text.split(' ', 1)
            obj_type = parts[0]
            if len(parts) > 1:
                obj_args = parts[1]
            else:
                obj_args = None

            await self.create(obj_type, obj_args)

            # obj_args may get forcibly changed on create
            if self.obj_args and (len(parts) < 2 or self.obj_args != parts[1]):
                self.label.set_text(self.obj_type + ' ' + self.obj_args)

        if self.obj_id is not None and self.obj_state != self.OBJ_COMPLETE:
            self.obj_state = self.OBJ_COMPLETE

        if not self.show_label:
            self.label.hide()

        self.update()

    def label_changed_cb(self, *args):
        newtext = self.label.get_text()
        if newtext != self.label_text:
            self.label_text = newtext
            self.update()

    def set_size(self, w, h):
        super().set_size(w, h)

        self.texture.set_size(w, h)
        self.texture.invalidate()

    def select(self):
        super().select()
        self.label.set_color(self.get_color('text-color'))
        self.texture.invalidate()

    def unselect(self):
        super().unselect()
        self.label.set_color(self.get_color('text-color'))
        self.texture.invalidate()

    async def make_edit_mode(self):
        return LabelEditMode(self.app_window, self, self.label)

    def configure(self, params):
        if self.obj_args is None:
            self.label.set_text("%s" % (self.obj_type,))
        else:
            self.label.set_text("%s %s" % (self.obj_type, self.obj_args))

        need_update = False

        labelheight = 20
        if "show_label" in params:
            oldval = self.show_label
            self.show_label = params.get("show_label")
            if oldval ^ self.show_label:
                need_update = True
                if self.show_label:
                    self.label.show()
                else:
                    self.label.hide()

        self.export_x = params.get("export_x")
        self.export_y = params.get("export_y")
        self.export_w = params.get("export_w")
        self.export_h = params.get("export_h")
        if self.export_x is not None and self.export_y is not None:
            self.export_created = True

        params["width"] = max(self.width, params.get("export_w") or 0)
        params["height"] = max(self.height, (params.get("export_h") or 0) + labelheight)

        super().configure(params)

        if self.obj_id is not None and self.obj_state != self.OBJ_COMPLETE:
            self.obj_state = self.OBJ_COMPLETE
            if self.export_created:
                MFPGUI().mfp.create_export_gui.task(self.obj_id)
                need_update = True

        if "debug" in params:
            need_update = True

        if need_update:
            self.update()

