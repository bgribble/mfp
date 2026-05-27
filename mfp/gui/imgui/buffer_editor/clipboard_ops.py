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
    if not self.buffer_data or self.implot_selection is None:
        return

    clip_start = int(self.implot_selection.x.min * self.buffer_info.rate)
    clip_size = int((self.implot_selection.x.max - self.implot_selection.x.min) * self.buffer_info.rate)
    clip_data = [
        chan[clip_start:clip_start+clip_size]
        for chan in self.buffer_data
    ]

    self.clipboard_pos = clip_start
    self.clipboard_size = clip_size
    self.clipboard_data = clip_data


@extends(BufferEditor)
async def clipboard_cut(self):
    if not self.buffer_data:
        return

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


@extends(BufferEditor)
async def clipboard_clear(self):
    if not self.buffer_data or not self.implot_selection:
        return

    section_start = int(self.implot_selection.x.min * self.buffer_info.rate)
    section_end = int(self.implot_selection.x.max * self.buffer_info.rate)

    for chan in self.buffer_data:
        chan[section_start:section_end] = np.zeros(section_end-section_start, dtype=np.float32)

    self.buffer_sync(None, None, self.working_buf_obj, self.working_buf_info)
    self.buffer_compute_peaks()


@extends(BufferEditor)
async def clipboard_delete(self):
    if not self.buffer_data or not self.implot_selection:
        return

    section_start = int(self.implot_selection.x.min * self.buffer_info.rate)
    section_end = int(self.implot_selection.x.max * self.buffer_info.rate)

    self.buffer_data = [
        np.delete(chan, np.s_[section_start:section_end])
        for chan in self.buffer_data
    ]

    self.buffer_sync(None, None, self.working_buf_obj, self.working_buf_info)
    self.buffer_compute_peaks()

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

    # sink buffer just needs to point to the new segment and
    # adjust internal buffers
    if working_buf:
        await self.buffer_reshape(
            self.working_sink_id,
            buf_id=working_buf.buf_id,
            size=bufsize,
            channels=working_buf.channels
        )

    self.implot_selection = None


@extends(BufferEditor)
async def clipboard_paste(self):
    if not self.buffer_data or not self.clipboard_data:
        return

    clip_size = len(self.clipboard_data[0])

    if self.implot_selection is None:
        sel_start = int(self.implot_playhead * self.buffer_info.rate)
        sel_size = 0
        sel_data = []
    else:
        sel_start = int(self.implot_selection.x.min * self.buffer_info.rate)
        sel_size = int((self.implot_selection.x.max - self.implot_selection.x.min) * self.buffer_info.rate)
        sel_data = [
            chan[sel_start:sel_start+sel_size]
            for chan in self.buffer_data
        ]

    delta_len = clip_size - sel_size

    if delta_len > 0:
        self.buffer_data = [
            np.insert(chan, sel_start, np.zeros(delta_len))
            for chan in self.buffer_data
        ]
    elif delta_len < 0:
        self.buffer_data = [
            np.delete(chan, np.s_[sel_start:sel_start - delta_len])
            for chan in self.buffer_data
        ]

    if delta_len != 0:
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

        # sink buffer just needs to point to the new segment and
        # adjust internal buffers
        if working_buf:
            await self.buffer_reshape(
                self.working_sink_id,
                buf_id=working_buf.buf_id,
                size=bufsize,
                channels=working_buf.channels
            )

        self.implot_selection = None

    for chan_number, chan in enumerate(self.buffer_data):
        chan[sel_start:sel_start+clip_size] = self.clipboard_data[chan_number]

    self.buffer_sync(None, None, self.working_buf_obj, self.working_buf_info)
    self.buffer_compute_peaks()


@extends(BufferEditor)
async def clipboard_paste_to_fit(self):
    import resampy

    if not self.buffer_data or self.implot_selection is None:
        return

    sel_start = max(0, int(self.implot_selection.x.min * self.buffer_info.rate))
    sel_size = min(
        int((self.implot_selection.x.max - self.implot_selection.x.min) * self.buffer_info.rate),
        self.buffer_info.size - sel_start
    )
    sel_data = [
        chan[sel_start:sel_start+sel_size]
        for chan in self.buffer_data
    ]

    log.debug(f"[stretch] resampling from {self.clipboard_size} to {sel_size}")
    new_data = [
        resampy.resample(chan_data, self.clipboard_size, sel_size)
        for chan_data in self.clipboard_data
    ]
    log.debug(f"[stretch] resampled size={len(new_data[0])}")

    for chan_num, chan in enumerate(self.buffer_data):
        chan[sel_start:sel_start+sel_size] = new_data[chan_num]

    self.buffer_sync(None, None, self.working_buf_obj, self.working_buf_info)
    self.buffer_compute_peaks()
