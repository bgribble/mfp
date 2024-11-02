'''
tile_manager.py: Minor mode for controlling tile splits (imgui only)

Copyright (c) Bill Gribble <grib@billgribble.com>
'''

import asyncio
import copy
import dataclasses

from mfp import log
from mfp.gui_main import MFPGUI
from ..input_mode import InputMode
from ..tile_manager import TileManager


class TileManagerMode (InputMode):
    def __init__(self, window):
        self.window = window
        self.manager = window.input_mgr

        self.recent_page_id = 0

        InputMode.__init__(self, "Tile control", "Tile")

    @classmethod
    def init_bindings(cls):
        # window control
        cls._mode_prefix = "C-a"
        # tile control
        cls.cl_bind(
            "split-tile-vert", cls.split_vertical, "Split tile vertically",
            keysym="-", menupath="Window > |Split tile vertically"
        )
        cls.cl_bind(
            "split-tile-horiz", cls.split_horizontal, "Split tile horizontally",
            keysym="|", menupath="Window > |Split tile horizontally"
        )
        cls.cl_bind(
            "convert-tile-to-page", cls.create_page_from_tile, "Convert tile to page",
            keysym="!", menupath="Window > |Convert tile to page"
        )
        cls.cl_bind(
            "swap-tile-left", cls.swap_tile_left, "Swap tile to the left",
            keysym="{", menupath="Window > |Swap tile left"
        )
        cls.cl_bind(
            "swap-tile-right", cls.swap_tile_right, "Swap tile to the left",
            keysym="}", menupath="Window > |Swap tile right"
        )
        cls.cl_bind(
            "swap-tile-up", cls.swap_tile_up, "Swap tile upward",
            keysym="<", menupath="Window > |Swap tile upward"
        )
        cls.cl_bind(
            "swap-tile-down", cls.swap_tile_down, "Swap tile downward",
            keysym=">", menupath="Window > |Swap tile downward"
        )
        cls.cl_bind(
            "close-tile", cls.close_tile, "Close tile",
            keysym="x", menupath="Window > |Close tile"
        )
        cls.cl_bind(
            "create-tile-page", cls.create_page, "Create new page",
            keysym="c", menupath="Window > ||Create new page"
        )
        cls.cl_bind(
            "next-tile-page", cls.next_page, "Go to next page",
            keysym="n", menupath="Window > ||Go to next page"
        )
        cls.cl_bind(
            "prev-tile-page", cls.prev_page, "Go to previous page",
            keysym="p", menupath="Window > ||Go to prev page"
        )
        cls.cl_bind(
            "recent-tile-page", cls.recent_page, "Go to last-visited page",
            keysym="l", menupath="Window > ||Go to recent page"
        )
        cls.cl_bind(
            "go-tile-page-0", lambda mode: mode.select_page(0), "Go to page 0",
            keysym="0"
        )
        cls.cl_bind(
            "go-tile-page-1", lambda mode: mode.select_page(1), "Go to page 1",
            keysym="1"
        )
        cls.cl_bind(
            "go-tile-page-2", lambda mode: mode.select_page(2), "Go to page 2",
            keysym="2"
        )
        cls.cl_bind(
            "go-tile-page-3", lambda mode: mode.select_page(3), "Go to page 3",
            keysym="3"
        )
        cls.cl_bind(
            "go-tile-page-4", lambda mode: mode.select_page(4), "Go to page 4",
            keysym="4"
        )
        cls.cl_bind(
            "go-tile-page-5", lambda mode: mode.select_page(5), "Go to page 5",
            keysym="5"
        )
        cls.cl_bind(
            "go-tile-page-6", lambda mode: mode.select_page(6), "Go to page 6",
            keysym="6"
        )
        cls.cl_bind(
            "go-tile-page-7", lambda mode: mode.select_page(7), "Go to page 7",
            keysym="7"
        )
        cls.cl_bind(
            "go-tile-page-8", lambda mode: mode.select_page(8), "Go to page 8",
            keysym="8"
        )
        cls.cl_bind(
            "go-tile-page-9", lambda mode: mode.select_page(9), "Go to page 9",
            keysym="9"
        )
        cls.cl_bind(
            "go-tile-page-10", cls.close_window, "Close window and all tiles",
            keysym="&"
        )

        cls.cl_bind(
            "select-tile-up", cls.select_up, "Select tile above",
            keysym="UP"
        )
        cls.cl_bind(
            "select-tile-down", cls.select_down, "Select tile below",
            keysym="DOWN"
        )
        cls.cl_bind(
            "select-tile-left", cls.select_left, "Select tile to the left",
            keysym="LEFT"
        )
        cls.cl_bind(
            "select-tile-right", cls.select_right, "Select tile to the right",
            keysym="RIGHT"
        )
        cls.cl_bind(
            "select-tile-next", cls.select_next, "Select next tile by number",
            keysym="'"
        )
        cls.cl_bind(
            "select-tile-prev", cls.select_prev, "Select previous tile by number",
            keysym=";"
        )
        cls.cl_bind(cls.dismiss_mode, "End tile management mode", keysym=None)


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
        allowed_pages = sorted(list(set(
            t.page_id
            for t in self.window.canvas_tile_manager.tiles
            if t.page_id is not None
        )))
        try:
            next_page = next(a for a in allowed_pages if a > self.window.canvas_tile_page)
            self.recent_page_id = self.window.canvas_tile_page
            self.window.canvas_tile_page = next_page
        except StopIteration:
            if len(allowed_pages) > 0:
                self.recent_page_id = self.window.canvas_tile_page
                self.window.canvas_tile_page = allowed_pages[0]

        self.manager.disable_minor_mode(self)
        return True

    def prev_page(self):
        allowed_pages = list(reversed(sorted(list(set(
            t.page_id
            for t in self.window.canvas_tile_manager.tiles
            if t.page_id is not None
        )))))

        try:
            next_page = next(a for a in allowed_pages if a < self.window.canvas_tile_page)
            self.recent_page_id = self.window.canvas_tile_page
            self.window.canvas_tile_page = next_page
        except StopIteration:
            if len(allowed_pages) > 0:
                self.recent_page_id = self.window.canvas_tile_page
                self.window.canvas_tile_page = allowed_pages[-1]

        self.manager.disable_minor_mode(self)
        return True

    def recent_page(self):
        allowed_pages = set(
            t.page_id for t in self.window.canvas_tile_manager.tiles if t.page_id is not None
        )
        if self.recent_page_id in allowed_pages:
            dest_page_id = self.recent_page_id
            self.recent_page_id = self.window.canvas_tile_page
            self.window.canvas_tile_page = dest_page_id
        self.manager.disable_minor_mode(self)
        return True

    def select_page(self, page_num):
        allowed_pages = set(
            t.page_id for t in self.window.canvas_tile_manager.tiles
            if t.page_id is not None
        )
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

    async def create_page(self):
        tile = self.window.canvas_tile_manager.init_tile()
        self.recent_page_id = self.window.canvas_tile_page
        self.window.canvas_tile_page = tile.page_id
        await self.window.patch_new()
        self.manager.disable_minor_mode(self)
        return True

    def create_page_from_tile(self):
        current_tile = self.window.selected_patch.display_info
        self.window.canvas_tile_manager.convert_to_page(current_tile)
        self.recent_page_id = self.window.canvas_tile_page
        self.window.canvas_tile_page = current_tile.page_id
        self.manager.disable_minor_mode(self)
        return True

    async def close_window(self):
        page_id = self.window.selected_patch.display_info.page_id
        page_patches = [
            p for p in self.window.patches
            if p.display_info.page_id == page_id
        ]

        async def close_confirm(answer):
            if answer is not None:
                aa = answer.strip().lower()
                if aa in ['y', 'yes']:
                    await asyncio.wait([
                        asyncio.create_task(self.window.patch_close(p))
                        for p in page_patches
                    ])

        some_unsaved = [
            await MFPGUI().mfp.has_unsaved_changes(p.obj_id)
            for p in page_patches
        ]

        log.debug(f"page_patches: {page_patches}")
        log.debug(f"some_unsaved: {some_unsaved}")

        if some_unsaved and any(x for x in some_unsaved):
            await self.window.cmd_get_input(
                "Some patches have unsaved changes. Close anyway? [yN]",
                close_confirm,
                ''
            )
        else:
            await asyncio.wait([
                asyncio.create_task(self.window.patch_close(p))
                for p in page_patches
            ])

        return self.prev_page()

    async def close_tile(self):
        async def close_confirm(answer):
            if answer is not None:
                aa = answer.strip().lower()
                if aa in ['y', 'yes']:
                    await self.window.patch_close()

        p = self.window.selected_patch
        page_id = p.display_info.page_id
        if await MFPGUI().mfp.has_unsaved_changes(p.obj_id):
            await self.window.cmd_get_input(
                "Patch has unsaved changes. Close anyway? [yN]",
                close_confirm,
                ''
            )
        else:
            await self.window.patch_close()

        if not any(
            p for p in self.window.patches
            if p.display_info.page_id and p.display_info.page_id == page_id
        ):
            return self.prev_page()

        self.manager.disable_minor_mode(self)
        return True
