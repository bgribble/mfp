"""
Helper to track and manipulate tiles in a tmux style
"""
from dataclasses import dataclass
from mfp import log


@dataclass
class Tile:
    title: str
    origin_x: float
    origin_y: float
    width: float
    height: float
    view_x: float 
    view_y: float
    view_zoom: float
    id_page: int
    id_tile: int
    neighbors: dict

class TileManager:
    HORIZ = 1
    VERT = 2

    def __init__(self, total_width, total_height):
        self.total_width = total_width
        self.total_height = total_height
        self.tiles = []
        self.next_id_page = 0
        self.next_id_tile = 0

    def resize(self, new_width, new_height):
        """
        resize the entire tile manager space, just scaling all the tiles
        """
        width_scale = new_width / self.total_width
        height_scale = new_height / self.total_height

        for tile in self.tiles:
            tile.origin_x = tile.origin_x * width_scale
            tile.origin_y = tile.origin_y * height_scale
            tile.width = tile.width * width_scale
            tile.height = tile.height * height_scale

        self.total_width = new_width
        self.total_height = new_height

    def init_tile(self, **kwargs):
        t = Tile(
            title="Initial tile",
            origin_x=0,
            origin_y=0,
            width=self.total_width,
            height=self.total_height,
            view_x=0,
            view_y=0,
            view_zoom=1.0,
            id_page=self.next_id_page,
            id_tile=self.next_id_tile,
            neighbors={}
        )

        # optional overrides for tile fields
        for k, v in kwargs.items():
            setattr(t, k, v)

        self.next_id_page += 1
        self.next_id_tile += 1
        self.tiles.append(t)
        return t

    def add_tile(self, tile):
        if tile not in self.tiles:
            self.tiles.append(tile)

    def maximize_tile(self, tile):
        tile.origin_x = 0
        tile.origin_y = 0
        tile.width = self.total_width
        tile.height = self.total_height

    def get_page(self, page_id):
        return [
            t for t in self.tiles if t.id_page == page_id
        ]

    def alloc_tile(self, **kwargs):
        """
        Create a new tile by subdividing the largest one
        """
        if not self.tiles:
            return self.init_tile(**kwargs)

        areas = {
            (t.width * t.height): t
            for t in self.tiles
        }
        biggest_tile = areas[max(areas)]
        if biggest_tile.width > biggest_tile.height:
            divide_dir = TileManager.HORIZ
        else:
            divide_dir = TileManager.VERT

        old_tile, new_tile = self.split_tile(biggest_tile, divide_dir)
        return new_tile

    def convert_to_page(self, tile):
        tile.id_page = self.next_id_page
        self.next_id_page += 1
        self.maximize_tile(tile)

    def split_tile(self, tile, direction):
        dw = tile.width / 2 if direction == TileManager.HORIZ else 0
        dh = tile.height / 2 if direction == TileManager.VERT else 0

        new_tile = Tile(
            title="New tile",
            origin_x=tile.origin_x + dw,
            origin_y=tile.origin_y + dh,
            width=tile.width - dw,
            height=tile.height - dh,
            view_x=0, 
            view_y=0,
            view_zoom=1.0,
            id_page=tile.id_page,
            id_tile=self.next_id_tile,
            neighbors={}
        )
        self.next_id_tile += 1

        tile.width -= dw
        tile.height -= dh

        new_neighbors = {}
        old_neighbors = {}

        if direction == TileManager.HORIZ:
            old_neighbors['left'] = tile.neighbors.get('left') or []
            old_neighbors['right'] = [ new_tile ]

            new_neighbors['left'] = [ tile ]
            new_neighbors['right'] = tile.neighbors.get('right') or []

            for nbr in tile.neighbors.get('top') or []:
                if (
                    (nbr.origin_x + neighbor.width) >= tile.origin_x
                    and nbr.origin_x <= (tile.origin_x + tile.width)
                ):
                    old_top = old_neighbors.setdefault("top", [])
                    old_top.append(nbr)
                else:
                    nbr.neighbors['bottom'] = [
                        n for n in (nbr.neighbors['bottom'] or [])
                        if n is not tile
                    ]
                if (
                    (nbr.origin_x + nbr.width) >= new_tile.origin_x
                    and nbr.origin_x <= (new_tile.origin_x + new_tile.width)
                ):
                    new_top = new_neighbors.setdefault("top", [])
                    new_top.append(nbr)

            for nbr in tile.neighbors.get('bottom') or []:
                if (
                    (nbr.origin_x + nbr.width) >= tile.origin_x
                    and nbr.origin_x <= (tile.origin_x + tile.width)
                ):
                    old_top = old_neighbors.setdefault("bottom", [])
                    old_top.append(nbr)
                else:
                    nbr.neighbors['top'] = [
                        n for n in (nbr.neighbors['top'] or [])
                        if n is not tile
                    ]
                if (
                    (nbr.origin_x + nbr.width) >= new_tile.origin_x
                    and nbr.origin_x <= (new_tile.origin_x + new_tile.width)
                ):
                    new_top = new_neighbors.setdefault("bottom", [])
                    new_top.append(nbr)
        else:
            old_neighbors['top'] = tile.neighbors.get('top') or []
            old_neighbors['bottom'] = [new_tile]

            new_neighbors['top'] = [tile]
            new_neighbors['bottom'] = tile.neighbors.get('bottom') or []

            for nbr in tile.neighbors.get('left') or []:
                if (
                    (nbr.origin_y + nbr.height) >= tile.origin_y
                    and nbr.origin_y <= (tile.origin_y + tile.height)
                ):
                    old_left = old_neighbors.setdefault("left", [])
                    old_left.append(nbr)
                else:
                    nbr.neighbors['right'] = [
                        n for n in (nbr.neighbors['right'] or [])
                        if n is not tile
                    ]
                if (
                    (nbr.origin_y + nbr.height) >= new_tile.origin_y
                    and nbr.origin_y <= (new_tile.origin_y + new_tile.height)
                ):
                    new_left = new_neighbors.setdefault("left", [])
                    new_left.append(nbr)

            for nbr in tile.neighbors.get('right') or []:
                if (
                    (nbr.origin_y + nbr.height) >= tile.origin_y
                    and nbr.origin_y <= (tile.origin_y + tile.height)
                ):
                    old_left = old_neighbors.setdefault("right", [])
                    old_left.append(nbr)
                else:
                    nbr.neighbors['left'] = [
                        n for n in (nbr.neighbors['left'] or [])
                        if n is not tile
                    ]
                if (
                    (nbr.origin_y + nbr.height) >= new_tile.origin_y
                    and nbr.origin_y <= (new_tile.origin_y + new_tile.height)
                ):
                    new_left = new_neighbors.setdefault("right", [])
                    new_left.append(nbr)
        tile.neighbors = old_neighbors
        new_tile.neighbors = new_neighbors

        self.add_tile(new_tile)
        return (tile, new_tile)
