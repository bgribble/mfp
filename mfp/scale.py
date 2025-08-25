

class Scale (object):
    def __init__(self):
        pass


class Tuning (object):
    def __init__(self):
        pass


class EqualTemper12 (Tuning):
    def __init__(self, a4=440.0):
        Tuning.__init__(self)
        self.base_frequencies = [261.63, 277.18, 293.66, 311.13, 329.63,
                                 349.23, 369.99, 392.00, 415.30, 440.00,
                                 466.16, 493.88]
        self.a4_freq = a4
        self.frequencies = []
        self.retune(self.a4_freq)

    def retune(self, a4):
        scaling = a4 / 440.0
        self.a4_freq = a4
        self.frequencies = [f * scaling for f in self.base_frequencies]

    def freq(self, octave, tone):
        octave_scale = 2.0 ** (octave - 4)
        return self.frequencies[tone] * octave_scale


class MapScale(Scale):
    MAP = {}

    def __init__(self, transpose=0):
        Scale.__init__(self)
        self.transpose_semis = transpose

    def transpose(self, offset):
        self.transpose_semis = offset

    def from_midi_key(self, keynum):
        note = keynum + self.transpose_semis
        octave = int(note) // 12 - 2
        tone = self.MAP.get(int(note) % 12, note)
        return (octave, tone)


class Major (MapScale):
    MAP = {
        0: 0,
        1: 0,
        2: 2,
        3: 2,
        4: 4,
        5: 5,
        6: 5,
        7: 7,
        8: 7,
        9: 9,
        10: 9,
        11: 11,
    }


class Minor (MapScale):
    MAP = {
        0: 0,
        1: 0,
        2: 2,
        3: 3,
        4: 3,
        5: 5,
        6: 5,
        7: 7,
        8: 8,
        9: 8,
        10: 10,
        11: 10,
    }


class Chromatic (Scale):
    def __init__(self, transpose=0):
        Scale.__init__(self)
        self.transpose_semis = transpose

    def transpose(self, offset):
        self.transpose_semis = offset

    def from_midi_key(self, keynum):
        note = keynum + self.transpose_semis
        octave = int(note) // 12 - 2
        tone = int(note) % 12
        return (octave, tone)
