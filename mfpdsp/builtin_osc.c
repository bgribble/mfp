#include <math.h>
#include <stdio.h>
#include <string.h>
#include <glib.h>

#include "mfp_dsp.h"
#include "mfp_block.h"

typedef struct {
    mfp_block * int_0;
    double const_freq;
    double const_ampl;
    double phase;
} builtin_osc_data;

#define OSC_TABSIZE 2048
#define OSC_TABRANGE (2.0 * M_PI + 0.000001)
#define OSC_TABSCALE (OSC_TABSIZE / OSC_TABRANGE)
#define OSC_TABINCR (OSC_TABRANGE / OSC_TABSIZE) 

double osc_table[OSC_TABSIZE + 1]; 

static void 
table_load(void) {
    double phase = 0.0;
    double phase_incr = OSC_TABINCR;
    int sample;

    for(sample = 0; sample < OSC_TABSIZE + 1; sample++) {
        osc_table[sample] = sin(phase);
        phase += phase_incr;
    }
}


static mfp_sample 
table_lookup(double phase) {
        
    int index = (int)(phase * OSC_TABSCALE);
    double rem, s1, s2;

    rem = phase - index*OSC_TABINCR;
    if((index < 0) || (index > OSC_TABSIZE-1)) {
        printf("table_lookup: out-of-range phase %f (index %d) max is %d\n", phase, index,
                OSC_TABSIZE);
        return 0.0;
    }
    s1 = osc_table[index];
    s2 = osc_table[index+1];

    return (mfp_sample)(s1 + (s2-s1)*(rem*OSC_TABSCALE));

}

static int 
process(mfp_processor * proc) 
{
    builtin_osc_data * d = (builtin_osc_data *)(proc->data);
    int mode_am = 0, mode_fm = 0;
    double phase_base;
    float newphase = 0.0;
    int c;


    if (mfp_proc_has_input(proc, 0)) {
        mode_fm = 1;
    }

    if (mfp_proc_has_input(proc, 1)) {
        mode_am = 1;
    }

    phase_base = 2.0*M_PI / (double)proc->context->samplerate;

    if (proc->outlet_buf[0] == NULL) {
        mfp_proc_error(proc, "No output buffers allocated");
        return 0;
    }

    if(mode_fm == 1) {
        newphase = mfp_block_prefix_sum(proc->inlet_buf[0], phase_base, d->phase, d->int_0); 
        newphase = fmod(newphase, 2.0*M_PI);

        /* wrap the phase to function domain */
        mfp_block_fmod(d->int_0, 2.0*M_PI, d->int_0);

    }
    else {
        newphase = mfp_block_phase(d->int_0, d->phase, phase_base*d->const_freq, 2.0*M_PI);
    }


    /* now the real work */
    for (c=0; c < proc->outlet_buf[0]->blocksize; c++) {
        proc->outlet_buf[0]->data[c] = table_lookup(d->int_0->data[c]);
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
    builtin_osc_data * d = g_malloc0(sizeof(builtin_osc_data));

    d->const_ampl = 1.0;
    d->const_freq = 0.0;
    d->phase = 0;
    d->int_0 = mfp_block_new(mfp_max_blocksize);
    mfp_block_resize(d->int_0, proc->context->blocksize);

    proc->data = (void *)d;

}

static void
destroy(mfp_processor * proc) 
{
    builtin_osc_data * d = (builtin_osc_data *)(proc->data);

    if (proc->data != NULL) {
        g_free(proc->data);
        proc->data = NULL;
    }
}

static int 
config(mfp_processor * proc) 
{
    builtin_osc_data * d = (builtin_osc_data *)(proc->data);
    gpointer freq_ptr = g_hash_table_lookup(proc->params, "_sig_1");
    gpointer ampl_ptr = g_hash_table_lookup(proc->params, "_sig_2");
    gpointer phase_ptr = g_hash_table_lookup(proc->params, "phase");

    /* if blocksize has changed, resize internal buffer */ 
    if (d->int_0->blocksize != proc->context->blocksize) {
        mfp_block_resize(d->int_0, proc->context->blocksize);
    }

    /* get parameters */ 
    if (freq_ptr != NULL) {
        d->const_freq = *(float *)freq_ptr;
    }

    if (ampl_ptr != NULL) {
        d->const_ampl = *(float *)ampl_ptr;
    }

    if (phase_ptr != NULL) {
        d->phase = *(float *)phase_ptr;-
        g_hash_table_remove(proc->params, "phase");
        g_free(phase_ptr);
    }

    return 1;
}



mfp_procinfo *  
init_builtin_osc(void) {
    mfp_procinfo * p = g_malloc0(sizeof(mfp_procinfo));
    p->name = strdup("osc~");
    p->is_generator = GENERATOR_CONDITIONAL;
    p->process = process;
    p->init = init;
    p->destroy = destroy;
    p->config = config;
    p->params = g_hash_table_new_full(g_str_hash, g_str_equal, NULL, NULL);
    g_hash_table_insert(p->params, "_sig_1", (gpointer)PARAMTYPE_FLT);
    g_hash_table_insert(p->params, "_sig_2", (gpointer)PARAMTYPE_FLT);
    g_hash_table_insert(p->params, "phase", (gpointer)PARAMTYPE_FLT);

    table_load();

    return p;
}


