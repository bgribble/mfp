#! /usr/bin/env python
'''
base_element.py
A patch element is the parent of all GUI entities backed by MFP objects

Copyright (c) 2011 Bill Gribble <grib@billgribble.com>
'''

from abc import ABCMeta, abstractmethod
from flopsy import Action, Store, mutates, reducer, saga
from mfp.gui_main import MFPGUI
from mfp import log
from .colordb import ColorDB, RGBAColor
from .backend_interfaces import BackendInterface
from .param_info import ParamInfo, ListOfInt, CodeBlock, DictOfProperty
from .layer import Layer


class BaseElementImpl(metaclass=ABCMeta):
    @abstractmethod
    async def delete(self, **kwargs):
        await super().delete(**kwargs)

    @abstractmethod
    def update_badge(self):
        pass

    @abstractmethod
    def draw_ports(self):
        pass

    @abstractmethod
    def hide_ports(self):
        pass

    @abstractmethod
    async def set_size(self, width, height, **kwargs):
        await super().set_size(width, height, **kwargs)

    @abstractmethod
    async def move(self, x, y, **kwargs):
        await super().move(x, y, **kwargs)

    @abstractmethod
    def move_z(self, z):
        pass

    @abstractmethod
    def move_to_top(self):
        pass


BASE_STORE_ATTRS = {
    'obj_id': ParamInfo(label="Object ID", param_type=int, editable=False),
    'obj_type': ParamInfo(label="Type", param_type=str),
    'obj_args': ParamInfo(label="Creation args", param_type=str),
    'display_type': ParamInfo(label="Display type", param_type=str, editable=False),
    'obj_name': ParamInfo(label="Name", param_type=str),
    'obj_state': ParamInfo(label="State", param_type=int, editable=False),
    'scope': ParamInfo(label="Lexical scope", param_type=str),
    'layer': ParamInfo(
        label="Layer",
        choices=lambda obj: [(l.name, l) for l in obj.layer.patch.layers],
        param_type=Layer
    ),
    'position_x': ParamInfo(label="X position", param_type=float),
    'position_y': ParamInfo(label="Y position", param_type=float),
    'position_z': ParamInfo(label="Z position", param_type=float),
    'width': ParamInfo(label="Width", param_type=float, editable=False),
    'height': ParamInfo(label="Height", param_type=float, editable=False),
    'min_width': ParamInfo(label="Min width", param_type=float),
    'min_height': ParamInfo(label="Min height", param_type=float),
    'update_required': ParamInfo(label="Update required", param_type=bool),
    'no_export': ParamInfo(label="No export", param_type=bool),
    'is_export': ParamInfo(label="Is export", param_type=bool),
    'num_inlets': ParamInfo(label="# inlets", param_type=int, editable=False),
    'num_outlets': ParamInfo(label="# outlets", param_type=int, editable=False),
    'dsp_inlets': ParamInfo(label="# outlets", param_type=ListOfInt, editable=False),
    'dsp_outlets': ParamInfo(label="# outlets", param_type=ListOfInt, editable=False),
    'style': ParamInfo(label="Style variables", param_type=dict),
    'export_offset_x': ParamInfo(label="Export offset X", param_type=float),
    'export_offset_y': ParamInfo(label="Export offset Y", param_type=float),
    'debug': ParamInfo(label="Enable debugging", param_type=bool),
    'code': ParamInfo(label="Custom code", param_type=CodeBlock, show=True),
    'properties': ParamInfo(label="Properties", param_type=DictOfProperty, show=True),
}

# these are params that may appear within 'properties' and get
# their own editors. It's awkward to have type-specific info here 
# and in the Processor definition but I can't see a way around it
PROPERTY_ATTRS = {
    'lv2_type': ParamInfo(
        label="(lv2) Port type",
        choices=lambda o: [('MIDI', 'midi'), ('Control', 'control')],
        param_type=str, show=True
    ),
    'lv2_description': ParamInfo(
        label="(lv2) Description", param_type=str, show=True
    ),
    'lv2_default_val': ParamInfo(
        label="(lv2) Default value [control ports]", param_type=float, show=True
    ),
    'lv2_minimum_val': ParamInfo(
        label="(lv2) Minimum value [control ports]", param_type=float, show=True
    ),
    'lv2_maximum_val': ParamInfo(
        label="(lv2) Maximum value [control ports]", param_type=float, show=True
    ),
}

class BaseElement (Store):
    '''
    Parent class of elements represented in the patch window
    '''
    store_attrs = BASE_STORE_ATTRS
    style_defaults = {
        'porthole-width': 8,
        'porthole-height': 4,
        'porthole-border': 1,
        'porthole-minspace': 14,
        'padding': dict(left=4, top=2, right=4, bottom=2),
        'badge-size': 15,
    }

    PORT_IN = 0
    PORT_OUT = 1

    OBJ_NONE = 0
    OBJ_HALFCREATED = 1
    OBJ_ERROR = 2
    OBJ_COMPLETE = 3
    OBJ_DELETED = 4
    TINY_DELTA = .0001

    last_id = 0

    def __init__(self, window, x, y):
        self.id = BaseElement.last_id + 1
        BaseElement.last_id = self.id

        # MFP object and UI descriptors
        self.obj_id = None
        self.parent_id = None
        self.obj_name = None
        self.obj_type = None
        self.obj_args = None
        self.obj_state = self.OBJ_COMPLETE
        self.scope = None
        self.num_inlets = 1
        self.num_outlets = 0
        self.dsp_inlets = []
        self.dsp_outlets = []
        self.dsp_context = ""
        self.connections_out = []
        self.connections_in = []
        self.is_export = False
        self.param_list = [a for a in self.store_attrs]
        self.code = None

        self.app_window = window

        # container is either a layer or another BaseElement (graph-on-parent)
        self.container = None

        # could be the same as self.container but is definitely a layer
        self.layer = None

        self.tags = {}

        # these can't be initialized until there's a backend
        BaseElement.style_defaults.update({
            'badge-edit-color': ColorDB().find('default-edit-badge-color'),
            'badge-learn-color': ColorDB().find('default-learn-badge-color'),
            'badge-error-color': ColorDB().find('default-error-badge-color')
        })

        # UI state
        self.position_x = x
        self.position_y = y
        self.position_z = 0
        self.export_offset_x = 0
        self.export_offset_y = 0
        self.min_width = 0
        self.min_height = 0
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
        self.properties = {}
        self.style = {}
        self._all_styles = self.combine_styles()

        # for interactive search
        self.highlight_text = None

        super().__init__(window, x, y)

    def __repr__(self):
        return "<%s %s>" % (type(self).__name__, id(self))

    @classmethod
    def build(cls, *args, **kwargs):
        backend = cls.get_backend(MFPGUI().backend_name)
        if not backend:
            log.error(f"[build] No '{MFPGUI().backend_name}' backend found for {cls}")
            raise ValueError
        return backend(*args, **kwargs)

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

    async def set_size(self, width, height, **kwargs):
        update_state = kwargs.get("update_state", True)
        prev_width = kwargs.get('previous_width', self.width)
        prev_height = kwargs.get('previous_height', self.height)
        changed_w = not self.width or abs(width - self.width) > BaseElement.TINY_DELTA
        changed_h = not self.height or abs(height - self.height) > BaseElement.TINY_DELTA

        if self.width and self.height and not changed_w and not changed_h:
            return

        width = max(width, self.min_width)
        height = max(height, self.min_height)

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

    def get_style(self, propname, default=None):
        return self._all_styles.get(propname, default)

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
        if isinstance(rgba, str):
            return ColorDB().find(rgba)
        if isinstance(rgba, (list, tuple)):
            return ColorDB().find(rgba[0], rgba[1], rgba[2], rgba[3])
        return rgba

    def combine_styles(self):
        styles = {}
        styles.update(
            MFPGUI().style_defaults
        )
        for base_type in reversed(type(self).mro()):
            if hasattr(base_type, 'style_defaults'):
                styles.update(base_type.style_defaults)
        styles.update(self.style)
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
        if "drag" not in self.app_window.motion_overrides:
            await self.move(self.position_x + dx, self.position_y + dy, update_state=False)

    async def move(self, x, y, **kwargs):
        update_state = kwargs.get("update_state", True)
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

    @saga('code', 'properties')
    async def params_changed(self, action, state_diff, previous):
        yield self.send_params()

    @mutates('obj_state')
    async def delete(self, delete_obj=True):
        # FIXME this is because self.app_window is the backend, not the app window
        MFPGUI().appwin.unregister(self)
        if delete_obj and self.obj_id is not None and not self.is_export:
            await MFPGUI().mfp.delete(self.obj_id)

        for conn in [c for c in self.connections_out]:
            await conn.delete(delete_obj=delete_obj)
        for conn in [c for c in self.connections_in]:
            await conn.delete(delete_obj=delete_obj)

        self.obj_id = None
        self.obj_state = self.OBJ_DELETED

    @reducer('layer')
    def SET_LAYER(self, action, state, previous):
        new_layer = action.payload['value']
        self.move_to_layer(new_layer)
        return new_layer

    @saga('style')
    async def update_all_styles(self, action, state_diff, previous):
        self._all_styles = self.combine_styles()
        yield None

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

        self.obj_type = obj_type
        self.obj_args = init_args

        self.tags = {}
        self.update_badge()
        objinfo = await MFPGUI().mfp.create(obj_type, init_args, patchname, scopename, name, self.synced_params())
        if not objinfo or "obj_id" not in objinfo:
            self.app_window.hud_write("ERROR: Could not create, see log for details")

            if objinfo and "code" in objinfo:
                self.code = objinfo["code"]

            self.connections_out = connections_out
            self.connections_in = connections_in
            self.tags['errorcount'] = 1
            self.update_badge()
            return None

        if self.layer is not None and objinfo and isinstance(objinfo, dict):
            objinfo["layername"] = self.layer.name
        objinfo['obj_type'] = obj_type

        # init state from objinfo
        await self.dispatch(
            Action(self, self.CREATE_OBJECT, objinfo)
        )

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

    @reducer(
        'obj_id', 'scope', 'num_inlets', 'num_outlets', 'dsp_inlets', 'dsp_outlets',
        'obj_type', 'obj_name', 'obj_args', 'properties'
    )
    def CREATE_OBJECT(self, action, state, previous_value):
        """
        Initialize store from creation payload
        """
        objinfo = action.payload
        if state in (
            'obj_id', 'obj_type', 'scope', 'num_inlets', 'num_outlets', 'dsp_inlets', 'dsp_outlets',
            'properties'
        ):
            return objinfo.get(state, previous_value)

        if state == 'obj_name':
            return objinfo.get('name', previous_value)
        if state == 'obj_args':
            return objinfo.get('initargs', previous_value)
        return previous_value

    def synced_params(self):
        prms = {}
        for k in self.param_list:
            val = getattr(self, k)
            if k == "layer":
                prms["layername"] = val.name
                continue
            if isinstance(val, BaseElement):
                val = val.obj_id
            prms[k] = val

        outbound = []
        for c in self.connections_out:
            outbound.append(c.synced_params())
        prms["connection_info"] = outbound

        return prms

    def send_params(self, **extras):
        if self.obj_id is None:
            return

        prms = self.synced_params()
        for k, v in extras.items():
            prms[k] = v

        MFPGUI().async_task(
            MFPGUI().mfp.set_params(self.obj_id, prms)
        )

    def get_stage_position(self):
        if not self.container or not self.layer or self.container == self.layer:
            return (self.position_x, self.position_y)

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

        return (pos_x + ppos[0], pos_y + ppos[1])

    def port_size(self):
        return (self.get_style('porthole-width'), self.get_style('porthole-height'))

    def port_position(self, port_dir, port_num):
        """
        port_position returns the (x,y) position of the center of the
        porthole, on the object bounding box. If the rendered box is
        offset from that position, that can be handled in the renderer.
        """
        w = self.width
        h = self.height
        port_width = self.get_style('porthole-width')
        # inlet
        if port_dir == BaseElement.PORT_IN:
            if self.num_inlets < 2:
                spc = 0
            else:
                spc = max(self.get_style('porthole-minspace'),
                          ((w
                            - port_width
                            - 2.0 * self.get_style('porthole-border'))
                           / (self.num_inlets - 1.0)))
            return (self.get_style('porthole-border') + spc * port_num + port_width / 2.0, 0)

        # outlet
        if self.num_outlets < 2:
            spc = 0
        else:
            spc = max(self.get_style('porthole-minspace'),
                      ((w - port_width
                        - 2.0 * self.get_style('porthole-border'))
                       / (self.num_outlets - 1.0)))
        return (self.get_style('porthole-border') + spc * port_num + port_width / 2.0, h)

    def port_alloc(self):
        space = self.get_style('porthole-minspace')
        border = self.get_style('porthole-border')
        return (max(self.num_inlets, self.num_outlets) - 1) * space + 2*border

    @mutates(
        'num_inlets', 'num_outlets', 'dsp_inlets', 'dsp_outlets',
        'obj_name', 'no_export', 'is_export', 'export_offset_x',
        'export_offset_y', 'debug', 'layer', 'code', 'properties'
    )
    async def configure(self, params):
        self.num_inlets = params.get("num_inlets", 0)
        self.num_outlets = params.get("num_outlets", 0)
        self.dsp_inlets = params.get("dsp_inlets", [])
        self.dsp_outlets = params.get("dsp_outlets", [])
        self.obj_name = params.get("name") or params.get("obj_name")
        self.no_export = params.get("no_export", False)
        self.is_export = params.get("is_export", False)
        self.export_offset_x = params.get("export_offset_x", 0)
        self.export_offset_y = params.get("export_offset_y", 0)
        self.debug = params.get("debug", False)
        self.code = params.get("code", None)
        self.properties = params.get("properties", {})

        newscope = params.get("scope", "__patch__")
        if (not self.scope) or newscope != self.scope:
            self.scope = newscope

        if params.get("tags") is not None and self.tags != params.get("tags"):
            self.tags = params.get("tags")
            self.update_badge()

        layer_name = params.get("layername") or params.get("layer")

        mypatch = (
            (self.layer and self.layer.patch)
            or (self.app_window and self.app_window.selected_patch)
        )
        layer = None
        if mypatch:
            layer = mypatch.find_layer(layer_name)

        if layer and self.layer != layer:
            self.move_to_layer(layer)

        if 'style' in params:
            self.style.update(params.get('style'))

        self._all_styles = self.combine_styles()

        self.min_width = params.get('min_width', self.min_width)
        self.min_height = params.get('min_height', self.min_height)

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

    @mutates('layer')
    def move_to_layer(self, layer):
        layer_child = False
        if layer and layer == self.layer:
            return

        if self.layer:
            if self.container == self.layer:
                self.container = None
                layer_child = True
            #elif self.get_parent() is None:
            #    layer_child = True
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
        # should be overridden
        return None

    async def begin_edit(self):
        if not self.editable:
            return False

        if not self.edit_mode:
            self.edit_mode = await self.make_edit_mode()
            if self.edit_mode:
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

    async def get_help_patch(self):
        info = await MFPGUI().mfp.get_tooltip_info(self.obj_id)
        return info.get("help_patch", self.help_patch)

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
                h += 4
                if direction == self.PORT_IN:
                    y -= h-2
                if (xpos >= x-1) and (xpos <= x+w) and (ypos >= y) and (ypos <= y+h):
                    tiptxt = await MFPGUI().mfp.get_tooltip(self.obj_id, direction, port_num, details)

        if tiptxt is None:
            tiptxt = await MFPGUI().mfp.get_tooltip(self.obj_id, None, None, details)
        self.app_window.hud_banner(tiptxt)
        return True

    def command(self, action, args):
        pass
