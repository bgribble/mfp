#include <glib.h>
#include <jack/jack.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <execinfo.h>
#include <fcntl.h>
#include <sys/stat.h>
#include <semaphore.h>

#include "mfp_dsp.h"

static int
process_cb (jack_nframes_t nframes, void * ctxt_arg)
{
    mfp_context * ctxt = (mfp_context *)ctxt_arg;
    jack_position_t trans_info;
    jack_transport_state_t trans_state; 

    /* get transport info */ 
    trans_state = jack_transport_query(ctxt->info.jack->client, &trans_info);
    trans_state; 

    /* 
    printf("JACK transport: frame %d, rate %d, time %e\n", trans_info.frame, 
            trans_info.frame_rate, trans_info.frame_time);
    printf("JACK BBT: %d:%d:%d\n", trans_info.bar, trans_info.beat, trans_info.tick);
    */ 

    /* run processing network */ 
    mfp_dsp_set_blocksize(ctxt, nframes);
    mfp_dsp_run(ctxt);

    return 0;
}


static void
info_cb (const char * msg)
{
    return;
}

static int 
reorder_cb (void * ctxt_arg) 
{
    mfp_context * ctxt = (mfp_context *)ctxt_arg;
    jack_latency_range_t range;
    int portno;
    int lastval;
    int maxval;
    int num_inports = mfp_num_input_buffers(ctxt);
    int num_outports = mfp_num_output_buffers(ctxt);

    jack_recompute_total_latencies(ctxt->info.jack->client);
    maxval = 0;
    for (portno = 0; portno < num_inports; portno++) {
        jack_port_get_latency_range(g_array_index(ctxt->info.jack->input_ports, 
                                                  jack_port_t *, portno),
                                    JackCaptureLatency, & range); 
        if (range.max > maxval) {
            maxval = range.max;
        }

        lastval = jack_port_get_total_latency(ctxt->info.jack->client, 
                                              g_array_index(ctxt->info.jack->input_ports, 
                                                            jack_port_t *, portno));
        if (lastval > maxval) {
            maxval = lastval;
        }

    }
    mfp_in_latency = 1000.0 * maxval / ctxt->samplerate;

    maxval = 0;
    for (portno = 0; portno < num_outports; portno++) {
        jack_port_get_latency_range(g_array_index(ctxt->info.jack->output_ports, 
                                                  jack_port_t *,  portno),
                                    JackPlaybackLatency, & range); 
        if (range.max > maxval) {
            maxval = range.max;
        }
        lastval = jack_port_get_total_latency(ctxt->info.jack->client, 
                                              g_array_index(ctxt->info.jack->output_ports, 
                                                            jack_port_t *, portno));
        if (lastval > maxval) {
            maxval = lastval;
        }
    }

    mfp_out_latency = 1000.0 * maxval / ctxt->samplerate;

    /* mfp_dsp_send_response_float(NULL, 1, 0.0); */
    return 0;
}

mfp_context * 
mfp_jack_startup(char * client_name, int num_inputs, int num_outputs) 
{
    mfp_context * ctxt;
    jack_status_t status;
    jack_port_t * port;
    int i;

    char namebuf[16];

    ctxt = mfp_context_new(CTYPE_JACK);

    if ((ctxt->info.jack->client = jack_client_open(client_name, JackNullOption, &status, NULL)) == 0) {
        fprintf (stderr, "jack_client_open() failed.");
        return NULL;
    }
    
    /* callbacks */ 
    jack_set_process_callback(ctxt->info.jack->client, process_cb, ctxt);
    jack_set_graph_order_callback(ctxt->info.jack->client, reorder_cb, ctxt);

    /* no info logging to console */ 
    jack_set_info_function(info_cb);
    jack_set_error_function(info_cb);
    
    /* create application input and output ports */ 
    if (num_inputs > 0) {
        ctxt->info.jack->input_ports = g_array_new(TRUE, TRUE, sizeof(jack_port_t *));

        for(i=0; i<num_inputs; i++) {
            snprintf(namebuf, 16, "in_%d", i);
            port = jack_port_register (ctxt->info.jack->client, namebuf, JACK_DEFAULT_AUDIO_TYPE, 
                                       JackPortIsInput, i);
            g_array_append_val(ctxt->info.jack->input_ports, port);
        }
    }

    if (num_outputs > 0) {
        ctxt->info.jack->output_ports = g_array_new(TRUE, TRUE, sizeof(jack_port_t *));

        for(i=0; i<num_outputs; i++) {
            snprintf(namebuf, 16, "out_%d", i);
            port = jack_port_register (ctxt->info.jack->client, namebuf, JACK_DEFAULT_AUDIO_TYPE, 
                                       JackPortIsOutput, i);
            g_array_append_val(ctxt->info.jack->output_ports, port);
        }

    }
    
    /* find out sample rate */ 
    ctxt->samplerate = jack_get_sample_rate(ctxt->info.jack->client);
    ctxt->blocksize = jack_get_buffer_size(ctxt->info.jack->client);
    mfp_in_latency = 3000.0 * ctxt->blocksize / ctxt->samplerate; 
    mfp_out_latency = 3000.0 * ctxt->blocksize / ctxt->samplerate; 

    printf("jack_startup: samplerate=%d, blocksize=%d, in_latency=%.1f, out_latency = %.1f\n", 
            ctxt->samplerate, ctxt->blocksize, mfp_in_latency, mfp_out_latency); 

    /* tell the JACK server that we are ready to roll */
    if (jack_activate (ctxt->info.jack->client)) {
        fprintf (stderr, "cannot activate client");
        return NULL;
    }

    return ctxt;

}

void
mfp_jack_shutdown(mfp_context * ctxt) 
{
    printf("jack_shutdown: closing client, good-bye!\n");
    jack_deactivate(ctxt->info.jack->client);
    jack_client_close(ctxt->info.jack->client);
    ctxt->info.jack->client = NULL;
}

void * 
test_SETUP(void) 
{
    mfp_context * ctxt = g_malloc0(sizeof(mfp_context));
    ctxt->blocksize = 1024;
    ctxt->samplerate = 44100;
    
    /* called before each test case, where each test case is run 
     * in a separate executable */
    mfp_dsp_init();
    mfp_alloc_init();


    return (void *)ctxt;
}

void * 
benchmark_SETUP(void) 
{
    return test_SETUP();
}

int
test_TEARDOWN(void)
{
    mfp_alloc_finish();
    return 0;
}


static void
sigsegv_handler(int sig, siginfo_t *si, void *unused)
{
    void * buffer[100];
    char ** strings;
    int nptrs, j;

    printf("ERROR: SIGSEGV received\n");
    nptrs = backtrace(buffer, 100);
    strings = backtrace_symbols(buffer, nptrs);

    for (j = 0; j < nptrs; j++)
        printf("%s\n", strings[j]);

    free(strings);

    exit(-11);
}




