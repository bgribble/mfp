#!/usr/bin/env python

from setuptools import setup, Extension

setup(
    name='testext',
    version='1.0',
    description='Nose plugin to find and run tests in C extensions',
    packages= ['testext'],
    zip_safe = False,
    entry_points={
        'nose.plugins.0.10': [
            'testext = testext:TestExt'
        ],
        'console_scripts': [
            'testext_wrapper=testext.wrapper:main'
        ]
    },
    ext_modules=[ Extension('_testext', libraries=['dl'], 
                            sources=['_testext/testext.c']),
                  Extension('test', 
                            sources=['test/test_testext.c'])],
    include_package_data=True
)
