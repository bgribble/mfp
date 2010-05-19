
#include <Python.h>
#include "mfp_dsp.h"
#include "builtin.h"


static PyObject * 
dsp_startup(PyObject * mod, PyObject * args) 
{
	int num_inputs, num_outputs;
	PyArg_ParseTuple(args, "ii", &num_inputs, &num_outputs);

	mfp_jack_startup(num_inputs, num_outputs);
	return Py_None;
}

static PyObject *
dsp_enable(PyObject * mod, PyObject * args)
{
	mfp_dsp_enabled = 1;
	return Py_True;
}

static PyObject *
dsp_disable(PyObject * mod, PyObject * args)
{
	mfp_dsp_enabled = 0;
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
	PyArg_ParseTuple(args, "siiO", &typestr, &num_inlets, &num_outlets, &paramdict); 
	
	mfp_procinfo * pinfo = (mfp_procinfo *)g_hash_table_lookup(mfp_proc_registry, typestr);
	mfp_processor * proc = NULL;	
	if (pinfo == NULL) {
		return Py_None;
	}
	else {
		proc = mfp_proc_create(pinfo, num_inlets, num_outlets, mfp_blocksize);
		proc_set_pyparams(proc, paramdict);
		return PyCObject_FromVoidPtr(proc, NULL);
	}
}

static PyObject * 
proc_delete(PyObject * mod, PyObject * args)
{
	/* arg is the processor as a CObject */ 
	PyObject * cobj = NULL;
	PyArg_ParseTuple(args, "O", &cobj);
	mfp_processor * proc = NULL;

	proc = PyCObject_AsVoidPtr(cobj);
	mfp_proc_destroy(proc);
	return Py_True;
}

static PyObject * 
proc_connect(PyObject * mod, PyObject * args)
{
	/* args: self, target, outlet, inlet is the processor as a CObject */ 
	PyObject * self=NULL, * target=NULL;
	int my_outlet, targ_inlet;
	mfp_processor * self_proc = NULL, * targ_proc = NULL;
	
	PyArg_ParseTuple(args, "OOii", &self, &target, &my_outlet, &targ_inlet);

	self_proc = PyCObject_AsVoidPtr(self);
	targ_proc = PyCObject_AsVoidPtr(target);
	mfp_proc_connect(self_proc, targ_proc, my_outlet, targ_inlet);
	return Py_True;
}

static PyObject * 
proc_disconnect(PyObject * mod, PyObject * args)
{
	/* args: self, target, outlet, inlet is the processor as a CObject */ 
	PyObject * self=NULL, * target=NULL;
	int my_outlet, targ_inlet;
	mfp_processor * self_proc = NULL, * targ_proc = NULL;
	
	PyArg_ParseTuple(args, "OOii", &self, &target, &my_outlet, &targ_inlet);

	self_proc = PyCObject_AsVoidPtr(self);
	targ_proc = PyCObject_AsVoidPtr(target);
	mfp_proc_disconnect(self_proc, targ_proc, my_outlet, targ_inlet);
	return Py_True;
}

static PyObject * 
proc_setparam(PyObject * mod, PyObject * args) 
{
	PyObject * self=NULL;
	char * param_name=NULL;
	double param_value = 0.0;

	PyArg_ParseTuple(args, "Osd", &self, &param_name, &param_value);
	mfp_proc_setparam(PyCObject_AsVoidPtr(self), param_name, param_value);
	return Py_True;
}

static PyObject * 
proc_getparam(PyObject * mod, PyObject * args) 
{
	PyObject * self=NULL;
	char * param_name=NULL;
	double prmval;

	PyArg_ParseTuple(args, "Os", &self, &param_name);
	prmval = mfp_proc_getparam(PyCObject_AsVoidPtr(self), param_name);
	return PyFloat_FromDouble(prmval);
}

static PyMethodDef MfpDspMethods[] = {
	{ "dsp_startup",  dsp_startup, METH_VARARGS, "Start processing thread" },
	{ "dsp_enable",  dsp_enable, METH_VARARGS, "Enable dsp" },
	{ "dsp_disable",  dsp_disable, METH_VARARGS, "Disable dsp" },
	{ "proc_create", proc_create, METH_VARARGS, "Create DSP processor" },
	{ "proc_delete", proc_delete, METH_VARARGS, "Delete DSP processor" },
	{ "proc_connect", proc_connect, METH_VARARGS, "Connect 2 DSP processors" },
	{ "proc_disconnect", proc_disconnect, METH_VARARGS, "Disconnect 2 DSP processors" },
	{ "proc_setparam", proc_setparam, METH_VARARGS, "Set processor parameter" },
	{ "proc_getparam", proc_getparam, METH_VARARGS, "Get processor parameter" },
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
}


PyMODINIT_FUNC
initmfpdsp(void) 
{
	init_globals();
	init_builtins();
	Py_InitModule("mfpdsp", MfpDspMethods);
}

