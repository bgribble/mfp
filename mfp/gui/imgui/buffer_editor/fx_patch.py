"""
buffer_editor/fx_patch.py -- set up and teardown the internal FX patch

Copyright (c) Bill Gribble <grib@billgribble.com>
"""

import asyncio
from mfp import log
from mfp.utils import extends
from .buffer_editor import BufferEditor


########################################
# fx patch
@extends(BufferEditor)
async def fx_open_patch(self, fxname):
    from mfp.gui_main import MFPGUI

    # close the previous patch
    await self.fx_close_patch()

    # create new patch wrapping the specified effect
    self.fx_patch_id = await MFPGUI().mfp.open_file(
        "bufedit.fx~.mfp",
        initargs=f"'{fxname}', {self.buffer_info.channels}",
        show_gui=True,
    )

    # each fx patch needs to take a number param for channel count
    # input level and xfade channels on the left

    # connect source to fx
    for port in range(self.buffer_info.channels):
        await MFPGUI().mfp.disconnect(
            self.working_source_id, port, self.working_sink_id, port
        )
        await MFPGUI().mfp.connect(
            self.working_source_id, port, self.fx_patch_id, port + 2
        )
        await MFPGUI().mfp.connect(
            self.fx_patch_id, port, self.working_sink_id, port
        )


    # connect input level and xfade
    for port in [0, 1]:
        await MFPGUI().mfp.connect(
            self.working_source_id, self.buffer_info.channels + port + 1,
            self.fx_patch_id, port
        )

    for element in [
        'apply_button', 'cancel_button', 'selection_toggle',
        'bypass_toggle', 'xfade_enum', 'preroll_enum'
    ]:
        element_id = await MFPGUI().mfp.resolve(element, self.fx_patch_id)
        self.fx_patch_elements[element] = MFPGUI().objects.get(element_id)

    # if there's a selection, default to "Selection only"
    if self.implot_selection:
        sel_toggle = self.fx_patch_elements.get('selection_toggle')
        await MFPGUI().mfp.send(
            sel_toggle.obj_id, 0, True
        )

    # add actions for Apply and Cancel buttons
    cancel = self.fx_patch_elements["cancel_button"]
    cancel.extra_action = self.fx_close_patch

    apply = self.fx_patch_elements["apply_button"]
    apply.extra_action = self.fx_apply_patch


@extends(BufferEditor)
async def fx_apply_patch(self):
    from mfp.gui_main import MFPGUI
    rec_channels = sum(
        1 << c for c in range(self.buffer_info.channels)
    )

    source_params = dict(
        buf_mode=7,
        play_channels=0xff,
        buf_pos=0,
        region_start=0,
        region_end=self.buffer_info.size,
        trig_chan=self.buffer_info.channels,
    )
    sink_params = dict(
        buf_mode=3,
        play_channels=0,
        rec_channels=rec_channels,
        rec_enabled=1,
        buf_pos=0,
        region_start=0,
        region_end=self.buffer_info.size,
        trig_chan=self.buffer_info.channels,
    )

    handler_id = []
    async def fw_handler(target, signal, status):
        if status == 0:
            MFPGUI().appwin.signal_unlisten(handler_id[0])
            self.buffer_grab(self.working_buf_obj)
            await MFPGUI().mfp.send(self.working_trigger_id, 0, 0)
            log.debug(f"[freewheel] done freewheeling")

    handler_id.append(MFPGUI().appwin.signal_listen("freewheel", fw_handler))

    await MFPGUI().mfp.send(self.working_source_id, 0, source_params)
    await MFPGUI().mfp.send(self.working_sink_id, 0, sink_params)

    # sleep a bit to make sure params hit
    await asyncio.sleep(0.1)
    await MFPGUI().mfp.send(self.working_trigger_id, 0, 1)
    log.debug(f"[freewheel] freewheeling for {self.buffer_info.size} frames")
    await MFPGUI().mfp.freewheel(self.working_patch_id, self.buffer_info.size)


@extends(BufferEditor)
async def fx_close_patch(self):
    from mfp.gui_main import MFPGUI

    if not self.fx_patch_id:
        return

    # remove actions for Apply and Cancel buttons
    cancel = self.fx_patch_elements["cancel_button"]
    cancel.extra_action = None

    # reconnect sink buffer to audition outs, disconnect FX outs
    for port in range(self.buffer_info.channels):
        await MFPGUI().mfp.disconnect(
            self.working_source_id, port,
            self.fx_patch_id, port + 2
        )
        await MFPGUI().mfp.disconnect(
            self.fx_patch_id, port,
            self.working_sink_id, port
        )
        await MFPGUI().mfp.connect(
            self.working_source_id, port, self.working_sink_id, port
        )

    # connect input level and xfade
    for port in [0, 1]:
        await MFPGUI().mfp.disconnect(
            self.working_source_id, self.buffer_info.channels + port,
            self.fx_patch_id, port
        )

    # delete FX patch
    await MFPGUI().mfp.delete(self.fx_patch_id)
    self.fx_patch_id = None
