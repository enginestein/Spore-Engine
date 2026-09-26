from __future__ import annotations
import math
import random
from ..core.canvas import Canvas
from ..core.glyphs import SHADE_CHARS
from ..core.color import Color


#: Re-exported from core.glyphs so the ramp is defined once.
SHADE = SHADE_CHARS


class VolumetricFog:
    def __init__(self, width: int, height: int, density: float = 0.3):
        self.w = width
        self.h = height
        self.density = density
        self.fog_grid: list[list[float]] = [[0] * width for _ in range(height)]
        self.color = Color(200, 200, 220)
        self.scroll_x = 0
        self.scroll_y = 0

    def update(self, dt: float, wind_x: float = 0.2, wind_y: float = 0.05):
        self.scroll_x += wind_x * dt
        self.scroll_y += wind_y * dt
        decay = 0.98
        for y in range(self.h):
            for x in range(self.w):
                self.fog_grid[y][x] *= decay
                nx = (x + self.scroll_x * 0.1) * 0.05
                ny = (y + self.scroll_y * 0.1) * 0.05
                val = (1 + math.sin(nx * 3 + ny * 2 + dt * 0.3)) * 0.5
                if val > 0.7:
                    self.fog_grid[y][x] = min(1, self.fog_grid[y][x] + val * 0.02 * self.density)

    def apply(self, canvas: Canvas, light_pos: tuple[int, int] | None = None):
        """Composite the fog field over whatever canvas is handed in.

        The fog grid is sized when the object is constructed, but the canvas
        is not - terminals get resized. The previous version iterated the
        grid and indexed the canvas directly, so any size mismatch raised
        IndexError. The field is now sampled with nearest-neighbour scaling,
        so a fog built for 80x24 still covers a 12x6 buffer.
        """
        if not self.w or not self.h or not canvas.w or not canvas.h:
            return
        for y in range(canvas.h):
            gy = min(self.h - 1, y * self.h // canvas.h)
            grid_row = self.fog_grid[gy]
            for x in range(canvas.w):
                density = grid_row[min(self.w - 1, x * self.w // canvas.w)]
                if density < 0.01:
                    continue
                cell = canvas.buffer[y][x]
                if not cell.fg:
                    continue
                if light_pos:
                    lx, ly = light_pos
                    dist = math.hypot(x - lx, y - ly)
                    density *= max(0, 1 - dist / 40)
                lum = cell.fg.luminance
                int(lum * (1 - density * 0.5) + 200 * density * 0.5)
                r = min(255, int(cell.fg.r * (1 - density * 0.4) + self.color.r * density * 0.4))
                g = min(255, int(cell.fg.g * (1 - density * 0.4) + self.color.g * density * 0.4))
                b = min(255, int(cell.fg.b * (1 - density * 0.4) + self.color.b * density * 0.4))
                cell.fg = Color(r, g, b)

    def render(self, canvas: Canvas, ox: int = 0, oy: int = 0):
        for y in range(self.h):
            for x in range(self.w):
                d = self.fog_grid[y][x]
                if d > 0.05:
                    ci = min(9, int(d * 9))
                    canvas.set_pixel(x + ox, y + oy, SHADE[ci], self.color.mul(d), z=0)


class LightCone:
    def __init__(self, x: float, y: float, angle: float, width: float,
                 length: float, color: Color | None = None):
        self.x = x
        self.y = y
        self.angle = angle
        self.width = width
        self.length = length
        self.color = color or Color(255, 230, 180)
        self.intensity = 0.6
        self.flicker = 0

    def update(self, dt: float, flicker_amp: float = 0):
        if flicker_amp > 0:
            self.flicker += dt * 5
            self.intensity = 0.6 + math.sin(self.flicker) * flicker_amp

    def apply(self, canvas: Canvas, height_map: list[list[float]] | None = None):
        cx, cy = self.x, self.y
        for angle_step in range(int(self.width * 10)):
            a = self.angle - self.width / 2 + angle_step / 10
            for d in range(1, int(self.length * 2)):
                r = d / 2
                px = int(cx + math.cos(a) * r)
                py = int(cy + math.sin(a) * r)
                if px < 0 or px >= canvas.w or py < 0 or py >= canvas.h:
                    continue
                shadow = False
                if height_map:
                    hx = int(px * len(height_map[0]) / canvas.w)
                    hy = int(py * len(height_map) / canvas.h)
                    if 0 <= hx < len(height_map[0]) and 0 <= hy < len(height_map):
                        if height_map[hy][hx] > 0.3:
                            shadow = True
                if shadow:
                    continue
                atten = max(0, 1 - r / self.length) * self.intensity
                cell = canvas.buffer[py][px]
                if cell.fg:
                    r = min(255, int(cell.fg.r + self.color.r * atten * 0.3))
                    g = min(255, int(cell.fg.g + self.color.g * atten * 0.3))
                    b = min(255, int(cell.fg.b + self.color.b * atten * 0.3))
                    cell.fg = Color(r, g, b)
                canvas.set_pixel(px, py, '·', self.color.mul(atten), z=0)


class SmokePlume:
    def __init__(self, x: float, y: float, color: Color | None = None):
        self.x = x
        self.y = y
        self.color = color or Color(150, 150, 160)
        self.particles: list[dict] = []
        self.rate = 2
        self.timer = 0

    def update(self, dt: float, wind_x: float = 0.3):
        self.timer += dt
        while self.timer > 1 / self.rate:
            self.timer -= 1 / self.rate
            self.particles.append({
                'x': self.x + random.uniform(-1, 1),
                'y': self.y,
                'vx': random.uniform(-0.3, 0.3) + wind_x,
                'vy': random.uniform(-1.5, -0.5),
                'life': 1.0,
                'size': random.uniform(1, 3),
            })
        for p in self.particles[:]:
            p['x'] += p['vx'] * dt
            p['y'] += p['vy'] * dt
            p['vy'] -= 0.1 * dt
            p['vx'] += (random.random() - 0.5) * 0.2 * dt
            p['life'] -= dt * 0.4
            if p['life'] <= 0:
                self.particles.remove(p)

    def render(self, canvas: Canvas, ox: int = 0, oy: int = 0):
        for p in self.particles:
            ci = min(9, max(0, int(p['life'] * 9)))
            c = self.color.mul(p['life'])
            for dy in range(-1, 2):
                for dx in range(-1, 2):
                    px = int(p['x']) + ox + dx
                    py = int(p['y']) + oy + dy
                    if 0 <= px < canvas.w and 0 <= py < canvas.h:
                        canvas.set_pixel(px, py, SHADE[ci], c, z=1)


class VolumetricRenderer:
    def __init__(self, width: int, height: int):
        self.w = width
        self.h = height
        self.fog = VolumetricFog(width, height)
        self.cones: list[LightCone] = []
        self.plumes: list[SmokePlume] = []

    def add_cone(self, cone: LightCone):
        self.cones.append(cone)

    def add_plume(self, plume: SmokePlume):
        self.plumes.append(plume)

    def update(self, dt: float):
        self.fog.update(dt)
        for c in self.cones:
            c.update(dt)
        for p in self.plumes:
            p.update(dt)

    def render(self, canvas: Canvas, apply_to_scene: bool = True,
               height_map: list[list[float]] | None = None):
        for c in self.cones:
            c.apply(canvas, height_map)
        for p in self.plumes:
            p.render(canvas)
        if apply_to_scene:
            self.fog.apply(canvas)
        else:
            self.fog.render(canvas)
