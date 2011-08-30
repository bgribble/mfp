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

	void * dlfile;
	int (* dlfunc)(void);
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
		dlfunc = dlsym(dlfile, setup);
		if (dlfunc == NULL) {
			printf("testext ERROR: Could not look up setup symbol %s (error: %s)\n", setup, dlerror());
			dlclose(dlfile);
			Py_IncRef(Py_None);
			return Py_None;
		}

		/* run setup */
		dlfunc();
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
	testres = dlfunc();

	if(strcmp(teardown, "None")) {
		dlfunc = dlsym(dlfile, teardown);
		if (dlfunc == NULL) {
			printf("testext ERROR: Could not look up teardown symbol %s (error: %s)\n", teardown, dlerror());
			dlclose(dlfile);
			Py_IncRef(Py_None);
			return Py_None;
		}

		/* run setup */
		dlfunc();
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

static PyMethodDef TestExtExtMethods[] = {
	{"run_dl_test", run_dl_test, METH_VARARGS, "Run a named test from a named dynamic library" },
	{ NULL, NULL, 0, NULL }
};

PyMODINIT_FUNC
init_testext(void) 
{

	Py_InitModule("_testext", TestExtExtMethods);
}
