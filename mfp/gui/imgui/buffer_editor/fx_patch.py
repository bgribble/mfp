"""
buffer_editor/fx_patch.py -- set up and teardown the internal FX patch

Copyright (c) Bill Gribble <grib@billgribble.com>
"""

from mfp import log
from mfp.utils import extends
from .buffer_editor import BufferEditor


########################################
# fx patch
@extends(BufferEditor)
async def fx_open_patch(self, fxname):
    from mfp.gui_main import MFPGUI

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
        await MFPGUI().mfp.connect(
            self.working_source_id, port, self.fx_patch_id, port + 2
        )
        await MFPGUI().mfp.connect(
            self.fx_patch_id, port, self.working_sink_id, port
        )

        if port % 2 == 0:
            # disconnect previous outputs
            await MFPGUI().mfp.disconnect(
                self.working_sink_id, port, self.working_aud0_info.get("obj_id"), 0
            )
            await MFPGUI().mfp.connect(
                self.fx_patch_id, port, self.working_aud0_info.get("obj_id"), 0
            )
        else:
            await MFPGUI().mfp.disconnect(
                self.working_sink_id, port, self.working_aud1_info.get("obj_id"), 0
            )
            await MFPGUI().mfp.connect(
                self.fx_patch_id, port, self.working_aud1_info.get("obj_id"), 0
            )

    # connect input level and xfade
    for port in [0, 1]:
        await MFPGUI().mfp.connect(
            self.working_source_id, self.buffer_info.channels + port,
            self.fx_patch_id, port
        )

    for element in [
        'apply_button', 'cancel_button', 'selection_toggle',
        'bypass_toggle', 'xfade_enum', 'preroll_enum'
    ]:
        element_id = await MFPGUI().mfp.resolve(element, self.fx_patch_id)
        self.fx_patch_elements[element] = MFPGUI().objects.get(element_id)

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
        buf_mode=5,
        play_channels=0xff,
        buf_pos=0,
        region_start=0,
        region_end=self.buffer_info.size,
        trig_trigger=1,
    )
    sink_params = dict(
        buf_mode=0,
        play_channels=0,
        rec_channels=rec_channels,
        rec_enabled=1,
        buf_pos=0,
        region_start=0,
        region_end=self.buffer_info.size,
        trig_trigger=1,
    )

    def fw_handler(target, signal, status):
        if status == 0:
            log.debug(f"[bufedit] re-grabbing data from {self.working_buf_obj}")
            self.buffer_grab(self.working_buf_obj)

    MFPGUI().appwin.signal_listen("freewheel", fw_handler)
    await MFPGUI().mfp.send(self.working_source_id, 0, source_params)
    await MFPGUI().mfp.send(self.working_sink_id, 0, sink_params)
    await MFPGUI().mfp.freewheel(self.working_sink_id, self.buffer_info.size)


@extends(BufferEditor)
async def fx_close_patch(self):
    from mfp.gui_main import MFPGUI

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

        if port % 2 == 0:
            # reconnect previous outputs
            await MFPGUI().mfp.connect(
                self.working_sink_id, port, self.working_aud0_info.get("obj_id"), 0
            )
            await MFPGUI().mfp.disconnect(
                self.fx_patch_id, port, self.working_aud0_info.get("obj_id"), 0
            )
        else:
            await MFPGUI().mfp.connect(
                self.working_sink_id, port, self.working_aud1_info.get("obj_id"), 0
            )
            await MFPGUI().mfp.disconnect(
                self.fx_patch_id, port, self.working_aud1_info.get("obj_id"), 0
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
