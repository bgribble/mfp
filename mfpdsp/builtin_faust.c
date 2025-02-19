
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
    int sig_inputs;
    int sig_outputs;
} builtin_faust_data;


char argv_buf[] = "---empty---";


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

    return;
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
        "mfp_faust", d->faust_code, 0, (const char **)argv_buf, "", error_msg, -1
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
        }
    }
}




static int
config(mfp_processor * proc)
{
    builtin_faust_data * d = (builtin_faust_data *)(proc->data);
    gpointer code = g_hash_table_lookup(proc->params, "faust_code");

    if (
        (!code && !d->faust_code)
        || (code && d->faust_code && !strcmp(code, d->faust_code))
    ) {
        return 1;
    }

    if (d->faust_code && (!code || strcmp(code, d->faust_code))) {
        g_free(d->faust_code);
        d->faust_code = NULL;
    }
    if (code) {
        d->faust_code = g_strdup((char *)code);
        return faust_config(proc);
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
