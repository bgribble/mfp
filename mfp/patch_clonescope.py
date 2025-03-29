#! /usr/bin/env python
'''
patch_clonescope.py: methods for cloning a scope within a patch
(aka hygienic subpatch copying)
'''

from .utils import extends
from .patch import Patch
from . import log
from .bang import Uninit

@extends(Patch)
async def clonescope(self, scopename, num_copies, **kwargs):
    from .mfp_app import MFPApp

    scope = self.scopes.get(scopename)
    parts = scopename.split('_')
    basename = scopename
    ccount = 2
    cdigits = 3

    grid = kwargs.get("grid", (1, 0))
    grid_row = 0
    grid_col = 0

    if not scope:
        log.warning("clonescope: no scope", scopename, "found")
        return

    if num_copies is Uninit or not num_copies:
        log.warning("clonescope: no number of copies provided")
        return

    # num_copies is the total number desired, including the template
    num_copies = num_copies - 1

    if len(parts) > 1:
        try:
            ccount = int(parts[-1]) + 1
            cdigits = len(parts[-1])
            basename = '_'.join(parts[:-1])
        except Exception as e:
            log.error("clonescope: caught exception", e)
            log.debug_traceback(e)

    # find bounding box of any interface elements
    bbox_min_x = bbox_max_x = bbox_min_y = bbox_max_y = bbox_w = bbox_h = None
    ui_items = {}

    for name, srcobj in scope.bindings.items():
        if self.obj_is_exportable(srcobj):
            ui_items[name] = srcobj
            xpos = srcobj.gui_params.get("position_x")
            ypos = srcobj.gui_params.get("position_y")
            width = srcobj.gui_params.get("width")
            height = srcobj.gui_params.get("height")
            if bbox_min_x is None or xpos < bbox_min_x:
                bbox_min_x = xpos
            if bbox_max_x is None or (xpos + width) > bbox_max_x:
                bbox_max_x = xpos + width
            if bbox_min_y is None or ypos < bbox_min_y:
                bbox_min_y = ypos
            if bbox_max_y is None or (ypos + height) > bbox_max_y:
                bbox_max_y = ypos + height

    if bbox_min_x is not None:
        bbox_w = bbox_max_x - bbox_min_x + 2
        bbox_h = bbox_max_y - bbox_min_y + 2

    if MFPApp().gui_command:
        await MFPApp().gui_command.load_start()

    need_gui = []
    all_clones = []

    # make copies of elements in scope
    for copynum in range(num_copies):
        obj_copied = {}
        obj_idmap = {}

        fmt = "%%s_%%0%dd" % cdigits
        newscope = self.add_scope(fmt % (basename, copynum + ccount))
        newscope.clonenum = copynum + 1

        if grid[0] and not grid[1]:
            grid_row += 1
            if grid_row >= grid[0]:
                grid_row = 0
                grid_col += 1
        else:
            grid_col += 1
            if grid[1] and grid_col >= grid[1]:
                grid_col = 0
                grid_row += 1

        # remake objects
        for name, srcobj in scope.bindings.items():
            if not srcobj.save_to_patch:
                continue
            newobj = await srcobj.clone(self, newscope, name)
            all_clones.append(newobj)
            obj_copied[name] = newobj
            obj_idmap[srcobj.obj_id] = newobj

            if name in ui_items:
                dx = grid_col * bbox_w
                dy = grid_row * bbox_h
                newobj.gui_params["position_x"] += dx
                newobj.gui_params["position_y"] += dy

            if srcobj.gui_created:
                need_gui.append(newobj)

        # remake connections
        for name, srcobj in scope.bindings.items():
            if not srcobj.save_to_patch:
                continue
            newobj = obj_copied[name]

            for port_num, port_conn in enumerate(srcobj.connections_in):
                for tobj, tport in port_conn:
                    tobj_newid = obj_idmap.get(tobj.obj_id)
                    if not tobj_newid:
                        if tobj.scope != scope:
                            tobj_newid = tobj
                        else:
                            continue
                    if (newobj, port_num) not in tobj_newid.connections_out[tport]:
                        await tobj_newid.connect(tport, newobj, port_num)

            for port_num, port_conn in enumerate(srcobj.connections_out):
                for tobj, tport in port_conn:
                    tobj_newid = obj_idmap.get(tobj.obj_id)
                    if not tobj_newid:
                        if tobj.scope != scope:
                            tobj_newid = tobj
                        else:
                            continue
                    if (tobj_newid, tport) not in newobj.connections_out[port_num]:
                        await newobj.connect(port_num, tobj_newid, tport)

    for name, srcobj in ui_items.items():
        # kludge -- change labels in the UI template objects
        if srcobj.gui_params.get("display_type") == "text":
            txtprms = dict(num=0, row=0, col=0)
            srcobj.value = srcobj.value % txtprms
            srcobj.gui_params["value"] = srcobj.value

    self.update_export_bounds()

    if not MFPApp().no_onload:
        MFPApp().async_task(
            self._run_onload([obj for obj in all_clones])
        )

    for obj in need_gui:
        await obj.create_gui()
