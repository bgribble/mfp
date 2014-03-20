#include "mfp_dsp.h"

#include <unistd.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <glib.h>
#include <pthread.h>

#include <time.h>

GArray      * mfp_request_cleanup = NULL;
mfp_reqdata * request_queue[REQ_BUFSIZE];
int         request_queue_write = 0;
int         request_queue_read = 0;
pthread_mutex_t mfp_request_lock = PTHREAD_MUTEX_INITIALIZER;

mfp_respdata mfp_response_queue[REQ_BUFSIZE];
int          mfp_response_queue_write = 0;
int          mfp_response_queue_read = 0;

pthread_mutex_t mfp_response_lock = PTHREAD_MUTEX_INITIALIZER;
pthread_cond_t  mfp_response_cond = PTHREAD_COND_INITIALIZER;

void 
mfp_dsp_push_request(mfp_reqdata rd) 
{
    int count; 
    int cleanup = 0; 
    gpointer newreq = g_malloc0(sizeof(mfp_reqdata));
    struct timespec shorttime;

    shorttime.tv_sec = 0; shorttime.tv_nsec = 1000;

    memcpy(newreq, &rd, sizeof(mfp_reqdata)); 

    /* note: this mutex just keeps a single writer thread with access 
     * to the requests data, it doesn't block the JACK callback thread */ 
    pthread_mutex_lock(&mfp_request_lock);
    if (request_queue_read == request_queue_write) {
        cleanup = 1;
    }
    
    while((request_queue_read == 0 && request_queue_write == REQ_LASTIND)
        || (request_queue_write + 1 == request_queue_read)) {
        nanosleep(&shorttime, NULL);
    }

    request_queue[request_queue_write] = newreq;
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
            mfp_reqdata * cmd = g_array_index(mfp_request_cleanup, gpointer, count);
            if (cmd->reqtype == REQTYPE_SETPARAM) {
                if (cmd->param_value != NULL) {
                    g_free(cmd->param_value);
                    cmd->param_value = NULL;
                }
                if (cmd->param_name != NULL) {
                    g_free(cmd->param_name);
                    cmd->param_name = NULL;
                }
            }
            g_free(cmd);
        }

        if (mfp_request_cleanup->len > 0)  {
            g_array_set_size(mfp_request_cleanup, 0);
        }
    }

    /* we will clean this one up at some time in the future */ 
    g_array_append_val(mfp_request_cleanup, newreq);

    pthread_mutex_unlock(&mfp_request_lock);
}

void
mfp_dsp_handle_requests(void)
{
    while(request_queue_read != request_queue_write) {
        mfp_reqdata * cmd = request_queue[request_queue_read];
        int type = cmd->reqtype;

        switch (type) {
        case REQTYPE_CONNECT:
            mfp_proc_connect(cmd->src_proc, cmd->src_port, cmd->dest_proc, cmd->dest_port);
            break;

        case REQTYPE_DISCONNECT:
            mfp_proc_disconnect(cmd->src_proc, cmd->src_port, cmd->dest_proc, cmd->dest_port);
            break;

        case REQTYPE_DESTROY:
            mfp_proc_destroy(cmd->src_proc);
            break;

        case REQTYPE_SETPARAM:
            mfp_proc_setparam_req(cmd->src_proc, cmd);
            cmd->src_proc->needs_config = 1;
            break;

        case REQTYPE_GETPARAM:
            printf("FIXME: getparam unimplemented\n");
            break;

        case REQTYPE_RESET: 
            printf("FIXME: reset unimplemented\n");
            break;

        case REQTYPE_EXTLOAD:
            mfp_ext_init((mfp_extinfo *)cmd->param_value);
            break;
        }
        request_queue_read = (request_queue_read+1) % REQ_BUFSIZE;
    }
}


static int
push_response(mfp_respdata rd) 
{

    if((mfp_response_queue_read == 0 && mfp_response_queue_write == REQ_LASTIND)
        || (mfp_response_queue_write + 1 == mfp_response_queue_read)) {
        return 0;
    }

    mfp_response_queue[mfp_response_queue_write] = rd;
    if(mfp_response_queue_write == REQ_LASTIND) {
        mfp_response_queue_write = 0;
    }
    else {
        mfp_response_queue_write += 1;
    }

    return 1;
}



void
mfp_dsp_send_response_str(mfp_processor * proc, int msg_type, char * response)
{
    mfp_respdata rd;
    
    rd.dst_proc = proc;
    rd.msg_type = msg_type;
    rd.response_type = PARAMTYPE_STRING;
    rd.response.c = g_strdup(response);
   
    if(push_response(rd)) {
        pthread_cond_broadcast(&mfp_response_cond);
    }
    else {
        printf("DSP Response queue full, dropping response\n");
    }
}

void
mfp_dsp_send_response_bool(mfp_processor * proc, int msg_type, int response)
{
    mfp_respdata rd;
    
    rd.dst_proc = proc;
    rd.msg_type = msg_type;
    rd.response_type = PARAMTYPE_BOOL;
    rd.response.i = response;
    
    if(push_response(rd)) {
        pthread_cond_broadcast(&mfp_response_cond);
    }
    else {
        printf("DSP Response queue full, dropping response\n");
    }
}

void
mfp_dsp_send_response_int(mfp_processor * proc, int msg_type, int response)
{
    mfp_respdata rd;
    
    rd.dst_proc = proc;
    rd.msg_type = msg_type;
    rd.response_type = PARAMTYPE_INT;
    rd.response.i = response;
    
    if(push_response(rd)) {
        pthread_cond_broadcast(&mfp_response_cond);
    }
    else {
        printf("DSP Response queue full, dropping response\n");
    }
}

void
mfp_dsp_send_response_float(mfp_processor * proc, int msg_type, double response)
{
    mfp_respdata rd;
    
    rd.dst_proc = proc;
    rd.msg_type = msg_type;
    rd.response_type = PARAMTYPE_FLT;
    rd.response.f = response;
    
    if(push_response(rd)) {
        pthread_cond_broadcast(&mfp_response_cond);
    }
    else {
        printf("DSP Response queue full, dropping response\n");
    }
}

