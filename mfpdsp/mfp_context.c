
#include <glib.h>
#include "mfp_dsp.h"

int next_context_id = 0;

mfp_context * 
mfp_context_new(int ctxt_type)
{
    mfp_context * ctxt = g_malloc(sizeof(mfp_context));

    ctxt->id = next_context_id;
    next_context_id ++;
    ctxt->ctype = ctxt_type; 
    if (ctxt_type == CTYPE_JACK) {
        ctxt->info.jack = g_malloc(sizeof(mfp_jack_info));
    }
    else if (ctxt_type == CTYPE_LV2) {
        ctxt->info.lv2 = g_malloc(sizeof(mfp_lv2_info));
    }

    g_hash_table_insert(mfp_contexts, GINT_TO_POINTER(ctxt->id), (gpointer)ctxt);
    return ctxt;
}

