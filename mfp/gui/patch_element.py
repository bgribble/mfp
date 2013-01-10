#! /usr/bin/env python
'''
patch_element.py
A patch element is the parent of all GUI entities backed by MFP objects

Copyright (c) 2011 Bill Gribble <grib@billgribble.com>
'''

from gi.repository import Clutter
from mfp import MFPGUI
from mfp import log


class PatchElement (Clutter.Group):
    '''
    Parent class of elements represented in the patch window
    '''
    PORT_IN = 0
    PORT_OUT = 1
    porthole_width = 8
    porthole_height = 4
    porthole_border = 1
    porthole_minspace = 11

    OBJ_NONE = 0
    OBJ_HALFCREATED = 1
    OBJ_ERROR = 2
    OBJ_COMPLETE = 3

    def __init__(self, window, x, y):
        # MFP object and UI descriptors
        self.obj_id = None
        self.obj_name = None
        self.obj_type = None
        self.obj_args = None
        self.obj_state = self.OBJ_COMPLETE
        self.num_inlets = 0
        self.num_outlets = 0
        self.dsp_inlets = []
        self.dsp_outlets = []
        self.connections_out = []
        self.connections_in = []
        self.param_list = ['position_x', 'position_y', 'update_required', 
                           'display_type', 'name', 'layername', 'num_inlets', 
                           'num_outlets', 'dsp_inlets', 'dsp_outlets' ]
            
        # Clutter objects
        self.stage = window
        self.layer = None
        self.port_elements = {}

        # UI state
        self.position_x = x
        self.position_y = y
        self.drag_x = None
        self.drag_y = None
        self.selected = False
        self.update_required = False
        self.edit_mode = None
        self.control_mode = None

        # create placeholder group and add to stage
        Clutter.Group.__init__(self)
        self.stage.register(self)

    @property
    def layername(self):
        return self.layer.name 

    @property
    def name(self):
        return self.obj_name 

    def update(self):
        pass

    def event_source(self):
        return self

    def move_to_top(self):
        p = self.get_parent()
        if not p: 
            return 

        def bump(actor):
            p.remove_actor(actor)
            p.add_actor(actor)

        bump(self)
        for c in self.connections_out + self.connections_in:
            bump(c)

    def drag_start(self, x, y):
        self.drag_x = x - self.position_x
        self.drag_y = y - self.position_y

    def move(self, x, y):
        self.position_x = x
        self.position_y = y
        self.set_position(x, y)

        for c in self.connections_out:
            c.draw()

        for c in self.connections_in:
            c.draw()

    def drag(self, dx, dy):
        self.move(self.position_x + dx, self.position_y + dy)

    def delete(self):
        self.stage.unregister(self)
        if self.obj_id is not None:
            MFPGUI().mfp.delete(self.obj_id)
            self.obj_id = None

    def create(self, obj_type, init_args):
        scopename = self.layer.scope
        connections_out = []
        connections_in = [] 

        if self.obj_name is not None:
            name = self.obj_name
        else:
            name_index = self.stage.object_counts_by_type.get(self.display_type, 0)
            name = "%s_%s" % (self.display_type, name_index)

        if self.obj_id is not None:
            connections_out = self.connections_out
            self.connections_out = [] 
            connections_in = self.connections_in
            self.connections_in = []
            MFPGUI().mfp.delete(self.obj_id)
            self.obj_id = None 

        objinfo = MFPGUI().mfp.create(obj_type, init_args, "default", scopename, name)
        if objinfo is None:
            self.stage.hud_write("ERROR: Could not create, see log for details")
            return None

        self.obj_id = objinfo.get('obj_id')
        self.obj_name = objinfo.get('name')
        self.obj_args = objinfo.get('initargs')
        self.num_inlets = objinfo.get("num_inlets")
        self.num_outlets = objinfo.get("num_outlets")
        self.dsp_inlets = objinfo.get("dsp_inlets")
        self.dsp_outlets = objinfo.get("dsp_outlets")

        if self.obj_id is not None:
            # rebuild connections if necessary 
            for c in connections_in:
                if c.obj_2 is self and c.port_2 >= self.num_inlets:
                    c.obj_2 = None 
                    c.delete()
                else: 
                    self.connections_in.append(c)
                    MFPGUI().mfp.connect(c.obj_1.obj_id, c.port_1, c.obj_2.obj_id, c.port_2)

            for c in connections_out:
                if c.obj_1 is self and c.port_1 >= self.num_outlets:
                    c.obj_1 = None 
                    c.delete()
                else: 
                    self.connections_out.append(c)
                    MFPGUI().mfp.connect(c.obj_1.obj_id, c.port_1, c.obj_2.obj_id, c.port_2)

            MFPGUI().remember(self)
            self.send_params()
            MFPGUI().mfp.set_gui_created(self.obj_id, True)

        self.stage.refresh(self)
        return self.obj_id

    def send_params(self, **extras):
        if self.obj_id is None:
            return
        prms = {} 
        for k in self.param_list:
            prms[k] = getattr(self, k)

        for k, v in extras.items():
            prms[k] = v
        MFPGUI().mfp.set_params(self.obj_id, prms)

    def get_params(self):
        return MFPGUI().mfp.get_params(self.obj_id)

    def port_center(self, port_dir, port_num):
        ppos = self.port_position(port_dir, port_num)
        return (self.position_x + ppos[0] + 0.5 * self.porthole_width,
                self.position_y + ppos[1] + 0.5 * self.porthole_height)

    def port_position(self, port_dir, port_num):
        w = self.get_width()
        h = self.get_height()

        if port_dir == PatchElement.PORT_IN:
            if self.num_inlets < 2:
                spc = 0
            else:
                spc = max(self.porthole_minspace,
                         (w - self.porthole_width - 2.0 * self.porthole_border) / (self.num_inlets - 1.0))
            return (self.porthole_border + spc * port_num, 0)

        elif port_dir == PatchElement.PORT_OUT:
            if self.num_outlets < 2:
                spc = 0
            else:
                spc = max(self.porthole_minspace,
                         (w - self.porthole_width - 2.0 * self.porthole_border) / (self.num_outlets - 1.0))
            return (self.porthole_border + spc * port_num, h - self.porthole_height)

    def draw_ports(self):
        ports_done = [] 
        def confport(pid, px, py):
            pobj = self.port_elements.get(pid)
            if pobj is None:
                pobj = Clutter.Rectangle()
                pobj.set_color(self.stage.color_unselected)
                pobj.set_size(self.porthole_width, self.porthole_height)
                self.add_actor(pobj)
                self.port_elements[pid] = pobj
            pobj.set_position(px, py)
            pobj.show()
            ports_done.append(pobj)

        for i in range(self.num_inlets):
            x, y = self.port_position(PatchElement.PORT_IN, i)
            pid = (PatchElement.PORT_IN, i)
            confport(pid, x, y)

        for i in range(self.num_outlets):
            x, y = self.port_position(PatchElement.PORT_OUT, i)
            pid = (PatchElement.PORT_OUT, i)
            confport(pid, x, y)

        # clean up -- ports may need to be deleted if 
        # the object resizes smaller 
        for pid, port in self.port_elements.items():
            if port not in ports_done:
                del self.port_elements[pid]
                self.remove_actor(port)

        # redraw connections 
        for c in self.connections_out:
            c.draw()

        for c in self.connections_in:
            c.draw()

    def hide_ports(self):
        def hideport(pid):
            pobj = self.port_elements.get(pid)
            if pobj:
                pobj.hide()

        for i in range(self.num_inlets):
            pid = (PatchElement.PORT_IN, i)
            hideport(pid)

        for i in range(self.num_outlets):
            pid = (PatchElement.PORT_OUT, i)
            hideport(pid)

    def command(self, action, data):
        pass

    def configure(self, params):
        self.num_inlets = params.get("num_inlets")
        self.num_outlets = params.get("num_outlets")
        self.dsp_inlets = params.get("dsp_inlets")
        self.dsp_outlets = params.get("dsp_outlets")
        self.obj_name = params.get("name")
        layer_name = params.get("layername") or params.get("layer")
        layer = self.stage.selected_patch.find_layer(layer_name)

        if layer and self.layer != layer:
            self.move_to_layer(layer)

        self.draw_ports()
        self.stage.refresh(self)

    def move_to_layer(self, layer):
        if self.layer:
            self.layer.group.remove_actor(self)
            self.layer.remove(self)
        layer.add(self)
        self.layer.group.add_actor(self)

    def make_edit_mode(self):
        return None

    def make_control_mode(self):
        return None

    def begin_edit(self):
        if not self.edit_mode:
            self.edit_mode = self.make_edit_mode()

        if self.edit_mode:
            self.stage.input_mgr.enable_minor_mode(self.edit_mode)

    def end_edit(self):
        if self.edit_mode:
            self.stage.input_mgr.disable_minor_mode(self.edit_mode)
            self.edit_mode = None
            self.stage.refresh(self)

    def begin_control(self):
        if not self.control_mode:
            self.control_mode = self.make_control_mode()

        if self.control_mode:
            self.stage.input_mgr.enable_minor_mode(self.control_mode)

    def end_control(self):
        if self.control_mode:
            self.stage.input_mgr.disable_minor_mode(self.control_mode)
            self.control_mode = None
