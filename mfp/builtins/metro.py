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

class TimerTick (object):
    def __init__(self, payload=None):
        self.payload = payload


class Throttle (Processor):
    doc_tooltip_obj = "Pass through input, but at a limited rate"
    doc_tooltip_inlet = ["Passthru input",
                         "Minimum time between outputs (ms) (default: initarg 0)" ]
    doc_tooltip_outlet = ["Passthru output" ]

    _timer = None

    def __init__(self, init_type, init_args, patch, scope, name):
        Processor.__init__(self, 2, 1, init_type, init_args, patch, scope, name)

        self.started = False
        self.interval = False
        self.count = 0
        self.queue = []

        if Throttle._timer is None:
            Throttle._timer = MultiTimer()

        parsed_args, kwargs = self.parse_args(init_args)

        if len(parsed_args):
            self.interval = timedelta(milliseconds=int(parsed_args[0]))

    async def trigger(self):
        if self.inlets[1] is not Uninit:
            self.interval = timedelta(milliseconds=int(self.inlets[1]))
            self.inlets[1] = Uninit

        if isinstance(self.inlets[0], TimerTick):
            if self.queue:
                d = self.queue[0]
                self.queue = self.queue[1:]
                self.outlets[0] = d
                self.count += 1
                self._timer.schedule(self.started + self.count * self.interval, self.timer_cb)
            else:
                self.started = False
        elif self.started:
            self.queue.append(self.inlets[0])
        else:
            self.started = datetime.now()
            self.count = 1
            self._timer.schedule(self.started + self.interval, self.timer_cb)
            self.outlets[0] = self.inlets[0]

    async def timer_cb(self):
        await self.send(TimerTick())


class Delay (Processor):
    doc_tooltip_obj = "Pass through input messages, delayed by a specified amount"
    doc_tooltip_inlet = ["Passthru input", "Delay (ms) (default: initarg 0)" ]
    doc_tooltip_outlet = ["Passthru output"]

    _timer = None

    def __init__(self, init_type, init_args, patch, scope, name):
        Processor.__init__(self, 2, 1, init_type, init_args, patch, scope, name)

        self.delay = False

        if Delay._timer is None:
            Delay._timer = MultiTimer()

        parsed_args, kwargs = self.parse_args(init_args)

        if len(parsed_args):
            self.delay = timedelta(milliseconds=int(parsed_args[0]))

    async def trigger(self):
        if self.inlets[1] is not Uninit:
            self.delay = timedelta(milliseconds=int(self.inlets[1]))
            self.inlets[1] = Uninit

        if isinstance(self.inlets[0], TimerTick):
            self.outlets[0] = self.inlets[0].payload
        else:
            self._timer.schedule(datetime.now() + self.delay, self.timer_cb, [self.inlets[0]])
            self.started = False

    async def timer_cb(self, data):
        await self.send(TimerTick(data))


class Metro (Processor):
    doc_tooltip_obj = "Emit a Bang at specified interval"
    doc_tooltip_inlet = ["Control input (True/Bang/nonzero to start, False/None/zero to stop)",
                         "Interval between Bang (ms) (default: initarg 0)" ]
    doc_tooltip_outlet = ["Metronome output"]
    _timer = None

    def __init__(self, init_type, init_args, patch, scope, name):
        Processor.__init__(self, 2, 1, init_type, init_args, patch, scope, name)

        self.started = False
        self.interval = False
        self.count = 0

        if Metro._timer is None:
            Metro._timer = MultiTimer()

        parsed_args, kwargs = self.parse_args(init_args)

        if len(parsed_args):
            self.interval = timedelta(milliseconds=int(parsed_args[0]))

    async def trigger(self):
        if self.inlets[1] is not Uninit:
            self.interval = timedelta(milliseconds=int(self.inlets[1]))
            self.inlets[1] = Uninit
            if self.started:
                self.started = datetime.now()
                self.count = 0

        if isinstance(self.inlets[0], TimerTick):
            if self.started:
                self.outlets[0] = Bang
                self.count += 1
                self._timer.schedule(self.started + self.count * self.interval, self.timer_cb)
        elif self.inlets[0]:
            self.started = datetime.now()
            self.count = 1
            self._timer.schedule(self.started + self.interval, self.timer_cb)
            self.outlets[0] = Bang
        else:
            self.started = False

    async def timer_cb(self):
        await self.send(TimerTick())

class BeatChase (Processor):
    doc_tooltip_obj = "Chase a series of bangs, potentially adjusting timing"
    doc_tooltip_inlet = ["Bang/True/False to chase/start/stop",
                         "Multiplier of beat (higher is faster)",
                         "Beat slip (milliseconds)"]
    _timer = None

    RUNNING = 2
    STARTING = 1
    STOPPED = 0

    def __init__(self, init_type, init_args, patch, scope, name):
        Processor.__init__(self, 3, 1, init_type, init_args, patch, scope, name)

        self.run = BeatChase.STOPPED
        self.chase_lastbang = False
        self.chase_interval = False
        self.multiplier = 1.0
        self.interval = None
        self.slip = timedelta()
        self.baseline_count = 0
        self.baseline_time = False

        if BeatChase._timer is None:
            BeatChase._timer = MultiTimer()

        parsed_args, kwargs = self.parse_args(init_args)
        if len(parsed_args) > 1:
            self.slip = timedelta(milliseconds=parsed_args[1])
        if len(parsed_args) > 0:
            self.multiplier = parsed_args[0]

    async def trigger(self):
        def interval_div(intvl, divisor):
            ts = intvl.total_seconds() / float(divisor)
            int_sec = int(ts)
            frac_sec = ts - int_sec
            return timedelta(seconds=int_sec, microseconds=int(frac_sec * 1000000))
        def interval_mul(intvl, mult):
            ts = intvl.total_seconds() * float(mult)
            int_sec = int(ts)
            frac_sec = ts - int_sec
            return timedelta(seconds=int_sec, microseconds=int(frac_sec * 1000000))

        if self.inlets[2] is not Uninit:
            self.slip = timedelta(milliseconds=int(self.inlets[2]))
            self.inlets[2] = Uninit

        ticker = self.inlets[0]
        self.inlets[0] = Uninit
        if isinstance(ticker, TimerTick):
            self.baseline_count += 1

            if self.inlets[1] is not Uninit:
                self.baseline_count *= (1.0 * self.inlets[1] / self.multiplier)
                self.multiplier = self.inlets[1]
                self.interval = interval_div(self.chase_interval, self.multiplier)
                self.inlets[1] = Uninit

            if self.run:
                self.outlets[0] = Bang
                self._timer.schedule(self.baseline_time + self.slip
                                     + interval_mul(self.interval, self.baseline_count),
                                     self.timer_cb)
        elif isinstance(ticker, type(Bang)):
            bangtime = datetime.now()
            if self.chase_lastbang:
                self.chase_interval = bangtime - self.chase_lastbang
                self.interval = interval_div(self.chase_interval, self.multiplier)
                self.chase_lastbang = bangtime
                if self.run == BeatChase.STARTING:
                    self.baseline_time = self.chase_lastbang
                    self.baseline_count = 1
                    self.run = BeatChase.RUNNING
                    deadline = self.baseline_time + self.slip + self.interval
                    self._timer.schedule(deadline, self.timer_cb)
                    self.outlets[0] = Bang
            else:
                self.chase_lastbang = bangtime
        elif ticker:
            self.run = BeatChase.STARTING
        else:
            self.run = BeatChase.STOPPED

    async def timer_cb(self):
        await self.send(TimerTick())



def register():
    MFPApp().register("metro", Metro)
    MFPApp().register("throttle", Throttle)
    MFPApp().register("delay", Delay)
    MFPApp().register("beatchase", BeatChase)
