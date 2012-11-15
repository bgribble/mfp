
#include <math.h>
#include <stdio.h>
#include "mfp_dsp.h"
#include "builtin.h"


int
test_sig_1(void) 
{
	mfp_procinfo * sigtype = g_hash_table_lookup(mfp_proc_registry, "sig");
	mfp_processor * sig = mfp_proc_create(sigtype, 1, 1, mfp_blocksize);
	mfp_sample * outp; 

	printf("   test_sig_1... ");
	mfp_proc_setparam_float(sig, "value", 13.0);
	mfp_proc_process(sig);

	outp = sig->outlet_buf[0]->data;

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

	outp = dac->inlet_buf[0]->data;

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

	outp = dac->outlet_buf[0]->data;

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

	float tval[] = { 0.0, 1.0, 1.0, 
					 0.0, 0.0, 0.0, 
					 1.0, 1.0, 1.0 };

	GArray * env_1 = g_array_sized_new(TRUE, TRUE, sizeof(float), 6);

	printf("   test_line_1 \n ");
	for (snum=0; snum < 9; snum++) {
		g_array_append_val(env_1, tval[snum]);
	}

	if(!proctype || !line) {
		printf("FAIL: proctype=%p, proc=%p\n", proctype, line);
		return 0;
	}

	mfp_proc_setparam_array(line, "segments", env_1);
	line->needs_config = 1;

	mfp_proc_process(line);

	outp = line->outlet_buf[0]->data;

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
	float tval_1[] = { 0.0, 1.0, 2.0*(mfp_blocksize-1)/mfp_samplerate*1000.0 } ;
	float tval_2[] = { 0.0, 0.0, 1.0*(mfp_blocksize-1)/mfp_samplerate*1000.0 } ;

	GArray * env_1 = g_array_sized_new(TRUE, TRUE, sizeof(float), 4);
	GArray * env_2 = g_array_sized_new(TRUE, TRUE, sizeof(float), 4);

	printf("   test_line_2... ");
	for (snum=0; snum < 3; snum++) {
		g_array_append_val(env_1, tval_1[snum]);
	}
	for (snum=0; snum < 3; snum++) {
		g_array_append_val(env_2, tval_2[snum]);
	}

	if(!proctype || !line) {
		printf("FAIL: proctype=%p, proc=%p\n", proctype, line);
		return 0;
	}

	mfp_proc_setparam_array(line, "segments", env_1);
	line->needs_config = 1;
	mfp_proc_process(line);

	outp = line->outlet_buf[0]->data;
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

	outp = line->outlet_buf[0]->data;
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

int
test_osc_2(void)
{
	mfp_procinfo * proctype = g_hash_table_lookup(mfp_proc_registry, "osc");
	mfp_procinfo * sigtype = g_hash_table_lookup(mfp_proc_registry, "sig");
	mfp_processor * osc = mfp_proc_create(proctype, 2, 1, mfp_blocksize);
	mfp_processor * sig = mfp_proc_create(sigtype, 0, 1, mfp_blocksize);
	double phase;
	int i;
	int fail = 0;

	printf("test_osc_2... \n");
	mfp_proc_setparam_float(osc, "_sig_1", 1000.0);
	mfp_proc_setparam_float(sig, "value", 100.0);

	mfp_proc_connect(sig, 0, osc, 1);

	mfp_dsp_schedule();
	mfp_dsp_run(mfp_blocksize);

	for(i=0;i<mfp_blocksize;i++) {
		phase = fmod((double)i*1000.0*2.0*M_PI/(double)mfp_samplerate, 2*M_PI);
		if (fabs(100.0*sin(phase) - osc->outlet_buf[0]->data[i]) > 0.25) {
			fail = 1;
			printf("i=%d, phase=%f, expected %f, got %f\n", i, phase, 
				   100.0*sin(phase), osc->outlet_buf[0]->data[i]);
		}
	}
	if(fail)
		return 0;
	return 1;

}

int
test_osc_1(void)
{
	mfp_procinfo * proctype = g_hash_table_lookup(mfp_proc_registry, "osc");
	mfp_processor * osc = mfp_proc_create(proctype, 2, 1, mfp_blocksize);
	double phase;
	int i;
	int fail = 0;

	printf("test_osc_1... \n");
	mfp_proc_setparam_float(osc, "_sig_1", 1000.0);
	mfp_proc_setparam_float(osc, "_sig_2", 100.0);

	printf("calling process()");
	mfp_proc_process(osc);

	for(i=0;i<mfp_blocksize;i++) {
		phase = fmod((double)i*1000.0*2.0*M_PI/(double)mfp_samplerate, 2*M_PI);
		if (fabs(100.0*sin(phase) - osc->outlet_buf[0]->data[i]) > 0.25) {
			fail = 1;
			printf("i=%d, phase=%f, expected %f, got %f\n", i, phase, 
				   100.0*sin(phase), osc->outlet_buf[0]->data[i]);
		}
	}
	if(fail)
		return 0;
	return 1;

}

int
test_buffer_1(void)
{
	mfp_procinfo * buf_t = g_hash_table_lookup(mfp_proc_registry, "buffer");
	mfp_processor * b = mfp_proc_create(buf_t, 2, 0, mfp_blocksize);

	mfp_proc_setparam_float(b, "trig_triggered", 1.0);

	mfp_proc_process(b);
	return 1;
}


typedef struct {
	char shm_id[64];
	int shm_fd;
	int shm_size;
	void * shm_ptr;
	int chan_count;
	int chan_size;
	int chan_pos;
	int trig_triggered;
	int trig_channel;
	int trig_op;
	int trig_mode;
	mfp_sample trig_thresh;
} buf_info;


int
test_buffer_2(void)
{
	mfp_procinfo * line_t = g_hash_table_lookup(mfp_proc_registry, "line");
	mfp_procinfo * buf_t = g_hash_table_lookup(mfp_proc_registry, "buffer");
	mfp_processor * line = mfp_proc_create(line_t, 0, 1, mfp_blocksize);
	mfp_processor * b = mfp_proc_create(buf_t, 2, 0, mfp_blocksize);
	GArray * lparm = g_array_sized_new(TRUE, TRUE, sizeof(float), 3);
	buf_info * info = (buf_info *) b->data;
	int i;
	int fail=0;
	float ft;

	ft = (float)(1000.0*(mfp_blocksize/2 -1)/mfp_samplerate);
	g_array_append_val(lparm, ft); 
	ft = 5.0;
	g_array_append_val(lparm, ft);
	ft = 0.0;
	g_array_append_val(lparm, ft);

	mfp_proc_setparam_array(line, "segments", lparm);

	mfp_proc_setparam_float(b, "trig_mode", 1.0);
	mfp_proc_setparam_float(b, "trig_thresh", 2.0);
	mfp_proc_setparam_float(b, "channels", 1.0);
	mfp_proc_setparam_float(b, "size", mfp_blocksize);

	mfp_proc_connect(line, 0, b, 0);

	mfp_dsp_schedule();
	mfp_dsp_run(mfp_blocksize);

	if((info->shm_fd == -1) 
		|| (info->shm_size != mfp_blocksize*sizeof(float))
		|| (info->chan_count != 1) 
		|| (info->chan_size != mfp_blocksize)) {
		printf("config fail %d %d %d %d\n", info->shm_fd, info->shm_size, 
				info->chan_count, info->chan_size);
		return 0;
	}

	for(i=0; i < mfp_blocksize; i++) {
		if (i < mfp_blocksize/2.0) {
			if (info->shm_ptr == NULL || ((float *)(info->shm_ptr))[i] != 5.0) {
				printf("  triggered %d %f\n", i, ((float *)(info->shm_ptr))[i]);
				fail = 1;
			}
		}
		else {
			if (info->shm_ptr == NULL || ((float *)(info->shm_ptr))[i] != 0.0) {
				printf("  zero %d %f", i, ((float *)(info->shm_ptr))[i]);
				fail = 1;
			}
		}
	}
	if (fail)
		return 0;
	return 1;
}

