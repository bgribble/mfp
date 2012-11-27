
#include <stdio.h>
#include <string.h>
#include <glib.h>

#include "mfp_dsp.h"

#define ARITH_OP_ADD 1
#define ARITH_OP_SUB 2
#define ARITH_OP_MUL 3
#define ARITH_OP_DIV 4

typedef struct {
	int op_type;
	mfp_sample const_sample;
} builtin_arith_data;


static void
iterate_div(mfp_sample * in_0, mfp_sample * in_1, mfp_sample const_sample, mfp_sample * outbuf)
{
	int scount;
	int in_1_present=0;

	if (in_1 != NULL)
		in_1_present = 1;

	/* iterate */ 
	for(scount=0; scount < mfp_blocksize; scount++) {
		if (in_1_present)
			*outbuf++ =  *in_0++ / *in_1++ / const_sample;
		else
			*outbuf++ =  *in_0++ / const_sample;

	}
}

static void
iterate_mul(mfp_sample * in_0, mfp_sample * in_1, mfp_sample const_sample, mfp_sample * outbuf)
{
	int scount;
	int in_1_present=0;

	if (in_1 != NULL)
		in_1_present = 1;

	/* iterate */ 
	for(scount=0; scount < mfp_blocksize; scount++) {
		if (in_1_present)
			*outbuf++ =  *in_0++ * *in_1++ * const_sample;
		else
			*outbuf++ =  *in_0++ * const_sample;

	}
}

static void
iterate_sub(mfp_sample * in_0, mfp_sample * in_1, mfp_sample const_sample, mfp_sample * outbuf)
{
	int scount;
	int in_1_present=0;

	if (in_1 != NULL)
		in_1_present = 1;

	/* iterate */ 
	for(scount=0; scount < mfp_blocksize; scount++) {
		if (in_1_present)
			*outbuf++ =  *in_0++ - *in_1++ - const_sample;
		else
			*outbuf++ =  *in_0++ - const_sample;

	}
}

static void
iterate_add(mfp_sample * in_0, mfp_sample * in_1, mfp_sample const_sample, mfp_sample * outbuf)
{
	int scount;
	int in_1_present=0;

	if (in_1 != NULL)
		in_1_present = 1;

	/* iterate */ 
	for(scount=0; scount < mfp_blocksize; scount++) {
		if (in_1_present)
			*outbuf++ = const_sample + *in_0++ + *in_1++;
		else
			*outbuf++ = const_sample + *in_0++ ;

	}
}

static int 
process(mfp_processor * proc) 
{
	builtin_arith_data * d = (builtin_arith_data *)(proc->data);
	mfp_sample const_sample = d->const_sample;

	mfp_sample * outbuf = proc->outlet_buf[0]->data;
	mfp_sample * in_0 = proc->inlet_buf[0]->data;
	mfp_sample * in_1 = proc->inlet_buf[1]->data;

	if ((outbuf == NULL) || (in_0 == NULL) || (in_1 == NULL))  {
		return 0;
	}

	/* pass NULL in_1 if there is nothing connected */
	if (g_array_index(proc->inlet_conn, GArray *, 1)->len == 0)
		in_1 = NULL;

	switch (d->op_type) {
		case ARITH_OP_ADD:
			iterate_add(in_0, in_1, const_sample, outbuf);
			break;
		case ARITH_OP_SUB:
			iterate_sub(in_0, in_1, const_sample, outbuf);
			break;
		case ARITH_OP_MUL:
			iterate_mul(in_0, in_1, const_sample, outbuf);
			break;
		case ARITH_OP_DIV:
			iterate_div(in_0, in_1, const_sample, outbuf);
			break;
	}

	return 1;
}

static void 
init_div(mfp_processor * proc) 
{
	builtin_arith_data * d = g_malloc(sizeof(builtin_arith_data));
	proc->data = d;
	
	d->op_type = ARITH_OP_DIV;
	d->const_sample = (mfp_sample)1.0;
	return;
}

static void 
init_mul(mfp_processor * proc) 
{
	builtin_arith_data * d = g_malloc(sizeof(builtin_arith_data));
	proc->data = d;
	
	d->op_type = ARITH_OP_MUL;
	d->const_sample = (mfp_sample)1.0;
	return;
}

static void 
init_sub(mfp_processor * proc) 
{
	builtin_arith_data * d = g_malloc(sizeof(builtin_arith_data));
	proc->data = d;
	
	d->op_type = ARITH_OP_SUB;
	d->const_sample = (mfp_sample)0.0;
	return;
}

static void 
init_add(mfp_processor * proc) 
{
	builtin_arith_data * d = g_malloc(sizeof(builtin_arith_data));
	proc->data = d;
	
	d->op_type = ARITH_OP_ADD;
	d->const_sample = (mfp_sample)0.0;
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
	gpointer const_ptr = g_hash_table_lookup(proc->params, "const");
	builtin_arith_data * d = (builtin_arith_data *)(proc->data);

	if (const_ptr != NULL) {
		d->const_sample = (mfp_sample)(*(float *)const_ptr);
	}
	return;
}

mfp_procinfo *  
init_builtin_add(void) {
	mfp_procinfo * p = g_malloc(sizeof(mfp_procinfo));
	p->name = strdup("+~");
	p->is_generator = 0;
	p->process = process;
	p->init = init_add;
	p->config = config;
	p->destroy = destroy;
	p->params = g_hash_table_new_full(g_str_hash, g_str_equal, NULL, NULL);
	g_hash_table_insert(p->params, "const", (gpointer)PARAMTYPE_FLT);
	return p;
}

mfp_procinfo *  
init_builtin_sub(void) {
	mfp_procinfo * p = g_malloc(sizeof(mfp_procinfo));
	p->name = strdup("-~");
	p->is_generator = 0;
	p->process = process;
	p->init = init_sub;
	p->config = config;
	p->destroy = destroy;
	p->params = g_hash_table_new_full(g_str_hash, g_str_equal, NULL, NULL);
	g_hash_table_insert(p->params, "const", (gpointer)PARAMTYPE_FLT);
	return p;
}

mfp_procinfo *  
init_builtin_mul(void) {
	mfp_procinfo * p = g_malloc(sizeof(mfp_procinfo));
	p->name = strdup("*~");
	p->is_generator = 0;
	p->process = process;
	p->init = init_mul;
	p->config = config;
	p->destroy = destroy;
	p->params = g_hash_table_new_full(g_str_hash, g_str_equal, NULL, NULL);
	g_hash_table_insert(p->params, "const", (gpointer)PARAMTYPE_FLT);
	return p;
}

mfp_procinfo *  
init_builtin_div(void) {
	mfp_procinfo * p = g_malloc(sizeof(mfp_procinfo));
	p->name = strdup("/~");
	p->is_generator = 0;
	p->process = process;
	p->init = init_div;
	p->config = config;
	p->destroy = destroy;
	p->params = g_hash_table_new_full(g_str_hash, g_str_equal, NULL, NULL);
	g_hash_table_insert(p->params, "const", (gpointer)PARAMTYPE_FLT);
	return p;
}

