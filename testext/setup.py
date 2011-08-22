#!/usr/bin/env python

from setuptools import setup, Extension

setup(
	name='testext',
	version='1.0',
	description='Nose plugin to find and run tests in C extensions',
	packages= ['testext'],
	entry_points={
		'nose.plugins.0.10': [
			'testext = testext:TestExt'
		],
		'console_scripts': [
			'testext_run=testext.runner:run_test'
		]
	},
	ext_modules=[ Extension('_testext', libraries=['dl'], 
							sources=['_testext/testext.c', '_testext/test_testext.c'])],
	include_package_data=True
)
