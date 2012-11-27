
#include <stdio.h>
#include <string.h>
#include <sys/time.h>
#include <stdlib.h>
#include <glib.h>

#include "mfp_dsp.h"

static int 
process(mfp_processor * proc) 
{
	mfp_sample * sample = proc->outlet_buf[0]->data;
	int scount; 

	if (sample == NULL) {
		return 0;
	}

	/* iterate */ 
	for(scount=0; scount < mfp_blocksize; scount++) {
		*sample++ = (float)(1.0 - 2.0*(double)random() / ((double)RAND_MAX));
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
init_builtin_noise(void) {
	mfp_procinfo * p = g_malloc(sizeof(mfp_procinfo));
	struct timeval tv;

	gettimeofday(&tv, NULL);
	srandom(tv.tv_usec);
	
	p->name = strdup("noise~");
	p->is_generator = 1;
	p->process = process;
	p->init = init;
	p->destroy = destroy;
	p->config = config;
	p->params = g_hash_table_new_full(g_str_hash, g_str_equal, NULL, NULL);
	return p;
}


