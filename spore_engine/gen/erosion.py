from __future__ import annotations
import math
import random
from ..core.color import Color
from ..core.glyphs import SHADE_CHARS
from ..core.canvas import Canvas
from ..sim.noise import PerlinNoise


#: Re-exported from core.glyphs so the ramp is defined once.
SHADE = SHADE_CHARS


class ErosionSim:
    def __init__(self, width: int, height: int):
        self.w = width
        self.h = height
        self.heightmap: list[list[float]] = [[0.0] * width for _ in range(height)]
        self.water: list[list[float]] = [[0.0] * width for _ in range(height)]
        self.sediment: list[list[float]] = [[0.0] * width for _ in range(height)]
        self._rng = random.Random(42)

    def generate_heightmap(self, scale: float = 0.08, octaves: int = 5,
                           seed: int = 42, amplitude: float = 1.0):
        noise = PerlinNoise(seed)
        for y in range(self.h):
            for x in range(self.w):
                v = noise.fbm2(x * scale, y * scale, octaves=octaves)
                v = v * 0.5 + 0.5
                v = v ** 1.5
                self.heightmap[y][x] = v * amplitude

    def resize(self, width: int, height: int):
        """Reallocate the grids to a new size, resampling what fits.

        Callers used to "resize" an ErosionSim by assigning ``sim.w`` and
        ``sim.h`` directly, which left heightmap/water/sediment at their
        original dimensions while every accessor believed the new ones. Any
        terminal resize then raised IndexError partway through erosion.
        Values inside the overlapping region are carried over, so a resize
        does not wipe out terrain that is still on screen.
        """
        width, height = max(1, int(width)), max(1, int(height))
        if (width, height) == (self.w, self.h):
            return

        def _resample(old):
            if not old or not old[0]:
                return [[0.0] * width for _ in range(height)]
            oh, ow = len(old), len(old[0])
            return [[old[min(oh - 1, y * oh // height)]
                     [min(ow - 1, x * ow // width)] for x in range(width)]
                    for y in range(height)]

        self.heightmap = _resample(self.heightmap)
        self.water = _resample(self.water)
        self.sediment = _resample(self.sediment)
        self.w, self.h = width, height

    def get_height(self, x: int, y: int) -> float:
        if 0 <= x < self.w and 0 <= y < self.h:
            return self.heightmap[y][x]
        return 0.0

    def _gradient(self, x: int, y: int) -> tuple[float, float]:
        left = self.get_height(x - 1, y)
        right = self.get_height(x + 1, y)
        up = self.get_height(x, y - 1)
        down = self.get_height(x, y + 1)
        return (left - right, up - down)

    def _total_height(self, x: int, y: int) -> float:
        if not (0 <= x < self.w and 0 <= y < self.h):
            return 0.0
        return self.heightmap[y][x] + self.water[y][x]

    def erode(self, num_drops: int = 10000, rain_rate: float = 0.01,
              evap_rate: float = 0.05, sediment_capacity: float = 4.0,
              deposit_rate: float = 0.3, erosion_rate: float = 0.05,
              gravity: float = 4.0, max_steps: int = 80):
        for _ in range(num_drops):
            # randint(1, w-2) raises on grids narrower than 3, which is a
            # legitimate size on a small terminal.
            x = self._rng.randint(1, self.w - 2) if self.w > 2 else self._rng.randrange(self.w)
            y = self._rng.randint(1, self.h - 2) if self.h > 2 else self._rng.randrange(self.h)
            water_vol = 1.0
            sediment = 0.0
            speed = 0.0
            px, py = x, y

            for _step in range(max_steps):
                gx, gy = self._gradient(px, py)
                gx /= max(1e-6, abs(gx) + abs(gy))
                gy /= max(1e-6, abs(gx) + abs(gy))

                nx = px + gx
                ny = py + gy

                if nx < 1 or nx >= self.w - 1 or ny < 1 or ny >= self.h - 1:
                    break

                nxi, nyi = round(nx), round(ny)
                if nxi < 0 or nxi >= self.w or nyi < 0 or nyi >= self.h:
                    break

                cur_h = self._total_height(px, py)
                next_h = self._total_height(nxi, nyi)
                dh = cur_h - next_h

                if dh <= 0:
                    if self._rng.random() < 0.5:
                        nxi = max(1, min(self.w - 2, px + self._rng.choice([-1, 1])))
                        nyi = max(1, min(self.h - 2, py + self._rng.choice([-1, 1])))
                    else:
                        break

                dh = max(dh, 0.001)
                speed = math.sqrt(speed * speed + gravity * dh)
                carry = max(sediment_capacity * speed * water_vol, 0.001)

                if speed > 0:
                    eroded = erosion_rate * speed * dh * water_vol
                    self.heightmap[py][px] -= eroded
                    sediment += eroded

                if sediment > carry:
                    deposited = (sediment - carry) * deposit_rate
                    self.heightmap[py][px] += deposited
                    sediment -= deposited

                self.water[py][px] -= water_vol * 0.1
                if self.water[py][px] < 0:
                    self.water[py][px] = 0

                px, py = nxi, nyi
                water_vol *= (1 - evap_rate)

                if water_vol < 0.01:
                    break

            if sediment > 0:
                self.heightmap[py][px] += sediment

        self._normalize()

    def _normalize(self):
        mn, mx = float('inf'), float('-inf')
        for y in range(self.h):
            for x in range(self.w):
                v = self.heightmap[y][x]
                if v < mn: mn = v
                if v > mx: mx = v
        rng = mx - mn
        if rng > 0:
            for y in range(self.h):
                for x in range(self.w):
                    self.heightmap[y][x] = (self.heightmap[y][x] - mn) / rng

    def add_rain(self, amount: float = 0.05, density: float = 0.1):
        for y in range(self.h):
            for x in range(self.w):
                if self._rng.random() < density:
                    self.water[y][x] += amount + self._rng.random() * amount

    def add_uniform_rain(self, amount: float = 0.05):
        for y in range(self.h):
            for x in range(self.w):
                self.water[y][x] += amount

    def evaporate(self, rate: float = 0.1):
        for y in range(self.h):
            for x in range(self.w):
                self.water[y][x] *= (1 - rate)
                self.water[y][x] = max(0, self.water[y][x])

    def render(self, canvas: Canvas, show_water: bool = True,
               z: float = 5, water_z: float = 10):
        for y in range(self.h):
            for x in range(self.w):
                v = self.heightmap[y][x]
                hue = 0.2 + v * 0.2
                bright = 0.15 + v * 0.7
                col = Color.from_hsv(hue, 0.65, bright)
                ci = int(v * (len(SHADE) - 1))
                canvas.set_pixel(x, y, SHADE[ci], col, z=z)

                if show_water and self.water[y][x] > 0.01:
                    w = min(1, self.water[y][x])
                    wcol = Color.from_hsv(0.55, 0.7, 0.3 + w * 0.6)
                    canvas.set_pixel(x, y, '~', wcol, z=water_z)

    def render_shaded(self, canvas: Canvas, z: float = 5):
        for y in range(1, self.h - 1):
            for x in range(1, self.w - 1):
                gx, gy = self._gradient(x, y)
                gx /= max(1e-6, abs(gx) + abs(gy))
                gy /= max(1e-6, abs(gx) + abs(gy))
                light = max(0.2, min(1, 0.5 + (-gx + gy) * 0.5))
                v = self.heightmap[y][x]
                col = Color(int(light * 200), int(light * 180), int(light * 150))
                ci = int(v * (len(SHADE) - 1))
                canvas.set_pixel(x, y, SHADE[ci], col, z=z)
