from .bang import Bang
from .patch import Patch
from .method import MethodCall
from .processor import Processor
from .rpc import RPCWrapper, rpcwrap, rpcwrap_noresp
from mfp import log

class MFPCommand(RPCWrapper):
    @rpcwrap
    def create(self, objtype, initargs, patch_name, scope_name, obj_name):
        from .mfp_app import MFPApp
        patch = MFPApp().patches.get(patch_name)
        scope = patch.scopes.get(scope_name) or patch.default_scope

        obj = MFPApp().create(objtype, initargs, patch, scope, obj_name)
        if obj is None:
            return None
        return obj.gui_params

    @rpcwrap
    def create_export_gui(self, obj_id):
        from .mfp_app import MFPApp
        obj = MFPApp().recall(obj_id)
        if isinstance(obj, Patch):
            obj.create_export_gui()
            return True
        else:
            return False 

    @rpcwrap
    def connect(self, obj_1_id, obj_1_port, obj_2_id, obj_2_port):
        from .mfp_app import MFPApp
        obj_1 = MFPApp().recall(obj_1_id)
        obj_2 = MFPApp().recall(obj_2_id)
        if isinstance(obj_1, Processor) and isinstance(obj_2, Processor):
            return obj_1.connect(obj_1_port, obj_2, obj_2_port)
        else: 
            return None 

    @rpcwrap
    def disconnect(self, obj_1_id, obj_1_port, obj_2_id, obj_2_port):
        from .mfp_app import MFPApp
        obj_1 = MFPApp().recall(obj_1_id)
        obj_2 = MFPApp().recall(obj_2_id)

        if isinstance(obj_1, Processor) and isinstance(obj_2, Processor):
            return obj_1.disconnect(obj_1_port, obj_2, obj_2_port)
        else:
            return None 
    @rpcwrap
    def dsp_response(self, obj_id, resp_type, resp_value):
        from .mfp_app import MFPApp
        obj = MFPApp().recall(obj_id)
        if isinstance(obj, Processor): 
            obj.send((resp_type, resp_value), -1)

    @rpcwrap
    def send_bang(self, obj_id, port):
        from .mfp_app import MFPApp
        obj = MFPApp().recall(obj_id)
        if isinstance(obj, Processor):
            obj.send(Bang, port)
        return True

    @rpcwrap
    def send(self, obj_id, port, data):
        from .mfp_app import MFPApp
        obj = MFPApp().recall(obj_id)
        if isinstance(obj, Processor):
            obj.send(data, port)
        return True

    @rpcwrap
    def eval_and_send(self, obj_id, port, message):
        from .mfp_app import MFPApp
        obj = MFPApp().recall(obj_id)
        if isinstance(obj, Processor):
            obj.send(obj.parse_obj(message), port)
        return True

    @rpcwrap
    def send_methodcall(self, obj_id, port, method, *args, **kwargs): 
        from .mfp_app import MFPApp
        obj = MFPApp().recall(obj_id)
        m = MethodCall(method, *args, **kwargs)
        if isinstance(obj, Processor):
            obj.send(m, port)

    @rpcwrap
    def delete(self, obj_id):
        from .mfp_app import MFPApp
        obj = MFPApp().recall(obj_id)
        if isinstance(obj, Processor):
            obj.delete()

    @rpcwrap
    def set_params(self, obj_id, params):
        from .mfp_app import MFPApp
        obj = MFPApp().recall(obj_id)

        if isinstance(obj, Processor):
            obj.gui_params = params

    @rpcwrap
    def set_gui_created(self, obj_id, value):
        from .mfp_app import MFPApp
        obj = MFPApp().recall(obj_id)
        if isinstance(obj, Processor):
            obj.gui_created = value

    @rpcwrap
    def set_do_onload(self, obj_id, value):
        from .mfp_app import MFPApp
        obj = MFPApp().recall(obj_id)
        if isinstance(obj, Processor):
            obj.do_onload = value 

    @rpcwrap
    def get_info(self, obj_id):
        from .mfp_app import MFPApp
        obj = MFPApp().recall(obj_id)
        if isinstance(obj, Processor):
            return dict(num_inlets=len(obj.inlets),
                        num_outlets=len(obj.outlets),
                        dsp_inlets=obj.dsp_inlets,
                        dsp_outlets=obj.dsp_outlets)
        else: 
            return {}
    
    @rpcwrap
    def get_tooltip(self, obj_id, direction=None, portno=None, details=False):
        from .mfp_app import MFPApp
        obj = MFPApp().recall(obj_id)
        if isinstance(obj, Processor):
            return obj.tooltip(direction, portno, details)
        else:
            return ''

    @rpcwrap
    def log_write(self, msg):
        from .mfp_app import MFPApp
        if log.log_force_console:
            print 'console:', msg 
        MFPApp().gui_command.log_write(msg)

    @rpcwrap
    def console_eval(self, cmd):
        from .mfp_app import MFPApp
        return MFPApp().console.runsource(cmd)

    @rpcwrap
    def add_scope(self, patch_id, scope_name):
        from .mfp_app import MFPApp
        patch = MFPApp().recall(patch_id)
        patch.add_scope(scope_name)

    @rpcwrap
    def rename_scope(self, patch_id, old_name, new_name):
        from .mfp_app import MFPApp
        patch = MFPApp().recall(patch_id)
        scope = patch.scopes.get(old_name)
        if scope:
            scope.name = new_name
        # FIXME merge scopes if changing to a used name?
        # FIXME signal send/receive objects to flush and re-resolve

    @rpcwrap
    def rename_obj(self, obj_id, new_name):
        from .mfp_app import MFPApp
        obj = MFPApp().recall(obj_id)
        obj.rename(new_name)

    @rpcwrap
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

    @rpcwrap
    def open_file(self, file_name, context=None):
        from .mfp_app import MFPApp
        patch = MFPApp().open_file(file_name)
        return patch.obj_id

    @rpcwrap
    def save_file(self, patch_name, file_name):
        from .mfp_app import MFPApp
        patch = MFPApp().patches.get(patch_name)
        if patch:
            patch.save_file(file_name)

    @rpcwrap
    def show_editor(self, obj_id, show):
        from .mfp_app import MFPApp
        patch = MFPApp().objects.get(obj_id)
        if not isinstance(patch, Patch):
            log.warning("show_editor: error: obj_id=%s, obj=%s is not a patch" 
                        % (obj_id, patch))
        elif show:
            patch.create_gui()
        else:
            patch.delete_gui()

    @rpcwrap
    def save_lv2(self, patch_name, plugin_name):
        from .mfp_app import MFPApp
        patch = MFPApp().patches.get(patch_name)
        file_name = plugin_name + ".mfp"
        if patch:
            patch.save_lv2(plugin_name, file_name)

    @rpcwrap
    def clipboard_copy(self, pointer_pos, objlist):
        from .mfp_app import MFPApp
        return MFPApp().clipboard_copy(pointer_pos, objlist)

    @rpcwrap
    def clipboard_paste(self, json_txt, patch_id, scope_name, mode):
        from .mfp_app import MFPApp
        patch = MFPApp().recall(patch_id)
        scope = patch.scopes.get(scope_name)
        return MFPApp().clipboard_paste(json_txt, patch, scope, mode)

    @rpcwrap
    def open_context(self, node_id, context_id, owner_pid, samplerate):
        from .dsp_object import DSPContext 
        from .mfp_app import MFPApp
        try: 
            ctxt_name = open("/proc/%d/cmdline" % owner_pid, "r").read().split("\x00")[0]
            log.debug("open_context: new context, name=%s" % ctxt_name)
        except: 
            ctxt_name = ""

        if MFPApp().samplerate != samplerate: 
            log.debug("open_context: samplerate changing from %d to %d" % 
                      (MFPApp().samplerate, samplerate))
            MFPApp().samplerate = samplerate 


        if DSPContext.create(node_id, context_id, ctxt_name):
            return True
        else:
            return False

    @rpcwrap
    def load_context(self, file_name, node_id, context_id):
        from .mfp_app import MFPApp
        from .dsp_object import DSPContext 
        ctxt = DSPContext.lookup(node_id, context_id)
        patch = MFPApp().open_file(file_name, ctxt, False)
        patch.hot_inlets = range(len(patch.inlets))
        patch.gui_params['deletable'] = False
        return patch.obj_id

    @rpcwrap
    def close_context(self, node_id, context_id):
        from .mfp_app import MFPApp
        from .dsp_object import DSPContext 
        ctxt = DSPContext.lookup(node_id, context_id)

        to_delete = [] 
        for patch_id, patch in MFPApp().patches.items():
            if patch.context == ctxt:
                to_delete.append(patch)

        for patch in to_delete: 
            pid = patch.obj_id
            patch.delete()
            if pid in MFPApp().patches:
                del MFPApp().patches[patch_id] 

        if not len(MFPApp().patches):
            MFPApp().finish_soon()
            return None 

    @rpcwrap
    def open_patches(self):
        from .mfp_app import MFPApp
        return [ p.obj_id for p in MFPApp().patches.values()]

    @rpcwrap
    def has_unsaved_changes(self, obj_id): 
        from .mfp_app import MFPApp
        patch = MFPApp().recall(obj_id)
        return patch.has_unsaved_changes()

    @rpcwrap_noresp
    def quit(self):
        from .mfp_app import MFPApp
        from threading import Thread 
        Thread(target=lambda *_: MFPApp().finish()).start()
        return None

    @rpcwrap
    def toggle_pause(self): 
        from .mfp_app import MFPApp
        return MFPApp().toggle_pause()


