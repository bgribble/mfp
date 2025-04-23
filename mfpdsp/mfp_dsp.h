
#ifndef MFP_DSP_H
#define MFP_DSP_H

/* #define _POSIX_C_SOURCE 199309L */
#include <glib.h>
#include <jack/jack.h>
#include <pthread.h>
#include <json-glib/json-glib.h>
#ifndef M_PI
#    define M_PI 3.14159265358979323846
#endif

#include "lv2/atom/atom.h"
#include "lv2/atom/util.h"
#include "lv2/midi/midi.h"
#include "lv2/urid/urid.h"
#include "lv2/log/log.h"
#include "lv2/log/logger.h"
#include "lv2/core/lv2.h"

typedef jack_default_audio_sample_t mfp_sample;

#include "pytypes.pb-c.h"
#include "mfp_block.h"

struct mfp_procinfo_struct;
struct mfp_context_struct;

typedef struct {
    /* type, settable parameters, and internal state */
    int rpc_id;
    int patch_id;

    struct mfp_context_struct * context;
    struct mfp_procinfo_struct * typeinfo;
    GHashTable * params;
    void * data;
    int needs_config;
    int needs_reset;

    /* inlet and outlet connections (g_array of g_array) */
    GArray * inlet_conn;
    GArray * outlet_conn;

    /* input/output buffers */
    mfp_block ** inlet_buf;
    mfp_block ** inlet_buf_alloc;
    mfp_block ** outlet_buf;

    /* scheduling information */
    int depth;

} mfp_processor;

typedef struct {
    int reqtype;
    int src_proc;
    int src_port;
    int dest_proc;
    int dest_port;
    int context_id;
    gpointer param_name;
    int param_type;
    gpointer param_value;
} mfp_in_data;

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
    char * msgbuf;
    int msglen;
} mfp_out_data;

typedef struct {
    char * filename;
    void * dlinfo;
    int  state;
} mfp_extinfo;

typedef struct {
    /* parsed from the TTL file */
    char * object_name;
    char * object_path;
    int port_count;

    GArray * port_symbol;
    GArray * port_name;

    int port_input_mask;
    int port_output_mask;
    int port_audio_mask;
    int port_control_mask;
    int port_midi_mask;

    /* LV2 "feature" stuff, please don't ask me to explain */
    LV2_URID_Map*  map;
    LV2_Log_Logger logger;

    struct {
        LV2_URID midi_MidiEvent;
        LV2_URID time_Position;
        LV2_URID atom_Sequence;
    } uris;

    /* port_data is the LV2 data for each port */
    GArray * port_data;
    GArray * port_control_values;

    /* input_ports and output_ports are vectors of the LV2 port
     * numbers for input and output... i.e. port data for the first
     * output port is at port_data[output_ports[0]] */
    GArray * input_ports;
    GArray * output_ports;
    GArray * output_buffers;
    int output_capacity;

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
    int owner;
    int samplerate;
    int blocksize;
    int proc_count;
    int activated;
    int needs_reschedule;
    int default_obj_id;

    void (* msg_handler)(struct mfp_context_struct *, int port_id, int64_t message);

    union {
        mfp_jack_info * jack;
        mfp_lv2_info * lv2;
    } info;
} mfp_context;

typedef Carp__PythonArray mfp_rpc_args;

#define MFP_RPC_ARGBLOCK_SIZE 32

typedef struct mfp_rpc_argblock_struct {
    Carp__PythonValue arg_array_value;
    Carp__PythonArray arg_array;
    Carp__PythonValue * arg_value_pointers[MFP_RPC_ARGBLOCK_SIZE];
    Carp__PythonValue arg_values[MFP_RPC_ARGBLOCK_SIZE];
} mfp_rpc_argblock;

#define MFP_RPC_ARGS__INIT CARP__PYTHON_ARRAY__INIT

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
#define REQTYPE_GETPARAM 7
#define REQTYPE_RESET 8
#define REQTYPE_CONTEXT_MSG 9

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

#define MFP_DEFAULT_SOCKET "/tmp/mfp_rpcsock"
#define MFP_EXEC_NAME "mfp"
#define MFP_EXEC_SHELLMAX 2048
#define MFP_MAX_MSGSIZE 8192
#define MFP_NUM_BUFFERS 8192

#define MAX_PEER_ID_LEN 128

/* Logging helpers */
#define mfp_log_info(...) _mfp_log("INFO", __FILE__, __LINE__, __VA_ARGS__)
#define mfp_log_debug(...) _mfp_log("DEBUG", __FILE__, __LINE__, __VA_ARGS__)
#define mfp_log_warning(...) _mfp_log("WARNING", __FILE__, __LINE__, __VA_ARGS__)
#define mfp_log_error(...) _mfp_log("ERROR", __FILE__, __LINE__, __VA_ARGS__)


/* library global variables */
extern int mfp_initialized;
extern int mfp_max_blocksize;
extern float mfp_in_latency;
extern float mfp_out_latency;
extern int mfp_log_quiet;

extern GHashTable * mfp_proc_registry;
extern GHashTable * mfp_proc_objects;
extern GHashTable * mfp_contexts;
extern GHashTable * mfp_extensions;

extern GArray * mfp_proc_list;
extern GArray * incoming_cleanup;

extern pthread_mutex_t incoming_lock;
extern pthread_mutex_t outgoing_lock;
extern pthread_cond_t outgoing_cond;
extern int outgoing_queue_read;
extern int outgoing_queue_write;
extern mfp_out_data outgoing_queue[REQ_BUFSIZE];

extern char rpc_node_id[MAX_PEER_ID_LEN];

/* main.c */
extern void mfp_init_all(char * sockname);
extern void mfp_finish_all(void);

/* mfp_jack.c */
extern mfp_context * mfp_jack_startup(char * client_name, int num_inputs, int num_outputs);
extern void mfp_jack_shutdown(void);
extern mfp_sample * mfp_get_input_buffer(mfp_context *, int);
extern mfp_sample * mfp_get_output_buffer(mfp_context *, int);
extern int mfp_num_output_buffers(mfp_context * ctxt);
extern int mfp_num_input_buffers(mfp_context * ctxt);


/* mfp_dsp.c */
extern void mfp_dsp_init(void);
extern int mfp_dsp_schedule(mfp_context * ctxt);
extern void mfp_dsp_run(mfp_context * ctxt);
extern void mfp_dsp_set_blocksize(mfp_context * ctxt, int nsamples);
extern void mfp_dsp_accum(mfp_sample *, mfp_sample *, int count);
extern void mfp_dsp_push_request(mfp_in_data rd);
extern void mfp_dsp_send_response_str(mfp_processor * proc, int msg_type, char * response);
extern void mfp_dsp_send_response_bool(mfp_processor * proc, int msg_type, int response);
extern void mfp_dsp_send_response_int(mfp_processor * proc, int msg_type, int response);
extern void mfp_dsp_send_response_float(mfp_processor * proc, int msg_type, double response);

extern int mfp_num_input_buffers(mfp_context * ctxt);
extern int mfp_num_output_buffers(mfp_context * ctxt);

/* mfp_proc.c */
extern mfp_processor * mfp_proc_lookup(int proc_id);
extern int mfp_proc_param_type(mfp_processor * p, char * pname);
extern int mfp_proc_ready_to_schedule(mfp_processor * p);
extern mfp_processor * mfp_proc_create(mfp_procinfo *, int, int, mfp_context *);
extern mfp_processor * mfp_proc_alloc(mfp_procinfo *, int, int, mfp_context *);
extern int mfp_proc_alloc_buffers(mfp_processor *, int, int, int);
extern void mfp_proc_free_buffers(mfp_processor *);
extern mfp_processor * mfp_proc_init(mfp_processor *, int rpc_id, int patch_id);
extern int mfp_proc_error(mfp_processor * self, const char * message);
extern void mfp_proc_process(mfp_processor *);
extern void mfp_proc_reset(mfp_processor *);
extern void mfp_proc_destroy(mfp_processor *);
extern int mfp_proc_connect(mfp_processor *, int, mfp_processor *, int);
extern int mfp_proc_disconnect(mfp_processor *, int, mfp_processor *, int);
extern int mfp_proc_setparam(mfp_processor * self, char * param_name, void * param_val);

extern int mfp_proc_has_input(mfp_processor * self, int inlet_num);
extern int mfp_proc_setparam_req(mfp_processor * self, mfp_in_data * rd) ;

/* mfp_alloc.c */
extern void mfp_alloc_init(void);
extern void mfp_alloc_finish(void);
extern int mfp_alloc_allocate(mfp_processor *, void * data, int * status);

/* mfp_ext.c */
extern mfp_extinfo * mfp_ext_load(char *);
extern void mfp_ext_init(mfp_extinfo *);

/* mfp_lv2_ttl.c */
extern int mfp_lv2_ttl_read(mfp_lv2_info * self, const char * bundle_path);
extern void * mfp_lv2_get_port_data(mfp_lv2_info * self, int portnum);

/* mfp_comm.c */
extern void mfp_comm_io_start(void);
extern void mfp_comm_io_finish(void);
extern void mfp_comm_io_wait(void);
extern int mfp_comm_init(char * init_sockid);
extern int mfp_comm_connect(char * sockname);
extern int mfp_comm_quit_requested(void);
extern char * mfp_comm_get_buffer(void);
extern int mfp_comm_submit_buffer(char * msgbuf, int msglen);
extern void mfp_comm_release_buffer(char * msgbuf);
extern int mfp_comm_send_buffer(char * msg, int msglen);

/* mfp_request.c */
extern void mfp_rpc_init(void);

/* incoming data processing */
extern void mfp_dsp_push_request(mfp_in_data rd);
extern void mfp_dsp_handle_requests(void);

/* outgoing data processing */
extern int mfp_rpc_request(
    const char * service_name,
    int instance_id,
    const mfp_rpc_args * params,
    void (* callback)(Carp__PythonValue *, void *),
    void * callback_data,
    char * msgbuf,
    int * msglen
);
extern int mfp_rpc_response(
    int request_id,
    const char * service_name,
    Carp__PythonValue * result,
    char * msgbuf,
    int * msglen
);
extern void mfp_rpc_wait(int request_id);

/* mfp_rpc.c */
extern int mfp_rpc_dispatch_request(const char *, int);

extern mfp_rpc_args * mfp_rpc_args_init(mfp_rpc_argblock * block);
extern void mfp_rpc_args_append_bool(mfp_rpc_args *, int);
extern void mfp_rpc_args_append_string(mfp_rpc_args *, const char *);
extern void mfp_rpc_args_append_int(mfp_rpc_args *, int64_t);
extern void mfp_rpc_args_append_double(mfp_rpc_args *, double);

/* mfp_context.c */
extern mfp_context * mfp_context_new(int ctype);
extern int mfp_context_init(mfp_context * context);
extern void mfp_context_destroy(mfp_context * context);
extern int mfp_context_default_io(mfp_context * context, int obj_id);

/* mfp_api.c */
extern void mfp_api_init(void);
extern int mfp_api_open_context(mfp_context * ctxt, char *, int *);
extern int mfp_api_load_context(mfp_context * ctxt, char * patchname, char *, int *);
extern int mfp_api_close_context(mfp_context * ctxt);
extern int mfp_api_send_to_inlet(mfp_context * ctxt, int port, float val, char *, int *);
extern int mfp_api_send_to_outlet(mfp_context * ctxt, int port, float val, char *, int *);
extern int mfp_api_send_midi_to_inlet(mfp_context * ctxt, int port, int64_t val, char *, int *);
extern int mfp_api_send_midi_to_outlet(mfp_context * ctxt, int port, int64_t val, char *, int *);
extern int mfp_api_show_editor(mfp_context * ctxt, int show, char *, int *);
extern int mfp_api_dsp_response(int proc_id, char * resp, int mtype, char * mbuf, int * mlen);
extern int mfp_api_exit_notify(void);

extern void _mfp_log(const char * , const char *, int, ...);
#endif

