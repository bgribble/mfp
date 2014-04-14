
#include <stdio.h>
#include <string.h>
#include <glib.h>

#include "mfp_dsp.h"

#define ARITH_OP_ADD 1
#define ARITH_OP_SUB 2
#define ARITH_OP_MUL 3
#define ARITH_OP_DIV 4
#define ARITH_OP_GT 5 
#define ARITH_OP_LT 6

typedef struct {
    int op_type;
    mfp_sample const_in_0;
    mfp_sample const_in_1;
} builtin_arith_data;


static void
iterate_div(mfp_processor * proc, mfp_sample * in_0, mfp_sample * in_1, 
            mfp_sample const_in_0, mfp_sample const_in_1, mfp_sample * outbuf)
{
    int scount;
    int in_0_present=((in_0 == NULL) ? 0 : 1);
    int in_1_present=((in_1 == NULL) ? 0 : 1);

    /* iterate */ 
    if (in_0_present && in_1_present) {
        for(scount=0; scount < proc->context->blocksize; scount++) {
            *outbuf++ =  *in_0++ / *in_1++;
        }
    }
    else if (in_1_present) {
        for(scount=0; scount < proc->context->blocksize; scount++) {
            *outbuf++ =  const_in_0 / *in_1++;
        }
    }
    else if (in_0_present) {
        for(scount=0; scount < proc->context->blocksize; scount++) {
            *outbuf++ =  *in_0++ / const_in_1;
        }
    }
    else {
        for(scount=0; scount < proc->context->blocksize; scount++) {
            *outbuf++ =  const_in_0 / const_in_1;
        }
    }
}

static void
iterate_mul(mfp_processor * proc, mfp_sample * in_0, mfp_sample * in_1, 
            mfp_sample const_in_0, mfp_sample const_in_1, mfp_sample * outbuf)
{
    int scount;
    int in_0_present=((in_0 == NULL) ? 0 : 1);
    int in_1_present=((in_1 == NULL) ? 0 : 1);

    /* iterate */ 
    if (in_0_present && in_1_present) {
        for(scount=0; scount < proc->context->blocksize; scount++) {
            *outbuf++ =  *in_0++ * *in_1++;
        }
    }
    else if (in_1_present) {
        for(scount=0; scount < proc->context->blocksize; scount++) {
            *outbuf++ =  const_in_0 * *in_1++;
        }
    }
    else if (in_0_present) {
        for(scount=0; scount < proc->context->blocksize; scount++) {
            *outbuf++ =  *in_0++ * const_in_1;
        }
    }
    else {
        for(scount=0; scount < proc->context->blocksize; scount++) {
            *outbuf++ =  const_in_0 * const_in_1;
        }
    }
}

static void
iterate_sub(mfp_processor * proc, mfp_sample * in_0, mfp_sample * in_1, 
            mfp_sample const_in_0, mfp_sample const_in_1, mfp_sample * outbuf)
{
    int scount;
    int in_0_present=((in_0 == NULL) ? 0 : 1);
    int in_1_present=((in_1 == NULL) ? 0 : 1);

    /* iterate */ 
    if (in_0_present && in_1_present) {
        for(scount=0; scount < proc->context->blocksize; scount++) {
            *outbuf++ =  *in_0++ - *in_1++;
        }
    }
    else if (in_1_present) {
        for(scount=0; scount < proc->context->blocksize; scount++) {
            *outbuf++ =  const_in_0 - *in_1++;
        }
    }
    else if (in_0_present) {
        for(scount=0; scount < proc->context->blocksize; scount++) {
            *outbuf++ =  *in_0++ - const_in_1;
        }
    }
    else {
        for(scount=0; scount < proc->context->blocksize; scount++) {
            *outbuf++ =  const_in_0 - const_in_1;
        }
    }
}

static void
iterate_add(mfp_processor * proc, mfp_sample * in_0, mfp_sample * in_1, 
            mfp_sample const_in_0, mfp_sample const_in_1, mfp_sample * outbuf)
{
    int scount;
    int in_0_present=((in_0 == NULL) ? 0 : 1);
    int in_1_present=((in_1 == NULL) ? 0 : 1);

    /* iterate */ 
    if (in_0_present && in_1_present) {
        for(scount=0; scount < proc->context->blocksize; scount++) {
            *outbuf++ =  *in_0++ + *in_1++;
        }
    }
    else if (in_1_present) {
        for(scount=0; scount < proc->context->blocksize; scount++) {
            *outbuf++ =  const_in_0 + *in_1++;
        }
    }
    else if (in_0_present) {
        for(scount=0; scount < proc->context->blocksize; scount++) {
            *outbuf++ =  *in_0++ + const_in_1;
        }
    }
    else {
        for(scount=0; scount < proc->context->blocksize; scount++) {
            *outbuf++ =  const_in_0 + const_in_1;
        }
    }
}

static void
iterate_gt(mfp_processor * proc, mfp_sample * in_0, mfp_sample * in_1, 
           mfp_sample const_in_0, mfp_sample const_in_1, mfp_sample * outbuf)
{
    int scount;
    int in_0_present=((in_0 == NULL) ? 0 : 1);
    int in_1_present=((in_1 == NULL) ? 0 : 1);

    /* iterate */ 
    if (in_0_present && in_1_present) {
        for(scount=0; scount < proc->context->blocksize; scount++) {
            *outbuf++ = (*in_0++ > *in_1++) ? 1.0 : 0.0; 
        }
    }
    else if (in_1_present) {
        for(scount=0; scount < proc->context->blocksize; scount++) {
            *outbuf++ =  (const_in_0 > *in_1++) ? 1.0 : 0.0;
        }
    }
    else if (in_0_present) {
        for(scount=0; scount < proc->context->blocksize; scount++) {
            *outbuf++ =  (*in_0++ > const_in_1) ? 1.0 : 0.0;
        }
    }
    else {
        for(scount=0; scount < proc->context->blocksize; scount++) {
            *outbuf++ =  (const_in_0 > const_in_1) ? 1.0 : 0.0;
        }
    }
}

static void
iterate_lt(mfp_processor * proc, mfp_sample * in_0, mfp_sample * in_1, 
           mfp_sample const_in_0, mfp_sample const_in_1, mfp_sample * outbuf)
{
    int scount;
    int in_0_present=((in_0 == NULL) ? 0 : 1);
    int in_1_present=((in_1 == NULL) ? 0 : 1);

    /* iterate */ 
    if (in_0_present && in_1_present) {
        for(scount=0; scount < proc->context->blocksize; scount++) {
            *outbuf++ = (*in_0++ < *in_1++) ? 1.0 : 0.0; 
        }
    }
    else if (in_1_present) {
        for(scount=0; scount < proc->context->blocksize; scount++) {
            *outbuf++ =  (const_in_0 < *in_1++) ? 1.0 : 0.0;
        }
    }
    else if (in_0_present) {
        for(scount=0; scount < proc->context->blocksize; scount++) {
            *outbuf++ =  (*in_0++ < const_in_1) ? 1.0 : 0.0;
        }
    }
    else {
        for(scount=0; scount < proc->context->blocksize; scount++) {
            *outbuf++ =  (const_in_0 < const_in_1) ? 1.0 : 0.0;
        }
    }
}

static int 
process(mfp_processor * proc) 
{
    builtin_arith_data * d = (builtin_arith_data *)(proc->data);
    mfp_sample const_in_1 = d->const_in_1;
    mfp_sample const_in_0 = d->const_in_0;

    mfp_sample * outbuf = proc->outlet_buf[0]->data;
    mfp_sample * in_0 = proc->inlet_buf[0]->data;
    mfp_sample * in_1 = proc->inlet_buf[1]->data;

    if ((outbuf == NULL) || (in_0 == NULL) || (in_1 == NULL))  {
        return 0;
    }

    /* pass NULL in_* if there is nothing connected */
    if (!mfp_proc_has_input(proc, 0))
        in_0 = NULL;

    if (!mfp_proc_has_input(proc, 1))
        in_1 = NULL;

    switch (d->op_type) {
        case ARITH_OP_ADD:
            iterate_add(proc, in_0, in_1, const_in_0, const_in_1, outbuf);
            break;
        case ARITH_OP_SUB:
            iterate_sub(proc, in_0, in_1, const_in_0, const_in_1, outbuf);
            break;
        case ARITH_OP_MUL:
            iterate_mul(proc, in_0, in_1, const_in_0, const_in_1, outbuf);
            break;
        case ARITH_OP_DIV:
            iterate_div(proc, in_0, in_1, const_in_0, const_in_1, outbuf);
            break;
        case ARITH_OP_GT:
            iterate_gt(proc, in_0, in_1, const_in_0, const_in_1, outbuf);
            break;
        case ARITH_OP_LT:
            iterate_lt(proc, in_0, in_1, const_in_0, const_in_1, outbuf);
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
    d->const_in_0 = (mfp_sample)1.0;
    d->const_in_1 = (mfp_sample)1.0;
    return;
}

static void 
init_mul(mfp_processor * proc) 
{
    builtin_arith_data * d = g_malloc(sizeof(builtin_arith_data));
    proc->data = d;
    
    d->op_type = ARITH_OP_MUL;
    d->const_in_0 = (mfp_sample)1.0;
    d->const_in_1 = (mfp_sample)1.0;
    return;
}

static void 
init_sub(mfp_processor * proc) 
{
    builtin_arith_data * d = g_malloc(sizeof(builtin_arith_data));
    proc->data = d;
    
    d->op_type = ARITH_OP_SUB;
    d->const_in_0 = (mfp_sample)0.0;
    d->const_in_1 = (mfp_sample)0.0;
    return;
}

static void 
init_add(mfp_processor * proc) 
{
    builtin_arith_data * d = g_malloc(sizeof(builtin_arith_data));
    proc->data = d;
    
    d->op_type = ARITH_OP_ADD;
    d->const_in_0 = (mfp_sample)0.0;
    d->const_in_1 = (mfp_sample)0.0;
    return;
}

static void 
init_gt(mfp_processor * proc) 
{
    builtin_arith_data * d = g_malloc(sizeof(builtin_arith_data));
    proc->data = d;
    
    d->op_type = ARITH_OP_GT;
    d->const_in_0 = (mfp_sample)0.0;
    d->const_in_1 = (mfp_sample)0.0;
    return;
}

static void 
init_lt(mfp_processor * proc) 
{
    builtin_arith_data * d = g_malloc(sizeof(builtin_arith_data));
    proc->data = d;
    
    d->op_type = ARITH_OP_LT;
    d->const_in_0 = (mfp_sample)0.0;
    d->const_in_1 = (mfp_sample)0.0;
    return;
}

static void
destroy(mfp_processor * proc) 
{
    return;
}

static int
config(mfp_processor * proc) 
{
    gpointer sig_0_ptr = g_hash_table_lookup(proc->params, "_sig_0");
    gpointer sig_1_ptr = g_hash_table_lookup(proc->params, "_sig_1");

    builtin_arith_data * d = (builtin_arith_data *)(proc->data);

    if (sig_0_ptr != NULL) {
        d->const_in_0 = (mfp_sample)(*(float *)sig_0_ptr);
    }
    if (sig_1_ptr != NULL) {
        d->const_in_1 = (mfp_sample)(*(float *)sig_1_ptr);
    }
    return 1;
}

mfp_procinfo *  
init_builtin_add(void) {
    mfp_procinfo * p = g_malloc0(sizeof(mfp_procinfo));
    p->name = strdup("+~");
    p->is_generator = 0;
    p->process = process;
    p->init = init_add;
    p->config = config;
    p->destroy = destroy;
    p->params = g_hash_table_new_full(g_str_hash, g_str_equal, NULL, NULL);
    g_hash_table_insert(p->params, "_sig_0", (gpointer)PARAMTYPE_FLT);
    g_hash_table_insert(p->params, "_sig_1", (gpointer)PARAMTYPE_FLT);
    return p;
}

mfp_procinfo *  
init_builtin_sub(void) {
    mfp_procinfo * p = g_malloc0(sizeof(mfp_procinfo));
    p->name = strdup("-~");
    p->is_generator = 0;
    p->process = process;
    p->init = init_sub;
    p->config = config;
    p->destroy = destroy;
    p->params = g_hash_table_new_full(g_str_hash, g_str_equal, NULL, NULL);
    g_hash_table_insert(p->params, "_sig_0", (gpointer)PARAMTYPE_FLT);
    g_hash_table_insert(p->params, "_sig_1", (gpointer)PARAMTYPE_FLT);
    return p;
}

mfp_procinfo *  
init_builtin_mul(void) {
    mfp_procinfo * p = g_malloc0(sizeof(mfp_procinfo));
    p->name = strdup("*~");
    p->is_generator = 0;
    p->process = process;
    p->init = init_mul;
    p->config = config;
    p->destroy = destroy;
    p->params = g_hash_table_new_full(g_str_hash, g_str_equal, NULL, NULL);
    g_hash_table_insert(p->params, "_sig_0", (gpointer)PARAMTYPE_FLT);
    g_hash_table_insert(p->params, "_sig_1", (gpointer)PARAMTYPE_FLT);
    return p;
}

mfp_procinfo *  
init_builtin_div(void) {
    mfp_procinfo * p = g_malloc0(sizeof(mfp_procinfo));
    p->name = strdup("/~");
    p->is_generator = 0;
    p->process = process;
    p->init = init_div;
    p->config = config;
    p->destroy = destroy;
    p->params = g_hash_table_new_full(g_str_hash, g_str_equal, NULL, NULL);
    g_hash_table_insert(p->params, "_sig_0", (gpointer)PARAMTYPE_FLT);
    g_hash_table_insert(p->params, "_sig_1", (gpointer)PARAMTYPE_FLT);
    return p;
}

mfp_procinfo *  
init_builtin_lt(void) {
    mfp_procinfo * p = g_malloc0(sizeof(mfp_procinfo));
    p->name = strdup("<~");
    p->is_generator = 0;
    p->process = process;
    p->init = init_lt;
    p->config = config;
    p->destroy = destroy;
    p->params = g_hash_table_new_full(g_str_hash, g_str_equal, NULL, NULL);
    g_hash_table_insert(p->params, "_sig_0", (gpointer)PARAMTYPE_FLT);
    g_hash_table_insert(p->params, "_sig_1", (gpointer)PARAMTYPE_FLT);
    return p;
}

mfp_procinfo *  
init_builtin_gt(void) {
    mfp_procinfo * p = g_malloc0(sizeof(mfp_procinfo));
    p->name = strdup(">~");
    p->is_generator = 0;
    p->process = process;
    p->init = init_gt;
    p->config = config;
    p->destroy = destroy;
    p->params = g_hash_table_new_full(g_str_hash, g_str_equal, NULL, NULL);
    g_hash_table_insert(p->params, "_sig_0", (gpointer)PARAMTYPE_FLT);
    g_hash_table_insert(p->params, "_sig_1", (gpointer)PARAMTYPE_FLT);
    return p;
}

