#! /usr/bin/env python 

APPNAME = "mfp" 
VERSION = "0.05" 

top = '.'
out = 'wafbuild'
WAFTOOLS = "compiler_c gcc python glib2"
pkgconf_libs = ["glib-2.0", "json-glib-1.0", "serd-0", "jack"]

from waflib.Configure import conf
import waflib

import os, os.path

def eggname(pkgname, pkgver, pyver, arch): 
    print "eggname:", pkgname, pkgver, pyver, arch
    if arch:
        archstr = "-%s" % arch
    else:
        archstr = "" 
    return "%s-%s-py%s%s.egg" % (pkgname, pkgver, pyver, archstr)

def shcall(cmdline):
    # print " --> %s" % (cmdline,)
    from subprocess import Popen,PIPE
    return Popen(['/bin/sh', '-c', cmdline], stdout=PIPE).communicate()[0]

def git_version(): 
    vers = shcall("git show --oneline").split('\n')[0].split(' ')[0]
    return 'git_' + vers.strip()

@conf
def egg(ctxt, *args, **kwargs):
    setup_py = kwargs.get("setup", "setup.py")
    srcdir = kwargs.get("srcdir", ctxt.run_dir)
    pkgname = kwargs.get("pkgname")
    extname = kwargs.get("extname")
    pkgversion = kwargs.get("version", "") 
    arch = kwargs.get("arch")

    pkglibdir = "lib/python%s/site-packages/" % ctxt.env.PYTHON_VERSION 
    if ctxt.env.USE_VIRTUALENV: 
        pkglibdir = "virtual/" + pkglibdir
    abs_pkglibdir = os.path.abspath(ctxt.out_dir + "/" + pkglibdir)

    srcfiles = [] 
    if extname:
        srcfiles.extend(ctxt.path.ant_glob("%s/**/*.{c,h}" % (srcdir,)))
        targetfile=pkglibdir + extname + ".so" 

    if pkgname: 
        srcfiles.extend(ctxt.path.ant_glob("%s/%s/**/*.py" % (srcdir, pkgname)))
        targetfile = (pkglibdir 
                      + eggname(pkgname, pkgversion, ctxt.env.PYTHON_VERSION, arch) 
                      + "/EGG-INFO/PKG-INFO")

    if ctxt.env.USE_VIRTUALENV:
        prefix = ""
    else: 
        prefix = "--prefix %s" %  os.path.abspath(ctxt.out_dir)

    eggrule = "cd %s && python %s install %s" % (os.path.abspath(srcdir), setup_py, prefix)
    #eggrule = "type -p python"
    if ctxt.env.USE_VIRTUALENV: 
        eggrule = (". %s/virtual/bin/activate && %s" 
                   % (os.path.abspath(ctxt.out_dir), eggrule))
    print "egg:", eggrule
    #print "egg: ctxt vars: run=%s, cwd=%s" % (ctxt.run_dir, os.getcwd())
    #print "egg: rule", eggrule
    #print "egg: target file ", targetfile   
    #print "egg: source files ", srcfiles 

    tgen = ctxt(rule = eggrule, source = srcfiles, target = targetfile)
    tgen.env.env = dict(os.environ)
    if 'PYTHONPATH' in tgen.env.env:
        tgen.env.env['PYTHONPATH'] += ':' + abs_pkglibdir 
    else: 
        tgen.env.env['PYTHONPATH'] = abs_pkglibdir 

def ensure_virtualenv(ctxt):
    if ctxt.env.USE_VIRTUALENV: 
        if not ctxt.env.VIRTUALENV_CREATED: 
            print "Creating virtualenv for build in %s/virtual" % ctxt.out_dir
            shcall("cd %s && %s --system-site-packages virtual" 
                   % (ctxt.out_dir, ctxt.env.VIRTUALENV[0], ))
            ctxt.env.VIRTUALENV_CREATED = True 
        print "Activating virtualenv for build" 
        activate = "%s/virtual/bin/activate_this.py" % ctxt.out_dir
        execfile(activate, dict(__file__=activate))
    else: 
        print "*** no virtualenv in config"
    
def gitversion(ctxt):
    print "gitversion:", VERSION + "_" + git_version()
    ctxt.env.GITVERSION = VERSION + "_" + git_version()

def fetchdeps(ctxt): 
    ctxt.load(WAFTOOLS) 
    ensure_virtualenv(ctxt) 
    print "Fetching Python library dependencies..." 
    libs = ctxt.env.PIPLIBS_NOTFOUND 
    installer = ctxt.env.PYTHON_INSTALLER 
    if not installer: 
        print "ERROR: no installer program (pip or easy_install) found"
        print "Install one and run ./waf configure"

    for l in libs: 
        ctxt.exec_command("%s %s" % (ctxt.env.PYTHON_INSTALLER, l))

from waflib.Build import BuildContext 
class MFPContext (BuildContext):
    fun = 'fetchdeps'
    cmd = 'fetchdeps' 

def options(opt):
    opt.load(WAFTOOLS)
    optgrp = opt.get_option_group('Configuration options')
    optgrp.add_option("--virtualenv", action="store_true", dest="USE_VIRTUALENV",
                   help="Install into a virtualenv")

def configure(conf):
    conf.load(WAFTOOLS) 
    conf.check_python_version((2,7))
    conf.check_python_headers()

    installer = None 
    if conf.options.USE_VIRTUALENV: 
        conf.env.USE_VIRTUALENV = True 
        conf.find_program("virtualenv")
        installer = "pip install"
    else: 
        try:
            conf.find_program("pip")
            installer = "pip install"
        except waflib.Errors.ConfigurationError, e: 
            pass 

        if installer is None:
            conf.find_program("easy_install")
            installer = "easy_install"
    conf.env.PYTHON_INSTALLER = installer 

    uselibs = [] 

    for l in pkgconf_libs: 
        uname = l.split("-")[0].upper()
        conf.check_cfg(package=l, args="--libs --cflags", 
                       uselib_store=uname)
        uselibs.append(uname)
    conf.env.PKGCONF_LIBS = uselibs 

    pip_libs = [ "posix_ipc", "simplejson", ("cairo", "pycairo"), "numpy", "nose" ]
    gi_libs = [ "Clutter", "GObject", "Gtk", "Gdk", "GtkClutter", "Pango"]
    
    pip_notfound = [] 
    bindings_notfound = [] 

    for l in pip_libs: 
        if isinstance(l, tuple):
            modulename, pipname = l 
        else: 
            modulename = pipname = l 

        try:
            conf.check_python_module(modulename)
        except waflib.Errors.ConfigurationError, e: 
            pip_notfound.append(pipname)

    conf.env.PIPLIBS_NOTFOUND = pip_notfound 

    for l in gi_libs: 
        if not conf.check_python_module('gi.repository.' + l):
            bindings_notfound.append(l)

    conf.env.GITVERSION = VERSION + "_" + git_version()
    print "MFP version", conf.env.GITVERSION, "configured."


               
def build(bld): 
    bld.add_pre_fun(ensure_virtualenv)

    bld.egg(pkgname="mfp", version=bld.env.GITVERSION)
    bld.egg(srcdir="testext", pkgname="testext", arch="linux-x86_64", version="1.0")
    bld.egg(srcdir="lib/alsaseq-0.4.1", pkgname="alsaseq", 
            extname="alsaseq", arch="linux-x86_64", version="0.4.1")
    bld.egg(srcdir="lib/pyliblo-0.9.1", extname="liblo", arch="linux-x86_64", 
            version="0.9.1")

    bld.shlib(source=bld.path.ant_glob("mfpdsp/*.c"), 
              target="mfpdsp", 
              cflags=["-std=gnu99", "-fpic", "-g", "-D_GNU_SOURCE", "-DMFP_USE_SSE"],
              uselib = bld.env.PKGCONF_LIBS)
    
    bld.program(source="mfpdsp/main.c", target="mfpdsp/mfpdsp", 
                cflags=["-std=gnu99", "-fpic", "-g", "-D_GNU_SOURCE", "-DMFP_USE_SSE"],
                uselib = bld.env.PKGCONF_LIBS,
                use=['mfpdsp'])


