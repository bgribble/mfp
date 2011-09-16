/*
 * cspline.h -- cubic spline functions
 *
 * Copyright (c) 2011 Bill Gribble <grib@billgribble.com>
 */

#ifndef MFP_CSPLINE_H
#define MFP_CSPLINE_H
#include "mfp_dsp.h"
#include "mfp_block.h"

typedef struct {
	mfp_block *x2, *block_segs, *coeff; /* intermediate buffers */ 
	float * segments;
	int num_segments;
	float domain_start;
	float domain_end;
} cspline;


extern cspline * cspline_new(int segments, int blocksize);
extern void cspline_init(cspline * self, float domain_start, float domain_end, float *segments);
extern void cspline_free(cspline * self);
extern int cspline_block_eval(cspline * self, mfp_block * in, mfp_block * out);

#endif

