
#include <stdio.h>
#include <string.h>
#include <glib.h>

#include "mfp_dsp.h"

typedef struct {
    mfp_sample sample;
} builtin_sig_data;


static int 
process(mfp_processor * proc) 
{
    builtin_sig_data * d = (builtin_sig_data *)(proc->data);
    mfp_sample * sample; 
    int scount; 
    
    if ((proc == NULL) || (proc->outlet_buf == NULL) || (proc->outlet_buf[0] == NULL)) {
        printf("sig~: critical error ((NULL pointers)\n");
        return 0;
    }
    sample = proc->outlet_buf[0]->data;

    if (sample == NULL) {
        return 0;
    }

    /* iterate */ 
    for(scount=0; scount < mfp_blocksize; scount++) {
        *sample++ = d->sample;
    }

    return 0;
}

static void 
init(mfp_processor * proc) 
{
    proc->data = g_malloc0(sizeof(builtin_sig_data));
    return;
}

static void
destroy(mfp_processor * proc) 
{
    builtin_sig_data * d = (builtin_sig_data *)(proc->data);
    printf("sig~ destroy\n");
    proc->data = NULL;
    g_free(d);

    return;
}

static int
config(mfp_processor * proc) 
{
    builtin_sig_data * d = (builtin_sig_data *)(proc->data);
    gpointer val_ptr = g_hash_table_lookup(proc->params, "value");

    if(val_ptr != NULL) {
        d->sample = *(float *)val_ptr;
        printf("sig~ config: %f\n", d->sample);
    }

    return 1;
}

mfp_procinfo *  
init_builtin_sig(void) {
    mfp_procinfo * p = g_malloc0(sizeof(mfp_procinfo));
    p->name = strdup("sig~");
    p->is_generator = 1;
    p->process = process;
    p->init = init;
    p->destroy = destroy;
    p->config = config;
    p->params = g_hash_table_new_full(g_str_hash, g_str_equal, NULL, NULL);
    g_hash_table_insert(p->params, "value", (gpointer)PARAMTYPE_FLT);
    return p;
}


