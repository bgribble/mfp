has_setuptools = False
try:
	from setuptools import setup, Extension
	has_setuptools = True
except ImportError:
	from distutils.core import setup, Extension

import sys,os,string,time

version = '0.4.1'

kwargs = dict()
if has_setuptools:
	kwargs = dict(
			include_package_data = True,
			install_requires = ['setuptools'],
			zip_safe = False)

setup(
	#-- Package description
	name = 'alsaseq',
	version = version,
	description = 'ALSA sequencer bindings for Python',
	author = 'Patricio Paez',
	author_email = 'pp@pp.com.mx',
	url = 'http://pp.com.mx/python/alsaseq/',
	license = 'GNU GPL v2 or later',
	#-- C extension modules
	ext_modules = [
		Extension(
		'alsaseq',
		[
			'alsaseq.c',
		],
		libraries = ['asound'],
		),
	],
	#-- Python "stand alone" modules 
	py_modules = [
		'alsamidi',
		'midiinstruments',
	],
	data_files = [ ( 'share/alsaseq-' + version, [ 'COPYING',
		'CHANGELOG', 'README', 'CREDITS', 'doc/project.html',
                'doc/project.rst'] ) ],
	platforms = ['linux'],
	long_description='''alsaseq is a Python 3 and Python 2 module that allows to interact with ALSA
sequencer clients. It can create an ALSA client, connect to other
clients, send and receive ALSA events immediately or at a scheduled
time using a sequencer queue. It provides a subset of the ALSA
sequencer capabilities in a simplified model. It is implemented in
C language and licensed under the Gnu GPL license version 2 or
later.''',
	classifiers=[ "Development Status :: 3 - Alpha",
            "Topic :: Multimedia :: Sound/Audio :: MIDI" ],
	package_dir = {'': '.',},
	**kwargs
)
