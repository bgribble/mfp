#! /usr/bin/env python
'''
pluginfo.py

Python package using C extension to dig info about plugins
'''

import _pluginfo

def is_ladspa(filename):
    return _pluginfo.is_ladspa(filename)

def list_plugins(filename):
    return _pluginfo.list_plugins(filename)


