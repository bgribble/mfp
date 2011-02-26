#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include <math.h>
#include "mfp_dsp.h"

static int 
adc_process(mfp_processor * proc) 
{
	gpointer chan_ptr = g_hash_table_lookup(proc->params, "chan");
	int channel = 0;
	mfp_sample * inbuf;
	mfp_sample * outbuf;

	if (chan_ptr != NULL) {
		channel = (int)(*(float *)chan_ptr);
	}

	inbuf = mfp_get_input_buffer(channel);
	outbuf = proc->outlet_buf[0];

	if ((inbuf == NULL) || (outbuf == NULL)) {
		return 0;
	}
	else {
		memcpy(outbuf, inbuf, mfp_blocksize * sizeof(mfp_sample));
	}

	return 1;
}

static int
dac_process(mfp_processor * proc) 
{
	gpointer chan_ptr = g_hash_table_lookup(proc->params, "channel");
	int channel = 0;
	mfp_sample * inbuf;
	mfp_sample * outbuf;
	int count;

	if (chan_ptr != NULL) {
		channel = (int)(*(float *)chan_ptr);
	}
	outbuf = mfp_get_output_buffer(channel);
	inbuf = proc->inlet_buf[0];

	if ((outbuf == NULL) || (inbuf == NULL)) {
		return 0;
	}

	mfp_dsp_accum(outbuf, inbuf, mfp_blocksize);

	return 1;
}

static void 
init(mfp_processor * proc) 
{
	return;
}

static void
destroy(mfp_processor * proc) 
{
	return;
}

static void
config(mfp_processor * proc)
{
	return;
}


mfp_procinfo *  
init_builtin_adc(void) {
	mfp_procinfo * p = malloc(sizeof(mfp_procinfo));
	p->name = strdup("adc");
	p->is_generator = 1;
	p->process = adc_process;
	p->init = init;
	p->destroy = destroy;
	p->config = config;
	p->params = g_hash_table_new_full(g_str_hash, g_str_equal, NULL, NULL);
	g_hash_table_insert(p->params, "channel", (gpointer)1);

	return p;
}

mfp_procinfo *  
init_builtin_dac(void) {
	printf("initializing dac\n");
	mfp_procinfo * p = malloc(sizeof(mfp_procinfo));
	p->name = strdup("dac");
	p->is_generator = 0;
	p->process = dac_process;
	p->init = init;
	p->destroy = destroy;
	p->config = config;
	p->params = g_hash_table_new_full(g_str_hash, g_str_equal, NULL, NULL);
	g_hash_table_insert(p->params, "channel", (gpointer)1);
	return p;
}


