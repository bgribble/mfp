
#include <stdio.h>
#include <string.h>
#include <glib.h>

#include "mfp_dsp.h"
#include "mfp_block.h"

typedef struct {
    double const_freq;
    double const_ampl;
    double phase;
} builtin_phasor_data;

static int 
process(mfp_processor * proc) 
{
    builtin_phasor_data * d = (builtin_phasor_data *)(proc->data);
    int mode_am = 0, mode_fm = 0;
    double phase_base;
    float newphase = 0.0;

    if (mfp_proc_has_input(proc, 0)) {
        mode_fm = 1;
    }

    if (mfp_proc_has_input(proc, 1)) {
        mode_am = 1;
    }

    phase_base = 1.0 / (double)mfp_samplerate;

    if (proc->outlet_buf[0] == NULL) {
        mfp_proc_error(proc, "No output buffers allocated");
        return 0;
    }

    if(mode_fm == 1) {
        newphase = mfp_block_prefix_sum(proc->inlet_buf[0], phase_base, d->phase, 
                                        proc->outlet_buf[0]); 

        /* wrap the phase to function domain */
        mfp_block_fmod(proc->outlet_buf[0], 1.0, proc->outlet_buf[0]);

    }
    else {
        newphase = mfp_block_phase(proc->outlet_buf[0], d->phase, 
                                   phase_base*d->const_freq, 1.0);
    }

    /* apply gain or amplitude modulation */
    if(mode_am == 1) {
        mfp_block_mul(proc->inlet_buf[1], proc->outlet_buf[0], proc->outlet_buf[0]);
    }
    else {
        mfp_block_const_mul(proc->outlet_buf[0], d->const_ampl, proc->outlet_buf[0]);
    }

    d->phase = newphase;
    return 0;
}

static void 
init(mfp_processor * proc) 
{
    builtin_phasor_data * d = g_malloc(sizeof(builtin_phasor_data));

    d->const_ampl = 1.0;
    d->const_freq = 0.0;
    d->phase = 0;

    proc->data = (void *)d;

    return;
}

static void
destroy(mfp_processor * proc) 
{
    if (proc->data != NULL) {
        g_free(proc->data);
        proc->data = NULL;
    }
    return;
}

static void
config(mfp_processor * proc) 
{
    builtin_phasor_data * d = (builtin_phasor_data *)(proc->data);
    gpointer freq_ptr = g_hash_table_lookup(proc->params, "_sig_1");
    gpointer ampl_ptr = g_hash_table_lookup(proc->params, "_sig_2");
    gpointer phase_ptr = g_hash_table_lookup(proc->params, "phase");

    /* get parameters */ 
    if (freq_ptr != NULL) {
        d->const_freq = *(float *)freq_ptr;
        g_hash_table_remove(proc->params, "_sig_1");
        g_free(freq_ptr);
    }

    if (ampl_ptr != NULL) {
        d->const_ampl = *(float *)ampl_ptr;
        g_hash_table_remove(proc->params, "_sig_2");
        g_free(ampl_ptr);
    }

    if (phase_ptr != NULL) {
        d->phase = (double)(*(float *)phase_ptr);
        g_hash_table_remove(proc->params, "phase");
        g_free(phase_ptr);
    }

    return;
}

mfp_procinfo *  
init_builtin_phasor(void) {
    mfp_procinfo * p = g_malloc0(sizeof(mfp_procinfo));

    p->name = strdup("phasor~");
    p->is_generator = 1;

    p->process = process;
    p->init = init;
    p->destroy = destroy;
    p->config = config;
    p->params = g_hash_table_new_full(g_str_hash, g_str_equal, NULL, NULL);
    
    g_hash_table_insert(p->params, "_sig_1", (gpointer)PARAMTYPE_FLT);
    g_hash_table_insert(p->params, "_sig_2", (gpointer)PARAMTYPE_FLT);
    g_hash_table_insert(p->params, "phase", (gpointer)PARAMTYPE_FLT);
    
    return p;
}


