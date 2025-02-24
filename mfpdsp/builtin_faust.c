
#include <math.h>
#include <stdio.h>
#include <string.h>
#include <glib.h>
#include <pthread.h>

#include "faust/dsp/libfaust-c.h"
#include "faust/dsp/llvm-dsp-c.h"

#include "mfp_dsp.h"

typedef struct {
    char * faust_code;
    llvm_dsp_factory * faust_factory;
    llvm_dsp * faust_dsp;
    FAUSTFLOAT ** faust_inbufs;
    FAUSTFLOAT ** faust_outbufs;
    FAUSTFLOAT * faust_buffers;
    gpointer faust_params;
    int sig_inputs;
    int sig_outputs;

    pthread_t compile_thread;
    int compile_thread_finished;
    llvm_dsp_factory * next_faust_factory;
    llvm_dsp * next_faust_dsp;
    FAUSTFLOAT ** next_faust_inbufs;
    FAUSTFLOAT ** next_faust_outbufs;
    FAUSTFLOAT * next_faust_buffers;

} builtin_faust_data;

typedef struct {
    char * prm_label;
    FAUSTFLOAT * prm_zoneptr;
    FAUSTFLOAT prm_value;
    FAUSTFLOAT prm_min;
    FAUSTFLOAT prm_max;
} faust_prm_data;

#define RESP_PARAM 0
#define RESP_DSP_INLETS 1
#define RESP_DSP_OUTLETS 2


static void
faust_cleanup_dsp(mfp_processor * proc) {
    builtin_faust_data * d = (builtin_faust_data *)(proc->data);
    if (d->faust_dsp) {
        deleteCDSPInstance(d->faust_dsp);
        d->faust_dsp = NULL;
    }

    if (d->faust_factory) {
        deleteCDSPFactory(d->faust_factory);
        d->faust_factory = NULL;
    }

    if (d->faust_buffers) {
        g_free(d->faust_buffers);
        d->faust_buffers = NULL;
    }
}


static int
process(mfp_processor * proc)
{
    builtin_faust_data * d = (builtin_faust_data *)(proc->data);
    int blocksize = proc->context->blocksize;

    /* to make sure compile output is synced with the execution loop, */
    /* update the processor state here */
    if (d->compile_thread && d->compile_thread_finished) {
        faust_cleanup_dsp(proc);
        pthread_join(d->compile_thread, NULL);
        d->compile_thread = (pthread_t)0;
        d->compile_thread_finished = 0;

        d->faust_dsp = d->next_faust_dsp;
        d->faust_factory = d->next_faust_factory;
        d->faust_inbufs = d->next_faust_inbufs;
        d->faust_outbufs = d->next_faust_outbufs;
        d->faust_buffers = d->next_faust_buffers;
        if (d->faust_dsp) {
            d->sig_inputs = getNumInputsCDSPInstance(d->faust_dsp);
            d->sig_outputs = getNumOutputsCDSPInstance(d->faust_dsp);
        }
        else {
            d->sig_inputs = 0;
            d->sig_outputs = 0;
        }

        /* reconfigure buffers in the processor object */
        mfp_proc_free_buffers(proc);
        mfp_proc_alloc_buffers(proc, d->sig_inputs, d->sig_outputs, proc->context->blocksize);
    }

    if ((proc == NULL) || (d->faust_dsp == NULL)){
        return 0;
    }

    /* copy inputs to Faust buffer */
    for(int sig=0; sig < d->sig_inputs; sig++) {
        FAUSTFLOAT * faustin = d->faust_inbufs[sig];
        if (mfp_proc_has_input(proc, sig)) {
            mfp_sample * inbuf = proc->inlet_buf[sig]->data;
            for(int scount=0; scount < blocksize; scount++) {
                *faustin++ = (FAUSTFLOAT)(*inbuf++);
            }
        }
        else {
            for(int scount=0; scount < blocksize; scount++) {
                *faustin++ = (FAUSTFLOAT)(0.0);
            }
        }
    }

    /* run the faust process */
    computeCDSPInstance(
        d->faust_dsp,
        blocksize,
        d->faust_inbufs,
        d->faust_outbufs
    );

    /* copy outputs to mfp buffers */
    for(int sig=0; sig < d->sig_outputs; sig++) {
        FAUSTFLOAT * faustout = d->faust_outbufs[sig];
        mfp_sample * outbuf = proc->outlet_buf[sig]->data;
        for(int scount=0; scount < blocksize; scount++) {
            *outbuf++ = (mfp_sample)(*faustout++);
        }
    }

    return 1;
}

static void
init(mfp_processor * proc)
{
    builtin_faust_data * d = g_malloc0(sizeof(builtin_faust_data));
    d->faust_code = NULL;
    d->faust_params = g_hash_table_new_full(g_str_hash, g_str_equal, NULL, NULL);
    proc->data = (void *)d;
    return;
}

static void
destroy(mfp_processor * proc)
{
    builtin_faust_data * d = (builtin_faust_data *)(proc->data);

    if (d->faust_dsp) {
        deleteCDSPInstance(d->faust_dsp);
        d->faust_dsp = NULL;
    }

    if (d->faust_factory) {
        deleteCDSPFactory(d->faust_factory);
        d->faust_factory = NULL;
    }

    if (d->faust_code) {
        g_free(d->faust_code);
        d->faust_code = NULL;
    }

    if (d->faust_buffers) {
        g_free(d->faust_buffers);
        d->faust_buffers = NULL;
    }
    if (d->faust_params) {
        g_hash_table_destroy(d->faust_params);
        d->faust_params = NULL;
    }

    return;
}

static void
faust_prm_ignore_box(void * interface, const char * label) {
    return;
}

static void
faust_prm_ignore_close(void * interface) {
    return;
}

static void
faust_prm_ignore_number(
    void * interface, const char * label,
    FAUSTFLOAT * zone, FAUSTFLOAT min, FAUSTFLOAT max
) {
    return;
}

static void
faust_prm_ignore_declare(
    void * interface, FAUSTFLOAT * zone,  const char * key, const char * value
) {
    return;
}

static void
faust_prm_number(
    void * proc, const char * label,
    FAUSTFLOAT * zone, FAUSTFLOAT init, FAUSTFLOAT min, FAUSTFLOAT max, FAUSTFLOAT step
) {
    builtin_faust_data * d = (builtin_faust_data *)(((mfp_processor *)proc)->data);
    faust_prm_data * prm = g_malloc0(sizeof(faust_prm_data));
    prm->prm_label = g_strdup(label);
    prm->prm_zoneptr = zone;
    prm->prm_value = init;
    prm->prm_min = min;
    prm->prm_max = max;
    g_hash_table_insert(d->faust_params, prm->prm_label, prm);
    g_hash_table_insert(((mfp_processor *)proc)->typeinfo->params, g_strdup(label), (gpointer)PARAMTYPE_FLT);
    mfp_dsp_send_response_str(proc, RESP_PARAM, g_strdup(label));
}

static void
faust_prm_bool(
    void * proc, const char * label, FAUSTFLOAT * zone
) {
    builtin_faust_data * d = (builtin_faust_data *)(((mfp_processor *)proc)->data);
    faust_prm_data * prm = g_malloc0(sizeof(faust_prm_data));
    prm->prm_label = g_strdup(label);
    prm->prm_zoneptr = zone;
    prm->prm_value = 0;
    prm->prm_min = 0;
    prm->prm_max = 1;
    g_hash_table_insert(d->faust_params, prm->prm_label, prm);
    g_hash_table_insert(((mfp_processor *)proc)->typeinfo->params, g_strdup(label), (gpointer)PARAMTYPE_FLT);
    mfp_dsp_send_response_str(proc, RESP_PARAM, g_strdup(label));
}


static void
faust_config_params(mfp_processor * proc, llvm_dsp * dsp) {
    builtin_faust_data * d = (builtin_faust_data *)(proc->data);

    UIGlue ui_controls;
    ui_controls.uiInterface = (void *)proc;
    ui_controls.openHorizontalBox = faust_prm_ignore_box;
    ui_controls.openVerticalBox = faust_prm_ignore_box;
    ui_controls.openTabBox = faust_prm_ignore_box;
    ui_controls.closeBox = faust_prm_ignore_close;
    ui_controls.addButton = faust_prm_bool;
    ui_controls.addCheckButton = faust_prm_bool;
    ui_controls.addVerticalSlider = faust_prm_number;
    ui_controls.addHorizontalSlider = faust_prm_number;
    ui_controls.addNumEntry = faust_prm_number;
    ui_controls.addVerticalBargraph = faust_prm_ignore_number;
    ui_controls.addHorizontalBargraph = faust_prm_ignore_number;
    ui_controls.declare = faust_prm_ignore_declare;

    buildUserInterfaceCDSPInstance(dsp, &ui_controls);
}


static int
faust_config(mfp_processor * proc) {
    builtin_faust_data * d = (builtin_faust_data *)(proc->data);
    char error_msg[4096];

    llvm_dsp_factory * faust_factory;
    llvm_dsp * faust_dsp;
    FAUSTFLOAT ** faust_inbufs;
    FAUSTFLOAT ** faust_outbufs;
    FAUSTFLOAT * faust_buffers;

    if (d->faust_code && strlen(d->faust_code) >= 2) {
        faust_factory = createCDSPFactoryFromString(
            "mfp_faust", d->faust_code, 0, NULL, "", error_msg, -1
        );

        if (!faust_factory) {
            mfp_log_debug("[faust~] Cannot create JIT factory : %s\n", error_msg);
            return -1;
        }
        else {
            faust_dsp = createCDSPInstance(faust_factory);
            if (!faust_dsp) {
                mfp_log_debug("[faust~] Cannot create DSP engine\n");
            } else {
                int sig_inputs = getNumInputsCDSPInstance(faust_dsp);
                int sig_outputs = getNumOutputsCDSPInstance(faust_dsp);
                faust_buffers = g_malloc0(
                    (sig_inputs + sig_outputs)*sizeof(FAUSTFLOAT)*proc->context->blocksize
                );
                faust_inbufs = g_malloc0((sig_inputs + 1) * sizeof(FAUSTFLOAT *));
                faust_outbufs = g_malloc0((sig_outputs + 1) * sizeof(FAUSTFLOAT *));

                for (int in = 0; in < sig_inputs; in++) {
                    faust_inbufs[in] = faust_buffers + in * proc->context->blocksize;
                }
                FAUSTFLOAT * out_start = faust_buffers + sig_inputs * proc->context->blocksize;
                for (int out = 0; out < sig_outputs; out++) {
                    faust_outbufs[out] = out_start + out * proc->context->blocksize;
                }

                /* init the DSP instance */
                initCDSPInstance(faust_dsp, proc->context->samplerate);

                /* extract parameters */
                faust_config_params(proc, faust_dsp);

                mfp_dsp_send_response_int(proc, RESP_DSP_INLETS, sig_inputs);
                mfp_dsp_send_response_int(proc, RESP_DSP_OUTLETS, sig_outputs);
            }
        }
        d->next_faust_factory = faust_factory;
        d->next_faust_dsp = faust_dsp;
        d->next_faust_inbufs = faust_inbufs;
        d->next_faust_outbufs = faust_outbufs;
        d->next_faust_buffers = faust_buffers;
    }
    return 0;
}


static void *
faust_recompile_thread(void * data) {
    mfp_processor * proc = (mfp_processor *)data;
    builtin_faust_data * d = (builtin_faust_data *)(proc->data);
    faust_config(proc);
    d->compile_thread_finished = 1;
    pthread_exit(NULL);
    return NULL;
}


static void
start_recompile_thread(mfp_processor * proc) {
    builtin_faust_data * d = (builtin_faust_data *)(proc->data);
    d->compile_thread_finished = 0;
    int create_error = pthread_create(
        &(d->compile_thread),
        NULL,
        faust_recompile_thread,
        (void *)proc
    );
    if (create_error != 0) {
        d->compile_thread = (pthread_t)0;
        mfp_log_error("[faust~] Could not create Faust compile thread\n");
    }
}


static void
config_faust_param(gpointer key, gpointer value, gpointer user_data) {
    mfp_processor * proc = (mfp_processor *)user_data;
    builtin_faust_data * d = (builtin_faust_data *)(proc->data);

    faust_prm_data * prm = (faust_prm_data *)value;
    gpointer conf_value = g_hash_table_lookup(proc->params, key);

    if (prm != NULL && conf_value != NULL) {
        *(prm->prm_zoneptr) = (FAUSTFLOAT)(*(double *)conf_value);
    }
}


static int
config(mfp_processor * proc)
{
    builtin_faust_data * d = (builtin_faust_data *)(proc->data);
    gpointer code = g_hash_table_lookup(proc->params, "faust_code");

    if (
        (!d->faust_code && code)
        || (d->faust_code && !code)
        || (d->faust_code && code && strcmp(d->faust_code, code))
    ) {
        if (d->faust_code) {
            g_free(d->faust_code);
            d->faust_code = NULL;
        }
        if (code) {
            d->faust_code = g_strdup((char *)code);
        }
        start_recompile_thread(proc);

    }
    else {
        g_hash_table_foreach(
            d->faust_params,
            config_faust_param,
            (gpointer)proc
        );
    }

    return 1;
}


mfp_procinfo *
init_builtin_faust(void) {
    mfp_procinfo * p = g_malloc0(sizeof(mfp_procinfo));
    p->name = strdup("faust~");
    p->is_generator = GENERATOR_CONDITIONAL;
    p->process = process;
    p->init = init;
    p->destroy = destroy;
    p->config = config;
    p->params = g_hash_table_new_full(g_str_hash, g_str_equal, NULL, NULL);
    g_hash_table_insert(p->params, "faust_code", (gpointer)PARAMTYPE_STRING);
    return p;
}
