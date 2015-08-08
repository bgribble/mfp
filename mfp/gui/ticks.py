#! /usr/bin/env python
'''
scale_ticks.py
Helpers to compute ticks for displayed axes

Copyright (c) 2012 Bill Gribble <grib@billgribble.com>
'''

import math
from mfp import log 

class LinearScale (object):
    scale_type = 0
    def __init__(self, min_value=0.0, max_value=1.0):
        self.max_value = max_value
        self.min_value = min_value

    # given a linear fraction of the scale (pixel pos as a fraction of size)), 
    # return the value 
    def value(self, fraction):
        value = (self.min_value + (fraction * (self.max_value - self.min_value)))
        return value

    # given a value, return the linear scale fraction
    def fraction(self, value):
        val = (value - self.min_value) / float(self.max_value - self.min_value)
        return val

    def ticks(self, vmin, vmax, numticks, tick_min=None, tick_max=None):
        # generate ticks in the range [tick_min, tick_max]
        # for a chart showing a total of numticks ticks (approximately)
        # on the total range of [vmin, vmax]
        if tick_min is None:
            tick_min = vmin
        if tick_max is None:
            tick_max = vmax

        # interv is the target interval between ticks.  We want the
        # nearest .1, .25, .5, or 1 to that.  This calculation is based on
        # the chart as a whole, not the target range
        interv = float(vmax - vmin) / numticks
        logbase = pow(10, math.floor(math.log10(interv)))
        choices = [logbase, logbase * 2.5, logbase * 5.0, logbase * 10]
        diffs = [abs(interv - c) for c in choices]
        tickint = choices[diffs.index(min(*diffs))]

        # tickint now has the interval between ticks.  Use the target range
        # to generate the ticks
        first_tick = tickint * math.floor(tick_min / tickint)
        numticks = int(float(tick_max - tick_min) / tickint) + 2
        ticks = [first_tick + n * tickint for n in range(numticks)]
        filtered = [t for t in ticks if t >= tick_min and t <= tick_max]
        return filtered 


class DecadeScale (object): 
    scale_type = 1
    def __init__(self):
        pass

    def ticks(self, vmin, vmax, numticks, tick_min=None, tick_max=None):
        # generate ticks for a decade log-scaled axis
        if tick_min is None:
            tick_min = vmin
        if tick_max is None:
            tick_max = vmax
        if tick_min <= 0:
            tick_min = min(tick_max / 100.0, 0.1)

        interv = math.log10(float(vmax)/float(vmin)) / numticks 
        logbase = math.ceil(interv)
        first_tick_pow = math.ceil(math.log10(tick_min))
        ticks = [ pow(10, first_tick_pow + n*logbase) for n in range(int(numticks)+1) ]
        filtered = [t for t in ticks if t >= tick_min and t <= tick_max]
        return filtered 


class AudioScale (object):
    scale_type = 2
    def __init__(self):
        pass 
    def ticks(self, vmin, vmax, numticks, tick_min, tick_max):
        # generate ticks for an octave log-scaled axis
        pass
