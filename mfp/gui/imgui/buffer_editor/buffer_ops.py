"""
buffer_editor/buffer_ops.py -- manipulate the shared mem buffers

Copyright (c) Bill Gribble <grib@billgribble.com>
"""

import asyncio
import os
import numpy as np
from posix_ipc import SharedMemory
from imgui_bundle import implot

from mfp import log
from mfp.gui_main import MFPGUI
from mfp.utils import extends
from mfp.buffer_info import BufferInfo
from .buffer_editor import BufferEditor


########################################
# buffer operations
@extends(BufferEditor)
def buffer_grab(self, shm_obj=None, buffer_info=None):
    if buffer_info is None:
        buffer_info = self.buffer_info

    def offset(channel):
        return channel * buffer_info.size * self.FLOAT_SIZE

    if buffer_info is None:
        return None

    if shm_obj is None:
        if self.shm_obj is None:
            self.shm_obj = SharedMemory(buffer_info.buf_id)
        shm_obj = self.shm_obj

    self.buffer_data = []
    self.channel_selections = [None] * (buffer_info.channels + 1)
    self.channel_selections_active = [False] * (buffer_info.channels + 1)
    self.implot_limits = None
    self.implot_limits_need_set = [None] * (buffer_info.channels + 1)

    try:
        for c in range(buffer_info.channels):
            os.lseek(shm_obj.fd, offset(c), os.SEEK_SET)
            slc = os.read(shm_obj.fd, int(buffer_info.size * self.FLOAT_SIZE))
            self.buffer_data.append(np.fromstring(slc, dtype=np.float32))
    except Exception as e:
        log.debug("[grab]: error grabbing data", e)
        import traceback
        traceback.print_exc()
        return None
    self.buffer_compute_peaks()


@extends(BufferEditor)
def buffer_sync(self, from_obj, from_info, to_obj, to_info, data=None):
    sync_channels = to_info.channels
    if from_info:
        sync_channels = min(from_info.channels, to_info.channels)
    for c in range(sync_channels):
        self.buffer_sync_channel(c, from_obj, from_info, to_obj, to_info, data[c] if data else None)


@extends(BufferEditor)
def buffer_sync_channel(self, channel, from_obj, from_info, to_obj, to_info, data=None):
    def offset(buf_info, channel):
        return channel * buf_info.size * self.FLOAT_SIZE

    if from_obj:
        os.lseek(from_obj.fd, offset(from_info, channel), os.SEEK_SET)
        slc = os.read(from_obj.fd, int(from_info.size * self.FLOAT_SIZE))
    elif data is not None:
        slc = data.tobytes()
    elif len(self.buffer_data) > channel:
        slc = self.buffer_data[channel].tobytes()
    else:
        slc = np.zeros(len(self.buffer_data[0]), dtype=np.float32)

    os.lseek(to_obj.fd, offset(to_info, channel), os.SEEK_SET)
    os.write(to_obj.fd, slc)


@extends(BufferEditor)
def buffer_compute_peaks(self):
    self.buffer_peaks = {}
    padding = 10 - len(self.buffer_data[0]) % 10
    padded = [
        np.pad(chan, (0, padding), mode='constant')
        for chan in self.buffer_data
    ]
    total_time = len(padded[0]) / self.buffer_info.rate
    sample_time = 1/self.buffer_info.rate
    self.implot_total_time = total_time
    self.implot_limits = implot.Rect(
        x_min=0, x_max=total_time, y_min=-1, y_max=1
    )
    self.implot_limits_need_set = [True] * (self.buffer_info.channels + 1)
    self.buffer_peaks["1"] = (
        padded,
        np.arange(0, total_time, sample_time, dtype=np.float32)
    )
    last_peaks = padded

    for peak_factor in (10, 100, 1000, 10000):
        if peak_factor == 10:
            shape = 10
        else:
            shape = 20
        next_peaks = []
        for channel in last_peaks:
            maxima = channel.reshape(-1, shape).max(axis=1)
            minima = channel.reshape(-1, shape).min(axis=1)
            combined = np.ravel(np.column_stack((maxima, minima)))
            padding = 20 - len(combined) % 20
            padded = np.pad(combined, (0, padding), mode='constant')
            next_peaks.append(padded)

        x_values = np.arange(
            0, sample_time * peak_factor * len(padded) / 2,
            peak_factor * sample_time / 2, dtype=np.float32
        )
        self.buffer_peaks[str(peak_factor)] = (
            next_peaks, x_values
        )
        last_peaks = next_peaks


@extends(BufferEditor)
def get_peak_scale(self):
    """
    called within a begin_plot()
    """
    limits = implot.get_plot_limits()
    compress = self.buffer_info.rate * (
        (max(limits.x.max, 1.0) - limits.x.min)
        / self.app_window.canvas_panel_width
    )

    if compress < 10:
        peak_scale = "1"
    elif compress < 100:
        peak_scale = "10"
    elif compress < 1000:
        peak_scale = "100"
    elif compress < 10000:
        peak_scale = "1000"
    else:
        peak_scale = "10000"
    return peak_scale


@extends(BufferEditor)
def buffer_set_selection(self):
    preroll = 0
    xfade = 0

    if "preroll_enum" in self.fx_patch_elements:
        preroll = self.fx_patch_elements.get('preroll_enum').value
        xfade = self.fx_patch_elements.get('xfade_enum').value

    working_buf_info = BufferInfo(
        buf_id=self.working_buf_id,
        size=self.buffer_info.size,
        channels=self.buffer_info.channels + 3,
        rate=self.buffer_info.rate,
        offset=self.buffer_info.offset
    )
    # input level signal
    startpos = int(
        (self.implot_selection.x.min - (preroll / 1000.0)) * self.buffer_info.rate
    )
    endpos = int(
        (self.implot_selection.x.max + (preroll / 1000.0)) * self.buffer_info.rate
    )

    startpos = max(0, startpos)
    endpos = min(self.buffer_info.size, endpos)

    input_arr = np.zeros(self.buffer_info.size, dtype=np.float32)
    input_arr[startpos:endpos] = 1
    self.buffer_sync_channel(
        self.buffer_info.channels + 1, None, None, self.working_buf_obj, working_buf_info,
        data=input_arr
    )

    # crossfade signal
    inramp_start = int(self.implot_selection.x.min * self.buffer_info.rate)
    outramp_end = int(self.implot_selection.x.max * self.buffer_info.rate)

    ramp_len = max(
        0,
        min(
            int((xfade / 1000) * self.buffer_info.rate),
            int((outramp_end - inramp_start) / 2)
        )
    )

    inramp_end = inramp_start + ramp_len
    outramp_start = outramp_end - ramp_len

    xfade_arr = np.zeros(self.buffer_info.size, dtype=np.float32)
    xfade_arr[inramp_start:outramp_end] = 1
    xfade_arr[inramp_start:inramp_end] = np.linspace(0, 1, ramp_len, dtype=np.float32)
    xfade_arr[outramp_start:outramp_end] = np.linspace(1, 0, ramp_len, dtype=np.float32)

    self.buffer_sync_channel(
        self.buffer_info.channels + 2, None, None, self.working_buf_obj, working_buf_info,
        data=xfade_arr
    )


@extends(BufferEditor)
async def buffer_reshape(self, buffer_proc_id, **params):
    # to prevent synchronization errors, we let the buffer resize itself.
    # send it a message, then wait for a signal in response that the buffer
    # has been reshaped.

    event = asyncio.Event()
    new_buf = []

    async def buf_ready(target, signal, bufdata):
        new_buf.append(BufferInfo(**bufdata))
        event.set()
        return False

    handler_id = self.app_window.signal_listen("buffer_ready", buf_ready)

    params["gui_notify"] = True
    await MFPGUI().mfp.send(
        buffer_proc_id, 0, params
    )
    await asyncio.wait_for(event.wait(), 1)

    self.app_window.signal_unlisten(handler_id)

    if len(new_buf) > 0:
        return new_buf[0]
    return None


@extends(BufferEditor)
async def buffer_apply(self):
    # transfer working buffer to origin buffer
    bufsize = len(self.buffer_data[0]) / (self.buffer_info.rate / 1000.0)
    buf_info = await self.buffer_reshape(
        self.buffer_source_info.get('proc_id'),
        channels=self.buffer_info.channels,
        size=bufsize,
        region_start=0,
        region_end=len(self.buffer_data[0]),
        file_name=self.working_buf_info.filename
    )

    buf_id = buf_info.buf_id
    buf_obj = SharedMemory(buf_id)

    self.buffer_sync(None, None, buf_obj, buf_info)
    return True


@extends(BufferEditor)
async def buffer_import(self, filename):
    event = asyncio.Event()
    handler_id = []

    async def buf_ready(target, signal, bufdata):
        self.buffer_data = None
        self.buffer_selected = BufferInfo(**bufdata)
        self.working_buf_id = bufdata.get("buf_id")
        self.working_buf_obj = SharedMemory(self.working_buf_id)
        self.buffer_grab(self.working_buf_obj, self.buffer_selected)
        self.app_window.signal_unlisten(handler_id[0])
        new_chan = self.buffer_selected.channels + 2
        new_size = self.buffer_selected.size / (self.buffer_info.rate / 1000.0)
        working_buf = await self.buffer_reshape(
            self.working_source_id,
            channels=new_chan, 
            size=new_size,
            file_name=filename,
        )
        self.working_buf_id = working_buf.buf_id
        self.working_buf_obj = SharedMemory(self.working_buf_id)
        self.working_buf_info = working_buf

        await self.buffer_reshape(
            self.working_sink_id,
            buf_id=self.working_buf_id,
            channels=new_chan, 
            size=new_size,
            file_name=filename,
        )
        self.buffer_sync(None, None, self.working_buf_obj, working_buf)
        event.set()
        return False

    handler_id.append(self.app_window.signal_listen("buffer_ready", buf_ready))
    await MFPGUI().mfp.send(
        self.working_source_id, 0, filename
    )
    await asyncio.wait_for(event.wait(), 5)


@extends(BufferEditor)
async def buffer_export(self, filename):
    pass
