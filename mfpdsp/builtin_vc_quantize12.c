#include <math.h>
#include <stdio.h>
#include <string.h>
#include <glib.h>

#include "mfp_dsp.h"

#define NUM_SEMITONES 12
#define VOCT_SEMITONE ((mfp_sample)(1.0 / 12.0))

typedef struct {
    mfp_sample map[NUM_SEMITONES];
} builtin_quantize12_data;

static int
config(mfp_processor * proc) 
{
    builtin_quantize12_data * pdata = (builtin_quantize12_data *)proc->data;
    GArray * map_raw = (GArray *)g_hash_table_lookup(proc->params, "map");
    int nummap = 0;
    int rawpos = 0;
    int framebase, semitone, scaletone;

    /* populate new segment data if passed */
    if (map_raw != NULL) {
        if(map_raw->len == 0) {
            nummap = 0;
        }
        else {
            nummap = (map_raw->len)/2; 
        }

        rawpos = 0;
        framebase = 0;
        for (int scount=0; scount < nummap; scount++) {
            semitone = g_array_index(map_raw, double, rawpos++);
            scaletone = g_array_index(map_raw, double, rawpos++);
            pdata->map[(int)semitone] = scaletone;
        }

        g_hash_table_remove(proc->params, "map");
    }

    return 1;
}

static int 
process_quantize12(mfp_processor * proc) 
{
    builtin_quantize12_data * data = ((builtin_quantize12_data *)(proc->data));
    mfp_sample * output = proc->outlet_buf[0]->data;
    mfp_sample * input = proc->inlet_buf[0]->data;
    double octave_base;
    double unquant;
    int semitone;
    mfp_sample scaletone;

    if ((input == NULL) || (data == NULL)) {
        mfp_block_zero(proc->outlet_buf[0]);
        return 0;
    }
    /* iterate */ 
    for(int scount=0; scount < proc->context->blocksize; scount++) {
        unquant = *input++;
        octave_base = floor((double)unquant);
        semitone = (int)((unquant-octave_base) / VOCT_SEMITONE);
        scaletone = data->map[semitone % NUM_SEMITONES];
        *output++ = (mfp_sample)(octave_base + scaletone * VOCT_SEMITONE); 
    }
    
    return 0;
}

static void 
init(mfp_processor * proc) 
{
    builtin_quantize12_data * p = g_malloc0(sizeof(builtin_quantize12_data));

    proc->data = p; 
    
    for(int sem=0; sem < NUM_SEMITONES; sem++){ 
        p->map[sem] = (mfp_sample)sem;
    }
}

static void
destroy(mfp_processor * proc) 
{
    builtin_quantize12_data * p;
    if (proc->data != NULL) {
        g_free(proc->data);
        proc->data = NULL;
    }
}


mfp_procinfo *  
init_builtin_vc_quantize12(void) {
    mfp_procinfo * p = g_malloc0(sizeof(mfp_procinfo));
    p->name = strdup("vcq12~");
    p->is_generator = GENERATOR_NEVER;
    p->process = process_quantize12;
    p->init = init;
    p->destroy = destroy;
    p->config = config;
    p->params = g_hash_table_new_full(g_str_hash, g_str_equal, NULL, NULL);
    g_hash_table_insert(p->params, "map", (gpointer)PARAMTYPE_FLTARRAY);

    return p;
}



