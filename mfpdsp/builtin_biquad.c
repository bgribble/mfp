#include <stdio.h>
#include <string.h>
#include <sys/time.h>
#include <stdlib.h>
#include <glib.h>
#include <math.h>

#include "mfp_dsp.h"

typedef struct {
    double b0;
    double b1;
    double b2;
    double a1;
    double a2;

    double delay_1;
    double delay_2; 
} builtin_biquad_data;

static int 
process(mfp_processor * proc) 
{
    builtin_biquad_data * pdata = (builtin_biquad_data *)proc->data;
    mfp_sample * in_sample = proc->inlet_buf[0]->data;
    mfp_sample * out_sample = proc->outlet_buf[0]->data;
    double tmp, w_n;
    int scount=0;

    for (; scount < proc->inlet_buf[0]->blocksize; scount++) {
        tmp = *in_sample++;
        w_n = tmp - (pdata->a1 * pdata->delay_1) - (pdata->a2 * pdata->delay_2);
        *out_sample ++ = (pdata->b0 * w_n) + (pdata->b1 * pdata->delay_1) + 
            (pdata->b2 * pdata->delay_2);
        pdata->delay_2 = pdata->delay_1; 
        pdata->delay_1 = w_n;
    }
    return 0;
    

    
}

static void 
init(mfp_processor * proc) 
{
    builtin_biquad_data * p = g_malloc(sizeof(builtin_biquad_data));
    proc->data = p;
    p->a1 = 0.0;
    p->a2 = 0.0;
    p->b0 = 1.0;
    p->b1 = 0.0;
    p->b2 = 0.0;
    p->delay_1 = 0.0;
    p->delay_2 = 0.0;

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
config(mfp_processor * proc) 
{
    builtin_biquad_data * pdata = (builtin_biquad_data *)proc->data;
    gpointer a1_ptr = g_hash_table_lookup(proc->params, "a1");
    gpointer a2_ptr = g_hash_table_lookup(proc->params, "a2");
    gpointer b0_ptr = g_hash_table_lookup(proc->params, "b0");
    gpointer b1_ptr = g_hash_table_lookup(proc->params, "b1");
    gpointer b2_ptr = g_hash_table_lookup(proc->params, "b2");

    if(b0_ptr != NULL) {
        pdata->b0 = *(float *)b0_ptr ;
    }

    if(b1_ptr != NULL) {
        pdata->b1 = *(float *)b1_ptr ;
    }

    if(b2_ptr != NULL) {
        pdata->b2 = *(float *)b2_ptr ;
    }

    if(a1_ptr != NULL) {
        pdata->a1 = *(float *)a1_ptr ;
    }

    if(a2_ptr != NULL) {
        pdata->a2 = *(float *)a2_ptr ;
    }


    return;
}

static void
reset(mfp_processor * proc) 
{
    builtin_biquad_data * pdata = (builtin_biquad_data *)proc->data;
    pdata->a1 = 0.0;
    pdata->a2 = 0.0;
    pdata->b0 = 1.0;
    pdata->b1 = 0.0;
    pdata->b2 = 0.0;
    pdata->delay_1 = 0.0;
    pdata->delay_2 = 0.0;

}

mfp_procinfo *  
init_builtin_biquad(void) {
    mfp_procinfo * p = g_malloc0(sizeof(mfp_procinfo));

    p->name = strdup("biquad~");
    p->is_generator = 0;
    p->process = process;
    p->init = init;
    p->destroy = destroy;
    p->config = config;
    p->reset = reset;

    p->params = g_hash_table_new_full(g_str_hash, g_str_equal, NULL, NULL);
    g_hash_table_insert(p->params, "b0", (gpointer)PARAMTYPE_FLT);
    g_hash_table_insert(p->params, "b1", (gpointer)PARAMTYPE_FLT);
    g_hash_table_insert(p->params, "b2", (gpointer)PARAMTYPE_FLT);
    g_hash_table_insert(p->params, "a1", (gpointer)PARAMTYPE_FLT);
    g_hash_table_insert(p->params, "a2", (gpointer)PARAMTYPE_FLT);

    return p;
}


