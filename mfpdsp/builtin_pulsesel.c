#include <math.h>
#include <stdio.h>
#include <string.h>
#include <glib.h>

#include "mfp_dsp.h"
#include "mfp_block.h"


#define PW_MODE_FRAC 0
#define PW_MODE_MS 1

typedef struct {
    int period;
    int bitmask;
    double threshold;

    int phase;
    int in_pulse;
    int in_selected_pulse;

} builtin_pulsesel_data;

/*
 * pulse train divider/selector
 * signal inputs:
 *    Pulse train
 * constant params:
 *    period: number of pulses in cycle
 *    bitmask: which pulses to pass through
 *    phase: Resettable phase
 */

static int
process_pulsesel(mfp_processor * proc)
{
    builtin_pulsesel_data * d = (builtin_pulsesel_data *)(proc->data);

    if (!mfp_proc_has_input(proc, 0)) {
        return 0;
    }

    if (proc->outlet_buf[0] == NULL) {
        mfp_proc_error(proc, "No output buffers allocated");
        return 0;
    }

    mfp_sample * iptr, * optr, *iend;
    iptr = proc->inlet_buf[0]->data;
    iend = proc->inlet_buf[0]->data + proc->inlet_buf[0]->blocksize;
    optr = proc->outlet_buf[0]->data;

    int phase = d->phase;
    int in_selected_pulse = d->in_selected_pulse;
    double thresh = d->threshold;
    int in_pulse = d->in_pulse;

    for(; iptr < iend; iptr++) {
        if (in_pulse && *iptr < thresh) {
            in_pulse = in_selected_pulse = 0;
        }
        else if (!in_pulse && *iptr >= thresh) {
            in_pulse = 1;
            phase = (phase + 1) % d->period;
            if (d->bitmask & (1 << phase)) {
                in_selected_pulse = 1;
            }
            else {
                in_selected_pulse = 0;
            }
        }

        if (in_selected_pulse) {
            *optr = *iptr;
        }
        else {
            *optr = 0.0;
        }
        optr++;
    }
    d->phase = phase;
    d->in_pulse = in_pulse;
    d->in_selected_pulse = in_selected_pulse;
    return 0;
}


static void
init(mfp_processor * proc)
{
    builtin_pulsesel_data * d = g_malloc0(sizeof(builtin_pulsesel_data));

    d->bitmask = 1;
    d->period = 1;
    d->threshold = 0.25;
    d->phase = 0;
    d->in_pulse = 0;
    d->in_selected_pulse = 0;

    proc->data = (void *)d;

}

static void
destroy(mfp_processor * proc)
{
    builtin_pulsesel_data * d = (builtin_pulsesel_data *)(proc->data);

    if (proc->data != NULL) {
        g_free(proc->data);
        proc->data = NULL;
    }
}

static int
config(mfp_processor * proc)
{
    builtin_pulsesel_data * d = (builtin_pulsesel_data *)(proc->data);
    gpointer phase_ptr = g_hash_table_lookup(proc->params, "phase");
    gpointer period_ptr = g_hash_table_lookup(proc->params, "period");
    gpointer bitmask_ptr = g_hash_table_lookup(proc->params, "bitmask");
    gpointer threshold_ptr = g_hash_table_lookup(proc->params, "threshold");

    /* get parameters */
    if (period_ptr != NULL) {
        d->period = *(double *)period_ptr;
    }

    if (bitmask_ptr != NULL) {
        d->bitmask = (int)(*(double *)bitmask_ptr);
    }

    if (threshold_ptr != NULL) {
        d->threshold = *(double *)threshold_ptr;
    }

    if (phase_ptr != NULL) {
        d->phase = (int)*(double *)phase_ptr;
        g_hash_table_remove(proc->params, "phase");
        /* FIXME free in config() */
        g_free(phase_ptr);
    }

    return 1;
}



mfp_procinfo *
init_builtin_pulsesel(void) {
    mfp_procinfo * p = g_malloc0(sizeof(mfp_procinfo));
    p->name = strdup("pulsesel~");
    p->is_generator = GENERATOR_CONDITIONAL;
    p->process = process_pulsesel;
    p->init = init;
    p->destroy = destroy;
    p->config = config;
    p->params = g_hash_table_new_full(g_str_hash, g_str_equal, NULL, NULL);
    g_hash_table_insert(p->params, "phase", (gpointer)PARAMTYPE_INT);
    g_hash_table_insert(p->params, "period", (gpointer)PARAMTYPE_INT);
    g_hash_table_insert(p->params, "bitmask", (gpointer)PARAMTYPE_INT);
    g_hash_table_insert(p->params, "threshold", (gpointer)PARAMTYPE_FLT);

    return p;
}


