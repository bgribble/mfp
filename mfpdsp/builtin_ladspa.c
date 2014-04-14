#include <stdio.h>
#include <string.h>
#include <sys/time.h>
#include <stdlib.h>
#include <glib.h>
#include <ladspa.h>
#include <dlfcn.h>

#include "mfp_dsp.h"

typedef struct {
    /* DLL information */
    char * lib_name;
    int  lib_index;
    void * lib_dlptr;

    /* plugin instance information */
    LADSPA_Descriptor * plug_descrip;
    LADSPA_Handle plug_handle; 
    LADSPA_Data * plug_control; 
    int plug_activated;

    int plug_ready; 

} builtin_ladspa_data;


static void
ladspa_setup(mfp_processor * proc)
{
    builtin_ladspa_data * d = (builtin_ladspa_data *)(proc->data);
    gpointer p_lib_name = g_hash_table_lookup(proc->params, "lib_name");
    gpointer p_lib_index = g_hash_table_lookup(proc->params, "lib_index");
    int lib_index;
    LADSPA_Descriptor * (* descrip_func)(unsigned long);
    int portnum; 
    int portcount;
    int portdesc;
    int signal_ins=0, signal_outs=0;
    void * dllib; 

    if (p_lib_name == NULL) 
        return;

    if (p_lib_index == NULL) {
        lib_index = 0;
    }
    else {
        lib_index = (int)(*(float *)p_lib_index);
    }

    d->lib_name = g_strdup((char *)p_lib_name);
    dllib = dlopen((char *)p_lib_name, RTLD_NOW);
    d->lib_dlptr = dllib;

    /* get the plugin descriptor */ 
    descrip_func = dlsym(dllib, "ladspa_descriptor");
 
    /* get the descriptor */ 
    if (descrip_func != NULL) { 
        d->plug_descrip = descrip_func(lib_index);
    }

    /* instantiate the plugin */ 
    if (d->plug_descrip != NULL) {
        /* allocate storage for control parameters */ 
        portcount = d->plug_descrip->PortCount;
        d->plug_control = g_malloc0(portcount * sizeof(LADSPA_Data));

        /* actually instantiate the plugin */
        d->plug_handle = d->plug_descrip->instantiate(d->plug_descrip, proc->context->samplerate);

        /* count the signal inputs and outputs, and connect control ports */
        for(portnum=0; portnum < portcount; portnum++) {
            portdesc = d->plug_descrip->PortDescriptors[portnum];
            if (portdesc & LADSPA_PORT_AUDIO) {
                if (portdesc & LADSPA_PORT_INPUT) {
                    signal_ins ++;
                }
                else if (portdesc & LADSPA_PORT_OUTPUT) {
                    signal_outs ++;
                }
            }
            else if (portdesc & LADSPA_PORT_CONTROL) {
                d->plug_descrip->connect_port(d->plug_handle, portnum, 
                                              d->plug_control + portnum);
            }
        }

        /* reconfigure buffers in the processor object */ 
        mfp_proc_free_buffers(proc);
        mfp_proc_alloc_buffers(proc, signal_ins, signal_outs, proc->context->blocksize);

        /* connect signal inputs and outputs to the new buffers */
        signal_ins = 0;
        signal_outs = 0;
        for(portnum=0; portnum < portcount; portnum++) {
            portdesc = d->plug_descrip->PortDescriptors[portnum];
            if (portdesc & LADSPA_PORT_AUDIO) {
                if (portdesc & LADSPA_PORT_INPUT) {
                    d->plug_descrip->connect_port(d->plug_handle, portnum, 
                            proc->inlet_buf[signal_ins]->data);
                    signal_ins++;
                }
                else if (portdesc & LADSPA_PORT_OUTPUT) {
                    d->plug_descrip->connect_port(d->plug_handle, portnum, 
                            proc->outlet_buf[signal_outs]->data);
                    signal_outs++;
                }
            }
        }
    }
}



static int 
process(mfp_processor * proc) 
{
    builtin_ladspa_data * d = (builtin_ladspa_data *)(proc->data);

    /* this is simple! */
    if (d->plug_descrip != NULL) {
        d->plug_descrip->run(d->plug_handle, proc->context->blocksize);
    }
    return 0;
}

static void 
init(mfp_processor * proc) 
{
    builtin_ladspa_data * d = (builtin_ladspa_data *)g_malloc0(sizeof(builtin_ladspa_data));

    d->lib_name = NULL;
    d->lib_index = 0;
    d->lib_dlptr = NULL;
    d->plug_descrip = NULL;
    d->plug_control = NULL;
    d->plug_activated = 0;
    proc->data = d;

    ladspa_setup(proc);
    
    return;
}

static void
destroy(mfp_processor * proc) 
{
    builtin_ladspa_data * d = (builtin_ladspa_data *)(proc->data);

    if (d->plug_descrip != NULL) {

        if (d->plug_activated == 1) {
            if (d->plug_descrip->deactivate != NULL)
                d->plug_descrip->deactivate(d->plug_handle);
            d->plug_activated = 0;
        }

        d->plug_descrip->cleanup(d->plug_handle);
        d->plug_descrip = NULL; 

        if (d->lib_dlptr != NULL) {
            dlclose(d->lib_dlptr);
            d->lib_dlptr = NULL;
        }
    }

    if (d->plug_control != NULL) {
        g_free(d->plug_control);
        d->plug_control = NULL;
    }

    return;
}

static int
config(mfp_processor * proc) 
{
    builtin_ladspa_data * d = (builtin_ladspa_data *)(proc->data);
    gpointer control_p = g_hash_table_lookup(proc->params, "plug_control");
    int portnum;

    /* copy plugin control values */ 
    if (control_p != NULL) { 
        for (portnum=0; portnum < ((GArray *)control_p)->len; portnum++) {
            d->plug_control[portnum] = g_array_index((GArray *)control_p, float, portnum);     
        }
    }

    /* activate the plugin if necessary */ 
    if (d->plug_activated != 1) {
        if (d->plug_descrip->activate != NULL)
            d->plug_descrip->activate(d->plug_handle);
        d->plug_activated = 1;
    }
    return 1;
}


mfp_procinfo *  
init_builtin_ladspa(void) {
    mfp_procinfo * p = g_malloc0(sizeof(mfp_procinfo));

    p->name = strdup("ladspa~");
    p->is_generator = 0;
    p->process = process;
    p->init = init;
    p->destroy = destroy;
    p->config = config;
    p->reset = NULL;
    p->params = g_hash_table_new_full(g_str_hash, g_str_equal, NULL, NULL);
    g_hash_table_insert(p->params, "plug_control", (gpointer)PARAMTYPE_FLTARRAY);
    g_hash_table_insert(p->params, "lib_name", (gpointer)PARAMTYPE_STRING);
    g_hash_table_insert(p->params, "lib_index", (gpointer)PARAMTYPE_INT);
    return p;
}


