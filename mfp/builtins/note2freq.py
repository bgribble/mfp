#! /usr/bin/env python
'''
p_note2freq.py:  Convert a NoteOn or note number to freq in Hz

Copyright (c) 2012 Bill Gribble <grib@billgribble.com>
'''

from ..processor import Processor
from ..main import MFPApp
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
    def __init__(self, init_type, init_args, patch, scope, name):
        initargs, kwargs = self.parse_args(init_args)
        if kwargs.get('scale'):
            self.scale = kwargs.get('scale')
        else:
            self.scale = scale.Chromatic()

        if kwargs.get('tuning'):
            self.tuning = kwargs.get('tuning')
        else:
            self.tuning = scale.EqualTemper()
        Processor.__init__(self, 1, 1, init_type, init_args, patch, scope, name)

    def trigger(self):
        inval = self.inlets[0]
        note = None
        if isinstance(inval, midi.Note):
            note = inval.key
        elif isinstance(inval, (float, int)):
            note = int(inval)
        elif isinstance(inval, scale.Scale):
            self.scale = inval
        elif isinstance(inval, scale.Tuning):
            self.tuning = inval
        elif isinstance(inval, dict):
            if 'scale' in inval:
                self.scale = inval.get('scale')
            if 'tuning' in inval:
                self.tuning = inval.get('tuning')

        if note is not None:
            self.outlets[0] = self.tuning.freq(*self.scale.midinote(note))


def register():
    MFPApp().register("note2freq", Note2Freq)
