#! /usr/bin/env python
'''
pluginfo.py

Python package using C extension to dig info about plugins
'''

import _pluginfo
import os 
import math 

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
        self.samplerate = 44100
        const = _pluginfo.get_constants()
        for k, v in const.items():
            setattr(self, k, v)

    def index_ladspa(self):
        pathenv = os.environ.get("LADSPA_PATH") 
        if not pathenv: 
            pathenv = self.LADSPA_PATH_DEFAULT % os.environ.get("HOME", "~")
        
        dirs = splitpath(pathenv)
        for d in dirs:
            try: 
                candidates = os.listdir(d)
            except:
                continue 

            for c in candidates: 
                fullpath = os.path.join(d, c)
                if _pluginfo.is_ladspa(fullpath):
                    plugs = _pluginfo.list_plugins(fullpath)
                    self.libinfo[fullpath] = plugs  
                    for p in plugs: 
                        key = p[2].lower()
                        pinfo = _pluginfo.describe_plugin(p[0], p[1])
                        self.pluginfo[key] = pinfo

    def find(self, name):
        return self.pluginfo.get(name.lower())

    def port_default(self, portinfo): 
        htype = portinfo.get("hint_type", 0)
        hlower = portinfo.get("hint_lower", 0)
        hupper = portinfo.get("hint_upper", 0)

        if htype & self.LADSPA_HINT_SAMPLE_RATE:
            multiplier = self.samplerate
        else: 
            multiplier = 1.0 

        if htype & self.LADSPA_HINT_TOGGLED:
            if htype & self.LADSPA_HINT_DEFAULT_1:
                return 1
            else:
                return 0 
        elif htype & self.LADSPA_HINT_DEFAULT_MIDDLE == self.LADSPA_HINT_DEFAULT_MIDDLE:
            if htype & self.LADSPA_HINT_LOGARITHMIC: 
                return math.exp(math.log(hlower) * 0.5 + math.log(hupper) * 0.5) * multiplier
            else: 
                return (hlower * 0.5 + hupper * 0.5) * multiplier
        elif htype & self.LADSPA_HINT_DEFAULT_MINIMUM: 
            return hlower * multiplier
        elif htype & self.LADSPA_HINT_DEFAULT_LOW:
            if htype & self.LADSPA_HINT_LOGARITHMIC: 
                return math.exp(math.log(hlower) * 0.75 + math.log(hupper) * 0.25) * multiplier
            else: 
                return (hlower * 0.75 + hupper * 0.25) * multiplier
        elif htype & self.LADSPA_HINT_DEFAULT_HIGH:
            if htype & self.LADSPA_HINT_LOGARITHMIC: 
                return math.exp(math.log(hlower) * 0.25 + math.log(hupper) * 0.75) * multiplier
            else: 
                return (hlower * 0.25 + hupper * 0.75) * multiplier
        elif htype & self.LADSPA_HINT_DEFAULT_MAXIMUM: 
            return hupper * multiplier
        elif htype & self.LADSPA_HINT_DEFAULT_0:
            return 0.0
        elif htype & self.LADSPA_HINT_DEFAULT_1:
            return 1.0
        elif htype & self.LADSPA_HINT_DEFAULT_100:
            return 100.0
        elif htype & self.LADSPA_HINT_DEFAULT_440:
            return 440.0
        else: 
            return hlower

    def plugin_docstring(self, pluginfo):
        name = pluginfo.get("name")
        author = pluginfo.get("maker") 

        if author is not None:
            astr = "by %s" % author 
        else:
            astr = None 

        ds = "LADSPA plugin: %s" % ' '.join([s for s in [name, astr] if s is not None])
        return ds
    
    def port_docstring(self, portinfo): 
        name = portinfo.get("name")
        htype = portinfo.get("hint_type") 
        minval = portinfo.get("hint_lower")
        maxval = portinfo.get("hint_upper")
        default = self.port_default(portinfo)

        if minval is not None and (htype & self.LADSPA_HINT_BOUNDED_BELOW):
            minstr = "min=%s" % minval
        else: 
            minstr = None

        if maxval is not None and (htype & self.LADSPA_HINT_BOUNDED_ABOVE):
            maxstr = "max=%s" % maxval
        else: 
            maxstr = None 

        if default is not None and (htype & self.LADSPA_HINT_DEFAULT_MASK):
            defstr = "default=%s" % default
        else:
            defstr = None 

        hints = ', '.join([ h for h in [minstr, maxstr, defstr] if h is not None])
        if len(hints):
            hints = " (%s)" % hints 
            return name + hints 
        else:
            return name 


            



