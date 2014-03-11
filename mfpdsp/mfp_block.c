#include <math.h>
#include <stdlib.h>
#include <stdio.h>
#ifdef MFP_USE_SSE
#include <x86intrin.h>
#endif
#include <glib.h>
#include <string.h>

#include "mfp_dsp.h"
#include "mfp_block.h"

#ifdef MFP_USE_SSE 
int mfp_block_use_sse = 1;
static int mfp_block_compiled_with_sse = 1;
#else
int mfp_block_use_sse = 0;
static int mfp_block_compiled_with_sse = 0;
#endif 

mfp_block * 
mfp_block_new(int blocksize) 
{
    mfp_block * b = g_malloc(sizeof(mfp_block));
    gpointer buf;
    int allocbytes = (int)(ceil(blocksize / 4.0)) * sizeof(float) * 4;

    posix_memalign(&buf, 16, allocbytes);

    mfp_block_init(b, buf, blocksize, allocbytes/4);
    return b;
}

void
mfp_block_init(mfp_block * block, mfp_sample * data, int blocksize, int allocsize) 
{
    block->data = data; 
    block->blocksize = blocksize;
    block->allocsize = allocsize;

    if(data == NULL) {
        printf("mfp_block_init: WARNING: data pointer NULL, blocksize=%d\n", blocksize);
        block->blocksize = 0;
        block->allocsize = 0;
    }

    if (((long)data & (long)0xf) == 0) {
        block->aligned = 1;
    }
    else {
        printf("mfp_block_init: WARNING: data pointer unaligned, %p\n", data);
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
    int allocbytes = (int)(ceil(newsize / 4.0)) * sizeof(float) * 4;

    if (newsize <= in->allocsize) {
        in->blocksize = newsize;
    }
    else {
        free(in->data);
        posix_memalign((void **)(&(in->data)), 16, allocbytes);
        in->blocksize = newsize;
        in->allocsize = allocbytes/4;
        in->aligned = 1;
    }
}

int
mfp_block_const_mul(mfp_block * in, mfp_sample constant, mfp_block * out) 
{
    if (mfp_block_use_sse && mfp_block_compiled_with_sse) { 
#ifdef MFP_USE_SSE 
        __v4sf cval, ival;
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
#endif
    }
    else { 
        mfp_sample * iptr, * optr, *iend;
        if (mfp_block_use_sse) 
            printf("WARNING: Compiled without SSE but trying to use it at runtime!\n");
        iptr = in->data;
        iend = in->data + in->blocksize;
        optr = out->data;
        for(; iptr < iend; iptr++) {
            *optr = *iptr * constant;
            optr++;
        }
    }
    return 1;
}


int
mfp_block_const_add(mfp_block * in, mfp_sample constant, mfp_block * out) 
{
    if (mfp_block_use_sse && mfp_block_compiled_with_sse) { 
#ifdef MFP_USE_SSE
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
#endif
    }
    else {
        mfp_sample * iptr, * optr, * iend;
        if (mfp_block_use_sse) 
            printf("WARNING: Compiled without SSE but trying to use it at runtime!\n");
        iptr = in->data;
        iend = in->data + in->blocksize;
        optr = out->data;
        for(; iptr < iend; iptr++) {
            *optr = *iptr + constant;
            optr++;
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
    if (mfp_block_use_sse && mfp_block_compiled_with_sse) { 
#ifdef MFP_USE_SSE
        int loc = 0;
        int end = in->blocksize;
        __v4sf cval = (__v4sf) { constant, constant, constant, constant }; 

        for(; loc < end; loc+=4) {
            __builtin_ia32_storeups(in->data + loc, cval);
        }
#endif
    }
    else {
        mfp_sample * iptr, * iend;
        if (mfp_block_use_sse) 
            printf("WARNING: Compiled without SSE but trying to use it at runtime!\n");
        iptr = in->data;
        iend = in->data + in->blocksize;
        for(; iptr < iend; iptr++) {
            *iptr = constant;
        }
    }
    return 1;
}

int
mfp_block_fmod(mfp_block * in, mfp_sample modulus, mfp_block * out) 
{
    if (mfp_block_use_sse && mfp_block_compiled_with_sse) { 
#ifdef MFP_USE_SSE 
        int loc;
        int end = in->blocksize;
        double outv[2];
        __v2df cval = (__v2df) { modulus, modulus };
        __v2df xmm0, xmm1;
        __v4si xmm2;
        for(loc = 0; loc < end; loc += 2) {
            xmm0 = __builtin_ia32_cvtps2pd(*(__v4sf *)(in->data+loc));
            xmm1 = xmm0;
            xmm1 = xmm1 / cval;
            xmm2 = __builtin_ia32_cvttpd2dq(xmm1);
            xmm1 = __builtin_ia32_cvtdq2pd(xmm2);
            xmm1 = xmm1 * cval;
            xmm0 = xmm0 - xmm1;
            *(__v2df *)outv = xmm0;
            out->data[loc] = (float)(outv[0]);
            out->data[loc+1] = (float)(outv[1]);
        }
#endif
    }
    else {
        mfp_sample * iptr, * optr, * iend;
        if (mfp_block_use_sse) 
            printf("WARNING: Compiled without SSE but trying to use it at runtime!\n");
        iptr = in->data;
        iend = in->data + in->blocksize;
        optr = out->data;
        for(; iptr < iend; iptr++) {
            *optr = fmodf(*iptr, modulus);
            optr++;
        }
    }
    return 1;
}

int
mfp_block_mac(mfp_block * in_1, mfp_block * in_2, mfp_block * in_3, mfp_block * out)
{
    if (mfp_block_use_sse && mfp_block_compiled_with_sse) { 
#ifdef MFP_USE_SSE
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
#endif
    }
    else {
        mfp_sample * i1, * i2, * i3, *optr, * iend;
        i1 = in_1->data;
        i2 = in_2->data;
        iend = in_1->data + in_1->blocksize;
        optr = out->data;
        if (in_3 != NULL) {
            i3 = in_3->data;
            for(; i1 < iend; i1++) {
                *optr = *optr + *i1 * *i2 * *i3;
                optr++;
                i2++;
                i3++;            
            }
        }
        else {
            for(; i1 < iend; i1++) {
                *optr = *optr + *i1 * *i2 ;
                optr++;
                i2++;
            }
        }
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

#ifdef MFP_USE_SSE
typedef float fv4[4] __attribute__ ((aligned(16)));
#endif

double
mfp_block_phase(mfp_block * out, mfp_sample initval, double incr, double phase_limit)
{
    mfp_sample * optr = out->data, * iend;
    double scratch = initval;

    optr = out->data;
    iend = out->data + out->blocksize;
    for(; optr < iend; optr++) {
        *optr = (mfp_sample)scratch;
        scratch += incr;
        if (scratch > phase_limit) {
            scratch = fmod(scratch, phase_limit);
        }
    }
    return scratch;
}

double
mfp_block_ramp(mfp_block * out, mfp_sample initval, double incr)
{
    mfp_sample * optr = out->data, * iend;
    double scratch = initval;
    optr = out->data;
    iend = out->data + out->blocksize;
    for(; optr < iend; optr++) {
        *optr = (mfp_sample)scratch;
        scratch += incr;
    }
    return scratch;
}

double
mfp_block_prefix_sum(mfp_block * in, mfp_sample scale, mfp_sample initval, mfp_block * out)
{
    if (mfp_block_use_sse && mfp_block_compiled_with_sse) { 
#ifdef MFP_USE_SSE
        float * inptr, * outptr, * endptr;
        fv4 scratch = { 0.0, 0.0, 0.0, 0.0 };
        __v4sf xmm0, xmm1, xmm2;
        __v4sf zeros = (__v4sf) { 0.0, 0.0, 0.0, 0.0 };
        __v4si mask = (__v4si) { 0x00, 0xffffffff, 0xffffffff, 0xffffffff }; 
        __v4sf scaler = { scale, scale, scale, scale };

        endptr = in->data + in->blocksize;
        outptr = out->data;
        scratch[0] = initval;

        /* xmm1 gets carry in */
        xmm1 = *(__v4sf *)scratch;

        for(inptr = in->data; inptr < endptr; inptr += 4) {
            /* xmm0 gets A+I, B, C, D */
            xmm0 = *(__v4sf *)inptr;
            xmm0 = __builtin_ia32_mulps(xmm0, scaler);
            xmm0 = __builtin_ia32_addss(xmm0, xmm1);

            /* xmm2 gets 0, A+I, B, C */
            xmm2 = xmm0;
            xmm2 = __builtin_ia32_shufps(xmm2, xmm2, 0x60);
            xmm2 = __builtin_ia32_andps(xmm2, (__v4sf)mask);

            /* xmm2 gets A+I, A+B+I, B+C, C+D */
            xmm2 = __builtin_ia32_addps(xmm2, xmm0);

            /* xmm0 gets 0, 0, A+I, A+B+I */
            xmm0 = zeros;
            xmm0 = __builtin_ia32_shufps(xmm0, xmm2, 0x40);

            /* xmm0 gets A+I, A+B+I, A+B+C+I, A+B+C+D+I */
            xmm0 = __builtin_ia32_addps(xmm0, xmm2);

            /* preparing for next iteration, xmm1 gets carry */
            xmm1 = xmm0;
            xmm1 = __builtin_ia32_shufps(xmm1, xmm1, 0xff);

            *(__v4sf *)outptr = xmm0;

            outptr += 4;
        }
        *(__v4sf *)&scratch = xmm1;
        return scratch[0];
#endif
    }
    else {
        mfp_sample * iptr, * optr, * iend, accum=initval;
        iptr = in->data;
        iend = in->data + in->blocksize;
        optr = out->data;
        for(; iptr < iend; iptr++) {
            accum += *iptr * scale;
            *optr = accum; 
            optr++;
        }
        return accum;
    }
}

int
mfp_block_mul(mfp_block * in_1, mfp_block * in_2, mfp_block * out)
{
    if (mfp_block_use_sse && mfp_block_compiled_with_sse) { 
#ifdef MFP_USE_SSE
        int loc = 0;
        int end = in_1->blocksize;    
        __v4sf xmm0, xmm1;

        for(; loc < end; loc+=4) {
            xmm0 = *(__v4sf *)(in_1->data + loc);
            xmm1 = *(__v4sf *)(in_2->data + loc);
            xmm0 = xmm0 * xmm1;
            *(__v4sf *)(out->data + loc) = xmm0;
        }
#endif
    }
    else {
        mfp_sample * i1, * i2, *optr, * iend;
        i1 = in_1->data;
        i2 = in_2->data;
        iend = in_1->data + in_1->blocksize;
        optr = out->data;
        for(; i1 < iend; i1++) {
            *optr++ =  *i1 * *i2;
            i2++;
        }
    }
    return 1;
}

int
mfp_block_add(mfp_block * in_1, mfp_block * in_2, mfp_block * out)
{
    if (mfp_block_use_sse && mfp_block_compiled_with_sse) { 
#ifdef MFP_USE_SSE
        int loc = 0;
        int end = in_1->blocksize;    
        __v4sf xmm0, xmm1;

        for(; loc < end; loc+=4) {
            xmm0 = *(__v4sf *)(in_1->data + loc);
            xmm1 = *(__v4sf *)(in_2->data + loc);
            xmm0 = xmm0 + xmm1;
            *(__v4sf *)(out->data + loc) = xmm0;
        }
#endif
    }
    else {
        mfp_sample * i1, * i2, *optr, * iend;

        i1 = in_1->data;
        i2 = in_2->data;
        iend = in_1->data + in_1->blocksize;
        optr = out->data;
        for(; i1 < iend; i1++) {
            *optr++ =  *i1 + *i2;
            i2++;
        }
    }
    return 1;

}

int
mfp_block_trunc(mfp_block * in, mfp_block * out) 
{
    if (mfp_block_use_sse && mfp_block_compiled_with_sse) { 
#ifdef MFP_USE_SSE
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
#endif
    }
    else {
        mfp_sample * inptr = in->data, * optr = out->data;
        mfp_sample * iend = in->data + in->blocksize;
        for (; inptr < iend; inptr++) {
            *optr = truncf(*inptr);
            optr++;
        }
    }
    return 1;
}

