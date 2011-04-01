
import math 


class CubicEstimator(object):
	def __init__(self, domain, npieces, f, f1=None, f2=None,
			     guess_resolution=1000):
		self.domain = domain
		self.npieces = npieces
		self.f = f
		self.f1 = f1 or self._f1_guess
		self.f2 = f2 or self._f2_guess
		self.guess_resolution = guess_resolution
		self.piece_starts = None
		self.cubic_coeffs = None

		self.build()

	def _f1_guess(self, x):
		piecesize = (self.domain[1] - self.domain[0])/(self.npieces * self.guess_resolution)
		f_0 = self.f(x - piecesize/2.0)
		f_1 = self.f(x + piecesize/2.0)
		return (f_1 - f_0)/(piecesize)

	def _f2_guess(self, x):
		piecesize = (self.domain[1] - self.domain[0])/(self.npieces * self.guess_resolution)
		f1_0 = self.f1(x - piecesize/2.0)
		f1_1 = self.f1(x + piecesize/2.0)
		return (f1_1 - f1_0)/(piecesize)

	def build(self):
		xjump = (self.domain[1] - self.domain[0]) / self.npieces
		xval = [ n*xjump for n in range(self.npieces) ]
		fval = [ self.f(x) for x in xval ]
		f1val = [ self.f1(x) for x in xval ] 
		f2val = [ self.f2(x) for x in xval ]
		
		self.cubic_coeffs = [] 
		self.piece_starts = xval[:-1] 
	
		for n in range(len(xval) - 1):
			minx = xval[n]
			coeffs = self._calc_piece_coeffs([ xval[n], fval[n], f1val[n], f2val[n]],
								             [ xval[n+1], fval[n+1], f1val[n+1], f2val[n+1]])
			self.cubic_coeffs.append(coeffs)
		print self.cubic_coeffs
		print len(self.cubic_coeffs)

	
	def _find_coeffs(self, x):
		if (x < self.domain[0]) or (x > self.domain[1]):
			return None 
		for n in range(len(self.piece_starts)-1):
			if self.piece_starts[n+1] > x:
				return self.cubic_coeffs[n]
			elif self.piece_starts[n+1] == x:
				return self.cubic_coeffs[n+1]
		return self.cubic_coeffs[-1]

	def _calc_piece_coeffs(self, p1, p2):
		def x(p):
			return p[0]
		def f(p):
			return p[1]
		def f1(p):
			return p[2]
		def f2(p):
			return p[3]
		a3 = (f2(p1)-f2(p2))/(6.0*(x(p1)-x(p2)))
		a2 = (f2(p1)+f2(p2)-6.0*a3*(x(p1)+x(p2)))/4.0
		a1 = (f(p1) - f(p2) - (a2*x(p1)**2 + a3*x(p1)**3 - a2*x(p2)**2 -a3*x(p2)**3)) / (x(p1) - x(p2)) 
		a0 = f(p1) - a1*x(p1) - a2*x(p1)**2 - a3*x(p1)**3 
		return [a0, a1, a2, a3] 


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


