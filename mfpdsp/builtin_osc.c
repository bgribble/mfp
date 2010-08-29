#include <math.h>
#include <stdio.h>
#include <string.h>
#include <glib.h>

#include "mfp_dsp.h"

typedef struct {
	float phase;
} builtin_osc_data;


static int 
process(mfp_processor * proc) 
{
	gpointer freq_ptr = g_hash_table_lookup(proc->params, "freq");
	gpointer reset_ptr = g_hash_table_lookup(proc->params, "reset");
	float freq;
	float reset_phase;
	float cur_phase; 
	float phase_incr;
	mfp_sample * sample; 
	int scount; 

	/* get parameters */ 
	if (freq_ptr != NULL) 
		freq = *(float *)freq_ptr;
	else
		freq = 0;

	if (reset_ptr != NULL)
		reset_phase = *(float *)reset_ptr;
	else
		reset_phase = 0;

	phase_incr = 2.0 * M_PI * freq / (float)mfp_samplerate;

	/* sending "reset = 1" resets phase */ 
	if (reset_phase > 0.1) {
		*(float *)reset_ptr = 0.0;
		cur_phase = 0.0;
	}
	else {
		cur_phase = ((builtin_osc_data *)(proc->data))->phase;
	}
	
	sample = proc->outlet_buf[0];
	if (sample == NULL) {
		return 0;
	}

	/* iterate */ 
	for(scount=0; scount < mfp_blocksize; scount++) {
		*sample++ = sin(cur_phase);
		cur_phase = fmod(cur_phase + phase_incr, 2 * M_PI);
	}

	/* save phase for next starting point */
	((builtin_osc_data *)(proc->data))->phase = cur_phase;
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


mfp_procinfo *  
init_builtin_osc(void) {
	mfp_procinfo * p = g_malloc(sizeof(mfp_procinfo));
	p->name = strdup("osc~");
	p->is_generator = 1;
	p->process = process;
	p->init = init;
	p->destroy = destroy;
	p->params = g_hash_table_new_full(g_str_hash, g_str_equal, NULL, NULL);
	g_hash_table_insert(p->params, "freq", (gpointer)1);
	g_hash_table_insert(p->params, "reset", (gpointer)1);
	return p;
}


