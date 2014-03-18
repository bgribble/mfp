#include <stdio.h>
#include <string.h>
#include <glib.h>

#include "mfp_dsp.h"

static int 
process(mfp_processor * proc) 
{
    if (proc == NULL) { 
        printf("builtin_noop.c: proc is NULL!\n");
        return -1;
    }
    else if (proc->outlet_buf == NULL) {
        printf("builtin_noop.c: proc ID %d (%p) proc->outlet_buf is NULL\n",
                proc->rpc_id, proc);
        return -1;
    }
    else if (proc->outlet_buf[0] == NULL) {
        printf("builtin_noop.c: proc ID %d (%p) proc->outlet_buf[0] is NULL\n",
                proc->rpc_id, proc);
        return -1;
    }

    memcpy(proc->outlet_buf[0]->data, proc->inlet_buf[0]->data, 
           proc->outlet_buf[0]->blocksize * sizeof(mfp_sample));
        
    return 0;
}

static void 
init(mfp_processor * proc) 
{
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
    return 1;
}

mfp_procinfo *  
init_builtin_noop(void) {
    mfp_procinfo * p = g_malloc0(sizeof(mfp_procinfo));
    p->name = strdup("noop~");
    p->is_generator = 1;
    p->process = process;
    p->init = init;
    p->destroy = destroy;
    p->config = config;
    p->params = g_hash_table_new_full(g_str_hash, g_str_equal, NULL, NULL);
    return p;
}


