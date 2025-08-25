#! /usr/bin/env python
'''
quantize.py: Quantize a note number to a scale

Copyright (c) Bill Gribble <grib@billgribble.com>
'''

from ..processor import Processor
from ..mfp_app import MFPApp
from .. import Bang, Uninit
from .. import scale
from .. import midi


class Quantize(Processor):
    '''
    [quantize] rounds or truncates a note to a scale
    Parameters
            scale: a subclass of Scale (defaults to Chromatic)
            root: a note representing the octave root
    '''
    doc_tooltip_obj = "Convert a MIDI note or note number to a frequency"
    doc_tooltip_inlet = [
        "Note or note number",
        "Scale (default: Chromatic 60=C4)",
        "Root (note number of scale root) (default: 0)"
    ]
    doc_tooltip_outlet = [
        "Note number"
    ]

    def __init__(self, init_type, init_args, patch, scope, name, defs=None):
        extra=defs or {}
        initargs, kwargs = patch.parse_args(init_args, **extra)
        self.root = 0
        self.scale = scale.Chromatic

        if len(initargs) > 1:
            self.root = initargs[1]
        if len(initargs):
            self.scale = initargs[0]

        Processor.__init__(self, 3, 1, init_type, init_args, patch, scope, name, defs)

    async def trigger(self):
        if self.inlets[1] is not Uninit:
            self.scale = self.inlets[1]
            self.inlets[1] = Uninit

        if self.inlets[2] is not Uninit:
            self.root = self.inlets[2]
            self.inlets[2] = Uninit

        inval = self.inlets[0]
        note = None
        if isinstance(inval, midi.Note):
            note = inval.key
        elif isinstance(inval, (float, int)):
            note = int(inval)

        if note is not None:
            octave, note = self.scale.from_midi_key(note - self.root)
            self.outlets[0] = octave * 12 + note + self.root

def register():
    MFPApp().register("quantize", Quantize)
