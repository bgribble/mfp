#! /usr/bin/env python
'''
patch_lv2.py
Methods to save a patch as an LV2 plugin

Copyright (c) 2014 Bill Gribble <grib@billgribble.com>
'''

from .patch import Patch
from .utils import extends

def find_mfplib():
    from subprocess import Popen, PIPE
    import re 
    sub = Popen(['/bin/bash', '-c', 
                 "ldd `type -p mfpdsp` | grep libmfpdsp | cut -d '>' -f 2"],
                stdout=PIPE, stderr=PIPE)
    stdout, stderr = sub.communicate()
    #m = re.search(r"([^ ]\+) \(([0-9a-fx]\+)\)$", stdout.strip())
    m = re.search(r"^(.*) ([()0-9a-fx]+)$", stdout.strip())
    if m: 
        return m.group(1) 
    else: 
        return None 

def create_path(fullpath):
    import os.path
    if os.path.isdir(fullpath):
        return True 
    elif os.path.exists(fullpath):
        return False 
    elif not fullpath:
        return True
    else: 
        if fullpath[-1] == '/':
            fullpath = fullpath[:-1]
        head, tail = os.path.split(fullpath)
        head_ok = create_path(head) 
        if head_ok: 
            try: 
                os.mkdir(fullpath)
                return True 
            except OSError: 
                pass
        return False 

@extends(Patch)
def lv2_create_dir(self, plugname):
    from .mfp_app import MFPApp
    import os 
    import os.path 

    lv2_basedir = MFPApp().lv2_savepath
    lv2_dirname = plugname + ".lv2"
    fullpath = os.path.join(lv2_basedir, lv2_dirname)

    dir_ok = create_path(fullpath)

    if not dir_ok:
        return None

    mfplib_path = os.path.relpath(find_mfplib(), fullpath)
    print "Patch.lv2_create_dir: found mfplib at '%s'" % mfplib_path
    if not mfplib_path: 
        return None 
    else: 
        os.symlink(mfplib_path, os.path.join(fullpath, "libmfpdsp.so"))
    print "Patch.lv2_create_dir: made lv2 plugin dir '%s'" % fullpath

    return fullpath

@extends(Patch)
def lv2_write_ttl(self, ttlpath, filename):
    print "Patch.lv2_write_ttl()"
    pass 

@extends(Patch)
def lv2_bless(self, plugname):
    pass 





