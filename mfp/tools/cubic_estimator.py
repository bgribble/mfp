
import math 


class CubicEstimator(object):
	def __init__(self, domain, npieces, f):
		self.domain = domain
		self.npieces = npieces
		self.f = f
		self.piece_starts = None
		self.cubic_coeffs = None

		self.build()

	def build(self):
		'''
		Each cubic segment has 4 coefficients, A_n, B_n, C_n, and D_n:
			A_n + x B_n + x^2 C_n + x^3 D_n = y

		Constraints:  we will use the endpoints and midpoints of each 
		segment (calculated from self.f()) and constrain the derivative
		of the spline to be constant at segment boundaries. 

			B_n + 2x C_n + 3x^2 D_n = B_n+1 + 2x C_n+1 + 3x^2 D_n+1

		The linear equations will solve for the A_n ... D_N.
		'''
		import numpy as np
		coeffs = np.float_([[0] * (self.npieces*4)] * (self.npieces*4))
		solns = np.float_([0] * (self.npieces*4))

		# substitute the start, end, and midpoint (x,y) for each 
		# segment 
		eqno = 0
		segno = 0 
		for pc in range(npieces):
			x = piece_starts[pc]
			y = self.f(x)
			coeffs[eqno][segno*4] = 1
			coeffs[eqno][segno*4+1] = x 
			coeffs[eqno][segno*4+2] = x*x
			coeffs[eqno][segno*4+3] = x*x*x
			solns[eqno] = y 



	def _find_coeffs(self, x):
		if (x < self.domain[0]) or (x > self.domain[1]):
			return None 
		for n in range(len(self.piece_starts)-1):
			if self.piece_starts[n+1] > x:
				return self.cubic_coeffs[n]
			elif self.piece_starts[n+1] == x:
				return self.cubic_coeffs[n+1]
		return self.cubic_coeffs[-1]

	def errlevel(self, nsamples):
		xdelta = (self.domain[1] - self.domain[0])/nsamples
		accum = 0.0
		for n in range(nsamples-1):
			x = self.domain[0] + n*xdelta
			accum += (self.est(x) - self.f(x))**2 
		return (accum/(nsamples-1))**0.5

	def est(self, x):
		coeffs = self._find_coeffs(x)
		if not coeffs: 
			return None
		else:
			return coeffs[0] + coeffs[1]*x + coeffs[2]*x*x + coeffs[3]*x**3


# e = CubicEstimator([0, math.pi*2], 8, math.sin, math.cos, lambda x: -1.0*math.sin(x))
# print e.errlevel(10000)


