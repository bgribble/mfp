"""
mfp_command.py -- API to send commands to the main MFP process

Copyright (c) Bill Gribble <grib@billgribble.com>
"""

import json
from carp.service import apiclass, noresp

from mfp import log
from .bang import Bang
from .patch import Patch
from .method import MethodCall
from .processor import Processor


@apiclass
class MFPCommand:
    async def create(self, objtype, initargs, patch_name, scope_name, obj_name):
        from .mfp_app import MFPApp
        patch = MFPApp().patches.get(patch_name)
        scope = patch.scopes.get(scope_name) or patch.default_scope

        obj = await MFPApp().create(objtype, initargs, patch, scope, obj_name)
        if obj is None:
            log.warning(f"Failed to create object {objtype} {initargs} {patch} {scope} {obj_name}")
            return None
        return obj.gui_params

    async def create_export_gui(self, obj_id):
        from .mfp_app import MFPApp
        obj = MFPApp().recall(obj_id)
        if isinstance(obj, Patch):
            await obj.create_export_gui()
            return True
        return False

    def connect(self, obj_1_id, obj_1_port, obj_2_id, obj_2_port):
        from .mfp_app import MFPApp
        obj_1 = MFPApp().recall(obj_1_id)
        obj_2 = MFPApp().recall(obj_2_id)
        if isinstance(obj_1, Processor) and isinstance(obj_2, Processor):
            return obj_1.connect(obj_1_port, obj_2, obj_2_port)
        return None

    def disconnect(self, obj_1_id, obj_1_port, obj_2_id, obj_2_port):
        from .mfp_app import MFPApp
        obj_1 = MFPApp().recall(obj_1_id)
        obj_2 = MFPApp().recall(obj_2_id)

        if isinstance(obj_1, Processor) and isinstance(obj_2, Processor):
            return obj_1.disconnect(obj_1_port, obj_2, obj_2_port)
        return None

    @noresp
    async def dsp_response(self, obj_id, resp_type, resp_value):
        from .mfp_app import MFPApp
        obj = MFPApp().recall(obj_id)
        if isinstance(obj, Processor):
            await obj.send((resp_type, json.loads(resp_value)), -1)

    @noresp
    async def send_bang(self, obj_id, port):
        from .mfp_app import MFPApp
        obj = MFPApp().recall(obj_id)
        if isinstance(obj, Processor):
            await obj.send(Bang, port)
        return True

    @noresp
    async def send(self, obj_id, port, data):
        from .mfp_app import MFPApp
        obj = MFPApp().recall(obj_id)
        if isinstance(obj, Processor):
            await obj.send(data, port)
        return True

    @noresp
    async def eval_and_send(self, obj_id, port, message):
        from .mfp_app import MFPApp
        obj = MFPApp().recall(obj_id)
        if isinstance(obj, Processor):
            await obj.send(obj.parse_obj(message), port)
        return True

    @noresp
    async def send_methodcall(self, obj_id, port, method, *args, **kwargs):
        from .mfp_app import MFPApp
        obj = MFPApp().recall(obj_id)
        m = MethodCall(method, *args, **kwargs)
        if isinstance(obj, Processor):
            await obj.send(m, port)

    async def delete(self, obj_id):
        from .mfp_app import MFPApp
        obj = MFPApp().recall(obj_id)
        if isinstance(obj, Processor):
            await obj.delete()

    @noresp
    def set_params(self, obj_id, params):
        from .mfp_app import MFPApp
        obj = MFPApp().recall(obj_id)
        if isinstance(obj, Processor):
            obj.set_gui_params(params)

    def set_gui_created(self, obj_id, value):
        from .mfp_app import MFPApp
        obj = MFPApp().recall(obj_id)
        if isinstance(obj, Processor):
            obj.gui_created = value

    @noresp
    def set_do_onload(self, obj_id, value):
        from .mfp_app import MFPApp
        obj = MFPApp().recall(obj_id)
        if isinstance(obj, Processor):
            obj.do_onload = value

    def get_info(self, obj_id):
        from .mfp_app import MFPApp
        obj = MFPApp().recall(obj_id)
        if isinstance(obj, Processor):
            return dict(num_inlets=len(obj.inlets),
                        num_outlets=len(obj.outlets),
                        dsp_inlets=obj.dsp_inlets,
                        dsp_outlets=obj.dsp_outlets)
        return {}

    def get_tooltip(self, obj_id, direction=None, portno=None, details=False):
        from .mfp_app import MFPApp
        obj = MFPApp().recall(obj_id)
        if isinstance(obj, Processor):
            return obj.tooltip(direction, portno, details)
        else:
            return ''

    def get_tooltip_info(self, obj_id, direction=None, portno=None, details=False):
        from .mfp_app import MFPApp
        obj = MFPApp().recall(obj_id)
        if isinstance(obj, Processor):
            return obj.tooltip_info(direction, portno, details)
        else:
            return ''

    @noresp
    def log_write(self, msg):
        from .mfp_app import MFPApp
        if log.log_force_console:
            print('console:', msg)
        MFPApp().gui_command.log_write(msg)

    async def console_eval(self, cmd):
        from .mfp_app import MFPApp
        return await MFPApp().console.runsource(cmd)

    @noresp
    def add_scope(self, patch_id, scope_name):
        from .mfp_app import MFPApp
        patch = MFPApp().recall(patch_id)
        patch.add_scope(scope_name)

    @noresp
    def rename_scope(self, patch_id, old_name, new_name):
        from .mfp_app import MFPApp
        patch = MFPApp().recall(patch_id)
        scope = patch.scopes.get(old_name)
        if scope:
            scope.name = new_name
        # FIXME merge scopes if changing to a used name?
        # FIXME signal send/receive objects to flush and re-resolve

    @noresp
    def rename_obj(self, obj_id, new_name):
        from .mfp_app import MFPApp
        obj = MFPApp().recall(obj_id)
        obj.rename(new_name)

    @noresp
    def set_scope(self, obj_id, scope_name):
        from .mfp_app import MFPApp
        obj = MFPApp().recall(obj_id)

        if obj is None or isinstance(obj, MFPApp):
            log.debug("Cannot find object for %s to set scope to %s" % (obj_id, scope_name))
            return

        scope = obj.patch.scopes.get(scope_name)
        if scope is None:
            scope = obj.patch.add_scope(scope_name)
        obj.assign(obj.patch, scope, obj.name)

    @noresp
    async def open_file(self, file_name, context=None):
        from .mfp_app import MFPApp
        patch = await MFPApp().open_file(file_name)
        return patch.obj_id

    @noresp
    async def save_file(self, patch_name, file_name):
        from .mfp_app import MFPApp
        patch = MFPApp().patches.get(patch_name)
        if patch:
            await patch.save_file(file_name)

    @noresp
    async def show_editor(self, obj_id, show):
        from .mfp_app import MFPApp
        patch = MFPApp().objects.get(obj_id)
        if not isinstance(patch, Patch):
            log.warning("show_editor: error: obj_id=%s, obj=%s is not a patch"
                        % (obj_id, patch))
        elif show:
            await patch.create_gui()
        else:
            await patch.delete_gui()

    @noresp
    async def save_lv2(self, patch_name, plugin_name):
        from .mfp_app import MFPApp
        patch = MFPApp().patches.get(patch_name)
        file_name = plugin_name + ".mfp"
        if patch:
            await patch.save_lv2(plugin_name, file_name)

    def clipboard_copy(self, pointer_pos, objlist):
        from .mfp_app import MFPApp
        return MFPApp().clipboard_copy(pointer_pos, objlist)

    def clipboard_paste(self, json_txt, patch_id, scope_name, mode):
        from .mfp_app import MFPApp
        patch = MFPApp().recall(patch_id)
        scope = patch.scopes.get(scope_name)
        return MFPApp().clipboard_paste(json_txt, patch, scope, mode)

    def open_context(self, node_id, context_id, owner_pid, samplerate):
        from .dsp_object import DSPContext
        from .mfp_app import MFPApp
        try:
            ctxt_name = open("/proc/%d/cmdline" % owner_pid, "r").read().split("\x00")[0]
            log.debug(f"open_context: new context, name={ctxt_name}")
        except Exception:
            ctxt_name = ""

        if MFPApp().samplerate != samplerate:
            log.debug("open_context: samplerate changing from %d to %d" %
                      (MFPApp().samplerate, samplerate))
            MFPApp().samplerate = samplerate

        if DSPContext.create(node_id, context_id, ctxt_name):
            log.debug(f"open_context: created context, node={node_id} id={context_id} name={ctxt_name}")
            return True
        return False

    async def load_context(self, file_name, node_id, context_id):
        from .mfp_app import MFPApp
        from .dsp_object import DSPContext
        log.debug(f"load_context: loading {file_name} in context node={node_id} ctxt_id={context_id}")
        ctxt = DSPContext.lookup(node_id, context_id)
        patch = await MFPApp().open_file(file_name, ctxt, False)
        patch.hot_inlets = list(range(len(patch.inlets)))
        patch.gui_params['deletable'] = False
        return patch.obj_id

    async def close_context(self, node_id, context_id):
        from .mfp_app import MFPApp
        from .dsp_object import DSPContext
        ctxt = DSPContext.lookup(node_id, context_id)

        to_delete = []
        for _, patch in MFPApp().patches.items():
            if patch.context == ctxt:
                to_delete.append(patch)

        for patch in to_delete:
            pid = patch.obj_id
            await patch.delete()
            if pid in MFPApp().patches:
                del MFPApp().patches[pid]

        if not len(MFPApp().patches):
            await MFPApp().finish_soon()
            return None

    def open_patches(self):
        from .mfp_app import MFPApp
        return [p.obj_id for p in MFPApp().patches.values()]

    async def has_unsaved_changes(self, obj_id):
        from .mfp_app import MFPApp
        patch = MFPApp().recall(obj_id)
        return await patch.has_unsaved_changes()

    @noresp
    def quit(self):
        from .mfp_app import MFPApp
        MFPApp().async_task(MFPApp().finish())
        return None

    def toggle_pause(self):
        from .mfp_app import MFPApp
        return MFPApp().toggle_pause()
