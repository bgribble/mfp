"""
imgui/colordb.py -- Imgui backend for color database

Copyright (c) Bill Gribble <grib@billgribble.com>
"""
from imgui_bundle import imgui

from mfp import log
from ..colordb import ColorDBBackend, RGBAColor


class ImguiColorDBBackend(ColorDBBackend):
    backend_name = "imgui"

    def create_from_rgba(self, red_val, green_val, blue_val, alpha_val):
        return RGBAColor(red=red_val, green=green_val, blue=blue_val, alpha=alpha_val)

    def create_from_name(self, color_name):
        return RGBAColor(red=0, green=0, blue=0, alpha=0)

    def im_col32(self, color):
        return imgui.IM_COL32(
            int(color.red),
            int(color.green),
            int(color.blue),
            int(color.alpha)
        )

    def im_colvec(self, color):
        return (
            color.red,
            color.green,
            color.blue,
            color.alpha
        )

    def normalize(self, color):
        from mfp.gui.colordb import RGBAColor

        if color is not None:
            rv = RGBAColor(
                red=(color.red / 255.0),
                green=(color.green / 255.0),
                blue=(color.blue / 255.0),
                alpha=color.alpha / 255.0
            )
        else:
            rv = RGBAColor(red=0, green=0, blue=0, alpha=1)
        return rv
