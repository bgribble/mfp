#include <stdio.h>

#include "mfp_dsp.h"
#include "builtin.h"

int
test_sched_prod_to_sink(void * data)
{
    mfp_procinfo * dactype = g_hash_table_lookup(mfp_proc_registry, "out~");
    mfp_procinfo * osctype = g_hash_table_lookup(mfp_proc_registry, "osc~");

    mfp_processor * osc = mfp_proc_create(osctype, 2, 1, (mfp_context *)data);
    mfp_processor * dac = mfp_proc_create(dactype, 1, 0, (mfp_context *)data);

    mfp_proc_connect(osc, 0, dac, 0);
    mfp_dsp_schedule((mfp_context *)data);

    if ((osc->depth == 0) && (dac->depth == 1)) {
        return 1;
    }
    else {
        printf("FAIL\n");
        return 0;
    }
}

int
test_sched_y_conn(void * data)
{
    mfp_procinfo * dactype = g_hash_table_lookup(mfp_proc_registry, "out~");
    mfp_procinfo * osctype = g_hash_table_lookup(mfp_proc_registry, "osc~");

    mfp_processor * osc_1 = mfp_proc_create(osctype, 2, 1, (mfp_context *)data);
    mfp_processor * osc_2 = mfp_proc_create(osctype, 2, 1, (mfp_context *)data);
    mfp_processor * dac = mfp_proc_create(dactype, 1, 0, (mfp_context *)data);

    if((osc_1 == NULL) || (osc_2 == NULL) || (dac == NULL)) {
        printf("  setup failed\n");
        return 0;
    }

    mfp_proc_connect(osc_2, 0, dac, 0);
    mfp_proc_connect(osc_1, 0, dac, 0);
    mfp_dsp_schedule((mfp_context *)data);

    if ((osc_1->depth == 0) && (osc_2->depth == 0) && (dac->depth == 1) ) {
        return 1;
    }
    else {
        printf("FAIL\n");
        return 0;
    }
}


