#include <unistd.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <glib.h>
#include <pthread.h>

#include "mfp_dsp.h"

#define REQ_BUFSIZE 2048
#define REQ_LASTIND (REQ_BUFSIZE-1)

GArray      * mfp_request_cleanup = NULL;
mfp_reqdata request_queue[REQ_BUFSIZE];
int         request_queue_write = 0;
int         request_queue_read = 0;

GArray          * mfp_responses_pending = NULL;
pthread_mutex_t mfp_request_lock = PTHREAD_MUTEX_INITIALIZER;
pthread_mutex_t mfp_response_lock = PTHREAD_MUTEX_INITIALIZER;
pthread_cond_t  mfp_response_cond = PTHREAD_COND_INITIALIZER;

int mfp_dsp_enabled = 0;
int mfp_needs_reschedule = 1;
int proc_count = 0; 

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
mfp_dsp_schedule(void) 
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
        (*p)->depth = -1;
        proc_count ++;
    }

    /* calculate scheduling order */ 
    while (another_pass == 1) {
        for (p = (mfp_processor **)(mfp_proc_list->data); *p != NULL; p++) {
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


void 
mfp_dsp_push_request(mfp_reqdata rd) 
{
    int count; 
    int cleanup = 0; 

    /* note: this mutex just keeps a single writer thread with access 
     * to the requests data, it doesn't block the JACK callback thread */ 
    pthread_mutex_lock(&mfp_request_lock);
    if (request_queue_read == request_queue_write) {
        //cleanup = 1;
        /* cleanup is causing double frees, need to debug */ 
        cleanup = 0; 
    }
    
    while((request_queue_read == 0 && request_queue_write == REQ_LASTIND)
        || (request_queue_write + 1 == request_queue_read)) {
        usleep(100);
    }

    request_queue[request_queue_write] = rd;
    if(request_queue_write == REQ_LASTIND) {
        request_queue_write = 0;
    }
    else {
        request_queue_write += 1;
    }

    if (cleanup == 1) {
        /* now that JACK has finished with the new data, we can clean up 
         * the old data at our leisure.  mfp_dsp_handle_requests will 
         * put any old values that need to be freed into cmd.param_value */ 
        for(count=0; count < mfp_request_cleanup->len; count++) {
            mfp_reqdata cmd = g_array_index(mfp_request_cleanup, mfp_reqdata, count);
            if (cmd.reqtype == REQTYPE_SETPARAM) {
                if (cmd.param_value != NULL) {
                    g_free(cmd.param_value);
                }
                if (cmd.param_name != NULL) {
                    g_free(cmd.param_name);
                }
            }
        }

        if (mfp_request_cleanup->len > 0) 
            g_array_remove_range(mfp_request_cleanup, 0, mfp_request_cleanup->len);
    }

    /* we will clean this one up at some time in the future */ 
    g_array_append_val(mfp_request_cleanup, rd);

    pthread_mutex_unlock(&mfp_request_lock);
}

void
mfp_dsp_handle_requests(void)
{
    int count;

    while(request_queue_read != request_queue_write) {
        mfp_reqdata cmd = request_queue[request_queue_read];
        int type = cmd.reqtype;

        switch (type) {
        case REQTYPE_CONNECT:
            mfp_proc_connect(cmd.src_proc, cmd.src_port, cmd.dest_proc, cmd.dest_port);
            break;

        case REQTYPE_DISCONNECT:
            mfp_proc_disconnect(cmd.src_proc, cmd.src_port, cmd.dest_proc, cmd.dest_port);
            break;

        case REQTYPE_DESTROY:
            mfp_proc_destroy(cmd.src_proc);
            break;

        case REQTYPE_SETPARAM:
            mfp_proc_setparam_req(cmd.src_proc, &cmd);
            cmd.src_proc->needs_config = 1;
            break;

        }
        request_queue_read = (request_queue_read+1) % REQ_BUFSIZE;
    }
}


/*
 * mfp_dsp_run is the bridge between JACK processing and the MFP DSP 
 * network.  It is called once per JACK block from the process() 
 * callback.
 */

void
mfp_dsp_run(int nsamples) 
{
    mfp_processor ** p;
    mfp_sample * buf;
    int chan;

    mfp_dsp_set_blocksize(nsamples);

    /* handle any DSP config requests */
    mfp_dsp_handle_requests();

    /* zero output buffers ... out~ will accumulate into them */ 
    if (mfp_output_ports != NULL) {
        for(chan=0; chan < mfp_output_ports->len ; chan++) {
            buf = mfp_get_output_buffer(chan);
            if (buf != NULL) { 
                memset(buf, 0, nsamples * sizeof(mfp_sample));
            }
        }
    }
    
    if (mfp_needs_reschedule == 1) {
        if (!mfp_dsp_schedule()) {
            printf("mfp_dsp_run: DSP Error: Some processors could not be scheduled\n");
        }
        mfp_needs_reschedule = 0;
    }

    /* the proclist is already scheduled, so iterating in order is OK */
    for(p = (mfp_processor **)(mfp_proc_list->data); *p != NULL; p++) {
        mfp_proc_process(*p);
    }

    proc_count ++;
}

void
mfp_dsp_set_blocksize(int nsamples) 
{
    mfp_blocksize = nsamples;

    /* FIXME need to inform all processors so to reallocate buffers */ 
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

void
mfp_dsp_send_response_str(mfp_processor * proc, int msg_type, char * response)
{
    mfp_respdata rd;
    
    rd.dst_proc = proc;
    rd.msg_type = msg_type;
    rd.response_type = PARAMTYPE_STRING;
    rd.response.c = g_strdup(response);
    
    pthread_mutex_lock(&mfp_response_lock);
    g_array_append_val(mfp_responses_pending, rd);
    pthread_cond_broadcast(&mfp_response_cond);
    pthread_mutex_unlock(&mfp_response_lock);
    
}

void
mfp_dsp_send_response_bool(mfp_processor * proc, int msg_type, int response)
{
    mfp_respdata rd;
    
    rd.dst_proc = proc;
    rd.msg_type = msg_type;
    rd.response_type = PARAMTYPE_BOOL;
    rd.response.i = response;
    
    pthread_mutex_lock(&mfp_response_lock);
    g_array_append_val(mfp_responses_pending, rd);
    pthread_cond_broadcast(&mfp_response_cond);
    pthread_mutex_unlock(&mfp_response_lock);
    
}

void
mfp_dsp_send_response_int(mfp_processor * proc, int msg_type, int response)
{
    mfp_respdata rd;
    
    rd.dst_proc = proc;
    rd.msg_type = msg_type;
    rd.response_type = PARAMTYPE_INT;
    rd.response.i = response;
    
    pthread_mutex_lock(&mfp_response_lock);
    g_array_append_val(mfp_responses_pending, rd);
    pthread_cond_broadcast(&mfp_response_cond);
    pthread_mutex_unlock(&mfp_response_lock);
    
}

void
mfp_dsp_send_response_float(mfp_processor * proc, int msg_type, double response)
{
    mfp_respdata rd;
    
    rd.dst_proc = proc;
    rd.msg_type = msg_type;
    rd.response_type = PARAMTYPE_FLT;
    rd.response.f = response;
    
    pthread_mutex_lock(&mfp_response_lock);
    g_array_append_val(mfp_responses_pending, rd);
    pthread_cond_broadcast(&mfp_response_cond);
    pthread_mutex_unlock(&mfp_response_lock);
    
}

