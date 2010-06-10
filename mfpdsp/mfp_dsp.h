
#include <glib.h>
#include <jack/jack.h>

typedef jack_default_audio_sample_t mfp_sample;

struct mfp_procinfo_struct;

typedef struct {
	/* type, settable parameters, and internal state */
	struct mfp_procinfo_struct * typeinfo;
	GHashTable * params; 
	GHashTable * params_nxt; 
	void * data;
	
	/* inlet and outlet connections (g_array of g_array) */
	GArray * inlet_conn;
	GArray * outlet_conn; 

	/* input/output buffers */ 
	mfp_sample ** inlet_buf;
	mfp_sample ** outlet_buf;

	/* scheduling information */ 
	int depth;

} mfp_processor;

typedef struct mfp_procinfo_struct {
	char * name;
	int  is_generator;
	void (* init)(mfp_processor *);
	void (* destroy)(mfp_processor *);
	int  (* process)(mfp_processor *);
} mfp_procinfo;

typedef struct {
	mfp_processor * dest_proc;
	int dest_port;
} mfp_connection;

/* global variables */ 
extern int mfp_dsp_enabled;
extern int mfp_needs_reschedule;
extern int mfp_samplerate;
extern int mfp_blocksize; 

extern GHashTable * mfp_proc_registry;
extern GArray * mfp_proc_list; 

/* mfp_jack.c */
extern GArray * mfp_input_ports;
extern GArray * mfp_output_ports;
extern int mfp_jack_startup(int num_inputs, int num_outputs);
extern void mfp_jack_shutdown(void);
extern mfp_sample * mfp_get_input_buffer(int);
extern mfp_sample * mfp_get_output_buffer(int);

/* mfp_dsp.c */
extern int mfp_dsp_schedule(void);
extern void mfp_dsp_run(int nsamples);
extern void mfp_dsp_set_blocksize(int nsamples);
extern void mfp_dsp_accum(mfp_sample *, mfp_sample *, int count);

/* mfp_proc.c */
extern int mfp_proc_ready_to_schedule(mfp_processor * p);
extern mfp_processor * mfp_proc_create(mfp_procinfo *, int, int, int);

extern void mfp_proc_process(mfp_processor *);
extern void mfp_proc_destroy(mfp_processor *);
extern int mfp_proc_connect(mfp_processor *, int, mfp_processor *, int);
extern int mfp_proc_disconnect(mfp_processor *, int, mfp_processor *, int);
extern int mfp_proc_setparam(mfp_processor * self, char * param_name, double param_val);
extern double mfp_proc_getparam(mfp_processor * self, char * param_name);

extern int test_ctests(void);
