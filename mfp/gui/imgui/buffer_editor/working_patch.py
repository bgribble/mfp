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
    from mfp.gui_main import MFPGUI
    if self.working_patch_id:
        await self.close_working_patch()

    self.working_patch_id = await MFPGUI().mfp.open_file(None, show_gui=False)
    self.working_patch_info = await MFPGUI().mfp.get_tooltip_info(
        self.working_patch_id, details=True
    )
    buffer_params = dict(
        channels=self.buffer_info.channels + 2,
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
    buffer_params["channels"] = source_buf.channels
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
    await MFPGUI().mfp.connect(self.working_sink_id, 0, self.working_aud0_info.get("obj_id"), 0)
    await MFPGUI().mfp.connect(self.working_sink_id, 1, self.working_aud1_info.get("obj_id"), 0)

    self.buffer_sync(self.shm_obj, self.buffer_info, self.working_buf_obj, source_buf)
    self.buffer_compute_peaks()


@extends(BufferEditor)
async def close_working_patch(self):
    from mfp.gui_main import MFPGUI

    if self.working_patch_id:
        await MFPGUI().mfp.delete(self.working_patch_id)
        self.working_patch_id = None
