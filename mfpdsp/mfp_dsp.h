
#ifndef MFP_DSP_H
#define MFP_DSP_H

/* #define _POSIX_C_SOURCE 199309L */
#include <glib.h>
#include <jack/jack.h>
#include <pthread.h>

#ifndef M_PI
#    define M_PI 3.14159265358979323846
#endif

typedef jack_default_audio_sample_t mfp_sample;

#include "mfp_block.h"

struct mfp_procinfo_struct;
struct mfp_context_struct;

typedef struct {
    /* type, settable parameters, and internal state */
    struct mfp_context_struct * context; 
    struct mfp_procinfo_struct * typeinfo;
    GHashTable * params; 
    GHashTable * pyparams; 
    void * data;
    int needs_config;
    int needs_reset;
    
    /* inlet and outlet connections (g_array of g_array) */
    GArray * inlet_conn;
    GArray * outlet_conn; 

    /* input/output buffers */ 
    mfp_block ** inlet_buf;
    mfp_block ** outlet_buf;

    /* scheduling information */ 
    int depth;

} mfp_processor;

typedef struct {
    int reqtype;
    mfp_processor * src_proc;
    int src_port;
    mfp_processor * dest_proc;
    int dest_port;
    gpointer param_name;
    gpointer param_value;
} mfp_reqdata;

typedef struct mfp_procinfo_struct {
    char * name;
    int  is_generator;
    GHashTable * params;
    void (* init)(mfp_processor *);
    void (* destroy)(mfp_processor *);
    int  (* process)(mfp_processor *);
    int  (* config)(mfp_processor *);
    void (* alloc)(mfp_processor *, void * allocdata);
    void (* reset)(mfp_processor *);
} mfp_procinfo;

typedef struct {
    mfp_processor * dest_proc;
    int dest_port;
} mfp_connection;


typedef struct {
    mfp_processor * dst_proc;
    int   msg_type;
    int   response_type;
    union {
        double f;
        int    i;
        char   * c;
    } response;
} mfp_respdata;

typedef struct {
    char * filename; 
    void * dlinfo;
    int  state;
} mfp_extinfo;

typedef struct {
    GArray * port_symbol;
    GArray * port_name;
    GArray * port_data;
    GArray * input_ports;
    GArray * output_ports; 
    char * object_name;
    int port_count;
    int port_input_mask; 
    int port_output_mask;
    int port_audio_mask;
    int port_control_mask; 
    int port_midi_mask; 
} mfp_lv2_info; 

typedef struct {
    jack_client_t * client;
    GArray * input_ports;
    GArray * output_ports; 
} mfp_jack_info; 

#define CTYPE_JACK 0
#define CTYPE_LV2 1

typedef struct mfp_context_struct { 
    int ctype; 
    int id;
    int samplerate;
    int blocksize; 
    int proc_count;
    union {
        mfp_jack_info * jack;
        mfp_lv2_info * lv2;
    } info;
} mfp_context;

#define PARAMTYPE_UNDEF 0
#define PARAMTYPE_FLT 1
#define PARAMTYPE_STRING 2
#define PARAMTYPE_FLTARRAY 3
#define PARAMTYPE_BOOL 4
#define PARAMTYPE_INT 5

#define REQTYPE_CREATE 1
#define REQTYPE_DESTROY 2
#define REQTYPE_CONNECT 3
#define REQTYPE_DISCONNECT 4
#define REQTYPE_SETPARAM 5 
#define REQTYPE_EXTLOAD 6 

#define ALLOC_IDLE 0
#define ALLOC_WORKING 1
#define ALLOC_READY 2

#define GENERATOR_NEVER 0
#define GENERATOR_ALWAYS 1
#define GENERATOR_CONDITIONAL 2

#define EXTINFO_NULL 0
#define EXTINFO_LOADED 1 
#define EXTINFO_READY 2 

#define REQ_BUFSIZE 2048
#define REQ_LASTIND (REQ_BUFSIZE-1)

/* global variables */ 
extern int mfp_dsp_enabled;
extern int mfp_dsp_usejack;
extern int mfp_needs_reschedule;
extern int mfp_max_blocksize; 
extern float mfp_in_latency;
extern float mfp_out_latency;

extern GHashTable * mfp_proc_registry;
extern GHashTable * mfp_proc_objects;
extern GHashTable * mfp_extensions; 

extern GArray * mfp_proc_list; 
extern GArray * mfp_request_cleanup;

extern pthread_mutex_t mfp_request_lock;
extern pthread_mutex_t mfp_response_lock;
extern pthread_cond_t mfp_response_cond;
extern int mfp_response_queue_read;
extern int mfp_response_queue_write;
extern mfp_respdata mfp_response_queue[REQ_BUFSIZE];

/* mfp_jack.c */
extern int mfp_jack_startup(char * client_name, int num_inputs, int num_outputs);
extern void mfp_jack_shutdown(void);
extern mfp_sample * mfp_get_input_buffer(mfp_context *, int);
extern mfp_sample * mfp_get_output_buffer(mfp_context *, int);

/* mfp_dsp.c */
extern int mfp_dsp_schedule(void);
extern void mfp_dsp_run(int nsamples);
extern void mfp_dsp_set_blocksize(int nsamples);
extern void mfp_dsp_accum(mfp_sample *, mfp_sample *, int count);
extern void mfp_dsp_push_request(mfp_reqdata rd); 
extern void mfp_dsp_send_response_str(mfp_processor * proc, int msg_type, char * response);
extern void mfp_dsp_send_response_bool(mfp_processor * proc, int msg_type, int response);
extern void mfp_dsp_send_response_int(mfp_processor * proc, int msg_type, int response);
extern void mfp_dsp_send_response_float(mfp_processor * proc, int msg_type, double response);

/* mfp_proc.c */
extern int mfp_proc_ready_to_schedule(mfp_processor * p);
extern mfp_processor * mfp_proc_create(mfp_procinfo *, int, int, int);
extern mfp_processor * mfp_proc_alloc(mfp_procinfo *, int, int, int);
extern int mfp_proc_alloc_buffers(mfp_processor *, int, int, int);
extern void mfp_proc_free_buffers(mfp_processor *);
extern mfp_processor * mfp_proc_init(mfp_processor *);
extern int mfp_proc_error(mfp_processor * self, const char * message);
extern void mfp_proc_process(mfp_processor *);
extern void mfp_proc_reset(mfp_processor *);
extern void mfp_proc_destroy(mfp_processor *);
extern int mfp_proc_connect(mfp_processor *, int, mfp_processor *, int);
extern int mfp_proc_disconnect(mfp_processor *, int, mfp_processor *, int);
extern int mfp_proc_setparam(mfp_processor * self, char * param_name, void * param_val);

extern int mfp_proc_has_input(mfp_processor * self, int inlet_num);
extern int mfp_proc_setparam_req(mfp_processor * self, mfp_reqdata * rd) ;

/* mfp_alloc.c */ 
extern void mfp_alloc_init(void);
extern void mfp_alloc_finish(void);
extern int mfp_alloc_allocate(mfp_processor *, void * data, int * status);

/* mfp_ext.c */
extern mfp_extinfo * mfp_ext_load(char *);
extern void mfp_ext_init(mfp_extinfo *);

/* mfp_lv2_ttl.c */ 
extern int mfp_lv2_ttl_read(mfp_lv2_info * self, char * bundle_path);  
#endif

