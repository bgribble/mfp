#! /usr/bin/env python
'''
metro.py: Metronome control processor

Copyright (c) 2010-2016 Bill Gribble <grib@billgribble.com>
'''

from ..timer import MultiTimer
from ..processor import Processor
from ..mfp_app import MFPApp
from datetime import datetime, timedelta
from .. import Bang, Uninit
from mfp import log

from .metro import TimerTick

class Replay (Processor):
    doc_tooltip_obj = "Basic event record/playback"
    doc_tooltip_inlet = ["Event input"]
    doc_tooltip_outlet = ["Event output"]

    _timer = None

    def __init__(self, init_type, init_args, patch, scope, name):
        Processor.__init__(self, 1, 1, init_type, init_args, patch, scope, name)

        self.buffer = []
        self.playing = False
        self.playing_start = None
        self.recording = False
        self.recording_start = None
        self.loop_length = None

        self.playing_ids = []

        if Replay._timer is None:
            Replay._timer = MultiTimer()
            Replay._timer.start()

        parsed_args, kwargs = self.parse_args(init_args)

    def record(self):
        self.recording = True
        self.recording_start = datetime.now()

    def record_stop(self):
        self.loop_length = datetime.now() - self.recording_start
        self.recording = False
        self.recording_start = None

    def play(self):
        if self.playing:
            self.play_stop()

        self.playing = True
        self.playing_start = datetime.now()
        for payload, delta in self.buffer: 
            item_id = self._timer.schedule(
                self.playing_start + delta, 
                self.timer_cb, 
                [payload]
            )
            self.playing_ids.append(item_id)
    
    def loop(self, data=None):
        self.play()
        if self.loop_length is None:
            return

        loop_id = self._timer.schedule(
            self.playing_start + self.loop_length,
            self.loop,
            [])
        self.playing_ids.append(loop_id)

    def play_stop(self):
        self.playing = False
        ids = self.playing_ids
        self.playing_ids = []
        for item in ids:
            self._timer.cancel(item)

    def clear(self):
        self.play_stop()
        self.buffer = []

    async def trigger(self):
        if isinstance(self.inlets[0], TimerTick):
            self.outlets[0] = self.inlets[0].payload
        elif self.recording:
            event_delta = datetime.now() - self.recording_start
            log.debug("[replay] recording", self.inlets[0], event_delta)
            self.buffer.append(
                [self.inlets[0], event_delta]
            )
            if self.playing:
                item = self._timer.schedule(
                    self.playing_start + event_delta, 
                    self.timer_cb, 
                    [self.inlets[0]]
                )
                self.playing_ids.append(item)
            self.started = False

    def timer_cb(self, data):
        self.send(TimerTick(data))

    def show_buffer(self):
        log.debug(self.buffer)

def register():
    MFPApp().register("replay", Replay)

