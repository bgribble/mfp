
#include <glib.h>

#include "mfp_dsp.h"


typedef struct {
	char * name;
	int  is_generator;
	void (* init)(mfp_processor *);
	void (* destroy)(mfp_processor *);
	int  (* process)(mfp_processor *)
} mfp_procinfo;


typedef struct {
	/* type, settable parameters, and internal state */
	mfp_procinfo * typeinfo;
	GHashTable * params; 
	void * data;
	
	/* inlet and outlet connections (g_array of g_array) */
	GArray * inlet_conn;
	GArray * outlet_conn; 

	/* input/output buffers */ 
	struct mfp_sample ** inlet_buf;
	struct mfp_sample ** outlet_buf;

	/* scheduling information */ 
	int depth;

} mfp_processor;

GArray     * proc_list = NULL;       /* all mfp_processors */ 
GHashTable * proc_registry = NULL;   /* hash of names to mfp_procinfo */ 

int
mfp_proc_ready_to_schedule(mfp_processor * p)
{
	int icount;
	int ready = 1;
	mfp_processor ** ip;

	for (icount = 0; icount < p->inlet_count; icount++) {
		ip = p->inlet_conn[icount];
		while(*ip != NULL) {
			if (*ip->depth < 0) {
				ready = 0;
				break;
			}
			ip++;
		}
		if (ready == 0) {
			break;
		}
	}
	return ready;
}

mfp_processor *
mfp_proc_create(mfp_procinfo * typeinfo, int num_inlets, int num_outlets,
				int blocksize) 
{
	mfp_processor * p = malloc(sizeof(mfp_processor));
	int incount, outcount;

	p->typeinfo = typeinfo; 
	p->params = g_hash_table_new(g_str_hash, g_str_equal);
	p->depth = -1;

	/* create inlet and outlet processor pointer arrays */
	p->inlet_conn = g_array_sized_new(TRUE, TRUE, sizeof(GArray *), num_inlets);
	
	for (incount = 0; incount < inlet_count; incount++) {
		GArray * in = g_array_new(TRUE, TRUE, sizeof(mfp_processor *));
		g_array_append(p->inlet_conn, in);
	}

	p->outlet_conn = g_array_sized_new(TRUE, TRUE, sizeof(GArray *), num_outlets);

	for (outcount = 0; outcount < outlet_count; outcount++) {
		GArray * out = g_array_new(TRUE, TRUE, sizeof(mfp_processor *));
		g_array_append(p->outlet_conn, out);
	}
	
	/* create input and output buffers (will be reallocated if blocksize changes */
	p->outlet_buf = malloc(num_outlets * sizeof(mfp_sample *));
	
	for (outcount = 0; outcount < num_outlets; outcount ++) {
		p->outlet_buf[outcount] = malloc(blocksize * sizeof(mfp_sample));
		memset(p->outlet_buf[outcount], 0, blocksize * sizeof(mfp_sample));
	}	

	p->inlet_buf = malloc(num_inlets * sizeof(mfp_sample *));
	
	for (outcount = 0; outcount < num_outlets; outcount ++) {
		p->outlet_buf[outcount] = malloc(blocksize * sizeof(mfp_sample));
		memset(p->outlet_buf[outcount], 0, blocksize * sizeof(mfp_sample));
	}	

	/* call type-specific initializer */
	typeinfo->init(p);

	return p;
}

void
mfp_proc_process(mfp_processor * self) 
{
	/* accumulate all the inlet fan-ins to a single input buffer */ 

	
}


void
mfp_proc_destroy(mfp_processor * self) 
{

}


int 
mfp_proc_connect(mfp_processor * self, mfp_processor * target, 
				 int my_outlet, int targ_inlet)
{

}

int
mfp_proc_disconnect(mfp_processor * self, mfp_processor * target, 
		            int my_outlet, int targ_inlet)
{

}
