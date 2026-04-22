"""
buffer_editor/clipboard_ops.py -- manipulate the clipboard

Copyright (c) Bill Gribble <grib@billgribble.com>
"""

from posix_ipc import SharedMemory
import numpy as np

from mfp import log
from mfp.utils import extends
from mfp.buffer_info import BufferInfo
from .buffer_editor import BufferEditor


@extends(BufferEditor)
async def clipboard_copy(self):
    if self.implot_selection is None:
        return

    clip_start = int(self.implot_selection.x.min * self.buffer_info.rate)
    clip_size = int((self.implot_selection.x.max - self.implot_selection.x.min) * self.buffer_info.rate)
    clip_data = self.buffer_data[clip_start:clip_start+clip_size]

    self.clipboard_pos = clip_start
    self.clipboard_size = clip_size
    self.clipboard_data = clip_data


@extends(BufferEditor)
async def clipboard_cut(self):
    await self.clipboard_copy()

    self.buffer_data = [
        np.delete(chan, np.s_[self.clipboard_pos:self.clipboard_pos + self.clipboard_size])
        for chan in self.buffer_data
    ]

    bufsize = len(self.buffer_data[0]) / (self.buffer_info.rate / 1000.0)

    # source buffer "owns" the reshape
    working_buf = await self.buffer_reshape(
        self.working_source_id,
        size=bufsize,
        channels=len(self.buffer_data) + 2
    )
    self.working_buf_id = working_buf.buf_id
    self.working_buf_obj = SharedMemory(self.working_buf_id)
    self.working_buf_info = working_buf

    self.buffer_sync(None, None, self.working_buf_obj, self.working_buf_info)

    # sink buffer just needs to point to the new segment and
    # adjust internal buffers
    if working_buf:
        await self.buffer_reshape(
            self.working_sink_id,
            buf_id=working_buf.buf_id,
            size=bufsize,
            channels=working_buf.channels
        )

    self.buffer_compute_peaks()
    self.implot_selection = None

