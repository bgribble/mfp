#! /usr/bin/env python
'''
scale_ticks.py
Helpers to compute ticks for displayed axes

Copyright (c) 2012 Bill Gribble <grib@billgribble.com>
'''

import math

# hey dipshit make these classes


def linear(vmin, vmax, numticks, tick_min=None, tick_max=None):
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
    return [t for t in ticks if t >= tick_min and t <= tick_max]


def decade(vmin, vmax, numticks, tick_min, tick_max):
    # generate ticks for a decade log-scaled axis
    pass


def octave(vmin, vmax, numticks, tick_min, tick_max):
    # generate ticks for an octave log-scaled axis
    pass
