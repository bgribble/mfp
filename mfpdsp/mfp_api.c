
#include <stdio.h>
#include <glib.h>
#include <json-glib/json-glib.h>
#include "mfp_dsp.h"

int api_rpcid = -1;

static void
api_create_callback(JsonNode * response, void * data)
{
    if (JSON_NODE_TYPE(response) == JSON_NODE_ARRAY) {
        JsonArray * arry = json_node_get_array(response);
        JsonNode * val = json_array_get_element(arry, 1);
        if (JSON_NODE_TYPE(val) == JSON_NODE_VALUE) {
            api_rpcid = (int)json_node_get_double(val);
            return;
        }
    }
}

void
mfp_api_init(void) 
{
    const char method[] = "create";
    const char params[] = "{ \"type\": \"MFPCommand\" }";
    char * msgbuf = mfp_comm_get_buffer();
    int msglen = 0;
    int request_id = mfp_rpc_request(method, params, api_create_callback, NULL,
                                     msgbuf, &msglen);
    mfp_comm_submit_buffer(msgbuf, msglen);
    mfp_rpc_wait(request_id);
    return;
}


static void
api_load_callback(JsonNode * response, void * data)
{
    int patch_objid;
    mfp_context * context = (mfp_context *)data;

    if (JSON_NODE_TYPE(response) == JSON_NODE_ARRAY) {
        JsonArray * arry = json_node_get_array(response);
        JsonNode * val = json_array_get_element(arry, 1);
        if (JSON_NODE_TYPE(val) == JSON_NODE_VALUE) {
            patch_objid = (int)json_node_get_double(val);
            mfp_context_connect_default_io(context, patch_objid);
        }
    }
}


int
mfp_api_send_to_inlet(mfp_context * context, int port, float value, 
                      char * msgbuf, int * msglen)
{
    const char method[] = "call";
    const char params[] = "{\"func\": \"send\", \"rpcid\": %d, \"args\": "
                          "[ %d, %d, %f ], \"kwargs\": {} }";
    char tbuf[MFP_MAX_MSGSIZE];

    snprintf(tbuf, MFP_MAX_MSGSIZE-1, params, api_rpcid, 
             context->default_obj_id, port, value); 
    int request_id = mfp_rpc_request(method, tbuf, NULL, NULL, msgbuf, msglen); 
    return request_id;
}

int
mfp_api_send_to_outlet(mfp_context * context, int port, float value, 
                       char * msgbuf, int * msglen)
{
    const char method[] = "call";
    const char params[] = "{\"func\": \"send_to_outlet\", \"rpcid\": %d, \"args\": "
                          "[ %d, %d, %f ], \"kwargs\": {} }";
    char tbuf[MFP_MAX_MSGSIZE];

    snprintf(tbuf, MFP_MAX_MSGSIZE-1, params, api_rpcid, 
             context->default_obj_id, port, value); 
    int request_id = mfp_rpc_request(method, tbuf, NULL, NULL, msgbuf, msglen); 
    return request_id;
}

int
mfp_api_show_editor(mfp_context * context, int show, char * msgbuf, int * msglen)
{
    const char method[] = "call";
    const char params[] = "{\"func\": \"show_editor\", \"rpcid\": %d, \"args\": "
                          "[ %d, %d ], \"kwargs\": {} }";
    char tbuf[MFP_MAX_MSGSIZE];

    snprintf(tbuf, MFP_MAX_MSGSIZE-1, params, api_rpcid, context->default_obj_id, show); 
    int request_id = mfp_rpc_request(method, tbuf, NULL, NULL, msgbuf, msglen); 
    return request_id;
}

int 
mfp_api_open_context(mfp_context * context, char * msgbuf, int * msglen)
{
    const char method[] = "call";
    const char params[] = "{\"func\": \"open_context\", \"rpcid\": %d, \"args\": "
                          "[%d, %d, %d ], \"kwargs\": {} }";
    char tbuf[MFP_MAX_MSGSIZE];
    snprintf(tbuf, MFP_MAX_MSGSIZE-1, params, api_rpcid, 
             mfp_comm_nodeid, context->id, context->owner);
    int request_id = mfp_rpc_request(method, tbuf, NULL, NULL, msgbuf, msglen); 
    return request_id;
}

/* FIXME call back the load_callback */ 
int 
mfp_api_load_context(mfp_context * context, char * patchfile, 
                     char * msgbuf, int * msglen)
{
    const char method[] = "call";
    const char params[] = "{\"func\": \"load_context\", \"rpcid\": %d, \"args\": "
                          "[\"%s\", %d, %d ], \"kwargs\": {} }";
    char tbuf[MFP_MAX_MSGSIZE];
    snprintf(tbuf, MFP_MAX_MSGSIZE-1, params, api_rpcid, patchfile, 
             mfp_comm_nodeid, context->id);
    int request_id = mfp_rpc_request(method, tbuf, NULL, NULL, msgbuf, msglen); 
    return request_id;
}

int  
mfp_api_dsp_response(int proc_id, char * resp, int resp_type, char * msgbuf, int * msglen)
{
    const char method[] = "call";
    const char params[] = "{ \"func\": \"dsp_response\", \"rpcid\": %d, "
        "\"args\": [ %d, %s ], \"kwargs\": {} }";
    char outbuf[MFP_MAX_MSGSIZE];

    snprintf(outbuf, MFP_MAX_MSGSIZE, params, proc_id, resp_type, resp);
    int request_id = mfp_rpc_request(method, outbuf, NULL, NULL, msgbuf, msglen); 
    return request_id;
}

/* FIXME make mfp_api_close_context nonblocking */ 
int
mfp_api_close_context(mfp_context * context)
{
    const char method[] = "call";
    const char params[] = "{\"func\": \"close_context\", \"rpcid\": %d, "
                          "\"args\": [ %d, %d ], \"kwargs\": {} }";

    char tbuf[MFP_MAX_MSGSIZE];
    char * msgbuf = mfp_comm_get_buffer();
    int msglen=0;
    int request_id;

    snprintf(tbuf, MFP_MAX_MSGSIZE-1, params, api_rpcid, mfp_comm_nodeid, context->id);
    request_id = mfp_rpc_request(method, tbuf, NULL, NULL, msgbuf, &msglen);
    mfp_comm_submit_buffer(msgbuf, msglen);
    mfp_rpc_wait(request_id);

    /* handle any DSP config requests */
    mfp_dsp_handle_requests();
}
    
/* FIXME make mfp_api_exit_notify nonblocking */ 
int
mfp_api_exit_notify(void)
{
    const char method[] = "exit_notify";
    const char params[] = "{}";
    char * msgbuf = mfp_comm_get_buffer();
    int msglen=0;

    int request_id = mfp_rpc_request(method, params, NULL, NULL, msgbuf, &msglen);
    mfp_comm_submit_buffer(msgbuf, msglen);
    //mfp_rpc_wait(request_id);
}


