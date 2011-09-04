#include <stdlib.h>
#include <stdio.h>
#include <x86intrin.h>
#include <glib.h>
#include <string.h>
#include "mfp_dsp.h"
#include "mfp_block.h"

typedef union {
	__v4sf v;
	float f[4];
} fv4 __attribute__ ((aligned (16)));

mfp_block * 
mfp_block_new(int blocksize) 
{
	mfp_block * b = g_malloc(sizeof(mfp_block));
	gpointer buf;
	posix_memalign(&buf, 16, (blocksize/4 * sizeof(fv4)));
	mfp_block_init(b, buf, blocksize);
	return b;
}

void
mfp_block_init(mfp_block * block, mfp_sample * data, int blocksize) 
{
	block->data = data; 
	block->blocksize = blocksize;
	block->allocsize = blocksize;

}

void
mfp_block_free(mfp_block * in)
{
	g_free(in->data);
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
		in->data = g_malloc(newsize);
		in->blocksize = newsize;
		in->allocsize = newsize;
	}
}

int
mfp_block_const_mul(mfp_block * in, mfp_sample constant, mfp_block * out) 
{
	fv4 cval;
	fv4 * iv = (fv4 *)(in->data);
	fv4 * ov = (fv4 *)(out->data);
	fv4 * iend = iv + in->blocksize/4;

	cval.v = (__v4sf) { constant, constant, constant, constant }; 

	for(; iv < iend; iv++) {
		ov->v = iv->v * cval.v;
		ov++;
	}
	return 1;
}


int
mfp_block_const_add(mfp_block * in, mfp_sample constant, mfp_block * out) 
{
	fv4 cval;
	fv4 * iv = (fv4 *)(in->data);
	fv4 * ov = (fv4 *)(out->data);
	fv4 * iend = iv + in->blocksize/4;

	cval.v = (__v4sf) { constant, constant, constant, constant }; 

	for(; iv < iend; iv++) {
		ov->v = iv->v + cval.v;
		ov++;
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
	__v4sf v0, v1, v2, v3, v4;


	if (in_3 != NULL) {
		for(; loc < end; loc+=4) {
			v0 = __builtin_ia32_loadups(out->data + loc);
			v1 = __builtin_ia32_loadups(in_1->data + loc);
			v2 = __builtin_ia32_loadups(in_2->data + loc);
			v3 = __builtin_ia32_loadups(in_3->data + loc);
			v4 = __builtin_ia32_mulss(v1, v2);

			__builtin_ia32_storeups(out->data + loc, 
									__builtin_ia32_addss(v0, __builtin_ia32_mulss(v3, v4))); 
		}
	}
	else {
		for(; loc < end; loc+=4) {
			v0 = __builtin_ia32_loadups(out->data + loc);
			v1 = __builtin_ia32_loadups(in_1->data + loc);
			v2 = __builtin_ia32_loadups(in_2->data + loc);
			v4 = __builtin_ia32_mulss(v1, v2);

			__builtin_ia32_storeups(out->data + loc, __builtin_ia32_addss(v0, v4));
		}
	}

	return 1;
}

int
mfp_block_trunc(mfp_block * in, mfp_block * out) 
{
	int loc = 0;
	int end = in->blocksize;

	for(; loc < end; loc+=4) {
		__builtin_ia32_storeups(out->data + loc, 
								__builtin_ia32_cvtdq2ps(
									__builtin_ia32_cvtps2dq(__builtin_ia32_loadups(in->data+loc))));
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
