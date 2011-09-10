#include <math.h>
#include <stdio.h>
#include <string.h>
#include <glib.h>

#include "mfp_dsp.h"
#include "mfp_block.h"
#include "cspline.h"

typedef struct {
	cspline * spline;
	mfp_block * inblk;
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
	mfp_block outblk, amblk, fmblk;
	int mode_am = 0, mode_fm = 0;
	float phase_base;
	float newphase = 0.0;

	if (mfp_proc_has_input(proc, 0)) {
		mode_fm = 1;
		mfp_block_init(&fmblk, proc->inlet_buf[0], mfp_blocksize);
	}

	if (mfp_proc_has_input(proc, 1)) {
		mode_am = 1;
		mfp_block_init(&amblk, proc->inlet_buf[1], mfp_blocksize);
	}

	phase_base = 2.0 * M_PI / (float)mfp_samplerate;

	if (proc->outlet_buf[0] == NULL) {
		mfp_proc_error(proc, "No output buffers allocated");
		return 0;
	}
	else {
		mfp_block_init(&outblk, proc->outlet_buf[0], mfp_blocksize);
	}

	if(mode_fm == 1) {
		newphase = mfp_block_prefix_sum(&fmblk, phase_base, d->phase, &outblk);  	
	}
	else {
		newphase = mfp_block_prefix_sum(NULL, phase_base*d->const_freq, d->phase, &outblk);
	}
	d->phase = newphase;

	return 0;
}

static void 
init(mfp_processor * proc) 
{
	builtin_osc_data * d = g_malloc(sizeof(builtin_osc_data));
	d->spline = cspline_new(9, mfp_blocksize);	
	d->const_ampl = 1.0;
	d->const_freq = 0.0;
	d->phase = 0;

	proc->data = (void *)d;

}

static void
destroy(mfp_processor * proc) 
{
	builtin_osc_data * d = (builtin_osc_data *)(proc->data);
	
	if (d->spline != NULL) {
		cspline_free(d->spline);
		d->spline = NULL;
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


