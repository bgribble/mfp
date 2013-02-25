#! /usr/bin/env python
'''
colordb.py -- RGBA color definitions for MFP app 

Copyright (c) 2013 Bill Gribble <grib@billgribble.com>
'''

from ..singleton import Singleton
from gi.repository import Clutter 


class RGBAColor(object):
    def __init__(self, r, g, b, a):
        self.red = r 
        self.green = g
        self.blue = b
        self.alpha = a 


class ColorDB (Singleton): 
    named_colors = {} 
    rgba_colors = {}  

    def find(self, *colorinfo):
        ll = len(colorinfo)
        if ll > 2:
            # RGB or RGBA color values 
            if ll > 3:
                key = (int(colorinfo[0]), int(colorinfo[1]), 
                       int(colorinfo[2]), int(colorinfo[3]))
            elif ll == 3: 
                key = (int(colorinfo[0]), int(colorinfo[1]), int(colorinfo[2]), 255)

            if not self.rgba_colors.has_key(key):
                nc = Clutter.Color.new(*key)
                self.rgba_colors[key] = nc
            else: 
                nc = self.rgba_colors.get(key)
            return nc 
        elif isinstance(colorinfo[0], str):
            nc = self.named_colors.get(colorinfo[0])
            if nc is not None:
                return nc 
            
            color = Clutter.Color()
            rv = color.from_string(colorinfo[0])
            if isinstance(rv, tuple):
                if isinstance(rv[0], Clutter.Color):
                    color = rv[0]
                elif isinstance(rv[1], Clutter.Color):
                    color = rv[1]
            return color 

    def find_cairo(self, *colorinfo):
        tmp = self.find(*colorinfo)
        rv = RGBAColor(tmp.red / 255.0, tmp.green / 255.0, tmp.blue/255.0, tmp.alpha/255.0)
        return rv 

    def insert(self, name, color):
        self.named_colors[name] = color

    @classmethod
    def to_cairo(klass, color): 
        return RGBAColor(color.red / 256.0, color.blue / 256.0, color.green / 256.0, 
                         color.alpha / 256.0)

    

