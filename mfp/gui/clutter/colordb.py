"""
clutter/colordb.py -- Clutter backend for color database

Copyright (c) Bill Gribble <grib@billgribble.com>
"""
from gi.repository import Clutter
from ..backend_interfaces import ColorDBBackend


class ClutterColorDBBackend(ColorDBBackend):
    backend_name = "clutter"

    def create_from_rgba(self, red_val, green_val, blue_val, alpha_val):
        return Clutter.Color.new(red_val, green_val, blue_val, alpha_val)

    def create_from_name(self, color_name):
        color = Clutter.Color()
        rv = color.from_string(color_name)
        if isinstance(rv, tuple):
            if isinstance(rv[0], Clutter.Color):
                color = rv[0]
            elif isinstance(rv[1], Clutter.Color):
                color = rv[1]
        return color

    def normalize(self, color):
        from mfp.gui.colordb import RGBAColor

        if color is not None:
            rv = RGBAColor(
                red=(color.red / 255.0),
                green=(color.green / 255.0),
                blue=(color.blue/255.0),
                alpha=color.alpha/255.0
            )
        else:
            rv = RGBAColor(red=0, green=0, blue=0, alpha=1)
        return rv
