from .bang import Bang
from .patch import Patch
from .method import MethodCall
from .rpc import RPCWrapper, rpcwrap, rpcwrap_noresp
from . import log

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
        r = obj_1.connect(obj_1_port, obj_2, obj_2_port)
        return r

    @rpcwrap
    def disconnect(self, obj_1_id, obj_1_port, obj_2_id, obj_2_port):
        from .mfp_app import MFPApp
        obj_1 = MFPApp().recall(obj_1_id)
        obj_2 = MFPApp().recall(obj_2_id)

        r = obj_1.disconnect(obj_1_port, obj_2, obj_2_port)
        return r

    @rpcwrap
    def send_bang(self, obj_id, port):
        from .mfp_app import MFPApp
        obj = MFPApp().recall(obj_id)
        obj.send(Bang, port)
        return True

    @rpcwrap
    def send(self, obj_id, port, data):
        from .mfp_app import MFPApp
        obj = MFPApp().recall(obj_id)
        obj.send(data, port)
        return True

    @rpcwrap
    def eval_and_send(self, obj_id, port, message):
        from .mfp_app import MFPApp
        obj = MFPApp().recall(obj_id)
        obj.send(obj.parse_obj(message), port)
        return True

    @rpcwrap
    def send_methodcall(self, obj_id, port, method, *args, **kwargs): 
        from .mfp_app import MFPApp
        obj = MFPApp().recall(obj_id)
        m = MethodCall(method, *args, **kwargs)
        obj.send(m, port)

    @rpcwrap
    def delete(self, obj_id):
        from .mfp_app import MFPApp
        obj = MFPApp().recall(obj_id)
        obj.delete()

    @rpcwrap
    def set_params(self, obj_id, params):
        from .mfp_app import MFPApp
        obj = MFPApp().recall(obj_id)
        obj.gui_params = params

    @rpcwrap
    def set_gui_created(self, obj_id, value):
        from .mfp_app import MFPApp
        obj = MFPApp().recall(obj_id)
        obj.gui_created = value

    @rpcwrap
    def set_do_onload(self, obj_id, value):
        from .mfp_app import MFPApp
        obj = MFPApp().recall(obj_id)
        obj.do_onload = value 

    @rpcwrap
    def get_info(self, obj_id):
        from .mfp_app import MFPApp
        obj = MFPApp().recall(obj_id)
        return dict(num_inlets=len(obj.inlets),
                    num_outlets=len(obj.outlets),
                    dsp_inlets=obj.dsp_inlets,
                    dsp_outlets=obj.dsp_outlets)
    
    @rpcwrap
    def get_tooltip(self, obj_id, direction=None, portno=None, details=False):
        from .mfp_app import MFPApp
        obj = MFPApp().recall(obj_id)
        if not obj or isinstance(obj, MFPApp):
            # FIXME: this is to wallpaper over bad behavior when deleting, #110 
            return ''
        return obj.tooltip(direction, portno, details)

    @rpcwrap
    def log_write(self, msg):
        from .mfp_app import MFPApp
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
        if obj is None:
            log.debug("Cannot find object for %s to set scope to %s" % (obj_id, scope_name))
            return

        scope = obj.patch.scopes.get(scope_name)

        log.debug("Reassigning scope for obj", obj_id, "to", scope_name)
        obj.assign(obj.patch, scope, obj.name)

    @rpcwrap
    def open_file(self, file_name, context=None):
        from .mfp_app import MFPApp
        print "MFPCommand.open_file:", file_name, context
        patch = MFPApp().open_file(file_name)
        return patch.obj_id

    @rpcwrap
    def save_file(self, patch_name, file_name):
        from .mfp_app import MFPApp
        patch = MFPApp().patches.get(patch_name)
        if patch:
            patch.save_file(file_name)

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
    def load_context(self, file_name, node_id, context_id):
        from .mfp_app import MFPApp
        from .dsp_object import DSPContext 

        ctxt = DSPContext(node_id, context_id)
        patch = MFPApp().open_file(file_name, ctxt)
        patch.hot_inlets = range(len(patch.inlets))
        return patch.obj_id

    @rpcwrap
    def close_context(self, node_id, context_id):
        from .mfp_app import MFPApp
        from .dsp_object import DSPContext 
        ctxt = DSPContext(node_id, context_id)

        print "close_context: patches on enter", MFPApp().patches 

        to_delete = [] 
        for patch_id, patch in MFPApp().patches.items():
            print "close_context: looking at", patch_id, patch
            if patch.context == ctxt:
                print " --> Closing patch %s in context %s" % (patch.name, ctxt)
                patch.delete()
                to_delete.append(patch_id)
                print "     Patch deleted"

        for patch_id in to_delete: 
            del MFPApp().patches[patch_id] 

        print "close_context: patches on leave", MFPApp().patches 

        if not len(MFPApp().patches):
            print "close_context: no patches left, closing MFP app"
            MFPApp().finish_soon()
            return None 

    @rpcwrap_noresp
    def quit(self):
        from .mfp_app import MFPApp
        MFPApp().finish()
        return None


