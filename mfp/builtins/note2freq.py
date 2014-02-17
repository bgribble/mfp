#! /usr/bin/env python
'''
p_note2freq.py:  Convert a NoteOn or note number to freq in Hz

Copyright (c) 2012 Bill Gribble <grib@billgribble.com>
'''

from ..processor import Processor
from ..mfp_app import MFPApp
from .. import Bang, Uninit
from .. import scale
from .. import midi


class Note2Freq(Processor):
    '''
    [note2freq] converts a note to a frequency
    Parameters:
            scale: a subclass of Scale (defaults to Chromatic)
            tuning: an instance of Tuning (defaults to EqualTemper)
    '''
    doc_tooltip_obj = "Convert a MIDI note or note number to a frequency"
    doc_tooltip_inlet = ["Scale (number to note name) (default: Chromatic 60=C4)"
                         "Tuning (note name to frequency) (default: Equal Temperament A4=440"]
    doc_tooltip_outlet = ["Frequency output"]

    def __init__(self, init_type, init_args, patch, scope, name):
        initargs, kwargs = patch.parse_args(init_args)
        if kwargs.get('scale'):
            self.scale = kwargs.get('scale')
        else:
            self.scale = scale.Chromatic()

        if kwargs.get('tuning'):
            self.tuning = kwargs.get('tuning')
        else:
            self.tuning = scale.EqualTemper()
        Processor.__init__(self, 3, 1, init_type, init_args, patch, scope, name)

    def trigger(self):
        if self.inlets[1] is not Uninit:
            self.scale = self.inlets[1]
            self.inlets[1] = Uninit 

        if self.inlets[2] is not Uninit:
            self.tuning = self.inlets[2]
            self.inlets[2] = Uninit 

        inval = self.inlets[0]
        note = None
        if isinstance(inval, midi.Note):
            note = inval.key
        elif isinstance(inval, (float, int)):
            note = int(inval)

        if note is not None:
            self.outlets[0] = self.tuning.freq(*self.scale.midinote(note))


def register():
    MFPApp().register("note2freq", Note2Freq)
