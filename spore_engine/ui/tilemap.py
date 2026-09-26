from __future__ import annotations
import random
from ..core.color import Color
from ..core.canvas import Canvas


class TileMap:
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.tiles = [[0] * width for _ in range(height)]
        self.collision = [[False] * width for _ in range(height)]

    def set_tile(self, x: int, y: int, tile_id: int):
        if 0 <= x < self.width and 0 <= y < self.height:
            self.tiles[y][x] = tile_id

    def get_tile(self, x: int, y: int) -> int:
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.tiles[y][x]
        return 0

    def set_collision(self, x: int, y: int, solid: bool = True):
        if 0 <= x < self.width and 0 <= y < self.height:
            self.collision[y][x] = solid

    def is_solid(self, x: int, y: int) -> bool:
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.collision[y][x]
        # Outside the grid counts as solid so movement is clamped at the
        # borders, except below the bottom edge where there is nothing to
        # collide with at all.
        return y < self.height

    def render(self, canvas: Canvas, tileset: dict[int, tuple[str, Color]],
               camera_x: int = 0, camera_y: int = 0, z: float = 0):
        for ty in range(canvas.h):
            world_y = ty + camera_y
            if world_y < 0 or world_y >= self.height: continue
            for tx in range(canvas.w):
                world_x = tx + camera_x
                if world_x < 0 or world_x >= self.width: continue
                tid = self.tiles[world_y][world_x]
                if tid in tileset:
                    ch, col = tileset[tid]
                    canvas.set_pixel(tx, ty, ch, col, z=z)

    def render_with_camera(self, canvas: Canvas, tileset: dict,
                           cam_x: float, cam_y: float, z: float = 0):
        ox = int(cam_x)
        oy = int(cam_y)
        for ty in range(canvas.h):
            wy = ty + oy
            if wy < 0 or wy >= self.height: continue
            for tx in range(canvas.h):
                wx = tx + ox
                if wx < 0 or wx >= self.width: continue
                tid = self.tiles[wy][wx]
                if tid in tileset:
                    ch, col = tileset[tid]
                    canvas.set_pixel(tx, ty, ch, col, z=z)


# -- AUTO-TILING ---------------------------------------------------

AUTO_TILE_LOOKUP = {}

def _build_auto_tile():
    global AUTO_TILE_LOOKUP
    if AUTO_TILE_LOOKUP:
        return
    keys = [
        (0,0,0,0,'┼'), (1,0,0,0,'┤'), (0,1,0,0,'┴'), (1,1,0,0,'┘'),
        (0,0,1,0,'├'), (1,0,1,0,'│'), (0,1,1,0,'└'), (1,1,1,0,'┴'),
        (0,0,0,1,'┬'), (1,0,0,1,'┐'), (0,1,0,1,'─'), (1,1,0,1,'┐'),
        (0,0,1,1,'┌'), (1,0,1,1,'─'), (0,1,1,1,'┌'), (1,1,1,1,'┼'),
    ]
    for n, e, s, w, ch in keys:
        AUTO_TILE_LOOKUP[(n, e, s, w)] = ch

def auto_tile_char(tilemap: TileMap, x: int, y: int, wall_id: int) -> str:
    _build_auto_tile()
    is_wall = tilemap.get_tile(x, y) == wall_id
    if not is_wall:
        return ' '
    n = tilemap.get_tile(x, y - 1) == wall_id
    s = tilemap.get_tile(x, y + 1) == wall_id
    e = tilemap.get_tile(x + 1, y) == wall_id
    w = tilemap.get_tile(x - 1, y) == wall_id
    return AUTO_TILE_LOOKUP.get((n, e, s, w), '#')


# -- PROCEDURAL MAP GENERATORS -------------------------------------

def generate_platformer(w: int, h: int, seed: int = 0) -> TileMap:
    rng = random.Random(seed)
    tm = TileMap(w, h)
    for x in range(w):
        tm.set_tile(x, h - 1, 1)
        tm.set_collision(x, h - 1, True)
    ground = h - 1
    for x in range(1, w - 1):
        if rng.random() < 0.15:
            ground += rng.choice([-1, 1])
        ground = max(h - 3, min(h - 1, ground))
        for y in range(ground, h):
            tm.set_tile(x, y, 1)
            tm.set_collision(x, y, True)
    for _ in range(w // 5):
        px = rng.randint(3, w - 3)
        ph = rng.randint(1, 3)
        pw = rng.randint(2, 5)
        solid = True
        for dx in range(pw):
            for dy in range(ph):
                cx = px + dx
                cy = ground - 1 - dy
                if 0 <= cx < w and cy >= 0:
                    if tm.is_solid(cx, cy + 1):
                        tm.set_tile(cx, cy, 1)
                        tm.set_collision(cx, cy, solid)
    return tm

def generate_cave(w: int, h: int, seed: int = 0, fill_prob: float = 0.45,
                  iterations: int = 4) -> TileMap:
    rng = random.Random(seed)
    tm = TileMap(w, h)
    for y in range(h):
        for x in range(w):
            if x == 0 or x == w - 1 or y == 0 or y == h - 1:
                tm.set_tile(x, y, 1)
                tm.set_collision(x, y, True)
            else:
                if rng.random() < fill_prob:
                    tm.set_tile(x, y, 1)
                    tm.set_collision(x, y, True)
    for _ in range(iterations):
        new_tiles = [row[:] for row in tm.tiles]
        new_coll = [row[:] for row in tm.collision]
        for y in range(1, h - 1):
            for x in range(1, w - 1):
                walls = sum(1 for dx in [-1, 0, 1] for dy in [-1, 0, 1]
                            if (dx != 0 or dy != 0) and tm.tiles[y + dy][x + dx] == 1)
                if walls > 4:
                    new_tiles[y][x] = 1
                    new_coll[y][x] = True
                else:
                    new_tiles[y][x] = 0
                    new_coll[y][x] = False
        tm.tiles = new_tiles
        tm.collision = new_coll
    return tm


# -- SIMPLE COLLISION ----------------------------------------------

def tile_collide(tilemap: TileMap, x: float, y: float,
                 radius: float = 0.4) -> bool:
    x1 = int(x - radius)
    x2 = int(x + radius)
    y1 = int(y - radius)
    y2 = int(y + radius)
    for ty in range(y1, y2 + 1):
        for tx in range(x1, x2 + 1):
            if tilemap.is_solid(tx, ty):
                return True
    return False


# -- CAMERA ---------------------------------------------------------

class TileCamera:
    def __init__(self, x: float = 0, y: float = 0, width: int = 80, height: int = 24):
        self.x = x
        self.y = y
        self.width = width
        self.height = height

    def follow(self, target_x: float, target_y: float, map_w: int, map_h: int,
               smooth: float = 0.1):
        target_cx = target_x - self.width / 2
        target_cy = target_y - self.height / 2
        self.x += (target_cx - self.x) * smooth
        self.y += (target_cy - self.y) * smooth
        self.x = max(0, min(map_w - self.width, self.x))
        self.y = max(0, min(map_h - self.height, self.y))

    @property
    def ox(self) -> int:
        return int(self.x)

    @property
    def oy(self) -> int:
        return int(self.y)
