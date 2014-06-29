#! /usr/bin/env python 

APPNAME = "mfp" 
VERSION = "0.05" 
WAFTOOLS = "compiler_c gcc python glib2"

top = '.'
out = 'wafbuild'
pkgconf_libs = ["glib-2.0", "json-glib-1.0", "serd-0", "jack"]

from waflib.Configure import conf
import waflib

import os, os.path

alleggs = [] 

def eggname(pkgname, pkgver, pyver, arch): 
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

def activate_virtualenv(ctxt):
    activate = "%s/virtual/bin/activate_this.py" % ctxt.out_dir
    execfile(activate, dict(__file__=activate))

@conf
def make_virtualenv(ctxt, *args, **kwargs):
    
    if ctxt.env.USE_VIRTUALENV: 
        targetfile = ".waf-built-virtual" 
        vrule = ("cd %s && %s --system-site-packages virtual && (find %s/virtual/ -type f -o -type l > %s)"
                 % (ctxt.out_dir, ctxt.env.VIRTUALENV[0], ctxt.out_dir, targetfile))
        ctxt(rule = vrule, source = [], target = targetfile)

@conf
def fix_virtualenv(ctxt, *args, **kwargs):
    if ctxt.env.USE_VIRTUALENV: 
        targetfile = ".waf-relo-virtual" 
        cmds = [
            "cd %s" % ctxt.out_dir,
            "echo 'Making virtualenv relocatable'", 
            "%s --relocatable virtual" % ctxt.env.VIRTUALENV[0], 
            (("cat virtual/bin/activate " 
              + "| sed -e 's/^VIRTUAL_ENV=.*$/VIRTUAL_ENV=\"%s\/\"/' "
              + "> activate.edited")
              % ctxt.env.PREFIX.replace("/", "\\/")),
            "echo 'export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:%s/lib' >> activate.edited" % ctxt.env.PREFIX,
            "cp activate.edited virtual/bin/activate",
            "touch %s" % targetfile
        ]
        vrule = ' && '.join(cmds)
        print "RELOCATE: ", vrule 
        ctxt.add_group()
        ctxt(rule=vrule, source=alleggs, target=targetfile)


@waflib.TaskGen.feature("install_eggfiles")
def install_eggfiles(ctxt):
    from waflib import Utils
    bld = ctxt.bld
    srcroot = os.path.abspath(out)
    if ctxt.env.USE_VIRTUALENV: 
        srcroot += "/virtual/"
    localroot = os.path.abspath(top) + '/'

    manifestfiles = alleggs 
    if ctxt.env.USE_VIRTUALENV: 
        manifestfiles.append('.waf-built-virtual')

    for targetfile in manifestfiles:
        with open(os.path.abspath(out + "/" + targetfile), "r") as manifest: 
            instfiles = [ l.strip()[len(localroot):] for l in manifest ] 
            for i in instfiles:
                dirprefix = os.path.dirname(i[len(srcroot)-len(localroot):])
                instpath = ctxt.env.PREFIX + '/' + dirprefix
                instfile = instpath + '/' + os.path.basename(i)
                if "/bin/" in i:
                    mode = 0755
                else:
                    mode = 0644
                if os.path.islink(i):
                    bld.symlink_as(instfile , os.path.realpath(i))
                else: 
                    ifile = bld.path.find_resource(i)
                    if not ifile:
                        print "Can't find resource", i
                        continue
                    ifile.sig = Utils.h_file(ifile.abspath())

                    bld.install_files(instpath, ifile, chmod=mode)

@conf
def egg(ctxt, *args, **kwargs):
    setup_py = kwargs.get("setup", "setup.py")
    srcdir = kwargs.get("srcdir", ctxt.run_dir)
    pkgname = kwargs.get("pkgname")
    extname = kwargs.get("extname")
    pkgversion = kwargs.get("version", "") 
    arch = kwargs.get("arch")

    import site
    py_prefixes = site.PREFIXES 
    py_sitepack = site.getsitepackages()
    pkglibdir = None

    for pdir in py_sitepack:
        for pprefix in py_prefixes: 
            if pdir.startswith(pprefix):
                suffix = pdir[len(pprefix):]
                if suffix.startswith("/lib/"):
                    pkglibdir = suffix[1:]
                    break
        if pkglibdir is not None:
            break

    if pkglibdir is None:
        # fallback 
        pkglibdir = "lib/python%s/site-packages/" % ctxt.env.PYTHON_VERSION 

    if ctxt.env.USE_VIRTUALENV: 
        pkglibdir = "virtual/%s" % pkglibdir
    abs_pkglibdir = os.path.abspath(ctxt.out_dir + "/" + pkglibdir)

    srcfiles = [] 
    if extname:
        srcfiles.extend(ctxt.path.ant_glob("%s/**/*.{c,h}" % (srcdir,)))
    
    pkgeggname = srcdir.replace("/", "-")
    if pkgname: 
        srcfiles.extend(ctxt.path.ant_glob("%s/%s/**/*.py" % (srcdir, pkgname)))
        pkgeggname = eggname(pkgname, pkgversion, ctxt.env.PYTHON_VERSION, arch)
    targetfile = ".waf-built-%s" % pkgeggname

    if ctxt.env.USE_VIRTUALENV:
        prefix = ""
    else: 
        ddir = os.path.abspath(ctxt.out_dir)
        prefix = "--prefix=%s" % ddir

    if ctxt.env.DEBIAN_STYLE:
        style = "--install-layout deb"
    else:
        style = ""

    manifestfile = ctxt.out_dir + "/" + targetfile
    actions = [
        "cd %s" % os.path.abspath(srcdir),
        "mkdir -p %s" % abs_pkglibdir,
        "python %s install %s %s --record %s" % (setup_py, style, prefix, manifestfile),
        "echo ./%s >> %s/mfp.pth" % (pkgeggname, abs_pkglibdir), 
        "echo %s/mfp.pth >> %s" % (abs_pkglibdir, manifestfile)
    ]

    eggrule = ' && '.join(actions)

    if ctxt.env.USE_VIRTUALENV: 
        srcfiles.append(".waf-built-virtual")
        eggrule = (". %s/virtual/bin/activate && %s" 
                   % (os.path.abspath(ctxt.out_dir), eggrule))
    else: 
        eggrule = "mkdir -p %s && %s" % (abs_pkglibdir, eggrule)

    # ensure that eggs are build sequentially.  Updating the .pth files 
    # gets racy otherwise 
    ctxt.post_mode = waflib.Build.POST_LAZY
    ctxt.add_group()
    tgen = ctxt(rule = eggrule, source = srcfiles, target = targetfile)
    tgen.env.env = dict(os.environ)

    if targetfile not in alleggs: 
        alleggs.append(targetfile)

    if 'PYTHONPATH' in tgen.env.env:
        tgen.env.env['PYTHONPATH'] += ':' + abs_pkglibdir 
    else: 
        tgen.env.env['PYTHONPATH'] = abs_pkglibdir 


def gitversion(ctxt):
    ctxt.env.GITVERSION = VERSION + "_" + git_version()

def install_deps(ctxt): 
    ctxt.load(WAFTOOLS) 
    print 
    print "======================================="
    print "Fetching Python library dependencies..." 
    print "======================================="
    print 

    if ctxt.env.USE_VIRTUALENV: 
        virt = "virtualenv "
    else:
        virt = ""
    libs = ctxt.env.PIPLIBS_NOTFOUND 

    print " * Will install to %s%s" % (virt, ctxt.env.PREFIX)
    print " * Installing packages: %s" % ', '.join(libs) 
    print 

    installer = ctxt.env.PYTHON_INSTALLER 
    if not installer: 
        print "ERROR: no installer program (pip or easy_install) found"
        print "Install one and run ./waf configure"

    if ctxt.env.USE_VIRTUALENV: 
        env = ". %s/bin/activate && " % ctxt.env.PREFIX
        prefix = ""
    else: 
        env = ''

        if installer == "pip install":
            prefix = '--install-option="--prefix=%s"' % ctxt.env.PREFIX
        else:
            print "INSTALLER = '%s'" % installer
            prefix = '--prefix=%s' % ctxt.env.PREFIX

    for l in libs: 
        print "%s %s %s %s" % (env, ctxt.env.PYTHON_INSTALLER, prefix, l)

        ctxt.exec_command("%s %s %s %s" % (env, ctxt.env.PYTHON_INSTALLER, prefix, l))

from waflib.Build import BuildContext 
class MFPContext (BuildContext):
    fun = 'install_deps'
    cmd = 'install_deps' 

def options(opt):
    from waflib.Options import options 
    opt.load(WAFTOOLS)
    optgrp = opt.get_option_group('Configuration options')
    optgrp.add_option("--virtualenv", action="store_true", dest="USE_VIRTUALENV",
                   help="Install into a virtualenv")

    # "egg" targets race to update the .pth file.  Must build them one at a time. 
    options['jobs'] = 1

def configure(conf):
    conf.load(WAFTOOLS) 

    # Python and dev files 
    conf.check_python_version((2,7))
    conf.check_python_headers()

    # check for Debian style 
    conf.start_msg("Checking for site-packages vs. dist-packages (Debian-style)")
    debstyle = False 
    import sys 
    for d in sys.path: 
        if "dist-packages" in d:
            debstyle = True 
            break

    if debstyle: 
        conf.end_msg("dist-packages")
        conf.env.DEBIAN_STYLE = True 
    else:
        conf.end_msg("site-packages")
    
    # virtualenv and setuptools 
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

    # C libraries with pkg-config support (listed at top of file) 
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

    # pip-installable libs we just mark them as not available 
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

    # GObject bindings for libraries are mandatory 
    for l in gi_libs: 
        try:
            conf.check_python_module('gi.repository.' + l)
        except waflib.Errors.ConfigurationError, e: 
            print 
            print "FATAL: GObject language bindings for %s not installed" % l 
            print "They are packaged like 'gir1.2-${libname}-${libver}' on Debian and Ubuntu" 
            print "Try 'apt-cache search gir %s' to find the right package" % l.lower()
            print 
            raise 

    conf.env.GITVERSION = VERSION + "_" + git_version()
    print 
    print "MFP version", conf.env.GITVERSION, "configured."
    if conf.env.USE_VIRTUALENV:
        print "Will build into virtualenv", out 
    print 
               
def build(bld): 
    print "build:", bld, bld.is_install

    # only gets built if USE_VIRTUALENV is set
    bld.make_virtualenv()

    bld.egg(pkgname="mfp", version=bld.env.GITVERSION)
    bld.egg(srcdir="pluginfo", pkgname="pluginfo", arch="linux-x86_64", version="1.0")
    bld.egg(srcdir="testext", pkgname="testext", arch="linux-x86_64", version="1.0")
    bld.egg(srcdir="lib/alsaseq-0.4.1", pkgname="alsaseq", 
            extname="alsaseq", arch="linux-x86_64", version="0.4.1")
    bld.egg(srcdir="lib/pyliblo-0.9.1", extname="liblo", arch="linux-x86_64", 
            version="0.9.1")

    # must make virtualenv "relocatable" after all packages added 
    bld.fix_virtualenv() 

    bld.shlib(source=bld.path.ant_glob("mfpdsp/*.c"), 
              target="mfpdsp", 
              cflags=["-std=gnu99", "-fpic", "-g", "-D_GNU_SOURCE", "-DMFP_USE_SSE"],
              uselib = bld.env.PKGCONF_LIBS)
    
    bld.program(source="mfpdsp/main.c", target="mfpdsp/mfpdsp", 
                cflags=["-std=gnu99", "-fpic", "-g", "-D_GNU_SOURCE", "-DMFP_USE_SSE"],
                uselib = bld.env.PKGCONF_LIBS,
                use=['mfpdsp'])

    bld.add_group()
    bld(features="install_eggfiles")
