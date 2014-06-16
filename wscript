#! /usr/bin/env python 

APPNAME = "mfp" 
VERSION = "0.05" 

top = '.'
out = 'wafbuild'
TOOLS = "compiler_c gcc python glib2"

from waflib.TaskGen import feature 
from waflib.Configure import conf

import os, os.path

def eggname(pkgname, pkgver, pyver, arch): 
    if arch:
        archstr = "-%s" % arch
    else:
        archstr = "" 
    return "%s-%s-py%s%s.egg" % (pkgname, pkgver, pyver, archstr)

@conf
def egg(ctxt, *args, **kwargs):
    print "egg:", ctxt, args, kwargs
    setup_py = kwargs.get("setup", "setup.py")
    srcdir = kwargs.get("srcdir", ctxt.run_dir)
    pkgname = kwargs.get("pkgname")
    extname = kwargs.get("extname")
    pkgversion = kwargs.get("version", "") 
    arch = kwargs.get("arch")

    pkglibdir = "lib/python%s/site-packages/" % ctxt.env.PYTHON_VERSION 
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

    eggrule = ("cd %s && python %s install --prefix %s" 
            % (os.path.abspath(srcdir), setup_py, os.path.abspath(ctxt.out_dir)))
    print "egg: ctxt vars: run=%s, cwd=%s" % (ctxt.run_dir, os.getcwd())
    print "egg: rule", eggrule
    print "egg: target file ", targetfile   
    print "egg: source files ", srcfiles 

    tgen = ctxt(rule = eggrule, source = srcfiles, target = targetfile)
    tgen.env.env = dict(os.environ)
    if 'PYTHONPATH' in tgen.env.env:
        tgen.env.env['PYTHONPATH'] += ':' + abs_pkglibdir 
    else: 
        tgen.env.env['PYTHONPATH'] = abs_pkglibdir 


def shcall(cmdline):
    from subprocess import Popen,PIPE
    return Popen(cmdline.split(), stdout=PIPE).communicate()[0]

def git_version(): 
    vers = shcall("git show --oneline").split('\n')[0].split(' ')[0]
    return 'git_' + vers.strip()

@conf
def gitversion(ctxt):
    ctxt.env['GITVERSION'] = VERSION + "_" + git_version()

def options(opt):
    print "** options"
    opt.load(TOOLS)
    opt.add_option("--virtualenv", default=True, 
                   help="Install into a virtualenv")


def configure(conf):
    print "** configure"

    pkgconf_libs = "glib-2.0 json-glib-1.0 serd-0"

    conf.load(TOOLS) 
    conf.check_python_version((2,7))
    conf.check_python_headers()
    uselibs = [] 

    for l in pkgconf_libs.split(): 
        uname = l.split("-")[0].upper()
        conf.check_cfg(package=l, args="--libs --cflags", 
                       uselib_store=uname)
        uselibs.append(uname)
    conf.env.PKGCONF_LIBS = uselibs 

def build(bld): 
    print "** build", bld.env.PKGCONF_LIBS

    bld.gitversion()
    bld.egg(pkgname="mfp", version=bld.env.GITVERSION)
    bld.egg(srcdir="testext", pkgname="testext", arch="linux-x86_64", version="1.0")
    bld.egg(srcdir="lib/alsaseq-0.4.1", pkgname="alsaseq", 
            extname="alsaseq", arch="linux-x86_64", version="0.4.1")
    bld.egg(srcdir="lib/pyliblo-0.9.1", extname="liblo", arch="linux-x86_64", 
            version="0.9.1")

    bld(features="c cshlib", 
        source=bld.path.ant_glob("mfpdsp/*.c"), 
        target="libmfpdsp.so", 
        cflags=["-std=gnu99", "-fpic", "-g", "-D_GNU_SOURCE", "-DMFP_USE_SSE"],
        uselib = bld.env.PKGCONF_LIBS)
              
    #bld.recurse("pluginfo")
    #bld.recurse("lib") 
    #bld.recurse("mfpdsp")


