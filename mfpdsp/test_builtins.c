
#include <math.h>
#include <stdio.h>
#include <unistd.h>
#include <sys/time.h>
#include "mfp_dsp.h"
#include "builtin.h"


static void
setparam_gpointer(mfp_processor * proc, char * param_name, gpointer value)
{
    mfp_proc_setparam(proc, g_strdup(param_name), value); 
}

static void
setparam_float(mfp_processor * proc, char * param_name, float value)
{
    gpointer val = g_malloc(sizeof(float));
    *(float *)val = value;
    mfp_proc_setparam(proc, g_strdup(param_name), val); 
}

int
test_sig_1(void * data) 
{
    mfp_procinfo * sigtype = g_hash_table_lookup(mfp_proc_registry, "sig~");
    mfp_processor * sig = mfp_proc_create(sigtype, 1, 1, (mfp_context *)data);
    mfp_sample * outp; 

    printf("   test_sig_1... ");
    setparam_float(sig, "value", 13.0);
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
test_sig_2(void * data) 
{
    mfp_procinfo * sigtype = g_hash_table_lookup(mfp_proc_registry, "sig~");
    mfp_procinfo * plustype = g_hash_table_lookup(mfp_proc_registry, "+~");

    mfp_processor * sig_1 = mfp_proc_create(sigtype, 1, 1, (mfp_context *)data);
    mfp_processor * sig_2 = mfp_proc_create(sigtype, 1, 1, (mfp_context *)data);
    mfp_processor * dac = mfp_proc_create(plustype, 2, 1, (mfp_context *)data);

    mfp_sample * outp; 

    printf("   test_sig_2...\n ");
    mfp_proc_connect(sig_1, 0, dac, 0);
    mfp_proc_connect(sig_2, 0, dac, 0);

    setparam_float(sig_1, "value", 13.0);
    setparam_float(sig_2, "value", 12.0);
    mfp_dsp_schedule((mfp_context *)data);
    mfp_dsp_run((mfp_context *)data);

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
test_plus_multi(void * data) 
{
    mfp_procinfo * sigtype = g_hash_table_lookup(mfp_proc_registry, "sig~");
    mfp_procinfo * plustype = g_hash_table_lookup(mfp_proc_registry, "+~");

    mfp_processor * sig_1 = mfp_proc_create(sigtype, 1, 1, (mfp_context *)data);
    mfp_processor * sig_2 = mfp_proc_create(sigtype, 1, 1, (mfp_context *)data);
    mfp_processor * sig_3 = mfp_proc_create(sigtype, 1, 1, (mfp_context *)data);
    mfp_processor * dac = mfp_proc_create(plustype, 2, 1, (mfp_context *)data);

    mfp_sample * outp; 

    printf("   test_plus_multi... ");
    mfp_proc_connect(sig_1, 0, dac, 0);
    mfp_proc_connect(sig_2, 0, dac, 0);
    mfp_proc_connect(sig_3, 0, dac, 1);

    setparam_float(sig_1, "value", 13.0);
    setparam_float(sig_2, "value", 11.0);
    setparam_float(sig_3, "value", 51.0);
    setparam_float(dac, "const", 10.0);

    mfp_dsp_schedule((mfp_context *)data);
    mfp_dsp_run((mfp_context *)data);

    outp = dac->outlet_buf[0]->data;

    if(outp[0] == 75.0) {
        printf("ok\n");
        return 1;
    }
    else {
        printf("FAIL\n");
        printf("Not equal to 75.0: %f\n", outp[0]);
        return 0;
    }
}


int
test_line_1(void * data) 
{
    mfp_procinfo * proctype = g_hash_table_lookup(mfp_proc_registry, "line~");
    mfp_processor * line = mfp_proc_create(proctype, 0, 1, (mfp_context *)data);
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

    setparam_gpointer(line, "segments", env_1);
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

    if (outp[88] != 0.0) {
        printf("FAIL: outp[88] was %f not 0.0\n", outp[89]);
        return 0;
    }

    if (outp[99] != 0.25) {
        printf("FAIL: outp[100] was %f not 0.25\n", outp[100]);
        return 0;
    }

    if (outp[134] != 1.0) {
        printf("FAIL: outp[134] was %f not 1.0\n", outp[134]);
        return 0;
    }


    printf("ok\n");
    return 1;
}

int
test_line_2(void * data) 
{
    mfp_procinfo * proctype = g_hash_table_lookup(mfp_proc_registry, "line~");
    mfp_processor * line = mfp_proc_create(proctype, 0, 1, (mfp_context *)data);
    mfp_sample * outp; 
    int snum;
    int blocksize = ((mfp_context *)data)->blocksize;
    int samplerate = ((mfp_context *)data)->samplerate;
    float tval_1[] = { 0.0, 1.0, 2.0*(blocksize-1)/samplerate*1000.0 } ;
    float tval_2[] = { 0.0, 0.0, 1.0*(blocksize-1)/samplerate*1000.0 } ;

    GArray * env_1 = g_array_sized_new(TRUE, TRUE, sizeof(float), 4);
    GArray * env_2 = g_array_sized_new(TRUE, TRUE, sizeof(float), 4);

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

    setparam_gpointer(line, "segments", env_1);
    line->needs_config = 1;
    mfp_proc_process(line);

    outp = line->outlet_buf[0]->data;
    if (outp[0] != 0.0) {
        printf("FAIL: outp[0] was %f not 0.0\n", outp[0]);
        return 0;
    }
    if (outp[blocksize -1] != 0.5) {
        printf("FAIL: outp[blocksize-1] was %f not 0.5\n", outp[blocksize-1]);
        return 0;
    }

    setparam_gpointer(line, "segments", env_2);
    line->needs_config = 1;
    mfp_proc_process(line);

    outp = line->outlet_buf[0]->data;
    if (outp[0] != 0.5) {
        printf("FAIL: outp[0] was %f not 0.5\n", outp[0]);
        return 0;
    }
    if (outp[blocksize -1] != 0.0) {
        printf("FAIL: outp[blocksize-1] was %f not 0.0\n", outp[blocksize-1]);
        return 0;
    }
    printf("ok\n");
    return 1;
}


static void
naive_block_sin(mfp_block * in, mfp_block * out)
{
    int i;
    for(i=0; i < in->blocksize; i++) {
        out->data[i] = sinf(in->data[i]);
    }
}

int 
benchmark_osc_1(void * data) 
{
    struct timeval start, end;
    float naive, fast;
    mfp_block * in = mfp_block_new(((mfp_context *)data)->blocksize);
    mfp_block * out = mfp_block_new(((mfp_context *)data)->blocksize);
    int x;
    mfp_procinfo * proctype = g_hash_table_lookup(mfp_proc_registry, "osc~");
    mfp_processor * osc = mfp_proc_create(proctype, 2, 1, (mfp_context *)data);

    setparam_float(osc, "_sig_1", 1000.0);
    setparam_float(osc, "_sig_2", 100.0);

    for(x = 0; x < in->blocksize; x++) {
        in->data[x] = (float)x * 2.0*M_PI/1024.0;
    }

    gettimeofday(&start, NULL);
    for(x = 0; x < 1024; x++) {
        mfp_proc_process(osc);
    }

    gettimeofday(&end, NULL);
    fast = (end.tv_sec + end.tv_usec/1000000.0) - (start.tv_sec + start.tv_usec / 1000000.0);

    gettimeofday(&start, NULL);
    for(x = 0; x < 1024; x++) {
        naive_block_sin(in, out);
    }
    gettimeofday(&end, NULL);
    naive = (end.tv_sec + end.tv_usec/1000000.0) - (start.tv_sec + start.tv_usec / 1000000.0);

    printf("\n     Naive: %f, fast: %f\n", naive, fast);
    return 1;
}

int
test_osc_2(void * data)
{
    mfp_procinfo * proctype = g_hash_table_lookup(mfp_proc_registry, "osc~");
    mfp_procinfo * sigtype = g_hash_table_lookup(mfp_proc_registry, "sig~");
    mfp_processor * osc = mfp_proc_create(proctype, 2, 1, (mfp_context *)data);
    mfp_processor * sig = mfp_proc_create(sigtype, 0, 1, (mfp_context *)data);
    double phase;
    int i;
    int fail = 0;

    printf("test_osc_2... \n");
    setparam_float(osc, "_sig_1", 1000.0);
    setparam_float(sig, "value", 100.0);

    mfp_proc_connect(sig, 0, osc, 1);

    mfp_dsp_schedule((mfp_context *)data);
    mfp_dsp_run((mfp_context *)data);

    for(i=0; i<((mfp_context *)data)->blocksize; i++) {
        phase = fmod((double)i*1000.0*2.0*M_PI/(double)((mfp_context *)data)->samplerate, 2*M_PI);
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
test_osc_1(void * data)
{
    mfp_procinfo * proctype = g_hash_table_lookup(mfp_proc_registry, "osc~");
    mfp_processor * osc = mfp_proc_create(proctype, 2, 1, (mfp_context *)data);
    double phase;
    int i;
    int fail = 0;

    printf("test_osc_1... \n");
    setparam_float(osc, "_sig_1", 1000.0);
    setparam_float(osc, "_sig_2", 100.0);

    mfp_proc_process(osc);

    for(i=0;i< ((mfp_context *)data)->blocksize;i++) {
        phase = fmod((double)i*1000.0*2.0*M_PI/(double)((mfp_context *)data)->samplerate, 2*M_PI);
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


typedef struct {
    char shm_id[64];
    int  shm_fd;
    int  buf_type;
    void * buf_ptr;
    int  buf_chancount;
    int  buf_chansize;
    int  buf_size;
    int  buf_ready; 
} buf_info;


typedef struct {
    buf_info buf_active;
    buf_info buf_to_alloc; 

    mfp_sample * buf_base;  
    int chan_count;
    int chan_size;
    
    /* trigger settings (for TRIG_THRESH, TRIG_EXT modes */ 
    int trig_pretrigger;
    int trig_channel;
    int trig_op;
    mfp_sample trig_thresh;

    /* record settings */ 
    int rec_mode;
    int rec_state;
    int rec_channels;
    int rec_enabled;
    int rec_pos;

    /* play settings */ 
    int play_mode; 
    int play_state;
    int play_channels;
    int play_pos;

    /* region definition (for LOOP modes, set by REC_LOOPSET) */ 
    int region_start;
    int region_end; 

} builtin_buffer_data;

int
test_buffer_1(void * data)
{
    mfp_procinfo * buf_t = g_hash_table_lookup(mfp_proc_registry, "buffer~");
    mfp_processor * b = mfp_proc_create(buf_t, 2, 1, (mfp_context *)data);
    mfp_proc_process(b);
    return 1;
}


int
test_buffer_2(void * data)
{
    mfp_procinfo * line_t = g_hash_table_lookup(mfp_proc_registry, "line~");
    mfp_procinfo * buf_t = g_hash_table_lookup(mfp_proc_registry, "buffer~");
    mfp_processor * line = mfp_proc_create(line_t, 0, 1, (mfp_context *)data);
    mfp_processor * b = mfp_proc_create(buf_t, 2, 1, (mfp_context *)data);
    GArray * lparm = g_array_sized_new(TRUE, TRUE, sizeof(float), 3);
    builtin_buffer_data * info = (builtin_buffer_data *)b->data;
    int blocksize = ((mfp_context *)data)->blocksize;
    int i;
    int fail=0;
    float ft;

    ft = (float)(1000.0*(((mfp_context *)data)->blocksize/2)/((mfp_context *)data)->samplerate);
    g_array_append_val(lparm, ft); 
    ft = 5.0;
    g_array_append_val(lparm, ft);
    ft = 0.0;
    g_array_append_val(lparm, ft);


    setparam_float(b, "buf_mode", 3.0);
    setparam_float(b, "rec_channels", 1.0);
    setparam_float(b, "rec_enabled", 1.0);
    setparam_float(b, "trig_channel", 0.0);
    setparam_float(b, "trig_thresh", 2.0);
    setparam_float(b, "channels", 1.0);
    setparam_float(b, "size", ((mfp_context *)data)->blocksize);

    mfp_proc_connect(line, 0, b, 0);

    mfp_dsp_schedule((mfp_context *)data);
    mfp_dsp_run((mfp_context *)data);

    /* give alloc thread time to work */
    usleep(100000);

    /* bang the line~ */ 
    setparam_gpointer(line, "segments", lparm);
    line->needs_config = 1;
    mfp_dsp_run((mfp_context *)data);

    if((info->buf_active.shm_fd == -1) 
        || (info->buf_active.buf_size != blocksize*sizeof(float))
        || (info->chan_count != 1) 
        || (info->chan_size != blocksize)) {
        printf("config fail %d %d %d %d\n", info->buf_active.shm_fd, 
                info->buf_active.buf_size, 
                info->chan_count, info->chan_size);
        return 0;
    }

    for(i=0; i < blocksize; i++) {
        if (i < blocksize/2.0) {
            if (info->buf_base == NULL || ((float *)(info->buf_base))[i] != 5.0) {
                printf("Fail at %d (%f should be 5.0)\n", i, ((float *)(info->buf_base))[i]);
                fail = 1;
            }
        }
        else {
            if (info->buf_base == NULL || ((float *)(info->buf_base))[i] != 0.0) {
                printf("Fail at %d (%f should be 0.0)\n", i, ((float *)(info->buf_base))[i]);
                fail = 1;
            }
        }
    }
    if (fail)
        return 0;
    return 1;
}

