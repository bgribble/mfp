#include <Python.h>
#include <pthread.h>
#include <signal.h>
#include <execinfo.h>
#include <sys/time.h>
#include "mfp_dsp.h"
#include "builtin.h"


static PyObject * 
dsp_startup(PyObject * mod, PyObject * args) 
{
    int num_inputs, num_outputs, max_blocksize;
    char * client_name;
    PyArg_ParseTuple(args, "siii", &client_name, &max_blocksize, &num_inputs, &num_outputs);

    mfp_max_blocksize = max_blocksize; 
    mfp_jack_startup(client_name, num_inputs, num_outputs);
    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject *
dsp_shutdown(PyObject * mod, PyObject * args) 
{
    mfp_jack_shutdown();
    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject *
dsp_enable(PyObject * mod, PyObject * args)
{
    mfp_dsp_enabled = 1;
    Py_INCREF(Py_True);
    return Py_True;
}

static PyObject *
dsp_disable(PyObject * mod, PyObject * args)
{
    mfp_dsp_enabled = 0;
    Py_INCREF(Py_True);
    return Py_True;
}

static PyObject * 
dsp_samplerate(PyObject * mod, PyObject * args)
{
    PyObject * rval = PyFloat_FromDouble((double)mfp_samplerate);
    Py_INCREF(rval);
    return rval;
}

static PyObject * 
dsp_blocksize(PyObject * mod, PyObject * args)
{
    PyObject * rval = PyFloat_FromDouble((double)mfp_blocksize);
    Py_INCREF(rval);
    return rval;
}

static PyObject * 
dsp_in_latency(PyObject * mod, PyObject * args)
{
    PyObject * rval = PyFloat_FromDouble((double)mfp_in_latency);
    Py_INCREF(rval);
    return rval;
}


static PyObject * 
dsp_out_latency(PyObject * mod, PyObject * args)
{
    PyObject * rval = PyFloat_FromDouble((double)mfp_out_latency);
    Py_INCREF(rval);
    return rval;
}

static PyObject *
dsp_response_wait(PyObject * mod, PyObject * args)
{
    int responses = 0;
    PyObject * l = NULL;
    PyObject * t;
    PyObject * proc;
    mfp_respdata r;
    struct timespec alarmtime;
    struct timeval nowtime;

    Py_BEGIN_ALLOW_THREADS
    pthread_mutex_lock(&mfp_response_lock);
    gettimeofday(&nowtime, NULL);
    alarmtime.tv_sec = nowtime.tv_sec; 
    alarmtime.tv_nsec = nowtime.tv_usec*1000 + 10000000;

    if (mfp_response_queue_read == mfp_response_queue_write) { 
        pthread_cond_timedwait(&mfp_response_cond, &mfp_response_lock, &alarmtime);
    }
    Py_END_ALLOW_THREADS

    /* copy/clear C response objects */
    if(mfp_response_queue_read != mfp_response_queue_write) {
        l = PyList_New(0);
        while(mfp_response_queue_read != mfp_response_queue_write) {
            t = PyTuple_New(3);
            r = mfp_response_queue[mfp_response_queue_read];

            proc = g_hash_table_lookup(mfp_proc_objects, r.dst_proc);
            if (proc == NULL)
                proc = Py_None;

            Py_INCREF(proc);

            PyTuple_SetItem(t, 0, proc);
            PyTuple_SetItem(t, 1, PyInt_FromLong(r.msg_type));
            switch(r.response_type) {
                case PARAMTYPE_FLT:
                    PyTuple_SetItem(t, 2, PyFloat_FromDouble(r.response.f));
                    break;
                case PARAMTYPE_BOOL:
                    PyTuple_SetItem(t, 2, PyBool_FromLong(r.response.i));
                    break;
                case PARAMTYPE_INT:
                    PyTuple_SetItem(t, 2, PyInt_FromLong(r.response.i));
                    break;
                case PARAMTYPE_STRING:
                    PyTuple_SetItem(t, 2, PyString_FromString(r.response.c));
                    g_free(r.response.c);
                    break;
            }
            PyList_Append(l, t);
            responses += 1;
            mfp_response_queue_read = (mfp_response_queue_read+1) % REQ_BUFSIZE;
        }
    }
    pthread_mutex_unlock(&mfp_response_lock);

    /* build python response */
    if (responses == 0) {
        Py_INCREF(Py_None);
        return Py_None;
    }
    else {
        Py_INCREF(l);
        return l;
    }
}

static void * 
py_floatlist_to_c(PyObject * val) 
{
    int llen = PyList_Size(val);
    int lpos; 
    GArray * g; 
    PyObject * listval;
    float cflt;

    g = g_array_sized_new(FALSE, FALSE, sizeof(float), llen);
    for(lpos=0; lpos < llen; lpos++) {
        listval = PyList_GetItem(val, lpos);
        if (PyNumber_Check(listval)) {
            cflt = (float)PyFloat_AsDouble(PyNumber_Float(listval));
            g_array_append_val(g, cflt); 
        }
        else {
            g_array_free(g, TRUE);
            g = NULL;
            break;
        }
    }
    return g; 
}


static void * 
py_float_to_c(PyObject * val) 
{
    gpointer newval = g_malloc(sizeof(float));
    *(float *)newval = (float)PyFloat_AsDouble(val); 
    return newval;
}

static void * 
py_string_to_c(PyObject * val) 
{
    gpointer newval = g_strdup(PyString_AsString(val));
    return newval;
}

static void * 
py_param_value_to_c(mfp_processor * proc, char * paramname, PyObject * val) 
{
    int vtype = (int)g_hash_table_lookup(proc->typeinfo->params, paramname);    
    void * rval = NULL;

    switch ((int)vtype) {
        case PARAMTYPE_UNDEF:
            printf("py_param_value_to_c: undefined parameter %s\n", paramname);
            break;
        case PARAMTYPE_FLT:
            if (PyNumber_Check(val)) {
                rval = py_float_to_c(PyNumber_Float(val));
            }
            break;

        case PARAMTYPE_INT:
            if (PyNumber_Check(val)) {
                rval = py_float_to_c(PyNumber_Float(val));
            }
            break;

        case PARAMTYPE_STRING:
            if (PyString_Check(val)) {
                rval = py_string_to_c(val);
            }
            break;

        case PARAMTYPE_FLTARRAY:
            if (PyList_Check(val)) {
                rval = py_floatlist_to_c(val);
            }
            break;
    }
    return rval;
}

static void
set_pyparam(mfp_processor * proc, char * param_name, PyObject * val)
{
    PyObject * oldval;
    oldval = g_hash_table_lookup(proc->pyparams, param_name);
    if (oldval != NULL) {
        Py_DECREF(oldval);
    }
    Py_INCREF(val);
    g_hash_table_replace(proc->pyparams, param_name, val);
}

static int
init_params(mfp_processor * proc, PyObject * params)
{
    PyObject *key, *value;
    Py_ssize_t pos = 0;
    void * param_value = NULL;
    char * param_name;
    int retval = 1;

    while(PyDict_Next(params, &pos, &key, &value)) {
        param_name = PyString_AsString(key);
        param_value = py_param_value_to_c(proc, param_name, value);
        if (param_value == NULL) { 
            retval = 0;
        }
        else {
            mfp_proc_setparam(proc, g_strdup(param_name), param_value);
            set_pyparam(proc, g_strdup(param_name), value);
        }
    }
    return retval;
}

static PyObject * 
proc_create(PyObject * mod, PyObject *args)
{
    /* args are processor typename and param dict */ 
    char     * typestr = NULL;
    int num_inlets, num_outlets;
    PyObject * paramdict;
    PyObject * newobj;
    PyArg_ParseTuple(args, "siiO", &typestr, &num_inlets, &num_outlets, &paramdict); 

    mfp_procinfo * pinfo = (mfp_procinfo *)g_hash_table_lookup(mfp_proc_registry, typestr);
    mfp_processor * proc;

    if (pinfo == NULL) {
        Py_INCREF(Py_None);
        return Py_None;
    }
    else {
        proc = mfp_proc_alloc(pinfo, num_inlets, num_outlets, mfp_blocksize);
        init_params(proc, paramdict);
        mfp_proc_init(proc);

        newobj = PyCObject_FromVoidPtr(proc, NULL);
        Py_INCREF(newobj);

        g_hash_table_insert(mfp_proc_objects, proc, newobj);
        Py_INCREF(newobj);
        return newobj;
    }
}

static PyObject *
proc_destroy(PyObject * mod, PyObject * args)
{
    PyObject * self=NULL;
    PyObject * objref;
    mfp_reqdata rd;

    PyArg_ParseTuple(args, "O", &self);
    rd.reqtype = REQTYPE_DESTROY;
    rd.src_proc = PyCObject_AsVoidPtr(self);

    mfp_dsp_push_request(rd);

    objref = (PyObject *)g_hash_table_lookup(mfp_proc_objects, rd.src_proc);
    Py_DECREF(objref);

    g_hash_table_remove(mfp_proc_objects, rd.src_proc);

    Py_INCREF(Py_False);
    return Py_False; 
}

static PyObject *
proc_connect(PyObject * mod, PyObject * args)
{
    PyObject * src =NULL;
    PyObject * srcport = NULL;
    PyObject * dst =NULL;
    PyObject * dstport = NULL;

    mfp_reqdata rd;

    PyArg_ParseTuple(args, "OOOO", &src, &srcport, &dst, &dstport);

    rd.reqtype = REQTYPE_CONNECT;
    rd.src_proc = PyCObject_AsVoidPtr(src);
    rd.src_port = (int)PyFloat_AsDouble(srcport);
    rd.dest_proc = PyCObject_AsVoidPtr(dst);
    rd.dest_port = (int)PyFloat_AsDouble(dstport);
   
    mfp_dsp_push_request(rd);

    Py_INCREF(Py_False);
    return Py_False; 
}

static PyObject *
proc_disconnect(PyObject * mod, PyObject * args)
{
    PyObject * src =NULL;
    PyObject * srcport = NULL;
    PyObject * dst =NULL;
    PyObject * dstport = NULL;

    mfp_reqdata rd;

    PyArg_ParseTuple(args, "OOOO", &src, &srcport, &dst, &dstport);
    rd.reqtype = REQTYPE_DISCONNECT;
    rd.src_proc = PyCObject_AsVoidPtr(src);
    rd.src_port = (int)PyFloat_AsDouble(srcport);
    rd.dest_proc = PyCObject_AsVoidPtr(dst);
    rd.dest_port = (int)PyFloat_AsDouble(dstport);
   
    mfp_dsp_push_request(rd);

    Py_INCREF(Py_False);
    return Py_False; 
}

static PyObject * 
proc_getparam(PyObject * mod, PyObject * args) 
{
    PyObject * self=NULL;
    PyObject * retval = NULL;
    char * param_name=NULL;

    PyArg_ParseTuple(args, "Os", &self, &param_name);
    retval = g_hash_table_lookup(((mfp_processor *)PyCObject_AsVoidPtr(self))->pyparams, param_name);
    if (retval == NULL) {
        Py_INCREF(Py_None);
        return Py_None;
    }
    else {
        return retval;
    }
}

static PyObject * 
proc_setparam(PyObject * mod, PyObject * args) 
{
    PyObject * self=NULL;
    char * param_name=NULL;
    PyObject * param_value = NULL;
    void * param_c_value = NULL; 

    mfp_processor * p = NULL;
    mfp_reqdata rd; 

    PyArg_ParseTuple(args, "OsO", &self, &param_name, &param_value);
    p = (mfp_processor *)PyCObject_AsVoidPtr(self); 
    param_c_value = py_param_value_to_c(p, param_name, param_value);

    rd.src_proc = p;
    rd.reqtype = REQTYPE_SETPARAM;
    rd.param_name = g_strdup(param_name);
    rd.param_value = param_c_value; 

    set_pyparam(p, g_strdup(param_name), param_value);

    mfp_dsp_push_request(rd);

    Py_INCREF(Py_False);
    return Py_False;
}

static PyObject * 
proc_reset(PyObject * mod, PyObject * args) 
{
    PyObject * self=NULL;

    PyArg_ParseTuple(args, "O", &self);
    mfp_proc_reset((mfp_processor *)PyCObject_AsVoidPtr(self));
    Py_INCREF(Py_None);
    return Py_None;

}

static PyObject * 
ext_load(PyObject * mod, PyObject * args)
{
    char * filename = NULL;
    PyArg_ParseTuple(args, "s", &filename);
    mfp_reqdata rd;
    rd.reqtype = REQTYPE_EXTLOAD;
    rd.param_value = mfp_ext_load(filename);
    mfp_dsp_push_request(rd);
    Py_INCREF(Py_None);
    return Py_None;
}

static PyMethodDef MfpDspMethods[] = {
    { "dsp_startup",  dsp_startup, METH_VARARGS, "Start processing thread" },
    { "dsp_shutdown",  dsp_shutdown, METH_VARARGS, "Stop processing thread" },
    { "dsp_enable",  dsp_enable, METH_VARARGS, "Enable dsp" },
    { "dsp_disable",  dsp_disable, METH_VARARGS, "Disable dsp" },
    { "dsp_samplerate",  dsp_samplerate, METH_VARARGS, "Return samplerate" },
    { "dsp_blocksize",  dsp_blocksize, METH_VARARGS, "Return blocksize" },
    { "dsp_in_latency",  dsp_in_latency, METH_VARARGS, "Return input latency" },
    { "dsp_out_latency",  dsp_out_latency, METH_VARARGS, "Return output latency" },
    { "dsp_response_wait",  dsp_response_wait, METH_VARARGS, "Return next DSP responses" },
    { "proc_create", proc_create, METH_VARARGS, "Create DSP processor" },
    { "proc_destroy", proc_destroy, METH_VARARGS, "Destroy DSP processor" },
    { "proc_connect", proc_connect, METH_VARARGS, "Connect DSP processors" },
    { "proc_disconnect", proc_disconnect, METH_VARARGS, "Disconnect DSP processors" },
    { "proc_getparam", proc_getparam, METH_VARARGS, "Get processor parameter" },
    { "proc_setparam", proc_setparam, METH_VARARGS, "Set processor parameter" },
    { "proc_reset", proc_reset, METH_VARARGS, "Reset processor state" },
    { "ext_load", ext_load, METH_VARARGS, "Load an extension (shared library)" },
    { NULL, NULL, 0, NULL}
};


static void
init_globals(void)
{
    mfp_proc_list = g_array_new(TRUE, TRUE, sizeof(mfp_processor *));
    mfp_proc_registry = g_hash_table_new(g_str_hash, g_str_equal);
    mfp_proc_objects = g_hash_table_new(NULL, NULL);
    mfp_extensions = g_hash_table_new(g_str_hash, g_str_equal); 

    mfp_request_cleanup = g_array_new(TRUE, TRUE, sizeof(mfp_reqdata *));

    pthread_cond_init(&mfp_response_cond, NULL);
    pthread_mutex_init(&mfp_response_lock, NULL);
    pthread_mutex_init(&mfp_request_lock, NULL);

}

#define ARRAY_LEN(arry, eltsize) (sizeof(arry) / eltsize)

static void
init_builtins(void)
{
    int i;
    mfp_procinfo * pi;
    mfp_procinfo * (* initfuncs[])(void) = { 
        init_builtin_osc, init_builtin_in, init_builtin_out, 
        init_builtin_sig, init_builtin_snap, init_builtin_ampl, 
        init_builtin_add, init_builtin_sub, init_builtin_mul, init_builtin_div, 
        init_builtin_lt, init_builtin_gt,
        init_builtin_line, init_builtin_noise, init_builtin_buffer,
        init_builtin_biquad, init_builtin_phasor,
        init_builtin_ladspa, init_builtin_delay, init_builtin_delblk, init_builtin_noop
    };
    int num_initfuncs = ARRAY_LEN(initfuncs, sizeof(mfp_procinfo *(*)(void)));

    printf("init_builtins: initializing %d builtin DSP processors\n", num_initfuncs);

    for(i = 0; i < num_initfuncs; i++) {
        pi = initfuncs[i]();
        g_hash_table_insert(mfp_proc_registry, pi->name, pi);
    }

}

int
test_SETUP(void) 
{
    /* called before each test case, where each test case is run 
     * in a separate executable */
    init_globals();
    init_builtins();

    mfp_alloc_init();
    return 0;
}

int 
benchmark_SETUP(void) 
{
    return test_SETUP();
}

int
test_TEARDOWN(void)
{
    mfp_alloc_finish();
    return 0;
}


static void
sigsegv_handler(int sig, siginfo_t *si, void *unused)
{
    void * buffer[100];
    char ** strings;
    int nptrs, j;

    printf("ERROR: SIGSEGV received\n");
    nptrs = backtrace(buffer, 100);
    strings = backtrace_symbols(buffer, nptrs);

    for (j = 0; j < nptrs; j++)
        printf("%s\n", strings[j]);

    free(strings);

    exit(-11);
}


PyMODINIT_FUNC
initmfpdsp(void) 
{
    struct sigaction sa;

    /* install signal handlers */
    sa.sa_flags = SA_SIGINFO;
    sigemptyset(&sa.sa_mask);
    sa.sa_sigaction = sigsegv_handler;
    if (sigaction(SIGSEGV, &sa, NULL) == -1) {
        printf("mfpdsp init ERROR: could not install SIGSEGV handler\n");
    }

    init_globals();
    init_builtins();

    Py_InitModule("mfpdsp", MfpDspMethods);
}

