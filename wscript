#! /usr/bin/env python

from __future__ import print_function

APPNAME = "mfp"
VERSION = "0.05"
WAFTOOLS = "compiler_c gcc python glib2"

top = '.'
out = 'wafbuild'
pkgconf_libs = ["glib-2.0", "json-glib-1.0", "serd-0", "jack", "liblo"]

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

def git_version():
    import subprocess

    vers = subprocess.check_output(['git', 'rev-parse', '--verify', '--short', 'HEAD'])
    if not isinstance(vers, str):
        vers = vers.decode()

    vers = vers.strip()

    return 'git_' + format(vers)

@conf
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
            "rm -rf virtual/local",
            (("cat virtual/bin/activate "
              + "| sed -e 's/^VIRTUAL_ENV=.*$/VIRTUAL_ENV=\"%s\/\"/' "
              + "> activate.edited")
              % ctxt.env.PREFIX.replace("/", "\\/")),
            "echo 'if echo $LD_LIBRARY_PATH | grep -vq :%s/lib:' >> activate.edited" % ctxt.env.PREFIX,
            "echo 'then export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:%s/lib:' >> activate.edited" % ctxt.env.PREFIX,
            "echo 'fi' >> activate.edited",
            "mv activate.edited virtual/bin/activate",
            "touch %s" % targetfile
        ]
        vrule = ' && '.join(cmds)
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

    symlinks = []
    for targetfile in manifestfiles:
        with open(os.path.abspath(out + "/" + targetfile), "r") as manifest:
            instfiles = [ l.strip()[len(localroot):] for l in manifest ]
            for i in instfiles:
                dirprefix = os.path.dirname(i[len(srcroot)-len(localroot):])
                instpath = ctxt.env.PREFIX + '/' + dirprefix
                instfile = instpath + '/' + os.path.basename(i)
                if "/bin/" in i:
                    mode = 0o755
                else:
                    mode = 0o644
                if os.path.islink(i):
                    bld.symlink_as(instfile, os.path.realpath(i))
                    symlinks.append(i)
                else:
                    file_symlinked = False
                    for prepath in symlinks:
                        if os.path.dirname(i).startswith(prepath):
                            print("File under symlink:", i, prepath)
                            file_symlinked = False
                            break
                    if file_symlinked:
                        continue

                    ifile = bld.path.find_resource(i)
                    if not ifile:
                        print("Can't find resource", i)
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

    pkglibdir = ctxt.env.PYTHON_PKGLIBDIR

    if ctxt.env.USE_VIRTUALENV:
        pkglibdir = "virtual/%s" % pkglibdir
    abs_pkglibdir = os.path.abspath(ctxt.out_dir + "/" + pkglibdir)

    srcfiles = []
    if extname:
        srcfiles.extend(ctxt.path.ant_glob("%s/**/*.{c,h}" % (pkgname,)))

    pkgeggname = srcdir.replace("/", "-")
    if pkgname:
        srcfiles.extend(ctxt.path.ant_glob("%s/**/*.py" % pkgname))
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
    print()
    print("=======================================")
    print("Fetching Python library dependencies...")
    print("=======================================")
    print()

    if ctxt.env.USE_VIRTUALENV:
        virt = "virtualenv "
    else:
        virt = ""
    libs = ctxt.env.PIPLIBS_NOTFOUND

    print(" * Will install to %s%s" % (virt, ctxt.env.PREFIX))
    print(" * Installing packages: %s" % ', '.join(libs))
    print()

    installer = ctxt.env.PYTHON_INSTALLER
    if not installer:
        print("ERROR: no installer program (pip or easy_install) found")
        print("Install one and run ./waf configure")

    if ctxt.env.USE_VIRTUALENV:
        env = ". %s/bin/activate && " % ctxt.env.PREFIX
        prefix = ""
    else:
        env = ''

        if installer == "pip install":
            prefix = '--install-option="--prefix=%s"' % ctxt.env.PREFIX
        else:
            print("INSTALLER = '%s'" % installer)
            prefix = '--prefix=%s' % ctxt.env.PREFIX

    for l in libs:
        print("%s %s %s %s" % (env, ctxt.env.PYTHON_INSTALLER, prefix, l))

        ctxt.exec_command("%s %s %s %s" % (env, ctxt.env.PYTHON_INSTALLER, prefix, l))

from waflib.Build import BuildContext, CleanContext, CFG_FILES

class MFPBuildContext (BuildContext):
    fun = 'install_deps'
    cmd = 'install_deps'

class MFPCleanContext (CleanContext):
    cmd = 'clean'

    def execute(self):
        self.restore()
        if not self.all_envs:
            self.load_envs()

        self.recurse([self.run_dir])
        try:
            self.clean()
        finally:
            self.store()

    def clean(self):
        if self.bldnode != self.srcnode:
            # would lead to a disaster if top == out
            lst=[]
            symlinks = []
            for e in self.all_envs.values():
                exclfiles = '.lock* *conf_check_*/** config.log c4che/*'
                allfiles = self.bldnode.ant_glob('**/*', dir=True, excl=exclfiles, quiet=True)
                allfiles.sort(key=lambda n: n.abspath())
                lst.extend(self.root.find_or_declare(f) for f in e[CFG_FILES])

                for n in allfiles:
                    if n in lst:
                        continue
                    else:
                        is_symlinked = False
                        for link in symlinks:
                            if os.path.dirname(n.abspath()).startswith(link):
                                is_symlinked = True
                                break
                        if is_symlinked:
                            continue
                    if os.path.islink(n.abspath()) and hasattr(n, 'children'):
                        symlinks.append(n.abspath())
                        delattr(n, "children")
                    elif os.path.isdir(n.abspath()):
                        continue
                    n.delete()
                    self.root.children = {}

        for v in ['node_deps', 'task_sigs', 'raw_deps']:
            setattr(self, v, {})


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
        except waflib.Errors.ConfigurationError as e:
            pass

        if installer is None:
            conf.find_program("easy_install")
            installer = "easy_install"
    conf.env.PYTHON_INSTALLER = installer

    # python lib-install prefix
    import site, sys
    py_prefixes = site.PREFIXES
    py_sitepack = sys.path
    pkglibdir = None
    conf.start_msg("Finding package lib install path")
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
    conf.end_msg(pkglibdir)
    conf.env.PYTHON_PKGLIBDIR = pkglibdir

    # C libraries with pkg-config support (listed at top of file)
    uselibs = []

    for l in pkgconf_libs:
        uname = l.split("-")[0].upper()
        conf.check_cfg(package=l, args="--libs --cflags",
                       uselib_store=uname)
        uselibs.append(uname)
    conf.env.PKGCONF_LIBS = uselibs

    pip_libs = ["posix_ipc", "simplejson", ("cairo", "pycairo"), "numpy", 
                "nose", "yappi", "pyliblo" ]
    gi_libs = [ "Clutter", "GObject", "Gtk", "Gdk", "GLib", "GtkClutter", "Pango"]

    pip_notfound = []

    # LADSPA header
    conf.check_cc(header_name="ladspa.h")

    # pip-installable libs we just mark them as not available
    for l in pip_libs:
        if isinstance(l, tuple):
            modulename, pipname = l
        else:
            modulename = pipname = l

        try:
            conf.check_python_module(modulename)
        except waflib.Errors.ConfigurationError as e:
            pip_notfound.append(pipname)

    conf.env.PIPLIBS_NOTFOUND = pip_notfound

    # GObject bindings for libraries are mandatory
    for l in gi_libs:
        try:
            conf.check_python_module('gi.repository.' + l)
        except waflib.Errors.ConfigurationError as e:
            print()
            print("FATAL: GObject language bindings for %s not installed" % l)
            print("They are packaged like 'gir1.2-${libname}-${libver}' on Debian and Ubuntu")
            print("Try 'apt-cache search gir %s' to find the right package" % l.lower())
            print()
            raise

    conf.env.GITVERSION = VERSION + "_" + git_version()

    print()
    print("MFP version", conf.env.GITVERSION, "configured.")
    if conf.env.USE_VIRTUALENV:
        print("Will build into virtualenv", conf.env.PREFIX)
    print()

def build(bld):
    # only gets built if USE_VIRTUALENV is set
    bld.make_virtualenv()
    bld.activate_virtualenv()

    bld.egg(pkgname="mfp", version=bld.env.GITVERSION)
    bld.egg(srcdir="pluginfo", pkgname="pluginfo", arch="linux-x86_64", version="1.0")
    bld.egg(srcdir="testext", pkgname="testext", arch="linux-x86_64", version="1.0")
    bld.egg(srcdir="lib/alsaseq-0.4.1", pkgname="alsaseq",
            extname="alsaseq", arch="linux-x86_64", version="0.4.1")

    # must make virtualenv "relocatable" after all packages added
    bld.fix_virtualenv()

    bld.shlib(source=bld.path.ant_glob("mfpdsp/*.c"),
              target="mfpdsp",
              cflags=["-std=gnu99", "-fpic", "-g", "-O2", "-D_GNU_SOURCE", "-DMFP_USE_SSE"],
              uselib = bld.env.PKGCONF_LIBS)

    bld.program(source="mfpdsp/main.c", target="mfpdsp/mfpdsp",
                cflags=["-std=gnu99", "-fpic", "-g", "-O2", "-D_GNU_SOURCE", "-DMFP_USE_SSE"],
                uselib = bld.env.PKGCONF_LIBS,
                use=['mfpdsp'])

    bld.add_group()
    bld(features="install_eggfiles")
