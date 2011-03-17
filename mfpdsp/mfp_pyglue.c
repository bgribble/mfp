
#include <Python.h>
#include <pthread.h>
#include "mfp_dsp.h"
#include "builtin.h"


static PyObject * 
dsp_startup(PyObject * mod, PyObject * args) 
{
	int num_inputs, num_outputs;
	PyArg_ParseTuple(args, "ii", &num_inputs, &num_outputs);

	mfp_jack_startup(num_inputs, num_outputs);
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

static int
set_c_param(mfp_processor * proc, char * paramname, PyObject * val) 
{
	int rval = 1;
	int vtype = (int)g_hash_table_lookup(proc->typeinfo->params, paramname);	
	float cflt;
	char * cstr;
	int llen, lpos;
	GArray * g;
	PyObject * oldval;
	PyObject * listval;

	switch ((int)vtype) {
		case PARAMTYPE_UNDEF:
			rval = 0;
			break;
		case PARAMTYPE_FLT:
			if (PyFloat_Check(val)) {
				cflt = PyFloat_AsDouble(val);
				mfp_proc_setparam_float(proc, paramname, cflt);
			}
			else
				rval = 0;

			break;

		case PARAMTYPE_STRING:
			if (PyString_Check(val)) {
				cstr = PyString_AsString(val);
				mfp_proc_setparam_string(proc, paramname, cstr);
			}
			else
				rval = 0;
			break;

		case PARAMTYPE_FLTARRAY:
			if (PyList_Check(val)) {
				llen = PyList_Size(val);
				g = g_array_sized_new(FALSE, FALSE, sizeof(float), llen);
				for(lpos=0; lpos < llen; lpos++) {
					listval = PyList_GetItem(val, lpos);
					if (PyFloat_Check(listval)) {
						cflt = (float)PyFloat_AsDouble(listval);
						g_array_insert_val(g, lpos, cflt); 
					}
					else
						rval = 0;
				}
				if (rval == 1) 
					mfp_proc_setparam_array(proc, paramname, g);
				else
					g_array_free(g);
			}
			else
				rval = 0;
			break;
	}
	if (rval != 0) {
		oldval = g_hash_table_lookup(proc->pyparams, paramname);
		if (oldval != NULL) {
			Py_DECREF(oldval);
		}
		Py_INCREF(val);
		g_hash_table_replace(proc->pyparams, paramname, val);
		proc->needs_config = 1;
	}

	return rval;
}


static int
extract_c_params(mfp_processor * proc, PyObject * params)
{
	PyObject *key, *value;
	Py_ssize_t pos = 0;
	char * param_name;
	int retval = 1;

	while(PyDict_Next(params, &pos, &key, &value)) {
		param_name = PyString_AsString(key);
		retval = set_c_param(proc, param_name, value);
		if (retval == 0) 
			return retval;
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
	mfp_reqdata rd;

	if (pinfo == NULL) {
		Py_INCREF(Py_None);
		return Py_None;
	}
	else {
		rd.reqtype = REQTYPE_CREATE;
		rd.src_proc = mfp_proc_alloc(pinfo, num_inlets, num_outlets, mfp_blocksize);
		extract_c_params(rd.src_proc, paramdict);

	    pthread_mutex_lock(&mfp_globals_lock);
		g_array_append_val(mfp_requests_pending, rd);
		pthread_mutex_unlock(&mfp_globals_lock);

		newobj = PyCObject_FromVoidPtr(rd.src_proc, NULL);
		Py_INCREF(newobj);
		return newobj;
	}
}

static PyObject *
proc_destroy(PyObject * mod, PyObject * args)
{
	PyObject * self=NULL;
	mfp_reqdata rd;

	PyArg_ParseTuple(args, "O", &self);
	rd.reqtype = REQTYPE_DESTROY;
	rd.src_proc = PyCObject_AsVoidPtr(self);
	
	pthread_mutex_lock(&mfp_globals_lock);
	g_array_append_val(mfp_requests_pending, rd);
	pthread_mutex_unlock(&mfp_globals_lock);

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
	
	pthread_mutex_lock(&mfp_globals_lock);
	g_array_append_val(mfp_requests_pending, rd);
	pthread_mutex_unlock(&mfp_globals_lock);

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
	
	pthread_mutex_lock(&mfp_globals_lock);
	g_array_append_val(mfp_requests_pending, rd);
	pthread_mutex_unlock(&mfp_globals_lock);

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

	PyArg_ParseTuple(args, "OsO", &self, &param_name, &param_value);
	set_c_param(((mfp_processor *)PyCObject_AsVoidPtr(self)), param_name, param_value);
	Py_INCREF(Py_False);
	return Py_False;
}

static PyObject * 
py_test_ctests(PyObject * mod, PyObject * args) {
	if (! test_ctests()) {
		Py_INCREF(Py_False);
		return Py_False;
	}
	else {
		Py_INCREF(Py_True);
		return Py_True;
	}

}

static PyMethodDef MfpDspMethods[] = {
	{ "dsp_startup",  dsp_startup, METH_VARARGS, "Start processing thread" },
	{ "dsp_shutdown",  dsp_shutdown, METH_VARARGS, "Stop processing thread" },
	{ "dsp_enable",  dsp_enable, METH_VARARGS, "Enable dsp" },
	{ "dsp_disable",  dsp_disable, METH_VARARGS, "Disable dsp" },
	{ "proc_create", proc_create, METH_VARARGS, "Create DSP processor" },
	{ "proc_destroy", proc_destroy, METH_VARARGS, "Destroy DSP processor" },
	{ "proc_connect", proc_connect, METH_VARARGS, "Connect DSP processors" },
	{ "proc_disconnect", proc_disconnect, METH_VARARGS, "Disconnect DSP processors" },
	{ "proc_getparam", proc_getparam, METH_VARARGS, "Get processor parameter" },
	{ "proc_setparam", proc_setparam, METH_VARARGS, "Set processor parameter" },
	{ "test_ctests", py_test_ctests, METH_VARARGS, "Wrapper for C unit tests" },
	{ NULL, NULL, 0, NULL}
};


static void
init_globals(void)
{
	mfp_proc_list = g_array_new(TRUE, TRUE, sizeof(mfp_processor *));
	mfp_proc_registry = g_hash_table_new(g_str_hash, g_str_equal);
    mfp_requests_pending = g_array_new(TRUE, TRUE, sizeof(mfp_reqdata));
}

static void
init_builtins(void)
{
	mfp_procinfo * pi;

	pi = init_builtin_osc();
	g_hash_table_insert(mfp_proc_registry, pi->name, pi);

	pi = init_builtin_adc();
	g_hash_table_insert(mfp_proc_registry, pi->name, pi);
	
	pi = init_builtin_dac();
	g_hash_table_insert(mfp_proc_registry, pi->name, pi);
	
	pi = init_builtin_sig();
	g_hash_table_insert(mfp_proc_registry, pi->name, pi);
	
	pi = init_builtin_add();
	g_hash_table_insert(mfp_proc_registry, pi->name, pi);

	pi = init_builtin_sub();
	g_hash_table_insert(mfp_proc_registry, pi->name, pi);

	pi = init_builtin_mul();
	g_hash_table_insert(mfp_proc_registry, pi->name, pi);

	pi = init_builtin_div();
	g_hash_table_insert(mfp_proc_registry, pi->name, pi);

	pi = init_builtin_line();
	g_hash_table_insert(mfp_proc_registry, pi->name, pi);

	pi = init_builtin_noise();
	g_hash_table_insert(mfp_proc_registry, pi->name, pi);
}


PyMODINIT_FUNC
initmfpdsp(void) 
{
	init_globals();
	init_builtins();
	Py_InitModule("mfpdsp", MfpDspMethods);
}

