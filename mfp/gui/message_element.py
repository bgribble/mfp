#! /usr/bin/env python
'''
message_element.py
A patch element corresponding to a clickable message

Copyright (c) 2010 Bill Gribble <grib@billgribble.com>
'''

from gi.repository import Clutter
import cairo
from mfp.gui_main import MFPGUI
from mfp.utils import catchall
from .text_widget import TextWidget
from .patch_element import PatchElement
from .connection_element import ConnectionElement
from .modes.label_edit import LabelEditMode
from .modes.transient import TransientMessageEditMode
from .modes.clickable import ClickableControlMode
from .colordb import ColorDB


class MessageElement (PatchElement):
    display_type = "message"
    proc_type = "message"

    PORT_TWEAK = 5

    def __init__(self, window, x, y):
        PatchElement.__init__(self, window, x, y)

        self.message_text = None
        self.clickstate = False

        # create elements
        self.texture = Clutter.Canvas.new()
        self.set_content(self.texture)
        self.texture.connect("draw", self.draw_cb)
        self.texture.set_size(35, 25)

        self.label = TextWidget(self)

        self.set_reactive(True)
        self.set_size(35, 25)
        self.obj_state = self.OBJ_HALFCREATED
        self.texture.invalidate()

        # configure label
        self.label.set_position(4, 1)
        self.label.set_color(self.get_color('text-color'))
        self.label.set_font_name(self.get_fontspec())
        self.label.connect('text-changed', self.text_changed_cb)

        self.move(x, y)

        # request update when value changes
        self.update_required = True

    def set_size(self, width, height):
        PatchElement.set_size(self, width, height)
        self.texture.set_size(width, height)
        self.update()

    @catchall
    def draw_cb(self, texture, ct, width, height):
        if self.clickstate:
            lw = 5.0
        else:
            lw = 2.0

        w = width - lw
        h = height - lw
        c = None

        # clear the drawing area
        ct.save()
        ct.set_operator(cairo.OPERATOR_CLEAR)
        ct.paint()
        ct.restore()

        if self.obj_state == self.OBJ_COMPLETE:
            ct.set_dash([])
        else:
            ct.set_dash([8, 4])

        ct.set_line_width(lw)

        ct.set_antialias(cairo.ANTIALIAS_NONE)
        ct.translate(lw / 2.0, lw / 2.0)
        ct.move_to(0, 0)
        ct.line_to(0, h)
        ct.line_to(w, h)
        ct.curve_to(w - 8, h - 8, w - 8, 8, w, 0)
        ct.line_to(0, 0)
        ct.close_path()

        # fill to paint the background
        c = ColorDB.to_cairo(self.get_color('fill-color'))
        ct.set_source_rgba(c.red, c.green, c.blue, c.alpha)
        ct.fill_preserve()

        # stroke to draw the outline
        c = ColorDB.to_cairo(self.get_color('stroke-color'))
        ct.set_source_rgba(c.red, c.green, c.blue, c.alpha)
        ct.stroke()

        return True

    def update(self):
        self.texture.invalidate()
        self.draw_ports()

    def clicked(self, *args):
        self.clickstate = True
        if self.obj_id is not None:
            MFPGUI().async_task(MFPGUI().mfp.send_bang(self.obj_id, 0))
        self.texture.invalidate()
        return False

    def unclicked(self):
        self.clickstate = False
        self.texture.invalidate()
        return False

    def label_edit_start(self):
        self.obj_state = self.OBJ_HALFCREATED
        self.texture.invalidate()

    async def label_edit_finish(self, widget=None, text=None):
        if text is not None and text != self.message_text:
            self.message_text = text
            await self.create(self.proc_type, self.message_text)

        if self.obj_id is not None:
            self.obj_state = self.OBJ_COMPLETE
            self.send_params()
            self.update()

    @catchall
    def text_changed_cb(self, *args):
        lwidth = self.label.get_property('width')
        bwidth = self.texture.get_property('width')

        new_w = None
        if (lwidth > (bwidth - 20)):
            new_w = lwidth + 20
        elif (bwidth > 35) and (lwidth < (bwidth - 20)):
            new_w = max(35, lwidth + 20)

        if new_w is not None:
            self.set_size(new_w, self.texture.get_property('height'))
            self.update()

    def configure(self, params):
        if params.get('value') is not None:
            self.message_text = repr(params.get('value'))
            self.label.set_text(self.message_text)
            params['width'] = None
            params['height'] = None
        elif self.obj_args is not None:
            self.message_text = self.obj_args
            self.label.set_text(self.obj_args)
            params['width'] = None
            params['height'] = None

        if self.obj_state != self.OBJ_COMPLETE and self.obj_id is not None:
            self.obj_state = self.OBJ_COMPLETE
            self.update()
        PatchElement.configure(self, params)

    def port_position(self, port_dir, port_num):
        # tweak the right input port display to be left of the "kick"
        if port_dir == PatchElement.PORT_IN and port_num == 1:
            default = PatchElement.port_position(self, port_dir, port_num)
            return (default[0] - self.PORT_TWEAK, default[1])
        else:
            return PatchElement.port_position(self, port_dir, port_num)

    def select(self):
        PatchElement.select(self)
        self.label.set_color(self.get_color('text-color'))
        self.texture.invalidate()

    def unselect(self):
        PatchElement.unselect(self)
        self.label.set_color(self.get_color('text-color'))
        self.texture.invalidate()

    def make_edit_mode(self):
        return LabelEditMode(self.stage, self, self.label)

    def make_control_mode(self):
        return ClickableControlMode(self.stage, self, "Message control")


class TransientMessageElement (MessageElement):
    ELBOW_ROOM = 50

    def __init__(self, window, x, y):
        self.target_obj = [t for t in window.selected if t is not self]
        self.target_port = None

        pos_x, pos_y = self.target_obj[0].get_stage_position()
        MessageElement.__init__(self, window, pos_x, pos_y - self.ELBOW_ROOM)

        self.message_text = "Bang"
        self.num_inlets = 0
        self.num_outlets = 1
        self.label.set_text(self.message_text)
        self.obj_state = self.OBJ_COMPLETE
        self.draw_ports()
        self.set_port(0)

    def set_port(self, portnum):
        if portnum == self.target_port:
            return True

        for c in self.connections_out:
            c.delete()

        self.target_port = portnum
        for to in self.target_obj:
            c = ConnectionElement(self.stage, self, 0, to, self.target_port)
            self.stage.active_layer().add(c)
            self.stage.register(c)
            self.connections_out.append(c)
            to.connections_in.append(c)

        return True

    async def end_edit(self):
        await PatchElement.end_edit(self)
        if self.obj_state == self.OBJ_COMPLETE:
            await self.delete()

    def label_edit_start(self):
        self.label.set_text(self.message_text)
        self.label.set_selection(0, len(self.message_text))
        self.texture.invalidate()

    async def label_edit_finish(self, widget=None, text=None):
        if text is not None:
            self.message_text = text
            for to in self.target_obj:
                if to is not self:
                    await MFPGUI().mfp.eval_and_send(
                        to.obj_id,
                        self.target_port,
                        self.message_text
                    )
        for to in self.target_obj:
            self.stage.select(to)
        self.message_text = None
        await self.delete()

    def make_edit_mode(self):
        return TransientMessageEditMode(self.stage, self, self.label)
