
#include <stdio.h>
#include <string.h>
#include <glib.h>

#include "mfp_dsp.h"

static int 
process(mfp_processor * proc) 
{
	gpointer const_ptr = g_hash_table_lookup(proc->params, "const");
	mfp_sample const_sample ;

	mfp_sample * outbuf = proc->outlet_buf[0];
	mfp_sample * in_0 = proc->inlet_buf[0];
	mfp_sample * in_1 = proc->inlet_buf[1];

	int scount; 

	if (const_ptr != NULL) {
		const_sample = (mfp_sample)(*(double *)const_ptr);
	}
	else {
		const_sample = (mfp_sample)(0.0);
	}

	if ((outbuf == NULL) || (in_0 == NULL) || (in_1 == NULL))  {
		return 0;
	}

	/* iterate */ 
	for(scount=0; scount < mfp_blocksize; scount++) {
		*outbuf++ = const_sample + *in_0++ + *in_1++;
	}

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


mfp_procinfo *  
init_builtin_plus(void) {
	mfp_procinfo * p = g_malloc(sizeof(mfp_procinfo));
	p->name = strdup("+~");
	p->is_generator = 0;
	p->process = process;
	p->init = init;
	p->destroy = destroy;
	return p;
}


