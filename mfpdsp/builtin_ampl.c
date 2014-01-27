
#include <stdio.h>
#include <string.h>
#include <sys/time.h>
#include <stdlib.h>
#include <glib.h>
#include <math.h>

#include "mfp_dsp.h"

typedef struct {
    /* configurable params */
    float peak_decay_ms;
    float rms_window_ms;

    /* runtime state */ 
    mfp_block * rms_buffer;
    mfp_block * rms_alloc;
    int       rms_alloc_ready; 
    int       rms_pointer;
    double    last_peak;
    double    rms_accum;
} builtin_ampl_data;

static int 
process(mfp_processor * proc) 
{
    builtin_ampl_data * pdata = (builtin_ampl_data *)proc->data;
    mfp_sample * in_sample = proc->inlet_buf[0]->data;
    mfp_sample * rms_sample = proc->outlet_buf[0]->data;
    mfp_sample * peak_sample = proc->outlet_buf[1]->data;
    mfp_sample * rms_buffer = pdata->rms_buffer->data + pdata->rms_pointer;
    mfp_sample * rms_bufend = pdata->rms_buffer->data + pdata->rms_buffer->blocksize;
    mfp_sample sample;
    double peak_slope = 1000.0/((double)pdata->peak_decay_ms * 
                                (double)(proc->context->samplerate));
    double peak = pdata->last_peak;
    double rms_accum = pdata->rms_accum;
    double rms_scale = 1.0 / (pdata->rms_buffer->blocksize);
    double sqr_sample;
    int scount; 

    if ((in_sample == NULL) || (rms_sample == NULL) || (peak_sample == NULL)) {
        return 0;
    }

    for(scount = 0; scount < proc->context->blocksize; scount++) {
        sample = *in_sample++;

        /* peak */
        if (fabs(sample) > (peak - peak_slope)) {
            peak = fabs(sample);
        }
        else {
            peak -= peak_slope;
        }
        *peak_sample++ = (float)peak;

        /* rms (not really, this is super ghetto) */
        sqr_sample = sample * sample;
        rms_accum = rms_accum + sqr_sample - *rms_buffer;
        *rms_buffer++ = sqr_sample; 
        if (rms_accum < 0) {
            rms_accum = 0.0;
        }

        *rms_sample++ = (mfp_sample)sqrt(rms_accum * rms_scale); 
        pdata->rms_pointer ++;             

        if(rms_buffer >= rms_bufend) {
            rms_buffer = pdata->rms_buffer->data;
            pdata->rms_pointer = 0;
        }

    }

    /* save state */
    pdata->last_peak = peak;
    pdata->rms_accum = rms_accum;

    return 0;
}

static void 
init(mfp_processor * proc) 
{
    builtin_ampl_data * p = g_malloc(sizeof(builtin_ampl_data));
    proc->data = p;
    p->peak_decay_ms = 200;
    p->last_peak = 0.0;
    p->rms_window_ms = 20;
    p->rms_buffer = mfp_block_new((int)(20 * proc->context->samplerate / 1000.0));
    p->rms_alloc = mfp_block_new((int)(20 * proc->context->samplerate / 1000.0));
    p->rms_alloc_ready = ALLOC_IDLE;
    p->rms_accum = 0.0;
    p->rms_pointer = 0;

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

static void
alloc(mfp_processor * proc, void * alloc_data)
{
    mfp_block * allocblk = (mfp_block *)alloc_data;
    mfp_block_resize(allocblk, allocblk->blocksize);
}


static int
config(mfp_processor * proc) 
{
    builtin_ampl_data * pdata = (builtin_ampl_data *)proc->data;
    gpointer peak_decay_ptr = g_hash_table_lookup(proc->params, "peak_decay");
    gpointer rms_window_ptr = g_hash_table_lookup(proc->params, "rms_window");
    mfp_block * tmp;
    float rms_window; 
    int rms_samples;
    int config_handled = 1;

    if(peak_decay_ptr != NULL) {
        pdata->peak_decay_ms = *(float *)peak_decay_ptr;
    }

    if(rms_window_ptr != NULL) {
        rms_window = *(float *)rms_window_ptr;
        rms_samples = (int)(rms_window * proc->context->samplerate / 1000.0);
        if (rms_samples < pdata->rms_buffer->allocsize) {
            mfp_block_resize(pdata->rms_buffer, rms_samples);
            pdata->rms_accum = 0.0;
            pdata->rms_pointer = 0;
            pdata->rms_window_ms = rms_window; 
        }
        else if (rms_samples > pdata->rms_buffer->allocsize) {
            if (pdata->rms_alloc_ready == ALLOC_READY) {
                tmp = pdata->rms_buffer;
                pdata->rms_buffer = pdata->rms_alloc;
                pdata->rms_alloc = tmp; 
                pdata->rms_accum = 0.0;
                pdata->rms_window_ms = rms_window;
                pdata->rms_pointer = 0;
                mfp_block_zero(pdata->rms_buffer);
            }
            else if (pdata->rms_alloc_ready == ALLOC_IDLE) {
                pdata->rms_alloc->blocksize = rms_samples;
                mfp_alloc_allocate(proc, pdata->rms_alloc, &(pdata->rms_alloc_ready));
                config_handled = 0;
            }
            else if (pdata->rms_alloc_ready == ALLOC_WORKING) {
                config_handled = 0;
            }
        }

    }

    return config_handled;
}

mfp_procinfo *  
init_builtin_ampl(void) {
    mfp_procinfo * p = g_malloc0(sizeof(mfp_procinfo));

    p->name = strdup("ampl~");
    p->is_generator = 0;
    p->process = process;
    p->init = init;
    p->destroy = destroy;
    p->config = config;
    p->alloc = alloc;
    p->params = g_hash_table_new_full(g_str_hash, g_str_equal, NULL, NULL);
    g_hash_table_insert(p->params, "peak_decay", (gpointer)PARAMTYPE_FLT);
    g_hash_table_insert(p->params, "rms_window", (gpointer)PARAMTYPE_FLT);

    return p;
}


