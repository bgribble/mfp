
#include <dlfcn.h>
#include <stdio.h>
#include <glib.h>

#include "mfp_dsp.h"

GHashTable * mfp_extensions = NULL;


mfp_extinfo * 
mfp_ext_load(char * filename) 
{
    void * dlinfo;
    mfp_extinfo * rv; 
    dlinfo = dlopen(filename, RTLD_NOW);
    
    if (dlinfo == NULL) {
        return NULL; 
    }
    rv = g_malloc0(sizeof(mfp_extinfo));
    rv->filename = filename; 
    rv->dlinfo = dlinfo; 
    rv->state = EXTINFO_LOADED;
    g_hash_table_insert(mfp_extensions, rv->filename, rv); 

    return rv; 
}

void 
mfp_ext_init(mfp_extinfo * ext) 
{
    void (* initfunc) (void); 

    if (ext == NULL) {
        return;
    }

    initfunc = dlsym(ext->dlinfo, "ext_initialize");
    initfunc();
    ext->state = EXTINFO_READY;
}
