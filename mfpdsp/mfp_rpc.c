#include "mfp_dsp.h"
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <glib.h>
#include <json-glib/json-glib.h>

static int
json_notval(JsonNode * node)
{
    if (node == NULL) {
        return 1;
    }
    else if (JSON_NODE_TYPE(node) == JSON_NODE_NULL) {
        return 1;
    }
    else {
        return 0;
    }
}

static gpointer 
extract_param_value(mfp_processor * proc, const char * param_name, JsonNode * param_val)
{
    int vtype = GPOINTER_TO_INT(g_hash_table_lookup(proc->typeinfo->params, param_name));
    JsonArray * jarray;
    void * rval = NULL;
    double dval;
    const char * strval;
    int i, endex;

    switch ((int)vtype) {
        case PARAMTYPE_UNDEF:
            printf("extract_param_value: undefined parameter %s\n", param_name);
            break;
        case PARAMTYPE_FLT:
        case PARAMTYPE_INT:
            dval = json_node_get_double(param_val);
            rval = (gpointer)g_malloc0(sizeof(float));
            *(float *)rval = (float)dval;
            break;

        case PARAMTYPE_STRING:
            strval = json_node_get_string(param_val);
            rval = (gpointer)g_strdup(strval);
            break;

        case PARAMTYPE_FLTARRAY:
            jarray = json_node_get_array(param_val);
            endex = json_array_get_length(jarray);
            rval = (gpointer)g_array_sized_new(FALSE, FALSE, sizeof(float), endex);
            dval = json_node_get_double(json_array_get_element(jarray, i));
            for (i=0; i < endex; i++) { 
                g_array_append_val((GArray *)rval, dval);
            }
            break;
    }
    return rval;
}

/*
 * dispatch_object_methodcall implments the API of the Python DSPObject class 
 * (see dsp_object.py)
 */

static char *  
dispatch_object_methodcall(int obj_id, const char * methodname, JsonArray * args)
{
    JsonNode * val;
    mfp_reqdata rd;
    char * rval = NULL;

    printf("dispatch_object_methodcall: '%s' on %d\n", methodname, obj_id); 
    
    if(!strcmp(methodname, "connect")) {
        rd.reqtype = REQTYPE_CONNECT;
        rd.src_proc = mfp_proc_lookup(obj_id); 
        rd.src_port = (int)(json_node_get_double(json_array_get_element(args, 0)));
        rd.dest_proc = mfp_proc_lookup((int)(json_node_get_double(
                        json_array_get_element(args, 1))));
        rd.dest_port = (int)(json_node_get_double(json_array_get_element(args, 2)));
        mfp_dsp_push_request(rd);
    }
    else if (!strcmp(methodname, "disconnect")) {
        rd.reqtype = REQTYPE_DISCONNECT;
        rd.src_proc = mfp_proc_lookup(obj_id); 
        rd.src_port = (int)(json_node_get_double(json_array_get_element(args, 0)));
        rd.dest_proc = mfp_proc_lookup((int)(json_node_get_double(
                        json_array_get_element(args, 1))));
        rd.dest_port = (int)(json_node_get_double(json_array_get_element(args, 2)));
        mfp_dsp_push_request(rd);
    }
    else if (!strcmp(methodname, "getparam")) {
        rd.reqtype = REQTYPE_GETPARAM;
        rd.src_proc = mfp_proc_lookup(obj_id); 
        rd.param_name = (gpointer)json_node_get_string(json_array_get_element(args, 0));
    }
    else if (!strcmp(methodname, "setparam")) {
        rd.reqtype = REQTYPE_SETPARAM;
        rd.src_proc = mfp_proc_lookup(obj_id); 
        rd.param_name = (gpointer)json_node_get_string(json_array_get_element(args, 0));
        rd.param_value = (gpointer)extract_param_value(rd.src_proc, rd.param_name, 
                                                       json_array_get_element(args, 1));
        mfp_dsp_push_request(rd);
    }
    else if (!strcmp(methodname, "destroy")) {
        rd.reqtype = REQTYPE_DESTROY;
        rd.src_proc = mfp_proc_lookup(obj_id); 
        mfp_dsp_push_request(rd);
    }
    else if (!strcmp(methodname, "reset")) {
        rd.reqtype = REQTYPE_RESET;
        rd.src_proc = mfp_proc_lookup(obj_id); 
        mfp_dsp_push_request(rd);
    }
    else {
        printf("methodcall: unhandled method '%s'\n", methodname);
    }

    return rval;
}


static void
init_param_helper(JsonObject * obj, const gchar * key, JsonNode * val, gpointer udata)
{
    mfp_processor * proc = (mfp_processor *)udata;
    void * c_value = extract_param_value(proc, key, val);
    printf("init_param_helper: key='%s'\n", key);

    if (c_value != NULL) { 
        printf("   init_param: prm='%s' val=%p\n", key, c_value); 
        mfp_proc_setparam(proc, g_strdup(key), c_value);
    }
}

static mfp_processor * 
dispatch_create(JsonArray * args, JsonObject * kwargs)
{
    int num_inlets, num_outlets;
    int ctxt_id;
    int rpc_id;
    mfp_procinfo * pinfo;
    mfp_processor * proc;
    mfp_context * ctxt;
    JsonObject * createprms;
    const char * typename = json_node_get_string(json_array_get_element(args, 1));

    pinfo = (mfp_procinfo *)g_hash_table_lookup(mfp_proc_registry, typename);

    if (pinfo == NULL) {
        printf("create: could not find type info for type '%s'\n", typename);
        return NULL;
    }
    else {
        rpc_id = (int)json_node_get_double(json_array_get_element(args, 0));
        num_inlets = (int)json_node_get_double(json_array_get_element(args, 2));
        num_outlets = (int)json_node_get_double(json_array_get_element(args, 3));
        createprms = json_node_get_object(json_array_get_element(args, 4));
        ctxt_id =  (int)json_node_get_double(json_array_get_element(args, 5));

        printf("create: init '%s' inlets=%d outlets=%d context=%d\n", typename, num_inlets, 
               num_outlets, ctxt_id);
        ctxt = (mfp_context *)g_hash_table_lookup(mfp_contexts, GINT_TO_POINTER(ctxt_id));
        if (ctxt == NULL) {
            printf("create: cannot find context %d\n", ctxt_id);
            return NULL; 
        }

        proc = mfp_proc_alloc(pinfo, num_inlets, num_outlets, ctxt);
        printf("create: setting initial params\n");
        json_object_foreach_member(createprms, init_param_helper, (gpointer)proc);
        printf("create: calling proc_init\n");
        mfp_proc_init(proc, rpc_id);
        return proc;
    }
}


/* 
 * dispatch_methodcall implements the API of the Python RPCHost class 
 * (see RPCHost.py:RPCHost.handle_request).
 */ 

static char * 
dispatch_methodcall(const char * methodname, JsonObject * params) 
{
    char * rval = NULL; 


    if(!strcmp(methodname, "call")) {
        JsonNode * funcname, * funcparams, * funcobj;

       printf("dispatch_methodcall: handling call\n");
        funcname = json_object_get_member(params, "func");
        funcparams = json_object_get_member(params, "args");
        funcobj = json_object_get_member(params, "rpcid");

        /* all must be set */
        if (json_notval(funcname) || json_notval(funcparams) || json_notval(funcobj)) {
            printf("dispatch_methodcall: problem with func, args, or rpcid\n");
        }
        else {
            rval = dispatch_object_methodcall((int)json_node_get_double(funcobj), 
                                               json_node_get_string(funcname), 
                                               json_node_get_array(funcparams));
        }
    }
    else if (!strcmp(methodname, "create")) {
        JsonNode * typename, * args, * kwargs;
        mfp_processor * proc=NULL;
        char ret[32];

        printf("dispatch_methodcall: handling create\n");
        typename = json_object_get_member(params, "type");
        args = json_object_get_member(params, "args");
        kwargs = json_object_get_member(params, "kwargs");
        if (json_notval(typename) || json_notval(args) || json_notval(kwargs)) {
            printf("dispatch_methodcall: couldn't parse one of type, args, kwargs\n");
        }
        else {
            proc = dispatch_create(json_node_get_array(args), 
                    json_node_get_object(kwargs));
            if (proc != NULL) {
                snprintf(ret, 31, "[true, %d]", proc->rpc_id);
                rval = g_strdup(ret);
            }
        }
    }
    else if (!strcmp(methodname, "peer_exit")) {
        printf("FIXME: peer_exit unhandled\n");
    }
    else if (!strcmp(methodname, "publish")) {
        printf("FIXME: publish unhandled\n");
    }
    return rval;

}

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
            "{\"jsonrpc\": \"2.0\", \"id\": %d, \"result\": %s}", req_id, result);
    printf("Response: id %d\n",  req_id);
    mfp_comm_send(reqbuf);
}

int 
mfp_rpc_json_dispatch_request(const char * msgbuf, int msglen) 
{
    JsonParser * parser = json_parser_new();
    JsonNode * root, * val, * params;
    JsonObject * msgobj;
    GError * err;
    const char * methodname;
    char * result = NULL;
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
    if (val && (JSON_NODE_TYPE(val) == JSON_NODE_VALUE)) { 
        need_response = 1;
        methodname = json_node_get_string(val);
        params = json_object_get_member(msgobj, "params");
        if (methodname != NULL) {
            printf("json_dispatch: got methodcall '%s'\n", methodname);
            result = dispatch_methodcall(methodname, json_node_get_object(params));
        }
    }

    val = json_object_get_member(msgobj, "id");
    if (need_response && val && (JSON_NODE_TYPE(val) == JSON_NODE_VALUE)) {
        char * respbuf;

        reqid = (int)json_node_get_double(val);
        if (result != NULL) {
            mfp_rpc_send_response(reqid, result);
            g_free(result);
        }
        else {
            mfp_rpc_send_response(reqid, "[ true, true]");
        }
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

