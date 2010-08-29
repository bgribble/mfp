#include <stdio.h>

#include "mfp_dsp.h"
#include "builtin.h"

static int
test_sched_prod_to_sink(void) 
{
	mfp_procinfo * dactype = g_hash_table_lookup(mfp_proc_registry, "dac~");
	mfp_procinfo * osctype = g_hash_table_lookup(mfp_proc_registry, "osc~");

	mfp_processor * osc = mfp_proc_create(osctype, 2, 1, mfp_blocksize);
	mfp_processor * dac = mfp_proc_create(dactype, 1, 0, mfp_blocksize);
	printf("   test_sched_prod_to_sink... ");

	mfp_proc_connect(osc, 0, dac, 0);
	mfp_dsp_schedule();

	if ((osc->depth == 0) && (dac->depth == 1)) {
		printf("ok\n");
		return 1;
	}
	else {
		printf("FAIL\n");
		return 0;
	}
}

static int
test_sched_y_conn(void)
{
	mfp_procinfo * dactype = g_hash_table_lookup(mfp_proc_registry, "dac~");
	mfp_procinfo * osctype = g_hash_table_lookup(mfp_proc_registry, "osc~");

	mfp_processor * osc_1 = mfp_proc_create(osctype, 2, 1, mfp_blocksize);
	mfp_processor * osc_2 = mfp_proc_create(osctype, 2, 1, mfp_blocksize);
	mfp_processor * dac = mfp_proc_create(dactype, 1, 0, mfp_blocksize);

	printf("   test_sched_y_conn... ");

	mfp_proc_connect(osc_2, 0, dac, 0);
	mfp_proc_connect(osc_1, 0, dac, 0);
	mfp_dsp_schedule();
	
	if ((osc_1->depth == 0) && (osc_2->depth == 0) && (dac->depth == 1) ) {
		printf("ok\n");
		return 1;
	}
	else {
		printf("FAIL\n");
		return 0;
	}
}

static int
test_sig_1(void) 
{
	mfp_procinfo * sigtype = g_hash_table_lookup(mfp_proc_registry, "sig~");
	mfp_processor * sig = mfp_proc_create(sigtype, 1, 1, mfp_blocksize);
	mfp_sample * outp; 

	printf("   test_sig_1... ");
	mfp_proc_setparam_float(sig, "value", 13.0);
	mfp_proc_process(sig);

	outp = sig->outlet_buf[0];

	if(outp[0] == 13.0) {
		printf("ok\n");
		return 1;
	}
	else {
		printf("FAIL\n");
		printf("Not equal to 13.0: %f\n", outp[0]);
		return 0;
	}
}

static int
test_sig_2(void) 
{
	mfp_procinfo * sigtype = g_hash_table_lookup(mfp_proc_registry, "sig~");
	mfp_procinfo * plustype = g_hash_table_lookup(mfp_proc_registry, "+~");

	mfp_processor * sig_1 = mfp_proc_create(sigtype, 1, 1, mfp_blocksize);
	mfp_processor * sig_2 = mfp_proc_create(sigtype, 1, 1, mfp_blocksize);
	mfp_processor * dac = mfp_proc_create(plustype, 2, 1, mfp_blocksize);

	mfp_sample * outp; 

	printf("   test_sig_2... ");
	mfp_proc_connect(sig_1, 0, dac, 0);
	mfp_proc_connect(sig_2, 0, dac, 0);

	mfp_proc_setparam_float(sig_1, "value", 13.0);
	mfp_proc_setparam_float(sig_2, "value", 12.0);
	mfp_dsp_schedule();
	mfp_dsp_run(mfp_blocksize);

	outp = dac->inlet_buf[0];

	if(outp[0] == 25.0) {
		printf("ok\n");
		return 1;
	}
	else {
		printf("FAIL\n");
		printf("Not equal to 25.0: %f\n", outp[0]);
		return 0;
	}
}


static int
test_plus_multi(void) 
{
	mfp_procinfo * sigtype = g_hash_table_lookup(mfp_proc_registry, "sig~");
	mfp_procinfo * plustype = g_hash_table_lookup(mfp_proc_registry, "+~");

	mfp_processor * sig_1 = mfp_proc_create(sigtype, 1, 1, mfp_blocksize);
	mfp_processor * sig_2 = mfp_proc_create(sigtype, 1, 1, mfp_blocksize);
	mfp_processor * sig_3 = mfp_proc_create(sigtype, 1, 1, mfp_blocksize);
	mfp_processor * dac = mfp_proc_create(plustype, 2, 1, mfp_blocksize);

	mfp_sample * outp; 

	printf("   test_plus_multi... ");
	mfp_proc_connect(sig_1, 0, dac, 0);
	mfp_proc_connect(sig_2, 0, dac, 0);
	mfp_proc_connect(sig_3, 0, dac, 1);

	mfp_proc_setparam_float(sig_1, "value", 13.0);
	mfp_proc_setparam_float(sig_2, "value", 11.0);
	mfp_proc_setparam_float(sig_3, "value", 51.0);
	mfp_proc_setparam_float(dac, "const", 10.0);

	mfp_dsp_schedule();
	mfp_dsp_run(mfp_blocksize);

	outp = dac->outlet_buf[0];

	if(outp[0] == 85.0) {
		printf("ok\n");
		return 1;
	}
	else {
		printf("FAIL\n");
		printf("Not equal to 25.0: %f\n", outp[0]);
		return 0;
	}
}
int 
test_ctests(void) 
{
	printf ("\n");

	if (!test_sched_prod_to_sink()) 
		return 0;

	if (!test_sched_y_conn())
		return 0;

	if (!test_sig_1())
		return 0;

	if (!test_sig_2())
		return 0;

	if (!test_plus_multi())
		return 0;

	return 1;
}

