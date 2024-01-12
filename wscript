#! /usr/bin/env python3

from __future__ import print_function

from waflib.Configure import conf
from waflib.Build import BuildContext, InstallContext, CleanContext, CFG_FILES
import waflib

import os
import os.path

APPNAME = "mfp"
VERSION = "0.6"
WAFTOOLS = "compiler_c gcc python glib2"

top = '.'
out = 'wafbuild'
pkgconf_libs = ["glib-2.0", "json-glib-1.0", "serd-0", "jack", "liblo", "lv2", "libprotobuf-c"]


allwheels = []
allwheeltargets = []


def wheelname(pkgname, pkgver, pyver, arch):
    if arch:
        archstr = "-%s" % arch
    else:
        archstr = "-none-any"
    return "%s-%s-%s%s.whl" % (pkgname, pkgver, pyver, archstr)


def git_version():
    import subprocess

    vers = subprocess.check_output(['git', 'rev-parse', '--verify', '--short', 'HEAD'])
    if not isinstance(vers, str):
        vers = vers.decode()

    vers = vers.strip()

    return str(int(vers, 16))


def activate_virtualenv(ctxt):
    activate = "%s/virtual/bin/activate_this.py" % ctxt.out_dir
    exec(open(activate).read())


@conf
def make_virtualenv(ctxt, *args, **kwargs):
    if ctxt.env.USE_VIRTUALENV:
        python_name = ctxt.env.PYTHON[0].split('/')[-1]
        targetfile = ".waf-built-virtual"
        vrule = ' && '.join([
            f"cd {ctxt.out_dir}",
            f"{ctxt.env.VIRTUALENV[0]} -p {python_name} --system-site-packages virtual",
            f"(find {ctxt.out_dir}/virtual/ -type f -o -type l > {targetfile})",
            "cp virtual/bin/activate virtual/bin/activate.orig"
        ])
        ctxt(rule=vrule, target=targetfile, shell=True)


@conf
def fix_virtualenv(ctxt, *args, **kwargs):
    if ctxt.env.USE_VIRTUALENV:
        targetfile = ".waf-relo-virtual"
        python_name = ctxt.env.PYTHON[0].split('/')[-1]
        cmds = [
            "cd %s" % ctxt.out_dir,
            "echo 'Making virtualenv relocatable'",
            "%s -p %s --system-site-packages virtual" % (
                ctxt.env.VIRTUALENV[0], python_name
            ),
            "rm -rf virtual/local",
            ((
                "cat virtual/bin/activate "
                + "| sed -e 's/^VIRTUAL_ENV=.*$/VIRTUAL_ENV=\"%s\\/\"/' "
                + "> activate.edited"
            ) % ctxt.env.PREFIX.replace("/", "\\/")),
            "echo 'if echo $LD_LIBRARY_PATH | grep -vq :%s/lib64:' >> activate.edited" % ctxt.env.PREFIX,
            "echo 'then export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:%s/lib64:' >> activate.edited" % ctxt.env.PREFIX,
            "echo 'fi' >> activate.edited",
            "mv activate.edited virtual/bin/activate",
            "touch %s" % targetfile
        ]
        vrule = ' && '.join(cmds)
        ctxt.add_group()
        ctxt(rule=vrule, source=allwheeltargets, target=targetfile)


@conf
def wheel(ctxt, *args, **kwargs):
    srcdir = kwargs.get("srcdir", ctxt.run_dir)
    pkgname = kwargs.get("pkgname")
    extname = kwargs.get("extname")
    pyver = kwargs.get("pyver", ctxt.env.PYTHON_VERSION)
    pkgversion = kwargs.get("version", "")
    arch = kwargs.get("arch")

    pkglibdir = ctxt.env.PYTHON_PKGLIBDIR

    if ctxt.env.USE_VIRTUALENV:
        pkglibdir = "virtual/%s" % pkglibdir
    abs_pkglibdir = os.path.abspath(ctxt.out_dir + "/" + pkglibdir)

    srcfiles = []
    if extname:
        srcfiles.extend(ctxt.path.ant_glob("%s/**/*.{c,h}" % (pkgname,)))

    pkgwheelname = srcdir.replace("/", "-")
    if pkgname:
        srcfiles.extend(ctxt.path.ant_glob("%s/**/*.py" % pkgname))
        pkgwheelname = wheelname(pkgname, pkgversion, pyver, arch)

    if ctxt.env.USE_VIRTUALENV:
        prefix = ""
    else:
        ddir = os.path.abspath(ctxt.out_dir)

    if ctxt.env.DEBIAN_STYLE:
        style = "--config-settings=install-layout=deb"
        pkg_path = "dist-packages"
    else:
        style = ""
        pkg_path = "site-packages"

    wheeldir = f"{ctxt.out_dir}/wheel"
    targetfile = f"wheel/{pkgwheelname}"

    actions = [
        "cd %s" % os.path.abspath(srcdir),
        f"mkdir -p {wheeldir}",
        f"pip3 wheel -w {wheeldir} .",
        f"pip3 install --no-index --find-links={wheeldir} {wheeldir}/{pkgwheelname}"
    ]

    wheelrule = (
        f"echo Building {kwargs['pkgname']} && "
        + ' && '.join([
            f"echo ': {action}' && {action}"
            for action in actions
        ])
    )

    if ctxt.env.USE_VIRTUALENV:
        srcfiles.append(".waf-built-virtual")
        wheelrule = (". %s/virtual/bin/activate.orig && %s"
                   % (os.path.abspath(ctxt.out_dir), wheelrule))

    # ensure that eggs are build sequentially.  Updating the .pth files
    # gets racy otherwise
    ctxt.post_mode = waflib.Build.POST_LAZY
    ctxt.add_group()

    tgen = ctxt(rule=wheelrule, source=srcfiles, target=targetfile)
    tgen.env.env = dict(os.environ)

    if targetfile not in allwheeltargets:
        allwheeltargets.append(targetfile)

    if pkgname not in allwheels:
        allwheels.append(pkgname)

    if 'PYTHONPATH' in tgen.env.env:
        tgen.env.env['PYTHONPATH'] += ':' + abs_pkglibdir
    else:
        tgen.env.env['PYTHONPATH'] = abs_pkglibdir


def gitversion(ctxt):
    ctxt.env.GITVERSION = VERSION + "." + git_version()


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

    for lib in libs:
        print("%s %s %s %s" % (env, ctxt.env.PYTHON_INSTALLER, prefix, lib))

        ctxt.exec_command("%s %s %s %s" % (env, ctxt.env.PYTHON_INSTALLER, prefix, lib))


class MFPInstallContext (InstallContext):
    cmd = 'install'

    def execute(self):
        self.restore()
        if not self.all_envs:
            self.load_envs()

        self.recurse([self.run_dir])
        try:
            self.install_virtualenv()
            self.install_wheels()
            self.rewrite_shebang()
        finally:
            self.store()

        super().execute()

    def install_virtualenv(self):
        allfiles = open(f"{self.out_dir}/.waf-built-virtual", "r").read().split("\n")
        topdir_chunk = len(f"{self.out_dir}/virtual")
        self.exec_command(f"echo Installing virtualenv files to {self.env.PREFIX}")

        for file in allfiles:
            if not file:
                continue
            destfile = f"{self.env.PREFIX}{file[topdir_chunk:]}"
            destdir = os.path.dirname(destfile)
            self.exec_command(f"mkdir -p '{destdir}' && cp -a '{file}' '{destfile}'")

    def install_wheels(self):
        srcroot = os.path.abspath(out)
        if self.env.USE_VIRTUALENV:
            srcroot += "/virtual/"

        actions = [
            f". {self.env.PREFIX}/bin/activate",
            f"cd {os.path.abspath(self.out_dir)}",
        ]

        for wheel in allwheeltargets:
            actions.append(f"pip install --force-reinstall --prefix={self.env.PREFIX} --no-index {wheel}")

        rule = (
            f"echo Installing wheels {allwheels} && "
            + ' && '.join([
                f"echo ': {action}' && {action}"
                for action in actions
            ])
        )
        self.exec_command(rule)

    def rewrite_shebang(self):
        if not self.env.USE_VIRTUALENV:
            return
        build_bindir = f"{self.out_dir}/virtual/bin/".replace("/", "\\/")
        inst_bindir = f"{self.env.PREFIX}/bin/".replace("/", "\\/")

        action = (
            "echo Cleaning up wheel install && "
            + f"echo : Rewrite {build_bindir} to {inst_bindir} ; "
            + f"for f in {inst_bindir}/* ; "
            + "do "
            + f"cat $f | sed -e 's/{build_bindir}/{inst_bindir}/g' > $f.fixed; "
            + "mv $f.fixed $f; "
            + "chmod a+x $f; "
            + "done; "
        )
        self.exec_command(action)

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
                    if os.path.islink(n.abspath()):
                        symlinks.append(n.abspath())
                        if hasattr(n, 'children'):
                            delattr(n, "children")
                        continue
                    elif os.path.islink(n.abspath()):
                        continue
                    elif os.path.isdir(n.abspath()):
                        continue
                    n.delete()
                    self.root.children = {}
            print("clean: left with symlinks", symlinks)
        for v in ['node_deps', 'task_sigs', 'raw_deps']:
            setattr(self, v, {})


def options(opt):
    opt.load(WAFTOOLS)
    optgrp = opt.get_option_group('Configuration options')
    optgrp.add_option(
        "--virtualenv", action="store_true", dest="USE_VIRTUALENV",
        help="Install into a virtualenv"
    )

    # "egg" targets race to update the .pth file.  Must build them one at a time.
    opt.parser.set_defaults(jobs=1)


def configure(conf):
    conf.load(WAFTOOLS)

    # Python and dev files
    conf.check_python_version((3, 5))
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
        except waflib.Errors.ConfigurationError:
            pass

        if installer is None:
            conf.find_program("easy_install")
            installer = "easy_install"
    conf.env.PYTHON_INSTALLER = installer

    # python lib-install prefix
    conf.start_msg("Finding Python lib install prefix...")
    py_major = conf.env.PYTHON_VERSION.split(".")[0]
    pkglibdir = f"lib/python{py_major}"
    conf.end_msg(pkglibdir)
    conf.env.PYTHON_PKGLIBDIR = pkglibdir

    # Git (needed during build)
    conf.find_program("git")

    # Need jackd installed!
    conf.find_program("jackd")

    # C libraries with pkg-config support (listed at top of file)
    uselibs = []

    for lib in pkgconf_libs:
        uname = lib.split("-")[0].upper()
        conf.check_cfg(
            package=lib, args="--libs --cflags",
            uselib_store=uname
        )
        uselibs.append(uname)
    conf.env.PKGCONF_LIBS = uselibs

    pip_libs = ["posix_ipc", "simplejson", ("cairo", "pycairo"), "numpy",
                "pynose", "yappi", "cython", "pyliblo", "gbulb", "carp-rpc", "flopsy"]
    gi_libs = ["Clutter", "GObject", "Gtk", "Gdk", "GLib", "GtkClutter", "Pango"]

    pip_notfound = []

    # LADSPA header
    conf.check_cc(header_name="ladspa.h")
    conf.check_cc(header_name="asoundlib.h")

    # pip-installable libs we just mark them as not available
    for lib in pip_libs:
        if isinstance(lib, tuple):
            modulename, pipname = lib
        else:
            modulename = pipname = lib

        try:
            conf.check_python_module(modulename)
        except waflib.Errors.ConfigurationError:
            pip_notfound.append(pipname)

    conf.env.PIPLIBS_NOTFOUND = pip_notfound

    # GObject bindings for libraries are mandatory
    for lib in gi_libs:
        try:
            conf.check_python_module('gi.repository.' + lib)
        except waflib.Errors.ConfigurationError:
            print()
            print("FATAL: GObject language bindings for %s not installed" % lib)
            print("They are packaged like 'gir1.2-${libname}-${libver}' on Debian and Ubuntu")
            print("Try 'apt-cache search gir %s' to find the right package" % lib.lower())
            print()
            raise

    conf.env.GITVERSION = VERSION + "." + git_version()

    print()
    print("MFP version", conf.env.GITVERSION, "configured.")
    if conf.env.USE_VIRTUALENV:
        print("Will build into virtualenv", conf.env.PREFIX)
    print()


def build(bld):
    import platform
    import sys

    version_python_only = f'py{sys.version_info.major}'
    version_extensions = f'cp{sys.version_info.major}{sys.version_info.minor}'
    version_extensions = f'{version_extensions}-{version_extensions}'
    arch = f'{sys.platform}_{platform.machine()}'

    # only gets built if USE_VIRTUALENV is set
    bld.make_virtualenv()

    bld.wheel(
        pkgname="mfp",
        version=bld.env.GITVERSION,
        pyver=version_python_only
    )
    bld.wheel(
        srcdir="pluginfo",
        pkgname="pluginfo",
        pyver=version_extensions,
        arch=arch,
        version="1.0"
    )
    bld.wheel(
        srcdir="testext",
        pkgname="testext",
        pyver=version_extensions,
        arch=arch,
        version="1.0"
    )
    bld.wheel(
        srcdir="lib/alsaseq-0.4.1",
        pkgname="alsaseq",
        extname="alsaseq",
        pyver=version_extensions,
        arch=arch,
        version="0.4.1"
    )

    cflags = ["-std=gnu99", "-fpic", "-g", "-O2", "-D_GNU_SOURCE"]
    if 'x86' in arch:
        cflags.append("-DMFP_USE_SSE")

    bld.shlib(source=bld.path.ant_glob("mfpdsp/*.c"),
              target="mfpdsp",
              cflags=cflags,
              uselib=bld.env.PKGCONF_LIBS)

    bld.program(source="mfpdsp/main.c", target="mfpdsp/mfpdsp",
                cflags=cflags,
                uselib=bld.env.PKGCONF_LIBS,
                use=['mfpdsp'])
    bld.add_group()

    #bld(features="install_wheels")
    #bld.add_group()

    # must make virtualenv "relocatable" after all packages added
    bld.fix_virtualenv()
