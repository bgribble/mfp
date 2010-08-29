
#include <glib.h>
#include <string.h>
#include <stdio.h> 

#include "mfp_dsp.h"

GArray     * mfp_proc_list = NULL;       /* all mfp_processors */ 
GHashTable * mfp_proc_registry = NULL;   /* hash of names to mfp_procinfo */ 

mfp_processor *
mfp_proc_create(mfp_procinfo * typeinfo, int num_inlets, int num_outlets,
				int blocksize) 
{
	mfp_processor * p = g_malloc(sizeof(mfp_processor));
	int incount, outcount;

	p->typeinfo = typeinfo; 
	p->params = g_hash_table_new_full(g_str_hash, g_str_equal, g_free, g_free);
	p->pyparams = g_hash_table_new_full(g_str_hash, g_str_equal, g_free, NULL);
	p->depth = -1;

	/* create inlet and outlet processor pointer arrays */
	p->inlet_conn = g_array_sized_new(TRUE, TRUE, sizeof(GArray *), num_inlets);
	
	/* these are arrays of mfp_connection * */	
	for (incount = 0; incount < num_inlets; incount++) {
		GArray * in = g_array_new(TRUE, TRUE, sizeof(mfp_connection *));
		g_array_append_val(p->inlet_conn, in);
	}

	p->outlet_conn = g_array_sized_new(TRUE, TRUE, sizeof(GArray *), num_outlets);

	for (outcount = 0; outcount < num_outlets; outcount++) {
		GArray * out = g_array_new(TRUE, TRUE, sizeof(mfp_connection *));
		g_array_append_val(p->outlet_conn, out);
	}
	
	/* create input and output buffers (will be reallocated if blocksize changes */
	p->inlet_buf = g_malloc0(num_inlets * sizeof(mfp_sample *));

	for (outcount = 0; outcount < num_inlets; outcount ++) {
		p->inlet_buf[outcount] = g_malloc0(blocksize * sizeof(mfp_sample));
	}	

	p->outlet_buf = g_malloc(num_outlets * sizeof(mfp_sample *));
	
	for (outcount = 0; outcount < num_outlets; outcount ++) {
		p->outlet_buf[outcount] = g_malloc0(blocksize * sizeof(mfp_sample));
	}	

	/* call type-specific initializer */
	typeinfo->init(p);

	/* add proc to global list */
	g_array_append_val(mfp_proc_list, p); 

	return p;
}

void
mfp_proc_process(mfp_processor * self) 
{
	GArray * inlet_conn;
	mfp_connection ** curr_inlet; 
	mfp_sample * inlet_buf;
	
	mfp_processor * upstream_proc;
	mfp_sample    * upstream_outlet_buf;
	int           upstream_outlet_num;

	int inlet_num;

	/* accumulate all the inlet fan-ins to a single input buffer */ 
	for (inlet_num = 0; inlet_num < self->inlet_conn->len; inlet_num++) {
		inlet_conn = g_array_index(self->inlet_conn, GArray *, inlet_num);
		inlet_buf = self->inlet_buf[inlet_num];
		memset(inlet_buf, 0, mfp_blocksize * sizeof(mfp_sample));
		for(curr_inlet = (mfp_connection **)inlet_conn->data; *curr_inlet != NULL; curr_inlet++) {
			upstream_proc = (*curr_inlet)->dest_proc;
			upstream_outlet_num = (*curr_inlet)->dest_port;	
			upstream_outlet_buf = upstream_proc->outlet_buf[upstream_outlet_num];	
			mfp_dsp_accum(inlet_buf, upstream_outlet_buf, mfp_blocksize);
		}
	}

	/* perform processing */ 
	self->typeinfo->process(self);	
}


void
mfp_proc_destroy(mfp_processor * self) 
{
	self->typeinfo->destroy(self);
	g_hash_table_destroy(self->params);
	g_array_free(self->inlet_conn, TRUE);
	g_array_free(self->outlet_conn, TRUE);
	g_free(self->inlet_buf);
	g_free(self->outlet_buf);
	g_free(self);
	return;
}


int 
mfp_proc_connect(mfp_processor * self, int my_outlet,  
			     mfp_processor * target, int targ_inlet)
{
	GArray * xlets;
	
	mfp_connection * my_conn = g_malloc(sizeof(mfp_connection));
	mfp_connection * targ_conn = g_malloc(sizeof(mfp_connection));
	
	my_conn->dest_proc = target;
	my_conn->dest_port = targ_inlet;
	targ_conn->dest_proc = self;
	targ_conn->dest_port = my_outlet; 

	xlets = g_array_index(self->outlet_conn, GArray *, my_outlet);
	g_array_append_val(xlets, my_conn);

	xlets =  g_array_index(target->inlet_conn, GArray *, targ_inlet);
	g_array_append_val(xlets, targ_conn);

	return 0;
}

int
mfp_proc_disconnect(mfp_processor * self, int my_outlet, 
		            mfp_processor * target, int targ_inlet)
{
	return 0;
}

int
mfp_proc_setparam_float(mfp_processor * self, char * param_name, float param_val)
{
	gpointer newval = g_malloc(sizeof(float));
	*(float *)newval = param_val;

	printf("setparam_float:	%p %s %f\n", self, param_name, param_val);

	g_hash_table_replace(self->params, g_strdup(param_name), (gpointer)newval);
	return 0;
}

int
mfp_proc_setparam_string(mfp_processor * self, char * param_name, char * param_val)
{
	gpointer newval = g_strdup(param_val);

	printf("setparam_string: %p %s %s\n", self, param_name, param_val);

	g_hash_table_replace(self->params, g_strdup(param_name), (gpointer)newval);
	return 0;
}

int
mfp_proc_setparam_array(mfp_processor * self, char * param_name, GArray * param_val)
{
	printf("setparam_array: %p %s %p\n", self, param_name, param_val);

	g_hash_table_replace(self->params, g_strdup(param_name), (gpointer)param_val);
	return 0;
}

