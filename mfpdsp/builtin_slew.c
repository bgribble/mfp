#include <string.h>
#include "mfp_dsp.h" 

typedef struct { 
    double rise_time;
    double fall_time; 
    double const_signal;
    double last_val; 
} builtin_slew_data;

#define DELTA_FUDGE 0.000001

static int 
process_slew(mfp_processor * proc) 
{ 
    builtin_slew_data * pdata = (builtin_slew_data *)proc->data; 
    mfp_sample * in_sample = proc->inlet_buf[0]->data;
    mfp_sample * out_sample = proc->outlet_buf[0]->data;
    double before = pdata->last_val;
    double after; 
    double delta;
    double rise_rate = 1.0 / (.001 * pdata->rise_time * proc->context->samplerate);
    double fall_rate = 1.0 / (.001 * pdata->fall_time * proc->context->samplerate);
    int use_const = 1;

    if (mfp_proc_has_input(proc, 0)) {
        use_const = 0;
    }
    else if (fabs(pdata->last_val - pdata->const_signal) < DELTA_FUDGE){
        /* shortcut! */
        mfp_block_fill(proc->outlet_buf[0], pdata->const_signal);
        return;
    }

    for (int scount=0; scount < proc->outlet_buf[0]->blocksize; scount++) {
        if (use_const) {
            after = (double)pdata->const_signal;
        }
        else {
            after = (double)*in_sample++;
        }
        delta = after - before; 
        if (delta > 0) {
            delta = delta * rise_rate;
        }
        else if (delta < 0) { 
            delta = delta * fall_rate;
        }

        after = (before + delta); 
        *out_sample++ = (mfp_sample)after;
        before = after;
    }
    pdata->last_val = after;
}

static void
init(mfp_processor * proc)
{
    builtin_slew_data * p = g_malloc(sizeof(builtin_slew_data));
    proc->data = p; 
    p->rise_time = 100.0;
    p->fall_time = 100.0;
    p->last_val = 0.0;
    p->const_signal = 0.0;
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
    builtin_slew_data * p = (builtin_slew_data *)proc->data;
    gpointer const_ptr = g_hash_table_lookup(proc->params, "_sig_0");
    gpointer rise_ptr = g_hash_table_lookup(proc->params, "rise");
    gpointer fall_ptr = g_hash_table_lookup(proc->params, "fall");

    
    if (const_ptr != NULL) {
        p->const_signal = (double)(*(float *)const_ptr);
    }
    if (rise_ptr != NULL) {
        p->rise_time = (double)(*(float *)rise_ptr);
    }
    if (fall_ptr != NULL) {
        p->fall_time = (double)(*(float *)fall_ptr);
    }

    return 1;
}

mfp_procinfo * 
init_builtin_slew(void)
{
    mfp_procinfo * p = g_malloc0(sizeof(mfp_procinfo));
    p->name = strdup("slew~");
    p->is_generator = 0;
    p->process = process_slew;
    p->init = init;
    p->destroy = destroy;
    p->config = config;
    p->params = g_hash_table_new_full(g_str_hash, g_str_equal, NULL, NULL);
    g_hash_table_insert(p->params, "_sig_0", (gpointer)PARAMTYPE_FLT);
    g_hash_table_insert(p->params, "rise", (gpointer)PARAMTYPE_FLT);
    g_hash_table_insert(p->params, "fall", (gpointer)PARAMTYPE_FLT);
    return p;
}

