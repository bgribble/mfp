"""
Helper to track and manipulate tiles in a tmux style
"""
import math
from dataclasses import dataclass, field
from mfp import log

FUZZ = 0.5


@dataclass
class Tile:
    title: str
    tile_id: int
    page_id: int
    origin_x: float = 0
    origin_y: float = 0
    width: float = 0
    height: float = 0
    frame_offset_x: float = 0
    frame_offset_y: float = 0
    view_x: float = 0
    view_y: float = 0
    view_zoom: float = 1.0
    neighbors: dict = field(default_factory=dict)
    in_use: bool = False


class TileManager:
    HORIZ = 1
    VERT = 2

    def __init__(self, total_width, total_height):
        self.total_width = total_width
        self.total_height = total_height
        self.tiles = []
        self.next_page_id = 0
        self.next_tile_id = 0

    def find_tile(self, **kwargs):
        if kwargs.get("new_page") or not self.tiles:
            page_id = self.next_page_id
            tile_id = self.next_tile_id
            self.next_page_id += 1
            self.next_tile_id += 1
            tile = Tile(
                title=kwargs.get("title", "New tile"),
                tile_id=tile_id,
                page_id=page_id,
                width=self.total_width,
                height=self.total_height
            )
            self.add_tile(tile)
            return tile

        # are there any free tiles?
        for tile in self.tiles:
            if tile.in_use:
                continue
            found_match = True
            for attr, val in kwargs.items():
                if getattr(tile, attr) != val:
                    found_match = False
                    break
            if found_match:
                return tile

        return self.alloc_tile(**kwargs)

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
            frame_offset_x=0,
            frame_offset_y=0,
            view_x=0,
            view_y=0,
            view_zoom=1.0,
            width=self.total_width,
            height=self.total_height,
            page_id=self.next_page_id,
            tile_id=self.next_tile_id,
        )

        # optional overrides for tile fields
        for k, v in kwargs.items():
            setattr(t, k, v)

        self.next_page_id += 1
        self.next_tile_id += 1
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
            t for t in self.tiles if t.page_id == page_id
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

    def _check_neighbor(self, tile_1, tile_2, direction):
        """
        return True if tile_1 and tile_2 overlap in "direction"
        (as seen from tile_1) and are adjoining in the cross dimension
        """
        def fequal(v1, v2):
            return math.fabs(v1 - v2) < FUZZ

        adjoining = False
        overlapping = False

        if direction == 'left':
            adjoining = fequal(
                tile_2.origin_x + tile_2.width,
                tile_1.origin_x
            )
        elif direction == 'right':
            adjoining = fequal(
                tile_1.origin_x + tile_1.width,
                tile_2.origin_x
            )
        elif direction == 'top':
            adjoining = fequal(
                tile_2.origin_y + tile_2.height,
                tile_1.origin_y
            )
        elif direction == 'bottom':
            adjoining = fequal(
                tile_1.origin_y + tile_1.height,
                tile_2.origin_y
            )

        if direction in ['left', 'right']:
            overlapping = (
                (tile_1.origin_y + tile_1.height) >= tile_2.origin_y
                and tile_1.origin_y <= (tile_2.origin_y + tile_2.height)
            )
        else:
            overlapping = (
                (tile_1.origin_x + tile_1.width) >= tile_2.origin_x
                and tile_1.origin_x <= (tile_2.origin_x + tile_2.width)
            )

        return adjoining and overlapping

    def _connect_neighbor(self, tile_1, tile_2, direction):
        """
        point tile_1 and tile_2 at each other as neighbors
        """
        opps = dict(left='right', right='left', top='bottom', bottom='top')
        n = tile_1.neighbors.setdefault(direction, [])
        if tile_2 not in n:
            n.append(tile_2)
        n = tile_2.neighbors.setdefault(opps[direction], [])
        if tile_1 not in n:
            n.append(tile_1)

    def _remove_neighbor(self, tile_1, tile_2, direction):
        neighbors = tile_1.neighbors.get(direction, [])
        if tile_2 in neighbors:
            tile_1.neighbors[direction] = [
                n for n in neighbors if n != tile_2
            ]

    def remove_tile(self, tile):
        """
        Remove tile, adjusting neighbors to fill space
        """
        opps = dict(left='right', right='left', top='bottom', bottom='top')

        made_space = False

        # find a neighbor that can expand to fill this space
        for neighbor_dir in ['left', 'right', 'top', 'bottom']:
            scalable_direction = True
            neighbors = tile.neighbors.get(neighbor_dir, [])
            if not neighbors:
                continue

            for n in neighbors:
                # if, for a direction, all the neighbors in that direction
                # only have "tile" as a neighbor in the opposite direction,
                # then it's safe to scale the neighbors in that direction to
                # fill tile's space
                opp_neighbors = n.neighbors.get(opps[neighbor_dir], [])
                if len(opp_neighbors) != 1:
                    scalable_direction = False
                    break

            if scalable_direction:
                # "neighbors" is the set of tiles we are adjusting.
                # we need to potentially connect them as neighbors with
                # "tile"'s neighbors on the opposite side
                for adjusted_neighbor in neighbors:
                    if neighbor_dir == 'left':
                        adjusted_neighbor.width += tile.width
                    elif neighbor_dir == 'right':
                        adjusted_neighbor.width += tile.width
                        adjusted_neighbor.origin_x -= tile.width
                    elif neighbor_dir == 'top':
                        adjusted_neighbor.height += tile.height
                    elif neighbor_dir == 'bottom':
                        adjusted_neighbor.height += tile.height
                        adjusted_neighbor.origin_y -= tile.height

                    for potential_neighbor in tile.neighbors.get(opps[neighbor_dir], []):
                        if self._check_neighbor(potential_neighbor, adjusted_neighbor, neighbor_dir):
                            self._connect_neighbor(potential_neighbor, adjusted_neighbor, neighbor_dir)
                        self._remove_neighbor(potential_neighbor, tile, neighbor_dir)
                made_space = True
                break

        for ndir, neighbors in tile.neighbors.items():
            for n in neighbors:
                reverse_neighbors = n.neighbors.setdefault(opps[ndir], [])
                if tile in reverse_neighbors:
                    reverse_neighbors.remove(tile)
                else:
                    log.debug(f"[tile] While removing {tile} - neighbor {n} not in reverse")

        tile.page_id = None
        tile.neighbors = {}
        self.tiles = [t for t in self.tiles if t != tile]

    def convert_to_page(self, tile):
        self.remove_tile(tile)
        self.add_tile(tile)
        tile.page_id = self.next_page_id
        self.next_page_id += 1
        self.maximize_tile(tile)

    def split_tile(self, tile, direction):
        dw = tile.width / 2 if direction == TileManager.HORIZ else 0
        dh = tile.height / 2 if direction == TileManager.VERT else 0

        new_tile = Tile(
            title='New tile',
            origin_x=tile.origin_x + dw,
            origin_y=tile.origin_y + dh,
            view_x=0,
            view_y=0,
            view_zoom=1.0,
            frame_offset_x=tile.frame_offset_x,
            frame_offset_y=tile.frame_offset_y,
            width=tile.width - dw,
            height=tile.height - dh,
            page_id=tile.page_id,
            tile_id=self.next_tile_id,
        )
        self.next_tile_id += 1

        tile.width -= dw
        tile.height -= dh

        new_neighbors = {}
        old_neighbors = {}

        if direction == TileManager.HORIZ:
            old_neighbors['left'] = [*tile.neighbors.get('left', [])]
            old_neighbors['right'] = [new_tile]

            new_neighbors['left'] = [tile]
            new_neighbors['right'] = [*tile.neighbors.get('right', [])]

            for nbr in new_neighbors.get('right'):
                nbr.neighbors['left'] = [
                    n for n in (nbr.neighbors['left'] or [])
                    if n is not tile
                ]
                nbr.neighbors['left'].append(new_tile)

            for nbr in tile.neighbors.get('top') or []:
                if self._check_neighbor(tile, nbr, 'top'):
                    old = old_neighbors.setdefault('top', [])
                    old.append(nbr)
                else:
                    nbr.neighbors['bottom'] = [
                        n for n in (nbr.neighbors['bottom'] or [])
                        if n is not tile
                    ]
                if self._check_neighbor(new_tile, nbr, 'top'):
                    new = new_neighbors.setdefault('top', [])
                    new.append(nbr)
                    nbr.neighbors['bottom'].append(new_tile)

            for nbr in tile.neighbors.get('bottom') or []:
                if self._check_neighbor(tile, nbr, 'bottom'):
                    old = old_neighbors.setdefault('bottom', [])
                    old.append(nbr)
                else:
                    nbr.neighbors['top'] = [
                        n for n in (nbr.neighbors['top'] or [])
                        if n is not tile
                    ]
                if self._check_neighbor(new_tile, nbr, 'bottom'):
                    new = new_neighbors.setdefault('bottom', [])
                    new.append(nbr)
                    nbr.neighbors['top'].append(new_tile)
        else:
            old_neighbors['top'] = [*tile.neighbors.get('top', [])]
            old_neighbors['bottom'] = [new_tile]

            new_neighbors['top'] = [tile]
            new_neighbors['bottom'] = [*tile.neighbors.get('bottom', [])]

            for nbr in new_neighbors.get('bottom'):
                nbr.neighbors['top'] = [
                    n for n in nbr.neighbors.get('top', [])
                    if n is not tile
                ]
                nbr.neighbors['top'].append(new_tile)

            for nbr in tile.neighbors.get('left', []):
                if self._check_neighbor(tile, nbr, 'left'):
                    old = old_neighbors.setdefault('left', [])
                    old.append(nbr)
                else:
                    nbr.neighbors['right'] = [
                        n for n in (nbr.neighbors['right'] or [])
                        if n is not tile
                    ]
                if self._check_neighbor(new_tile, nbr, 'left'):
                    new = new_neighbors.setdefault('left', [])
                    new.append(nbr)
                    nbr.neighbors['right'].append(new_tile)

            for nbr in tile.neighbors.get('right') or []:
                if self._check_neighbor(tile, nbr, 'right'):
                    old = old_neighbors.setdefault('right', [])
                    old.append(nbr)
                else:
                    nbr.neighbors['left'] = [
                        n for n in nbr.neighbors.get('left', [])
                        if n is not tile
                    ]
                if self._check_neighbor(new_tile, nbr, 'right'):
                    new = new_neighbors.setdefault('right', [])
                    new.append(nbr)
                    nbr.neighbors['left'].append(new_tile)

        tile.neighbors = old_neighbors
        new_tile.neighbors = new_neighbors

        self.add_tile(new_tile)

        return (tile, new_tile)

    def resize_tile(self, tile, target_w, target_h, target_x, target_y):
        """
        resize_tile: shuffle other tiles to change target tile
        """
        def tiny(v1):
            return abs(v1) < .001

        def change_tile(t, side, amount):
            if side == "top":
                t.origin_y += amount
                t.height -= amount
            elif side == "bottom":
                t.height += amount
            elif side == "left":
                t.origin_x += amount
                t.width -= amount
            elif side == "right":
                t.width += amount

        changes = dict(left=0, right=0, top=0, bottom=0)
        opposites = dict(left="right", right="left", top="bottom", bottom="top")

        delta_w = target_w - tile.width
        delta_h = target_h - tile.height
        delta_x = target_x - tile.origin_x
        delta_y = target_y - tile.origin_y

        if not tiny(delta_w):
            if abs(delta_w) <= abs(delta_x):
                changes["left"] = -delta_w
                target_x = tile.origin_x - delta_w
                target_y = tile.origin_y
            else:
                changes["right"] = delta_w
                target_x = tile.origin_x
                target_y = tile.origin_y
        if abs(delta_h) :
            if abs(delta_h) <= abs(delta_y):
                changes["top"] = -delta_h
                target_x = tile.origin_x
                target_y = tile.origin_y - delta_h
            else:
                changes["bottom"] = delta_h
                target_y = tile.origin_y
                target_x = tile.origin_x

        made_changes = False
        for direction, amount in changes.items():
            if tiny(amount):
                # don't make insignificant changes
                continue
            if not tile.neighbors.get(direction):
                # ignore changes on sides that border the window frame
                continue
            made_changes = True

            # resize neighbors in the direction we are growing/shrinking
            my_neighbors = tile.neighbors.get(direction)
            for neighbor in my_neighbors:
                oppo = opposites[direction]
                change_tile(neighbor, oppo, amount)
                their_neighbors = neighbor.neighbors.get(oppo, [])
                for theirs in their_neighbors:
                    if theirs != tile:
                        change_tile(theirs, direction, amount)

        if made_changes:
            tile.width = target_w
            tile.height = target_h
            tile.origin_x = target_x
            tile.origin_y = target_y
