
#include <Python.h>
#include "mfp_jack.h"

static PyObject * 
mfp_dsp_startup(PyObject * self, PyObject * args) 
{
	mfp_jack_startup();
	return Py_None;
}

static PyMethodDef MfpDspMethods[] = {
	{ "startup", mfp_dsp_startup, METH_VARARGS, "Start processing thread" },
	{ NULL, NULL, 0, NULL}
};

PyMODINIT_FUNC
initmfpdsp(void) 
{
	Py_InitModule("mfpdsp", MfpDspMethods);
}

