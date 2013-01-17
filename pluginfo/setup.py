#! /usr/bin/env python

from setuptools import setup, Extension

setup(
    name='pluginfo',
    verseion='1.0',
    description='Package wrapping C extension to query plugin DLLs',
    packages=['pluginfo'],
    ext_modules=[ Extension('_pluginfo', libraries=['dl'],
                             sources=['_pluginfo/pluginfo.c'])],
    include_package_data=True
)

