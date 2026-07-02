from __future__ import annotations
import math
import random
from typing import Optional, Callable
from ..core.color import Color, Gradient, PALETTES, BLACK, WHITE, DIM
from ..core.canvas import Canvas, SHADE_CHARS
from ..sim.noise import PerlinNoise


class ParallaxLayer:
    def __init__(self, width: int, height: int, speed: float = 1.0,
                 z: float = 0.0):
        self.width = width
        self.height = height
        self.speed = speed
        self.z = z
        self.fn: Optional[Callable] = None

    def scroll(self, camera_x: float) -> float:
        return camera_x * self.speed

    def render(self, canvas: Canvas, camera_x: float, camera_y: float):
        if self.fn:
            ox = self.scroll(camera_x) % self.width
            self.fn(canvas, ox, camera_y, self.z)


class ParallaxScenery:
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.layers: list[ParallaxLayer] = []

    def add(self, layer: ParallaxLayer):
        self.layers.append(layer)
        return layer

    def render(self, canvas: Canvas, camera_x: float = 0, camera_y: float = 0):
        for layer in sorted(self.layers, key=lambda l: l.z):
            layer.render(canvas, camera_x, camera_y)


class Cloud:
    def __init__(self, x: float, y: float, w: int, h: int, speed: float,
                 color: Color, z: float = 0):
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.speed = speed
        self.color = color
        self.z = z
        self.shape: list[list[int]] = []
        self._generate()

    def _generate(self):
        rng = random.Random(abs(int(self.x * 100 + self.y)))
        for iy in range(self.h):
            row = []
            for ix in range(self.w):
                v = 1 if rng.random() < 0.65 else 0
                row.append(v)
            self.shape.append(row)

    def update(self, dt: float):
        self.x += self.speed * dt

    def render(self, canvas: Canvas, ox: float = 0, z: float = 0):
        for iy, row in enumerate(self.shape):
            for ix, v in enumerate(row):
                if v:
                    cx = int(self.x + ix - ox)
                    cy = int(self.y + iy)
                    if 0 <= cx < canvas.w and 0 <= cy < canvas.h:
                        shade = SHADE_CHARS[min(7 + v, len(SHADE_CHARS) - 1)]
                        canvas.set_pixel(cx, cy, shade, self.color, z=z)


class CloudLayer:
    def __init__(self, count: int = 8, min_y: int = 1, max_y: int = 8,
                 min_w: int = 6, max_w: int = 20,
                 speed_range: tuple[float, float] = (0.2, 0.8),
                 color: Optional[Color] = None):
        self.clouds: list[Cloud] = []
        self.min_y = min_y
        self.max_y = max_y
        self.min_w = min_w
        self.max_w = max_w
        self.speed_range = speed_range
        self.color = color or Color(200, 200, 220)
        for _ in range(count):
            self._spawn_cloud(random.uniform(0, 200))

    def _spawn_cloud(self, x: float):
        w = random.randint(self.min_w, self.max_w)
        h = random.randint(2, 4)
        y = random.randint(self.min_y, self.max_y)
        speed = random.uniform(*self.speed_range)
        self.clouds.append(Cloud(x, y, w, h, speed, self.color))

    def update(self, dt: float, screen_w: int):
        self.clouds = [c for c in self.clouds if c.x < screen_w + 20]
        for c in self.clouds:
            c.update(dt)
        while len(self.clouds) < 8:
            self._spawn_cloud(random.uniform(-40, -10))

    def render(self, canvas: Canvas, camera_x: float = 0, z: float = 0):
        for cloud in sorted(self.clouds, key=lambda c: c.y):
            cloud.render(canvas, camera_x, z)


class MountainProfile:
    def __init__(self, width: int, height: int, scale: float = 40,
                 octaves: int = 4, color: Color = Color(80, 70, 100),
                 snow_color: Optional[Color] = None, z: float = 0):
        self.width = width
        self.height = height
        self.scale = scale
        self.octaves = octaves
        self.color = color
        self.snow_color = snow_color or Color(220, 220, 240)
        self.z = z
        self.profile: list[int] = []
        self._generate()

    def _generate(self):
        pn = PerlinNoise()
        for x in range(self.width):
            h = pn.fbm2(x / self.scale, 0.5, self.octaves, 2.0, 0.5)
            h = (h + 1) * 0.5 * self.height
            self.profile.append(int(h))

    def render(self, canvas: Canvas, camera_x: float = 0, z: float = 0):
        ox = int(camera_x) % self.width
        for x in range(canvas.w):
            px = (x + ox) % self.width
            peak = self.profile[px]
            base = self.height
            for y in range(peak, base):
                cy = canvas.h - (self.height - peak) - 1 + (y - peak)
                if 0 <= cy < canvas.h:
                    t = (y - peak) / max(1, base - peak)
                    col = self.color.mul(1.0 - t * 0.4)
                    if y - peak < 2 and self.snow_color:
                        col = self.snow_color
                    canvas.set_pixel(x, cy, SHADE_CHARS[int(t * 8)], col, z=z)


class DayNightCycle:
    def __init__(self, cycle_duration: float = 60.0):
        self.cycle_duration = cycle_duration
        self.time = 0.0

    def update(self, dt: float):
        self.time += dt

    @property
    def phase(self) -> float:
        return (self.time % self.cycle_duration) / self.cycle_duration

    @property
    def is_day(self) -> bool:
        return 0.2 <= self.phase < 0.7

    @property
    def sky_color(self) -> Color:
        p = self.phase
        if p < 0.15:
            t = p / 0.15
            return Color(8, 6, 20).lerp(Color(200, 100, 60), t)
        elif p < 0.25:
            t = (p - 0.15) / 0.1
            return Color(200, 100, 60).lerp(Color(100, 150, 255), t)
        elif p < 0.6:
            t = (p - 0.25) / 0.35
            return Color(100, 150, 255).lerp(Color(100, 150, 255), t)
        elif p < 0.75:
            t = (p - 0.6) / 0.15
            return Color(100, 150, 255).lerp(Color(200, 100, 60), t)
        elif p < 0.85:
            t = (p - 0.75) / 0.1
            return Color(200, 100, 60).lerp(Color(30, 20, 50), t)
        else:
            t = (p - 0.85) / 0.15
            return Color(30, 20, 50).lerp(Color(8, 6, 20), t)

    @property
    def ambient_brightness(self) -> float:
        if self.is_day:
            return 1.0
        p = self.phase
        if p < 0.15:
            return p / 0.15
        elif p < 0.7:
            return 1.0
        elif p < 0.85:
            return 1.0 - (p - 0.7) / 0.15
        else:
            return (1.0 - (p - 0.85) / 0.15) * 0.2


class WaterSurface:
    def __init__(self, y: int, width: int, color: Color = Color(40, 80, 160),
                 wave_speed: float = 1.0, z: float = 0):
        self.y = y
        self.width = width
        self.color = color
        self.wave_speed = wave_speed
        self.z = z
        self.time = 0.0

    def update(self, dt: float):
        self.time += dt * self.wave_speed

    def render(self, canvas: Canvas, z: float = 0):
        for x in range(canvas.w):
            wave = math.sin(x * 0.3 + self.time * 2) * 0.3
            wave += math.sin(x * 0.7 + self.time * 1.3) * 0.15
            wy = self.y + int(wave)
            if 0 <= wy < canvas.h:
                shade = x % 3
                ch = '~' if shade == 0 else '≈' if shade == 1 else ' '
                b = 0.5 + 0.5 * math.sin(x * 0.1 + self.time)
                col = self.color.mul(b)
                canvas.set_pixel(x, wy, ch, col, z=z)


class Tree:
    def __init__(self, x: float, y: float, height: int = 5,
                 color: Color = Color(60, 140, 60),
                 trunk_color: Color = Color(100, 70, 40), z: float = 0):
        self.x = x
        self.y = y
        self.height = height
        self.color = color
        self.trunk_color = trunk_color
        self.z = z

    def render(self, canvas: Canvas, camera_x: float = 0, z: float = 0):
        sx = round(self.x - camera_x)
        if sx < -5 or sx >= canvas.w + 5:
            return
        base_y = int(self.y)
        for i in range(self.height // 2):
            cy = base_y - i
            if 0 <= cy < canvas.h:
                canvas.set_pixel(sx, cy, '|', self.trunk_color, z=z)
        crown_r = max(2, self.height // 3)
        for dy in range(-crown_r, crown_r + 1):
            for dx in range(-crown_r, crown_r + 1):
                d = math.hypot(dx, dy)
                if d <= crown_r:
                    cy = base_y - self.height // 2 + dy
                    cx = sx + dx
                    if 0 <= cx < canvas.w and 0 <= cy < canvas.h:
                        d2 = math.hypot(dx - 0.3, dy + 0.3)
                        shade = int((1 - d2 / crown_r) * 6)
                        canvas.set_pixel(cx, cy, SHADE_CHARS[shade], self.color, z=z)


def render_sky(canvas: Canvas, sky_color: Color, z: float = 0):
    for y in range(canvas.h // 2):
        t = y / (canvas.h // 2)
        c = sky_color.lerp(Color(255, 255, 255), t * 0.3)
        for x in range(canvas.w):
            canvas.set_pixel(x, y, ' ', bg=c, z=z)


def render_stars(canvas: Canvas, t: float, count: int = 60, z: float = 0):
    rng = random.Random(42)
    for _ in range(count):
        x = int(rng.random() * canvas.w)
        y = int(rng.random() * (canvas.h // 2))
        twinkle = 0.5 + 0.5 * math.sin(t * 2 + x * 7 + y * 13)
        if twinkle > 0.7:
            b = int(150 + 105 * ((twinkle - 0.7) / 0.3))
            canvas.set_pixel(x, y, '.', Color(b, b, b), z=z)


def render_moon(canvas: Canvas, t: float, phase: float, z: float = 0):
    moon_x = int(canvas.w * 0.8)
    moon_y = int(canvas.h * 0.15)
    moon_color = Color(240, 240, 220)
    for dy in range(-3, 4):
        for dx in range(-3, 4):
            d = math.hypot(dx, dy)
            if d <= 3:
                cx = moon_x + dx
                cy = moon_y + dy
                if 0 <= cx < canvas.w and 0 <= cy < canvas.h:
                    canvas.set_pixel(cx, cy, '@', moon_color, z=z)
