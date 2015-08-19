#! /usr/bin/env python
'''
scale_ticks.py
Helpers to compute ticks for displayed axes

Copyright (c) 2012 Bill Gribble <grib@billgribble.com>
'''

import math

class ScaleType (object):
    pass

class LinearScale (ScaleType):
    def __init__(self, min_value=0.0, max_value=1.0):
        self.max_value = max_value
        self.min_value = min_value

    def __repr__(self):
        return "linear"

    def set_bounds(self, minv, maxv):
        self.min_value = minv
        self.max_value = maxv

    # given a linear fraction of the scale (pixel pos as a fraction of size)), 
    # return the value 
    def value(self, fraction):
        value = (self.min_value + (fraction * (self.max_value - self.min_value)))
        return value

    # given a value, return the linear scale fraction
    def fraction(self, value):
        val = (value - self.min_value) / float(self.max_value - self.min_value)
        return val

    def ticks(self, numticks, tick_min=None, tick_max=None):
        # generate ticks in the range [tick_min, tick_max]
        # for a chart showing a total of numticks ticks (approximately)
        # on the total range of [vmin, vmax]
        if tick_min is None:
            tick_min = self.min_value
        if tick_max is None:
            tick_max = self.max_value

        # interv is the target interval between ticks.  We want the
        # nearest .1, .25, .5, or 1 to that.  This calculation is based on
        # the chart as a whole, not the target range
        interv = float(self.max_value - self.min_value) / numticks
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


class DecadeScale (ScaleType): 
    def __init__(self, min_value=-40, max_value=0):
        self.min_value = min_value
        self.max_value = max_value

    def __repr__(self):
        return "decade"

    def fraction(self, value):
        pass

    def value(self, fraction):
        pass

    def ticks(self, numticks, tick_min=None, tick_max=None):
        # generate ticks for a decade log-scaled axis
        if tick_min is None:
            tick_min = self.min_value
        if tick_max is None:
            tick_max = self.max_value
        if tick_min <= 0:
            tick_min = min(tick_max / 100.0, 0.1)

        interv = math.log10(float(self.max_value)/float(self.min_value)) / numticks 
        logbase = math.ceil(interv)
        first_tick_pow = math.ceil(math.log10(tick_min))
        ticks = [ pow(10, first_tick_pow + n*logbase) for n in range(int(numticks)+1) ]
        filtered = [t for t in ticks if t >= tick_min and t <= tick_max]
        return filtered 


class AudioScale (ScaleType):
    '''
    The audio scale is modeled on large-console mixer faders.  
    Scale increments are dB, with basically 3 different slopes: 
        +10 dB -- -10 dB (a 20 dB range) at slope M
        -10 dB -- -50 dB (a 40 dB range) at slope 2M
        -50 dB -- -inf dB over a short range at the bottom
    ticks would be evenly spaced, at 5dB intervals on the top and 
    10 db on the bottom
    '''

    def __init__(self, min_value=-1000, max_value=10):
        self.min_value = min_value
        self.max_value = max_value
        self.thresh_hi = 1.0
        self.thresh_low = 0.55
        self.thresh_inf = 0.1
        self.value_hi = 10
        self.value_med = -10
        self.value_low = -50
        pass 

    def __repr__(self):
        return "audio"

    def set_bounds(self, minv, maxv):
        self.min_value = minv
        self.max_value = maxv
        self._calibrate()

    def _calibrate(self):
        from mfp import log
        split_range = 0.90
        self.thresh_inf = 0.1
        if self.min_value > -50:
            split_range = 1.0
            self.thresh_inf = 0

        nunits = 0
        top = self.max_value
        if top > self.value_hi:
            nunits += top - max(self.value_hi, self.min_value)
            top = self.value_hi
        if top > self.value_med and top > self.min_value:
            nunits += 2*(top - max(self.value_med, self.min_value))
            top = self.value_med
        if top > self.value_low and top > self.min_value:
            nunits += top - max(self.value_low, self.min_value)
            
        unitsize = split_range / nunits
        if self.max_value > self.value_hi:
            self.thresh_hi = 1.0 - unitsize*(self.max_value-self.value_hi)
        else:
            self.thresh_hi = 1.0 - 2*unitsize*(self.max_value-self.value_hi)
        self.thresh_low = self.thresh_hi - 2*unitsize*(self.value_hi - self.value_med)

    def value(self, fraction):
        if fraction < self.thresh_inf: 
            return (self.min_value 
                    + fraction * (self.value_low - self.min_value)/self.thresh_inf)
        elif fraction < self.thresh_low: 
            delta = fraction - self.thresh_inf
            return (self.value_low
                    + delta * (self.value_med - self.value_low)
                    /(self.thresh_low - self.thresh_inf))
        elif fraction < self.thresh_hi: 
            delta = fraction - self.thresh_low
            return (self.value_med  
                    + delta * (self.value_hi - self.value_med)
                    /(self.thresh_hi - self.thresh_low) )
        else:
            delta = fraction - self.thresh_hi
            return (self.value_hi  + delta * (self.value_med - self.value_low)
                    /(self.thresh_low - self.thresh_inf)) 

    def fraction(self, value):
        if value < self.min_value:
            return 0 
        elif value < self.value_low:
            delta = value - self.min_value
            return self.thresh_inf * delta / (self.value_low - self.min_value)
        elif value < self.value_med:
            delta = value - self.value_low 
            return (self.thresh_inf + (self.thresh_low - self.thresh_inf) 
                    * delta / (self.value_med - self.value_low))
        elif value < self.value_hi:
            delta = value - self.value_med
            return (self.thresh_low + (self.thresh_hi - self.thresh_low) 
                    * delta / (self.value_hi - self.value_med))
        else:
            delta = value - 10.0
            return (self.thresh_hi + (self.thresh_hi - self.thresh_low) 
                    * delta / (self.value_med - self.value_low))

    def ticks(self, numticks, tick_min=None, tick_max=None):
        allticks = [-50, -40, -30, -20, -10, -5, 0, 5, 10, 20]
        
        return [t for t in allticks if t >= self.min_value and t <= self.max_value]
