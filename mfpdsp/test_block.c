
#include <stdio.h>

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

