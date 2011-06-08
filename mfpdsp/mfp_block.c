
#include "mfp_block.h"

mfp_block * 
mfp_block_new(int blocksize) 
{
	mfp_block * b = g_malloc(sizeof(mfp_block));
	b->data = g_malloc(blocksize * sizeof(float));
	b->blocksize = blocksize;
	b->allocsize = blocksize;
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
mfp_block_const_mul(mfp_block * in, float constant, mfp_block * out) 
{
	int loc = 0;
	int end = in->blocksize;
	__v4sf cval = (__v4sf) { constant, constant, constant, constant }; 

	for(; loc < end; loc+=4) {
		__builtin_ia32_storeups(out->data + loc, 
								__builtin_ia32_mulss(cval, __builtin_ia32_loadups(in->data+loc)));
	}
}


int
mfp_block_const_add(mfp_block * in, float constant, mfp_block * out) 
{
	int loc = 0;
	int end = in->blocksize;
	__v4sf cval = (__v4sf) { constant, constant, constant, constant }; 

	for(; loc < end; loc+=4) {
		__builtin_ia32_storeups(out->data + loc, 
								__builtin_ia32_addss(cval, __builtin_ia32_loadups(in->data+loc)));
	}
}

int
mfp_block_index_fetch(mfp_block * indexes, float * base, mfp_block * out) 
{
	int loc = 0;
	int end = in->blocksize;

	for(; loc < end; loc++) {
		out->data[loc] = base[(int)(indexes->data[loc])];
	}
}

int
mfp_block_zero(mfp_block * b) 
{
	memset(b->data, 0, b->blocksize*sizeof(float));
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
			v4 = __builtin_ia32_mulss(v1, v2)

			__builtin_ia32_storeups(out->data + loc, 
									__builtin_ia32_addss(v0, __builtin_ia32_mulss(v3, v4))); 
		}
	}
	else {
		for(; loc < end; loc+=4) {
			v0 = __builtin_ia32_loadups(out->data + loc);
			v1 = __builtin_ia32_loadups(in_1->data + loc);
			v2 = __builtin_ia32_loadups(in_2->data + loc);
			v4 = __builtin_ia32_mulss(v1, v2)

			__builtin_ia32_storeups(out->data + loc, __builtin_ia32_addss(v0, v4))
		}
	}

}

int
mfp_block_trunc(mfp_block * in, mfp_block * out) 
{
	int loc = 0;
	int end = in->blocksize;

	for(; loc < end; loc+=4) {
		__builtin_ia32_storeups(out->data + loc, 
								__builtin_ia32_roundps(__builtin_ia32_loadups(in->data+loc),
													   _MM_FROUND_FLOOR));	
	}
}

int
mfp_block_copy(mfp_block * in, mfp_block * out)
{
	if (out->blocksize != in->blocksize) {
		mfp_block_resize(out, in->blocksize);
	}
	g_memcpy(out->data, in->data, in->blocksize*sizeof(float));

}
