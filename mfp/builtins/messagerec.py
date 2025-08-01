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
        self.clock_tick_ms = None
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
        clock_starting = self.clock_beat or 0

        if self.inlets[1] is not Uninit:
            if isinstance(self.inlets[1], (float, int)):
                self.clock_beat = self.inlets[1]
            else:
                self.clock_beat += 1

            if self.clock_tempo_ts_timestamp is None:
                self.clock_tick_ms = 0
                self.clock_tempo_ts_timestamp = rightnow
                self.clock_tempo_ts_beat = self.clock_beat
            else:
                self.clock_tick_ms = (rightnow - self.clock_tempo_ts_timestamp).total_seconds() * 1000
                delta_beats = self.clock_beat - self.clock_tempo_ts_beat
                if delta_beats > 0:
                    self.clock_tempo_ms = (
                        1000 * (rightnow - self.clock_tempo_ts_timestamp).total_seconds() / delta_beats
                    )
                self.clock_tempo_ts_timestamp = rightnow
                self.clock_tempo_ts_beat = self.clock_beat
            self.inlets[1] = Uninit

        newevent = None
        if self.inlets[0] is not Uninit:
            beat_fraction = 0
            if self.clock_tempo_ms:
                ms_since_clock = 1000 * (rightnow - self.clock_tempo_ts_timestamp).total_seconds()
                if self.clock_tempo_ts_beat != self.clock_beat:
                    ms_since_clock = (
                        ms_since_clock
                        + self.clock_tempo_ms * (self.clock_tempo_ts_beat - self.clock_beat)
                    )
                beat_fraction = ms_since_clock / self.clock_tempo_ms
            newevent = (self.clock_beat + beat_fraction, rightnow, self.inlets[0])
            self.messages.append(newevent)
            self.messages.sort()
            self.inlets[0] = Uninit

        # we want to emit any events that are "due" when quantized to
        # the current clock. To make this sound natural, we want to
        # look ahead in time to find events that aren't due yet but will
        # be due well before the next clock (ones that were likely "late" when
        # recorded)
        fudge = 0
        if self.clock_tick_ms and self.clock_tempo_ms:
            # fudge factor is .1 of a clock tick. This is quite conservative,
            # could probably be as much as .5
            fudge = 0.1 * self.clock_tick_ms / self.clock_tempo_ms

        def test_beat(beat):
            if self.clock_beat > clock_starting:
                # normal case: clock is moving forward
                return (
                    clock_starting < beat <= (self.clock_beat + fudge)
                )
            else:
                # edge case: clock wrapped around
                return (
                    (beat > clock_starting and beat <= clock_starting + 1)
                    or beat <= (self.clock_beat + fudge)
                )

        pending = [
            m for m in self.messages
            if test_beat(m[0]) or (m == newevent and m[0] == clock_starting)
        ]

        if not pending:
            return

        # if we grabbed any late events, make sure we don't play them again
        beat_max = max(m[0] for m in pending)
        if (self.clock_beat > clock_starting) or (beat_max <= clock_starting):
            self.clock_beat = max(self.clock_beat, beat_max)

        if len(pending) == 1:
            self.outlets[0] = pending[0][2]
        else:
            self.outlets[0] = MultiOutput([p[2] for p in pending])


def register():
    MFPApp().register("messagerec", MessageRec)
