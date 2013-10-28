#include <stdlib.h>

#include "lv2/lv2plug.in/ns/ext/atom/atom.h"
#include "lv2/lv2plug.in/ns/ext/atom/util.h"
#include "lv2/lv2plug.in/ns/ext/midi/midi.h"
#include "lv2/lv2plug.in/ns/ext/urid/urid.h"
#include "lv2/lv2plug.in/ns/lv2core/lv2.h"

#include "mfp_dsp.h" 

#define MFP_LV2_URL "http://www.billgribble.com/mfp/mfp_lv2"

typedef struct {

} mfp_lv2_info; 

static LV2_Handle
mfp_lv2_instantiate(const LV2_Descriptor * descriptor, double rate, 
                    const char * bundle_path, const LV2_Feature * const * features)
{
    mfp_lv2_info * self = g_malloc(sizeof(mfp_lv2_info));

        
    return (LV2_Handle)self;
}


static void
mfp_lv2_connect_port(LV2_Handle instance, uint32_t port, void * data) 
{
    mfp_lv2_info * self = (mfp_lv2_info *)instance;
}

static void
mfp_lv2_activate(LV2_Handle instance)
{
    mfp_lv2_info * self = (mfp_lv2_info *)instance;
}

static void
mfp_lv2_run(LV2_Handle instance, uint32_t sample_count) 
{
    mfp_lv2_info * self = (mfp_lv2_info *)instance;
}

static void
mfp_lv2_deactivate(LV2_Handle instance)
{ }

static void
mfp_lv2_cleanup(LV2_Handle instance)
{
    free(instance);
}

static const void*
mfp_lv2_extension_data(const char* uri)
{
    return NULL;
}

static const LV2_Descriptor descriptor = {
    MIDIGATE_URI,
    mfp_lv2_instantiate,
    mfp_lv2_connect_port,
    mfp_lv2_activate,
    mfp_lv2_run,
    mfp_lv2_deactivate,
    mfp_lv2_cleanup,
    mfp_lv2_extension_data
};

