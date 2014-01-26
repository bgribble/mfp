#include <glib.h>
#include <jack/jack.h>
#include <stdio.h>
#include <string.h>
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
    trans_state = jack_transport_query(ctxt->jack.client, &trans_info);
    trans_state; 

    /* 
    printf("JACK transport: frame %d, rate %d, time %e\n", trans_info.frame, 
            trans_info.frame_rate, trans_info.frame_time);
    printf("JACK BBT: %d:%d:%d\n", trans_info.bar, trans_info.beat, trans_info.tick);
    */ 

    /* run processing network */ 
    if (mfp_dsp_enabled == 1) {
        mfp_dsp_run((int)nframes);
    }
    else {
        printf("DSP DISABLED, process() not running network\n");
    }

    return 0;
}


static void
info_cb (const char * msg)
{
    return;
}

static void
reorder_cb (void * ctxt_arg) 
{
    mfp_context * ctxt = (mfp_context *)ctxt_arg;
    jack_latency_range_t range;
    int portno;
    int lastval;
    int maxval;

    jack_recompute_total_latencies(ctxt->jack.client);
    maxval = 0;
    for (portno = 0; portno < mfp_input_ports->len; portno++) {
        jack_port_get_latency_range(g_array_index(mfp_input_ports, jack_port_t *, portno),
                JackCaptureLatency, & range); 
        if (range.max > maxval) {
            maxval = range.max;
        }

        lastval = jack_port_get_total_latency(ctxt->jack.client, 
                    g_array_index(mfp_input_ports, jack_port_t *, portno));
        if (lastval > maxval) {
            maxval = lastval;
        }

    }
    mfp_in_latency = 1000.0 * maxval / ctxt->jack.samplerate;

    maxval = 0;
    for (portno = 0; portno < mfp_output_ports->len; portno++) {
        jack_port_get_latency_range(g_array_index(mfp_output_ports, jack_port_t *,  portno),
                                    JackPlaybackLatency, & range); 
        if (range.max > maxval) {
            maxval = range.max;
        }
        lastval = jack_port_get_total_latency(ctxt->jack.client, 
                                              g_array_index(mfp_output_ports, 
                                                            jack_port_t *, portno));
        if (lastval > maxval) {
            maxval = lastval;
        }
    }

    mfp_out_latency = 1000.0 * maxval / ctxt->jack.samplerate;

    mfp_dsp_send_response_float(NULL, 1, 0.0);
}

mfp_context * 
mfp_jack_startup(char * client_name, int num_inputs, int num_outputs) 
{
    mfp_context * ctxt;
    jack_status_t status;
    jack_port_t * port;
    int i;

    char namebuf[16];

    ctxt = g_malloc(sizeof(mfp_context));
    ctxt->ctype = CTYPE_JACK;

    if ((ctxt->jack.client = jack_client_open(client_name, JackNullOption, &status, NULL)) == 0) {
        fprintf (stderr, "jack_client_open() failed.");
        return NULL;
    }
    
    /* callbacks */ 
    jack_set_process_callback(ctxt->jack.client, process_cb, ctxt);
    jack_set_graph_order_callback(ctxt->jack.client, reorder_cb, ctxt);

    /* no info logging to console */ 
    jack_set_info_function(info_cb);
    jack_set_error_function(info_cb);
    
    /* create application input and output ports */ 
    if (num_inputs > 0) {
        input_ports = g_array_new(TRUE, TRUE, sizeof(jack_port_t *));

        for(i=0; i<num_inputs; i++) {
            snprintf(namebuf, 16, "in_%d", i);
            port = jack_port_register (ctxt->jack.client, namebuf, JACK_DEFAULT_AUDIO_TYPE, 
                                       JackPortIsInput, i);
            g_array_append_val(mfp_input_ports, port);
        }
    }

    if (num_outputs > 0) {
        mfp_output_ports = g_array_new(TRUE, TRUE, sizeof(jack_port_t *));

        for(i=0; i<num_outputs; i++) {
            snprintf(namebuf, 16, "out_%d", i);
            port = jack_port_register (ctxt->jack.client, namebuf, JACK_DEFAULT_AUDIO_TYPE, 
                                       JackPortIsOutput, i);
            g_array_append_val(mfp_output_ports, port);
        }

    }
    
    /* find out sample rate */ 
    ctxt->jack.samplerate = jack_get_sample_rate(ctxt->jack.client);
    ctxt->jack.blocksize = jack_get_buffer_size(ctxt->jack.client);
    mfp_in_latency = 3000.0 * ctxt->jack.blocksize / ctxt->jack.samplerate; 
    mfp_out_latency = 3000.0 * ctxt->jack.blocksize / ctxt->jack.samplerate; 

    printf("jack_startup: samplerate=%d, blocksize=%d, in_latency=%.1f, out_latency = %.1f\n", 
            ctxt->jack.samplerate, ctxt->jack.blocksize, mfp_in_latency, mfp_out_latency); 

    /* tell the JACK server that we are ready to roll */
    if (jack_activate (ctxt->jack.client)) {
        fprintf (stderr, "cannot activate client");
        return NULL;
    }

    return ctxt;

}

void
mfp_jack_shutdown(mfp_context * ctxt) 
{
    printf("jack_shutdown: closing client, good-bye!\n");
    jack_deactivate(ctxt->jack.client);
    jack_client_close(ctxt->jack.client);
    ctxt->jack.client = NULL;
}


/* main() gets called only if this is a standalone JACK client 
 * startup.  The MFP process will cause this to be run */ 
int
main(int argc, char ** argv) 
{
    printf("mfp_jack:main() Starting up as standalone JACK client\n");
  
    /* set up global state */
    mfp_alloc_init();
    mfp_comm_init();

    /* enter main lister loop */ 
    printf("mfpdsp:main() Entering comm event loop, will not return to main()\n");
    mfp_comm_ioloop();

    printf("mfpdsp:main() Returned from comm event loop, will exit.\n"); 
    return 0;

}



