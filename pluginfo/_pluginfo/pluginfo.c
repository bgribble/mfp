
#include <Python.h>
#include <ladspa.h>
#include <dlfcn.h>

static PyObject * 
is_ladspa(PyObject * mod, PyObject * args) 
{
    char * libname = NULL;
    void * dlfile;
    LADSPA_Descriptor (* descrip)(unsigned long);

    PyArg_ParseTuple(args, "s", &libname);
    
    if (libname == NULL) {
        Py_INCREF(Py_None);
        return Py_None;
    }

    dlfile = dlopen(libname, RTLD_NOW);
    if (dlfile == NULL) {
        Py_INCREF(Py_False);
        return Py_False;
    }
    
    descrip = dlsym(dlfile, "ladspa_descriptor");
    
    dlclose(dlfile);

    if (descrip != NULL) {
        Py_INCREF(Py_True);
        return Py_True;
    }
    else {
        Py_INCREF(Py_False);
        return Py_False;
    }
}


static PyObject * 
list_plugins(PyObject * mod, PyObject * args) 
{
    char * libname = NULL;
    void * dlfile;
    int plug_id;
    LADSPA_Descriptor * (* descrip_func)(unsigned long);
    LADSPA_Descriptor * descrip;
    PyObject * list = NULL;
    PyObject * tup = NULL; 

    PyArg_ParseTuple(args, "s", &libname);
    
    if (libname == NULL) {
        Py_INCREF(Py_None);
        return Py_None;
    }

    dlfile = dlopen(libname, RTLD_NOW);
    if (dlfile == NULL) {
        Py_INCREF(Py_None);
        return Py_None;
    }
    
    descrip_func = dlsym(dlfile, "ladspa_descriptor");
    
    list = PyList_New(0);

    for(plug_id = 0; (descrip = descrip_func(plug_id)) != NULL; plug_id++) {
        tup = PyTuple_New(3);
        PyTuple_SetItem(tup, 0, PyString_FromString(libname));
        PyTuple_SetItem(tup, 1, PyString_FromString(descrip->Label));
        PyTuple_SetItem(tup, 2, PyString_FromString(descrip->Name));

        PyList_Append(list, tup);
    }
    Py_INCREF(list);
    return list;
}

static PyMethodDef PlugInfoMethods[] = {
    { "is_ladspa", is_ladspa, METH_VARARGS, "Check if object is a LADSPA DLL" },
    { "list_plugins", list_plugins, METH_VARARGS, "List plugins in object" },
    { NULL, NULL, 0, NULL } 
};


PyMODINIT_FUNC
init_pluginfo(void)
{
        Py_InitModule("_pluginfo", PlugInfoMethods);
}
