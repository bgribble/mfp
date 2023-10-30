#! /usr/bin/env python
'''
colordb.py -- RGBA color definitions for MFP app

Copyright (c) 2013 Bill Gribble <grib@billgribble.com>
'''

from ..singleton import Singleton
from .backend_interfaces import ColorDBBackend


class RGBAColor:
    def __init__(self, r, g, b, a):
        self.red = r
        self.green = g
        self.blue = b
        self.alpha = a

    @classmethod
    def load(self, propdict):
        return RGBAColor(propdict.get('red', 0),
                         propdict.get('green', 0),
                         propdict.get('blue', 0),
                         propdict.get('alpha', 0))


class ColorDB (Singleton):
    named_colors = {}
    rgba_colors = {}

    def __init__(self):
        from .app_window import AppWindow
        factory = ColorDBBackend.get_backend(AppWindow.backend_name)
        self.backend = factory(self)
        super().__init__()

    def find(self, *colorinfo):
        ll = len(colorinfo)
        if ll > 2:
            # RGB or RGBA color values
            key = None
            if ll > 3:
                key = (int(colorinfo[0]), int(colorinfo[1]),
                       int(colorinfo[2]), int(colorinfo[3]))
            elif ll == 3:
                key = (int(colorinfo[0]), int(colorinfo[1]), int(colorinfo[2]), 255)

            if key in self.rgba_colors:
                return self.rgba_colors.get(key)

            nc = self.create_from_rgba(*key)
            self.rgba_colors[key] = nc
            return nc

        if isinstance(colorinfo[0], str):
            color_name = colorinfo[0]
            if color_name in self.named_colors:
                return self.named_colors[color_name]

            nc = self.create_from_name(color_name)
            self.named_colors[color_name] = nc
            return nc
        return None

    def insert(self, name, color):
        self.named_colors[name] = color
