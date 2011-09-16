
import math 

def frange(start, stop, steps):
	dd = (stop-start)/steps
	return [ start + n*dd for n in range(steps) ]


class CubicEstimator(object):
	def __init__(self, domain, npieces, f):
		self.domain = domain
		self.npieces = npieces
		self.f = f
		self.piece_starts = frange(domain[0], domain[1], npieces)
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
		for pc in range(self.npieces):
			pstart = self.piece_starts[pc]
			if pc != len(self.piece_starts)-1:
				pend = self.piece_starts[pc+1]
			else:
				pend = self.domain[1]

			xvals = [ pstart, pend, (pstart+pend)/2 ]

			for x in xvals:
				y = self.f(x)
				coeffs[eqno][pc*4] = 1
				coeffs[eqno][pc*4+1] = x 
				coeffs[eqno][pc*4+2] = x*x
				coeffs[eqno][pc*4+3] = x*x*x
				solns[eqno] = y 
				eqno += 1

			if pc != len(self.piece_starts)-1:
				nextseg = pc+1
				x = pend
				nx = pend
			else:
				nextseg = 0
				x = pend
				nx = 0

			coeffs[eqno][pc*4] = 0.0
			coeffs[eqno][nextseg*4] = 0.0

			coeffs[eqno][pc*4+1] = 1.0
			coeffs[eqno][nextseg*4+1] = -1.0

			coeffs[eqno][pc*4+2] = 2.0*x
			coeffs[eqno][nextseg*4+2] = -2.0*nx
			
			coeffs[eqno][pc*4+3] = 3.0*x*x
			coeffs[eqno][nextseg*4+3] = -3.0*nx*nx
			
			solns[eqno] = 0.0
			eqno += 1

		spline = np.linalg.solve(coeffs, solns)
		cc = []
		for piece in range(self.npieces):
			cc.append(spline[4*piece:4*piece+4])
		self.cubic_coeffs = cc

	def _find_coeffs(self, x):
		if (x < self.domain[0]) or (x > self.domain[1]):
			x = self.domain[0] + ((x - self.domain[0]) % (self.domain[1] - self.domain[0]))

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


	def hillclimb(self, size, weight):
		samples=1000
		old_starts = self.piece_starts
		old_coeffs = self.cubic_coeffs 

		init_err = self.errlevel(samples)

		dsize = (self.domain[1] - self.domain[0])
		delta =  dsize / float(samples) 
		

		for n in range(len(self.piece_starts[1:])):
			knot = self.piece_starts[1+n]
			left = (self.est(knot-size)- self.f(knot-size))**2
			right = (self.est(knot+size) - self.f(knot+size))**2
			if left > right:
				self.piece_starts[1+n] -= weight 
			elif right > left:
				self.piece_starts[1+n] += weight 

		self.build()
		final_err = self.errlevel(samples)

		if final_err > init_err:
			self.piece_starts = old_starts
			self.cubic_coeffs = old_coeffs 
			return False
		else:
			return True 

e = CubicEstimator([0, math.pi*2], 9, math.sin)

for x in frange(0, math.pi * 2, 441):
	print x, math.sin(x), e.est(x), e.est(x) - math.sin(x)

print e.cubic_coeffs


