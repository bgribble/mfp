"""
imgui/colordb.py -- Imgui backend for color database

Copyright (c) Bill Gribble <grib@billgribble.com>
"""
from ..colordb import ColorDBBackend


class ImguiColorDBBackend(ColorDBBackend):
    backend_name = "imgui"

    def create_from_rgba(self, red_val, green_val, blue_val, alpha_val):
        return (red_val, green_val, blue_val, alpha_val)

    def create_from_name(self, color_name):
        return (0, 0, 0, 0)

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
