#include "mfp_dsp.h"
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <glib.h>
#include <sys/time.h>
#include <json-glib/json-glib.h>

static int _next_reqid = 1;
static GHashTable * request_callbacks = NULL;
static GHashTable * request_data = NULL;
static GHashTable * request_waiting = NULL;

static pthread_mutex_t request_lock = PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t request_cond = PTHREAD_COND_INITIALIZER;

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

static JsonNode * 
encode_param_value(mfp_processor * proc, const char * param_name, const void * param_value)
{
    int vtype = GPOINTER_TO_INT(g_hash_table_lookup(proc->typeinfo->params, param_name));
    JsonArray * jarray;
    JsonNode * rval;
    GValue gval = G_VALUE_INIT;
    GArray * ga;
    float dval; 

    switch ((int)vtype) {
        case PARAMTYPE_UNDEF:
            printf("encode_param_value: undefined parameter %s\n", param_name);
            break;

        case PARAMTYPE_FLT:
        case PARAMTYPE_INT:
            dval = *(float *)param_value; 
            rval = json_node_new(JSON_NODE_VALUE); 
            g_value_init(&gval, G_TYPE_FLOAT);
            g_value_set_float(&gval, dval);
            json_node_set_value(rval, &gval);
            break;

        case PARAMTYPE_STRING:
            rval = json_node_new(JSON_NODE_VALUE); 
            g_value_init(&gval, G_TYPE_STRING);
            g_value_set_string(&gval, (const char *)param_value);
            json_node_set_value(rval, &gval);

            break;

        case PARAMTYPE_FLTARRAY:
            rval = json_node_new(JSON_NODE_ARRAY); 
            ga = (GArray *)param_value;
            jarray = json_array_new();

            for (int i=0; i < ga->len; i++) { 
                dval = g_array_index(ga, float, i); 
                json_array_add_double_element(jarray, dval);
            }
            json_node_set_array(rval, jarray); 
            break;
    }
    return rval;

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
        mfp_processor * src_proc = mfp_proc_lookup(obj_id);
        const char * param_name = json_node_get_string(json_array_get_element(args, 0));
        const void * param_value = g_hash_table_lookup(src_proc->params, param_name);
        JsonNode * to_encode = json_node_new(JSON_NODE_ARRAY);
        JsonArray * retpair = json_array_new();
        json_array_add_double_element(retpair, -4.0);

        json_array_add_element(retpair, 
                               encode_param_value(src_proc, param_name, param_value)); 
        json_node_set_array(to_encode, retpair); 
        JsonGenerator * gen = json_generator_new();
        json_generator_set_root(gen, to_encode);
        rval = json_generator_to_data(gen, NULL);
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

    if (c_value != NULL) { 
        mfp_proc_setparam(proc, g_strdup(key), c_value);
    }
}

static mfp_processor * 
dispatch_create(JsonArray * args, JsonObject * kwargs)
{
    int num_inlets, num_outlets;
    int ctxt_id;
    int rpc_id, patch_id;
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
        patch_id =  (int)json_node_get_double(json_array_get_element(args, 6));

        ctxt = (mfp_context *)g_hash_table_lookup(mfp_contexts, GINT_TO_POINTER(ctxt_id));
        if (ctxt == NULL) {
            printf("create: cannot find context %d\n", ctxt_id);
            return NULL; 
        }

        proc = mfp_proc_alloc(pinfo, num_inlets, num_outlets, ctxt);
        json_object_foreach_member(createprms, init_param_helper, (gpointer)proc);
        mfp_proc_init(proc, rpc_id, patch_id);
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
    else if (!strcmp(methodname, "node_id")) {
        JsonNode * id = json_object_get_member(params, "node_id");
        if (json_notval(id)) {
            printf("dispatch_methodcall: couldn't parse my new node_id\n");
        }
        else {
            mfp_comm_nodeid = (int)json_node_get_double(id);
            printf("dispatch_methodcall: set C node_id to %d\n", mfp_comm_nodeid);
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
    return retlen;
}

void
mfp_rpc_send_response(int req_id, const char * result) 
{
    char reqbuf[MFP_MAX_MSGSIZE];
    snprintf(reqbuf, MFP_MAX_MSGSIZE-1, 
            "{\"jsonrpc\": \"2.0\", \"id\": %d, \"result\": %s}", req_id, result);
    mfp_comm_send(reqbuf);
}


int
mfp_rpc_send_request(const char * method, const char * params, 
                     void (* callback)(JsonNode *, void *), void * cb_data) 
{
    char reqbuf[MFP_MAX_MSGSIZE];
    int req_id = _next_reqid ++; 

    snprintf(reqbuf, MFP_MAX_MSGSIZE-1, 
            "{\"jsonrpc\": \"2.0\", \"id\": %d, \"method\": \"%s\", \"params\": %s}", 
            req_id, method, params);
    if (callback != NULL) {
        g_hash_table_insert(request_callbacks, GINT_TO_POINTER(req_id), callback);
    }
    if(cb_data != NULL) {
        g_hash_table_insert(request_data, GINT_TO_POINTER(req_id), cb_data);
    }

    mfp_comm_send(reqbuf);
    return req_id; 
}

void 
mfp_rpc_wait(int request_id) 
{    
    struct timespec alarmtime;
    struct timeval nowtime;
    gpointer reqwaiting;

    pthread_mutex_lock(&request_lock);
    g_hash_table_insert(request_waiting, GINT_TO_POINTER(request_id), GINT_TO_POINTER(1));

    printf("mfp_rpc_wait: starting to wait for request %d\n", request_id);
    
    while(!mfp_comm_quit_requested()) {
        gettimeofday(&nowtime, NULL);
        alarmtime.tv_sec = nowtime.tv_sec; 
        alarmtime.tv_nsec = nowtime.tv_usec*1000 + 10000000;
        pthread_cond_timedwait(&request_cond, &request_lock, &alarmtime);

        reqwaiting = g_hash_table_lookup(request_waiting, GINT_TO_POINTER(request_id));
        if (reqwaiting == NULL) {
            printf("mfp_rpc_wait: request %d completed\n", request_id);
            break;
        }
    }

    pthread_mutex_unlock(&request_lock);
}

int 
mfp_rpc_json_dispatch_request(const char * msgbuf, int msglen) 
{
    JsonParser * parser = json_parser_new();
    JsonNode * id, * root, * val, * params;
    JsonObject * msgobj;
    GError * err;
    const char * methodname;
    char * result = NULL;
    void * callback;
    int success;
    int reqid = -1;
    int need_response = 0; 

    success = json_parser_load_from_data(parser, msgbuf, msglen, &err);
    if (!success) {
        printf("Error parsing JSON data: '%s'\n", msgbuf);
        return -1;
    }

    root = json_parser_get_root(parser);
    msgobj = json_node_get_object(root);
    id = json_object_get_member(msgobj, "id");
    if (id && (JSON_NODE_TYPE(id) == JSON_NODE_VALUE)) {
        reqid = (int)json_node_get_double(id);
    }

    val = json_object_get_member(msgobj, "result");
    if ((val != NULL) && (reqid != -1)) {
        printf("rpc_json_dispatch_request: got response for req %d\n", reqid);

        /* it's a response, is there a callback? */ 
        callback = g_hash_table_lookup(request_callbacks, GINT_TO_POINTER(reqid));
        if (callback != NULL) {
            void (* cbfunc)(JsonNode *, void *) = (void (*)(JsonNode *, void *))callback;
            void * cbdata = g_hash_table_lookup(request_data, GINT_TO_POINTER(reqid));

            g_hash_table_remove(request_callbacks, GINT_TO_POINTER(reqid));
            g_hash_table_remove(request_data, GINT_TO_POINTER(reqid));
            
            cbfunc(val, cbdata);
        }

        pthread_mutex_lock(&request_lock);
        g_hash_table_remove(request_waiting, GINT_TO_POINTER(reqid));
        pthread_cond_broadcast(&request_cond);
        pthread_mutex_unlock(&request_lock);
    }
    else { 
        val = json_object_get_member(msgobj, "method");
        if (val && (JSON_NODE_TYPE(val) == JSON_NODE_VALUE)) { 
            need_response = 1;
            methodname = json_node_get_string(val);
            params = json_object_get_member(msgobj, "params");
            if (methodname != NULL) {
                result = dispatch_methodcall(methodname, json_node_get_object(params));
            }
        }

        if (need_response && (reqid != -1)) {
            char * respbuf;
            if (result != NULL) {
                mfp_rpc_send_response(reqid, result);
                g_free(result);
            }
            else {
                mfp_rpc_send_response(reqid, "[ true, true]");
            }
        }
    }

    return 0;

}

void
mfp_rpc_init(void) 
{
    const char req[] = "{ \"jsonrpc\": \"2.0\", \"method\": \"publish\", "
        "\"params\": { \"classes\": [\"DSPObject\"]}}";

    request_callbacks = g_hash_table_new(g_direct_hash, g_direct_equal); 
    request_data = g_hash_table_new(g_direct_hash, g_direct_equal); 
    request_waiting = g_hash_table_new(g_direct_hash, g_direct_equal); 
   
    pthread_mutex_init(&request_lock, NULL);
    pthread_cond_init(&request_cond, NULL); 

    printf("sending publish req: %s\n", req);
    mfp_comm_send(req);
}

