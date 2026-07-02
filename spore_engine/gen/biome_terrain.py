from __future__ import annotations
import math, random
from ..core.canvas import Canvas
from ..core.color import Color, Gradient
from ..sim.noise import PerlinNoise


BIOMES = {
    'ocean':      Gradient(Color(10, 30, 70), Color(20, 60, 120), Color(30, 90, 160)),
    'beach':      Gradient(Color(180, 170, 120), Color(200, 190, 140)),
    'desert':     Gradient(Color(180, 150, 60), Color(210, 180, 80), Color(230, 200, 100)),
    'grassland':  Gradient(Color(60, 130, 40), Color(80, 160, 50), Color(100, 180, 60)),
    'forest':     Gradient(Color(30, 90, 20), Color(40, 120, 30), Color(50, 150, 40)),
    'rainforest': Gradient(Color(10, 70, 10), Color(20, 100, 20), Color(30, 130, 30)),
    'tundra':     Gradient(Color(120, 140, 130), Color(150, 160, 150), Color(180, 190, 180)),
    'taiga':      Gradient(Color(40, 80, 50), Color(50, 100, 60), Color(60, 120, 70)),
    'mountains':  Gradient(Color(100, 90, 80), Color(140, 130, 120), Color(200, 190, 180)),
    'snow':       Gradient(Color(200, 210, 220), Color(230, 235, 240), Color(255, 255, 255)),
    'swamp':      Gradient(Color(40, 70, 30), Color(50, 85, 35), Color(60, 100, 40)),
    'savanna':    Gradient(Color(140, 160, 40), Color(170, 190, 50), Color(200, 210, 60)),
}


def get_biome(elevation: float, moisture: float, temperature: float) -> str:
    if elevation < -0.1: return 'ocean'
    if elevation < 0.0: return 'beach'
    if elevation > 0.6: return 'snow' if temperature < 0.2 else 'mountains'
    if elevation > 0.45: return 'tundra' if temperature < 0.3 else 'mountains'

    temp = temperature
    moist = moisture

    if temp < 0.15: return 'tundra'
    if temp < 0.25: return 'taiga'

    if temp > 0.65:
        if moist < 0.3: return 'desert'
        if moist < 0.5: return 'savanna'
        return 'rainforest'

    if temp > 0.5:
        if moist < 0.3: return 'grassland'
        if moist < 0.6: return 'forest'
        return 'swamp'

    if moist < 0.25: return 'grassland'
    if moist < 0.55: return 'forest'
    return 'taiga'


class BiomeMap:
    def __init__(self, width: int, height: int, seed: int = 42):
        self.w = width
        self.h = height
        self.elevation_noise = PerlinNoise(seed)
        self.moisture_noise = PerlinNoise(seed + 1)
        self.temp_noise = PerlinNoise(seed + 2)
        self.elevation: list[list[float]] = []
        self.moisture: list[list[float]] = []
        self.temperature: list[list[float]] = []
        self.biomes: list[list[str]] = []
        self._generate()

    def _generate(self):
        for y in range(self.h):
            elev_row = []
            moist_row = []
            temp_row = []
            biome_row = []
            for x in range(self.w):
                nx, ny = x / self.w, y / self.h
                e = self.elevation_noise.fbm2(nx * 3, ny * 3, octaves=5)
                m = self.moisture_noise.fbm2(nx * 2.5 + 10, ny * 2.5 + 10, octaves=4)
                t = self.temp_noise.fbm2(nx * 2 + 20, ny * 2 + 20, octaves=3) * 0.5 + 0.5
                t = t * (1 - max(0, e) * 0.5)
                elev_row.append(e)
                moist_row.append(m * 0.5 + 0.5)
                temp_row.append(t)
                biome_row.append(get_biome(e, m * 0.5 + 0.5, t))
            self.elevation.append(elev_row)
            self.moisture.append(moist_row)
            self.temperature.append(temp_row)
            self.biomes.append(biome_row)

    def color_at(self, x: int, y: int) -> Color:
        if not (0 <= x < self.w and 0 <= y < self.h):
            return Color(0, 0, 0)
        biome = self.biomes[y][x]
        grad = BIOMES.get(biome, BIOMES['grassland'])
        e = self.elevation[y][x]
        t = max(0, min(1, (e + 0.5) * 0.8 + 0.1))
        return grad.at(t)

    def render(self, c: Canvas):
        for y in range(min(self.h, c.h)):
            for x in range(min(self.w, c.w)):
                col = self.color_at(x, y)
                c.set_pixel(x, y, '█', col, z=5)

    def render_minimap(self, c: Canvas, ox: int, oy: int, scale: int = 1):
        for y in range(0, self.h, scale):
            for x in range(0, self.w, scale):
                col = self.color_at(x, y)
                px, py = ox + x // scale, oy + y // scale
                if 0 <= px < c.w and 0 <= py < c.h:
                    c.set_pixel(px, py, '█', col, z=5)
