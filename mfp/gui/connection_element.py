
import cairo
from .base_element import BaseElement
from .colordb import ColorDB
from gi.repository import Clutter
import math
from mfp.gui_main import MFPGUI
from mfp import log


class ConnectionElement(BaseElement):
    display_type = "connection"
    LINE_WIDTH = 1.5

    def __init__(self, window, obj_1, port_1, obj_2, port_2, dashed=False):

        self.obj_1 = obj_1
        self.port_1 = port_1
        self.obj_2 = obj_2
        self.port_2 = port_2
        self.width = None
        self.height = None
        self.rotation = 0.0
        self.dashed = dashed
        self.dsp_connect = False

        if port_1 in obj_1.dsp_outlets:
            self.dsp_connect = True
        px, py = obj_1.get_stage_position()
        BaseElement.__init__(self, window, px, py)

        self.texture = Clutter.Canvas.new()
        self.backend.group.set_content(self.texture)
        self.texture.connect("draw", self.draw_cb)

        self.backend.group.set_reactive(True)
        if obj_1.layer is not None:
            self.move_to_layer(obj_1.layer)
        elif obj_2.layer is not None:
            self.move_to_layer(obj_2.layer)
        else:
            print("WARNING: creating ConnectionElement with no layer")
            print(obj_1, obj_2)

        self.set_size(15, 15)
        self.move(px, py)
        self.draw()

    def select(self):
        BaseElement.select(self)
        self.draw()

    def unselect(self):
        BaseElement.unselect(self)
        self.draw()

    async def delete(self):
        if (not self.dashed and self.obj_1 and self.obj_2 and
                self.obj_1.obj_id is not None and self.obj_2.obj_id is not None):
            await MFPGUI().mfp.disconnect(
                self.obj_1.obj_id, self.port_1,
                self.obj_2.obj_id, self.port_2
            )
        if self.obj_1 and self in self.obj_1.connections_out:
            self.obj_1.connections_out.remove(self)
        if self.obj_2 and self in self.obj_2.connections_in:
            self.obj_2.connections_in.remove(self)

        self.obj_1 = None
        self.obj_2 = None
        await BaseElement.delete(self)

    def draw_ports(self):
        pass

    def set_size(self, width, height):
        BaseElement.set_size(self, width, height)
        self.texture.set_size(width, height)
        self.texture.invalidate()

    def corners(self):
        if self.obj_1 and self.obj_2:
            p1 = self.obj_1.port_center(BaseElement.PORT_OUT, self.port_1)
            p2 = self.obj_2.port_center(BaseElement.PORT_IN, self.port_2)
            return [p1, p2]
        else:
            return None

    def draw(self):
        if self.obj_1 is None or self.obj_2 is None:
            return

        p1 = self.obj_1.port_center(BaseElement.PORT_OUT, self.port_1)
        p2 = self.obj_2.port_center(BaseElement.PORT_IN, self.port_2)

        if self.dsp_connect is True:
            self.width = 2.5 * self.LINE_WIDTH
        else:
            self.width = 1.5 * self.LINE_WIDTH
        self.height = ((p2[0] - p1[0]) ** 2 + (p2[1] - p1[1]) ** 2) ** 0.5
        theta = math.atan2(p1[0] - p2[0], p2[1] - p1[1])
        self.rotation = theta * 180.0 / math.pi
        self.position_x = p1[0] - math.cos(theta) * self.width / 2.0
        self.position_y = p1[1] - math.sin(theta) * self.width / 2.0

        self.set_position(self.position_x, self.position_y)
        self.backend.group.set_rotation(Clutter.RotateAxis.Z_AXIS, self.rotation, 0, 0, 0)

        self.set_size(math.ceil(self.width), math.ceil(self.height))

    def draw_cb(self, texture, ctx, width, height):
        # clear the drawing area
        ctx.save()
        ctx.set_operator(cairo.OPERATOR_CLEAR)
        ctx.paint()
        ctx.restore()

        ctx.set_operator(cairo.OPERATOR_OVER)
        ctx.set_antialias(cairo.ANTIALIAS_NONE)

        if self.dsp_connect:
            lw = 2.0 * self.LINE_WIDTH
        else:
            lw = self.LINE_WIDTH
        ctx.set_line_width(lw)

        if self.dashed:
            ctx.set_dash([4, 4])
        else:
            ctx.set_dash([])

        ctx.translate(width/2.0, lw/2.0)
        ctx.move_to(0, 0)
        ctx.line_to(0, height)
        ctx.close_path()

        c = ColorDB.to_cairo(self.get_color('stroke-color'))
        ctx.set_source_rgba(c.red, c.green, c.blue, c.alpha)
        ctx.stroke()
        return True
