#include <jack/jack.h>
#include <stdio.h>
#include <string.h>

jack_port_t * input_port;
jack_port_t * output_port;

static int
process (jack_nframes_t nframes, void *arg)
{
	/* pass through all audio */
	jack_default_audio_sample_t *out = (jack_default_audio_sample_t *) jack_port_get_buffer (output_port, nframes);
	jack_default_audio_sample_t *in = (jack_default_audio_sample_t *) jack_port_get_buffer (input_port, nframes);

	memcpy (out, in, sizeof (jack_default_audio_sample_t) * nframes);
	return 0;     
}


int
mfp_jack_startup(void) 
{
	printf("mfp_jack_start called.\n");

	jack_client_t * client;
	jack_status_t status;
	const char ** ports;

	if ((client = jack_client_open("mfp_dsp", JackNullOption, &status, NULL)) == 0) {
		fprintf (stderr, "jack_client_open() failed.");
		return 0;
	}
	
	jack_set_process_callback(client, process, 0);

	input_port = jack_port_register (client, "input", JACK_DEFAULT_AUDIO_TYPE, 
									 JackPortIsInput, 0);
	output_port = jack_port_register (client, "output", JACK_DEFAULT_AUDIO_TYPE, 
									  JackPortIsOutput, 0);

	/* tell the JACK server that we are ready to roll */
	if (jack_activate (client)) {
		fprintf (stderr, "cannot activate client");
		return 0;
	}

	ports = jack_get_ports (client, NULL, NULL, JackPortIsPhysical|JackPortIsOutput);
	if (ports == NULL) {
		fprintf(stderr, "no physical capture ports\n");
	}
	else if (jack_connect (client, ports[0], jack_port_name (input_port))) {
		fprintf (stderr, "cannot connect input ports\n");
	}
	free (ports);
 
	ports = jack_get_ports (client, NULL, NULL, JackPortIsPhysical|JackPortIsInput);
	if (ports == NULL) {
		fprintf(stderr, "no physical playback ports\n");
	}
	else if (jack_connect (client, ports[0], jack_port_name (output_port))) {
		fprintf (stderr, "cannot connect output ports\n");
	}
	free (ports);
 


	return 1;

}


