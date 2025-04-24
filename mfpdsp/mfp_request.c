#include "mfp_dsp.h"

#include <unistd.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <glib.h>
#include <pthread.h>

#include <time.h>


void
mfp_dsp_push_request(mfp_in_data rd)
{
    int count;
    int cleanup = 0;
    mfp_context * context = g_hash_table_lookup(mfp_contexts, GINT_TO_POINTER(rd.context_id));

    gpointer newreq = g_malloc0(sizeof(mfp_in_data));
    struct timespec shorttime;

    shorttime.tv_sec = 0; shorttime.tv_nsec = 1000;
    memcpy(newreq, &rd, sizeof(mfp_in_data));

    if (context == NULL) {
        mfp_log_debug("[push] can't find context %d, for request type %d", rd.context_id, rd.reqtype);
    }

    /* note: this mutex just keeps a single writer thread with access
     * to the requests data, it doesn't block the JACK callback thread */
    pthread_mutex_lock(&(context->incoming_lock));
    if (context->incoming_queue_read == context->incoming_queue_write) {
        cleanup = 1;
    }

    while((context->incoming_queue_read == 0 && context->incoming_queue_write == REQ_LASTIND)
        || (context->incoming_queue_write + 1 == context->incoming_queue_read)) {
        nanosleep(&shorttime, NULL);
    }

    context->incoming_queue[context->incoming_queue_write] = newreq;
    if(context->incoming_queue_write == REQ_LASTIND) {
        context->incoming_queue_write = 0;
    }
    else {
        context->incoming_queue_write += 1;
    }

    if (cleanup == 1) {
        /* now that JACK has finished with the new data, we can clean up
         * the old data at our leisure.  mfp_dsp_handle_requests will
         * put any old values that need to be freed into cmd.param_value */
        for(count=0; count < context->incoming_cleanup->len; count++) {
            mfp_in_data * cmd = g_array_index(context->incoming_cleanup, gpointer, count);
            if (cmd->reqtype == REQTYPE_SETPARAM) {
                if (cmd->param_value != NULL) {
                    /* FIXME g_free broken for fltarrays */
                    switch(cmd->param_type) {
                        case PARAMTYPE_INT:
                        case PARAMTYPE_FLT:
                        case PARAMTYPE_STRING:
                        case PARAMTYPE_BOOL:
                            g_free(cmd->param_value);
                            break;
                        case PARAMTYPE_FLTARRAY:
                            g_array_free((GArray *)cmd->param_value, TRUE);
                            break;
                    }
                    cmd->param_value = NULL;
                }
                if (cmd->param_name != NULL) {
                    g_free(cmd->param_name);
                    cmd->param_name = NULL;
                }
            }
            g_free(cmd);
        }

        if (context->incoming_cleanup->len > 0)  {
            g_array_set_size(context->incoming_cleanup, 0);
        }
    }

    /* we will clean this one up at some time in the future */
    g_array_append_val(context->incoming_cleanup, newreq);

    pthread_mutex_unlock(&(context->incoming_lock));
}

void
mfp_dsp_handle_requests(mfp_context * context)
{
    while(context->incoming_queue_read != context->incoming_queue_write) {
        mfp_in_data * cmd = context->incoming_queue[context->incoming_queue_read];
        mfp_processor * src_proc, * dest_proc;

        int type = cmd->reqtype;

        switch (type) {
        case REQTYPE_CONNECT:
            src_proc = mfp_proc_lookup(cmd->src_proc);
            dest_proc = mfp_proc_lookup(cmd->dest_proc);
            if (src_proc != NULL && dest_proc != NULL)
                mfp_proc_connect(src_proc, cmd->src_port, dest_proc, cmd->dest_port);
            break;

        case REQTYPE_DISCONNECT:
            src_proc = mfp_proc_lookup(cmd->src_proc);
            dest_proc = mfp_proc_lookup(cmd->dest_proc);
            if (src_proc != NULL && dest_proc != NULL)
                mfp_proc_disconnect(src_proc, cmd->src_port, dest_proc, cmd->dest_port);
            break;

        case REQTYPE_DESTROY:
            src_proc = mfp_proc_lookup(cmd->src_proc);
            if (src_proc != NULL)
                mfp_proc_destroy(src_proc);
            break;

        case REQTYPE_SETPARAM:
            src_proc = mfp_proc_lookup(cmd->src_proc);
            if (src_proc != NULL) {
                mfp_proc_setparam_req(src_proc, cmd);
                src_proc->needs_config = 1;
            }
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

        case REQTYPE_CONTEXT_MSG:
            /* FIXME -- this is specific to LV2 MIDI for now */
            context = g_hash_table_lookup(mfp_contexts, GINT_TO_POINTER(cmd->context_id));
            context->msg_handler(context, cmd->dest_port, (int64_t)(cmd->param_value));
            break;
        }
        context->incoming_queue_read = (context->incoming_queue_read + 1) % REQ_BUFSIZE;
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

