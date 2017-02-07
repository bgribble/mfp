/*
 * _testext.c -- Python extension to help running C tests
 *
 * Copyright (c) 2011 Bill Gribble <grib@billgribble.com>
 */

#include <Python.h>
#include <stdio.h>
#include <signal.h>
#include <execinfo.h>
#include <dlfcn.h>
#include <bytesobject.h>

int error_happened = 0;

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

/*
 * run_dl_test(String libname, String funcname)
 * intended to be called from the ExtTestCase run method
 *
 * returns True for pass, False for fail, None for error
 * Catches all signals and prints a backtrace (returning None if any signal)
 *
 */

PyObject * 
run_dl_test(PyObject * mod, PyObject * args)
{
    char * libname = NULL;
    char * funcname = NULL;
    char * setup = NULL;
    char * teardown = NULL;
    void * setup_ret = NULL;
    void * dlfile;
    void * (* setupfunc)(void);
    int (* dlfunc)(void *);
    int testres;
    struct sigaction sa;
    PyObject * pyres;

    error_happened = 0;

    /* grab lib and symbol name */
    PyArg_ParseTuple(args, "ssss", &libname, &funcname, &setup, &teardown);

    if (libname == NULL || funcname == NULL) {
        printf("testext ERROR: Library (%s) or function (%s) name could not be parsed", libname, funcname);
        Py_IncRef(Py_None);
        return Py_None;
    }

    /* install signal handlers */
    sa.sa_flags = SA_SIGINFO;
    sigemptyset(&sa.sa_mask);
    sa.sa_sigaction = sigsegv_handler;
    if (sigaction(SIGSEGV, &sa, NULL) == -1) {
        printf("testext ERROR: could not install SIGSEGV handler, exiting\n");
        Py_IncRef(Py_None);
        return Py_None;
    }
    
    /* look up test */
    dlfile = dlopen(libname, RTLD_NOW);
    if (dlfile == NULL) {
        printf("testext ERROR: Could not dlopen library %s (error: %s)\n", libname, dlerror());
        Py_IncRef(Py_None);
        return Py_None;
    }

    
    if(strcmp(setup, "None")) {
        setupfunc = dlsym(dlfile, setup);
        if (setupfunc == NULL) {
            printf("testext ERROR: Could not look up setup symbol %s (error: %s)\n", setup, dlerror());
            dlclose(dlfile);
            Py_IncRef(Py_None);
            return Py_None;
        }

        /* run setup */
        setup_ret = setupfunc();
    }

    /* now the real test */
    dlfunc = dlsym(dlfile, funcname);
    if (dlfunc == NULL) {
        printf("testext ERROR: Could not look up symbol %s (error: %s)\n", funcname, dlerror());
        dlclose(dlfile);
        Py_IncRef(Py_None);
        return Py_None;
    }

    /* run test */
    testres = dlfunc(setup_ret);

    if(strcmp(teardown, "None")) {
        dlfunc = dlsym(dlfile, teardown);
        if (dlfunc == NULL) {
            printf("testext ERROR: Could not look up teardown symbol %s (error: %s)\n", teardown, dlerror());
            dlclose(dlfile);
            Py_IncRef(Py_None);
            return Py_None;
        }

        /* run teardown */
        dlfunc(setup_ret);
    }

    /* clean up */
    dlclose(dlfile);

    if (error_happened)
        pyres = Py_None;
    else if (testres) 
        pyres = Py_True;
    else
        pyres = Py_False;

    Py_IncRef(pyres);
    return pyres;

}

static PyMethodDef TestExtMethods[] = {
    {"run_dl_test", run_dl_test, METH_VARARGS, "Run a named test from a named dynamic library" },
    { NULL, NULL, 0, NULL }
};


/* the following init code mostly copied from 
 * https://docs.python.org/2/howto/cporting.html */

struct module_state {
    PyObject *error;
};

#if PY_MAJOR_VERSION >= 3
#define GETSTATE(m) ((struct module_state*)PyModule_GetState(m))
#else
#define GETSTATE(m) (&_state)
static struct module_state _state;
#endif



#if PY_MAJOR_VERSION >= 3

static int TestExtTraverse(PyObject *m, visitproc visit, void *arg) {
    Py_VISIT(GETSTATE(m)->error);
    return 0;
}

static int TestExtClear(PyObject *m) {
    Py_CLEAR(GETSTATE(m)->error);
    return 0;
}


static struct PyModuleDef moduledef = {
        PyModuleDef_HEAD_INIT,
        "_testext",
        NULL,
        sizeof(struct module_state),
        TestExtMethods,
        NULL,
        TestExtTraverse,
        TestExtClear,
        NULL
};

#define INITERROR return NULL
PyMODINIT_FUNC
PyInit__testext(void)

#else  /* PY_MAJOR_VERSION < 3 */
#define INITERROR return
PyMODINIT_FUNC
init_testext(void)
#endif

{
#if PY_MAJOR_VERSION >= 3
    PyObject *module = PyModule_Create(&moduledef);
#else
    PYObject *module = Py_InitModule("_testext", TestExtMethods);
#endif

    if (module == NULL)
        INITERROR;
    struct module_state *st = GETSTATE(module);

    st->error = PyErr_NewException("_testext.Error", NULL, NULL);
    if (st->error == NULL) {
        Py_DECREF(module);
        INITERROR;
    }

#if PY_MAJOR_VERSION >= 3
    return module;
#endif
}




