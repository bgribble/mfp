
#include <Python.h>
#include "mfp_dsp.h"
#include "builtin.h"

PyObject * cmdqueue = NULL;
PyObject * PROC_CONNECT = NULL;
PyObject * PROC_DISCONNECT = NULL;
PyObject * PROC_SETPARAM = NULL;
PyObject * PROC_DELETE = NULL;

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

static void
proc_set_pyparams(mfp_processor * proc, PyObject * params)
{
	PyObject *key, *value;
	Py_ssize_t pos = 0;
	char * param_name;
	double param_value;
	while(PyDict_Next(params, &pos, &key, &value)) {
		param_name = PyString_AsString(key);
		param_value = PyFloat_AsDouble(value);
		mfp_proc_setparam(proc, param_name, param_value);
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

	printf("proc_create: %d, %d, %s, %p\n", num_inlets, num_outlets, typestr, pinfo);

	if (pinfo == NULL) {
		Py_INCREF(Py_None);
		return Py_None;
	}
	else {
		printf("creating DSP object\n");
		proc = mfp_proc_create(pinfo, num_inlets, num_outlets, mfp_blocksize);
		proc_set_pyparams(proc, paramdict);
		newobj = PyCObject_FromVoidPtr(proc, NULL);
		Py_INCREF(newobj);
		printf("Returning DSP object %p\n", proc);
		return newobj;
	}
}

static PyObject * 
proc_delete(PyObject * mod, PyObject * args)
{
	/* arg is the processor as a CObject */ 
	PyObject * cmdq = dsp_get_cmdqueue(NULL, NULL);
	PyObject * cobj = PyTuple_GetItem(args, 0);
	PyObject * reqtuple = PyTuple_New(2);

	PyTuple_SET_ITEM(reqtuple, 0, PROC_DELETE);
	PyTuple_SET_ITEM(reqtuple, 1, cobj);

	PyList_Append(cmdq, reqtuple);

	Py_INCREF(PROC_DELETE);
	Py_INCREF(cobj);
	Py_INCREF(reqtuple);
	Py_INCREF(Py_True);

	Py_DECREF(cmdq);	
	return Py_True;
}

static PyObject * 
proc_connect(PyObject * mod, PyObject * args)
{
	PyObject * cmdq = dsp_get_cmdqueue(NULL, NULL);
	PyObject * self = PyTuple_GetItem(args, 0);
	PyObject * outlet = PyTuple_GetItem(args, 1);
	PyObject * target = PyTuple_GetItem(args, 2);
	PyObject * inlet = PyTuple_GetItem(args, 3);
	PyObject * reqtuple = PyTuple_New(5);

	PyTuple_SET_ITEM(reqtuple, 0, PROC_CONNECT);
	PyTuple_SET_ITEM(reqtuple, 1, self);
	PyTuple_SET_ITEM(reqtuple, 2, outlet);
	PyTuple_SET_ITEM(reqtuple, 3, target);
	PyTuple_SET_ITEM(reqtuple, 4, inlet);

	PyList_Append(cmdq, reqtuple);

	int i;
	for(i=0; i < 5; i++) {
		Py_INCREF(PyTuple_GetItem(reqtuple, i));
	}
	Py_INCREF(reqtuple);
	Py_INCREF(Py_True);
	Py_DECREF(cmdq);	
	return Py_True;
}

static PyObject * 
proc_disconnect(PyObject * mod, PyObject * args)
{
	PyObject * cmdq = dsp_get_cmdqueue(NULL, NULL);
	PyObject * self = PyTuple_GetItem(args, 0);
	PyObject * outlet = PyTuple_GetItem(args, 1);
	PyObject * target = PyTuple_GetItem(args, 2);
	PyObject * inlet = PyTuple_GetItem(args, 3);
	PyObject * reqtuple = PyTuple_New(5);

	PyTuple_SET_ITEM(reqtuple, 0, PROC_DISCONNECT);
	PyTuple_SET_ITEM(reqtuple, 1, self);
	PyTuple_SET_ITEM(reqtuple, 2, outlet);
	PyTuple_SET_ITEM(reqtuple, 3, target);
	PyTuple_SET_ITEM(reqtuple, 4, inlet);

	PyList_Append(cmdq, reqtuple);

	int i;
	for(i=0; i < 5; i++) {
		Py_INCREF(PyTuple_GetItem(reqtuple, i));
	}
	Py_INCREF(reqtuple);
	Py_INCREF(Py_True);
	Py_DECREF(cmdq);	
	return Py_True;
}


static PyObject * 
proc_setparam(PyObject * mod, PyObject * args) 
{
	PyObject * cmdq = dsp_get_cmdqueue(NULL, NULL);
	PyObject * self = PyTuple_GetItem(args, 0);
	PyObject * param= PyTuple_GetItem(args, 1);
	PyObject * value = PyTuple_GetItem(args, 2);
	PyObject * reqtuple = PyTuple_New(5);

	PyTuple_SET_ITEM(reqtuple, 0, PROC_SETPARAM);
	PyTuple_SET_ITEM(reqtuple, 1, self);
	PyTuple_SET_ITEM(reqtuple, 2, param);
	PyTuple_SET_ITEM(reqtuple, 3, value);

	PyList_Append(cmdq, reqtuple);

	int i;
	for(i=0; i < 4; i++) {
		Py_INCREF(PyTuple_GetItem(reqtuple, i));
	}
	Py_INCREF(reqtuple);
	Py_INCREF(Py_True);
	Py_DECREF(cmdq);	
	return Py_True;
}

static PyObject * 
proc_getparam(PyObject * mod, PyObject * args) 
{
	PyObject * self=NULL;
	PyObject * retval = NULL;
	char * param_name=NULL;
	double prmval;

	PyArg_ParseTuple(args, "Os", &self, &param_name);
	printf("calling getparam %p %p %s\n", self, PyCObject_AsVoidPtr(self), param_name); 
	prmval = mfp_proc_getparam(PyCObject_AsVoidPtr(self), param_name);
	retval = PyFloat_FromDouble(prmval); 

	Py_INCREF(retval);
	return retval;
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
	{ "proc_delete", proc_delete, METH_VARARGS, "Delete DSP processor" },
	{ "proc_connect", proc_connect, METH_VARARGS, "Connect 2 DSP processors" },
	{ "proc_disconnect", proc_disconnect, METH_VARARGS, "Disconnect 2 DSP processors" },
	{ "proc_setparam", proc_setparam, METH_VARARGS, "Set processor parameter" },
	{ "proc_getparam", proc_getparam, METH_VARARGS, "Get processor parameter" },
	{ "test_ctests", py_test_ctests, METH_VARARGS, "Wrapper for C unit tests" },
	{ NULL, NULL, 0, NULL}
};


static void
init_globals(void)
{
	mfp_proc_list = g_array_new(TRUE, TRUE, sizeof(mfp_processor *));
	mfp_proc_registry = g_hash_table_new(g_str_hash, g_str_equal);
	
	PROC_CONNECT = PyString_FromString("connect");
	Py_INCREF(PROC_CONNECT);

	PROC_DISCONNECT = PyString_FromString("disconnect");
	Py_INCREF(PROC_DISCONNECT);

	PROC_SETPARAM= PyString_FromString("setparam");
	Py_INCREF(PROC_SETPARAM);
	
	PROC_DELETE = PyString_FromString("delete");
	Py_INCREF(PROC_DELETE);
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
	printf("mfpdsp module init\n");
}

