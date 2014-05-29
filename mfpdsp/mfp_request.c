#include "mfp_dsp.h"

#include <unistd.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <glib.h>
#include <pthread.h>

#include <time.h>

GArray      * incoming_cleanup = NULL;
mfp_in_data * incoming_queue[REQ_BUFSIZE];
int         incoming_queue_write = 0;
int         incoming_queue_read = 0;
pthread_mutex_t incoming_lock = PTHREAD_MUTEX_INITIALIZER;

mfp_out_data outgoing_queue[REQ_BUFSIZE];
int          outgoing_queue_write = 0;
int          outgoing_queue_read = 0;

pthread_mutex_t outgoing_lock = PTHREAD_MUTEX_INITIALIZER;
pthread_cond_t  outgoing_cond = PTHREAD_COND_INITIALIZER;

void 
mfp_dsp_push_request(mfp_in_data rd) 
{
    int count; 
    int cleanup = 0; 
    gpointer newreq = g_malloc0(sizeof(mfp_in_data));
    struct timespec shorttime;

    shorttime.tv_sec = 0; shorttime.tv_nsec = 1000;
    memcpy(newreq, &rd, sizeof(mfp_in_data)); 

    /* note: this mutex just keeps a single writer thread with access 
     * to the requests data, it doesn't block the JACK callback thread */ 
    pthread_mutex_lock(&incoming_lock);
    if (incoming_queue_read == incoming_queue_write) {
        cleanup = 1;
    }
    
    while((incoming_queue_read == 0 && incoming_queue_write == REQ_LASTIND)
        || (incoming_queue_write + 1 == incoming_queue_read)) {
        nanosleep(&shorttime, NULL);
    }

    incoming_queue[incoming_queue_write] = newreq;
    if(incoming_queue_write == REQ_LASTIND) {
        incoming_queue_write = 0;
    }
    else {
        incoming_queue_write += 1;
    }

    if (cleanup == 1) {
        /* now that JACK has finished with the new data, we can clean up 
         * the old data at our leisure.  mfp_dsp_handle_requests will 
         * put any old values that need to be freed into cmd.param_value */ 
        for(count=0; count < incoming_cleanup->len; count++) {
            mfp_in_data * cmd = g_array_index(incoming_cleanup, gpointer, count);
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

        if (incoming_cleanup->len > 0)  {
            g_array_set_size(incoming_cleanup, 0);
        }
    }

    /* we will clean this one up at some time in the future */ 
    g_array_append_val(incoming_cleanup, newreq);

    pthread_mutex_unlock(&incoming_lock);
}

void
mfp_dsp_handle_requests(void)
{
    while(incoming_queue_read != incoming_queue_write) {
        mfp_in_data * cmd = incoming_queue[incoming_queue_read];
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
        incoming_queue_read = (incoming_queue_read+1) % REQ_BUFSIZE;
    }
}

void
mfp_dsp_send_response_str(mfp_processor * proc, int msg_type, char * response)
{
    char * msgbuf = mfp_comm_get_buffer();
    int msglen = 0;
    char tbuf[MFP_MAX_MSGSIZE];

    snprintf(tbuf, MFP_MAX_MSGSIZE, "\"%s\"", response);
    mfp_api_dsp_response(proc->rpc_id, tbuf, msg_type, msgbuf, &msglen);
    mfp_comm_submit_buffer(msgbuf, msglen);
}

void
mfp_dsp_send_response_bool(mfp_processor * proc, int msg_type, int response)
{
    char * msgbuf = mfp_comm_get_buffer();
    int msglen = 0;
    char tbuf[MFP_MAX_MSGSIZE];
    snprintf(tbuf, MFP_MAX_MSGSIZE, "%d", response);
    mfp_api_dsp_response(proc->rpc_id, tbuf, msg_type, msgbuf, &msglen);
    mfp_comm_submit_buffer(msgbuf, msglen);
}

void
mfp_dsp_send_response_int(mfp_processor * proc, int msg_type, int response)
{
    char * msgbuf = mfp_comm_get_buffer();
    int msglen = 0;
    char tbuf[MFP_MAX_MSGSIZE];
    snprintf(tbuf, MFP_MAX_MSGSIZE, "%d", response);
    mfp_api_dsp_response(proc->rpc_id, tbuf, msg_type, msgbuf, &msglen);
    mfp_comm_submit_buffer(msgbuf, msglen);
}

void
mfp_dsp_send_response_float(mfp_processor * proc, int msg_type, double response)
{
    char * msgbuf = mfp_comm_get_buffer();
    int msglen = 0;
    char tbuf[MFP_MAX_MSGSIZE];
    snprintf(tbuf, MFP_MAX_MSGSIZE, "%f", response);
    mfp_api_dsp_response(proc->rpc_id, tbuf, msg_type, msgbuf, &msglen);
    mfp_comm_submit_buffer(msgbuf, msglen);
}

