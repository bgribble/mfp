
#include <stdio.h>
#include <string.h>
#include <sys/time.h>
#include <stdlib.h>
#include <glib.h>
#include <math.h>

#include "mfp_dsp.h"

typedef struct {
	/* configurable params */
	float peak_decay_ms;
	float rms_window_ms;

	/* runtime state */ 
	double last_peak;
	double rms_accum;
} builtin_ampl_data;

static int 
process(mfp_processor * proc) 
{
	builtin_ampl_data * pdata = (builtin_ampl_data *)proc->data;
	mfp_sample * in_sample = proc->inlet_buf[0]->data;
	mfp_sample * rms_sample = proc->outlet_buf[0]->data;
	mfp_sample * peak_sample = proc->outlet_buf[1]->data;
	mfp_sample sample;
	double peak_slope = 1000.0/((double)pdata->peak_decay_ms*(double)mfp_samplerate);
	double peak = pdata->last_peak;
	double rms_accum = pdata->rms_accum;
	double rms_scaler = 1000.0/((double)pdata->rms_window_ms*(double)mfp_samplerate);
	double rms_downsize = 1.0 - rms_scaler;
	int scount; 

	if ((in_sample == NULL) || (rms_sample == NULL) || (peak_sample == NULL)) {
		return 0;
	}

	for(scount = 0; scount < mfp_blocksize; scount++) {
		sample = *in_sample++;

		/* peak */
		if (fabs(sample) > (peak - peak_slope)) {
			peak = fabs(sample);
		}
		else {
			peak -= peak_slope;
		}
		*peak_sample++ = (float)peak;

		/* rms (not really, this is super ghetto) */
		rms_accum = rms_accum*rms_downsize + rms_scaler*sample*sample;
		*rms_sample++ = (mfp_sample)sqrt(rms_accum); 
	}

	/* save state */
	pdata->last_peak = peak;
	pdata->rms_accum = rms_accum;

	return 0;
}

static void 
init(mfp_processor * proc) 
{
	builtin_ampl_data * p = g_malloc(sizeof(builtin_ampl_data));
	proc->data = p;
	p->peak_decay_ms = 200;
	p->last_peak = 0.0;
	p->rms_window_ms = 20;
	p->rms_accum = 0.0;

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
	builtin_ampl_data * pdata = (builtin_ampl_data *)proc->data;
	gpointer peak_decay_ptr = g_hash_table_lookup(proc->params, "peak_decay");
	gpointer rms_window_ptr = g_hash_table_lookup(proc->params, "rms_window");

	if(peak_decay_ptr != NULL) {
		pdata->peak_decay_ms = *(float *)peak_decay_ptr;
	}


	if(rms_window_ptr != NULL) {
		pdata->rms_window_ms = *(float *)rms_window_ptr;
	}

	return;
}

mfp_procinfo *  
init_builtin_ampl(void) {
	mfp_procinfo * p = g_malloc0(sizeof(mfp_procinfo));

	p->name = strdup("ampl~");
	p->is_generator = 0;
	p->process = process;
	p->init = init;
	p->destroy = destroy;
	p->config = config;
	p->params = g_hash_table_new_full(g_str_hash, g_str_equal, NULL, NULL);
	g_hash_table_insert(p->params, "peak_decay", (gpointer)PARAMTYPE_FLT);
	g_hash_table_insert(p->params, "rms_window", (gpointer)PARAMTYPE_FLT);

	return p;
}


