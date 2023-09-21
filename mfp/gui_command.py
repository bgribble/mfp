from carp.service import apiclass, noresp

@apiclass
class GUICommand:
    def ready(self):
        from .gui_main import MFPGUI
        if MFPGUI().appwin is not None and MFPGUI().appwin.ready():
            return True
        else:
            return False

    @noresp
    def log_write(self, msg, level):
        from .gui_main import MFPGUI
        window = MFPGUI().appwin
        if window:
            MFPGUI().appwin.log_write(msg, level)
        else:
            print(msg)

    def console_set_prompt(self, prompt):
        from .gui_main import MFPGUI
        MFPGUI().appwin.console_mgr.ps1 = prompt
        return True

    def console_show_prompt(self, prompt):
        from .gui_main import MFPGUI
        MFPGUI().appwin.console_show_prompt(prompt)
        return True

    def console_write(self, msg):
        from .gui_main import MFPGUI
        MFPGUI().appwin.console_write(msg)

    def hud_write(self, msg):
        from .gui_main import MFPGUI
        MFPGUI().appwin.hud_write(msg)

    def finish(self):
        from .gui_main import MFPGUI
        MFPGUI().finish()

    def command(self, obj_id, action, args):
        from .gui_main import MFPGUI
        obj = MFPGUI().recall(obj_id)
        obj.command(action, args)

    def configure(self, obj_id, params=None, **kwparams):
        from .gui_main import MFPGUI
        obj = MFPGUI().recall(obj_id)
        if params is not None:
            obj.configure(params)
        else:
            prms = obj.synced_params()
            for k, v in kwparams.items():
                prms[k] = v
            obj.configure(prms)

    def create(self, obj_type, obj_args, obj_id, parent_id, params):
        from .gui_main import MFPGUI
        from .gui.patch_element import PatchElement
        from .gui.processor_element import ProcessorElement
        from .gui.message_element import MessageElement
        from .gui.text_element import TextElement
        from .gui.enum_element import EnumElement
        from .gui.plot_element import PlotElement
        from .gui.slidemeter_element import SlideMeterElement, DialElement
        from .gui.patch_info import PatchInfo
        from .gui.via_element import SendViaElement, ReceiveViaElement
        from .gui.via_element import SendSignalViaElement, ReceiveSignalViaElement
        from .gui.button_element import ToggleButtonElement
        from .gui.button_element import ToggleIndicatorElement
        from .gui.button_element import BangButtonElement
        from mfp import log

        elementtype = params.get('display_type', 'processor')

        ctors = {
            'processor': ProcessorElement,
            'message': MessageElement,
            'text': TextElement,
            'enum': EnumElement,
            'plot': PlotElement,
            'slidemeter': SlideMeterElement,
            'dial': DialElement,
            'patch': PatchInfo,
            'sendvia': SendViaElement,
            'recvvia': ReceiveViaElement,
            'sendsignalvia': SendSignalViaElement,
            'recvsignalvia': ReceiveSignalViaElement,
            'toggle': ToggleButtonElement,
            'button': BangButtonElement,
            'indicator': ToggleIndicatorElement
        }
        ctor = ctors.get(elementtype, ProcessorElement)
        if ctor:
            o = ctor(MFPGUI().appwin.backend, params.get('position_x', 0), params.get('position_y', 0))
            o.obj_id = obj_id
            o.parent_id = parent_id
            o.obj_type = obj_type
            o.obj_args = obj_args
            o.obj_state = PatchElement.OBJ_COMPLETE

            if isinstance(o, PatchElement):
                parent = MFPGUI().recall(o.parent_id)
                layer = None
                if isinstance(parent, PatchInfo):
                    if "layername" in params:
                        layer = parent.find_layer(params["layername"])
                    if not layer:
                        layer = MFPGUI().appwin.active_layer()
                    layer.add(o)
                    layer.group.add_actor(o)
                    o.container = layer.group
                elif isinstance(parent, PatchElement):
                    # FIXME: don't hardcode GOP offsets
                    if not parent.export_x:
                        log.debug(
                            f"_create: parent {parent.scope.name}.{parent.name} has no export_x\n",
                        )
                    xpos = params.get("position_x", 0) - parent.export_x + 2
                    ypos = params.get("position_y", 0) - parent.export_y + 20
                    o.move(xpos, ypos)
                    o.editable = False
                    parent.layer.add(o)
                    parent.add_actor(o)
                    o.container = parent

                o.configure(params)
                MFPGUI().appwin.register(o)
            else:
                o.configure(params)

            MFPGUI().remember(o)
            MFPGUI().appwin.refresh(o)
            o.update()

    def connect(self, obj_1_id, obj_1_port, obj_2_id, obj_2_port):
        from .gui_main import MFPGUI
        from .gui.connection_element import ConnectionElement
        from .gui.patch_info import PatchInfo
        from mfp import log

        obj_1 = MFPGUI().recall(obj_1_id)
        obj_2 = MFPGUI().recall(obj_2_id)

        if obj_1 is None or obj_2 is None:
            log.debug("ERROR: connect: obj_1 (id=%s) --> %s, obj_2 (id=%s) --> %s"
                      % (obj_1_id, obj_1, obj_2_id, obj_2))
            return None
        elif isinstance(obj_1, PatchInfo) or isinstance(obj_2, PatchInfo):
            log.debug("Trying to connect a PatchInfo (%s [%s] --> %s [%s])"
                      % (obj_1.obj_name, obj_1_id, obj_2.obj_name, obj_2_id))
            return None

        for conn in obj_1.connections_out:
            if conn.obj_2 == obj_2 and conn.port_2 == obj_2_port:
                return

        c = ConnectionElement(MFPGUI().appwin, obj_1, obj_1_port, obj_2, obj_2_port)
        MFPGUI().appwin.register(c)
        obj_1.connections_out.append(c)
        obj_2.connections_in.append(c)

    async def delete(self, obj_id):
        from .gui_main import MFPGUI
        from .gui.patch_info import PatchInfo
        obj = MFPGUI().recall(obj_id)
        if isinstance(obj, PatchInfo):
            await obj.delete()
            if obj in MFPGUI().appwin.patches:
                MFPGUI().appwin.patches.remove(obj)
        elif obj is not None:
            await obj.delete()

    def select(self, obj_id):
        from .gui_main import MFPGUI
        from .gui.patch_info import PatchInfo
        obj = MFPGUI().recall(obj_id)
        if isinstance(obj, PatchInfo):
            MFPGUI().appwin.layer_select(obj.layers[0])
        else:
            MFPGUI().appwin.select(obj)

    def load_start(self):
        from .gui_main import MFPGUI
        MFPGUI().appwin.load_start()

    def load_complete(self):
        from .gui_main import MFPGUI
        MFPGUI().appwin.load_complete()

    def set_undeletable(self, val):
        from .gui_main import MFPGUI
        MFPGUI().appwin.deletable = val

    def clear(self):
        pass
