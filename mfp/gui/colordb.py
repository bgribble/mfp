#! /usr/bin/env python
'''
colordb.py -- RGBA color definitions for MFP app

Copyright (c) 2013 Bill Gribble <grib@billgribble.com>
'''

from abc import ABCMeta, abstractmethod
from carp.serializer import Serializable
from ..singleton import Singleton
from .backend_interfaces import BackendInterface
from ..delegate import DelegateMixin, delegatemethod


class RGBAColor(Serializable):
    """
    RGBAColor represents colors on a (0, 255) interval for each element
    """
    def __init__(self, *, red=0, green=0, blue=0, alpha=0):
        self.red = red
        self.green = green
        self.blue = blue
        self.alpha = alpha
        super().__init__()

    def to_dict(self):
        return dict(
            red=self.red,
            green=self.green,
            blue=self.blue,
            alpha=self.alpha
        )
    def __str__(self):
        return f"{int(self.red):02x}{int(self.green):02x}{int(self.blue):02x}{int(self.alpha):02x}"

    @classmethod
    def load(cls, propdict):
        return RGBAColor(**propdict)


class ColorDBBackend(BackendInterface, DelegateMixin, metaclass=ABCMeta):
    @abstractmethod
    @delegatemethod
    def create_from_rgba(self, red: int, green: int, blue: int, alpha: int):
        """
        create_from_rgba assumes (0, 255) for each element and returns a
        native color object
        """
        pass

    @abstractmethod
    @delegatemethod
    def create_from_name(self, name) -> RGBAColor:
        """
        Native color object from name (color name DB is backend specific)
        """
        pass

    @abstractmethod
    @delegatemethod
    def normalize(self, color) -> RGBAColor:
        """
        Takes a native color type and converts to RGBAColor
        """
        pass


class ColorDB (Singleton):
    named_colors = {}
    rgba_colors = {}
    backend_name = None

    def __init__(self):
        from ..gui_main import MFPGUI
        factory = ColorDBBackend.get_backend(ColorDB.backend_name)
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
