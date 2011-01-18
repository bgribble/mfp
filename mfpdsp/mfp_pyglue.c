
#include <Python.h>
#include "mfp_dsp.h"
#include "builtin.h"

PyObject * cmdqueue = NULL;

#define PROC_CONNECT 1
#define PROC_DISCONNECT 2
#define PROC_SETPARAM 3
#define PROC_DELETE 4

static PyObject *
dsp_get_cmdqueue(PyObject * mod, PyObject * args)
{
	if (cmdqueue == NULL) {
		cmdqueue = PyList_New(0);
	}
	Py_INCREF(cmdqueue);
	return cmdqueue;

}

static PyObject *
get_and_clear_cmdqueue(void)
{
	PyObject * old = cmdqueue;
	cmdqueue = PyList_New(0);
	if (old == NULL) {
		old = PyList_New(0);
	}

	Py_INCREF(old);
	Py_INCREF(cmdqueue);
	return old;
}


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


static PyObject *
set_c_param(mfp_processor * proc, char * paramname, PyObject * val) {
	PyObject * rval = Py_True;
	int vtype = (int)g_hash_table_lookup(proc->typeinfo->params, paramname);	
	float cflt;
	char * cstr;
	int llen, lpos;
	GArray * g;
	PyObject * oldval;

	switch ((int)vtype) {
		case 0:
			rval = Py_None;
			break;
		case 1:
			cflt = PyFloat_AsDouble(val);
			mfp_proc_setparam_float(proc, paramname, cflt);
			break;
		case 2:
			cstr = PyString_AsString(val);
			mfp_proc_setparam_string(proc, paramname, cstr);
			break;
		case 3:
			llen = PyList_Size(val);
			g = g_array_sized_new(FALSE, FALSE, sizeof(float), llen);
			for(lpos=0; lpos < llen; lpos++) {
				cflt = PyFloat_AsDouble(PyList_GetItem(val, lpos));
				g_array_insert_val(g, lpos, cflt); 
			}
			mfp_proc_setparam_array(proc, paramname, g);
			break;
	}
	if (rval != Py_None) {
		oldval = g_hash_table_lookup(proc->pyparams, paramname);
		if (oldval != NULL) {
			Py_DECREF(oldval);
		}
		Py_INCREF(val);
		printf("setting pyparam %s", paramname);
		g_hash_table_replace(proc->pyparams, paramname, val);
	}

	Py_INCREF(rval);
	return rval;
}


void
dsp_handle_queue(void)
{
	PyObject * q = get_and_clear_cmdqueue();
	int qlen = PyList_Size(q);
	int count;

	for(count=0; count < qlen; count++) {
		PyObject * cmd = PyList_GetItem(q, count);
		int type = PyInt_AsLong(PyTuple_GetItem(cmd, 0));
		switch (type) {
		case PROC_CONNECT:
			mfp_proc_connect(PyCObject_AsVoidPtr(PyTuple_GetItem(cmd, 1)),
							 PyInt_AsLong(PyTuple_GetItem(cmd, 2)),
							 PyCObject_AsVoidPtr(PyTuple_GetItem(cmd, 3)),
							 PyInt_AsLong(PyTuple_GetItem(cmd, 4)));
			break;
		case PROC_DISCONNECT:
			mfp_proc_disconnect(PyCObject_AsVoidPtr(PyTuple_GetItem(cmd, 1)),
							 PyInt_AsLong(PyTuple_GetItem(cmd, 2)),
							 PyCObject_AsVoidPtr(PyTuple_GetItem(cmd, 3)),
							 PyInt_AsLong(PyTuple_GetItem(cmd, 4)));
			break;

		case PROC_DELETE:
			//mfp_proc_delete(PyCObject_AsVoidPtr(PyTuple_GetItem(cmd, 1)));
			break;

		case PROC_SETPARAM:
			set_c_param(PyCObject_AsVoidPtr(PyTuple_GetItem(cmd, 1)),
						PyString_AsString(PyTuple_GetItem(cmd, 2)),
						PyTuple_GetItem(cmd, 3));
			break;
		}
	}
}

static void
proc_set_pyparams(mfp_processor * proc, PyObject * params)
{
	PyObject *key, *value;
	Py_ssize_t pos = 0;
	char * param_name;
	while(PyDict_Next(params, &pos, &key, &value)) {
		param_name = PyString_AsString(key);
		set_c_param(proc, param_name, value);
	}
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
	mfp_processor * proc = NULL;	

	if (pinfo == NULL) {
		Py_INCREF(Py_None);
		return Py_None;
	}
	else {
		proc = mfp_proc_create(pinfo, num_inlets, num_outlets, mfp_blocksize);
		proc_set_pyparams(proc, paramdict);
		newobj = PyCObject_FromVoidPtr(proc, NULL);
		Py_INCREF(newobj);
		return newobj;
	}
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
	{ "dsp_get_cmdqueue",  dsp_get_cmdqueue, METH_VARARGS, "Return command queue list" },
	{ "proc_create", proc_create, METH_VARARGS, "Create DSP processor" },
	{ "proc_getparam", proc_getparam, METH_VARARGS, "Get processor parameter" },
	{ "test_ctests", py_test_ctests, METH_VARARGS, "Wrapper for C unit tests" },
	{ NULL, NULL, 0, NULL}
};


static void
init_globals(void)
{
	mfp_proc_list = g_array_new(TRUE, TRUE, sizeof(mfp_processor *));
	mfp_proc_registry = g_hash_table_new(g_str_hash, g_str_equal);
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
	
	pi = init_builtin_plus();
	g_hash_table_insert(mfp_proc_registry, pi->name, pi);
}


PyMODINIT_FUNC
initmfpdsp(void) 
{
	init_globals();
	init_builtins();
	Py_InitModule("mfpdsp", MfpDspMethods);
}

