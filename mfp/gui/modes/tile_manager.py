'''
tile_manager.py: Minor mode for controlling tile splits (imgui only)

Copyright (c) Bill Gribble <grib@billgribble.com>
'''

import asyncio
import copy
import dataclasses

from ..input_mode import InputMode
from ..colordb import ColorDB
from ..tile_manager import TileManager
from mfp import log
from mfp.gui_main import MFPGUI


class TileManagerMode (InputMode):
    def __init__(self, window):
        self.window = window
        self.manager = window.input_mgr

        self.recent_page_id = 0

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
        self.bind("{", self.swap_tile_left, "Swap tile to the left")
        self.bind("}", self.swap_tile_right, "Swap tile to the left")
        self.bind("<", self.swap_tile_up, "Swap tile upward")
        self.bind(">", self.swap_tile_down, "Swap tile downward")
        #self.bind(",", self.rotate_tiles_ccw, "Rotate tiles counter-clockwise")
        #self.bind(".", self.rotate_tiles_cw, "Rotate tiles clockwise")
        self.bind("UP", self.select_up, "Select tile above")
        self.bind("DOWN", self.select_down, "Select tile below")
        self.bind("LEFT", self.select_left, "Select tile to the left")
        self.bind("RIGHT", self.select_right, "Select tile to the right")
        self.bind("'", self.select_next, "Select next tile by number")
        self.bind(";", self.select_prev, "Select previous tile by number")
        #self.bind("x", self.close_tile, "Close tile")

        self.bind(None, self.dismiss_mode, "End tile management mode")

    def dismiss_mode(self, *args):
        self.manager.disable_minor_mode(self)
        return True

    def _select_tile(self, tile):
        try:
            next_patch = next(p for p in self.window.patches if p.display_info is tile)
        except StopIteration:
            next_patch = None
        if next_patch:
            self.window.layer_select(next_patch.selected_layer)

    def _select_neighbor(self, direction):
        target_tile = self.window.selected_patch.display_info
        neighbor_tiles = target_tile.neighbors.get(direction, [])
        if neighbor_tiles:
            neighbor_tile = sorted(neighbor_tiles, key=lambda t: t.origin_x)[0]
            self._select_tile(neighbor_tile)
        self.manager.disable_minor_mode(self)
        return True

    def select_next(self):
        current_id = self.window.selected_patch.display_info.tile_id
        current_page_id = self.window.selected_patch.display_info.page_id
        try:
            next_patch = next(
                p for p in sorted(self.window.patches, key=lambda p: p.display_info.tile_id)
                if p.display_info.page_id == current_page_id and p.display_info.tile_id > current_id
            )
        except StopIteration:
            next_patch = None
        if next_patch:
            self._select_tile(next_patch.display_info)

        self.manager.disable_minor_mode(self)
        return True

    def select_prev(self):
        current_id = self.window.selected_patch.display_info.tile_id
        current_page_id = self.window.selected_patch.display_info.page_id
        try:
            next_patch = next(
                p for p in sorted(self.window.patches, key=lambda p: -p.display_info.tile_id)
                if p.display_info.page_id == current_page_id and p.display_info.tile_id < current_id
            )
        except StopIteration:
            next_patch = None
        if next_patch:
            self._select_tile(next_patch.display_info)

        self.manager.disable_minor_mode(self)
        return True

    def select_up(self):
        return self._select_neighbor('top')

    def select_down(self):
        return self._select_neighbor('bottom')

    def select_left(self):
        return self._select_neighbor('left')

    def select_right(self):
        return self._select_neighbor('right')

    def _swap_tiles(self, target_tile, neighbor_tile):
        neighbor_fields = {
            k.name: copy.copy(getattr(neighbor_tile, k.name))
            for k in dataclasses.fields(neighbor_tile)
            if k.name != 'tile_id'
        }
        target_fields = {
            k.name: copy.copy(getattr(target_tile, k.name))
            for k in dataclasses.fields(target_tile)
            if k.name != 'tile_id'
        }
        for key, value in target_fields.items():
            setattr(neighbor_tile, key, value)

        for ndir, nlist in neighbor_tile.neighbors.items():
            new_list = []
            for neighbor in nlist:
                if neighbor is neighbor_tile:
                    new_list.append(target_tile)
                else:
                    new_list.append(neighbor)
            neighbor_tile.neighbors[ndir] = new_list

        for key, value in neighbor_fields.items():
            setattr(target_tile, key, value)

        for ndir, nlist in target_tile.neighbors.items():
            new_list = []
            for neighbor in nlist:
                if neighbor is target_tile:
                    new_list.append(neighbor_tile)
                else:
                    new_list.append(neighbor)
            target_tile.neighbors[ndir] = new_list

    def swap_tile_left(self):
        target_tile = self.window.selected_patch.display_info
        neighbor_tiles = target_tile.neighbors.get('left', [])
        if neighbor_tiles:
            neighbor_tile = sorted(neighbor_tiles, key=lambda t: t.origin_y)[0]
            self._swap_tiles(target_tile, neighbor_tile)

        self.manager.disable_minor_mode(self)
        return True

    def swap_tile_right(self):
        target_tile = self.window.selected_patch.display_info
        neighbor_tiles = target_tile.neighbors.get('right', [])
        if neighbor_tiles:
            neighbor_tile = sorted(neighbor_tiles, key=lambda t: t.origin_y)[0]
            self._swap_tiles(target_tile, neighbor_tile)
        self.manager.disable_minor_mode(self)
        return True

    def swap_tile_up(self):
        target_tile = self.window.selected_patch.display_info
        neighbor_tiles = target_tile.neighbors.get('top', [])
        if neighbor_tiles:
            neighbor_tile = sorted(neighbor_tiles, key=lambda t: t.origin_x)[0]
            self._swap_tiles(target_tile, neighbor_tile)
        self.manager.disable_minor_mode(self)
        return True

    def swap_tile_down(self):
        target_tile = self.window.selected_patch.display_info
        neighbor_tiles = target_tile.neighbors.get('bottom', [])
        if neighbor_tiles:
            neighbor_tile = sorted(neighbor_tiles, key=lambda t: t.origin_x)[0]
            self._swap_tiles(target_tile, neighbor_tile)
        self.manager.disable_minor_mode(self)
        return True

    def next_page(self):
        allowed_pages = sorted(list(set(t.page_id for t in self.window.canvas_tile_manager.tiles)))
        try:
            next_page = next(a for a in allowed_pages if a > self.window.canvas_tile_page)
            self.recent_page_id = self.window.canvas_tile_page
            self.window.canvas_tile_page = next_page
        except StopIteration:
            pass
        self.manager.disable_minor_mode(self)
        return True

    def prev_page(self):
        allowed_pages = reversed(sorted(list(set(t.page_id for t in self.window.canvas_tile_manager.tiles))))
        try:
            next_page = next(a for a in allowed_pages if a < self.window.canvas_tile_page)
            self.recent_page_id = self.window.canvas_tile_page
            self.window.canvas_tile_page = next_page
        except StopIteration:
            pass
        self.manager.disable_minor_mode(self)
        return True

    def recent_page(self):
        allowed_pages = set(t.page_id for t in self.window.canvas_tile_manager.tiles)
        if self.recent_page_id in allowed_pages:
            dest_page_id = self.recent_page_id
            self.recent_page_id = self.window.canvas_tile_page
            self.window.canvas_tile_page = dest_page_id
        self.manager.disable_minor_mode(self)
        return True

    def select_page(self, page_num):
        allowed_pages = set(t.page_id for t in self.window.canvas_tile_manager.tiles)
        if page_num in allowed_pages:
            self.recent_page_id = self.window.canvas_tile_page
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
