#! /usr/bin/env python 

APPNAME = "mfp" 
VERSION = "0.05" 

top = '.'
out = 'wafbuild'
TOOLS = "compiler_c gcc python glib2"

from waflib.TaskGen import feature 
from waflib.Configure import conf

import os, os.path

def eggname(pkgname, pkgver, pyver): 
    return "%s-%s-py%s.egg" % (pkgname, pkgver, pyver)

@conf
def egg(ctxt, *args, **kwargs):
    print "egg:", ctxt, args, kwargs
    setup_py = kwargs.get("setup", "setup.py")
    srcdir = kwargs.get("srcdir")
    pkgname = kwargs.get("pkgname")
    pkgversion = kwargs.get("version", "") 

    srcfiles = ctxt.path.ant_glob("%s/**/*.py" % srcdir)
    setupfile = os.path.abspath(top + "/" + setup_py)

    pkglibdir = "lib/python%s/site-packages/" % ctxt.env.PYTHON_VERSION 
    abs_pkglibdir = os.path.abspath(out + "/" + pkglibdir)
    tgen = ctxt(rule = "cd %s && python %s install --prefix %s" 
                        % (os.path.abspath(top), setupfile, os.path.abspath(out)),
                source = srcfiles, 
                target = (pkglibdir 
                          + eggname(pkgname, pkgversion, ctxt.env.PYTHON_VERSION) 
                          + "/EGG-INFO/PKG-INFO"))
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

    #opt.recurse("testext")
    #opt.recurse("pluginfo")
    #opt.recurse("lib") 
    #opt.recurse("mfpdsp")
    

def configure(conf):
    print "** configure"
    conf.load(TOOLS) 
    conf.check_python_version((2,7))
    conf.check_python_headers()

    #conf.recurse("testext")
    #conf.recurse("pluginfo")
    #conf.recurse("lib") 
    #conf.recurse("mfpdsp")


def build(bld): 
    print "** build"

    bld.gitversion()
    bld.egg(setup="setup.py", srcdir="mfp", pkgname="mfp", 
            version=bld.env['GITVERSION'])

    #bld.recurse("testext")
    #bld.recurse("pluginfo")
    #bld.recurse("lib") 
    #bld.recurse("mfpdsp")


