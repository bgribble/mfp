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
    m = re.search(r"^(.*) ([()0-9a-fx]+)$", stdout.strip().decode('utf-8'))
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

    print("Patch.lv2_create_dir: made lv2 plugin dir '%s'" % fullpath)
    return fullpath


ttl_template = """
# manifest.ttl -- an LV2 plugin definition file for MFP
# THIS FILE IS AUTOMATICALLY GENERATED.  DO NOT EDIT

@prefix doap: <http://usefulinc.com/ns/doap#> .
@prefix lv2:  <http://lv2plug.in/ns/lv2core#> .
@prefix midi:  <http://lv2plug.in/ns/ext/midi#> .
@prefix atom: <http://lv2plug.in/ns/ext/atom#> .
@prefix rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

<http://www.billgribble.com/mfp/%(ttl_plugname)s.lv2>
    a lv2:Plugin;
    lv2:binary <%(ttl_libname)s>;
    lv2:project <http://github.com/bgribble/mfp> ;
    doap:name "%(ttl_filename)s";
    doap:description "%(ttl_description)s";
    doap:license <http://opensource.org/licenses/gpl-license> ;
    lv2:optionalFeature lv2:hardRTCapable ;

    # port definitions
    lv2:port
    %(ports)s.
"""

port_template = """
    [
        a %(port_types)s ;
        lv2:index %(port_number)s ;
        lv2:symbol "%(port_symbol)s" ;
        lv2:name "%(port_name)s" ;
        %(port_property)s
        %(port_bounds)s
    ]"""

bounds_template = """
        lv2:default %(bounds_default)s;
        lv2:minimum %(bounds_minimum)s;
        lv2:maximum %(bounds_maximum)s;"""


@extends(Patch)
def lv2_write_ttl(self, ttlpath, plugname, filename):
    port_list = []
    libname = "lib%s_lv2.so" % plugname
    ttl_params = dict(ttl_plugname=plugname, ttl_filename=filename,
                      ttl_libname=libname,
                      ttl_description=(self.properties.get("lv2_description") or self.name))
    portnum = 0
    for p in self.inlet_objects + self.outlet_objects:
        port_params = dict(port_number=portnum, port_property='')
        port_types = []
        if p.init_type in ("inlet~", "outlet~"):
            needs_bounds = False
            port_types = ["lv2:AudioPort"]
        else:
            needs_bounds = True
            if p.properties.get("lv2_type") == "midi":
                port_params['port_property'] = '\n'.join([
                    'atom:bufferType atom:Sequence ; ',
                    'atom:supports midi:MidiEvent ; ',
                ])
                needs_bounds = False
                port_types = ["atom:AtomPort"]
            else:
                port_types = ["lv2:ControlPort"]

        if p.init_type in ("inlet~", "inlet"):
            port_types.append("lv2:InputPort")
        else:
            port_types.append("lv2:OutputPort")

        port_params['port_types'] = ', '.join(port_types)
        port_params['port_symbol'] = p.name
        port_params['port_name'] = p.properties.get("lv2_description") or p.name
        if needs_bounds:
            bounds=dict(bounds_default=p.properties.get('lv2_default_val', 0.0),
                        bounds_minimum=p.properties.get('lv2_minimum_val', 0.0),
                        bounds_maximum=p.properties.get('lv2_maximum_val', 1.0))
            port_params['port_bounds'] = bounds_template % bounds
        else:
            port_params['port_bounds'] = ""

        portnum += 1
        port_list.append(port_template % port_params)

    # Edit button
    port_params=dict(port_number=portnum)
    port_params['port_types'] = "lv2:InputPort, lv2:ControlPort"
    port_params['port_symbol'] = 'patch_edit'
    port_params['port_name'] = 'Edit'
    port_params['port_bounds'] = "lv2:default 0.0;"
    port_params['port_property'] = 'lv2:portProperty lv2:toggled;'
    port_list.append(port_template % port_params)

    ttl_params['ports'] = ',\n'.join(port_list)

    with open(ttlpath, "w") as ttlfile:
        ttlfile.write(ttl_template % ttl_params)

    # make the symlink to libmfpdsp.sp
    import os, os.path
    ttldir = os.path.dirname(ttlpath)
    mfplib_path = os.path.relpath(find_mfplib(), ttldir)
    if not mfplib_path:
        return None
    else:
        linkpath = os.path.join(ttldir, libname)
        if not os.path.exists(linkpath):
            os.symlink(mfplib_path, linkpath)

@extends(Patch)
def lv2_bless(self, plugname):
    pass
