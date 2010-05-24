#include <glib.h>
#include <jack/jack.h>
#include <stdio.h>
#include <string.h>
#include "mfp_dsp.h"

GArray * mfp_input_ports;
GArray * mfp_output_ports;

int mfp_samplerate; 
int mfp_blocksize; 

static int
process (jack_nframes_t nframes, void *arg)
{
	/* run processing network */ 
	if (mfp_dsp_enabled) {
		mfp_dsp_run((int)nframes);
	}

	return 0;
}

mfp_sample * 
mfp_get_input_buffer(int chan) {
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
	if (chan < mfp_output_ports->len) {
		return jack_port_get_buffer(g_array_index(mfp_input_ports, jack_port_t *, chan),
				                    mfp_blocksize);
	}
	else {
		return NULL;
	}
}


int
mfp_jack_startup(int num_inputs, int num_outputs) 
{
	jack_client_t * client;
	jack_status_t status;
	jack_port_t * port;
	const char ** ports;
	int i;

	if ((client = jack_client_open("mfp_dsp", JackNullOption, &status, NULL)) == 0) {
		fprintf (stderr, "jack_client_open() failed.");
		return 0;
	}
	
	jack_set_process_callback(client, process, 0);

	/* create application input and output ports */ 
	if (num_inputs > 0) {
		mfp_input_ports = g_array_new(TRUE, TRUE, sizeof(jack_port_t *));

		for(i=0; i<num_inputs; i++) {
			port = jack_port_register (client, "input", JACK_DEFAULT_AUDIO_TYPE, 
									   JackPortIsInput, i);
			g_array_append_val(mfp_input_ports, port);
		}
	}

	if (num_outputs > 0) {
		mfp_output_ports = g_array_new(TRUE, TRUE, sizeof(jack_port_t *));

		for(i=0; i<num_outputs; i++) {
			port = jack_port_register (client, "output", JACK_DEFAULT_AUDIO_TYPE, 
							           JackPortIsOutput, i);
			g_array_append_val(mfp_output_ports, port);
		}

	}
	
	/* find out sample rate */ 
	mfp_samplerate = jack_get_sample_rate(client);

	/* tell the JACK server that we are ready to roll */
	if (jack_activate (client)) {
		fprintf (stderr, "cannot activate client");
		return 0;
	}

	return 1;

}


