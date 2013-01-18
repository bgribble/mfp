
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
        tup = PyTuple_New(4);
        PyTuple_SetItem(tup, 0, PyString_FromString(libname));
        PyTuple_SetItem(tup, 1, PyInt_FromLong(plug_id));
        PyTuple_SetItem(tup, 2, PyString_FromString(descrip->Label));
        PyTuple_SetItem(tup, 3, PyString_FromString(descrip->Name));

        PyList_Append(list, tup);
    }
    dlclose(dlfile);

    Py_INCREF(list);
    return list;
}

static PyObject * 
describe_plugin(PyObject * mod, PyObject * args) 
{
    char * libname = NULL;
    int plug_id;
    int port_num;
    void * dlfile;
    LADSPA_Descriptor * (* descrip_func)(unsigned long);
    LADSPA_Descriptor * descrip;
    PyObject * dict = NULL; 
    PyObject * ports = NULL;
    PyObject * portinfo = NULL;
    PyArg_ParseTuple(args, "si", &libname, &plug_id);
    
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
    
    descrip = descrip_func(plug_id);
    if (descrip == NULL) {
        Py_INCREF(Py_None);
        return Py_None;
    }
    dict = PyDict_New();
    PyDict_SetItemString(dict, "lib_name", PyString_FromString(libname));
    PyDict_SetItemString(dict, "lib_type", PyString_FromString("ladspa"));
    PyDict_SetItemString(dict, "lib_index", PyInt_FromLong(plug_id));
    PyDict_SetItemString(dict, "unique_id", PyInt_FromLong(descrip->UniqueID));
    PyDict_SetItemString(dict, "properties", PyInt_FromLong(descrip->Properties));
    PyDict_SetItemString(dict, "label", PyString_FromString(descrip->Label));
    PyDict_SetItemString(dict, "name", PyString_FromString(descrip->Name));
    PyDict_SetItemString(dict, "maker", PyString_FromString(descrip->Maker));
    PyDict_SetItemString(dict, "copyright", PyString_FromString(descrip->Copyright));

    ports = PyList_New(descrip->PortCount);

    for(port_num=0; port_num < descrip->PortCount; port_num++) {
        portinfo = PyDict_New();
        PyDict_SetItemString(portinfo, "descriptor", 
                             PyInt_FromLong(descrip->PortDescriptors[port_num]));
        PyDict_SetItemString(portinfo, "name", 
                             PyString_FromString(descrip->PortNames[port_num]));
        PyDict_SetItemString(portinfo, "hint_type",
                             PyInt_FromLong(descrip->PortRangeHints[port_num].HintDescriptor));
        PyDict_SetItemString(portinfo, "hint_lower",
                             PyFloat_FromDouble(descrip->PortRangeHints[port_num].LowerBound));
        PyDict_SetItemString(portinfo, "hint_upper",
                             PyFloat_FromDouble(descrip->PortRangeHints[port_num].UpperBound));

        PyList_SetItem(ports, port_num, portinfo);
    }
    PyDict_SetItemString(dict, "ports", ports);

    dlclose(dlfile);
    Py_INCREF(dict);
    return dict;
}


#define ADD2DICT(P) PyDict_SetItemString(dict, #P, PyInt_FromLong(P)) 

static PyObject * 
get_constants(PyObject * mod, PyObject * args) 
{
    PyObject * dict = PyDict_New();

    ADD2DICT(LADSPA_PROPERTY_REALTIME);
    ADD2DICT(LADSPA_PROPERTY_INPLACE_BROKEN);
    ADD2DICT(LADSPA_PROPERTY_HARD_RT_CAPABLE);
    ADD2DICT(LADSPA_PORT_INPUT);
    ADD2DICT(LADSPA_PORT_OUTPUT);
    ADD2DICT(LADSPA_PORT_CONTROL);
    ADD2DICT(LADSPA_PORT_AUDIO);
    ADD2DICT(LADSPA_HINT_BOUNDED_BELOW);
    ADD2DICT(LADSPA_HINT_BOUNDED_ABOVE);
    ADD2DICT(LADSPA_HINT_TOGGLED);
    ADD2DICT(LADSPA_HINT_SAMPLE_RATE);
    ADD2DICT(LADSPA_HINT_LOGARITHMIC);
    ADD2DICT(LADSPA_HINT_INTEGER);
    ADD2DICT(LADSPA_HINT_DEFAULT_NONE);
    ADD2DICT(LADSPA_HINT_DEFAULT_MINIMUM);
    ADD2DICT(LADSPA_HINT_DEFAULT_LOW);
    ADD2DICT(LADSPA_HINT_DEFAULT_MIDDLE);
    ADD2DICT(LADSPA_HINT_DEFAULT_HIGH);
    ADD2DICT(LADSPA_HINT_DEFAULT_MAXIMUM);
    ADD2DICT(LADSPA_HINT_DEFAULT_0);
    ADD2DICT(LADSPA_HINT_DEFAULT_1);
    ADD2DICT(LADSPA_HINT_DEFAULT_100);
    ADD2DICT(LADSPA_HINT_DEFAULT_440);

    Py_INCREF(dict);
    return dict;
}


static PyMethodDef PlugInfoMethods[] = {
    { "is_ladspa", is_ladspa, METH_VARARGS, "Check if object is a LADSPA DLL" },
    { "list_plugins", list_plugins, METH_VARARGS, "List plugins in object" },
    { "describe_plugin", describe_plugin, METH_VARARGS, "Describe a single plugin" },
    { "get_constants", get_constants, METH_VARARGS, "Get compile-time LADSPA constants"},
    { NULL, NULL, 0, NULL } 
};


PyMODINIT_FUNC
init_pluginfo(void)
{
        Py_InitModule("_pluginfo", PlugInfoMethods);
}
