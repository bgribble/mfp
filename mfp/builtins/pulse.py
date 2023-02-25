#! /usr/bin/env python
'''
pulse.py:  Builtin oscillator DSP objects

Copyright (c) 2018 Bill Gribble <grib@billgribble.com>
'''

from mfp.processor import Processor
from ..mfp_app import MFPApp
from .. import Bang, Uninit


class Pulse(Processor):
    '''
    pulse train oscillator
    [pulse~] is (-1,1), [gate~] is (0,1)

    To create a fixed-width pulse (for pulse~ or gate~)
    include creation args with the PW and 'ms' as
    last args. Default or 'frac' as last arg means
    pulse width is a fraction of the overall cycle

    example:
    [pulse~ 100, 1, 10, 'ms']
    100 Hz, amplitude 1, 10 ms pulse width
    '''

    doc_tooltip_obj = "Pulse/square oscillator"
    doc_tooltip_inlet = ["Phase reset (radians)",
                         "Frequency (hz) (min: 0, max: samplerate/2, default: initarg 0)",
                         "Amplitude (default: initarg 1)",
                         "Pulse Width (default: initarg 2)",
                         "Pulse Width Mode ('ms' or 'frac') (default: initarg 3)"]
    doc_tooltip_outlet = ["Signal output"]

    def __init__(self, init_type, init_args, patch, scope, name):
        Processor.__init__(self, 4, 1, init_type, init_args, patch, scope, name)
        initargs, kwargs = self.parse_args(init_args)
        freq = 0
        ampl = 1.0
        pw = 0.5
        self.init_loval = -1.0
        self.init_hival = 1.0
        self.init_mode = 0

        if init_type == 'gate~':
            self.init_loval = 0.0

        if len(initargs) > 0:
            freq = initargs[0]
        if len(initargs) > 1:
            ampl = initargs[1]
        if len(initargs) > 2:
            pw = initargs[2]
        if len(initargs) > 3:
            if initargs[3] == 'ms':
                self.init_mode = 1
            elif initargs[3] == 'frac':
                self.init_mode = 0

        self.dsp_inlets = [1, 2, 3]
        self.dsp_outlets = [0]

    async def setup(self):
        await self.dsp_init(
            "pulse~",
            _sig_1=float(freq),
            _sig_2=float(ampl),
            _sig_3=float(pw),
            hival=self.init_hival,
            loval=self.init_loval,
            pw_mode=self.init_mode
        )

    async def trigger(self):
        # number inputs to the DSP ins (freq, amp) are
        # handled automatically
        if self.inlets[0] is Bang:
            await self.dsp_setparam("phase", float(0))
        else:
            phase = float(self.inlets[0])
            await self.dsp_setparam("phase", phase)


def register():
    MFPApp().register("pulse~", Pulse)
    MFPApp().register("gate~", Pulse)
