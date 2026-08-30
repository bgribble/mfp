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

def is_zero(buf):
    ZERO = 0.0001
    for sample in buf:
        if abs(sample) > ZERO:
            return False
    return True

@extends(BufferEditor)
async def clipboard_copy(self):
    if not self.buffer_data or self.implot_selection is None:
        return

    clip_start = int(self.position_to_sample(self.implot_selection.x.min))
    clip_size = int(self.position_to_sample(self.implot_selection.x.max - self.implot_selection.x.min))
    clip_data = [
        chan[clip_start:clip_start+clip_size].copy()
        for chan in self.buffer_data
    ]

    self.clipboard_pos = clip_start
    self.clipboard_size = clip_size
    self.clipboard_data = clip_data


@extends(BufferEditor)
async def clipboard_cut(self):
    if not self.buffer_data or not self.clipboard_pos:
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

    section_start = int(self.position_to_sample(self.implot_selection.x.min))
    section_end = int(self.position_to_sample(self.implot_selection.x.max))

    for chan in self.buffer_data:
        chan[section_start:section_end] = np.zeros(section_end-section_start, dtype=np.float32)

    self.buffer_sync(None, None, self.working_buf_obj, self.working_buf_info)
    self.buffer_compute_peaks()


@extends(BufferEditor)
async def clipboard_delete(self):
    if not self.buffer_data or not self.implot_selection:
        return

    section_start = int(self.position_to_sample(self.implot_selection.x.min))
    section_end = int(self.position_to_sample(self.implot_selection.x.max))

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
        sel_start = int(self.position_to_sample(self.implot_playhead))
        sel_size = 0
    else:
        sel_start = int(self.position_to_sample(self.implot_selection.x.min))
        sel_size = int(self.position_to_sample(self.implot_selection.x.max - self.implot_selection.x.min))

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
async def clipboard_paste__mixing(self):
    """
    Paste clipboard into buffer at selection or playhead.
    - Replace selection if it exists
    - If clipboard is larger than selection, mix tail of clipboard into buffer
    - If pasted clip overflows buffer, expand buffer
    """
    if not self.buffer_data or not self.clipboard_data:
        return

    clip_size = len(self.clipboard_data[0])

    if self.implot_selection is None:
        sel_start = int(self.position_to_sample(self.implot_playhead))
        sel_size = 0
    else:
        sel_start = int(self.position_to_sample(self.implot_selection.x.min))
        sel_size = int(self.position_to_sample(self.implot_selection.x.max - self.implot_selection.x.min))

    delta_len = sel_start + clip_size - len(self.buffer_data[0])

    # make room at end if needed
    if delta_len > 0:
        self.buffer_data = [
            np.append(chan, np.zeros(delta_len))
            for chan in self.buffer_data
        ]

    # copy the selection portion
    clip_consumed = 0
    if self.implot_selection is not None:
        clip_consumed = min(clip_size, sel_size)
        sel_end = sel_start + clip_consumed
        for chan_num, chan in enumerate(self.buffer_data):
            chan[sel_start:sel_start + sel_size] = 0
            chan[sel_start:sel_end] = self.clipboard_data[chan_num][:min(clip_size, sel_size)]

    # the overlap or extended region (non-selected)
    dest_begin = sel_start + clip_consumed
    dest_end = sel_start + clip_size
    src_begin = clip_consumed
    src_end = clip_size

    for chan_num, chan in enumerate(self.buffer_data):
        chan[dest_begin:dest_end] += self.clipboard_data[chan_num][src_begin:src_end]

    # resize the buffer object if needed
    if delta_len > 0:
        bufsize_ms = len(self.buffer_data[0]) / (self.buffer_info.rate / 1000.0)

        # source buffer "owns" the reshape
        working_buf = await self.buffer_reshape(
            self.working_source_id,
            size=bufsize_ms,
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
                size=bufsize_ms,
                channels=working_buf.channels
            )

        self.implot_selection = None

    # sync data back to working buffer
    self.buffer_sync(None, None, self.working_buf_obj, self.working_buf_info)
    self.buffer_compute_peaks()


@extends(BufferEditor)
async def clipboard_paste_to_fit__resample(self):
    import resampy

    if not self.buffer_data or self.implot_selection is None:
        return

    sel_start = max(0, int(self.position_to_sample(self.implot_selection.x.min)))
    sel_size = min(
        int(self.position_to_sample(self.implot_selection.x.max) - sel_start),
        self.buffer_info.size - sel_start
    )

    new_data = [
        resampy.resample(chan_data, 48000, 48000 * (sel_size / self.clipboard_size))
        for chan_data in self.clipboard_data
    ]

    new_buffer = []
    for chan_num, chan in enumerate(self.buffer_data):
        chan[sel_start:sel_start+sel_size] = np.zeros(sel_size, dtype=np.float32)
        chan[sel_start:sel_start+len(new_data[chan_num])] = new_data[chan_num]
        new_buffer.append(chan)

    self.buffer_data = new_buffer
    self.buffer_sync(None, None, self.working_buf_obj, self.working_buf_info)
    self.buffer_compute_peaks()


@extends(BufferEditor)
async def clipboard_paste_to_fit__stretch(self):
    import paulstretch

    if not self.buffer_data or self.implot_selection is None:
        return

    sel_start = int(self.position_to_sample(self.implot_selection.x.min))
    sel_size = min(
        int(self.position_to_sample(self.implot_selection.x.max) - sel_start),
        self.buffer_info.size - sel_start
    )

    new_data = [
        paulstretch.stretch(chan_data, stretch_factor=sel_size / self.clipboard_size)
        for chan_data in self.clipboard_data
    ]
    new_data_len = min(len(new_data[0]), self.buffer_info.size - sel_start)

    for chan_num, chan in enumerate(self.buffer_data):
        chan[sel_start:sel_start+sel_size] = np.zeros(sel_size, dtype=np.float32)
        chan[sel_start:sel_start+new_data_len] = new_data[chan_num][:new_data_len].squeeze()

    self.buffer_sync(None, None, self.working_buf_obj, self.working_buf_info)
    self.buffer_compute_peaks()
