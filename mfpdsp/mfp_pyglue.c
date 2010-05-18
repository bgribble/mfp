
#include <Python.h>
#include "mfp_jack.h"

static PyObject * 
startup(PyObject * self, PyObject * args) 
{
	mfp_jack_startup();
	return Py_None;
}

static PyObject * 
proc_create(PyObject * self, PyObject *args)
{
	/* args are processor typename and param dict */ 
	PyObject * typename;
	PyObject * paramdict;
	PyArg_ParseTuple(args, "sO", &typename, &paramdict); 
	
	char * typestr = PyString_AsString(typename);

	mfp_procinfo * pinfo = (mfp_procinfo *)g_hash_table_lookup(proc_registry, typestr);
	mfp_processor * proc = NULL;	
	if (pinfo == NULL) {
		return Py_None;
	}
	else {
		proc = mfp_proc_new(pinfo);
		mfp_proc_set_pyparams(proc, paramdict);
		return PyCObject_FromVoidPtr(proc);
	}
}


static PyMethodDef MfpDspMethods[] = {
	{ "startup",  startup, METH_VARARGS, "Start processing thread" },
	{ "proc_create", proc_create, METH_VARARGS, "Create DSP processor" },
	{ "proc_delete", proc_delete, METH_VARARGS, "Delete DSP processor" },
	{ "proc_connect", proc_connect, METH_VARARGS, "Connect 2 DSP processors" },
	{ "proc_disconnect", proc_connect, METH_VARARGS, "Disconnect 2 DSP processors" },
	{ "proc_setparam", proc_setparam, METH_VARARGS, "Set processor parameter" },
	{ "proc_getparam", proc_getparam, METH_VARARGS, "Get processor parameter" },
	{ NULL, NULL, 0, NULL}
};

PyMODINIT_FUNC
initmfpdsp(void) 
{
	Py_InitModule("mfpdsp", MfpDspMethods);
}

