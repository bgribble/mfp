#include <stdlib.h>
#include <stdio.h>
#include <dlfcn.h>

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
    mfp_context * context = NULL;
    mfp_lv2_info * self = NULL;

    /* make sure that the MFP process is running */ 
    if (!mfp_initialized) {
        mfp_init_all(NULL);
    }
    context = mfp_context_new(CTYPE_LV2);
    context->samplerate = rate;
    self = context->info.lv2;

    printf("mfp_lv2_instantiate: context %d, %s\n", context->id, bundle_path);
    self->port_symbol = g_array_new(FALSE, TRUE, sizeof(char *));
    self->port_name = g_array_new(FALSE, TRUE, sizeof(char *));
    self->port_data = g_array_new(FALSE, TRUE, sizeof(void *));
    self->port_control_values = g_array_new(FALSE, TRUE, sizeof(float));

    self->input_ports = g_array_new(FALSE, TRUE, sizeof(int));
    self->output_ports = g_array_new(FALSE, TRUE, sizeof(int));

    /* mfp_lv2_ttl_read populates self with info about this plugin */ 
    mfp_lv2_ttl_read(self, bundle_path);

    /* request that the MFP app build this patch */
    mfp_api_load_context(context, self->object_path);

    return (LV2_Handle)context;
}


static void
mfp_lv2_connect_port(LV2_Handle instance, uint32_t port, void * data) 
{
    mfp_context * context = (mfp_context *)instance; 
    mfp_lv2_info * self = context->info.lv2;

    g_array_index(self->port_data, void *, port) = data;
}

static void
mfp_lv2_activate(LV2_Handle instance)
{
    mfp_context * context = (mfp_context *)instance; 
    mfp_lv2_info * self = context->info.lv2;
    context->activated = 1;
}

static void
mfp_lv2_send_control_input(mfp_context * context, int port, float val)
{
    mfp_lv2_info * self = context->info.lv2;
    int port_count = 0;

    for(int i=0; i < port; i++) {
        if(self->port_input_mask & (1 << i)) {
            port_count ++;
        }
    }
    mfp_api_send_to_inlet(context, port_count, val);
}

static void
mfp_lv2_send_control_output(mfp_context * context, int port, float val)
{
    mfp_lv2_info * self = context->info.lv2;
    int port_count = 0;

    for(int i=0; i < port; i++) {
        if(self->port_output_mask & (1 << i)) {
            port_count ++;
        }
    }
    mfp_api_send_to_outlet(context, port_count, val);
}


static void
mfp_lv2_run(LV2_Handle instance, uint32_t nframes) 
{
    mfp_context * context = (mfp_context *)instance; 
    if (context == NULL) {
        printf("mfp_lv2_run: context is NULL\n");
        return;
    }
    else if (!context->activated) {
        printf("mfp_lv2_run: deactivated, skipping\n");
        return;
    }

    mfp_lv2_info * self = context->info.lv2;
    int first_run=1;

    mfp_dsp_set_blocksize(context, nframes);

    if (self->port_control_values->len > 0) {
        first_run = 0;
    }
    else {
        g_array_set_size(self->port_control_values, self->port_data->len);
    }

    /* send an event to control [inlet]/[outlet] on startup and any change 
     * in value 
     *
     * FIXME: Ignore the last input, which is the Edit button. */ 
    for(int i=0; i < (self->port_data->len - 1); i++) {
        if((self->port_input_mask & (1 << i)) &&  
           (self->port_control_mask & (1 << i))) { 
            int val_changed = 1;
            void * pdata = mfp_lv2_get_port_data(self, i);
            if (pdata != NULL) {
                float val = *(float *)pdata;
                if (!first_run && 
                    (g_array_index(self->port_control_values, float, i) == val )) {
                    val_changed = 0;
                }

                if (val_changed) { 
                    g_array_index(self->port_control_values, float, i) = val;
                    mfp_lv2_send_control_input(context, i, val);
                }
            }
        }
    }

    mfp_dsp_run(context);

    for(int i=0; i < self->port_data->len; i++) {
        if((self->port_output_mask & (1 << i)) &&  
           (self->port_control_mask & (1 << i))) { 
            int val_changed = 1;
            void * pdata = mfp_lv2_get_port_data(self, i);
            if (pdata != NULL) {
                float val = *(float *)pdata;
                if (!first_run && 
                    (g_array_index(self->port_control_values, float, i) == val )) {
                    val_changed = 0;
                }

                if (val_changed) { 
                    g_array_index(self->port_control_values, float, i) = val;
                    mfp_lv2_send_control_output(context, i, val);
                }
            }
        }
    }
}

static void
mfp_lv2_deactivate(LV2_Handle instance)
{ 
    mfp_context * context = (mfp_context *)instance; 
    mfp_lv2_info * self = context->info.lv2;
    context->activated = 0;
    printf("mfp_lv2_deactivate\n");
}

static void
mfp_lv2_cleanup(LV2_Handle instance)
{
    mfp_context * context = (mfp_context *)instance; 
    mfp_lv2_info * self = context->info.lv2;

    mfp_context_destroy(context);
}

static const void *
mfp_lv2_extension_data(const char * uri)
{
    return NULL;
}

static LV2_Descriptor descriptor = {
    NULL,
    mfp_lv2_instantiate,
    mfp_lv2_connect_port,
    mfp_lv2_activate,
    mfp_lv2_run,
    mfp_lv2_deactivate,
    mfp_lv2_cleanup,
    mfp_lv2_extension_data
};


static char * 
find_lib_plugname(const char * fullpath)
{
    char * pdup = g_strdup(fullpath);
    char * pname;
    int plen = strlen(pdup);
    
    if (plen < 7) { 
        return NULL;
    }
    
    pdup[plen-3] = 0;
    if (pdup[plen-7] == '_') {
        pdup[plen-7] = '.';
    }
    pname = rindex(pdup, (int)'/') + 4;
    printf("find_lib_plugname: got '%s'\n", pname);
    return pname;
}


LV2_SYMBOL_EXPORT
const LV2_Descriptor*
lv2_descriptor(uint32_t index)
{
    Dl_info info;
    char * uri = g_malloc0(2048);

    dladdr(lv2_descriptor, &info);

    printf("lv2_descriptor: fname = '%s'\n", info.dli_fname);
    snprintf(uri, 2047, "http://www.billgribble.com/mfp/%s", 
             find_lib_plugname(info.dli_fname));
    printf("lv2_descriptor: URI = '%s'\n", uri);

    descriptor.URI = uri;

    switch (index) {
        case 0:
            return &descriptor;
        default:
            return NULL;
    }
}


