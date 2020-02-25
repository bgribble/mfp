#include <stdio.h>
#include <string.h>
#include <glib.h>

#include "mfp_dsp.h"

#define HOLD_THRESH ((mfp_sample)0.01)

typedef struct {
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
            if (*in_1++ < HOLD_THRESH) {
                d->hold_value = *in_0++;
            }
            else {
                in_0++;
            }
            *outbuf++ = d->hold_value;
        }
    }
    else if (in_0_present) {
        for(int scount=0; scount < proc->context->blocksize; scount++) {
            if (!const_in_1) {
                d->hold_value = *in_0++;
            }
            else {
                in_0++;
            }
            *outbuf++ = d->hold_value;
        }
    }
    else {
        if (!const_in_1) {
            d->hold_value = const_in_0;
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
    gpointer sig_0_ptr = g_hash_table_lookup(proc->params, "_sig_0");
    gpointer sig_1_ptr = g_hash_table_lookup(proc->params, "_sig_1");

    builtin_hold_data * d = (builtin_hold_data *)(proc->data);

    if (sig_0_ptr != NULL) {
        d->const_in_0 = (mfp_sample)(*(float *)sig_0_ptr);
    }
    if (sig_1_ptr != NULL) {
        d->const_in_1 = (mfp_sample)(*(float *)sig_1_ptr);
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
    g_hash_table_insert(p->params, "_sig_0", (gpointer)PARAMTYPE_FLT);
    g_hash_table_insert(p->params, "_sig_1", (gpointer)PARAMTYPE_FLT);
    return p;
}


