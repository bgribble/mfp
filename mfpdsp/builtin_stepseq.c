#include <stdio.h>
#include <string.h>
#include <glib.h>

#include "mfp_dsp.h"
#include "mfp_block.h"

typedef struct {
    mfp_sample value;
    int slur_frames;
    int trigger;
} step;

typedef struct {
    step * steps;
    int num_steps;
    float clock_threshold;
    int trigger_len;

    int cur_step;
    int cur_step_frame;
    int clock_active;
    int trigger_active;

    float cv_slur_start_val;
    float cv_current_val;
} builtin_stepseq_data;

#define MAX_STEPS 1024

/*
 * step sequencer
 * signal inputs:
 *    Pulse train
 *    Reset
 * constant params:
 *    steps: ordered array of value/trigger/slur
 *    threshold: thresh for input clock
 *    trigger_len: frames for output trigger
 */

static int
config(mfp_processor * proc)
{
    builtin_stepseq_data * pdata = (builtin_stepseq_data *)proc->data;
    GArray * steps_raw = (GArray *)g_hash_table_lookup(proc->params, "steps");
    gpointer position_ptr = g_hash_table_lookup(proc->params, "position");
    gpointer threshold_ptr = g_hash_table_lookup(proc->params, "threshold");
    gpointer trig_ms_ptr = g_hash_table_lookup(proc->params, "trig_ms");

    float step_slur, step_value, frames_per_ms;
    int step_slur_frames;
    int step_trigger;
    step * steps = NULL;
    int num_steps = 0;
    int rawpos = 0;
    int scount;

    frames_per_ms = proc->context->samplerate / 1000.0;

    /* populate new step data if passed */
    if (steps_raw != NULL) {
        if(steps_raw->len == 0) {
            num_steps = 0;
        }
        else {
            num_steps = (steps_raw->len)/3;
        }
        num_steps = (num_steps > MAX_STEPS ? MAX_STEPS : num_steps);

        rawpos = 0;
        steps = pdata->steps;
        for (scount=0; scount < num_steps; scount++) {
            step_value = g_array_index(steps_raw, float, rawpos++);
            step_trigger = (int)(g_array_index(steps_raw, float, rawpos++));
            step_slur = g_array_index(steps_raw, float, rawpos++);

            step_slur_frames = (int)(step_slur * frames_per_ms + 0.5);

            steps[scount].slur_frames = step_slur_frames;
            steps[scount].value = step_value;
            steps[scount].trigger = step_trigger;
        }
        if (num_steps < 2) {
            pdata->cur_step = 0;
        }
        else if (pdata->cur_step >= num_steps) {
            pdata->cur_step = pdata->cur_step % num_steps;
        }
        pdata->num_steps = num_steps;
    }

    /* position */
    if(position_ptr != NULL) {
        pdata->cur_step = (int)(*(float *)position_ptr);
        pdata->cur_step_frame = 0;
        pdata->clock_active = 1;
        g_hash_table_remove(proc->params, "position");
    }

    /* trigger length */
    if(trig_ms_ptr != NULL) {
        pdata->trigger_len = (int)(
            *(float *)trig_ms_ptr * frames_per_ms + 0.5
        );
    }

    /* incoming clock transition threshold */
    if(threshold_ptr != NULL) {
        pdata->clock_threshold = *(float *)threshold_ptr;
    }

    return 1;
}

static int
process_stepseq(mfp_processor * proc)
{
    builtin_stepseq_data * data = ((builtin_stepseq_data *)(proc->data));
    step * cstep = data->steps + data->cur_step;
    int step_frame = data->cur_step_frame;
    int clock_active = data->clock_active;
    int trigger_active = data->trigger_active;
    int trigger_len = data->trigger_len;
    int block_frame;
    mfp_sample clock_thresh = data->clock_threshold;
    mfp_sample cur_cv, cur_trig;
    double slur_slope=0.0;
    mfp_sample * in_clk = proc->inlet_buf[0]->data;
    mfp_sample * out_cv = proc->outlet_buf[0]->data;
    mfp_sample * out_trig = proc->outlet_buf[1]->data;

    if (!out_cv && !out_trig || !data->num_steps) {
        mfp_block_zero(proc->outlet_buf[0]);
        mfp_block_zero(proc->outlet_buf[1]);
        return 0;
    }

    cur_cv = data->cv_current_val;
    if (cstep->slur_frames > 0) {
        slur_slope = (cstep->value - data->cv_slur_start_val) / cstep->slur_frames;
    }

    /* iterate */
    for(block_frame=0; block_frame < proc->context->blocksize; block_frame++) {
        /* if clock transitions high, go to next step */
        if (!clock_active && *in_clk > clock_thresh) {
            clock_active = 1;
            data->cur_step = (data->cur_step + 1) % data->num_steps;
            data->cv_slur_start_val = cur_cv;
            step_frame = 0;
            cstep = data->steps + data->cur_step;
            if (cstep->slur_frames > 0) {
                slur_slope = (cstep->value - cur_cv) / cstep->slur_frames;
            }

            if (cstep->trigger) {
                trigger_active = 1;
            }
        }
        else if (clock_active && *in_clk < clock_thresh*0.8) {
            clock_active = 0;
        }

        /* update value to output on CV out */
        if (out_cv) {
            if (step_frame >= cstep->slur_frames || cstep->slur_frames == 0) {
                cur_cv = cstep->value;
            }
            else {
                cur_cv += slur_slope;
            }
            *out_cv++ = cur_cv;
        }

        /* output trigger if needed */
        if (out_trig) {
            if (step_frame > data->trigger_len) {
                trigger_active = 0;
            }
            if (trigger_active) {
                cur_trig = 1;
            }
            else {
                cur_trig = 0;
            }
            *out_trig++ = cur_trig;
        }

        /* update counters */
        step_frame++;
        in_clk++;
    }

    /* update data record */
    data->cur_step_frame = step_frame;
    data->cv_current_val = cur_cv;
    data->trigger_active = trigger_active;
    data->clock_active = clock_active;

    return 0;
}

static void
init(mfp_processor * proc)
{
    builtin_stepseq_data * p = g_malloc0(sizeof(builtin_stepseq_data));
    proc->data = p;

    p->steps = g_malloc0(MAX_STEPS * sizeof(step));
    p->num_steps = 0;
    p->cur_step = 0;
    p->cur_step_frame = 0;
    p->cv_current_val = 0;
    p->cv_slur_start_val = 0;
}

static void
destroy(mfp_processor * proc)
{
    builtin_stepseq_data * p;
    if (proc->data != NULL) {
        p = (builtin_stepseq_data *)(proc->data);
        if (p->steps != NULL) {
            g_free(p->steps);
            p->steps = NULL;
        }
        g_free(proc->data);
        proc->data = NULL;
    }
}


mfp_procinfo *
init_builtin_stepseq(void) {
    mfp_procinfo * p = g_malloc0(sizeof(mfp_procinfo));
    p->name = strdup("stepseq~");
    p->is_generator = GENERATOR_CONDITIONAL;
    p->process = process_stepseq;
    p->init = init;
    p->destroy = destroy;
    p->config = config;
    p->params = g_hash_table_new_full(g_str_hash, g_str_equal, NULL, NULL);
    g_hash_table_insert(p->params, "steps", (gpointer)PARAMTYPE_FLTARRAY);
    g_hash_table_insert(p->params, "position", (gpointer)PARAMTYPE_FLT);
    g_hash_table_insert(p->params, "threshold", (gpointer)PARAMTYPE_FLT);
    g_hash_table_insert(p->params, "trig_ms", (gpointer)PARAMTYPE_FLT);

    return p;
}
