
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
    mfp_rpc_send_request(method, params, api_create_callback, NULL);
    return;
}

int 
mfp_api_load_patch(mfp_context * context, char * patchfile)
{
    const char method[] = "call";
    const char params[] = "{ \"func\": \"open_file\", \"rpc_id\": %d, \"args\": "
                          "[ %d, \"%s\" ]";
    char tbuf[MFP_MAX_MSGSIZE];

    snprintf(tbuf, MFP_MAX_MSGSIZE-1, params, api_rpcid, context->id, patchfile);
    mfp_rpc_send_request(method, tbuf, NULL, NULL);
}


