#include <stdlib.h>
#include <stdio.h>
#include <x86intrin.h>
#include <glib.h>
#include <string.h>
#include "mfp_dsp.h"
#include "mfp_block.h"


mfp_block * 
mfp_block_new(int blocksize) 
{
	mfp_block * b = g_malloc(sizeof(mfp_block));
	gpointer buf;
	posix_memalign(&buf, 16, (blocksize/4 * sizeof(__v4sf)));
	mfp_block_init(b, buf, blocksize);
	return b;
}

void
mfp_block_init(mfp_block * block, mfp_sample * data, int blocksize) 
{
	block->data = data; 
	block->blocksize = blocksize;
	block->allocsize = blocksize;
	if (((long)data & (long)0xf) == 0) {
		block->aligned = 1;
	}
	else {
		block->aligned = 0;
	}
}

void
mfp_block_free(mfp_block * in)
{
	free(in->data);
	in->data = NULL;
	in->blocksize = 0;
	in->allocsize = 0;
	g_free(in);
}

void
mfp_block_resize(mfp_block * in, int newsize) 
{
	if (newsize <= in->allocsize) {
		in->blocksize = newsize;
	}
	else {
		g_free(in->data);
		posix_memalign((void **)(&(in->data)), 16, newsize);
		in->blocksize = newsize;
		in->allocsize = newsize;
		in->aligned = 1;
	}
}

int
mfp_block_const_mul(mfp_block * in, mfp_sample constant, mfp_block * out) 
{
	__v4sf cval, ival, oval;
	__v4sf * iptr, * optr, * iend;
	mfp_sample * uiptr, *uoptr, *uiend;

	cval = (__v4sf) { constant, constant, constant, constant }; 

	if (in->aligned && out->aligned) {
		iptr = (__v4sf *)(in->data);
		optr = (__v4sf *)(out->data);
		iend = iptr + in->blocksize/4;
		for(; iptr < iend; iptr++) {
			*optr = *iptr * cval;
			optr++;
		}
	}
	else {
		uiptr = in->data;
		uoptr = out->data;
		uiend = uiptr + in->blocksize;

		for(; uiptr < uiend; uiptr += 4) {
			ival = __builtin_ia32_loadups(uiptr);
			__builtin_ia32_storeups(uoptr, ival*cval);
			uoptr += 4;
		}
	}
	return 1;
}


int
mfp_block_const_add(mfp_block * in, mfp_sample constant, mfp_block * out) 
{
	__v4sf cval, ival, oval;
	__v4sf * iptr, * optr, * iend;
	mfp_sample * uiptr, *uoptr, *uiend;

	cval = (__v4sf) { constant, constant, constant, constant }; 

	if (in->aligned && out->aligned) {
		iptr = (__v4sf *)(in->data);
		optr = (__v4sf *)(out->data);
		iend = iptr + in->blocksize/4;
		for(; iptr < iend; iptr++) {
			*optr = *iptr + cval;
			optr++;
		}
	}
	else {
		uiptr = in->data;
		uoptr = out->data;
		uiend = uiptr + in->blocksize;

		for(; uiptr < uiend; uiptr += 4) {
			ival = __builtin_ia32_loadups(uiptr);
			oval = ival + cval;
			__builtin_ia32_storeups(uoptr, oval);
			uoptr += 4;
		}
	}
	return 1;
}

int
mfp_block_index_fetch(mfp_block * indexes, mfp_sample * base, mfp_block * out) 
{
	int loc = 0;
	int end = out->blocksize;

	for(; loc < end; loc++) {
		out->data[loc] = base[(int)(indexes->data[loc])];
	}
	return 1;
}

int
mfp_block_zero(mfp_block * b) 
{
	memset(b->data, 0, b->blocksize*sizeof(mfp_sample));
	return 1;
}

int
mfp_block_fill(mfp_block * in, mfp_sample constant) 
{
	int loc = 0;
	int end = in->blocksize;
	__v4sf cval = (__v4sf) { constant, constant, constant, constant }; 

	for(; loc < end; loc+=4) {
		__builtin_ia32_storeups(in->data + loc, cval);
	}
	return 1;
}

int
mfp_block_mac(mfp_block * in_1, mfp_block * in_2, mfp_block * in_3, mfp_block * out)
{
	int loc = 0;
	int end = in_1->blocksize;
	__v4sf v0, v1, v2, v3;


	if (in_3 != NULL) {
		for(; loc < end; loc+=4) {
			v0 = __builtin_ia32_loadups(out->data + loc);
			v1 = __builtin_ia32_loadups(in_1->data + loc);
			v2 = __builtin_ia32_loadups(in_2->data + loc);
			v3 = __builtin_ia32_loadups(in_3->data + loc);

			__builtin_ia32_storeups(out->data + loc, v0+v1*v2*v3); 
		}
	}
	else {
		for(; loc < end; loc+=4) {
			v0 = __builtin_ia32_loadups(out->data + loc);
			v1 = __builtin_ia32_loadups(in_1->data + loc);
			v2 = __builtin_ia32_loadups(in_2->data + loc);

			__builtin_ia32_storeups(out->data + loc, v0 + v1*v2);
		}
	}

	return 1;
}

int
mfp_block_trunc(mfp_block * in, mfp_block * out) 
{
	int loc = 0;
	int end = in->blocksize;
	__v4sf ftmp;
	__v4si itmp;
	for(; loc < end; loc+=4) {
		ftmp = __builtin_ia32_loadups(in->data+loc);
		itmp = __builtin_ia32_cvttps2dq(ftmp);
		ftmp = __builtin_ia32_cvtdq2ps(itmp);
		__builtin_ia32_storeups(out->data + loc, ftmp); 
	}
	return 1;
}

int
mfp_block_copy(mfp_block * in, mfp_block * out)
{
	if (out->blocksize != in->blocksize) {
		mfp_block_resize(out, in->blocksize);
	}
	memcpy(out->data, in->data, in->blocksize*sizeof(mfp_sample));
	return 1;
}

mfp_sample 
mfp_block_integrate(mfp_block * deltas, mfp_sample scale, mfp_sample initval, mfp_block * out)
{
	int loc = 0;
	int end = out->blocksize;
	double accum = initval;

	if(deltas == NULL) {
		for(loc = 0; loc < end; loc++) {
			out->data[loc] = (mfp_sample)accum;
			accum += (double)scale;
		}
		return accum;
	}
	else {
		for(loc = 0; loc < end; loc++) {
			out->data[loc] = (mfp_sample)accum;
			accum += (deltas->data[loc]*(double)scale);
		}
		return accum;
	}
}
