/*
 * cspline.c -- cubic spline functions
 *
 * Copyright (c) 2011 Bill Gribble <grib@billgribble.com>
 */

#include <stdio.h>
#include <glib.h>
#include <string.h>
#include "mfp_dsp.h"
#include "cspline.h"
#include "mfp_block.h"

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
	memcpy(self->segments, segments, 4*self->num_segments*sizeof(float));
	self->domain_start = domain_start;
	self->domain_end = domain_end;
}

void 
cspline_free(cspline * self) 
{
	/* FIXME */
}

static void
print_block(mfp_block * b)
{
	int i;
	for (i=0; i<b->blocksize; i++) {
		printf("%f ", b->data[i]);
	}
	printf ("\n");
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
	mfp_block_mac(in, in, NULL, self->x2);

	/* compute spline segment number for each x */
	mfp_block_copy(in, self->block_segs);
	mfp_block_const_add(self->block_segs, self->domain_start, self->block_segs);
	mfp_block_const_mul(self->block_segs, 
			            (float)(self->num_segments)/(self->domain_end - self->domain_start),
						self->block_segs);
	mfp_block_trunc(self->block_segs, self->block_segs);

	/* init output y = c0 */
	fetch_constants(self, self->block_segs, 0, out);

	/* get c1 coefficients for x */
	fetch_constants(self, self->block_segs, 1,  self->coeff);

	/* mac y += c1 * x */
	mfp_block_mac(in, self->coeff, NULL, out);

	/* get c2 coefficients for x**2 */
	fetch_constants(self, self->block_segs, 2,  self->coeff);

	/* mac y += c2 * x**2 */
	mfp_block_mac(self->x2, self->coeff, NULL, out);

	/* get c3 coefficients for x**3 */
	fetch_constants(self, self->block_segs, 3,  self->coeff);

	/* mac y += c3 * x**2 * x */
	mfp_block_mac(self->x2, self->coeff, in, out);
}

