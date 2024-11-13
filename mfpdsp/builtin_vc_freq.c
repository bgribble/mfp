#include <math.h>
#include <stdio.h>
#include <string.h>
#include <glib.h>

#include "mfp_dsp.h"

typedef struct {
    mfp_sample const_signal;
    double base_freq;
} builtin_vc_freq_data;

static int
config(mfp_processor * proc)
{
    builtin_vc_freq_data * pdata = (builtin_vc_freq_data *)proc->data;
    GArray * base_raw = (GArray *)g_hash_table_lookup(proc->params, "base_freq");
    gpointer const_ptr = g_hash_table_lookup(proc->params, "_sig_0");

    /* populate new segment data if passed */
    if (base_raw != NULL) {
        pdata->base_freq = (double)(*(double *)base_raw);
        g_hash_table_remove(proc->params, "base_freq");
    }
    if (const_ptr != NULL) {
        pdata->const_signal = (double)(*(double *)const_ptr);
    }

    return 1;
}

static int
process_vc_freq(mfp_processor * proc)
{
    builtin_vc_freq_data * data = ((builtin_vc_freq_data *)(proc->data));
    mfp_sample * input = proc->inlet_buf[0]->data;
    mfp_sample * output = proc->outlet_buf[0]->data;
    double base = data->base_freq;
    double inval;
    int use_const = 1;

    if ((input == NULL) || (data == NULL)) {
        mfp_block_zero(proc->outlet_buf[0]);
        return 0;
    }

    if (mfp_proc_has_input(proc, 0)) {
        use_const = 0;
    }

    /* iterate */
    for(int scount=0; scount < proc->context->blocksize; scount++) {
        if (use_const) {
            inval = (double)data->const_signal;
        }
        else {
            inval = (double)(*input++);
        }
        *output++ = (mfp_sample)(base * pow((double)2.0, inval));
    }

    return 0;
}

static void
init(mfp_processor * proc)
{
    builtin_vc_freq_data * p = g_malloc0(sizeof(builtin_vc_freq_data));
    proc->data = p;

}

static void
destroy(mfp_processor * proc)
{
    builtin_vc_freq_data * p;
    if (proc->data != NULL) {
        g_free(proc->data);
        proc->data = NULL;
    }
}


mfp_procinfo *
init_builtin_vc_freq(void) {
    mfp_procinfo * p = g_malloc0(sizeof(mfp_procinfo));
    p->name = strdup("vcfreq~");
    p->is_generator = GENERATOR_CONDITIONAL;
    p->process = process_vc_freq;
    p->init = init;
    p->destroy = destroy;
    p->config = config;
    p->params = g_hash_table_new_full(g_str_hash, g_str_equal, NULL, NULL);
    g_hash_table_insert(p->params, "base_freq", (gpointer)PARAMTYPE_FLT);
    g_hash_table_insert(p->params, "_sig_0", (gpointer)PARAMTYPE_FLT);

    return p;
}
