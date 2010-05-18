#include <math.h>

#include "mfp_dsp.h"

typedef struct {
	double phase;
} builtin_osc_data;


static void
process(mfp_processor * proc) 
{
	gpointer freq_ptr = g_hash_table_lookup(proc->params, "freq");
	gpointer reset_ptr = g_hash_table_lookup(proc->params, "reset");
	double freq;
	double reset_phase;
	double cur_phase; 
	double phase_incr = 2.0 * M_PI * freq / mfp_dsp_samplerate;
	mfp_sample * sample; 
	
	/* get parameters */ 
	if freq_ptr != NULL:
		freq = *(double *)freq_ptr;
	if reset_ptr != NULL: 
		reset_phase = *(double *)reset_ptr;

	/* sending "reset = 1" resets phase */ 
	if (reset_phase > 0.1) {
		*(double *)reset_ptr = 0.0;
		cur_phase = 0.0;
	}
	else {
		cur_phase = ((builtin_osc_data *)(proc->data))->phase;
	}
	
	/* iterate */ 
	sample = proc->outlet_buf[0];

	for(int scount=0; scount < mfp_dsp_blocksize; scount++) {
		*sample++ = sin(cur_phase);
		cur_phase = fmod(cur_phase + phase_incr, 2 * M_PI);
	}

	/* save phase for next starting point */
	((builtin_osc_data *)(proc->data))->phase = cur_phase;
}

static void 
init(mfp_processor * proc) 
{
	builtin_osc_data * d = malloc(sizeof(builtin_osc_data));
	d->phase = 0;
	proc->data = (void *)d;

}

static void
destroy(mfp_processor * proc) 
{
	if (proc->data ! NULL) {
		free(proc->data);
		proc->data = NULL;
	}
}


mfp_procinfo *  
init_builtin_osc(void) {
	mfp_procinfo * p = malloc(sizeof(mfp_procinfo));
	p->name = strdup("osc~");
	p->is_generator = 1;
	p->process = process;
	p->init = init;
	p->destroy = destroy;
	return p;
}


