#include <math.h>
#include <stdio.h>
#include <string.h>
#include <glib.h>

#include "mfp_dsp.h"
#include "mfp_block.h"

typedef struct {
    mfp_block * int_phase;
    mfp_block * int_phase_thresh;
    double const_freq;
    double const_ampl;
    double const_pw_frac;
    double loval;
    double hival;
    double pw_ms;
    double phase;
} builtin_pulse_data;

/* 
 * square/pulse signal generator
 * signal inputs:
 *    Frequency
 *    Amplitude (gain after lowval/hival signal)
 *    Pulse width (fraction)
 * constant params:
 *    lowval: Low value ("off")
 *    hival: High value ("on")
 *    pw_ms: Fixed pulse with (milliseconds)
 *    phase: Resettable phase
 */

static int 
process_pulse(mfp_processor * proc) 
{
    builtin_pulse_data * d = (builtin_pulse_data *)(proc->data);
    int mode_fm = 0;
    int mode_am = 0;
    int mode_pwm = 0;
    double phase_base;
    float newphase = 0.0;
    int c;

    if (mfp_proc_has_input(proc, 0)) {
        mode_fm = 1;
    }

    if (mfp_proc_has_input(proc, 1)) {
        mode_am = 1;
    }

    if (mfp_proc_has_input(proc, 2)) {
        mode_pwm = 1;
    }

    phase_base = 2.0*M_PI / (double)proc->context->samplerate;

    if (proc->outlet_buf[0] == NULL) {
        mfp_proc_error(proc, "No output buffers allocated");
        return 0;
    }

    if(mode_fm == 1) {
        newphase = mfp_block_prefix_sum(proc->inlet_buf[0], phase_base, d->phase, d->int_phase); 
        newphase = fmod(newphase, 2.0*M_PI);

        /* wrap the phase to function domain */
        mfp_block_fmod(d->int_phase, 2.0*M_PI, d->int_phase);

    }
    else {
        newphase = mfp_block_phase(d->int_phase, d->phase, phase_base*d->const_freq, 2.0*M_PI);
    }

    if (mode_pwm == 1) {
        mfp_block_const_mul(proc->inlet_buf[2], 2.0*M_PI, d->int_phase_thresh);
    }
    else {
        mfp_block_fill(d->int_phase_thresh, d->const_pw_frac * 2.0 * M_PI);
    }

    /* now the real work */
    mfp_block_cmp(d->int_phase, d->int_phase_thresh,
            d->hival, d->loval, proc->outlet_buf[0]);

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
    builtin_pulse_data * d = g_malloc0(sizeof(builtin_pulse_data));

    d->const_freq = 0.0;
    d->const_ampl = 1.0;
    d->const_pw_frac = 0.5;
    d->phase = 0;
    d->pw_ms = -1.0;
    d->loval = -1.0;
    d->hival = 1.0;
    d->int_phase = mfp_block_new(mfp_max_blocksize);
    d->int_phase_thresh = mfp_block_new(mfp_max_blocksize);

    mfp_block_resize(d->int_phase, proc->context->blocksize);
    mfp_block_resize(d->int_phase_thresh, proc->context->blocksize);

    proc->data = (void *)d;

}

static void
destroy(mfp_processor * proc) 
{
    builtin_pulse_data * d = (builtin_pulse_data *)(proc->data);

    if (proc->data != NULL) {
        g_free(proc->data);
        proc->data = NULL;
    }
}

static int 
config(mfp_processor * proc) 
{
    builtin_pulse_data * d = (builtin_pulse_data *)(proc->data);
    gpointer freq_ptr = g_hash_table_lookup(proc->params, "_sig_1");
    gpointer ampl_ptr = g_hash_table_lookup(proc->params, "_sig_2");
    gpointer pw_frac_ptr = g_hash_table_lookup(proc->params, "_sig_3");
    gpointer phase_ptr = g_hash_table_lookup(proc->params, "phase");
    gpointer loval_ptr = g_hash_table_lookup(proc->params, "loval");
    gpointer hival_ptr = g_hash_table_lookup(proc->params, "hival");
    gpointer pw_ms_ptr = g_hash_table_lookup(proc->params, "pw_ms");

    /* if blocksize has changed, resize internal buffer */ 
    if (d->int_phase->blocksize != proc->context->blocksize) {
        mfp_block_resize(d->int_phase, proc->context->blocksize);
    }

    /* get parameters */ 
    if (freq_ptr != NULL) {
        d->const_freq = *(float *)freq_ptr;
    }

    if (pw_frac_ptr != NULL) {
        d->const_pw_frac = *(float *)pw_frac_ptr;
    }

    if (loval_ptr != NULL) {
        d->loval = *(float *)loval_ptr;
    }
    
    if (hival_ptr != NULL) {
        d->hival = *(float *)hival_ptr;
    }

    if (pw_ms_ptr != NULL) {
        d->pw_ms = *(float *)pw_ms_ptr;
    }

    if (phase_ptr != NULL) {
        d->phase = *(float *)phase_ptr;
        g_hash_table_remove(proc->params, "phase");
        /* FIXME free in config() */ 
        g_free(phase_ptr);
    }

    return 1;
}



mfp_procinfo *  
init_builtin_pulse(void) {
    mfp_procinfo * p = g_malloc0(sizeof(mfp_procinfo));
    p->name = strdup("pulse~");
    p->is_generator = GENERATOR_CONDITIONAL;
    p->process = process_pulse;
    p->init = init;
    p->destroy = destroy;
    p->config = config;
    p->params = g_hash_table_new_full(g_str_hash, g_str_equal, NULL, NULL);
    g_hash_table_insert(p->params, "_sig_1", (gpointer)PARAMTYPE_FLT);
    g_hash_table_insert(p->params, "_sig_2", (gpointer)PARAMTYPE_FLT);
    g_hash_table_insert(p->params, "_sig_3", (gpointer)PARAMTYPE_FLT);
    g_hash_table_insert(p->params, "loval", (gpointer)PARAMTYPE_FLT);
    g_hash_table_insert(p->params, "hival", (gpointer)PARAMTYPE_FLT);
    g_hash_table_insert(p->params, "pw_ms", (gpointer)PARAMTYPE_FLT);
    g_hash_table_insert(p->params, "phase", (gpointer)PARAMTYPE_FLT);

    return p;
}


