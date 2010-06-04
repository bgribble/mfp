#include <math.h>
#include <string.h>
#include <glib.h>

#include "mfp_dsp.h"

typedef struct {
	double phase;
} builtin_osc_data;


static int 
process(mfp_processor * proc) 
{
	gpointer freq_ptr = g_hash_table_lookup(proc->params, "freq");
	gpointer reset_ptr = g_hash_table_lookup(proc->params, "reset");
	double freq;
	double reset_phase;
	double cur_phase; 
	double phase_incr;
	mfp_sample * sample; 
	int scount; 

	printf("osc~ process\n");	
	/* get parameters */ 
	if (freq_ptr != NULL) 
		freq = *(double *)freq_ptr;
	else
		freq = 0;

	if (reset_ptr != NULL)
		reset_phase = *(double *)reset_ptr;
	else
		reset_phase = 0;

	phase_incr = 2.0 * M_PI * freq / mfp_samplerate;

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
	return p;
}


