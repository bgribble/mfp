#include <stdlib.h>
#include <stdio.h>

#include "lv2/lv2plug.in/ns/ext/atom/atom.h"
#include "lv2/lv2plug.in/ns/ext/atom/util.h"
#include "lv2/lv2plug.in/ns/ext/midi/midi.h"
#include "lv2/lv2plug.in/ns/ext/urid/urid.h"
#include "lv2/lv2plug.in/ns/lv2core/lv2.h"

#include "mfp_dsp.h" 

#define MFP_LV2_URL "http://www.billgribble.com/mfp/mfp_lv2"


void * 
mfp_lv2_get_port_data(mfp_lv2_info * self, int port)
{
    return g_array_index(self->port_data, void *, port);
}


/*
 * static functions for LV2 descriptor  
 */


static LV2_Handle
mfp_lv2_instantiate(const LV2_Descriptor * descriptor, double rate, 
                    const char * bundle_path, const LV2_Feature * const * features)
{
    mfp_context * context = mfp_context_new(CTYPE_LV2);
    mfp_lv2_info * self = context->info.lv2;

    printf("mfp_lv2_instantiate: %s\n", bundle_path);
    self->port_symbol = g_array_new(FALSE, TRUE, sizeof(char *));
    self->port_name = g_array_new(FALSE, TRUE, sizeof(char *));
    self->port_data = g_array_new(FALSE, TRUE, sizeof(void *));

    /* mfp_lv2_ttl_read populates self with info about this plugin */ 
    mfp_lv2_ttl_read(self, bundle_path);

    /* make sure that the MFP process is running */ 
    if (!mfp_initialized) {
        mfp_init_all(NULL);
    }

    /* request that the MFP app build this patch */
    mfp_context_load_patch(context, self->object_name);

    return (LV2_Handle)context;
}


static void
mfp_lv2_connect_port(LV2_Handle instance, uint32_t port, void * data) 
{
    mfp_context * context = (mfp_context *)instance; 
    mfp_lv2_info * self = context->info.lv2;

    printf("connect_port: port %d data %p\n", port, data);
    g_array_insert_val(self->port_data, port, data);
}

static void
mfp_lv2_activate(LV2_Handle instance)
{
    mfp_context * context = (mfp_context *)instance; 
    mfp_lv2_info * self = context->info.lv2;
    printf("mfp_lv2_activate\n");
}

static void
mfp_lv2_run(LV2_Handle instance, uint32_t nframes) 
{
    mfp_context * context = (mfp_context *)instance; 
    mfp_lv2_info * self = context->info.lv2;

    mfp_dsp_set_blocksize(context, nframes);
    printf("About to call mfp_dsp_run, context = %p\n", context);
    mfp_dsp_run(context);
}

static void
mfp_lv2_deactivate(LV2_Handle instance)
{ 
    mfp_context * context = (mfp_context *)instance; 
    mfp_lv2_info * self = context->info.lv2;
    printf("mfp_lv2_deactivate\n");
}

static void
mfp_lv2_cleanup(LV2_Handle instance)
{
    mfp_context * context = (mfp_context *)instance; 
    mfp_lv2_info * self = context->info.lv2;
    printf("mfp_lv2_cleanup\n");
}

static const void *
mfp_lv2_extension_data(const char * uri)
{
    return NULL;
}

static const LV2_Descriptor descriptor = {
    MFP_LV2_URL,
    mfp_lv2_instantiate,
    mfp_lv2_connect_port,
    mfp_lv2_activate,
    mfp_lv2_run,
    mfp_lv2_deactivate,
    mfp_lv2_cleanup,
    mfp_lv2_extension_data
};

LV2_SYMBOL_EXPORT
const LV2_Descriptor*
lv2_descriptor(uint32_t index)
{
    switch (index) {
        case 0:
            return &descriptor;
        default:
            return NULL;
    }
}


