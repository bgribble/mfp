#include <glib.h>
#include <stdio.h>
#include "mfp_dsp.h"

static void 
init(mfp_processor * proc) 
{
    proc->data = (void *)g_malloc(sizeof(int));
    printf("ext1~ init\n");
}

static void
config(mfp_processor * proc) 
{
    int * d = (int *)(proc->data);
    printf("ext1~ config\n");
    *d = 1;

}


static void
process(mfp_processor * proc) 
{
    int * d = (int *)(proc->data);
    printf("ext1~ process\n");
    *d = 2;
}

void
ext_initialize(void) 
{
    mfp_procinfo * p = g_malloc0(sizeof(mfp_procinfo));

    printf("extension_1.so: in ext_initialize\n");
    p->name = g_strdup("ext1~");
    p->is_generator = GENERATOR_ALWAYS;
    p->init = init;
    p->process = process; 
    p->config = config;
    p->params = g_hash_table_new_full(g_str_hash, g_str_equal, NULL, NULL);
    g_hash_table_insert(mfp_proc_registry, p->name, p);
    printf("extension_1.so: assigned procinfo %p to name %s\n", p, p->name);
    printf("registry has %d keys\n", g_hash_table_size(mfp_proc_registry));
}

