#include <string.h>
#include "mfp_dsp.h" 

typedef struct { 
    double rise_rate;
    double fall_rate; 
    double const_signal;
    mfp_sample last_val; 
} builtin_slew_data;

static int 
process(mfp_processor * proc) 
{ 
    builtin_slew_data * pdata = (builtin_slew_data *)proc->data; 
    mfp_sample * in_sample = proc->inlet_buf[0]->data;
    mfp_sample * out_sample = proc->outlet_buf[0]->data;
    mfp_sample before = pdata->last_val;
    mfp_sample after; 
    int use_const = 1;
    float delta;

    if (mfp_proc_has_input(proc, 0)) {
        use_const = 0;
    }

    for (int scount=0; scount < proc->outlet_buf[0]->blocksize; scount++) {
        if (use_const) {
            after = pdata->const_signal;
        }
        else {
            after = *in_sample++;
        }
        delta = after - before; 
        if ((delta > 0) && (delta > pdata->rise_rate)) { 
            delta = pdata->rise_rate;
        }
        if ((delta < 0) && (delta < (-1.0*pdata->fall_rate))) { 
            delta = -1.0 * pdata->fall_rate;
        }
        after = (float)(before + delta); 
        *out_sample++ = after;
        before = after;
    }
    pdata->last_val = after;
}

static void
init(mfp_processor * proc)
{
    builtin_slew_data * p = g_malloc(sizeof(builtin_slew_data));
    proc->data = p; 
    p->rise_rate = 10000.0;
    p->fall_rate = 10000.0;
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
        p->rise_rate = (double)(*(float *)rise_ptr) * proc->context->samplerate / 1000.0;
    }
    if (fall_ptr != NULL) {
        p->fall_rate = (double)(*(float *)fall_ptr) * proc->context->samplerate / 1000.0;
    }

    return 1;
}

mfp_procinfo * 
init_builtin_slew(void)
{
    mfp_procinfo * p = g_malloc0(sizeof(mfp_procinfo));
    p->name = strdup("slew~");
    p->is_generator = 0;
    p->process = process;
    p->init = init;
    p->destroy = destroy;
    p->config = config;
    p->params = g_hash_table_new_full(g_str_hash, g_str_equal, NULL, NULL);
    g_hash_table_insert(p->params, "_sig_0", (gpointer)PARAMTYPE_FLT);
    g_hash_table_insert(p->params, "rise", (gpointer)PARAMTYPE_FLT);
    g_hash_table_insert(p->params, "fall", (gpointer)PARAMTYPE_FLT);
    return p;
}

