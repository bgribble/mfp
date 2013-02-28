#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include <math.h>
#include "mfp_dsp.h"
#include "mfp_block.h"

static int 
in_process(mfp_processor * proc) 
{
    gpointer chan_ptr = g_hash_table_lookup(proc->params, "channel");
    int channel = 0;
    mfp_sample * inbuf;
    mfp_block * outbuf;

    if (chan_ptr != NULL) {
        channel = (int)(*(float *)chan_ptr);
    }

    inbuf = mfp_get_input_buffer(channel);
    outbuf = proc->outlet_buf[0]->data;

    if ((inbuf == NULL) || (outbuf == NULL)) {
        return 0;
    }
    else {
        memcpy(outbuf, inbuf, mfp_blocksize * sizeof(mfp_sample));
    }

    return 1;
}

static int
out_process(mfp_processor * proc) 
{
    gpointer chan_ptr = g_hash_table_lookup(proc->params, "channel");
    int channel = 0;
    mfp_sample * inbuf;
    mfp_sample * outbuf;
    int count;

    if (chan_ptr != NULL) {
        channel = (int)(*(float *)chan_ptr);
    }
    outbuf = mfp_get_output_buffer(channel);
    inbuf = proc->inlet_buf[0]->data;

    if ((outbuf == NULL) || (inbuf == NULL)) {
        return 0;
    }

    mfp_dsp_accum(outbuf, inbuf, mfp_blocksize);

    return 1;
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
init_builtin_in(void) {
    mfp_procinfo * p = g_malloc0(sizeof(mfp_procinfo));
    p->name = strdup("in~");
    p->is_generator = 1;
    p->process = in_process;
    p->init = init;
    p->destroy = destroy;
    p->config = config;
    p->params = g_hash_table_new_full(g_str_hash, g_str_equal, NULL, NULL);
    g_hash_table_insert(p->params, "channel", (gpointer)PARAMTYPE_INT);

    return p;
}

mfp_procinfo *  
init_builtin_out(void) {
    mfp_procinfo * p = g_malloc0(sizeof(mfp_procinfo));
    p->name = strdup("out~");
    p->is_generator = 0;
    p->process = out_process;
    p->init = init;
    p->destroy = destroy;
    p->config = config;
    p->params = g_hash_table_new_full(g_str_hash, g_str_equal, NULL, NULL);
    g_hash_table_insert(p->params, "channel", (gpointer)PARAMTYPE_INT);
    return p;
}


