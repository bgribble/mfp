
class Scale (object):
	def __init__(self):
		pass

class Tuning (object):
	def __init__(self):
		pass

class EqualTemper (Tuning):
	def __init__(self, a4=440.0):
		Tuning.__init__(self)
		self.base_frequencies = [ 261.63, 277.18, 293.66, 311.13, 329.63,
				   		          349.23, 369.99, 392.00, 415.30, 440.00,
						          466.16, 493.88 ] 
		self.a4_freq = a4
		self.frequencies = []
		self.retune(self.a4_freq)

	def retune(self, a4):
		scaling = a4 / 440.0
		self.a4_freq = a4
		self.frequencies = [ f*scaling for f in self.base_frequencies ]

	def freq(self, octave, tone):
		octave_scale = 2.0**(octave - 4)
		return self.frequencies[tone] * octave_scale

class Chromatic (Scale):
	def __init__(self, transpose=0):
		Scale.__init__(self)
		self.transpose_semis = transpose

	def transpose(self, offset):
		self.transpose_semis = offset

	def midinote(self, keynum):
		note = keynum + self.transpose_semis
		octave = int(note) / 12 - 2
		tone = int(note) % 12 
		return (octave, tone)

