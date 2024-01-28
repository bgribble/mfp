#! /usr/bin/env python
'''
base_element.py
A patch element is the parent of all GUI entities backed by MFP objects

Copyright (c) 2011 Bill Gribble <grib@billgribble.com>
'''

from flopsy import Store, mutates
from mfp.gui_main import MFPGUI
from mfp import log
from .colordb import ColorDB


class BaseElement (Store):
    '''
    Parent class of elements represented in the patch window
    '''
    store_attrs = [
        'position_x', 'position_y', 'position_z', 'width', 'height',
        'update_required', 'display_type', 'name', 'layername',
        'no_export', 'is_export', 'num_inlets', 'num_outlets', 'dsp_inlets',
        'dsp_outlets', 'scope', 'style', 'export_offset_x',
        'export_offset_y', 'debug', 'obj_name', 'obj_state'
    ]

    style_defaults = {
        'porthole_width': 8,
        'porthole_height': 4,
        'porthole_border': 1,
        'porthole_minspace': 11,
        'badge_size': 15,
        'badge-edit-color': 'default-edit-badge-color',
        'badge-learn-color': 'default-learn-badge-color',
        'badge-error-color': 'default-error-badge-color'
    }

    PORT_IN = 0
    PORT_OUT = 1

    OBJ_NONE = 0
    OBJ_HALFCREATED = 1
    OBJ_ERROR = 2
    OBJ_COMPLETE = 3
    OBJ_DELETED = 4
    TINY_DELTA = .0001

    def __init__(self, window, x, y):
        self.id = None

        # MFP object and UI descriptors
        self.obj_id = None
        self.parent_id = None
        self.obj_name = None
        self.obj_type = None
        self.obj_args = None
        self.obj_state = self.OBJ_COMPLETE
        self.scope = None
        self.num_inlets = 0
        self.num_outlets = 0
        self.dsp_inlets = []
        self.dsp_outlets = []
        self.dsp_context = ""
        self.connections_out = []
        self.connections_in = []
        self.is_export = False
        self.param_list = [a for a in self.store_attrs]

        self.app_window = window

        # container is either a layer or another BaseElement (graph-on-parent)
        self.container = None

        # could be the same as self.container but is definitely a layer
        self.layer = None
        self.layername = None

        self.tags = {}

        # UI state
        self.position_x = x
        self.position_y = y
        self.position_z = 0
        self.export_offset_x = 0
        self.export_offset_y = 0
        self.width = None
        self.height = None
        self.drag_start_x = None
        self.drag_start_y = None
        self.selected = False
        self.editable = True
        self.debug = False
        self.update_required = False
        self.no_export = False
        self.edit_mode = None
        self.control_mode = None
        self.style = {}
        self._all_styles = self.combine_styles()

        super().__init__()

    def __repr__(self):
        return "<%s %s>" % (type(self).__name__, id(self))

    @classmethod
    def get_factory(cls):
        return cls

    @classmethod
    def build(cls, *args, **kwargs):
        return cls.get_factory()(*args, **kwargs)

    def corners(self):
        return [(self.position_x, self.position_y),
                (self.position_x + self.width, self.position_y),
                (self.position_x + self.width, self.position_y + self.height),
                (self.position_x, self.position_y + self.height)]

    @property
    def name(self):
        return self.obj_name

    def get_size(self):
        return (self.width, self.height)

    async def set_size(self, width, height, update_state=True, **kwargs):
        prev_width = kwargs.get('width', self.width)
        prev_height = kwargs.get('height', self.height)
        changed_w = not self.width or abs(width - self.width) > BaseElement.TINY_DELTA
        changed_h = not self.height or abs(height - self.height) > BaseElement.TINY_DELTA

        if self.width and self.height and not changed_w and not changed_h:
            return

        if update_state:
            if changed_w:
                await self.dispatch(
                    self.action(
                        self.SET_WIDTH,
                        value=width,
                    ),
                    previous=dict(width=prev_width)
                )
            if changed_h:
                await self.dispatch(
                    self.action(
                        self.SET_HEIGHT,
                        value=height,
                    ),
                    previous=dict(height=prev_height)
                )
        else:
            self.width = width
            self.height = height

        self.draw_ports()
        self.send_params()

    def description(self):
        return self.obj_name

    def get_style(self, propname):
        return self._all_styles.get(propname)

    def get_position(self):
        return (self.position_x, self.position_y)

    def get_fontspec(self):
        return '{} {}px'.format(self.get_style('font-face'), self.get_style('font-size'))

    def get_color(self, colorspec):
        rgba = None
        if self.debug:
            rgba = self.get_style(colorspec + ':debug')
        elif self.selected:
            rgba = self.get_style(colorspec + ':selected')
        if not rgba:
            rgba = self.get_style(colorspec)
        if not rgba:
            rgba = self.get_style(colorspec.split(':')[0])

        if not rgba:
            log.error('Could not find color %s in %s' % (colorspec, self._all_styles))
            return ColorDB().find(64, 64, 64, 255)
        elif isinstance(rgba, str):
            return ColorDB().find(rgba)
        else:
            return ColorDB().find(rgba[0], rgba[1], rgba[2], rgba[3])

    def combine_styles(self):
        styles = {}
        for styleset in (
            MFPGUI().style_defaults,
            BaseElement.style_defaults,
            type(self).style_defaults,
            self.style
        ):
            styles.update(styleset)
        return styles

    async def update(self):
        pass

    def event_source(self):
        return self

    def select(self):
        self.selected = True
        self.move_to_top()
        self.draw_ports()

    def unselect(self):
        self.selected = False
        self.draw_ports()

    def drag_start(self):
        self.drag_start_x = self.position_x
        self.drag_start_y = self.position_y

    async def drag_end(self):
        await self.move(
            self.position_x,
            self.position_y,
            update_state=True,
            previous_x=self.drag_start_x,
            previous_y=self.drag_start_y
        )

    async def drag(self, dx, dy):
        await self.move(self.position_x + dx, self.position_y + dy, update_state=False)

    async def move(self, x, y, update_state=True, **kwargs):
        previous_x = kwargs.get('previous_x', self.position_x)
        previous_y = kwargs.get('previous_y', self.position_y)

        if update_state:
            if previous_x is None or abs(x - previous_x) > self.TINY_DELTA:
                await self.dispatch(
                    self.action(
                        self.SET_POSITION_X,
                        value=x,
                    ),
                    previous=dict(position_x=previous_x)
                )
            if previous_y is None or abs(y - previous_y) > self.TINY_DELTA:
                await self.dispatch(
                    self.action(
                        self.SET_POSITION_Y,
                        value=y,
                    ),
                    previous=dict(position_y=previous_y)
                )
        else:
            self.position_x = x
            self.position_y = y

    @mutates('obj_state')
    async def delete(self):
        # FIXME this is because self.app_window is the backend, not the app window
        MFPGUI().appwin.unregister(self)
        if self.obj_id is not None and not self.is_export:
            await MFPGUI().mfp.delete(self.obj_id)

        for conn in [c for c in self.connections_out]:
            await conn.delete()
        for conn in [c for c in self.connections_in]:
            await conn.delete()

        self.obj_id = None
        self.obj_state = self.OBJ_DELETED

    async def create(self, obj_type, init_args):
        scopename = self.layer.scope
        patchname = self.layer.patch.obj_name
        connections_out = self.connections_out
        connections_in = self.connections_in
        self.connections_out = []
        self.connections_in = []

        # FIXME: optional name-root argument?  Need to pass the number at all,
        # with the scope handling it?
        if self.obj_name is not None:
            name = self.obj_name
        else:
            name_index = self.app_window.object_counts_by_type.get(self.display_type, 0)
            name = "%s_%03d" % (self.display_type, name_index)

        if self.obj_id is not None:
            await MFPGUI().mfp.set_gui_created(self.obj_id, False)
            await MFPGUI().mfp.delete(self.obj_id)
            self.obj_id = None

        # need to emit this signal before creating so that if
        # create() makes sub-objects with visible elements they
        # get put in the correct place in the object tree
        await MFPGUI().appwin.signal_emit("created", self)

        objinfo = await MFPGUI().mfp.create(obj_type, init_args, patchname, scopename, name)
        if self.layer is not None and objinfo:
            objinfo["layername"] = self.layer.name

        if objinfo is None:
            self.app_window.hud_write("ERROR: Could not create, see log for details")
            self.connections_out = connections_out
            self.connections_in = connections_in
            return None

        # FIXME flopsy
        self.obj_id = objinfo.get('obj_id')
        self.obj_name = objinfo.get('name')
        self.obj_args = objinfo.get('initargs')
        self.obj_type = obj_type
        self.scope = objinfo.get('scope')
        self.num_inlets = objinfo.get("num_inlets")
        self.num_outlets = objinfo.get("num_outlets")
        self.dsp_inlets = objinfo.get("dsp_inlets", [])
        self.dsp_outlets = objinfo.get("dsp_outlets", [])

        if self.obj_id is not None:
            MFPGUI().remember(self)
            await self.configure(objinfo)

            # rebuild connections if necessary
            for c in connections_in:
                if c.obj_2 is self and c.port_2 >= self.num_inlets:
                    c.obj_2 = None
                    await c.delete()
                elif c.obj_1 is None or c.obj_2 is None:
                    await c.delete()
                else:
                    self.connections_in.append(c)
                    if not c.dashed:
                        await MFPGUI().mfp.connect(
                            c.obj_1.obj_id, c.port_1, c.obj_2.obj_id, c.port_2
                        )

            for c in connections_out:
                if c.obj_1 is self and c.port_1 >= self.num_outlets:
                    c.obj_1 = None
                    await c.delete()
                elif c.obj_1 is None or c.obj_2 is None:
                    await c.delete()
                else:
                    self.connections_out.append(c)
                    if not c.dashed:
                        await MFPGUI().mfp.connect(
                            c.obj_1.obj_id, c.port_1, c.obj_2.obj_id, c.port_2
                        )
            self.draw_ports()
            self.send_params()

            await MFPGUI().mfp.set_gui_created(self.obj_id, True)

        self.app_window.refresh(self)

        return self.obj_id

    def synced_params(self):
        prms = {}
        for k in self.param_list:
            prms[k] = getattr(self, k)
        return prms

    def send_params(self, **extras):
        if self.obj_id is None:
            return

        prms = self.synced_params()
        for k, v in extras.items():
            prms[k] = v

        MFPGUI().mfp.set_params.task(
            self.obj_id, prms
        )

    def get_stage_position(self):
        if not self.container or not self.layer or self.container == self.layer:
            return (self.position_x, self.position_y)
        else:
            pos_x = self.position_x
            pos_y = self.position_y

            c = self.container
            while isinstance(c, BaseElement):
                pos_x += c.position_x
                pos_y += c.position_y
                c = c.container

            return (pos_x, pos_y)

    def port_center(self, port_dir, port_num):
        ppos = self.port_position(port_dir, port_num)
        pos_x, pos_y = self.get_stage_position()

        return (pos_x + ppos[0] + 0.5 * self.get_style('porthole_width'),
                pos_y + ppos[1] + 0.5 * self.get_style('porthole_height'))

    def port_size(self):
        return (self.get_style('porthole_width'), self.get_style('porthole_height'))

    def port_position(self, port_dir, port_num):
        w = self.width
        h = self.height

        # inlet
        if port_dir == BaseElement.PORT_IN:
            if self.num_inlets < 2:
                spc = 0
            else:
                spc = max(self.get_style('porthole_minspace'),
                          ((w - self.get_style('porthole_width')
                            - 2.0 * self.get_style('porthole_border'))
                           / (self.num_inlets - 1.0)))
            return (self.get_style('porthole_border') + spc * port_num, 0)

        # outlet
        if self.num_outlets < 2:
            spc = 0
        else:
            spc = max(self.get_style('porthole_minspace'),
                      ((w - self.get_style('porthole_width')
                        - 2.0 * self.get_style('porthole_border'))
                       / (self.num_outlets - 1.0)))
        return (self.get_style('porthole_border') + spc * port_num,
                h - self.get_style('porthole_height'))

    @mutates(
        'num_inlets', 'num_outlets', 'dsp_inlets', 'dsp_outlets',
        'obj_name', 'no_export', 'is_export', 'export_offset_x',
        'export_offset_y', 'debug', 'layername'
    )
    async def configure(self, params):
        self.num_inlets = params.get("num_inlets", 0)
        self.num_outlets = params.get("num_outlets", 0)
        self.dsp_inlets = params.get("dsp_inlets", [])
        self.dsp_outlets = params.get("dsp_outlets", [])
        self.obj_name = params.get("name")
        self.no_export = params.get("no_export", False)
        self.is_export = params.get("is_export", False)
        self.export_offset_x = params.get("export_offset_x", 0)
        self.export_offset_y = params.get("export_offset_y", 0)
        self.debug = params.get("debug", False)

        newscope = params.get("scope", "__patch__")
        if (not self.scope) or newscope != self.scope:
            self.scope = newscope

        if params.get("tags") is not None and self.tags != params.get("tags"):
            self.tags = params.get("tags")
            self.update_badge()

        layer_name = params.get("layername") or params.get("layer")

        mypatch = ((self.layer and self.layer.patch)
                   or (self.app_window and self.app_window.selected_patch))
        layer = None
        if mypatch:
            layer = mypatch.find_layer(layer_name)

        if layer and self.layer != layer:
            self.move_to_layer(layer)

        if 'style' in params:
            self.style.update(params.get('style'))

        self._all_styles = self.combine_styles()

        w_orig, h_orig = self.get_size()

        w = params.get("width") or w_orig
        h = params.get("height") or h_orig

        if "position_x" in params and "position_y" in params:
            xpos = params['position_x']
            ypos = params['position_y']

            await self.move(xpos, ypos)

        if "z_index" in params:
            self.move_z(params.get("z_index"))

        if (w != w_orig) or (h != h_orig):
            await self.set_size(w, h)

        self.draw_ports()
        self.app_window.refresh(self)

    @mutates('layername')
    def move_to_layer(self, layer):
        layer_child = False
        if layer and layer == self.layer:
            return
        elif self.layer:
            if self.container == self.layer:
                self.container = None
                layer_child = True
            elif self.get_parent() is None:
                layer_child = True
            self.layer.remove(self)
        else:
            layer_child = True

        layer.add(self)
        if layer_child:
            self.container = self.layer
        self.send_params()

        for c in self.connections_out + self.connections_in:
            c.move_to_layer(layer)

    async def make_edit_mode(self):
        return None

    def make_control_mode(self):
        return None

    async def begin_edit(self):
        if not self.editable:
            return False

        if not self.edit_mode:
            self.edit_mode = await self.make_edit_mode()
            await self.edit_mode.setup()

        if self.edit_mode:
            self.app_window.input_mgr.enable_minor_mode(self.edit_mode)
        self.update_badge()

    async def end_edit(self):
        if self.edit_mode:
            self.app_window.input_mgr.disable_minor_mode(self.edit_mode)
            self.edit_mode = None
            self.app_window.refresh(self)
        self.update_badge()

    def begin_control(self):
        if not self.control_mode:
            self.control_mode = self.make_control_mode()

        if self.control_mode:
            self.app_window.input_mgr.enable_minor_mode(self.control_mode)

    def end_control(self):
        if self.control_mode:
            self.app_window.input_mgr.disable_minor_mode(self.control_mode)
            self.control_mode = None

    async def show_tip(self, xpos, ypos, details):
        tiptxt = None
        orig_x, orig_y = self.get_stage_position()

        if self.obj_id is None:
            return False

        for direction, num_ports in [(self.PORT_IN, self.num_inlets), (self.PORT_OUT, self.num_outlets)]:
            for port_num in range(num_ports):
                x, y = self.port_position(direction, port_num)
                x += orig_x - 1
                y += orig_y - 1
                w, h = self.port_size()
                w += 2
                h += 2
                if (xpos >= x) and (xpos <= x+w) and (ypos >= y) and (ypos <= y+h):
                    tiptxt = await MFPGUI().mfp.get_tooltip(self.obj_id, direction, port_num, details)

        if tiptxt is None:
            tiptxt = await MFPGUI().mfp.get_tooltip(self.obj_id, None, None, details)
        self.app_window.hud_banner(tiptxt)
        return True
