
#include <sys/time.h>
#include <stdlib.h>
#include <stdio.h>
#include <math.h>

#include "mfp_dsp.h"
#include "mfp_block.h"
#include "builtin.h"

int
test_block_create(void) 
{
	mfp_block * b = mfp_block_new(512);
	if (b == NULL) {
		printf("FAIL: mfp_block_create returned NULL\n");
		return 0;
	}

	if(b->blocksize != 512) {
		printf("FAIL: blocksize is %d, expected 512\n", b->blocksize);
		return 0;
	}

	mfp_block_resize(b, 256);

	if(b->blocksize != 256) {
		printf("FAIL: blocksize is %d, expected 256\n", b->blocksize);
		return 0;
	}

	if(b->allocsize != 512) {
		printf("FAIL: allocsize is %d, expected 512\n", b->allocsize);
		return 0;
	}

	mfp_block_free(b);
	return 1;
}

int 
test_block_constops_unaligned(void)
{
	mfp_block * b = mfp_block_new(16);
	int i;

	b->data ++;
	b->blocksize = 8;
	b->allocsize = 8;
	b->aligned = 0;

	mfp_block_fill(b, 32.0);
	for(i=0; i< 8; i++) {
		if (b->data[i] != 32.0) {
			printf("FAIL: block_fill\n");
			return 0;
		}
	}

	mfp_block_const_mul(b, 0.5, b);

	for(i=0; i< 8; i++) {
		if (b->data[i] != 16.0) {
			printf("FAIL: block_const_mul %f\n", b->data[i]);
			return 0;
		}
	}

	mfp_block_const_add(b, 16.0, b);

	for(i=0; i< 8; i++) {
		if (b->data[i] != 32.0) {
			printf("FAIL: block_const_add %f\n", b->data[i]);
			return 0;
		}
	}
}

int 
test_block_constops(void)
{
	mfp_block * b = mfp_block_new(8);
	int i;

	mfp_block_fill(b, 32.0);
	for(i=0; i< 8; i++) {
		if (b->data[i] != 32.0) {
			printf("FAIL: block_fill\n");
			return 0;
		}
	}

	mfp_block_const_mul(b, 0.5, b);

	for(i=0; i< 8; i++) {
		if (b->data[i] != 16.0) {
			printf("FAIL: block_const_mul %f\n", b->data[i]);
			return 0;
		}
	}

	mfp_block_const_add(b, 16.0, b);

	for(i=0; i< 8; i++) {
		if (b->data[i] != 32.0) {
			printf("FAIL: block_const_add %f\n", b->data[i]);
			return 0;
		}
	}
	return 1;
}

int
test_block_mac(void)
{
	mfp_block * b1, * b2, * b3;
	int i;

	b1 = mfp_block_new(8);
	b2 = mfp_block_new(8);
	b3 = mfp_block_new(8);

	mfp_block_fill(b1, 3.0);
	mfp_block_fill(b2, 5.0);
	mfp_block_zero(b3);

	mfp_block_mac(b1, b2, NULL, b3);

	for(i=0; i< 8; i++) {
		if (b3->data[i] != 15.0) {
			printf("FAIL: block_mac 1 %f\n", b3->data[i]);
			return 0;
		}
	}
	
	mfp_block_mac(b1, b2, NULL, b3);

	for(i=0; i< 8; i++) {
		if (b3->data[i] != 30.0) {
			printf("FAIL: block_mac 2%f\n", b3->data[i]);
			return 0;
		}
	}
	return 1;
}

int
test_block_trunc(void)
{
	mfp_block * b = mfp_block_new(8);
	int i;

	b->data[0] = 16.1;
	b->data[1] = -16.2;
	b->data[2] = 16.3;
	b->data[3] = -16.5;
	b->data[4] = 16.6;
	b->data[5] = -16.7;
	b->data[6] = 16.8;
	b->data[7] = -16.9;
	mfp_block_trunc(b, b);

	for(i=0; i< 8; i++) {
		if (fabs(b->data[i]) != 16.0) {
			printf("FAIL: block_trunc %d %f\n", i, b->data[i]);
			return 0;
		}
	}
	return 1;
}

#if 0
static mfp_sample 
mfp_block_prefix_sum_dumb(mfp_block * deltas, mfp_sample scale, mfp_sample initval, mfp_block * out)
{
	int loc = 0;
	int end = out->blocksize;
	double accum = initval;
	double buf;
	float zero = 0.0;
	v4sf fv_1, fv_2, fv_3;
	__v4sf zeros = (__v4sf) { 0.0, 0.0, 0.0, 0.0 };
	__v4sf scaler = { scale, scale, scale, scale };

	if(deltas == NULL) {
		for(loc = 0; loc < end; loc++) {
			out->data[loc] = (mfp_sample)accum;
			accum += (double)scale;
		}
	}
	else {
		for(; loc < end; loc += 4) {
			/* A+I, B, C, D */
			fv_1.v = __builtin_ia32_loadups(deltas->data + loc);
			fv_1.v = fv_1.v * scaler;
			fv_1.f[0] += accum;

			/* 0, A+I, B, C */
			fv_2.v = __builtin_ia32_shufps(fv_1.v, fv_1.v, 0x60);
			fv_2.f[0] = 0.0;

			/* A+I, A+B+I, B+C, C+D */
			fv_3.v = fv_1.v + fv_2.v;

			/* 0, 0, A+I, A+B+I */
			fv_1.v = __builtin_ia32_shufps(zeros, fv_3.v, 0x40);
			
			/* A+I, A+B+I, A+B+C+I, A+B+C+D+I */
			fv_2.v = fv_3.v + fv_1.v;
			accum = fv_2.f[3];
			__builtin_ia32_storeups(out->data + loc, fv_2.v);
		}
	}
	return accum;
}
#endif

static mfp_sample 
mfp_block_prefix_sum_naive(mfp_block * deltas, mfp_sample scale, mfp_sample initval, mfp_block * out)
{
	int loc = 0;
	int end = out->blocksize;
	double accum = initval;

	if(deltas == NULL) {
		for(loc = 0; loc < end; loc++) {
			accum += (double)scale;
			out->data[loc] = (mfp_sample)accum;
		}
		return accum;
	}
	else {
		for(loc = 0; loc < end; loc++) {
			accum += (deltas->data[loc]*(double)scale);
			out->data[loc] = (mfp_sample)accum;
		}
		return accum;
	}
}

int
benchmark_block_prefix_sum(void)
{
	struct timeval start, end;
	float naive, fast;
	mfp_block * in = mfp_block_new(65536);
	mfp_block * out = mfp_block_new(65536);
	int scount;
	mfp_sample * sample = in->data;

	/* random data */
	for(scount=0; scount < in->blocksize; scount++) {
		*sample++ = (float)(1.0 - 2.0*(double)random() / ((double)RAND_MAX));
	}

	gettimeofday(&start, NULL);
	/* time naive implementation */
	for(scount=0; scount < 1000; scount ++) {
		mfp_block_prefix_sum_naive(in, 1.0, 0.0, out);
	}
	gettimeofday(&end, NULL);

	naive = (end.tv_sec + end.tv_usec/1000000.0)-(start.tv_sec+start.tv_usec/1000000.0);

	gettimeofday(&start, NULL);
	for(scount=0; scount < 1000; scount ++) {
		mfp_block_prefix_sum(in, 1.0, 0.0, out);
	}
	gettimeofday(&end, NULL);

	fast = (end.tv_sec + end.tv_usec/1000000.0)-(start.tv_sec+start.tv_usec/1000000.0);
	printf("\n     Naive: %f, fast: %f\n", naive, fast);
	return 1;
}



int
test_block_prefix_sum()
{
	int i;
	mfp_block *b = mfp_block_new(8);

	mfp_block_fill(b, 10.0);
	mfp_block_prefix_sum(b, 0.50, 1.0, b);

	for(i=0; i< 8; i++) {
		if (b->data[i] != (i+1)*5.0 +1.0) {
			printf("FAIL: block_prefix_sum %d %f\n", i, b->data[i]);
			return 0;
		}
	}

	return 1;

}

int
test_block_ramp(void)
{
	int i;
	mfp_block *b = mfp_block_new(8);

	mfp_block_ramp(b, 1.0, 1.0);

	for(i=0; i< 8; i++) {
		if (b->data[i] != i + 1.0) {
			printf("FAIL: block_ramp %d %f\n", i, b->data[i]);
			return 0;
		}
	}
}


int
test_block_fmod(void)
{
	int i;
	mfp_block *b = mfp_block_new(1024);

	mfp_block_ramp(b, 0.0, 2.0*M_PI/44.10);
	mfp_block_fmod(b, 2.0*M_PI, b);

	for(i=0; i< 8; i++) {
		if (fabs(b->data[i] - fmod(i*2.0*M_PI/44.1, 2.0*M_PI)) > 0.001) {
			printf("FAIL: block_fmod %d %f %f\n", i, fmod(i*2.0*M_PI/44.1, 2.0*M_PI), b->data[i]);
			return 0;
		}
	}
	return 1;
}

