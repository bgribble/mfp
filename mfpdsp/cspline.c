/*
 * cspline.c -- cubic spline functions
 *
 * Copyright (c) 2011 Bill Gribble <grib@billgribble.com>
 */

#include "cspline.h"
#include "mfp_block.h"

typedef struct {
	mfp_block *x2, *block_segs, *coeff; /* intermediate buffers */ 
	float * segments;
	int num_segments;
	float domain_start;
	float domain_end;
} cspline;


cspline * 
cspline_new(int segments, int blocksize) 
{
	cspline * c = g_malloc(sizeof(cspline));
	float * d = (float *)g_malloc(segments*4*sizeof(float));

	c->num_segments = segments;
	c->segments = d;
	c->x2 = mfp_block_new(blocksize);
	c->block_segs = mfp_block_new(blocksize);
	c->coeff = mfp_block_new(blocksize);
	 
	return c;
}

void
cspline_init(cspline * self, float domain_start, float domain_end, float *segments)
{
	g_memcpy(self->segments, segments, 4*self->num_segments*sizeof(float));
	self->domain_start = domain_start;
	self->domain_end = domain_end;
}

static void 
fetch_constants(cspline * self, mfp_block * offsets, int const_num, mfp_block * out)
{
	mfp_block_const_mul(offsets, 4, out);
	mfp_block_const_add(out, const_num, out);
	mfp_block_index_fetch(out, self->segments, out);
}

int
cspline_block_eval(cspline * self, mfp_block * in, mfp_block * out)
{
	/* build x^2 */ 
	mfp_block_zero(self->x2);
	mfp_block_mac(in, in, self->x2);

	/* compute spline segment number for each x */
	mfp_block_copy(in, self->segs);
	mfp_block_const_add(self->segs, self->domain_start, self->segs);
	mfp_block_const_mul(self->segs, (self->domain_end - self->domain_start)/(float)(self->num_segments));
	mfp_block_trunc(self->segs, self->segs);

	/* init output y = c0 */
	fetch_constants(self, self->block_segs, 0, out);

	/* get c1 coefficients for x */
	fetch_constants(self, self->block_segs, segs, 1,  coeff);

	/* mac y += c1 * x */
	mfp_block_mac(in, coeff, NULL, out);

	/* get c2 coefficients for x**2 */
	fetch_constants(self, self->block_segs, segs, 2,  coeff);

	/* mac y += c2 * x**2 */
	mfp_block_mac(self->x2, coeff, NULL, out);

	/* get c3 coefficients for x**3 */
	fetch_constants(self, self->block_segs, segs, 3,  coeff);

	/* mac y += c3 * x**2 * x */
	mfp_block_mac(self->x2, coeff, in, out);
}

