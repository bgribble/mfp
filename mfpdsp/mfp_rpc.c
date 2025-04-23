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
static GHashTable * response_received = NULL;
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
encode_param_value(mfp_processor * proc, const char * param_name, const void * param_value, Carp__PythonValue * value)
{
    int vtype = GPOINTER_TO_INT(g_hash_table_lookup(proc->typeinfo->params, param_name));
    GValue gval = G_VALUE_INIT;
    GArray * ga;
    double dval;
    void * rval = NULL;
    mfp_rpc_argblock * resp = NULL;
    mfp_rpc_args * arglist = NULL;

    switch ((int)vtype) {
        case PARAMTYPE_UNDEF:
            mfp_log_debug("[encode_param_value] undefined parameter %s\n", param_name);
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
            resp = g_malloc0(sizeof(mfp_rpc_argblock));
            arglist = mfp_rpc_args_init(resp);

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


static gpointer
extract_param_value(mfp_processor * proc, const char * param_name, Carp__PythonValue * param_value)
{
    int vtype = GPOINTER_TO_INT(g_hash_table_lookup(proc->typeinfo->params, param_name));
    void * rval = NULL;
    double dval;
    const char * strval;
    int i, endex;
    Carp__PythonArray * pbarray = NULL;

    switch ((int)vtype) {
        case PARAMTYPE_UNDEF:
            mfp_log_debug("[extract_param_value] undefined parameter %s\n", param_name);
            break;

        case PARAMTYPE_FLT:
        case PARAMTYPE_INT:
        case PARAMTYPE_BOOL:
            switch(param_value->value_types_case) {
                case CARP__PYTHON_VALUE__VALUE_TYPES__DOUBLE:
                    dval = param_value->_double;
                    break;
                case CARP__PYTHON_VALUE__VALUE_TYPES__INT:
                    dval = (double)(param_value->_int);
                    break;
                case CARP__PYTHON_VALUE__VALUE_TYPES__BOOL:
                    dval = (double)(param_value->_bool);
                    break;
            }
            rval = (gpointer)g_malloc0(sizeof(double));
            *(double *)rval = dval;
            break;

        case PARAMTYPE_STRING:
            if (param_value == NULL) {
                rval = NULL;
            }
            else {
                strval = param_value->_string;
                rval = (gpointer)g_strdup(strval);
            }
            break;

        case PARAMTYPE_FLTARRAY:
            pbarray = param_value->_array;
            endex = pbarray->n_items;
            rval = (gpointer)g_array_sized_new(TRUE, TRUE, sizeof(double), endex);
            for (i=0; i < endex; i++) {
                switch(pbarray->items[i]->value_types_case) {
                    case CARP__PYTHON_VALUE__VALUE_TYPES__DOUBLE:
                        dval = pbarray->items[i]->_double;
                        break;
                    case CARP__PYTHON_VALUE__VALUE_TYPES__INT:
                        dval = (double)(pbarray->items[i]->_int);
                        break;
                }
                g_array_append_val((GArray *)rval, dval);
            }
            break;
    }
    return rval;
}

static void
init_param_helper(const gchar * key, Carp__PythonValue * val, gpointer udata)
{
    mfp_processor * proc = (mfp_processor *)udata;
    void * c_value = extract_param_value(proc, key, val);

    if (c_value != NULL) {
        mfp_proc_setparam(proc, g_strdup(key), c_value);
    }
}


void
dispatch_create(Carp__PythonArray * args, Carp__PythonDict * kwargs, Carp__PythonValue * response)
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

    if (pinfo == NULL) {
        mfp_log_debug("[create] could not find type info for type '%s'\n", typename);
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
            mfp_log_debug("[create] cannot find context %d\n", ctxt_id);
            return;
        }

        proc = mfp_proc_alloc(pinfo, num_inlets, num_outlets, ctxt);
        mfp_proc_init(proc, rpc_id, patch_id);

        for(int prm=0; prm < createprms->n_items; prm++) {
            init_param_helper(
                createprms->items[prm]->key->_string,
                createprms->items[prm]->value,
                (gpointer)proc
            );
        }
        response->value_types_case = CARP__PYTHON_VALUE__VALUE_TYPES__INT;
        response->_int = proc->rpc_id;

        return;
    }
}


int
mfp_rpc_response(int req_id, const char * service_name, Carp__PythonValue * result, char * msgbuf, int * msglen)
{
    char call_buf[MFP_MAX_MSGSIZE] __attribute__ ((aligned(32)));

    if(msgbuf == NULL) {
        mfp_log_debug("[mfp_rpc_response] NULL buffer, aborting buffer send\n");
        *msglen = 0;
        return -1;
    }

    Carp__Envelope env = CARP__ENVELOPE__INIT;
    Carp__CallResponse resp = CARP__CALL_RESPONSE__INIT;
    resp.call_id = req_id;
    resp.service_name = (char *)g_strdup(service_name);
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
        mfp_log_debug("[mfp_rpc_request] NULL buffer, aborting buffer send\n");
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
    gpointer respreceived;

    if (request_id < 0) {
        mfp_log_debug("[mfp_rpc] BADREQUEST, not waiting");
        return;
    }

    pthread_mutex_lock(&request_lock);

    /* check for response already received */
    respreceived = g_hash_table_lookup(response_received, GINT_TO_POINTER(request_id));
    if (respreceived) {
        g_hash_table_remove(response_received, GINT_TO_POINTER(request_id));
        pthread_mutex_unlock(&request_lock);
        return;
    }

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
dispatch_methodcall(
    const char * service_name,
    int obj_id,
    Carp__PythonArray * args,
    Carp__PythonDict * kwargs,
    Carp__PythonValue * rval)
{
    mfp_in_data rd;
    void * to_free = NULL;

    if(!strcmp(service_name, "DSPObject.connect")) {
        rd.reqtype = REQTYPE_CONNECT;
        rd.src_proc = obj_id;
        rd.src_port = args->items[0]->_int;
        rd.dest_proc = args->items[1]->_int;
        rd.dest_port = args->items[2]->_int;
        mfp_dsp_push_request(rd);
    }
    else if (!strcmp(service_name, "DSPObject.disconnect")) {
        rd.reqtype = REQTYPE_DISCONNECT;
        rd.src_proc = obj_id;
        rd.src_port = args->items[0]->_int;
        rd.dest_proc = args->items[1]->_int;
        rd.dest_port = args->items[2]->_int;

        mfp_dsp_push_request(rd);
    }
    else if (!strcmp(service_name, "DSPObject.getparam")) {
        mfp_processor * src_proc = mfp_proc_lookup(obj_id);
        const char * param_name = g_strdup(args->items[0]->_string);
        const void * param_value = g_hash_table_lookup(src_proc->params, param_name);
        to_free = encode_param_value(
            src_proc, param_name, param_value, rval
        );
    }
    else if (!strcmp(service_name, "DSPObject.setparam")) {
        mfp_processor * src_proc = mfp_proc_lookup(obj_id);
        rd.reqtype = REQTYPE_SETPARAM;
        rd.src_proc = obj_id;
        rd.param_name = g_strdup(args->items[0]->_string);
        rd.param_type = mfp_proc_param_type(src_proc, rd.param_name);
        rd.param_value = (gpointer)extract_param_value(
            src_proc, rd.param_name, args->items[1]
        );
        mfp_dsp_push_request(rd);
    }
    else if (!strcmp(service_name, "DSPObject.setparams")) {
        mfp_processor * src_proc = mfp_proc_lookup(obj_id);
        if (!kwargs) {
            return NULL;
        }
        for (int i=0; i < kwargs->n_items; i++) {
            rd.reqtype = REQTYPE_SETPARAM;
            rd.src_proc = obj_id;
            rd.param_name = g_strdup(kwargs->items[i]->key->_string);
            rd.param_type = mfp_proc_param_type(src_proc, rd.param_name);
            rd.param_value = (gpointer)extract_param_value(
                src_proc, rd.param_name, kwargs->items[i]->value
            );
            mfp_dsp_push_request(rd);
        }
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
    else if (!strcmp(service_name, "DSPObject.context_msg")) {
        const int context_id = args->items[0]->_int;
        const int port_id = args->items[1]->_int;
        const int64_t message = args->items[2]->_int;

        rd.reqtype = REQTYPE_CONTEXT_MSG;
        rd.context_id = context_id;
        rd.dest_port = port_id;
        rd.param_value = (gpointer)(message);
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

        if (!strcmp(calldata->service_name, "DSPObject")) {
            dispatch_create(calldata->args, calldata->kwargs, &response);
        }
        else if (!strncmp(calldata->service_name, "DSPObject", 9)) {
            dispatch_methodcall(
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
        carp__call_data__free_unpacked(calldata, NULL);
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
        pthread_mutex_lock(&request_lock);
        g_hash_table_remove(request_waiting, GINT_TO_POINTER(response->call_id));
        g_hash_table_insert(response_received, GINT_TO_POINTER(response->call_id), GINT_TO_POINTER(1));
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
    int success;
    int reqid = -1;

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
    response_received = g_hash_table_new(g_direct_hash, g_direct_equal);

    pthread_mutex_init(&request_lock, NULL);
    pthread_cond_init(&request_cond, NULL);

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
mfp_rpc_args_append_int(mfp_rpc_args * arglist, int64_t value) {
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
