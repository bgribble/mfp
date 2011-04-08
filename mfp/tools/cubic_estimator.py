
import math 

def frange(start, stop, steps):
	dd = (stop-start)/steps
	
	return [ start + n*dd for n in range(steps) ]


class CubicEstimator(object):
	def __init__(self, domain, npieces, f):
		self.domain = domain
		self.npieces = npieces
		self.f = f
		self.piece_starts = None
		self.cubic_coeffs = None
		self.piece_starts = frange(domain[0], domain[1], npieces)
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
		for pc in range(self.npieces):
			xvals = [self.piece_starts[pc], self.piece_starts[(pc+1)%len(self.piece_starts)]]
			if pc !=  len(self.piece_starts)-1:
				xvals.append((xvals[0] + xvals[1])/2.0)
			else:
				xvals.append((xvals[0] + self.domain[1])/2.0)

			for x in xvals:
				y = self.f(x)
				coeffs[eqno][segno*4] = 1
				coeffs[eqno][segno*4+1] = x 
				coeffs[eqno][segno*4+2] = x*x
				coeffs[eqno][segno*4+3] = x*x*x
				solns[eqno] = y 
				eqno += 1

			if pc != len(self.piece_starts)-1:
				nextseg = pc+1
			else:
				nextseg = 0

			coeffs[eqno][segno*4+1] = 1.0
			coeffs[eqno][nextseg*4+1] = -1.0
			coeffs[eqno][segno*4+2] = 2.0*x
			coeffs[eqno][nextseg*4+2] = -2.0*x
			coeffs[eqno][segno*4+3] = 3.0*x*x
			coeffs[eqno][nextseg*4+3] = -3.0*x*x
			solns[eqno] = 0.0
			eqno += 1
			segno += 1

		spline = np.linalg.solve(coeffs, solns)

		cc = []
		for piece in range(self.npieces):
			cc.append(spline[4*piece:4*piece+4])
		self.cubic_coeffs = cc

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
		return coeffs[0] + coeffs[1]*x + coeffs[2]*x*x + coeffs[3]*x**3


e = CubicEstimator([0, math.pi*2], 8, math.sin)

for x in frange(0, math.pi * 2, 1000):
	print x, math.sin(x), e.est(x)



