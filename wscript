#! /usr/bin/env python3
"""
wscript is like the Makefile for a waf project.

The waf commands configure and build map to the
functions with the same name in here.

The waf command install is a special case of build,
and uses the MFPInstallContext.execute() method. Don't ask,
I don't understand it either.

Copyright (c) Bill Gribble <grib@billgrible.com>
"""

from functools import wraps
import re
import os
import os.path
import tarfile

# pylint: disable=import-error
from waflib.Configure import conf
from waflib.Build import InstallContext, CleanContext, CFG_FILES
import waflib

APPNAME = "mfp"
VERSION = "0.7.2"
WAFTOOLS = "compiler_c gcc python glib2"

top = '.'
out = 'wafbuild'

allwheels = []
allwheeltargets = []

#####################
# helper funcs
#####################

def wheelname(pkgname, pkgver, pyver, arch):
    if arch:
        archstr = "-%s" % arch
    else:
        archstr = "-none-any"
    return "%s-%s-%s%s.whl" % (pkgname, pkgver, pyver, archstr)


#####################
# custom rules
#####################

def template(*args, **kwargs):
    variables = kwargs.get("variables")

    @wraps(template)
    def _inner(task):
        gen = task.generator
        ctxt = gen.bld

        source = task.inputs[0]
        target = task.outputs[0]

        print(f"[template] source={source} dest={target}")

        source_stat = os.stat(str(source))
        source_mode = oct(source_stat.st_mode & 0o777)

        actions = [
            f"cp {source} {target}",
        ]

        for varname, value in variables.items():
            escaped_value = re.sub("/", r"\/", value)
            actions.append(f"(cat {target} | sed -e 's/\\${{{varname}}}/{escaped_value}/g' > {target}.fixed) ")
            actions.append(f"mv {target}.fixed {target}")

        actions.append(f"chmod {source_mode[2:]} {target}")

        ctxt.exec_command(" && ".join(actions))

    return _inner


def tarball(*args, **kwargs):
    """
    helper to build a tar file for distribution/install
    inspired by https://www.phy.bnl.gov/~bviren/pub/topics/waf-latex-arxiv/index.html
    """
    files = kwargs.get("files")

    @wraps(tarball)
    def _inner(task):
        target = str(task.outputs[0])
        gen = task.generator
        ctxt = gen.bld

        if not files or not target:
            raise ValueError

        ext = os.path.splitext(target)[1][1:]

        with tarfile.open(target, f"w:{ext}") as tf:
            for node_glob, tar_path in files:
                nodes = ctxt.path.ant_glob(node_glob)

                # generally the file keeps the same name, but
                # not always
                rename_file = False
                if len(nodes) == 1 and tar_path[-1] != '/':
                    rename_file = True

                for node in nodes:
                    old_name = node.name
                    if rename_file:
                        old_name = ''
                    tf.add(node.abspath(), f"{tar_path}{old_name}")
    return _inner

def wheel(*args, **kwargs):
    pkgname = kwargs.get("pkgname", None)
    pyver = kwargs.get("pyver", None)
    pkgversion = kwargs.get("version", "")
    arch = kwargs.get("arch", None)
    pkgwheelname = wheelname(pkgname, pkgversion, pyver, arch)
    allwheels.append(pkgwheelname)

    @wraps(wheel)
    def _inner(task):
        gen = task.generator
        ctxt = gen.bld

        srcdir = kwargs.get("srcdir", ctxt.run_dir)
        pkgname = kwargs.get("pkgname", None)
        extname = kwargs.get("extname", None)

        pkglibdir = ctxt.env.PYTHON_PKGLIBDIR

        if ctxt.env.USE_VIRTUALENV:
            pkglibdir = "virtual/%s" % pkglibdir

        installer = ctxt.env.PYTHON_INSTALLER

        srcfiles = []
        if extname:
            srcfiles.extend(ctxt.path.ant_glob("%s/**/*.{c,h}" % (pkgname,)))

        if pkgname:
            srcfiles.extend(ctxt.path.ant_glob("%s/**/*.py" % pkgname))

        wheeldir = f"{ctxt.out_dir}/wheel"

        actions = [
            "cd %s" % os.path.abspath(srcdir),
            f"mkdir -p {wheeldir}",
            f"{installer} wheel -w {wheeldir} .",
        ]

        wheelrule = (
            f"echo Building {pkgname} && "
            + ' && '.join([
                f"echo ': {action}' && {action}"
                for action in actions
            ])
        )

        # ensure that eggs are build sequentially.  Updating the .pth files
        # gets racy otherwise
        ctxt.post_mode = waflib.Build.POST_LAZY
        ctxt.add_group()

        ctxt.exec_command(wheelrule)

    return _inner


class MFPInstallContext (InstallContext):
    cmd = 'install'

    def execute(self):
        self.restore()
        if not self.all_envs:
            self.load_envs()

        self.recurse([self.run_dir])
        self.add_group()
        try:
            if self.env.USE_VIRTUALENV:
                self.install_virtualenv()
                self.add_group()
            self.install_dependencies()
            self.add_group()
            self.install_wheels()
            self.add_group()
            self.install_static()
        finally:
            self.store()

        super().execute()

    def activate_virtualenv(self):
        if self.env.USE_VIRTUALENV:
            return f". {self.env.PREFIX}/share/mfp/venv/bin/activate"
        else:
            return "/bin/true"

    def install_virtualenv(self):
        python_name = self.env.PYTHON[0].split('/')[-1]
        vrule = ' && '.join([
            f"mkdir -p {self.env.PREFIX}/share/mfp/",
            f"cd {self.env.PREFIX}",
            "cd share/mfp/",
            f"{python_name} -m venv --system-site-packages venv",
            "cp venv/bin/activate venv/bin/activate.orig"
        ])
        print(f"[build_virtualenv] {vrule}")
        self.exec_command(vrule)

    def install_dependencies(self):
        cmds = [
            self.activate_virtualenv(),
            f"{self.env.PYTHON_INSTALLER} install -r {self.run_dir}/requirements.txt"
        ]

        self.exec_command(" && ".join(cmds))

    def install_wheels(self):
        wheelroot = os.path.abspath(out)
        wheeldir = f"{wheelroot}/wheel"

        actions = [
            self.activate_virtualenv()
        ]

        installer = self.env.PYTHON_INSTALLER

        actions.append(
            f"cd {wheeldir}",
        )

        for wheel in allwheels:
            actions.append(f"{installer} install --force-reinstall --no-index {wheel}")

        rule = (
            f"echo Installing wheels {allwheels} && "
            + ' && '.join([
                f"echo ': {action}' && {action}"
                for action in actions
            ])
        )
        self.exec_command(rule)

    def install_static(self):
        self.exec_command(
            f"cd {self.env.PREFIX} && tar zxf {self.out_dir}/static.tar.gz"
        )
        self.exec_command(
            f"cd {self.env.PREFIX} && tar zxf {self.out_dir}/templated.tar.gz"
        )


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
            lst = []
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
    optgrp.add_option(
        "--with-clutter", action="store_true", dest="WITH_CLUTTER",
        help="Enable build support for Clutter UI backend (default: do not build)"
    )
    optgrp.add_option(
        "--without-imgui", action="store_false", dest="WITH_IMGUI",
        help="Disable build support for Dear Imgui UI backend (default: build)"
    )

    # "egg" targets race to update the .pth file.  Must build them one at a time.
    opt.parser.set_defaults(jobs=1)


def configure(ctxt):
    ctxt.load(WAFTOOLS)

    # Python and dev files
    ctxt.check_python_version((3, 10))
    ctxt.check_python_headers()

    # check for Debian style
    ctxt.start_msg("Checking for site-packages vs. dist-packages (Debian-style)")
    debstyle = False
    import sys
    for d in sys.path:
        if "dist-packages" in d:
            debstyle = True
            break

    if debstyle:
        ctxt.end_msg("dist-packages")
        ctxt.env.DEBIAN_STYLE = True
    else:
        ctxt.end_msg("site-packages")

    # backend builds. Defaults: imgui yes, clutter no
    ctxt.env.WITH_CLUTTER = False
    ctxt.env.WITH_IMGUI = True

    if ctxt.options.WITH_CLUTTER is True:
        ctxt.env.WITH_CLUTTER = True
    if ctxt.options.WITH_IMGUI is False:
        ctxt.env.WITH_IMGUI = False

    # virtualenv and setuptools
    installer = None
    if ctxt.options.USE_VIRTUALENV:
        ctxt.env.USE_VIRTUALENV = True
        # venv is part of the standard python distro, but at least on
        # Debian needs to be installed separately.
        ctxt.check_python_module("venv")

    try:
        ctxt.find_program("pip")
        installer = "pip"
    except waflib.Errors.ConfigurationError:
        ctxt.find_program("pip3")
        installer = "pip3"
    finally:
        if not installer:
            print("The 'pip' package installer is required for the build.")

    ctxt.env.PYTHON_INSTALLER = installer

    # python lib-install prefix
    ctxt.start_msg("Finding Python lib install prefix...")
    py_major = ctxt.env.PYTHON_VERSION.split(".")[0]
    pkglibdir = f"lib/python{py_major}"
    ctxt.end_msg(pkglibdir)
    ctxt.env.PYTHON_PKGLIBDIR = pkglibdir

    # build-time dependencies
    ctxt.find_program("git")
    ctxt.find_program("cmake")

    pip_libs = [
        "posix_ipc", "simplejson", "numpy",
        "pynose", "yappi", "cython", "pyliblo3",
        "soundfile", "samplerate",
        # my other libs
        "carp-rpc", "flopsy",
    ]
    gi_libs = []

    pkgconf_libs = [
        "glib-2.0", "json-glib-1.0", "serd-0", "jack", "liblo", "lv2", "libprotobuf-c",
    ]
    uselibs = []

    for lib in pkgconf_libs:
        uname = lib.split("-")[0].upper()
        ctxt.check_cfg(
            package=lib, args="--libs --cflags",
            uselib_store=uname
        )
        uselibs.append(uname)
    ctxt.env.PKGCONF_LIBS = uselibs

    # LLVM needs special args
    ctxt.check_cfg(
        path="llvm-config",
        package="",
        args="--link-static --ldflags --libs all --system-libs",
        uselib_store="LLVM"
    )
    ctxt.env.PKGCONF_LIBS.append("LLVM")

    if ctxt.env.WITH_CLUTTER:
        pip_libs.extend([
            ("cairo", "pycairo"), "gbulb",
        ])

        # all only needed for clutter backend
        gi_libs = ["Clutter", "GObject", "Gtk", "Gdk", "GLib", "GtkClutter", "Pango"]

    if ctxt.env.WITH_IMGUI:
        pip_libs.extend([
            "pyopengl", "sdl", "imgui_bundle", "Pillow",  # imgui only
        ])

    pip_notfound = []

    # LADSPA header
    ctxt.check_cc(header_name="ladspa.h")
    ctxt.check_cc(header_name="asoundlib.h")

    # FAUST libs and header
    ctxt.check_cc(header_name="faust/dsp/libfaust-c.h")
    ctxt.find_program("llvm-config")
    ctxt.env.FAUST_LIBS = [
        "-lfaust", 
    ]
    

    # pip-installable libs we just mark them as not available
    for lib in pip_libs:
        if isinstance(lib, tuple):
            modulename, pipname = lib
        else:
            modulename = pipname = lib

        try:
            ctxt.check_python_module(modulename)
        except waflib.Errors.ConfigurationError:
            pip_notfound.append(pipname)

    ctxt.env.PIPLIBS_NOTFOUND = pip_notfound

    # GObject bindings for libraries are mandatory
    for lib in gi_libs:
        try:
            ctxt.check_python_module('gi.repository.' + lib)
        except waflib.Errors.ConfigurationError:
            print()
            print("FATAL: GObject language bindings for %s not installed" % lib)
            print("They are packaged like 'gir1.2-${libname}-${libver}' on Debian and Ubuntu")
            print("Try 'apt-cache search gir %s' to find the right package" % lib.lower())
            print()
            raise

    ctxt.env.GITVERSION = VERSION

    print()
    print("MFP version", ctxt.env.GITVERSION, "configured.")
    if ctxt.env.USE_VIRTUALENV:
        print("Will build into virtualenv", ctxt.env.PREFIX)
    if ctxt.env.WITH_IMGUI:
        print("Will build Dear Imgui UI")
    else:
        print("Will not build Dear Imgui UI")

    if ctxt.env.WITH_CLUTTER:
        print("Will build Clutter UI")
    else:
        print("Will not build Clutter UI")

    print()


def build(bld):
    import platform
    import sys

    version_python_only = f'py{sys.version_info.major}'
    version_extensions = f'cp{sys.version_info.major}{sys.version_info.minor}'
    version_extensions = f'{version_extensions}-{version_extensions}'
    arch = f'{sys.platform}_{platform.machine()}'

    bld(
        rule=wheel(
            pkgname="mfp",
            version=bld.env.GITVERSION,
            pyver=version_python_only
        ),
        source=[
            bld.path.ant_glob("**/*.py"),
        ],
        target=f"wheel/{wheelname('mfp', bld.env.GITVERSION, version_python_only, 'none-any')}"
    )
    bld(
        rule=wheel(
            srcdir="pluginfo",
            pkgname="pluginfo",
            pyver=version_extensions,
            arch=arch,
            version="1.0"
        ),
        source=bld.path.ant_glob("pluginfo/**/*.{c,py}"),
        target=f"wheel/{wheelname('pluginfo', '1.0', version_extensions, arch)}"
    )
    bld(
        rule=wheel(
            srcdir="testext",
            pkgname="testext",
            pyver=version_extensions,
            arch=arch,
            version="1.0"
        ),
        source=bld.path.ant_glob("testext/**/*.{c,py}"),
        target=f"wheel/{wheelname('testext', '1.0', version_extensions, arch)}"
    )
    bld(
        rule=wheel(
            srcdir="lib/alsaseq-0.4.1",
            pkgname="alsaseq",
            extname="alsaseq",
            pyver=version_extensions,
            arch=arch,
            version="0.4.1"
        ),
        source=bld.path.ant_glob("lib/alsaseq-0.4.1/*.{c,py}"),
        target=f"wheel/{wheelname('alsaseq', '0.4.1', version_extensions, arch)}"
    )

    bld(
        rule=template(
            variables=dict(
                PREFIX=bld.env.PREFIX,
                VIRTUAL_PREFIX=f"{bld.env.PREFIX}/share/mfp/venv" if bld.env.USE_VIRTUALENV else "",
            )
        ),
        source="mfp.launcher",
        target="mfp",
    )

    bld(
        rule=template(
            variables=dict(
                PREFIX=bld.env.PREFIX,
            )
        ),
        source="mfp.desktop",
        target="com.billgribble.mfp.desktop",
    )
    cflags = ["-std=gnu99", "-fpic", "-g", "-O2", "-D_GNU_SOURCE"]
    if 'x86' in arch:
        cflags.append("-DMFP_USE_SSE")

    bld.shlib(
        source=bld.path.ant_glob("mfpdsp/*.c"),
        target="mfpdsp",
        cflags=cflags,
        uselib=bld.env.PKGCONF_LIBS,
    )

    bld.program(
        source="mfpdsp/main.c",
        target="mfpdsp/mfpdsp",
        cflags=cflags,
        ldflags="-lfaust",
        uselib=bld.env.PKGCONF_LIBS,
        use=['mfpdsp']
    )
    bld.add_group()


    bld(
        rule=tarball(
            files=[
                ("wafbuild/mfp", "bin/"),
                ("wafbuild/com.billgribble.mfp.desktop", "share/mfp/"),
            ],
        ),
        source=["mfp", "com.billgribble.mfp.desktop"],
        target="templated.tar.gz"
    )

    bld(
        rule=tarball(
            files=[
                ("wafbuild/libmfpdsp.so", "lib/"),
                ("wafbuild/mfpdsp/mfpdsp", "bin/"),
            ],
        ),
        source=["mfpdsp/mfpdsp"],
        target="mfpdsp.tar.gz"
    )

    bld(
        rule=tarball(
            files=[
                ("wafbuild/mfp", "bin/"),
                ("mfp.svg", "share/mfp/icons/hicolor/scalable/actions/"),
                ("mfp.png", "share/mfp/icons/hicolor/96x96/actions/"),
                ("help/*.mfp", "share/mfp/patches/help/"),
            ],
        ),
        source=["mfp.svg", "mfp.png", bld.path.ant_glob("help/*.mfp")],
        target="static.tar.gz"
    )

    ver = f"mfp_{bld.env.GITVERSION}"
    bld(
        rule=tarball(
            files=[
                ("wafbuild/*.tar.gz", f"{ver}/files/"),
                ("wafbuild/wheel/*.whl", f"{ver}/files/"),
                ("requirements.txt", f"{ver}/files/"),
                ("mfp.launcher", f"{ver}/files/"),
                ("mfp.desktop", f"{ver}/files/"),
                ("mfp.installer", f"{ver}/install_mfp.py"),
                ("README.install", f"{ver}/")
            ]
        ),
        source=[
            "static.tar.gz", "mfpdsp.tar.gz",
            "templated.tar.gz", "mfp.installer", "requirements.txt",
            "mfp.launcher", "mfp.desktop", "README.install",
            [f"wheel/{wheel}" for wheel in allwheels]
        ],
        target=f"mfp_{bld.env.GITVERSION}_{version_extensions}_{arch}.tar.gz"
    )
    bld.add_group()

# helper waf command ("./waf gitversion")
def gitversion(ctxt):
    ctxt.env.GITVERSION = VERSION
