
#include <math.h>
#include <stdio.h>
#include <string.h>
#include <glib.h>

#include "faust/dsp/llvm-dsp-c.h"
#include "faust/dsp/libfaust-c.h"

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

static int
process(mfp_processor * proc)
{
    builtin_faust_data * d = (builtin_faust_data *)(proc->data);
    mfp_sample * inptr, * outptr;

    int blocksize = proc->context->blocksize;

    if ((proc == NULL) || (d->faust_dsp == NULL)){
        return 0;
    }

    mfp_sample * outbuf = proc->outlet_buf[0]->data;

    if ((outbuf == NULL) || (d->faust_outbufs == NULL)) {
        return 0;
    }

    /* run the faust process */
    computeCDSPInstance(
        d->faust_dsp,
        blocksize,
        d->faust_inbufs,
        d->faust_outbufs
    );

    /* copy output to mfp buffer */
    FAUSTFLOAT * faustout = d->faust_outbufs[0];
    for(int scount=0; scount < blocksize; scount++) {
        *outbuf++ = (mfp_sample)(*faustout++);
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
    g_hash_table_insert(((mfp_processor *)proc)->typeinfo->params, label, (gpointer)PARAMTYPE_FLT);
    mfp_dsp_send_response_str(proc, RESP_PARAM, g_strdup(label));
}


static void
faust_config_params(mfp_processor * proc) {
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

    buildUserInterfaceCDSPInstance(d->faust_dsp, &ui_controls);
}


static int
faust_config(mfp_processor * proc) {
    builtin_faust_data * d = (builtin_faust_data *)(proc->data);
    char error_msg[4096];
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

    if (!d->faust_code || strlen(d->faust_code) < 2) {
        return 0;
    }

    d->faust_factory = createCDSPFactoryFromString(
        "mfp_faust", d->faust_code, 0, NULL, "", error_msg, -1
    );

    if (!d->faust_factory) {
        mfp_log_debug("[faust~] Cannot create JIT factory : %s\n", error_msg);
    }
    else {
        d->faust_dsp = createCDSPInstance(d->faust_factory);
        if (!d->faust_dsp) {
            mfp_log_debug("[faust~] Cannot create DSP engine\n");
        } else {
            d->sig_inputs = getNumInputsCDSPInstance(d->faust_dsp);
            d->sig_outputs = getNumOutputsCDSPInstance(d->faust_dsp);

            /* reconfigure buffers in the processor object */
            mfp_proc_free_buffers(proc);
            mfp_proc_alloc_buffers(proc, d->sig_inputs, d->sig_outputs, proc->context->blocksize);
            d->faust_buffers = g_malloc0(
                (d->sig_inputs + d->sig_outputs)*sizeof(FAUSTFLOAT)*proc->context->blocksize
            );
            d->faust_inbufs = g_malloc0((d->sig_inputs + 1) * sizeof(FAUSTFLOAT *));
            d->faust_outbufs = g_malloc0((d->sig_outputs + 1) * sizeof(FAUSTFLOAT *));

            for (int in = 0; in < d->sig_inputs; in++) {
                d->faust_inbufs[in] = d->faust_buffers + in * proc->context->blocksize;
            }
            FAUSTFLOAT * out_start = d->faust_buffers + d->sig_inputs * proc->context->blocksize;
            for (int out = 0; out < d->sig_outputs; out++) {
                d->faust_outbufs[out] = out_start + out * proc->context->blocksize;
            }

            /* init the DSP instance */
            initCDSPInstance(d->faust_dsp, proc->context->samplerate);

            /* extract parameters */
            faust_config_params(proc);
        }
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
        faust_config(proc);
        mfp_dsp_send_response_int(proc, RESP_DSP_INLETS, d->sig_inputs);
        mfp_dsp_send_response_int(proc, RESP_DSP_OUTLETS, d->sig_outputs);
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
    p->is_generator = 0;
    p->process = process;
    p->init = init;
    p->destroy = destroy;
    p->config = config;
    p->params = g_hash_table_new_full(g_str_hash, g_str_equal, NULL, NULL);
    g_hash_table_insert(p->params, "faust_code", (gpointer)PARAMTYPE_STRING);
    return p;
}
