
#include <stdio.h>
#include <string.h>
#include <sys/time.h>
#include <stdlib.h>
#include <glib.h>
#include <math.h>

#include "mfp_dsp.h"

typedef struct {
    mfp_block * alloc_buffer;
    int alloc_ready; 

    mfp_block * delay_buffer;
    int buf_zero; 
    int min_blk;

    float const_delay_ms;
} builtin_delay_data;

static int 
process(mfp_processor * proc) 
{
    builtin_delay_data * pdata = (builtin_delay_data *)proc->data;
    mfp_sample * inptr; 
    mfp_sample * outptr; 
    mfp_sample * delptr;
    mfp_sample * bufptr;
    int outpos; 
    int calcind;
    int delay_samples = (int)(pdata->const_delay_ms * proc->context->samplerate / 1000.0);
    int delblk_size = pdata->delay_buffer->blocksize;
    int delblk;
    
    if (mfp_proc_has_input(proc, 1)) {
        delptr = proc->inlet_buf[1]->data;
    }
    else {
        delptr = NULL;
    }

    if (pdata->min_blk == 1) {
        delay_samples = MAX(proc->context->blocksize, delay_samples);
    }

    delay_samples = MIN(delblk_size, delay_samples);

    outptr = proc->outlet_buf[0]->data;
    inptr = proc->inlet_buf[0]->data;
    bufptr = pdata->delay_buffer->data;
    delblk = pdata->delay_buffer->blocksize;

    for(outpos=0; outpos < proc->context->blocksize; outpos++) {
        if (delptr != NULL) {
            delay_samples = MIN(delblk_size-1, 
                                MAX(0, (int)(*delptr * proc->context->samplerate / 1000.0)));
        }
        calcind = outpos - delay_samples;
        if (calcind >= 0) {
            *outptr++ = inptr[calcind];
        }
        else {
            *outptr++ = bufptr[(pdata->buf_zero + delblk + calcind) % delblk]; 
        }
    }

    /* now copy some input into the buffer */
    if (pdata->delay_buffer->blocksize <= proc->inlet_buf[0]->blocksize) {
        pdata->buf_zero = 0;
        memcpy(pdata->delay_buffer->data, 
               proc->inlet_buf[0]->data + proc->inlet_buf[0]->blocksize 
                - pdata->delay_buffer->blocksize, 
               delblk_size * sizeof(mfp_sample));
    }
    else {
        memcpy(pdata->delay_buffer->data + pdata->buf_zero, 
               proc->inlet_buf[0]->data, proc->inlet_buf[0]->blocksize * sizeof(mfp_sample));
        pdata->buf_zero += proc->inlet_buf[0]->blocksize; 
        pdata->buf_zero = pdata->buf_zero % delblk_size;
    }

    return 0;
}

static void 
init(mfp_processor * proc) 
{
    builtin_delay_data * p = g_malloc0(sizeof(builtin_delay_data));
    proc->data = p;
    p->delay_buffer = mfp_block_new(mfp_max_blocksize);
    p->alloc_buffer = mfp_block_new(mfp_max_blocksize);
    p->min_blk = 0;
    p->alloc_ready = ALLOC_IDLE;
    p->const_delay_ms = 0.0;
    p->buf_zero = 0;

    return;
}

static void 
init_blk(mfp_processor * proc) 
{
    builtin_delay_data * p = g_malloc0(sizeof(builtin_delay_data));
    proc->data = p;
    p->delay_buffer = mfp_block_new(mfp_max_blocksize);
    p->alloc_buffer = mfp_block_new(mfp_max_blocksize);
    p->min_blk = 1;
    p->alloc_ready = ALLOC_IDLE;
    p->const_delay_ms = 0.0;
    p->buf_zero = 0;

    return;
}

static void
destroy(mfp_processor * proc) 
{
    if (proc->data != NULL) {
        g_free(proc->data);
        proc->data = NULL;
    }
    return;
}

static int
config(mfp_processor * proc) 
{
    builtin_delay_data * pdata = (builtin_delay_data *)proc->data;
    gpointer delay_ptr = g_hash_table_lookup(proc->params, "_sig_1");
    gpointer bufsize_ptr = g_hash_table_lookup(proc->params, "bufsize");
    mfp_block * tmp;
    float buf_ms;
    int buf_samples; 
    int config_handled = 1;

    if(delay_ptr != NULL) {
        pdata->const_delay_ms = *(float *)delay_ptr;
    }

    if (bufsize_ptr != NULL) {
        buf_ms = *(float *)(bufsize_ptr);
        buf_samples = buf_ms * proc->context->samplerate / 1000.0;
        buf_samples = ((int)(buf_samples / proc->context->blocksize) + 1) * proc->context->blocksize;

        if (pdata->min_blk == 1) {
            buf_samples = MAX(proc->context->blocksize, buf_samples);
        }

        if (buf_samples < (pdata->delay_buffer->allocsize)) {
            mfp_block_resize(pdata->delay_buffer, buf_samples);
        }
        else if ( buf_samples > (pdata->delay_buffer->allocsize)) {
            if (pdata->alloc_ready == ALLOC_READY) {
                tmp = pdata->delay_buffer;
                pdata->delay_buffer = pdata->alloc_buffer;
                pdata->alloc_buffer = tmp;
                pdata->alloc_ready = ALLOC_IDLE;
                mfp_block_zero(pdata->delay_buffer);
            }
            else if (pdata->alloc_ready == ALLOC_IDLE) {
                pdata->alloc_buffer->blocksize = buf_samples;
                mfp_alloc_allocate(proc, pdata->alloc_buffer, &(pdata->alloc_ready));
                config_handled = 0;
            }
            else if (pdata->alloc_ready == ALLOC_WORKING) {
                config_handled = 0;
            }
        }
    } 

    return config_handled;
}


static void 
alloc(mfp_processor * proc, void * alloc_data) 
{
    mfp_block * alloc_block = (mfp_block *)alloc_data;
    mfp_block_resize(alloc_block, alloc_block->blocksize);
}


mfp_procinfo *  
init_builtin_delay(void) {
    mfp_procinfo * p = g_malloc0(sizeof(mfp_procinfo));

    p->name = strdup("del~");
    p->is_generator = GENERATOR_NEVER;
    p->process = process;
    p->init = init;
    p->destroy = destroy;
    p->config = config;
    p->alloc = alloc;
    p->params = g_hash_table_new_full(g_str_hash, g_str_equal, NULL, NULL);
    g_hash_table_insert(p->params, "_sig_1", (gpointer)PARAMTYPE_FLT);
    g_hash_table_insert(p->params, "bufsize", (gpointer)PARAMTYPE_FLT);

    return p;
}

mfp_procinfo *  
init_builtin_delblk(void) {
    mfp_procinfo * p = g_malloc0(sizeof(mfp_procinfo));

    p->name = strdup("delblk~");
    p->is_generator = GENERATOR_ALWAYS;
    p->process = process;
    p->init = init_blk;
    p->destroy = destroy;
    p->config = config;
    p->alloc = alloc;
    p->params = g_hash_table_new_full(g_str_hash, g_str_equal, NULL, NULL);
    g_hash_table_insert(p->params, "_sig_1", (gpointer)PARAMTYPE_FLT);
    g_hash_table_insert(p->params, "bufsize", (gpointer)PARAMTYPE_FLT);

    return p;
}


