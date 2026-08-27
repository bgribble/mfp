"""
buffer_editor/analyze.py -- helpers for audio analysis

Copyright (c) Bill Gribble <grib@billgribble.com>
"""
import math
import numpy as np

from mfp import log
from mfp.utils import extends
from .buffer_editor import BufferEditor


@extends(BufferEditor)
async def analyze_loudness(self):
    if self.implot_selection:
        start = self.implot_selection.x.min
        end = self.implot_selection.x.max
    else:
        start = 0
        end = self.implot_total_time

    sample_start = int(self.position_to_sample(start))
    sample_end = int(self.position_to_sample(end))
    sample_size = sample_end - sample_start

    region = [
        chan[sample_start:sample_end] for chan in self.buffer_data
    ]

    max_value = max(
        [np.max(np.abs(chan_data)) for chan_data in region]
    )
    rms_value = math.sqrt(sum([sum(chan_data**2) for chan_data in region]) / (sample_size * len(region)))

    if max_value > 0:
        max_db = 20 * math.log10(max_value)
    else:
        max_db = -100

    if rms_value > 0:
        rms_db = 20 * math.log10(rms_value)
    else:
        rms_db = -100

    return dict(peak=max_db, rms=rms_db)


@extends(BufferEditor)
async def analyze_bpm(self):
    return
