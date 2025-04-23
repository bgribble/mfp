
#include <sys/types.h>
#include <unistd.h>
#include <glib.h>
#include <stdio.h>

#include "mfp_dsp.h"

int next_context_id = 0;

mfp_context *
mfp_context_new(int ctxt_type)
{
    mfp_context * ctxt = g_malloc0(sizeof(mfp_context));

    ctxt->id = next_context_id;
    next_context_id ++;
    ctxt->ctype = ctxt_type;
    ctxt->activated = 0;
    ctxt->owner = getpid();
    ctxt->msg_handler = NULL;

    if (ctxt_type == CTYPE_JACK) {
        ctxt->info.jack = g_malloc0(sizeof(mfp_jack_info));
    }
    else if (ctxt_type == CTYPE_LV2) {
        ctxt->info.lv2 = g_malloc0(sizeof(mfp_lv2_info));
    }

    g_hash_table_insert(mfp_contexts, GINT_TO_POINTER(ctxt->id), (gpointer)ctxt);
    return ctxt;
}

void
mfp_context_destroy(mfp_context * ctxt)
{
    mfp_api_close_context(ctxt);

    g_hash_table_remove(mfp_contexts, GINT_TO_POINTER(ctxt->id));

    g_free((gpointer)ctxt->info.lv2);
    ctxt->info.lv2 = NULL;
    g_free(ctxt);

    if(g_hash_table_size(mfp_contexts) == 0) {
        mfp_api_exit_notify();
        mfp_finish_all();
    }
}

int
mfp_context_init(mfp_context * context)
{
    char * msgbuf = mfp_comm_get_buffer();
    int msglen = 0;
    int request_id = mfp_api_open_context(context, msgbuf, &msglen);
    mfp_comm_submit_buffer(msgbuf, msglen);
    mfp_rpc_wait(request_id);

    msgbuf = mfp_comm_get_buffer();
    msglen = snprintf(
        msgbuf,
        MFP_MAX_MSGSIZE-1,
        "json:{ \"host_id\": \"%s\", \"__type__\": \"HostExports\", \"exports\": [\"DSPObject\"], \"metadata\": [ %f, %f ] }",
        rpc_node_id, mfp_in_latency, mfp_out_latency
    );

    mfp_comm_submit_buffer(msgbuf, msglen);
    return 0;
}

int
mfp_context_default_io(mfp_context * context, int patch_id)
{
    mfp_procinfo * inlet_t;
    mfp_procinfo * outlet_t;
    mfp_processor ** p;
    void * newval;

    context->default_obj_id = patch_id;
    inlet_t = (mfp_procinfo *)g_hash_table_lookup(mfp_proc_registry, "inlet~");
    outlet_t = (mfp_procinfo *)g_hash_table_lookup(mfp_proc_registry, "outlet~");

    for(p = (mfp_processor **)(mfp_proc_list->data); *p != NULL; p++) {
        if (((*p)->patch_id == patch_id) && ((*p)->typeinfo == inlet_t)) {
            newval = g_malloc0(sizeof(double));
            *(double *)newval = 1.0;
            mfp_proc_setparam((*p), g_strdup("use_context_input"), newval);
            (*p)->needs_config = 1;
        }
        if (((*p)->patch_id == patch_id) && ((*p)->typeinfo == outlet_t)) {
            newval = g_malloc0(sizeof(double));
            *(double *)newval = 1.0;
            mfp_proc_setparam((*p), g_strdup("use_context_output"), newval);
            (*p)->needs_config = 1;
        }
    }
}

