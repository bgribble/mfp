#include <stdio.h>
#include <glib.h>
#include <json-glib/json-glib.h>
#include "mfp_dsp.h"

int api_rpcid = -1;

static void
api_create_callback(Carp__PythonValue * response, void * data)
{
    switch (response->value_types_case) {
        case CARP__PYTHON_VALUE__VALUE_TYPES__INT:
            api_rpcid = response->_int;
            break;
    }
}

void
mfp_api_init(void)
{
    const char service_name[] = "MFPCommand";
    int instance_id = 0;
    mfp_rpc_argblock argblock;
    mfp_rpc_args * args = mfp_rpc_args_init(&argblock);

    char * msgbuf = mfp_comm_get_buffer();
    int msglen = 0;
    int request_id = mfp_rpc_request(
        service_name, instance_id, args,
        api_create_callback, NULL,
        msgbuf, &msglen
    );
    mfp_comm_submit_buffer(msgbuf, msglen);
    mfp_rpc_wait(request_id);
    return;
}


static void
api_load_callback(Carp__PythonValue * response, void * data)
{
    int patch_objid;
    mfp_context * context = (mfp_context *)data;

    switch (response->value_types_case) {
        case CARP__PYTHON_VALUE__VALUE_TYPES__INT:
            mfp_context_default_io(context, response->_int);
            break;
    }
}


int
mfp_api_send_to_inlet(mfp_context * context, int port, float value,
                      char * msgbuf, int * msglen)
{
    const char service_name[] = "MFPCommand.send";
    const int instance_id = api_rpcid;
    mfp_rpc_argblock argblock;
    mfp_rpc_args * arglist = mfp_rpc_args_init(&argblock);

    mfp_rpc_args_append_int(arglist, context->default_obj_id);
    mfp_rpc_args_append_int(arglist, port);
    mfp_rpc_args_append_double(arglist, value);

    int request_id = mfp_rpc_request(
        service_name, instance_id, arglist,
        NULL, NULL, msgbuf, msglen
    );
    return request_id;
}

int
mfp_api_send_to_outlet(mfp_context * context, int port, float value,
                       char * msgbuf, int * msglen)
{
    /* FIXME - this service is not implemented in the MFPCommand API */
    const char service_name[] = "MFPCommand.send_to_outlet";
    const int instance_id = api_rpcid;
    mfp_rpc_argblock argblock;
    mfp_rpc_args * arglist = mfp_rpc_args_init(&argblock);

    mfp_rpc_args_append_int(arglist, context->default_obj_id);
    mfp_rpc_args_append_int(arglist, port);
    mfp_rpc_args_append_double(arglist, value);

    int request_id = mfp_rpc_request(
        service_name, instance_id, arglist,
        NULL, NULL, msgbuf, msglen
    );
    return request_id;
}

int
mfp_api_show_editor(mfp_context * context, int show, char * msgbuf, int * msglen)
{
    const char service_name[] = "MFPCommand.show_editor";
    const int instance_id = api_rpcid;
    mfp_rpc_argblock argblock;
    mfp_rpc_args * arglist = mfp_rpc_args_init(&argblock);

    mfp_rpc_args_append_int(arglist, context->default_obj_id);
    mfp_rpc_args_append_int(arglist, show);

    int request_id = mfp_rpc_request(
        service_name, instance_id, arglist,
        NULL, NULL, msgbuf, msglen
    );
    return request_id;
}

int
mfp_api_open_context(mfp_context * context, char * msgbuf, int * msglen)
{
    const char service_name[] = "MFPCommand.open_context";
    const int instance_id = api_rpcid;
    mfp_rpc_argblock argblock;
    mfp_rpc_args * arglist = mfp_rpc_args_init(&argblock);
    mfp_rpc_args_append_string(arglist, rpc_node_id);
    mfp_rpc_args_append_int(arglist, context->id);
    mfp_rpc_args_append_int(arglist, context->owner);
    mfp_rpc_args_append_int(arglist, context->samplerate);

    int request_id = mfp_rpc_request(
        service_name, instance_id, arglist,
        NULL, NULL, msgbuf, msglen
    );
    return request_id;
}

int
mfp_api_load_context(
    mfp_context * context, char * patchfile, char * msgbuf, int * msglen
)
{
    const char service_name[] = "MFPCommand.load_context";
    const int instance_id = api_rpcid;
    mfp_rpc_argblock argblock;
    mfp_rpc_args * arglist = mfp_rpc_args_init(&argblock);

    mfp_rpc_args_append_string(arglist, patchfile);
    mfp_rpc_args_append_string(arglist, rpc_node_id);
    mfp_rpc_args_append_int(arglist, context->id);

    int request_id = mfp_rpc_request(
        service_name, instance_id, arglist,
        api_load_callback, (void *)context, msgbuf, msglen
    );
    return request_id;
}

int
mfp_api_dsp_response(int proc_id, char * resp, int resp_type, char * msgbuf, int * msglen)
{
    const char service_name[] = "MFPCommand.dsp_response";
    const int instance_id = api_rpcid;
    mfp_rpc_argblock argblock;
    mfp_rpc_args * arglist = mfp_rpc_args_init(&argblock);

    mfp_rpc_args_append_int(arglist, proc_id);
    mfp_rpc_args_append_int(arglist, resp_type);
    mfp_rpc_args_append_string(arglist, resp);

    int request_id = mfp_rpc_request(
        service_name, instance_id, arglist,
        NULL, NULL, msgbuf, msglen
    );
    return request_id;
}

/* FIXME make mfp_api_close_context nonblocking */
int
mfp_api_close_context(mfp_context * context)
{
    const char service_name[] = "MFPCommand.close_context";
    const int instance_id = api_rpcid;
    mfp_rpc_argblock argblock;
    mfp_rpc_args * arglist = mfp_rpc_args_init(&argblock);

    mfp_rpc_args_append_string(arglist, rpc_node_id);
    mfp_rpc_args_append_int(arglist, context->id);

    char * msgbuf = mfp_comm_get_buffer();
    int msglen;

    int request_id = mfp_rpc_request(
        service_name, instance_id, arglist,
        NULL, NULL, msgbuf, &msglen
    );
    mfp_comm_submit_buffer(msgbuf, msglen);
    mfp_rpc_wait(request_id);

    /* handle any DSP config requests */
    mfp_dsp_handle_requests();
}

/* FIXME make mfp_api_exit_notify nonblocking */
int
mfp_api_exit_notify(void)
{
    char announce[] =
        "json:{ \"__type__\": \"HostExitNotify\", \"host_id\": \"%s\" }";
    char * msgbuf = mfp_comm_get_buffer();
    int msglen;

    strncpy(msgbuf, announce, strlen(announce));
    msglen = snprintf(msgbuf, MFP_MAX_MSGSIZE-1, announce, rpc_node_id);
    mfp_comm_submit_buffer(msgbuf, msglen);
}


