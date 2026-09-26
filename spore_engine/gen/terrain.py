from __future__ import annotations
import math
from ..core.canvas import Canvas
from ..core.glyphs import SHADE_CHARS
from ..core.color import Color, Gradient


#: Re-exported from core.glyphs so the ramp is defined once.
SHADE = SHADE_CHARS


class Terrain:
    def __init__(self, width: int, height: int, seed: int = 0):
        self.w = width
        self.h = height
        self.heightmap: list[list[float]] = [[0.0] * width for _ in range(height)]
        from ..sim.noise import PerlinNoise
        self.noise = PerlinNoise(seed)

    def generate(self, scale: float = 0.05, octaves: int = 6, persistence: float = 0.5):
        for y in range(self.h):
            for x in range(self.w):
                h = self.noise.fbm2(x * scale, y * scale, octaves, 2.0, persistence)
                h = (h + 1) * 0.5
                h = max(0, min(1, h))
                self.heightmap[y][x] = h

    def generate_island(self, scale: float = 0.06, octaves: int = 6):
        for y in range(self.h):
            for x in range(self.w):
                nx, ny = x / self.w - 0.5, y / self.h - 0.5
                dist = math.sqrt(nx * nx + ny * ny) * 2.0
                h = self.noise.fbm2(x * scale, y * scale, octaves, 2.0, 0.5)
                h = (h + 1) * 0.5
                h = max(0, h * (1 - dist * dist))
                self.heightmap[y][x] = h

    def get_height(self, x: float, y: float) -> float:
        ix, iy = int(x), int(y)
        if 0 <= ix < self.w - 1 and 0 <= iy < self.h - 1:
            fx, fy = x - ix, y - iy
            return (
                self.heightmap[iy][ix] * (1 - fx) * (1 - fy) +
                self.heightmap[iy][ix + 1] * fx * (1 - fy) +
                self.heightmap[iy + 1][ix] * (1 - fx) * fy +
                self.heightmap[iy + 1][ix + 1] * fx * fy
            )
        return 0

    def render_topdown(self, canvas: Canvas, ox: int = 0, oy: int = 0,
                       grad: Gradient | None = None, t: float = 0):
        g = grad or Gradient(
            Color(0, 40, 80), Color(50, 120, 50), Color(100, 180, 50),
            Color(160, 140, 40), Color(180, 120, 60), Color(200, 200, 200)
        )
        for y in range(min(self.h, canvas.height - oy)):
            for x in range(min(self.w, canvas.width - ox)):
                h = self.heightmap[y][x]
                ci = int(h * 9)
                canvas.set_pixel(x + ox, y + oy, SHADE[ci], g.at(h))

    def render_contour(self, canvas: Canvas, ox: int = 0, oy: int = 0,
                       levels: int = 5, fg: Color | None = None):
        col = fg or Color(150, 150, 100)
        for y in range(1, min(self.h, canvas.height - oy) - 1):
            for x in range(1, min(self.w, canvas.width - ox) - 1):
                h = self.heightmap[y][x]
                for level in range(levels):
                    t = (level + 1) / (levels + 1)
                    if abs(h - t) < 0.02:
                        above = self.heightmap[y - 1][x] > t
                        below = self.heightmap[y + 1][x] > t
                        left = self.heightmap[y][x - 1] > t
                        right = self.heightmap[y][x + 1] > t
                        if above != below or left != right:
                            canvas.set_pixel(x + ox, y + oy, '.', col)
                            break

    def render_3d_side(self, canvas: Canvas, ox: int = 0, oy: int = 0,
                       z_scale: float = 8, t: float = 0):
        hw = min(self.w, canvas.width - ox)
        for x in range(hw):
            profile = [self.heightmap[y][x] for y in range(self.h)]
            max(0, max(canvas.height - oy - 1, 0))
            for j, h in enumerate(profile):
                py = oy + canvas.height - 1 - int(h * z_scale) - j
                if py < oy or py >= oy + canvas.height:
                    continue
                depth = j / self.h
                hue = (0.1 + depth * 0.3 + t * 0.02) % 1.0
                color = Color.from_hsv(hue, 0.6, 0.3 + h * 0.7)
                ci = int(h * 9)
                canvas.set_pixel(x + ox, py, SHADE[ci], color)

    def render_wireframe_3d(self, canvas: Canvas, ox: int = 0, oy: int = 0,
                            scale: float = 1, t: float = 0):
        cx, cy = canvas.width // 2 + ox, canvas.height // 2 + oy
        angle = t * 0.2
        for y in range(self.h - 1):
            for x in range(self.w - 1):
                h = self.heightmap[y][x]
                h2 = self.heightmap[y + 1][x]
                h3 = self.heightmap[y][x + 1]
                rot = math.cos(angle)
                rot2 = math.sin(angle)
                pts = [
                    (int(cx + (x - self.w / 2) * scale * rot - h * scale * 2 * rot2),
                     int(cy + h * scale * 4 + (x - self.w / 2) * scale * rot2 * 0.5 + (y - self.h / 2) * scale * 0.5)),
                    (int(cx + (x - self.w / 2) * scale * rot - h2 * scale * 2 * rot2),
                     int(cy + h2 * scale * 4 + (x - self.w / 2) * scale * rot2 * 0.5 + ((y + 1) - self.h / 2) * scale * 0.5)),
                    (int(cx + ((x + 1) - self.w / 2) * scale * rot - h3 * scale * 2 * rot2),
                     int(cy + h3 * scale * 4 + ((x + 1) - self.w / 2) * scale * rot2 * 0.5 + (y - self.h / 2) * scale * 0.5)),
                ]
                col = Color.from_hsv((h * 0.5 + t * 0.02) % 1.0, 0.7, 0.5 + h * 0.5)
                for i in range(3):
                    j = (i + 1) % 3
                    canvas.draw_line(pts[i][0], pts[i][1], pts[j][0], pts[j][1], '.', col)


def marching_squares(heightmap: list[list[float]], level: float = 0.5) -> list[list[tuple[int, int]]]:
    contours = []
    h, w = len(heightmap), len(heightmap[0])
    for y in range(h - 1):
        for x in range(w - 1):
            tl = 1 if heightmap[y][x] >= level else 0
            tr = 1 if heightmap[y][x + 1] >= level else 0
            br = 1 if heightmap[y + 1][x + 1] >= level else 0
            bl = 1 if heightmap[y + 1][x] >= level else 0
            code = tl | (tr << 1) | (br << 2) | (bl << 3)
            if code == 0 or code == 15:
                continue
            _cx, _cy = x + 0.5, y + 0.5
            segs = {
                1: [(x + 0.5, y + 1), (x + 1, y + 0.5)],
                2: [(x + 1, y + 0.5), (x + 0.5, y)],
                3: [(x + 0.5, y + 1), (x + 0.5, y)],
                4: [(x, y + 0.5), (x + 0.5, y)],
                5: [(x + 0.5, y + 1), (x, y + 0.5), (x + 0.5, y), (x + 1, y + 0.5)],
                6: [(x, y + 0.5), (x + 1, y + 0.5)],
                7: [(x, y + 0.5), (x + 0.5, y)],
                8: [(x, y + 0.5), (x + 0.5, y)],
                9: [(x, y + 0.5), (x + 1, y + 0.5)],
                10: [(x + 0.5, y + 1), (x, y + 0.5), (x + 0.5, y), (x + 1, y + 0.5)],
                11: [(x, y + 0.5), (x + 0.5, y)],
                12: [(x + 0.5, y + 1), (x + 0.5, y)],
                13: [(x + 1, y + 0.5), (x + 0.5, y)],
                14: [(x + 0.5, y + 1), (x + 1, y + 0.5)],
            }.get(code, [])
            if segs:
                pts = [(int(p[0]), int(p[1])) for p in segs]
                contours.extend([(pts[i], pts[i + 1]) for i in range(0, len(pts), 2)])
    return contours
