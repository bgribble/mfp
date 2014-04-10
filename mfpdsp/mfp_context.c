
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
    printf("mfp_context_destroy -- enter\n");
    mfp_api_close_context(ctxt);

    g_hash_table_remove(mfp_contexts, GINT_TO_POINTER(ctxt->id));

    g_free((gpointer)ctxt->info.lv2);
    ctxt->info.lv2 = NULL;
    g_free(ctxt);

    if(g_hash_table_size(mfp_contexts) == 0) {
        printf("Last context destroyed, need to shut down library\n");
        mfp_api_node_exit();
        mfp_finish_all();
    }

    printf("mfp_context_destroy -- finished\n");
}

int
mfp_context_connect_default_io(mfp_context * context, int patch_id)
{
    mfp_procinfo * inlet_t; 
    mfp_procinfo * outlet_t; 
    mfp_processor ** p;
    void * newval;

    inlet_t = (mfp_procinfo *)g_hash_table_lookup(mfp_proc_registry, "inlet~");
    outlet_t = (mfp_procinfo *)g_hash_table_lookup(mfp_proc_registry, "outlet~");
    context->default_obj_id = patch_id;

    printf("connect_default_io: finding inlet~ and outlet~\n");

    for(p = (mfp_processor **)(mfp_proc_list->data); *p != NULL; p++) {
        if (((*p)->patch_id == patch_id) && ((*p)->typeinfo == inlet_t)) {
            newval = g_malloc0(sizeof(float));
            *(float *)newval = 1.0;
            mfp_proc_setparam((*p), "use_context_input", newval);
            /* FIXME -- you were working here */
            printf("  found inlet~ %p (id %d)\n", (*p), (*p)->rpc_id);
        }
        if (((*p)->patch_id == patch_id) && ((*p)->typeinfo == outlet_t)) {
            newval = g_malloc0(sizeof(float));
            *(float *)newval = 1.0;
            mfp_proc_setparam((*p), "use_context_output", newval);
            /* FIXME -- you were working here */
            printf("  found outlet~ %p (id %d)\n", (*p), (*p)->rpc_id);
        }
    }
}

