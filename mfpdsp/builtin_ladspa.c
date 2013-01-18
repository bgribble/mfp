#include <stdio.h>
#include <string.h>
#include <sys/time.h>
#include <stdlib.h>
#include <glib.h>
#include <ladspa.h>

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

} builtin_ladspa_data;


static int 
process(mfp_processor * proc) 
{

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
free_private(mfp_processor * proc, void * private_data) {
    builtin_ladspa_data * d = (builtin_ladspa_data *)(data);

    return;
}

static void
prealloc(mfp_processor * proc) 
{
    builtin_ladspa_data * old = (builtin_ladspa_data *)(proc->data);
    builtin_ladspa_data * new = (builtin_ladspa_data *)(proc->prealloc);
    gpointer p_lib_name = g_hash_table_lookup(proc->params, "lib_name");
    gpointer p_lib_index = g_hash_table_lookup(proc->params, "lib_index");
    
    LADSPA_Descriptor * (* descrip_func)(unsigned long);
    LADSPA_Descriptor * descrip;
    int portnum; 
    void * dllib; 

    printf("ladspa~ prealloc\n");

    /* open a new library if necessary.  Don't close the old one yet. */ 
    if ((old->lib_name != p_lib_name) 
        && ((old->lib_name == NULL) || (p_lib_name == NULL) 
            || strcmp(old->lib_name, (char *)p_lib_name))) {
        if (p_lib_name == NULL) {
            new->lib_name = NULL;
        }
        else { 
            new->lib_name = g_strcpy((char *)p_lib_name);
        }

        /* need a new library */ 
        dllib = dlopen((char *)p_lib_name, RTLD_NOW);
        new->lib_dlptr = dllib;
    }
    else {
        dllib = old->lib_dlptr;
    }

    /* get the plugin descriptor */ 
    if ((dllib != old->lib_dlptr) || ((int)p_lib_index != old->lib_index)) {
        descrip_func = dlsym(dllib, "ladspa_descriptor");
        
        /* get the descriptor */ 
        if (descrip_func != NULL) { 
            new->plug_descrip = descrip_func((int)p_lib_index);
        }

        /* instantiate the plugin */ 
        if (new->plug_descrip != NULL) {
            /* allocate storage for control parameters */ 
            new->plug_control = g_malloc(new->plug_descrip->PortCount * sizeof(LADSPA_Data));
            new->plug_handle = new->plug_descrip->instantiate(new->plug_descrip, 
                                                              mfp_samplerate);
            for(portnum=0; portnum < 
        }
    }

    /* create the control parameters vector */



    return;
}

static void
config(mfp_processor * proc) 
{
    builtin_ladspa_data * d = (builtin_ladspa_data *)(proc->data);
    builtin_ladspa_data * new = (builtin_ladspa_data *)(proc->prealloc);
    void * tmp; 

    if (new->lib_name != d->lib_name) {
        tmp = d->lib_name; 
        d->lib_name = new->lib_name;
        new->lib_name = tmp;
    }

    if (new->lib_index != NULL) {
        d->lib_index = new->lib_index;
    }

    if (new->lib_dlptr != d->lib_dlptr) {
        tmp = d->lib_dlptr; 
        d->lib_dlptr = new->lib_dlptr;
        new->lib_dlptr = tmp;
    }
    proc->needs_config = 0;
    return;
}

mfp_procinfo *  
init_builtin_ladspa(void) {
    mfp_procinfo * p = g_malloc(sizeof(mfp_procinfo));
    struct timeval tv;

    p->name = strdup("ladspa~");
    p->is_generator = 0;
    p->process = process;
    p->init = init;
    p->destroy = destroy;
    p->free_private = free_private;
    p->prealloc = prealloc;
    p->config = config;
    p->params = g_hash_table_new_full(g_str_hash, g_str_equal, NULL, NULL);
    return p;
}


