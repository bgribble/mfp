#! /usr/bin/env python
'''
pluginfo.py

Python package using C extension to dig info about plugins
'''

import _pluginfo
import os 

def is_ladspa(filename):
    return _pluginfo.is_ladspa(filename)

def list_plugins(filename):
    return _pluginfo.list_plugins(filename)

def describe_plugin(filename, plug_id):
    return _pluginfo.describe_plugin(filename, plug_id)

def splitpath(p):
    parts = p.split(":")
    unescaped = [] 
    prefix = None 
    for p in parts: 
        if p[-1] == '\\':
            newpart = p[:-1] + ':'
            if prefix is not None:
                prefix = prefix + newpart
            else:
                prefix = newpart 
        elif prefix is None:
            unescaped.append(p)
        else:
            unescaped.append(prefix + p)
            prefix = None 
    return unescaped 

class PlugInfo (object): 

    LADSPA_PATH_DEFAULT="%s/.ladspa:/usr/local/lib/ladspa:/usr/lib/ladspa"

    def __init__ (self): 
        self.plugindirs = [] 
        self.libinfo = {} 
        self.pluginfo = {} 

    def index_ladspa(self):
        print "PlugInfo: Crawling LADSPA_PATH"

        pathenv = os.environ.get("LADSPA_PATH") 
        if not pathenv: 
            pathenv = self.LADSPA_PATH_DEFAULT % os.environ.get("HOME", "~")
        
        print "Path to search:", pathenv 

        dirs = splitpath(pathenv)
        for d in dirs:
            print "Looking in directory", d
            try: 
                candidates = os.listdir(d)
            except:
                continue 

            for c in candidates: 
                fullpath = os.path.join(d, c)
                if _pluginfo.is_ladspa(fullpath):
                    print "Found LADSPA plugin lib:", fullpath 
                    plugs = _pluginfo.list_plugins(fullpath)
                    self.libinfo[fullpath] = plugs  
                    for p in plugs: 
                        key = p[2].lower()
                        print "     ", p
                        pinfo = _pluginfo.describe_plugin(p[0], p[1])
                        self.pluginfo[key] = pinfo

        print "done with search, found info about", len(self.pluginfo), "plugins in", len(self.libinfo), "DLLs"

    def find(self, name):
        return self.pluginfo.get(name.lower())


    



