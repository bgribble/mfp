#!/usr/bin/env python
# -*- coding: utf-8 -*-

from distutils.core import setup, Extension
from distutils.command.build_scripts import build_scripts
from distutils import util, log
import os, sys


if '--with-cython' in sys.argv:
    from Cython.Distutils import build_ext
    sys.argv.remove('--with-cython')
    use_cython = True
else:
    use_cython = False


class build_scripts_rename(build_scripts):
    def copy_scripts(self):
        build_scripts.copy_scripts(self)
        # remove the .py extension from scripts
        for s in self.scripts:
            f = util.convert_path(s)
            before = os.path.join(self.build_dir, os.path.basename(f))
            after = os.path.splitext(before)[0]
            log.info("renaming %s -> %s" % (before, after))
            os.rename(before, after)


cmdclass = {
    'build_scripts': build_scripts_rename
}

ext_modules = [
    Extension(
        'liblo',
        [use_cython and 'src/liblo.pyx' or 'src/liblo.c'],
        extra_compile_args = [
            '-fno-strict-aliasing',
            '-Werror-implicit-function-declaration',
            '-Wfatal-errors',
        ],
        libraries = ['lo']
    )
]

if use_cython:
    cmdclass['build_ext'] = build_ext


if sys.hexversion < 0x03000000:
    scripts = [
        'scripts/send_osc.py',
        'scripts/dump_osc.py',
    ]
    data_files = [
        ('share/man/man1', [
            'scripts/send_osc.1',
            'scripts/dump_osc.1',
        ]),
    ]
else:
    # doesn't work with Python 3.x yet
    scripts = []
    data_files = []


setup (
    name = 'pyliblo',
    version = '0.9.1',
    author = 'Dominic Sacre',
    author_email = 'dominic.sacre@gmx.de',
    url = 'http://das.nasophon.de/pyliblo/',
    description = 'Python bindings for the liblo OSC library',
    license = 'LGPL',
    scripts = scripts,
    data_files = data_files,
    cmdclass = cmdclass,
    ext_modules = ext_modules
)
