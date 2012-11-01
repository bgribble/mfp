
#include <stdio.h>
#include <string.h>
#include <glib.h>

#include "mfp_dsp.h"

typedef struct {
	int retrigger;
	int triggered;
} builtin_snap_data;

static int 
process(mfp_processor * proc) 
{
	builtin_snap_data * pdata = (builtin_snap_data *)proc->data;
	mfp_sample * sample = proc->inlet_buf[0]->data;

	/* iterate */ 
	if (pdata->triggered == 1) {
		mfp_dsp_send_response_float(proc, 0, *sample);
		if (pdata->retrigger == 0) {
			pdata->triggered = 0;
		}
	}
	return 0;
}

static void 
init(mfp_processor * proc) 
{
	builtin_snap_data * p = g_malloc(sizeof(builtin_snap_data));
	proc->data = p;
	p->triggered = 0;
	p->retrigger = 0;

	return;
}

static void
destroy(mfp_processor * proc) 
{
	if (proc->data != NULL) {
		g_free(proc->data);
		proc->data = NULL;
	}
	return;
}

static void
config(mfp_processor * proc) 
{
	builtin_snap_data * pdata = (builtin_snap_data *)proc->data;
	gpointer trigger_ptr = g_hash_table_lookup(proc->params, "trigger");
	gpointer retrigger_ptr = g_hash_table_lookup(proc->params, "retrigger");

	if(trigger_ptr != NULL) {
		pdata->triggered = (int)(*(float *)trigger_ptr);
	}
	if(retrigger_ptr != NULL) {
		pdata->retrigger = (int)(*(float *)retrigger_ptr);
	}


	return;
}

mfp_procinfo *  
init_builtin_snap(void) {
	mfp_procinfo * p = g_malloc(sizeof(mfp_procinfo));
	p->name = strdup("snap");
	p->is_generator = 0;
	p->process = process;
	p->init = init;
	p->destroy = destroy;
	p->config = config;
	p->params = g_hash_table_new_full(g_str_hash, g_str_equal, NULL, NULL);
	g_hash_table_insert(p->params, "trigger", (gpointer)PARAMTYPE_FLT);
	g_hash_table_insert(p->params, "retrigger", (gpointer)PARAMTYPE_FLT);
	return p;
}


