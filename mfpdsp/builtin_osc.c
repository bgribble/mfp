#include <math.h>
#include <stdio.h>
#include <string.h>
#include <glib.h>

#include "mfp_dsp.h"
#include "mfp_block.h"
#include "cspline.h"

typedef struct {
	cspline * spline;
	mfp_block * int_0;
	float const_freq;
	float const_ampl;
	float phase;
} builtin_osc_data;


static int 
process(mfp_processor * proc) 
{
	builtin_osc_data * d = (builtin_osc_data *)(proc->data);
	mfp_block outblk, amblk, fmblk;
	int mode_am = 0, mode_fm = 0;
	float phase_base;
	float newphase = 0.0;

	printf("osc process enter\n");

	if (mfp_proc_has_input(proc, 0)) {
		mode_fm = 1;
		mfp_block_init(&fmblk, proc->inlet_buf[0], mfp_blocksize);
	}

	if (mfp_proc_has_input(proc, 1)) {
		mode_am = 1;
		mfp_block_init(&amblk, proc->inlet_buf[1], mfp_blocksize);
	}

	phase_base = 2.0 * M_PI / (float)mfp_samplerate;

	printf("osc process: mode_fm=%d, mode_am=%d, phase_base=%f\n", mode_fm, mode_am, phase_base);

	if (proc->outlet_buf[0] == NULL) {
		mfp_proc_error(proc, "No output buffers allocated");
		return 0;
	}
	else {
		mfp_block_init(&outblk, proc->outlet_buf[0], mfp_blocksize);
	}

	if(mode_fm == 1) {
		newphase = mfp_block_prefix_sum(&fmblk, phase_base, d->phase, d->int_0); 
	}
	else {
		newphase = mfp_block_prefix_sum(NULL, phase_base*d->const_freq, d->phase, d->int_0);
	}

	/* now the real work */
	printf("osc process: start phase=%f incr=%f end phase=%f\n", d->phase, phase_base, newphase);
	cspline_block_eval(d->spline, d->int_0, &outblk);

	printf("osc process: applying gain\n");

	/* apply gain or amplitude modulation */
	if(mode_am == 1) {
		mfp_block_mul(&amblk, d->int_0, &outblk);
	}
	else {
		printf("gain = %f\n", d->const_ampl);
		mfp_block_const_mul(d->int_0, d->const_ampl, &outblk);
	}

	d->phase = newphase;
	printf("osc process: done\n");
	return 0;
}

static void 
init(mfp_processor * proc) 
{
	builtin_osc_data * d = g_malloc(sizeof(builtin_osc_data));
	float spline_segments[] = {
		0.        ,  1.02723878, -0.11914602, -0.04787508,
		-0.12429159,  1.41009724, -0.45090743,  0.00708993,
		-0.66900927,  2.35452208, -0.96547636,  0.09130121,
		-1.78575778,  3.74577624, -1.53026182,  0.16535537,
		-2.8811989 ,  4.7583966 , -1.83407729,  0.19460164,
		-2.35376891,  4.09984452, -1.58661354,  0.16535537,
		1.34330369,  1.03527082, -0.755511  ,  0.09130121,
		7.30684176, -3.41647466, 0.317265350, 7.08993236e-03,
		10.12478829, -6.14009133, 1.02156999, -0.04787508 
	};

	printf("osc init\n");
	d->spline = cspline_new(9, mfp_blocksize);	
	d->const_ampl = 1.0;
	d->const_freq = 0.0;
	d->phase = 0;

	cspline_init(d->spline, 0.0, M_2_PI, spline_segments);

	proc->data = (void *)d;

}

static void
destroy(mfp_processor * proc) 
{
	builtin_osc_data * d = (builtin_osc_data *)(proc->data);

	printf("osc destroy\n");
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


