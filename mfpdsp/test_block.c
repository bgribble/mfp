
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
}


