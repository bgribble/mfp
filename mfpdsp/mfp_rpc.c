#include "mfp_dsp.h"
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <glib.h>
#include <json-glib/json-glib.h>

int  
mfp_rpc_json_dsp_response(mfp_respdata r, char * outbuf)
{
    const char tmpl[] = "{ \"jsonrpc\": \"2.0\", \"method\": \"call\", "
        "\"params\": { \"func\": \"dsp_response\", \"rpcid\": %d, "
        "\"args\": { \"resp_type\": %d, \"resp_value\": %s }}}";
    char tbuf[MFP_MAX_MSGSIZE];
    int retlen;

    switch(r.response_type) {
        case PARAMTYPE_FLT:
            snprintf(tbuf, MFP_MAX_MSGSIZE, "%f", r.response.f);
            break;
        case PARAMTYPE_BOOL:
            snprintf(tbuf, MFP_MAX_MSGSIZE, "%d", r.response.i);
            break;
        case PARAMTYPE_INT:
            snprintf(tbuf, MFP_MAX_MSGSIZE, "%d", r.response.i);
            break;
        case PARAMTYPE_STRING:
            snprintf(tbuf, MFP_MAX_MSGSIZE, "\"%s\"", r.response.c);
            g_free(r.response.c);
            break;
    }
    retlen = snprintf(outbuf, MFP_MAX_MSGSIZE, tmpl, r.dst_proc, r.response_type, tbuf);
    printf("sending %s\n", outbuf);
    return retlen;
}

void
mfp_rpc_send_response(int req_id, const char * result) 
{
    char reqbuf[MFP_MAX_MSGSIZE];
    snprintf(reqbuf, MFP_MAX_MSGSIZE-1, 
            "{\"jsonrpc\": \"2.0\", \"id\": %d, \"result\": \"%s\"}", req_id, result);
    printf("Response: id %d\n",  req_id);
    mfp_comm_send(reqbuf);
}

int 
mfp_rpc_json_dispatch_request(const char * msgbuf, int msglen) 
{
    JsonParser * parser = json_parser_new();
    JsonNode * root, * val;
    JsonObject * msgobj;
    GError * err;
    const char * methodname;
    int success;
    int reqid;
    int need_response = 0; 

    success = json_parser_load_from_data(parser, msgbuf, msglen, &err);
    printf("parsing '%s'\n", msgbuf);
    if (!success) {
        printf("Error parsing JSON data: '%s'\n", msgbuf);
        return -1;
    }

    root = json_parser_get_root(parser);
    msgobj = json_node_get_object(root);

    val = json_object_get_member(msgobj, "method");
    switch JSON_NODE_TYPE(val) { 
        case JSON_NODE_OBJECT: 
            printf("get_member returned an object\n");
            break;
        case JSON_NODE_ARRAY:
            printf("get_member returned an array\n");
            break;
        case JSON_NODE_NULL:
            printf("json_dispatch: got response (NULL methodname)\n");
            break;
        case JSON_NODE_VALUE:
            need_response = 1;
            methodname = json_node_get_string(val);
            if (methodname != NULL) {
                printf("json_dispatch: got methodcall '%s'\n", json_node_get_string(val));
            }
            break;
    }

    val = json_object_get_member(msgobj, "id");
    if (need_response && val && (JSON_NODE_TYPE(val) == JSON_NODE_VALUE)) {
        reqid = (int)json_node_get_double(val);
        mfp_rpc_send_response(reqid, "[ true, true]");
    }

    return 0;

}

void
mfp_rpc_init(void) 
{
    const char req[] = "{ \"jsonrpc\": \"2.0\", \"method\": \"publish\", "
        "\"params\": { \"classes\": [\"DSPObject\"]}}";
    printf("sending publish req: %s\n", req);
    mfp_comm_send(req);
}

