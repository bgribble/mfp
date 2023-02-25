#include <stdio.h>
#include <string.h>
#include <glib.h>

#include "mfp_dsp.h"

#define SAMPLE_THRESH ((mfp_sample)0.05)

typedef struct {
    int param_response;
    int param_track;
    int sample_phase;
    mfp_sample hold_value;
    mfp_sample const_in_0;
    mfp_sample const_in_1;
} builtin_hold_data;

static int 
process(mfp_processor * proc) 
{
    builtin_hold_data * d = (builtin_hold_data *)(proc->data);
    mfp_sample const_in_1 = d->const_in_1;
    mfp_sample const_in_0 = d->const_in_0;
    
    mfp_sample * outbuf = proc->outlet_buf[0]->data;
    mfp_sample * in_0 = proc->inlet_buf[0]->data;
    mfp_sample * in_1 = proc->inlet_buf[1]->data;
    
    d->const_in_1 = 0;

    if ((outbuf == NULL) || (in_0 == NULL) || (in_1 == NULL))  {
        return 0;
    }

    /* pass NULL in_* if there is nothing connected */
    if (!mfp_proc_has_input(proc, 0))
        in_0 = NULL;

    if (!mfp_proc_has_input(proc, 1))
        in_1 = NULL;

    int in_0_present=((in_0 == NULL) ? 0 : 1);
    int in_1_present=((in_1 == NULL) ? 0 : 1);

    /* iterate */ 
    if (in_0_present && in_1_present) {
        for(int scount=0; scount < proc->context->blocksize; scount++) {
            if (*in_1++ < SAMPLE_THRESH) {
                d->sample_phase = 0;
                if (d->param_track) {
                    *outbuf++ = *in_0;
                }
                else {
                    *outbuf++ = d->hold_value;
                }
            }
            else {
                if (d->sample_phase == 0) {
                    d->hold_value = *in_0;
                    if (d->param_response) {
                        mfp_dsp_send_response_float(proc, 0, d->hold_value);
                    }
                }
                d->sample_phase = 1;
                *outbuf++ = d->hold_value;
            }
            in_0++;
        }
    }
    else if (in_0_present) {
        if (d->sample_phase == 0 && const_in_1) {
            d->hold_value = *in_0;
            d->sample_phase = 1;
            if (d->param_response) {
                mfp_dsp_send_response_float(proc, 0, d->hold_value);
            }
        }
        else if (d->sample_phase == 1 && !const_in_1) {
            d->sample_phase = 0;
        }

        for(int scount=0; scount < proc->context->blocksize; scount++) {
            if (!const_in_1 && d->param_track) {
                *outbuf++ = *in_0;
            }
            else  {
                *outbuf++ = d->hold_value;
            }
            in_0++;
        }
    }
    else if (in_1_present) {
        for(int scount=0; scount < proc->context->blocksize; scount++) {
            if (*in_1 < SAMPLE_THRESH) {
                d->sample_phase = 0;
                if (d->param_track) {
                    *outbuf++ = const_in_0;
                }
                else {
                    *outbuf++ = d->hold_value;
                }
            }
            else {
                if (d->sample_phase == 0) {
                    d->hold_value = const_in_0;
                    if (d->param_response) {
                        mfp_dsp_send_response_float(proc, 0, d->hold_value);
                    }
                }
                d->sample_phase = 1;
                *outbuf++ = d->hold_value;
            }
            in_1++;
        }

    }
    else {
        if (const_in_1) {
            d->hold_value = const_in_0;
            if (d->param_response) {
                mfp_dsp_send_response_float(proc, 0, d->hold_value);
            }
        }
        for(int scount=0; scount < proc->context->blocksize; scount++) {
            *outbuf++ = d->hold_value;
        }
    }

    return 1;
}

static void 
init(mfp_processor * proc) 
{
    builtin_hold_data * d = g_malloc(sizeof(builtin_hold_data));
    proc->data = d;
    
    d->hold_value = 0.0;
    d->param_track = FALSE;
    d->param_response = FALSE;
    d->const_in_0 = (mfp_sample)0.0;
    d->const_in_1 = (mfp_sample)0.0;
    return;
}

static void
destroy(mfp_processor * proc) 
{
    return;
}

static int
config(mfp_processor * proc) 
{
    gpointer track_ptr = g_hash_table_lookup(proc->params, "track");
    gpointer response_ptr = g_hash_table_lookup(proc->params, "response");
    gpointer sig_0_ptr = g_hash_table_lookup(proc->params, "_sig_0");
    gpointer sig_1_ptr = g_hash_table_lookup(proc->params, "_sig_1");

    builtin_hold_data * d = (builtin_hold_data *)(proc->data);

    if (track_ptr != NULL) {
        d->param_track = (int)(*(double *)track_ptr);
    }
    if (response_ptr != NULL) {
        d->param_response = (int)(*(double *)response_ptr);
    }
    if (sig_0_ptr != NULL) {
        d->const_in_0 = (mfp_sample)(*(double *)sig_0_ptr);
    }
    if (sig_1_ptr != NULL) {
        d->const_in_1 = (mfp_sample)(*(double *)sig_1_ptr);
        g_hash_table_remove(proc->params, "_sig_1");
    }
    else {
        d->const_in_1 = 0;
    }
    return 1;
}

mfp_procinfo *  
init_builtin_hold(void) {
    mfp_procinfo * p = g_malloc0(sizeof(mfp_procinfo));
    p->name = strdup("hold~");
    p->is_generator = 0;
    p->process = process;
    p->init = init;
    p->config = config;
    p->destroy = destroy;
    p->params = g_hash_table_new_full(g_str_hash, g_str_equal, NULL, NULL);
    g_hash_table_insert(p->params, "track", (gpointer)PARAMTYPE_FLT);
    g_hash_table_insert(p->params, "response", (gpointer)PARAMTYPE_FLT);
    g_hash_table_insert(p->params, "_sig_0", (gpointer)PARAMTYPE_FLT);
    g_hash_table_insert(p->params, "_sig_1", (gpointer)PARAMTYPE_FLT);
    return p;
}


