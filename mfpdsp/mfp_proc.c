
#include <glib.h>
#include <string.h>
#include <stdio.h> 
#include <pthread.h>

#include "mfp_dsp.h"
#include "mfp_block.h"

GArray          * mfp_proc_list = NULL;       /* all mfp_processors */ 
GHashTable      * mfp_proc_registry = NULL;   /* hash of names to mfp_procinfo */ 
GHashTable      * mfp_proc_objects = NULL;    /* hash of int ID to mfp_processor * */ 
GHashTable      * mfp_contexts = NULL;        /* hash of int ID to mfp_context */ 

mfp_processor * 
mfp_proc_lookup(int rpcid) 
{
    return g_hash_table_lookup(mfp_proc_objects, GINT_TO_POINTER(rpcid));
}

/* Note: mfp_proc_create is a shortcut used by tests only */ 
mfp_processor *
mfp_proc_create(mfp_procinfo * typeinfo, int num_inlets, int num_outlets, 
                mfp_context * ctxt)
{
    if (typeinfo == NULL) 
        return NULL;
    return mfp_proc_init(mfp_proc_alloc(typeinfo, num_inlets, num_outlets, ctxt), 0, 0);
}




mfp_processor *
mfp_proc_alloc(mfp_procinfo * typeinfo, int num_inlets, int num_outlets, 
               mfp_context * ctxt)
{
    mfp_processor * p;

    if (typeinfo == NULL) {
        return NULL;
    }

    p = g_malloc0(sizeof(mfp_processor));
    p->typeinfo = typeinfo; 
    p->context = ctxt;
    p->params = g_hash_table_new_full(g_str_hash, g_str_equal, NULL, NULL);
    p->depth = -1;
    p->needs_config = 0;
    p->needs_reset = 0;
    p->inlet_conn = NULL;
    p->outlet_conn = NULL;

    mfp_proc_alloc_buffers(p, num_inlets, num_outlets, ctxt->blocksize);

    return p;
}


int
mfp_proc_alloc_buffers(mfp_processor * p, int num_inlets, int num_outlets, int blocksize) 
{
    int count;
    int success=0;

    /* create inlet and outlet processor pointer arrays */
    p->inlet_conn = g_array_sized_new(TRUE, TRUE, sizeof(GArray *), num_inlets);
    
    /* these are arrays of mfp_connection * */    
    for (count = 0; count < num_inlets; count++) {
        GArray * in = g_array_new(TRUE, TRUE, sizeof(mfp_connection *));
        g_array_append_val(p->inlet_conn, in);
    }

    p->outlet_conn = g_array_sized_new(TRUE, TRUE, sizeof(GArray *), num_outlets);

    for (count = 0; count < num_outlets; count++) {
        GArray * out = g_array_new(TRUE, TRUE, sizeof(mfp_connection *));
        g_array_append_val(p->outlet_conn, out);
    }
    
    /* create input and output buffers (will be reallocated if blocksize changes */
    p->inlet_buf = g_malloc0(num_inlets * sizeof(mfp_block *));

    for (count = 0; count < num_inlets; count ++) {
        p->inlet_buf[count] = mfp_block_new(mfp_max_blocksize); 
        mfp_block_resize(p->inlet_buf[count], blocksize);
    }

    p->outlet_buf = g_malloc(num_outlets * sizeof(mfp_sample *));
    
    for (count = 0; count < num_outlets; count ++) {
        p->outlet_buf[count] = mfp_block_new(mfp_max_blocksize);
        mfp_block_resize(p->outlet_buf[count], blocksize);
    }    
    return success;
}

void
mfp_proc_free_buffers(mfp_processor * self) 
{
    int b;
    int num_inlets = self->inlet_conn->len;
    int num_outlets = self->outlet_conn->len;

    for (b=0; b < num_inlets; b++) {
        g_array_free(g_array_index(self->inlet_conn, GArray *, b), TRUE);
    }
    g_array_free(self->inlet_conn, TRUE);


    for (b=0; b < num_outlets; b++) {
        g_array_free(g_array_index(self->outlet_conn, GArray *, b), TRUE);
    }
    g_array_free(self->outlet_conn, TRUE);

    for (b=0; b < num_inlets; b++) {
        mfp_block_free(self->inlet_buf[b]);
    }
    g_free(self->inlet_buf);

    for (b=0; b < num_outlets; b++) {
        mfp_block_free(self->outlet_buf[b]);
    }
    g_free(self->outlet_buf);
}


mfp_processor *
mfp_proc_init(mfp_processor * p, int rpc_id, int patch_id)
{
    p->rpc_id = rpc_id;
    p->patch_id = patch_id;

    /* call type-specific initializer */
    if (p->typeinfo->init)
        p->typeinfo->init(p);

    p->needs_config = 1;

    /* add proc to global list */
    g_array_append_val(mfp_proc_list, p); 
    g_hash_table_insert(mfp_proc_objects, GINT_TO_POINTER(p->rpc_id), p); 

    p->context->needs_reschedule = 1;
    return p;
}

void
mfp_proc_process(mfp_processor * self) 
{
    GArray * inlet_conn;
    mfp_connection ** curr_inlet; 
    mfp_block * inlet_buf;
    
    mfp_processor * upstream_proc;
    mfp_block     * upstream_outlet_buf;
    int           upstream_outlet_num;

    int config_rv;
    int inlet_num;

    /* run config() if params have changed */
    if (self->needs_config) {
        sprintf(mfp_last_activity, "PROCESS: config %d (%s)", 
                self->rpc_id, self->typeinfo->name);
        config_rv = self->typeinfo->config(self);
        if (config_rv != 0) {
            self->needs_config = 0;
        }
        else {
            self->needs_config = 1;
        }
    }

    if (self->needs_reset != 0) {
        if (self->typeinfo->reset != NULL) {
            self->typeinfo->reset(self);
        }

        self->needs_reset = 0;
    }

    /* accumulate all the inlet fan-ins to a single input buffer */ 
    sprintf(mfp_last_activity, "PROCESS: accum %d (%s)", 
            self->rpc_id, self->typeinfo->name);
    for (inlet_num = 0; inlet_num < self->inlet_conn->len; inlet_num++) {
        inlet_conn = g_array_index(self->inlet_conn, GArray *, inlet_num);
        inlet_buf = self->inlet_buf[inlet_num];
        mfp_block_fill(inlet_buf, 0);
        for(curr_inlet = (mfp_connection **)inlet_conn->data; *curr_inlet != NULL; curr_inlet++) {
            upstream_proc = (*curr_inlet)->dest_proc;
            upstream_outlet_num = (*curr_inlet)->dest_port;    
            upstream_outlet_buf = upstream_proc->outlet_buf[upstream_outlet_num];    
            mfp_block_add(inlet_buf, upstream_outlet_buf, inlet_buf);
        }
    }

    /* perform processing */ 
    sprintf(mfp_last_activity, "PROCESS: process %d (%s)", 
            self->rpc_id, self->typeinfo->name);
    self->typeinfo->process(self);    
    sprintf(mfp_last_activity, "PROCESS: process complete %d (%s)", 
            self->rpc_id, self->typeinfo->name);
}


void
mfp_proc_reset(mfp_processor * self)
{
    self->needs_reset = 1;
}


void
mfp_proc_destroy(mfp_processor * self) 
{
    int procpos;
    
    /* remove from global processor list */
    for(procpos=0; procpos < mfp_proc_list->len; procpos++) {
        if (g_array_index(mfp_proc_list, mfp_processor *, procpos) == self) {
            g_array_remove_index(mfp_proc_list, procpos);
            break;
        }
    }

    self->typeinfo->destroy(self);
    g_hash_table_destroy(self->params);

    mfp_proc_free_buffers(self);
    g_free(self);
    self->context->needs_reschedule = 1;
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

    self->context->needs_reschedule = 1;
    return 0;
}

int
mfp_proc_disconnect(mfp_processor * self, int my_outlet, 
                    mfp_processor * target, int targ_inlet)
{
    GArray * xlets;
    mfp_connection * conn;
    int c;


    /* find the connection(s) between the specified ports */
    xlets = g_array_index(self->outlet_conn, GArray *, my_outlet);
    for(c=0; c < xlets->len; c++) {
        conn = g_array_index(xlets, mfp_connection *, c);
        if ((conn->dest_proc == target) && (conn->dest_port == targ_inlet)) {
            conn->dest_proc = NULL;
        }
    }

    /* delete connection from src */
    for(c=xlets->len-1; c >= 0; c--) {
        conn = g_array_index(xlets, mfp_connection *, c);
        if(conn->dest_proc == NULL) {
            g_array_remove_index(xlets, c);
            g_free(conn);
        }
    }

    /* delete connection and object from dest */
    xlets = g_array_index(target->inlet_conn, GArray *, targ_inlet);
    for(c=0; c < xlets->len; c++) {
        conn = g_array_index(xlets, mfp_connection *, c);
        if ((conn->dest_proc == self) && (conn->dest_port == my_outlet)) {
            conn->dest_proc = NULL;
        }
    }

    for(c=xlets->len-1; c >= 0; c--) {
        conn = g_array_index(xlets, mfp_connection *, c);
        if(conn->dest_proc == NULL) {
            g_array_remove_index(xlets, c);
            g_free(conn);
        }
    }

    self->context->needs_reschedule = 1;
    return 0;
}

int 
mfp_proc_setparam_req(mfp_processor * self, mfp_reqdata * rd) 
{
    gpointer orig_key=NULL;
    gpointer orig_val=NULL;
    gboolean found; 

    // FIXME: setparam suffering from serious confuxion

    found = g_hash_table_lookup_extended(self->params, (gpointer)rd->param_name, 
                                         &orig_key, &orig_val);
    g_hash_table_replace(self->params, (gpointer)(rd->param_name), 
                         (gpointer)(rd->param_value));

    if (found == TRUE) { 
        rd->param_name = orig_key;
        rd->param_value = orig_val;
    }
    else {
        rd->param_name = NULL;
        rd->param_value = NULL; 
    }
    return 0;
}

int
mfp_proc_setparam(mfp_processor * self, char * param_name, void * param_val)
{
    gpointer orig_key=NULL;
    gpointer orig_val=NULL;
    gboolean found=FALSE; 

    // FIXME: setparam_req suffering from serious confuxion

    found = g_hash_table_lookup_extended(self->params, (gpointer)param_name, 
                                         &orig_key, &orig_val);
    g_hash_table_replace(self->params, (gpointer)(param_name), (gpointer)(param_val));
    if (found) {
        if (orig_key != NULL)  
            g_free(orig_key);
        if (orig_val != NULL) 
            g_free(orig_val);
    }
}

int
mfp_proc_has_input(mfp_processor * self, int inlet_num)
{
    GArray * xlets;

    if (inlet_num >= self->inlet_conn->len)
        return 0;

    xlets = g_array_index(self->inlet_conn, GArray *, inlet_num);
    if (xlets->len > 0)
        return 1;
    else
        return 0;


}

int 
mfp_proc_error(mfp_processor * self, const char * message)
{
    return 1;
}

