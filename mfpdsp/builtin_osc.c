#include <math.h>
#include <stdio.h>
#include <string.h>
#include <glib.h>

#include "mfp_dsp.h"

typedef struct {
	float freq;
	float phase;
} builtin_osc_data;


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
	d->phase = 0;
	proc->data = (void *)d;

}

static void
destroy(mfp_processor * proc) 
{
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
	gpointer phase_ptr = g_hash_table_lookup(proc->params, "phase");

	/* get parameters */ 
	if (freq_ptr != NULL) {
		d->freq = *(float *)freq_ptr;
		g_hash_table_remove(proc->params, "freq");
		g_free(freq_ptr);
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
	p->is_generator = 1;
	p->process = process;
	p->init = init;
	p->destroy = destroy;
	p->config = config;
	p->params = g_hash_table_new_full(g_str_hash, g_str_equal, NULL, NULL);
	g_hash_table_insert(p->params, "freq", (gpointer)PARAMTYPE_FLT);
	g_hash_table_insert(p->params, "reset", (gpointer)PARAMTYPE_FLT);
	return p;
}


