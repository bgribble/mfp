#include "mfp_dsp.h"
#include "call_data.pb-c.h"
#include "envelope.pb-c.h"

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

char rpc_peer_id[MAX_PEER_ID_LEN] = "";
char rpc_node_id[MAX_PEER_ID_LEN] = "";

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

static void *
encode_param_value_pb2(mfp_processor * proc, const char * param_name, const void * param_value, Carp__PythonValue * value)
{
    int vtype = GPOINTER_TO_INT(g_hash_table_lookup(proc->typeinfo->params, param_name));
    GValue gval = G_VALUE_INIT;
    GArray * ga;
    double dval;
    void * rval = NULL;

    switch ((int)vtype) {
        case PARAMTYPE_UNDEF:
            printf("encode_param_value: undefined parameter %s\n", param_name);
            break;

        case PARAMTYPE_FLT:
            value->value_types_case = CARP__PYTHON_VALUE__VALUE_TYPES__DOUBLE;
            value->_double = *(double *)param_value;
            break;

        case PARAMTYPE_INT:
            value->value_types_case = CARP__PYTHON_VALUE__VALUE_TYPES__INT;
            value->_int = (int)(*(double *)param_value);
            break;

        case PARAMTYPE_BOOL:
            value->value_types_case = CARP__PYTHON_VALUE__VALUE_TYPES__BOOL;
            value->_bool = (int)(*(double *)param_value);
            break;

        case PARAMTYPE_STRING:
            value->value_types_case = CARP__PYTHON_VALUE__VALUE_TYPES__STRING;
            value->_string = g_strdup(param_value);
            break;

        case PARAMTYPE_FLTARRAY:
            mfp_rpc_argblock * resp = g_malloc0(sizeof(mfp_rpc_argblock));
            mfp_rpc_args * arglist = mfp_rpc_args_init(resp);

            ga = (GArray *)param_value;

            for (int i=0; i < ga->len; i++) {
                dval = g_array_index(ga, double, i);
                mfp_rpc_args_append_double(arglist, dval);
            }
            value->value_types_case = CARP__PYTHON_VALUE__VALUE_TYPES__ARRAY;
            value->_array = &(resp->arg_array);
            rval = resp;
            break;
    }
    return rval;

}

static JsonNode *
encode_param_value(mfp_processor * proc, const char * param_name, const void * param_value)
{
    int vtype = GPOINTER_TO_INT(g_hash_table_lookup(proc->typeinfo->params, param_name));
    JsonArray * jarray;
    JsonNode * rval;
    GValue gval = G_VALUE_INIT;
    GArray * ga;
    double dval;

    switch ((int)vtype) {
        case PARAMTYPE_UNDEF:
            printf("encode_param_value: undefined parameter %s\n", param_name);
            break;

        case PARAMTYPE_FLT:
        case PARAMTYPE_INT:
        case PARAMTYPE_BOOL:
            dval = *(double *)param_value;
            rval = json_node_new(JSON_NODE_VALUE);
            g_value_init(&gval, G_TYPE_DOUBLE);
            g_value_set_double(&gval, dval);
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
                dval = g_array_index(ga, double, i);
                json_array_add_double_element(jarray, dval);
            }
            json_node_set_array(rval, jarray);
            json_array_unref(jarray);
            break;
    }
    return rval;

}

static gpointer
extract_param_value_json(mfp_processor * proc, const char * param_name, JsonNode * param_val)
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
        case PARAMTYPE_BOOL:
            dval = (double)json_node_get_double(param_val);
            rval = (gpointer)g_malloc0(sizeof(double));
            *(double *)rval = dval;
            break;

        case PARAMTYPE_STRING:
            strval = json_node_get_string(param_val);
            rval = (gpointer)g_strdup(strval);
            break;

        case PARAMTYPE_FLTARRAY:
            jarray = json_node_get_array(param_val);
            endex = json_array_get_length(jarray);
            rval = (gpointer)g_array_sized_new(TRUE, TRUE, sizeof(double), endex);
            for (i=0; i < endex; i++) {
                dval = (double)json_node_get_double(json_array_get_element(jarray, i));
                g_array_append_val((GArray *)rval, dval);
            }
            break;
    }
    return rval;
}

static gpointer
extract_param_value_pb2(mfp_processor * proc, const char * param_name, Carp__PythonValue * param_value)
{
    int vtype = GPOINTER_TO_INT(g_hash_table_lookup(proc->typeinfo->params, param_name));
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
        case PARAMTYPE_BOOL:
            dval = param_value->_double;
            rval = (gpointer)g_malloc0(sizeof(double));
            *(double *)rval = dval;
            break;

        case PARAMTYPE_STRING:
            strval = param_value->_string;
            rval = (gpointer)g_strdup(strval);
            break;

        case PARAMTYPE_FLTARRAY:
            Carp__PythonArray * pbarray = param_value->_array;
            endex = pbarray->n_items;
            rval = (gpointer)g_array_sized_new(TRUE, TRUE, sizeof(double), endex);
            for (i=0; i < endex; i++) {
                dval = pbarray->items[i]->_double;
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
    mfp_in_data rd;
    char * rval = NULL;

    if(!strcmp(methodname, "connect")) {
        rd.reqtype = REQTYPE_CONNECT;
        rd.src_proc = obj_id;
        rd.src_port = (int)(json_node_get_double(json_array_get_element(args, 0)));
        rd.dest_proc = (int)(json_node_get_double(json_array_get_element(args, 1)));
        rd.dest_port = (int)(json_node_get_double(json_array_get_element(args, 2)));
        mfp_dsp_push_request(rd);
    }
    else if (!strcmp(methodname, "disconnect")) {
        rd.reqtype = REQTYPE_DISCONNECT;
        rd.src_proc = obj_id;
        rd.src_port = (int)(json_node_get_double(json_array_get_element(args, 0)));
        rd.dest_proc = (int)(json_node_get_double(json_array_get_element(args, 1)));
        rd.dest_port = (int)(json_node_get_double(json_array_get_element(args, 2)));

        mfp_dsp_push_request(rd);
    }
    else if (!strcmp(methodname, "getparam")) {
        mfp_processor * src_proc = mfp_proc_lookup(obj_id);
        const char * param_name = json_node_dup_string(json_array_get_element(args, 0));
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
        json_array_unref(retpair);
        json_node_free(to_encode);
        g_object_unref(gen);
    }
    else if (!strcmp(methodname, "setparam")) {
        mfp_processor * src_proc = mfp_proc_lookup(obj_id);
        rd.reqtype = REQTYPE_SETPARAM;
        rd.src_proc = obj_id;
        rd.param_name = (gpointer)json_node_dup_string(json_array_get_element(args, 0));
        rd.param_type = mfp_proc_param_type(src_proc, rd.param_name);
        rd.param_value = (gpointer)extract_param_value_json(src_proc, rd.param_name,
                                                       json_array_get_element(args, 1));
        mfp_dsp_push_request(rd);
    }
    else if (!strcmp(methodname, "delete")) {
        rd.reqtype = REQTYPE_DESTROY;
        rd.src_proc = obj_id;
        mfp_dsp_push_request(rd);
    }
    else if (!strcmp(methodname, "reset")) {
        rd.reqtype = REQTYPE_RESET;
        rd.src_proc = obj_id;
        mfp_dsp_push_request(rd);
    }
    else {
        printf("methodcall: unhandled method '%s'\n", methodname);
    }

    return rval;
}


static void
init_param_helper_json(JsonObject * obj, const gchar * key, JsonNode * val, gpointer udata)
{
    mfp_processor * proc = (mfp_processor *)udata;
    void * c_value = extract_param_value_json(proc, key, val);

    if (c_value != NULL) {
        mfp_proc_setparam(proc, g_strdup(key), c_value);
    }
}

static void
init_param_helper_pb2(const gchar * key, Carp__PythonValue * val, gpointer udata)
{
    mfp_processor * proc = (mfp_processor *)udata;
    void * c_value = extract_param_value_pb2(proc, key, val);

    if (c_value != NULL) {
        mfp_proc_setparam(proc, g_strdup(key), c_value);
    }
}

static mfp_processor *
dispatch_create_json(JsonArray * args, JsonObject * kwargs)
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
        json_object_foreach_member(createprms, init_param_helper_json, (gpointer)proc);
        mfp_proc_init(proc, rpc_id, patch_id);
        return proc;
    }
}

void
dispatch_create_pb2(Carp__PythonArray * args, Carp__PythonDict * kwargs, Carp__PythonValue * response)
{
    int num_inlets, num_outlets;
    int ctxt_id;
    int rpc_id, patch_id;
    mfp_procinfo * pinfo;
    mfp_processor * proc;
    mfp_context * ctxt;
    Carp__PythonDict * createprms;
    const char * typename = args->items[1]->_string;
    pinfo = (mfp_procinfo *)g_hash_table_lookup(mfp_proc_registry, typename);
    mfp_log_debug("[create] typename=%s", typename);

    if (pinfo == NULL) {
        printf("[create] could not find type info for type '%s'\n", typename);
        return;
    }
    else {
        rpc_id = (int)args->items[0]->_int;
        num_inlets = (int)args->items[2]->_int;
        num_outlets = (int)args->items[3]->_int;
        createprms = args->items[4]->_dict;
        ctxt_id = (int)args->items[5]->_int;
        patch_id = (int)args->items[6]->_int;

        ctxt = (mfp_context *)g_hash_table_lookup(mfp_contexts, GINT_TO_POINTER(ctxt_id));
        if (ctxt == NULL) {
            printf("create: cannot find context %d\n", ctxt_id);
            return;
        }

        proc = mfp_proc_alloc(pinfo, num_inlets, num_outlets, ctxt);

        for(int prm=0; prm < createprms->n_items; prm++) {
            init_param_helper_pb2(
                createprms->items[prm]->key->_string,
                createprms->items[prm]->value,
                (gpointer)proc
            );

        }
        mfp_proc_init(proc, rpc_id, patch_id);
        response->value_types_case = CARP__PYTHON_VALUE__VALUE_TYPES__INT;
        response->_int = proc->rpc_id;

        return;
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

    mfp_log_debug("[methodcall] dispatching %s", methodname);

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
            proc = dispatch_create_json(json_node_get_array(args),
                                   json_node_get_object(kwargs));
            if (proc != NULL) {
                snprintf(ret, 31, "[true, %d]", proc->rpc_id);
                rval = g_strdup(ret);
            }
        }
    }
    else if (!strcmp(methodname, "exit_request")) {
        mfp_comm_io_finish();
    }
    else if (!strcmp(methodname, "peer_exit")) {
        printf("FIXME: peer_exit unhandled\n");
    }
    else if (!strcmp(methodname, "publish")) {
        printf("FIXME: publish unhandled\n");
    }
    else {
        mfp_log_info("FIXME: Unhandled message type %s", methodname);
    }
    return rval;
}

int
mfp_rpc_response(int req_id, const char * service_name, Carp__PythonValue * result, char * msgbuf, int * msglen)
{
    char call_buf[MFP_MAX_MSGSIZE] __attribute__ ((aligned(32)));

    if(msgbuf == NULL) {
        printf("mfp_rpc_response: NULL buffer, aborting buffer send\n");
        *msglen = 0;
        return -1;
    }

    Carp__Envelope env = CARP__ENVELOPE__INIT;
    Carp__CallResponse resp = CARP__CALL_RESPONSE__INIT;
    resp.call_id = req_id;
    resp.service_name = (char *)service_name;
    resp.host_id = rpc_node_id;
    resp.value = result;

    int call_data_size = carp__call_response__pack(&resp, call_buf);
    env.content.data = call_buf;
    env.content.len = call_data_size;
    env.content_type = "CallResponse";
    strncpy(msgbuf, "pb2:", 4);
    *msglen = carp__envelope__pack(&env, msgbuf + 4) + 4;

    return req_id;
}

int
mfp_rpc_request(const char * service_name,
                int instance_id, const mfp_rpc_args * args,
                void (* callback)(Carp__PythonValue *, void *), void * cb_data,
                char * msgbuf, int * msglen)
{
    int req_id = _next_reqid ++;
    char call_buf[MFP_MAX_MSGSIZE] __attribute__ ((aligned(32)));

    if(msgbuf == NULL) {
        printf("mfp_rpc_request: NULL buffer, aborting buffer send\n");
        *msglen = 0;
        return -1;
    }

    Carp__Envelope env = CARP__ENVELOPE__INIT;
    Carp__CallData call_data = CARP__CALL_DATA__INIT;

    call_data.host_id = rpc_peer_id;
    call_data.call_id = req_id;
    call_data.service_name = (char *)service_name;
    call_data.instance_id = instance_id;
    call_data.args = (Carp__PythonArray *)args;
    call_data.kwargs = NULL;

    int call_data_size = carp__call_data__pack(&call_data, &call_buf[0]);
    env.content.data = call_buf;
    env.content.len = call_data_size;
    env.content_type = "CallData";

    strncpy(msgbuf, "pb2:", 4);
    *msglen = carp__envelope__pack(&env, msgbuf + 4) + 4;

    if (callback != NULL) {
        g_hash_table_insert(request_callbacks, GINT_TO_POINTER(req_id), callback);
    }
    if(cb_data != NULL) {
        g_hash_table_insert(request_data, GINT_TO_POINTER(req_id), cb_data);
    }

    return req_id;
}

void
mfp_rpc_wait(int request_id)
{
    struct timespec alarmtime;
    struct timeval nowtime;
    gpointer reqwaiting;

    if (request_id < 0) {
        mfp_log_debug("mfp_rpc: BADREQUEST, not waiting\n");
        return;
    }

    pthread_mutex_lock(&request_lock);

    g_hash_table_insert(request_waiting, GINT_TO_POINTER(request_id), GINT_TO_POINTER(1));

    while(!mfp_comm_quit_requested()) {
        gettimeofday(&nowtime, NULL);
        alarmtime.tv_sec = nowtime.tv_sec;
        alarmtime.tv_nsec = nowtime.tv_usec*1000 + 10000000;
        pthread_cond_timedwait(&request_cond, &request_lock, &alarmtime);

        reqwaiting = g_hash_table_lookup(request_waiting, GINT_TO_POINTER(request_id));
        if (reqwaiting == NULL) {
            break;
        }
    }

    pthread_mutex_unlock(&request_lock);
}


static void *
dispatch_methodcall_pb2(
    const char * service_name,
    int obj_id,
    Carp__PythonArray * args,
    Carp__PythonDict * kwargs,
    Carp__PythonValue * rval)
{
    mfp_in_data rd;
    void * to_free = NULL;

    mfp_log_debug("[method] %s on %d", service_name, obj_id);

    if(!strcmp(service_name, "DSPObject.connect")) {
        mfp_log_debug("[method] connect");
        rd.reqtype = REQTYPE_CONNECT;
        rd.src_proc = obj_id;
        rd.src_port = args->items[0]->_int;
        rd.dest_proc = args->items[1]->_int;
        rd.dest_port = args->items[2]->_int;
        mfp_dsp_push_request(rd);
    }
    else if (!strcmp(service_name, "DSPObject.disconnect")) {
        mfp_log_debug("[method] disconnect");
        rd.reqtype = REQTYPE_DISCONNECT;
        rd.src_proc = obj_id;
        rd.src_port = args->items[0]->_int;
        rd.dest_proc = args->items[1]->_int;
        rd.dest_port = args->items[2]->_int;

        mfp_dsp_push_request(rd);
    }
    else if (!strcmp(service_name, "DSPObject.getparam")) {
        mfp_processor * src_proc = mfp_proc_lookup(obj_id);
        const char * param_name = args->items[0]->_string;
        const void * param_value = g_hash_table_lookup(src_proc->params, param_name);
        to_free = encode_param_value_pb2(
            src_proc, param_name, param_value, rval
        );
    }
    else if (!strcmp(service_name, "DSPObject.setparam")) {
        mfp_processor * src_proc = mfp_proc_lookup(obj_id);
        rd.reqtype = REQTYPE_SETPARAM;
        rd.src_proc = obj_id;
        rd.param_name = args->items[0]->_string;
        rd.param_type = mfp_proc_param_type(src_proc, rd.param_name);
        rd.param_value = (gpointer)extract_param_value_pb2(
            src_proc, rd.param_name, args->items[1]
        );
        mfp_dsp_push_request(rd);
    }
    else if (!strcmp(service_name, "DSPObject.delete")) {
        rd.reqtype = REQTYPE_DESTROY;
        rd.src_proc = obj_id;
        mfp_dsp_push_request(rd);
    }
    else if (!strcmp(service_name, "DSPObject.reset")) {
        rd.reqtype = REQTYPE_RESET;
        rd.src_proc = obj_id;
        mfp_dsp_push_request(rd);
    }
    else {
        mfp_log_debug("[method] unhandled method '%s'", service_name);
    }

    return to_free;

}


static int
mfp_rpc_dispatch_pb2(const char * msgbuf, int msglen)
{
    void * callback;
    int success;

    Carp__Envelope * envelope = carp__envelope__unpack(NULL, msglen, msgbuf);

    if (!strcmp(envelope->content_type, "CallData")) {
        Carp__CallData * calldata =
            carp__call_data__unpack(NULL, envelope->content.len, envelope->content.data);

        Carp__PythonValue response = CARP__PYTHON_VALUE__INIT;
        mfp_log_debug("[dispatch] service_name='%s'", calldata->service_name);

        if (!strcmp(calldata->service_name, "DSPObject")) {
            dispatch_create_pb2(calldata->args, calldata->kwargs, &response);
        }
        else if (!strncmp(calldata->service_name, "DSPObject", 9)) {
            dispatch_methodcall_pb2(
                calldata->service_name,
                calldata->instance_id,
                calldata->args,
                calldata->kwargs,
                &response
            );
        }

        if (calldata->call_id > -1) {
            char * msgbuf = mfp_comm_get_buffer();
            int msglen = 0;
            mfp_rpc_response(
                calldata->call_id,
                calldata->service_name,
                &response,
                msgbuf,
                &msglen
            );
            mfp_comm_submit_buffer(msgbuf, msglen);
        }
    }
    else if (!strcmp(envelope->content_type, "CallResponse")) {
        Carp__CallResponse * response =
            carp__call_response__unpack(NULL, envelope->content.len, envelope->content.data);

        /* it's a response, is there a callback? */
        callback = g_hash_table_lookup(request_callbacks, GINT_TO_POINTER(response->call_id));
        if (callback != NULL) {
            void (* cbfunc)(Carp__PythonValue *, void *) = (void (*)(Carp__PythonValue *, void *))callback;
            void * cbdata = g_hash_table_lookup(request_data, GINT_TO_POINTER(response->call_id));

            g_hash_table_remove(request_callbacks, GINT_TO_POINTER(response->call_id));
            g_hash_table_remove(request_data, GINT_TO_POINTER(response->call_id));

            cbfunc(response->value, cbdata);
        }
        else {
            mfp_log_debug("[pb2] No callback for response");
        }

        pthread_mutex_lock(&request_lock);
        g_hash_table_remove(request_waiting, GINT_TO_POINTER(response->call_id));
        pthread_cond_broadcast(&request_cond);
        pthread_mutex_unlock(&request_lock);
        carp__call_response__free_unpacked(response, NULL);
    }
    carp__envelope__free_unpacked(envelope, NULL);
}


static int
mfp_rpc_dispatch_json(const char * msgbuf, int msglen)
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
        mfp_log_info("Error parsing JSON data: '%s'\n", msgbuf);
        return -1;
    }

    root = json_parser_get_root(parser);
    msgobj = json_node_get_object(root);

    val = json_object_get_member(msgobj, "__type__");
    if (val && (JSON_NODE_TYPE(val) == JSON_NODE_VALUE)) {
        const char * typename = json_node_get_string(val);
        if (typename != NULL && !strcmp(typename, "HostExports")) {
            val = json_object_get_member(msgobj, "host_id");
            if (val && (JSON_NODE_TYPE(val) == JSON_NODE_VALUE)) {
                const char * hostid = json_node_get_string(val);
                strncpy(rpc_peer_id, hostid, MAX_PEER_ID_LEN);
            }
        }
    }

    id = json_object_get_member(msgobj, "id");
    if (id && (JSON_NODE_TYPE(id) == JSON_NODE_VALUE)) {
        reqid = (int)json_node_get_double(id);
    }

    val = json_object_get_member(msgobj, "result");
    if ((val != NULL) && (reqid != -1)) {
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
            char * msgbuf = mfp_comm_get_buffer();
            int msglen = 0;
#if 0
            if (result != NULL) {
                mfp_rpc_response(reqid, result, msgbuf, &msglen);
                g_free(result);
            }
            else {
                mfp_rpc_response(reqid, "[ true, true]", msgbuf, &msglen);
            }
            mfp_comm_submit_buffer(msgbuf, msglen);
#endif
        }
    }

    g_object_unref(parser);
    return 0;

}

int
mfp_rpc_dispatch_request(const char * msgbuf, int msglen)
{
    if (!strncmp(msgbuf, "json:", 5)) {
        msgbuf += 5;
        msglen -= 5;
        return mfp_rpc_dispatch_json(msgbuf, msglen);
    }
    else if (!strncmp(msgbuf, "pb2:", 4)) {
        msgbuf += 4;
        msglen -= 4;
        return mfp_rpc_dispatch_pb2(msgbuf, msglen);
    }
    else {
        mfp_log_info("Unrecognized message serialization: %s", msgbuf);
        return -1;
    }

}

static void
ready_callback(JsonNode * response, void * data)
{
    if (JSON_NODE_TYPE(response) == JSON_NODE_ARRAY) {
        JsonArray * arry = json_node_get_array(response);
        JsonNode * val = json_array_get_element(arry, 1);
        if (JSON_NODE_TYPE(val) == JSON_NODE_VALUE) {
            mfp_comm_nodeid = (int)json_node_get_double(val);
            return;
        }
    }
}

static void
create_uuid_32(char * buffer) {
    const char hexdigits[] = "0123456789abcdef";
    for (int i=0; i < 32; i++){
        buffer[i] = hexdigits[rand() % 16];
    }
    buffer[32] = (char)0;
}

void
mfp_rpc_init(void)
{
    int req_id;
    char announce[] =
        "json:{ \"__type__\": \"HostAnnounce\", \"host_id\": \"%s\" }";
    char * msgbuf;
    int msglen;

    request_callbacks = g_hash_table_new(g_direct_hash, g_direct_equal);
    request_data = g_hash_table_new(g_direct_hash, g_direct_equal);
    request_waiting = g_hash_table_new(g_direct_hash, g_direct_equal);

    pthread_mutex_init(&request_lock, NULL);
    pthread_cond_init(&request_cond, NULL);

    mfp_log_info("Connecting to master process...");
    create_uuid_32(rpc_node_id);
    msgbuf = mfp_comm_get_buffer();
    msglen = snprintf(msgbuf, MFP_MAX_MSGSIZE-1, announce, rpc_node_id);

    /* clear the peer ID */
    rpc_peer_id[0] = 0;

    mfp_comm_submit_buffer(msgbuf, msglen);

    /* wait for host's service response to set the peer ID*/
    struct timespec alarmtime;
    struct timeval nowtime;

    pthread_mutex_lock(&request_lock);
    while(!mfp_comm_quit_requested()) {
        gettimeofday(&nowtime, NULL);
        alarmtime.tv_sec = nowtime.tv_sec;
        alarmtime.tv_nsec = nowtime.tv_usec*1000 + 10000000;
        pthread_cond_timedwait(&request_cond, &request_lock, &alarmtime);

        if (strlen(rpc_peer_id) > 0) {
            break;
        }
    }
    pthread_mutex_unlock(&request_lock);
}


mfp_rpc_args *
mfp_rpc_args_init(mfp_rpc_argblock * argblock) {
    /* ok maybe this is just stupid, but I don't like all the
     * allocations we have to do just to build a short argument
     * list. The "argblock" has enough rool for all the data in a
     * ARGBLOCK_SIZE list of values.
     */
    Carp__PythonArray arginit = CARP__PYTHON_ARRAY__INIT;
    Carp__PythonValue valinit = CARP__PYTHON_VALUE__INIT;

    memcpy(&(argblock->arg_array), &arginit, sizeof(Carp__PythonArray));
    memcpy(&(argblock->arg_array_value), &valinit, sizeof(Carp__PythonValue));

    argblock->arg_array_value._array = &(argblock->arg_array);
    argblock->arg_array_value.value_types_case = CARP__PYTHON_VALUE__VALUE_TYPES__ARRAY;

    argblock->arg_array.n_items = 0;
    argblock->arg_array.items = &(argblock->arg_value_pointers[0]);

    for(int i=0; i < MFP_RPC_ARGBLOCK_SIZE; i++) {
        argblock->arg_value_pointers[i] = argblock->arg_values + i;
        memcpy(&argblock->arg_values[i], &valinit, sizeof(Carp__PythonValue));
    }

    return &(argblock->arg_array);
}

void
mfp_rpc_args_append_string(mfp_rpc_args * arglist, const char * value) {
    int prev_count = arglist->n_items;

    arglist->items[prev_count]->value_types_case = CARP__PYTHON_VALUE__VALUE_TYPES__STRING;
    arglist->items[prev_count]->_string = (char *)value;

    arglist->n_items += 1;
}

void
mfp_rpc_args_append_bool(mfp_rpc_args * arglist, int value) {
    int prev_count = arglist->n_items;

    arglist->items[prev_count]->value_types_case = CARP__PYTHON_VALUE__VALUE_TYPES__BOOL;
    arglist->items[prev_count]->_bool = value;

    arglist->n_items += 1;
}

void
mfp_rpc_args_append_int(mfp_rpc_args * arglist, int value) {
    int prev_count = arglist->n_items;

    arglist->items[prev_count]->value_types_case = CARP__PYTHON_VALUE__VALUE_TYPES__INT;
    arglist->items[prev_count]->_int = value;

    arglist->n_items += 1;
}


void
mfp_rpc_args_append_double(mfp_rpc_args * arglist, double value) {
    int prev_count = arglist->n_items;

    arglist->items[prev_count]->value_types_case = CARP__PYTHON_VALUE__VALUE_TYPES__DOUBLE;
    arglist->items[prev_count]->_double = value;

    arglist->n_items += 1;
}
