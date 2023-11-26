#include "mfp_dsp.h"
#include "builtin.h"

#include <unistd.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <execinfo.h>
#include <glib.h>
#include <pthread.h>

#include <time.h>

int mfp_initialized = 0;
int mfp_max_blocksize = 32768;

float mfp_in_latency = 0.0;
float mfp_out_latency = 0.0;

#define ARRAY_LEN(arry, eltsize) (sizeof(arry) / eltsize)

void
mfp_dsp_init(void) {
    int i;
    mfp_procinfo * pi;
    mfp_procinfo * (* initfuncs[])(void) = {
        init_builtin_osc, init_builtin_in, init_builtin_out,
        init_builtin_sig, init_builtin_snap, init_builtin_ampl,
        init_builtin_add, init_builtin_sub, init_builtin_mul, init_builtin_div,
        init_builtin_lt, init_builtin_gt,
        init_builtin_line, init_builtin_noise, init_builtin_buffer,
        init_builtin_biquad, init_builtin_phasor,
        init_builtin_ladspa, init_builtin_delay, init_builtin_delblk, init_builtin_noop,
        init_builtin_inlet, init_builtin_outlet,
        init_builtin_errtest, init_builtin_slew, init_builtin_pulse,
        init_builtin_pulsesel, init_builtin_stepseq,
        init_builtin_vc_quantize12, init_builtin_vc_freq,
        init_builtin_hold
    };
    int num_initfuncs = ARRAY_LEN(initfuncs, sizeof(mfp_procinfo *(*)(void)));

    /* init global vars */
    mfp_proc_list = g_array_new(TRUE, TRUE, sizeof(mfp_processor *));
    mfp_proc_registry = g_hash_table_new(g_str_hash, g_str_equal);
    mfp_proc_objects = g_hash_table_new(g_direct_hash, g_direct_equal);
    mfp_contexts = g_hash_table_new(g_direct_hash, g_direct_equal);
    mfp_extensions = g_hash_table_new(g_str_hash, g_str_equal);

    incoming_cleanup = g_array_new(TRUE, TRUE, sizeof(mfp_in_data *));

    pthread_cond_init(&outgoing_cond, NULL);
    pthread_mutex_init(&outgoing_lock, NULL);
    pthread_mutex_init(&incoming_lock, NULL);

    mfp_log_info("mfpdsp: initializing %d builtin DSP processors\n", num_initfuncs);

    for(i = 0; i < num_initfuncs; i++) {
        pi = initfuncs[i]();
        g_hash_table_insert(mfp_proc_registry, pi->name, pi);
    }
}


mfp_sample *
mfp_get_input_buffer(mfp_context * ctxt, int chan) {
    if (chan >= mfp_num_input_buffers(ctxt)) {
        return NULL;
    }

    if (ctxt->ctype == CTYPE_JACK) {
        return jack_port_get_buffer(g_array_index(ctxt->info.jack->input_ports,
                                    jack_port_t *, chan), ctxt->blocksize);
    }
    else {
        int port = g_array_index(ctxt->info.lv2->input_ports, int, chan);
        mfp_sample * ptr = mfp_lv2_get_port_data(ctxt->info.lv2, port);
        return ptr;
    }
}

mfp_sample *
mfp_get_output_buffer(mfp_context * ctxt, int chan) {
    if (chan >= mfp_num_output_buffers(ctxt)) {
        return NULL;
    }

    if (ctxt->ctype == CTYPE_JACK) {
        return jack_port_get_buffer(
            g_array_index(ctxt->info.jack->output_ports, jack_port_t *, chan),
            ctxt->blocksize
        );
    }
    else {
        mfp_block * blk = g_array_index(ctxt->info.lv2->output_buffers, mfp_block *, chan);
        if (blk != NULL) {
            return blk->data;
        }
        else{
            return NULL;
        }
    }
}

int
mfp_num_output_buffers(mfp_context * ctxt) {
    GArray * ports = NULL;

    if (ctxt->ctype == CTYPE_JACK) {
        if (ctxt->info.jack != NULL) {
            ports = ctxt->info.jack->output_ports;
        }
    }
    else {
        ports = ctxt->info.lv2->output_ports;
    }

    if (ports != NULL) {
        return ports->len;
    }
    else {
        return 0;
    }
}

int
mfp_num_input_buffers(mfp_context * ctxt) {
    GArray * ports = NULL;

    if (ctxt->ctype == CTYPE_JACK) {
        if (ctxt->info.jack != NULL) {
            ports = ctxt->info.jack->input_ports;
        }
    }
    else {
        ports = ctxt->info.lv2->input_ports;
    }

    if (ports != NULL) {
        return ports->len;
    }
    else {
        return 0;
    }
}


static int
depth_cmp_func(const void * a, const void *b)
{
    if ((*(mfp_processor **) a)->depth < (*(mfp_processor **)b)->depth)
        return -1;
    else if ((*(mfp_processor **) a)->depth == (*(mfp_processor **)b)->depth)
        return 0;
    else
        return 1;
}


static int
ready_to_schedule(mfp_processor * p)
{
    int icount;
    int ready = 1;
    GArray * infan;
    mfp_connection ** ip;
    int maxdepth = -1;

    if (p == NULL) {
        return -1;
    }
    if (p->typeinfo == NULL) {
        return -1;
    }

    if (p->typeinfo->is_generator == GENERATOR_ALWAYS) {
        return 0;
    }

    /* conditional generator is a generator if nothing connected to dsp inlets */
    if (p->typeinfo->is_generator == GENERATOR_CONDITIONAL) {
        ready = 0;
        for (icount = 0; icount < p->inlet_conn->len; icount++) {
            infan = g_array_index(p->inlet_conn, GArray *, icount);
            if(infan && infan->len) {
                ready = 1;
                break;
            }
        }
        if (ready == 0)
            return 0;
    }

    for (icount = 0; icount < p->inlet_conn->len; icount++) {
        infan = g_array_index(p->inlet_conn, GArray *, icount);
        for(ip = (mfp_connection **)(infan->data); *ip != NULL; ip++) {
            if ((*ip)->dest_proc->depth < 0) {
                ready = 0;
                break;
            }
            else if ((*ip)->dest_proc->depth > maxdepth) {
                maxdepth = (*ip)->dest_proc->depth;
            }
        }
        if (ready == 0) {
            break;
        }
    }

    if (ready > 0) {
        return maxdepth + 1;
    }
    else {
        return -1;
    }
}

int
mfp_dsp_schedule(mfp_context * ctxt)
{
    int pass = 0;
    int lastpass_unsched = -1;
    int thispass_unsched = 0;
    int another_pass = 1;
    int proc_count = 0;
    int depth = -1;
    mfp_processor ** p;

    /* unschedule everything */
    for (p = (mfp_processor **)(mfp_proc_list->data); *p != NULL; p++) {
        if ((*p)->context == ctxt) {
            (*p)->depth = -1;
            proc_count ++;
        }
    }

    /* calculate scheduling order */
    while (another_pass == 1) {
        for (p = (mfp_processor **)(mfp_proc_list->data); *p != NULL; p++) {
            if ((*p)->context == ctxt) {
                if ((*p)->depth < 0) {
                    depth = ready_to_schedule(*p);
                    if (depth >= 0) {
                        (*p)->depth = depth;
                    }
                    else {
                        thispass_unsched++;
                    }
                }
            }
        }
        if ((thispass_unsched > 0) &&
            (lastpass_unsched < 0 || (thispass_unsched < lastpass_unsched))) {
            another_pass = 1;
        }
        else {
            another_pass = 0;
        }
        lastpass_unsched = thispass_unsched;
        thispass_unsched = 0;
        pass ++;
    }

    /* conclusion: either success, or a DSP loop */
    if (lastpass_unsched > 0) {
        /* DSP loop: some processors not scheduled */
        return 0;
    }
    else {
        /* sort processors in place by depth */
        g_array_sort(mfp_proc_list, depth_cmp_func);
        return 1;
    }
}


/*
 * mfp_dsp_run is the bridge between JACK/LV2 processing and the MFP DSP
 * network.  It is called once per JACK/LV2 block from the process()
 * callback.
 */

void
mfp_dsp_run(mfp_context * ctxt)
{
    mfp_processor ** p;
    mfp_sample * buf;
    int chan;
    int chancount = mfp_num_output_buffers(ctxt);

    /* handle any DSP config requests */
    /* FIXME only handle requests for this context */
    mfp_dsp_handle_requests();

    /* zero output buffers ... out~ will accumulate into them */
    for(chan=0; chan < chancount; chan++) {
        buf = mfp_get_output_buffer(ctxt, chan);
        if (buf != NULL) {
            memset(buf, 0, ctxt->blocksize * sizeof(mfp_sample));
        }
    }

    if (ctxt->needs_reschedule == 1) {
        if (!mfp_dsp_schedule(ctxt)) {
            mfp_log_error("Some processors could not be scheduled, check for cycles!");
        }
        ctxt->needs_reschedule = 0;
    }

    /* the proclist is already scheduled, so iterating in order is OK */
    for(p = (mfp_processor **)(mfp_proc_list->data); *p != NULL; p++) {
        if ((*p)->context == ctxt) {
            mfp_proc_process(*p);
        }
    }
    ctxt->proc_count ++;
}

void
mfp_dsp_set_blocksize(mfp_context * ctxt, int nsamples)
{
    mfp_processor ** p;
    int count;

    if (nsamples > mfp_max_blocksize) {
        mfp_log_warning("JACK requests blocksize larger than mfp_max_blocksize (%d)",
                     nsamples);
        nsamples = mfp_max_blocksize;
    }

    if (nsamples != ctxt->blocksize) {
        for(p = (mfp_processor **)(mfp_proc_list->data); *p != NULL; p++) {
            /* i/o buffers are pre-allocated to mfp_max_blocksize */
            for (count = 0; count < (*p)->inlet_conn->len; count ++) {
                mfp_block_resize((*p)->inlet_buf[count], nsamples);
            }

            for (count = 0; count < (*p)->outlet_conn->len; count ++) {
                mfp_block_resize((*p)->outlet_buf[count], nsamples);
            }

            (*p)->needs_config = 1;
        }

        ctxt->blocksize = nsamples;
        if (ctxt->ctype == CTYPE_JACK) {
            return;
        }
        else if (ctxt->ctype == CTYPE_LV2) {
            for (count = 0; count < ctxt->info.lv2->output_buffers->len; count ++) {
                mfp_block_resize(g_array_index(ctxt->info.lv2->output_buffers, mfp_block *,
                                               count),
                                 nsamples);
            }
        }
    }
}

void
mfp_dsp_accum(mfp_sample * accum, mfp_sample * addend, int blocksize)
{
    int i;
    if ((accum == NULL) || (addend == NULL)) {
        return;
    }

    for (i=0; i < blocksize; i++) {
        accum[i] += addend[i];
    }
}
