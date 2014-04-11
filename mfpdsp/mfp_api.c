
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
            printf("mfp_api_init: Got rpc_id %d for MFPCommand\n", api_rpcid);
            return;
        }
    }
}

void
mfp_api_init(void) 
{
    const char method[] = "create";
    const char params[] = "{ \"type\": \"MFPCommand\" }";
    int request_id = mfp_rpc_send_request(method, params, api_create_callback, NULL);
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
            printf("api_load_callback: Got obj_id %d for loaded patch\n", patch_objid);
            mfp_context_connect_default_io(context, patch_objid);
        }
    }
}


int
mfp_api_send_to_inlet(mfp_context * context, int port, float value)
{
    const char method[] = "call";
    const char params[] = "{\"func\": \"send\", \"rpcid\": %d, \"args\": "
                          "[ %d, %d, %f ], \"kwargs\": {} }";
    char tbuf[MFP_MAX_MSGSIZE];
    int request_id;

    snprintf(tbuf, MFP_MAX_MSGSIZE-1, params, api_rpcid, 
             context->default_obj_id, port, value); 
    request_id = mfp_rpc_send_request(method, tbuf, NULL, NULL);
    mfp_rpc_wait(request_id);
}

int
mfp_api_send_to_outlet(mfp_context * context, int port, float value)
{
    const char method[] = "call";
    const char params[] = "{\"func\": \"send_to_outlet\", \"rpcid\": %d, \"args\": "
                          "[ %d, %d, %f ], \"kwargs\": {} }";
    char tbuf[MFP_MAX_MSGSIZE];
    int request_id;

    snprintf(tbuf, MFP_MAX_MSGSIZE-1, params, api_rpcid, 
             context->default_obj_id, port, value); 
    request_id = mfp_rpc_send_request(method, tbuf, NULL, NULL);
    mfp_rpc_wait(request_id);
}


int 
mfp_api_load_context(mfp_context * context, char * patchfile)
{
    const char method[] = "call";
    const char params[] = "{\"func\": \"load_context\", \"rpcid\": %d, \"args\": "
                          "[\"%s\", %d, %d ], \"kwargs\": {} }";
    char tbuf[MFP_MAX_MSGSIZE];
    int request_id;

    snprintf(tbuf, MFP_MAX_MSGSIZE-1, params, api_rpcid, patchfile, 
             mfp_comm_nodeid, context->id);
    request_id = mfp_rpc_send_request(method, tbuf, api_load_callback, (void *)context);
    mfp_rpc_wait(request_id);
}

int
mfp_api_close_context(mfp_context * context)
{
    const char method[] = "call";
    const char params[] = "{\"func\": \"close_context\", \"rpcid\": %d, "
                          "\"args\": [ %d, %d ], \"kwargs\": {} }";

    char tbuf[MFP_MAX_MSGSIZE];
    int request_id;

    snprintf(tbuf, MFP_MAX_MSGSIZE-1, params, api_rpcid, mfp_comm_nodeid, context->id);
    request_id = mfp_rpc_send_request(method, tbuf, NULL, NULL);
    mfp_rpc_wait(request_id);

    /* handle any DSP config requests */
    mfp_dsp_handle_requests();
}
    
int
mfp_api_node_exit(void)
{
    const char method[] = "node_exit";
    const char params[] = "{}";

    mfp_rpc_send_request(method, params, NULL, NULL);
}
    

