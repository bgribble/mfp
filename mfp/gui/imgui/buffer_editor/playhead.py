"""
playhead.py -- playhead-related helpers for BufferEditor

Copyright (c) Bill Gribble <grib@billgribble.com>
"""

import asyncio
from datetime import datetime
import math
import numpy as np
from posix_ipc import SharedMemory
from imgui_bundle import implot

from mfp import log
from mfp.utils import extends
from .buffer_editor import BufferEditor


@extends(BufferEditor)
async def playhead_start(self):
    from mfp.gui_main import MFPGUI
    pos_samples = self.position_to_sample(self.implot_playhead)
    rec_channels = self.channel_options_rec_mask()

    buffer_params = dict(
        buf_mode=7,
        play_channels=0xff,
        rec_channels=0,
        monitor_channels=rec_channels,
        buf_pos=pos_samples,
        region_start=pos_samples,
        region_end=self.position_to_sample(self.implot_total_time)
    )
    await MFPGUI().mfp.send(self.working_source_id, 0, buffer_params)

    if self.rec_enabled:
        buffer_params["buf_mode"] = 3
        buffer_params["rec_channels"] = rec_channels
        buffer_params["rec_enabled"] = 1
        self.rec_recording = True
    else:
        buffer_params["rec_channels"] = 0
        buffer_params["rec_enabled"] = 0
        self.rec_recording = False

    buffer_params["monitor_channels"] = 0xff

    await MFPGUI().mfp.send(self.working_sink_id, 0, buffer_params)
    await asyncio.sleep(0.1)
    await MFPGUI().mfp.send(self.working_trigger_id, 0, 1)

    self.implot_playhead_start_time = datetime.now()
    self.implot_playhead_start_pos = self.implot_playhead
    self.implot_playhead_looping = False


@extends(BufferEditor)
async def playhead_move(self, new_pos):
    from mfp.gui_main import MFPGUI
    self.implot_playhead = new_pos
    pos_samples = self.position_to_sample(self.implot_playhead)

    buffer_params = dict(
        buf_pos=pos_samples
    )

    await MFPGUI().mfp.send(self.working_sink_id, 0, buffer_params)
    await MFPGUI().mfp.send(self.working_source_id, 0, buffer_params)

    if self.implot_playhead_start_time:
        self.implot_playhead_start_time = datetime.now()
        self.implot_playhead_start_pos = self.implot_playhead


@extends(BufferEditor)
async def playhead_pause(self, new_pos=None):
    from mfp.gui_main import MFPGUI
    buffer_params = dict(
        buf_state=0,
    )

    await MFPGUI().mfp.send(self.working_trigger_id, 0, 0)
    await MFPGUI().mfp.send(self.working_sink_id, 0, buffer_params)
    await MFPGUI().mfp.send(self.working_source_id, 0, buffer_params)

    if self.rec_recording:
        need_update = 0
        now = datetime.now()
        if not self.rec_recording_updated:
            need_update = 1
        else:
            tdelta = (now - self.rec_recording_updated).total_seconds()
            if tdelta > 2:
                need_update = 1
        if need_update:
            self.rec_recording_updated = now
            self.buffer_grab(self.working_buf_obj)

    self.implot_playhead_start_time = None
    self.implot_playhead_looping = False
    self.rec_recording = False

    if new_pos is not None:
        await self.playhead_move(new_pos)


@extends(BufferEditor)
async def playhead_set_selection(self, sel_start, sel_end):
    if not self.implot_selection:
        self.implot_selection = implot.Rect(
            0, 0, -1, 1
        )
    if sel_start is not None:
        self.implot_selection.x.min = sel_start
    if sel_end is not None:
        self.implot_selection.x.max = sel_end

    return await self.playhead_update_selection()


@extends(BufferEditor)
async def playhead_update_selection(self):
    from mfp.gui_main import MFPGUI
    start_samples = self.position_to_sample(self.implot_selection.x.min)
    end_samples = self.position_to_sample(self.implot_selection.x.max)
    buffer_params = dict(
        region_start=start_samples,
        region_end=end_samples
    )
    if self.implot_playhead_looping:
        if self.implot_playhead < self.implot_selection.x.min:
            self.implot_playhead = self.implot_selection.x.min
            buffer_params['buf_pos'] = self.position_to_sample(self.implot_playhead)
        elif self.implot_playhead >= self.implot_selection.x.max:
            self.implot_playhead = self.implot_selection.x.max
            buffer_params['buf_pos'] = self.position_to_sample(self.implot_playhead)
        await MFPGUI().mfp.send(self.working_sink_id, 0, buffer_params)
        await MFPGUI().mfp.send(self.working_source_id, 0, buffer_params)

    if self.implot_playhead_start_time:
        self.implot_playhead_start_time = datetime.now()
        self.implot_playhead_start_pos = self.implot_playhead

    self.buffer_set_selection()


@extends(BufferEditor)
async def playhead_loop_selection(self):
    from mfp.gui_main import MFPGUI
    start_samples = self.position_to_sample(self.implot_selection.x.min)
    end_samples = self.position_to_sample(self.implot_selection.x.max)

    buffer_params = dict(
        buf_mode=6,
        play_channels=0xff,
        rec_channels=0,
        monitor_channels=0,
        region_start=start_samples,
        region_end=end_samples
    )

    if not self.implot_playhead_start_time:
        self.implot_playhead_start_time = datetime.now()
        self.implot_playhead = self.implot_selection.x.min
        self.implot_playhead_start_pos = self.implot_selection.x.min
        buffer_params["buf_pos"] = start_samples

    await MFPGUI().mfp.send(self.working_source_id, 0, buffer_params)

    buffer_params["monitor_channels"] = 0xff

    await MFPGUI().mfp.send(self.working_sink_id, 0, buffer_params)
    await asyncio.sleep(0.1)
    await MFPGUI().mfp.send(self.working_trigger_id, 0, 1)

    self.implot_playhead_looping = True
    self.rec_recording = False


@extends(BufferEditor)
async def playhead_toggle_record(self):
    from mfp.gui_main import MFPGUI
    self.rec_enabled = int(not self.rec_enabled)
    rec_channels = self.channel_options_rec_mask()

    # turn on record mode for sink only if we are "rolling"
    if self.implot_playhead_start_time:
        buffer_params = dict(
            buf_mode=3 if self.rec_enabled else 7,
            rec_channels=rec_channels if self.rec_enabled else 0,
            monitor_channels=0xff,
            rec_enabled=1 if self.rec_enabled else 0,
        )
        await MFPGUI().mfp.send(self.working_sink_id, 0, buffer_params)
        self.rec_recording = bool(rec_channels) and self.rec_enabled


@extends(BufferEditor)
async def playhead_select_silence(self, thresh_db):
    """
    Select silence around playhead
    """
    def level(ind):
        absmax = max(chan[ind] for chan in (self.buffer_data or []))
        absmax = max(absmax, 1e-6)
        return 20 * math.log10(absmax)

    ph = int(self.position_to_sample(self.implot_playhead))

    pos_fwd = ph
    while pos_fwd < self.buffer_info.size and level(pos_fwd) <= thresh_db:
        pos_fwd += 1

    pos_rev = ph
    while pos_rev >= 0 and level(pos_rev) <= thresh_db:
        pos_rev -= 1

    await self.playhead_set_selection(
        self.sample_to_position(pos_rev),
        self.sample_to_position(pos_fwd)
    )


@extends(BufferEditor)
async def playhead_insert_data(self, data):
    if not len(self.buffer_data) or data is None or not len(data):
        return

    sel_start = int(self.position_to_sample(self.implot_playhead))

    self.buffer_data = [
        np.insert(chan, sel_start, data)
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

    # sink buffer just needs to point to the new segment and
    # adjust internal buffers
    if working_buf:
        await self.buffer_reshape(
            self.working_sink_id,
            buf_id=working_buf.buf_id,
            size=bufsize,
            channels=working_buf.channels
        )

    self.buffer_sync(None, None, self.working_buf_obj, self.working_buf_info)
    self.buffer_compute_peaks()
