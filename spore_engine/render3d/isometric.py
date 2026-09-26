from __future__ import annotations
from ..core.canvas import Canvas
from ..core.color import Color, WHITE


class IsoTile:
    def __init__(self, gx: int, gy: int, gz: int = 0,
                 char: str = '█', fg: Color = WHITE,
                 bg: Color = None, height: float = 1.0):
        self.gx = gx
        self.gy = gy
        self.gz = gz
        self.char = char
        self.fg = fg
        self.bg = bg
        self.height = height

    def screen_pos(self, origin_x: float, origin_y: float,
                   tile_w: float, tile_h: float) -> tuple[float, float]:
        sx = origin_x + (self.gx - self.gy) * tile_w
        sy = origin_y + (self.gx + self.gy) * tile_h * 0.5 - self.gz * tile_h * 0.5
        return sx, sy


class IsoCamera:
    def __init__(self):
        self.ox = 0.0
        self.oy = 0.0
        self.zoom = 1.0
        self.rot = 0.0


class IsoMap:
    def __init__(self, width: int, height: int, tile_w: float = 4, tile_h: float = 2):
        self.w = width
        self.h = height
        self.tile_w = tile_w
        self.tile_h = tile_h
        self.tiles: dict[tuple[int, int, int], IsoTile] = {}
        self.camera = IsoCamera()

    def set_tile(self, x: int, y: int, z: int, tile: IsoTile):
        self.tiles[(x, y, z)] = tile

    def get_tile(self, x: int, y: int, z: int) -> IsoTile | None:
        return self.tiles.get((x, y, z))

    def render(self, c: Canvas):
        cx, cy = c.w / 2 + self.camera.ox, c.h / 2 + self.camera.oy
        tw = self.tile_w * self.camera.zoom
        th = self.tile_h * self.camera.zoom

        visible = []
        for (gx, gy, gz), tile in self.tiles.items():
            sx, sy = tile.screen_pos(cx, cy, tw, th)
            if sx < -tw * 2 or sx > c.w + tw * 2 or sy < -th * 2 or sy > c.h + th * 2:
                continue
            visible.append((gz + gy + gx, tile, sx, sy))

        visible.sort(key=lambda v: v[0])

        for _, tile, sx, sy in visible:
            px, py = int(sx), int(sy)
            if 0 <= px < c.w and 0 <= py < c.h:
                c.set_pixel(px, py, tile.char, tile.fg, tile.bg, z=5)

            if tile.bg:
                for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    tx, ty = px + dx, py + dy
                    if 0 <= tx < c.w and 0 <= ty < c.h:
                        c.set_pixel(tx, ty, ' ', bg=tile.bg.mul(0.4), z=4)

            side_x, side_y = px - 1, py + 1
            if 0 <= side_x < c.w and 0 <= side_y < c.h:
                c.set_pixel(side_x, side_y, '░', tile.fg.mul(0.5), z=4)

    def generate_island(self, height_map: list[list[float]]):
        for gy in range(self.h):
            for gx in range(self.w):
                if gx < len(height_map) and gy < len(height_map[0]):
                    h = height_map[gy][gx]
                    z = int(h * 5)
                    hue = 0.25 + h * 0.15
                    b = 0.3 + h * 0.6
                    col = Color.from_hsv(hue, 0.6, b)
                    self.set_tile(gx, gy, z, IsoTile(gx, gy, z,
                        '█', col, height=h))
                    for iz in range(1, z + 1):
                        dark = col.mul(0.5 + 0.5 * (1 - iz / max(1, z)))
                        self.set_tile(gx, gy, iz, IsoTile(gx, gy, iz,
                            '▓', dark, height=h))
