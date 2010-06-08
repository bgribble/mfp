
#include <stdio.h>
#include <string.h>
#include <glib.h>

#include "mfp_dsp.h"

static int 
process(mfp_processor * proc) 
{
	gpointer val_ptr = g_hash_table_lookup(proc->params, "value");
	mfp_sample * sample = proc->outlet_buf[0];
	int scount; 

	if (sample == NULL) {
		return 0;
	}

	/* iterate */ 
	for(scount=0; scount < mfp_blocksize; scount++) {
		*sample++ = *(double *)val_ptr;
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


mfp_procinfo *  
init_builtin_sig(void) {
	mfp_procinfo * p = g_malloc(sizeof(mfp_procinfo));
	p->name = strdup("sig~");
	p->is_generator = 1;
	p->process = process;
	p->init = init;
	p->destroy = destroy;
	return p;
}


