'''
tile_manager.py: Minor mode for controlling tile splits (imgui only)

Copyright (c) Bill Gribble <grib@billgribble.com>
'''

import asyncio
from ..input_mode import InputMode
from ..colordb import ColorDB
from ..tile_manager import TileManager
from mfp import log
from mfp.gui_main import MFPGUI


class TileManagerMode (InputMode):
    def __init__(self, window):
        self.window = window
        self.manager = window.input_mgr

        self.recent_page = 0

        InputMode.__init__(self, "Tile control", "Tile")

        # window control
        #self.bind("c", self.create_page, "Create new page")
        self.bind("n", self.next_page, "Go to next page")
        self.bind("p", self.prev_page, "Go to previous page")
        self.bind("l", self.recent_page, "Go to last-visited page")
        self.bind("0", lambda: self.select_page(0), "Go to page 0")
        self.bind("1", lambda: self.select_page(1), "Go to page 1")
        self.bind("2", lambda: self.select_page(2), "Go to page 2")
        self.bind("3", lambda: self.select_page(3), "Go to page 3")
        self.bind("4", lambda: self.select_page(4), "Go to page 4")
        self.bind("5", lambda: self.select_page(5), "Go to page 5")
        self.bind("6", lambda: self.select_page(6), "Go to page 6")
        self.bind("7", lambda: self.select_page(7), "Go to page 7")
        self.bind("8", lambda: self.select_page(8), "Go to page 8")
        self.bind("9", lambda: self.select_page(9), "Go to page 9")
        #self.bind("&", self.close_window, "Close window and all tiles")

        # tile control
        self.bind("-", self.split_vertical, "Split tile vertically")
        self.bind("|", self.split_horizontal, "Split tile horizontally")
        self.bind("!", self.create_page_from_tile, "Convert tile to page")
        #self.bind("{", self.swap_tile_left, "Swap tile to the left")
        #self.bind("}", self.swap_tile_right, "Swap tile to the left")
        #self.bind("<", self.swap_tile_up, "Swap tile upward")
        #self.bind(">", self.swap_tile_down, "Swap tile downward")
        #self.bind(",", self.rotate_tiles_ccw, "Rotate tiles counter-clockwise")
        #self.bind(".", self.rotate_tiles_cw, "Rotate tiles clockwise")
        #self.bind("UP", self.select_up, "Select tile above")
        #self.bind("DOWN", self.select_down, "Select tile below")
        #self.bind("LEFT", self.select_left, "Select tile to the left")
        #self.bind("RIGHT", self.select_right, "Select tile to the right")
        #self.bind("o", self.select_next, "Select next tile by number")
        #self.bind(";", self.select_last, "Select last tile by number")
        #self.bind("x", self.close_tile, "Close tile")

    def next_page(self):
        allowed_pages = sorted(list(set(t.page_id for t in self.window.canvas_tile_manager.tiles)))
        try:
            next_page = next(a for a in allowed_pages if a > self.window.canvas_tile_page)
            self.recent_page = self.window.canvas_tile_page
            self.window.canvas_tile_page = next_page
        except StopIteration:
            pass
        self.manager.disable_minor_mode(self)
        return True

    def prev_page(self):
        allowed_pages = reversed(sorted(list(set(t.page_id for t in self.window.canvas_tile_manager.tiles))))
        try:
            next_page = next(a for a in allowed_pages if a < self.window.canvas_tile_page)
            self.recent_page = self.window.canvas_tile_page
            self.window.canvas_tile_page = next_page
        except StopIteration:
            pass
        self.manager.disable_minor_mode(self)
        return True

    def recent_page(self):
        allowed_pages = set(t.page_id for t in self.window.canvas_tile_manager.tiles)
        if self.recent_page in allowed_pages:
            self.recent_page = self.window.canvas_tile_page
            self.window.canvas_tile_page = self.recent_page
        self.manager.disable_minor_mode(self)
        return True

    def select_page(self, page_num):
        allowed_pages = set(t.page_id for t in self.window.canvas_tile_manager.tiles)
        if page_num in allowed_pages:
            self.recent_page = self.window.canvas_tile_page
            self.window.canvas_tile_page = page_num
        self.manager.disable_minor_mode(self)
        return True

    async def split_vertical(self):
        tile_mgr = self.window.canvas_tile_manager
        current_tile = self.window.selected_patch.display_info
        tile_mgr.split_tile(current_tile, TileManager.VERT)
        self.manager.disable_minor_mode(self)
        await self.window.patch_new()
        return True

    async def split_horizontal(self):
        tile_mgr = self.window.canvas_tile_manager
        current_tile = self.window.selected_patch.display_info
        tile_mgr.split_tile(current_tile, TileManager.HORIZ)
        self.manager.disable_minor_mode(self)
        await self.window.patch_new()
        return True

    def create_page_from_tile(self):
        current_tile = self.window.selected_patch.display_info
        self.window.canvas_tile_manager.convert_to_page(current_tile)
        self.manager.disable_minor_mode(self)
        return True
