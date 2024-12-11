#! /usr/bin/env python
'''
buffer.py:  Builtin POSIX shared memory buffer

Copyright (c) Bill Gribble <grib@billgribble.com>
'''

import os
import asyncio
from threading import Thread

from posix_ipc import SharedMemory

import numpy
from mfp import Bang
from mfp import log

from mfp.processor import Processor
from ..mfp_app import MFPApp
from ..buffer_info import BufferInfo


class Buffer(Processor):

    RESP_TRIGGERED = 0
    RESP_BUFID = 1
    RESP_BUFSIZE = 2
    RESP_BUFCHAN = 3
    RESP_RATE = 4
    RESP_OFFSET = 5
    RESP_BUFRDY = 6
    RESP_LOOPSTART = 7

    FLOAT_SIZE = 4

    doc_tooltip_obj = "Load or capture an audio signal in a shared buffer"
    doc_tooltip_inlet = ["Signal input/control messages"]
    doc_tooltip_outlet = [
        "Signal output",
        "Array output (for @slice)",
        "BufferInfo and status output"
    ]

    def __init__(self, init_type, init_args, patch, scope, name):
        initargs, kwargs = patch.parse_args(init_args)

        self.init_size = 0
        self.init_channels = 1

        if len(initargs):
            self.init_size = initargs[0]*MFPApp().samplerate/1000.0
        if len(initargs) > 1:
            self.init_channels = initargs[1]
        if "channels" in kwargs:
            self.init_channels = kwargs["channels"]

        Processor.__init__(
            self, self.init_channels, self.init_channels+2, init_type, init_args,
            patch, scope, name
        )

        self.buf_id = None
        self.buf_offset = 0
        self.channels = 0
        self.size = 0
        self.rate = None
        self.shm_obj = None

        self.file_name = None
        self.file_channels = None
        self.file_samplerate = None
        self.file_len = None
        self.file_data = None
        self.file_ready = False

        self.dsp_inlets = list(range(self.init_channels))
        self.dsp_outlets = list(range(self.init_channels))

    async def setup(self):
        await self.dsp_init("buffer~", size=self.init_size, channels=self.init_channels)

    def offset(self, channel, start):
        return (channel * self.size + start) * self.FLOAT_SIZE

    async def _init_file_read(self):
        ready = asyncio.Event()

        def _read_helper():
            import soundfile as sf
            self.file_ready = False
            data, samplerate = sf.read(self.file_name)
            self.file_channels = len(data.shape)
            self.file_len = data.shape[0]
            self.file_samplerate = samplerate
            self.file_data = data.astype(numpy.float32)
            self.file_ready = True
            ready.set()

        thread = Thread(target=_read_helper)
        thread.start()
        await ready.wait()
        thread.join()

        await self.dsp_setparam("channels", self.file_channels)
        await self.dsp_setparam("size", self.file_len)

    def _transfer_file_data(self):
        if self.shm_obj is None:
            self.shm_obj = SharedMemory(self.buf_id)

        for channel in range(self.file_channels):
            if self.file_channels == 1:
                byte_data = self.file_data.tobytes()
            else:
                byte_data = self.file_data[:, channel].tobytes()

            os.lseek(self.shm_obj.fd, self.offset(channel, 0), os.SEEK_SET)
            os.write(self.shm_obj.fd, byte_data)

    def dsp_response(self, resp_id, resp_value):
        if resp_id in (self.RESP_TRIGGERED, self.RESP_LOOPSTART):
            self.outlets[2] = resp_value
        elif resp_id == self.RESP_BUFID:
            if self.shm_obj:
                self.shm_obj.close_fd()
                self.shm_obj = None
            self.buf_id = resp_value
        elif resp_id == self.RESP_BUFSIZE:
            self.size = resp_value
        elif resp_id == self.RESP_BUFCHAN:
            self.channels = resp_value
        elif resp_id == self.RESP_RATE:
            self.rate = resp_value
        elif resp_id == self.RESP_OFFSET:
            self.buf_offset = resp_value
        elif resp_id == self.RESP_BUFRDY:
            self.outlets[2] = BufferInfo(
                buf_id=self.buf_id,
                size=self.size,
                channels=self.channels,
                rate=self.rate,
                offset=self.buf_offset
            )
            if self.file_ready:
                self.file_ready = False
                self._transfer_file_data()
        self.outlets[2] = (resp_id, resp_value)

    async def trigger(self):
        incoming = self.inlets[0]
        if incoming is Bang:
            await self.dsp_obj.setparam("buf_state", 1)
        elif incoming is True:
            await self.dsp_obj.setparam("rec_enabled", 1)
        elif incoming is False:
            await self.dsp_obj.setparam("rec_enabled", 0)
        elif isinstance(incoming, str):
            self.file_name = incoming
            await self._init_file_read()
        elif isinstance(incoming, dict):
            for k, v in incoming.items():
                if k == "size":
                    v = v*MFPApp().samplerate/1000.0
                setattr(self, k, v)
                await self.dsp_obj.setparam(k, v)

    def slice(self, start, end, channel=0):
        """
        @slice() outputs some audio data as a message
        """
        if self.shm_obj is None:
            self.shm_obj = SharedMemory(self.buf_id)

        if start < 0:
            start = 0
        if start >= self.size:
            start = self.size-1
        if end < 0:
            end = 0

        if end >= self.size:
            end = self.size-1

        try:
            os.lseek(self.shm_obj.fd, self.offset(channel, start), os.SEEK_SET)
            slc = os.read(self.shm_obj.fd, (end - start) * self.FLOAT_SIZE)
            self.outlets[1] = list(numpy.fromstring(slc, dtype=numpy.float32))
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            log.debug("buffer~: slice error '%s" % e)
            self.error(tb)
            return None

    def bufinfo(self):
        self.outlets[2] = BufferInfo(
            buf_id=self.buf_id,
            size=self.size,
            channels=self.channels,
            rate=self.rate,
            offset=self.buf_offset
        )


def register():
    MFPApp().register("buffer~", Buffer)
