#include <stdio.h>
#include <string.h>
#include <glib.h>

#include "mfp_dsp.h"

typedef struct {
    int io_channel;
    int use_context_input;
    int use_context_output;
} builtin_noop_data;

static int 
process(mfp_processor * proc) 
{
    builtin_noop_data * d = (builtin_noop_data *)(proc->data);
    mfp_sample * inptr, * outptr; 

    int blocksize = proc->context->blocksize;

    if (proc == NULL) { 
        printf("builtin_noop.c: proc is NULL!\n");
        return -1;
    }

    if(d->use_context_input) {
        inptr = mfp_get_input_buffer(proc->context, d->io_channel); 
    }
    else {
        if (proc->inlet_buf == NULL) {
            printf("builtin_noop.c: proc ID %d (%p) proc->inlet_buf is NULL\n",
                    proc->rpc_id, proc);
            return -1;
        }
        else if (proc->inlet_buf[0] == NULL) {
            printf("builtin_noop.c: proc ID %d (%p) proc->inlet_buf[0] is NULL\n",
                    proc->rpc_id, proc);
            return -1;
        }
        inptr = proc->inlet_buf[0]->data;
    }

    if(d->use_context_output) {
        outptr = mfp_get_output_buffer(proc->context, d->io_channel); 
    }
    else {
        if (proc->outlet_buf == NULL) {
            printf("builtin_noop.c: proc ID %d (%p) proc->outlet_buf is NULL\n",
                    proc->rpc_id, proc);
            return -1;
        }
        else if (proc->outlet_buf[0] == NULL) {
            printf("builtin_noop.c: proc ID %d (%p) proc->outlet_buf[0] is NULL\n",
                    proc->rpc_id, proc);
            return -1;
        }
        outptr = proc->outlet_buf[0]->data;
    }


    memcpy(outptr, inptr, blocksize*sizeof(mfp_sample));
        
    return 0;
}

static void 
init(mfp_processor * proc) 
{
    builtin_noop_data * d = g_malloc0(sizeof(builtin_noop_data));
    d->use_context_input = 0;
    d->use_context_output = 0;

    proc->data = (void *)d;
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
    builtin_noop_data * d = (builtin_noop_data *)(proc->data);
    gpointer ctxt_in = g_hash_table_lookup(proc->params, "use_context_input");
    gpointer ctxt_out = g_hash_table_lookup(proc->params, "use_context_output");
    gpointer chan = g_hash_table_lookup(proc->params, "io_channel");

    if (ctxt_in != NULL) {
        d->use_context_input = (int)(*(float *)ctxt_in);
    }

    if(ctxt_out != NULL) {
        d->use_context_output = (int)(*(float *)ctxt_out);
    }

    if(chan != NULL) {
        d->io_channel = (int)(*(float *)chan);
    }


    return 1;
}

static mfp_procinfo *  
init_builtin_noop_wrapper(void) {
    mfp_procinfo * p = g_malloc0(sizeof(mfp_procinfo));
    p->is_generator = 1;
    p->process = process;
    p->init = init;
    p->destroy = destroy;
    p->config = config;
    p->params = g_hash_table_new_full(g_str_hash, g_str_equal, NULL, NULL);
    g_hash_table_insert(p->params, "use_context_input", (gpointer)PARAMTYPE_FLT);
    g_hash_table_insert(p->params, "use_context_output", (gpointer)PARAMTYPE_FLT);
    g_hash_table_insert(p->params, "io_channel", (gpointer)PARAMTYPE_FLT);
    return p;
}

mfp_procinfo *  
init_builtin_outlet(void) {
    mfp_procinfo * p = init_builtin_noop_wrapper();
    p->name = strdup("outlet~");
    return p;
}

mfp_procinfo *  
init_builtin_inlet(void) {
    mfp_procinfo * p = init_builtin_noop_wrapper();
    p->name = strdup("inlet~");
    return p;
}

mfp_procinfo *  
init_builtin_noop(void) {
    mfp_procinfo * p = init_builtin_noop_wrapper();
    p->name = strdup("noop~");
    return p;
}


