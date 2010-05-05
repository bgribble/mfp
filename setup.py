
from distutils.core import setup, Extension

mfpdsp = Extension('mfpdsp',
					libraries = ['jack'],
                    sources = ['mfpdsp/mfp_pyglue.c',
							   'mfpdsp/mfp_jack.c'])

setup (name = 'mfp',
       version = '1.0',
       description = 'Music for programmers',
       ext_modules = [ mfpdsp ])

