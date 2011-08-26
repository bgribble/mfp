#include <stdio.h>

#include "mfp_dsp.h"
#include "builtin.h"

int
test_sched_prod_to_sink(void) 
{
	mfp_procinfo * dactype = g_hash_table_lookup(mfp_proc_registry, "dac");
	mfp_procinfo * osctype = g_hash_table_lookup(mfp_proc_registry, "osc");

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

int
test_sched_y_conn(void)
{
	mfp_procinfo * dactype = g_hash_table_lookup(mfp_proc_registry, "dac");
	mfp_procinfo * osctype = g_hash_table_lookup(mfp_proc_registry, "osc");

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

int
test_sig_1(void) 
{
	mfp_procinfo * sigtype = g_hash_table_lookup(mfp_proc_registry, "sig");
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

int
test_sig_2(void) 
{
	mfp_procinfo * sigtype = g_hash_table_lookup(mfp_proc_registry, "sig");
	mfp_procinfo * plustype = g_hash_table_lookup(mfp_proc_registry, "+");

	mfp_processor * sig_1 = mfp_proc_create(sigtype, 1, 1, mfp_blocksize);
	mfp_processor * sig_2 = mfp_proc_create(sigtype, 1, 1, mfp_blocksize);
	mfp_processor * dac = mfp_proc_create(plustype, 2, 1, mfp_blocksize);

	mfp_sample * outp; 

	printf("   test_sig_2...\n ");
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


int
test_plus_multi(void) 
{
	mfp_procinfo * sigtype = g_hash_table_lookup(mfp_proc_registry, "sig");
	mfp_procinfo * plustype = g_hash_table_lookup(mfp_proc_registry, "+");

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
test_line_1(void) 
{
	mfp_procinfo * proctype = g_hash_table_lookup(mfp_proc_registry, "line");
	mfp_processor * line = mfp_proc_create(proctype, 0, 1, mfp_blocksize);
	mfp_sample * outp; 
	int snum;
	float tval[] = { 3.0, 
		             0.0, 1.0, 1.0, 
					 0.0, 0.0, 0.0, 
					 1.0, 1.0, 1.0 };

	GArray * env_1 = g_array_sized_new(TRUE, TRUE, sizeof(float), 6);

	printf("   test_line_1... ");
	for (snum=0; snum < 10; snum++) {
		g_array_append_val(env_1, tval[snum]);
	}

	if(!proctype || !line) {
		printf("FAIL: proctype=%p, proc=%p\n", proctype, line);
		return 0;
	}

	mfp_proc_setparam_array(line, "segments", env_1);
	line->needs_config = 1;

	mfp_proc_process(line);

	outp = line->outlet_buf[0];

	if (outp[0] != 0) {
		printf("FAIL: outp[0] was %f not 0\n", outp[0]);
		return 0;
	}

	if (outp[22] != 0.5) {
		printf("FAIL: outp[22] was %f not 0.5\n", outp[22]);
		return 0;
	}

	if (outp[44] != 1.0) {
		printf("FAIL: outp[44] was %f not 1.0\n", outp[44]);
		return 0;
	}

	if (outp[45] != 0.0) {
		printf("FAIL: outp[45] was %f not 0.0\n", outp[45]);
		return 0;
	}

	if (outp[46] != 0.0) {
		printf("FAIL: outp[46] was %f not 0.0\n", outp[46]);
		return 0;
	}

	if (outp[89] != 0.0) {
		printf("FAIL: outp[89] was %f not 0.0\n", outp[89]);
		return 0;
	}

	if (outp[100] != 0.25) {
		printf("FAIL: outp[100] was %f not 0.25\n", outp[100]);
		return 0;
	}

	if (outp[134] != 1.0) {
		printf("FAIL: outp[134] was %f not 1.0\n", outp[134]);
		return 0;
	}


	/*
	for(snum=0; snum < mfp_blocksize; snum++) {
		printf("  %1.5f", outp[snum]);
		if (snum % 5 == 4) {
			printf("\n");
		}
	}
	*/
	printf("ok\n");
	return 1;
}

int
test_line_2(void) 
{
	mfp_procinfo * proctype = g_hash_table_lookup(mfp_proc_registry, "line");
	mfp_processor * line = mfp_proc_create(proctype, 0, 1, mfp_blocksize);
	mfp_sample * outp; 
	int snum;
	float tval_1[] = { 1.0, 
		               0.0, 1.0, 2.0*(mfp_blocksize-1)/mfp_samplerate*1000.0 } ;
	float tval_2[] = { 1.0, 
		               0.0, 0.0, 1.0*(mfp_blocksize-1)/mfp_samplerate*1000.0 } ;

	GArray * env_1 = g_array_sized_new(TRUE, TRUE, sizeof(float), 4);
	GArray * env_2 = g_array_sized_new(TRUE, TRUE, sizeof(float), 4);

	printf("   test_line_2... ");
	for (snum=0; snum < 4; snum++) {
		g_array_append_val(env_1, tval_1[snum]);
	}
	for (snum=0; snum < 4; snum++) {
		g_array_append_val(env_2, tval_2[snum]);
	}

	if(!proctype || !line) {
		printf("FAIL: proctype=%p, proc=%p\n", proctype, line);
		return 0;
	}

	mfp_proc_setparam_array(line, "segments", env_1);
	line->needs_config = 1;
	mfp_proc_process(line);

	outp = line->outlet_buf[0];
	if (outp[0] != 0.0) {
		printf("FAIL: outp[0] was %f not 0.0\n", outp[0]);
		return 0;
	}
	if (outp[mfp_blocksize -1] != 0.5) {
		printf("FAIL: outp[blocksize-1] was %f not 0.5\n", outp[mfp_blocksize-1]);
		return 0;
	}

	mfp_proc_setparam_array(line, "segments", env_2);
	line->needs_config = 1;
	mfp_proc_process(line);

	outp = line->outlet_buf[0];
	if (outp[0] != 0.5) {
		printf("FAIL: outp[0] was %f not 0.5\n", outp[0]);
		return 0;
	}
	if (outp[mfp_blocksize -1] != 0.0) {
		printf("FAIL: outp[blocksize-1] was %f not 0.0\n", outp[mfp_blocksize-1]);
		return 0;
	}
	printf("ok\n");
	return 1;
}



