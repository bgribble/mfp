#include <glib.h>
#include <jack/jack.h>
#include <stdio.h>
#include <string.h>
#include <fcntl.h>
#include <sys/stat.h>
#include <semaphore.h>

#include "mfp_dsp.h"

GArray * mfp_input_ports;
GArray * mfp_output_ports;

int mfp_samplerate = 44100; 
int mfp_blocksize = 1024; 
float mfp_in_latency = 0.0;
float mfp_out_latency = 0.0;

static jack_client_t * client;

static int
process (jack_nframes_t nframes, void *arg)
{
    jack_position_t trans_info;
    jack_transport_state_t trans_state; 

    /* get transport info */ 
    trans_state = jack_transport_query(client, &trans_info);

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

mfp_sample * 
mfp_get_input_buffer(int chan) {
    if (mfp_input_ports == NULL) {
        return NULL;
    }

    if (chan < mfp_input_ports->len) {
        return jack_port_get_buffer(g_array_index(mfp_input_ports, jack_port_t *, chan),
                                    mfp_blocksize);
    }
    else {
        return NULL;
    }
}

mfp_sample * 
mfp_get_output_buffer(int chan) {
    if (mfp_output_ports == NULL) {
        return NULL;
    }

    if (chan < mfp_output_ports->len) {
        return jack_port_get_buffer(g_array_index(mfp_output_ports, jack_port_t *, chan),
                                    mfp_blocksize);
    }
    else {
        return NULL;
    }
}


static void
info_callback(const char * msg)
{
    return;
}

static void
reorder_cb (void * arg) 
{
    jack_latency_range_t range;
    int portno;
    int lastval;
    int maxval;

    jack_recompute_total_latencies(client);
    maxval = 0;
    for (portno = 0; portno < mfp_input_ports->len; portno++) {
        jack_port_get_latency_range(g_array_index(mfp_input_ports, jack_port_t *, portno),
                JackCaptureLatency, & range); 
        if (range.max > maxval) {
            maxval = range.max;
        }

        lastval = jack_port_get_total_latency(client, 
                    g_array_index(mfp_input_ports, jack_port_t *, portno));
        if (lastval > maxval) {
            maxval = lastval;
        }

    }
    mfp_in_latency = 1000.0 * maxval / mfp_samplerate;

    maxval = 0;
    for (portno = 0; portno < mfp_output_ports->len; portno++) {
        jack_port_get_latency_range(g_array_index(mfp_output_ports, jack_port_t *,  portno),
                JackPlaybackLatency, & range); 
        if (range.max > maxval) {
            maxval = range.max;
        }
        lastval = jack_port_get_total_latency(client, 
                    g_array_index(mfp_output_ports, jack_port_t *, portno));
        if (lastval > maxval) {
            maxval = lastval;
        }
    }

    mfp_out_latency = 1000.0 * maxval / mfp_samplerate;

    mfp_dsp_send_response_float(NULL, 1, 0.0);
}

int
mfp_jack_startup(char * client_name, int num_inputs, int num_outputs) 
{
    jack_status_t status;
    jack_port_t * port;
    int i;

    char namebuf[16];

    mfp_alloc_init();

    if ((client = jack_client_open(client_name, JackNullOption, &status, NULL)) == 0) {
        fprintf (stderr, "jack_client_open() failed.");
        return 0;
    }
    
    /* callbacks */ 
    jack_set_process_callback(client, process, 0);
    jack_set_graph_order_callback(client, reorder_cb, NULL);

    /* no info logging to console */ 
    jack_set_info_function(info_callback);
    jack_set_error_function(info_callback);
    
    /* create application input and output ports */ 
    if (num_inputs > 0) {
        mfp_input_ports = g_array_new(TRUE, TRUE, sizeof(jack_port_t *));

        for(i=0; i<num_inputs; i++) {
            snprintf(namebuf, 16, "in_%d", i);
            port = jack_port_register (client, namebuf, JACK_DEFAULT_AUDIO_TYPE, 
                                       JackPortIsInput, i);
            g_array_append_val(mfp_input_ports, port);
        }
    }

    if (num_outputs > 0) {
        mfp_output_ports = g_array_new(TRUE, TRUE, sizeof(jack_port_t *));

        for(i=0; i<num_outputs; i++) {
            snprintf(namebuf, 16, "out_%d", i);
            port = jack_port_register (client, namebuf, JACK_DEFAULT_AUDIO_TYPE, 
                                       JackPortIsOutput, i);
            g_array_append_val(mfp_output_ports, port);
        }

    }
    
    /* find out sample rate */ 
    mfp_samplerate = jack_get_sample_rate(client);
    mfp_blocksize = jack_get_buffer_size(client);
    mfp_in_latency = 3000.0 * mfp_blocksize / mfp_samplerate; 
    mfp_out_latency = 3000.0 * mfp_blocksize / mfp_samplerate; 

    printf("jack_startup: samplerate=%d, blocksize=%d, in_latency=%.1f, out_latency = %.1f\n", 
            mfp_samplerate, mfp_blocksize, mfp_in_latency, mfp_out_latency); 

    /* tell the JACK server that we are ready to roll */
    if (jack_activate (client)) {
        fprintf (stderr, "cannot activate client");
        return 0;
    }

    return 1;

}

void
mfp_jack_shutdown(void) 
{
    printf("jack_shutdown: closing client, good-bye!\n");
    jack_deactivate(client);
    jack_client_close(client);
    client = NULL;
}


