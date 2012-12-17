#! /usr/bin/env python
'''
butter.py
Butterworth filter designer for cascaded biquad filter implementation

Lifted from musicdsp.com sample source code in C.

Basic idea: for the filter order n, take the s-domain "butterworth
polynomial", transform it to generate a filter transfer function, then
convert from s to z domain.  Then implement as a cascade of second-order
biquad  filter sections.

Polynomials:
	n	B_n(s)
	1	(s+1)
	2	s^2 + 1.4142 s + 1
	3   (s + 1)(s^2 + s + 1)
	4	(s^2 + 0.7654s + 1)(s^2 + 1.8478s + 1)
	5	(s + 1)(s^2 + 0.6180s + 1)(s^2 + 1.6180s + 1)
	6	(s^2 + 0.5176s + 1)(s^2 + 1.4142s + 1)(s^2 + 1.9319s + 1)
	7	(s + 1)(s^2 + 0.4450s + 1)(s^2 + 1.2470s + 1)(s^2 + 1.8019s + 1)
	8	(s^2 + 0.3902s + 1)(s^2 + 1.1111s + 1)(s^2 + 1.6629s + 1)(s^2 + 1.9616s + 1)

Each increase in n gets you 6dB/octave of sharpness on the rolloff.

Transfer function:
	H(s) = G_0 / B_n(a), where a = s / w_c
	w_c is cutoff freq, G_0 is DC gain (we take to be 1), so

	1	H(s) = 1/(s/w_c + 1) = w_c / (s + w_c)
	2   H(s) = 1/(s^2/w_c^2 + 1.4142 s/w_c + 1) =



'''
