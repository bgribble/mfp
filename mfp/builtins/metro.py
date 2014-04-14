#! /usr/bin/env python
'''
p_metro.py: Metronome control processor

Copyright (c) 2010 Bill Gribble <grib@billgribble.com>
'''

from ..timer import MultiTimer
from ..processor import Processor
from ..mfp_app import MFPApp
from datetime import datetime, timedelta
from .. import Bang, Uninit


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
            Throttle._timer.start()

        parsed_args, kwargs = self.parse_args(init_args)

        if len(parsed_args):
            self.interval = timedelta(milliseconds=int(parsed_args[0]))

    def trigger(self):
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

    def timer_cb(self):
        self.send(TimerTick())


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
            Delay._timer.start()

        parsed_args, kwargs = self.parse_args(init_args)

        if len(parsed_args):
            self.delay = timedelta(milliseconds=int(parsed_args[0]))

    def trigger(self):
        if self.inlets[1] is not Uninit:
            self.delay = timedelta(milliseconds=int(self.inlets[1]))
            self.inlets[1] = Uninit

        if isinstance(self.inlets[0], TimerTick):
            self.outlets[0] = self.inlets[0].payload
        else:
            self._timer.schedule(datetime.now() + self.delay, self.timer_cb, [self.inlets[0]])
            self.started = False

    def timer_cb(self, data):
        self.send(TimerTick(data))


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
            Metro._timer.start()

        parsed_args, kwargs = self.parse_args(init_args)

        if len(parsed_args):
            self.interval = timedelta(milliseconds=int(parsed_args[0]))

    def trigger(self):
        if self.inlets[1] is not Uninit:
            self.interval = timedelta(milliseconds=int(self.inlets[1]))
            self.inlets[1] = Uninit

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

    def timer_cb(self):
        self.send(TimerTick())


def register():
    MFPApp().register("metro", Metro)
    MFPApp().register("throttle", Throttle)
    MFPApp().register("delay", Delay)
