
import math
import numpy as np

from mfp import log
from mfp.utils import extends
from .buffer_editor import BufferEditor


def nearest_power_of_2(val):
    return 2**(int(math.log2(val)))


def compute_spectrogram(signal, nperseg=512, noverlap=256):
    # 1. Create a Hann window to reduce spectral leakage
    window = np.hanning(nperseg)

    # 2. Calculate the step (hop) size between consecutive windows
    hop_size = nperseg - noverlap

    # 3. Determine the total number of time segments
    num_segments = (len(signal) - nperseg) // hop_size + 1

    # 4. Initialize an empty list to hold the FFT data
    spectrogram_cols = []

    for i in range(num_segments):
        # Extract the current segment frame
        start = i * hop_size
        end = start + nperseg
        segment = signal[start:end]

        # Apply the window function to the segment
        windowed_segment = segment * window

        # Compute the Real FFT (only returns positive frequencies)
        fft_result = np.fft.rfft(windowed_segment)

        # Calculate the magnitude spectrum
        magnitude = np.log(np.real(np.abs(fft_result)))
        spectrogram_cols.append(magnitude)

    # 5. Stack columns vertically and transpose so time is on X-axis and frequency on Y-axis
    # Columns become rows: shape will be (frequency_bins, time_segments)
    if spectrogram_cols:
        return np.flipud(np.column_stack(spectrogram_cols))

    return None


@extends(BufferEditor)
def get_spectral_data(self, channel, x_min, x_max, plot_w, plot_h):
    x_min = int((x_min or 0) * self.buffer_info.rate)
    x_max = int((x_max * self.buffer_info.rate) if x_max else len(self.buffer_data[0]))

    time_bin_size = 0
    time_bin_overlap = 0
    if plot_w:
        time_bin_size = nearest_power_of_2((x_max - x_min) / (plot_w / 2))
        time_bin_overlap = time_bin_size // 2
        time_bin_size = max(time_bin_size, 256)

    freq_bin_count = nearest_power_of_2(min(time_bin_size // 2, int(plot_h // 2)))

    key = (channel, x_min, x_max, time_bin_size, freq_bin_count)
    if key in self.spectral_data_cache:
        return self.spectral_data_cache[key]

    spectral_data = compute_spectrogram(
        self.buffer_data[channel][x_min:x_max],
        time_bin_size, time_bin_overlap
    )
    if not spectral_data:
        return None

    spectral_rows, spectral_cols = spectral_data.shape
    group_size = max(1, (spectral_rows // 2) // freq_bin_count)
    reshaped = spectral_data[spectral_rows // 2 + 1:].reshape(
        freq_bin_count, group_size,
        spectral_cols, 1
    )
    summed = reshaped.sum(axis=(1, 3)) / group_size

    self.spectral_data_cache[key] = summed
    return summed

