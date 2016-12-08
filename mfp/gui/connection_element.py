
import cairo
from .patch_element import PatchElement
from .colordb import ColorDB
from gi.repository import Clutter
import math
from mfp import MFPGUI


class ConnectionElement(PatchElement):
    display_type = "connection"
    LINE_WIDTH = 1.25

    def __init__(self, window, obj_1, port_1, obj_2, port_2, dashed=False):

        self.texture = Clutter.CairoTexture.new(10, 10)
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
        PatchElement.__init__(self, window, px, py)

        self.texture.connect("draw", self.draw_cb)
        self.add_actor(self.texture)
        self.set_reactive(True)
        if obj_1.layer is not None:
            self.move_to_layer(obj_1.layer)
        elif obj_2.layer is not None:
            self.move_to_layer(obj_2.layer)
        else:
            print "WARNING: creating ConnectionElement with no layer"
            print obj_1, obj_2

        self.draw()

    def select(self):
        PatchElement.select(self)
        self.draw()

    def unselect(self):
        PatchElement.unselect(self)
        self.draw()

    def delete(self):
        if (not self.dashed and self.obj_1 and self.obj_2 and 
            self.obj_1.obj_id is not None and self.obj_2.obj_id is not None):
            MFPGUI().mfp.disconnect(self.obj_1.obj_id, self.port_1, 
                                    self.obj_2.obj_id, self.port_2)
        if self.obj_1 and self in self.obj_1.connections_out:
            self.obj_1.connections_out.remove(self)
        if self.obj_2 and self in self.obj_2.connections_in:
            self.obj_2.connections_in.remove(self)

        self.obj_1 = None
        self.obj_2 = None
        PatchElement.delete(self)

    def draw_ports(self):
        pass 

    def corners(self):
        if self.obj_1 and self.obj_2:
            p1 = self.obj_1.port_center(PatchElement.PORT_OUT, self.port_1)
            p2 = self.obj_2.port_center(PatchElement.PORT_IN, self.port_2)
            return [p1, p2]
        else:
            return None

    def draw(self):
        if self.obj_1 is None or self.obj_2 is None:
            return

        p1 = self.obj_1.port_center(PatchElement.PORT_OUT, self.port_1)
        p2 = self.obj_2.port_center(PatchElement.PORT_IN, self.port_2)

        if self.dsp_connect == True:
            self.width = 2.5 * self.LINE_WIDTH
        else:
            self.width = 1.5 * self.LINE_WIDTH
        self.height = ((p2[0] - p1[0]) ** 2 + (p2[1] - p1[1]) ** 2) ** 0.5
        theta = math.atan2(p1[0] - p2[0], p2[1] - p1[1])
        self.rotation = theta * 180.0 / math.pi
        self.position_x = p1[0] - math.cos(theta) * self.width / 2.0
        self.position_y = p1[1] - math.sin(theta) * self.width / 2.0

        self.set_size(self.width, self.height)
        self.set_position(self.position_x, self.position_y)
        self.set_rotation(Clutter.RotateAxis.Z_AXIS, self.rotation, 0, 0, 0)

        self.texture.set_position(0, 0)
        self.texture.set_size(self.width, self.height)
        self.texture.set_surface_size(self.width, self.height)
        self.texture.invalidate()

    def draw_cb(self, texture, ctx):
        texture.clear()
        ctx.set_antialias(cairo.ANTIALIAS_NONE)

        c = ColorDB.to_cairo(self.get_color('stroke-color'))
        ctx.set_source_rgba(c.red, c.green, c.blue, c.alpha)
        if self.dsp_connect:
            ctx.set_line_width(2.0 * self.LINE_WIDTH)
        else:
            ctx.set_line_width(self.LINE_WIDTH)

        if self.dashed: 
            ctx.set_dash([8, 4])
        else:
            ctx.set_dash([])

        ctx.move_to(self.width / 2.0, 0)
        ctx.line_to(self.width / 2.0, self.height)
        ctx.stroke()
