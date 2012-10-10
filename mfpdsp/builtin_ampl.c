
#include <stdio.h>
#include <string.h>
#include <sys/time.h>
#include <stdlib.h>
#include <glib.h>

#include "mfp_dsp.h"

static int 
process(mfp_processor * proc) 
{
	mfp_sample * in_sample = proc->inlet_buf[0]->data;
	mfp_sample * rms_sample = proc->outlet_buf[0]->data;
	mfp_sample * pk_sample = proc->outlet_buf[1]->data;

	int scount; 

	if (in_sample == NULL || rms_sample == NULL || pk_sample == NULL) {
		return 0;
	}


	return 0;
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
init_builtin_ampl(void) {
	mfp_procinfo * p = g_malloc(sizeof(mfp_procinfo));
	struct timeval tv;

	gettimeofday(&tv, NULL);
	srandom(tv.tv_usec);
	
	p->name = strdup("ampl");
	p->is_generator = 1;
	p->process = process;
	p->init = init;
	p->destroy = destroy;
	p->config = config;
	p->params = g_hash_table_new_full(g_str_hash, g_str_equal, NULL, NULL);
	return p;
}


