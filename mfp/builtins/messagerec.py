#! /usr/bin/env python
'''
builtins/messagerec.py: Record/playback for message sequences

Copyright (c) Bill Grbble <grib@billgribble.com>
'''

from datetime import datetime
from mfp import log
from mfp.bang import Uninit
from mfp.processor import Processor, MultiOutput
from ..mfp_app import MFPApp


class MessageRec(Processor):
    doc_tooltip_obj = "Message recorder"
    doc_tooltip_inlet = ["Values/control", "Clock"]
    doc_tooltip_outlet = ["Value output"]

    def __init__(self, init_type, init_args, patch, scope, name, defs=None):
        Processor.__init__(self, 2, 1, init_type, init_args, patch, scope, name, defs)
        extra = defs or {}
        _, _ = self.parse_args(init_args, **extra)

        self.messages = []
        self.clock_tempo_ts_timestamp = None
        self.clock_tempo_ts_beat = None
        self.clock_tempo_ms = None
        self.clock_beat = 0
        self.rec_state = False
        self.play_state = True
        self.play_state = False
        self.hot_inlets = (0, 1)

    # methods callable by messages on inlet 0
    def record(self, new_state=True):
        self.rec_state = new_state

    def clear(self):
        self.messages = []

    def play(self):
        self.play_state = True

    def stop(self):
        self.play_state = False

    async def trigger(self):
        rightnow = datetime.now()
        beatnow = self.clock_beat or 0

        if self.inlets[1] is not Uninit:
            if isinstance(self.inlets[1], (float, int)):
                self.clock_beat = self.inlets[1]
            else:
                self.clock_beat += 1

            if self.clock_tempo_ts_timestamp is None:
                self.clock_tempo_ts_timestamp = rightnow
                self.clock_tempo_ts_beat = self.clock_beat
            else:
                delta_beats = self.clock_beat - self.clock_tempo_ts_beat
                if delta_beats > 0:
                    self.clock_tempo_ms = (
                        1000 * (rightnow - self.clock_tempo_ts_timestamp).total_seconds() / delta_beats
                    )
                self.clock_tempo_ts_timestamp = rightnow
                self.clock_tempo_ts_beat = self.clock_beat
            self.inlets[1] = Uninit

        if self.inlets[0] is not Uninit:
            self.messages.append((self.clock_beat, rightnow, self.inlets[0]))
            self.messages.sort()
            self.inlets[0] = Uninit

        if self.clock_beat < beatnow:
            beatnow = -1

        pending = [
            m[2] for m in self.messages
            if m[0] > beatnow and m[0] <= self.clock_beat
        ]

        if not pending:
            return

        if len(pending) == 1:
            self.outlets[0] = pending[0]
        else:
            self.outlets[0] = MultiOutput(pending)


def register():
    MFPApp().register("messagerec", MessageRec)
