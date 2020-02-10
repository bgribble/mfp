#include <math.h>
#include <stdio.h>
#include <string.h>
#include <glib.h>

#include "mfp_dsp.h"

#define NUM_SEMITONES 12
#define VOCT_SEMITONE ((mfp_sample)(1.0 / 12.0))

typedef struct {
    double freq_base;
} builtin_vc_freq_data;

static int
config(mfp_processor * proc) 
{
    builtin_vc_freq_data * pdata = (builtin_vc_freq_data *)proc->data;
    GArray * base_raw = (GArray *)g_hash_table_lookup(proc->params, "base");

    /* populate new segment data if passed */
    if (base_raw != NULL) {
        pdata->freq_base = (double)(*(float *)base_raw);
        g_hash_table_remove(proc->params, "base");
    }

    return 1;
}

static int 
process_vc_freq(mfp_processor * proc) 
{
    builtin_vc_freq_data * data = ((builtin_vc_freq_data *)(proc->data));
    mfp_sample * sample = proc->outlet_buf[0]->data;
    double base = data->freq_base;

    if ((sample == NULL) || (data == NULL)) {
        mfp_block_zero(proc->outlet_buf[0]);
        return 0;
    }
    
    /* iterate */ 
    for(int scount=0; scount < proc->context->blocksize; scount++) {
        *sample++ = (mfp_sample)(base * pow((double)2.0, (double)(*sample))); 
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
    g_hash_table_insert(p->params, "base", (gpointer)PARAMTYPE_FLT);

    return p;
}



