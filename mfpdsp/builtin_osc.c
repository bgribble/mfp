#include <math.h>
#include <stdio.h>
#include <string.h>
#include <glib.h>

#include "mfp_dsp.h"
#include "mfp_block.h"
#include "cspline.h"

typedef struct {
	cspline * spline;
	int is_generator;
	float const_freq;
	float const_ampl;
	float phase;
} builtin_osc_data;

static float spline_segments[] = {

};

static int 
process(mfp_processor * proc) 
{
	builtin_osc_data * d = (builtin_osc_data *)(proc->data);
	float cur_phase; 
	float phase_incr;
	mfp_sample * sample; 
	int scount; 

	phase_incr = 2.0 * M_PI * d->freq / (float)mfp_samplerate;

	sample = proc->outlet_buf[0];
	if (sample == NULL) {
		return 0;
	}

	/* iterate */ 
	for(scount=0; scount < mfp_blocksize; scount++) {
		*sample++ = sin(d->phase);
		d->phase = fmod(d->phase + phase_incr, 2 * M_PI);
	}

	return 0;
}

static void 
init(mfp_processor * proc) 
{
	builtin_osc_data * d = g_malloc(sizeof(builtin_osc_data));
	d->cspline = cspline_new(9, mfp_blocksize);	
	d->const_ampl = 1.0;
	d->const_freq = 0.0;
	d->phase = 0;

	proc->data = (void *)d;

}

static void
destroy(mfp_processor * proc) 
{
	builtin_osc_data * d = (builtin_osc_data)(proc->data);
	
	if (d->cspline != NULL) {
		cspline_free(d->cspline);
		d->cspline = NULL;
	}

	if (proc->data != NULL) {
		g_free(proc->data);
		proc->data = NULL;
	}
}

static void
config(mfp_processor * proc) 
{
	builtin_osc_data * d = (builtin_osc_data *)(proc->data);
	gpointer freq_ptr = g_hash_table_lookup(proc->params, "freq");
	gpointer ampl_ptr = g_hash_table_lookup(proc->params, "ampl");
	gpointer phase_ptr = g_hash_table_lookup(proc->params, "phase");

	/* get parameters */ 
	if (freq_ptr != NULL) {
		d->const_freq = *(float *)freq_ptr;
		g_hash_table_remove(proc->params, "freq");
		g_free(freq_ptr);
	}

	if (ampl_ptr != NULL) {
		d->const_ampl = *(float *)ampl_ptr;
		g_hash_table_remove(proc->params, "ampl");
		g_free(ampl_ptr);
	}

	if (phase_ptr != NULL) {
		d->phase = *(float *)phase_ptr;
		g_hash_table_remove(proc->params, "phase");
		g_free(phase_ptr);
	}

	return;
}



mfp_procinfo *  
init_builtin_osc(void) {
	mfp_procinfo * p = g_malloc(sizeof(mfp_procinfo));
	p->name = strdup("osc");
	p->is_generator = GENERATOR_CONDITIONAL;
	p->process = process;
	p->init = init;
	p->destroy = destroy;
	p->config = config;
	p->params = g_hash_table_new_full(g_str_hash, g_str_equal, NULL, NULL);
	g_hash_table_insert(p->params, "freq", (gpointer)PARAMTYPE_FLT);
	g_hash_table_insert(p->params, "ampl", (gpointer)PARAMTYPE_FLT);
	g_hash_table_insert(p->params, "phase", (gpointer)PARAMTYPE_FLT);
	return p;
}


