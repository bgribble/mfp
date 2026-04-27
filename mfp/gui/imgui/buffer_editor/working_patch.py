"""
buffer_editor/working_patch.py -- set up and teardown the internal patch

Copyright (c) Bill Gribble <grib@billgribble.com>
"""

import asyncio

from posix_ipc import SharedMemory
from mfp import log
from mfp.utils import extends
from .buffer_editor import BufferEditor


@extends(BufferEditor)
async def init_working_patch(self):
    """
    The working patch has 2 buffer~ objects that are the source and
    sink for FX chains, sharing the same underlying working shm buffer.

    They are different numbers of channels, which is ugly but should work.

    * the first N channels of each are the equivalent channels of the original
    buffer

    * the next channel is the trigger channel, same for both buffer~, which should
    never be recorded to (it's just used as a live input)

    * the source buffer has 2 more channels: the input level and xfade level.
    These are not recorded from the inputs but are just written to through the
    shared memory from Python and played from the source buffer to the FX chain.
    """
    from mfp.gui_main import MFPGUI
    if self.working_patch_id:
        await self.close_working_patch()

    self.working_patch_id = await MFPGUI().mfp.open_file(None, show_gui=False)
    self.working_patch_info = await MFPGUI().mfp.get_tooltip_info(
        self.working_patch_id, details=True
    )
    buffer_params = dict(
        channels=self.buffer_info.channels + 3,
        trig_chan=self.buffer_info.channels,
        size=self.buffer_info.size,
        gui_notify=True,
    )

    self.working_source_info = await MFPGUI().mfp.create(
        "buffer~",
        ", ".join([f"{key}={value!r}" for key, value in buffer_params.items()]),
        self.working_patch_info.get("name"),
        None,
        "source_buffer"
    )
    self.working_source_id = self.working_source_info.get("obj_id")

    # wait for buffer to be initialized
    source = None
    while source is None:
        try:
            all_buffers = await MFPGUI().mfp.get_buffer_info()
            source = next(b for b in all_buffers if b.get("proc_name") == "source_buffer")
        except StopIteration:
            await asyncio.sleep(0.1)

    source_buf = source.get("buf_info")
    source_buf.file_name = self.buffer_info.file_name
    self.working_source_info['name'] = self.buffer_source_info['proc_name']

    self.working_buf_id = source_buf.buf_id
    self.working_buf_obj = SharedMemory(source_buf.buf_id)
    self.working_buf_info = source_buf

    buffer_params["buf_id"] = source_buf.buf_id
    buffer_params["channels"] = source_buf.channels + 1
    buffer_params["size"] = source_buf.size

    self.working_sink_info = await MFPGUI().mfp.create(
        "buffer~",
        ", ".join([f"{key}={value!r}" for key, value in buffer_params.items()]),
        self.working_patch_info.get("name"),
        None,
        "sink_buffer"
    )
    self.working_sink_id = self.working_sink_info.get("obj_id")

    self.working_aud0_info = await MFPGUI().mfp.create(
        "out~", "0", self.working_patch_info.get("name"), None, "audition 0"
    )
    self.working_aud1_info = await MFPGUI().mfp.create(
        "out~", "1", self.working_patch_info.get("name"), None, "audition 1"
    )

    # connect a sig~ to the source and sink triggers for synchronization
    self.working_trigger_info = await MFPGUI().mfp.create(
        "sig~", "0", self.working_patch_info.get("name"), None, "buffer trigger"
    )
    self.working_trigger_id = self.working_trigger_info.get("obj_id")
    await MFPGUI().mfp.connect(
        self.working_trigger_id, 0,
        self.working_source_id, self.buffer_info.channels,
    )
    await MFPGUI().mfp.connect(
        self.working_trigger_id, 0,
        self.working_sink_id, self.buffer_info.channels,
    )

    for port in range(self.buffer_info.channels):
        if port % 2 == 0:
            await MFPGUI().mfp.connect(self.working_sink_id, port, self.working_aud0_info.get("obj_id"), 0)
        else:
            await MFPGUI().mfp.connect(self.working_sink_id, port, self.working_aud1_info.get("obj_id"), 0)

    self.buffer_sync(self.shm_obj, self.buffer_info, self.working_buf_obj, source_buf)
    self.buffer_compute_peaks()


@extends(BufferEditor)
async def close_working_patch(self):
    from mfp.gui_main import MFPGUI

    # FIXME delete shared mem segment

    if self.working_patch_id:
        await MFPGUI().mfp.delete(self.working_patch_id)
        self.working_patch_id = None
