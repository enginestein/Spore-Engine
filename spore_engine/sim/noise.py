from __future__ import annotations
import math
import random
import numpy as np
from ..core._accel import njit


@njit
def _grad_nb(hash_val: int, x: float, y: float) -> float:
    h = hash_val & 15
    u = x if h < 8 else y
    v = y if h < 4 else (x if h in (12, 14) else 0.0)
    return (u if h & 1 == 0 else -u) + (v if h & 2 == 0 else -v)


@njit
def _perlin_sample(x: float, y: float, p_table: np.ndarray) -> float:
    X = math.floor(x) & 255
    Y = math.floor(y) & 255
    xf = x - math.floor(x)
    yf = y - math.floor(y)
    u = xf * xf * xf * (xf * (xf * 6 - 15) + 10)
    v = yf * yf * yf * (yf * (yf * 6 - 15) + 10)
    aa = p_table[p_table[X] + Y]
    ab = p_table[p_table[X] + Y + 1]
    ba = p_table[p_table[X + 1] + Y]
    bb = p_table[p_table[X + 1] + Y + 1]
    n00 = _grad_nb(aa, xf, yf)
    n10 = _grad_nb(ba, xf - 1.0, yf)
    n01 = _grad_nb(ab, xf, yf - 1.0)
    n11 = _grad_nb(bb, xf - 1.0, yf - 1.0)
    nx0 = n00 + u * (n10 - n00)
    nx1 = n01 + u * (n11 - n01)
    return nx0 + v * (nx1 - nx0)


@njit
def _perlin_fbm_grid(w: int, h: int, scale: float, ox: float, oy: float,
                     octaves: int, p_table: np.ndarray) -> np.ndarray:
    out = np.zeros((h, w), dtype=np.float64)
    for y in range(h):
        for x in range(w):
            value = 0.0
            amp = 1.0
            freq = 1.0
            bx = (x + ox) * scale
            by = (y + oy) * scale
            for _ in range(octaves):
                value += amp * _perlin_sample(bx * freq, by * freq, p_table)
                amp *= 0.5
                freq *= 2.0
            out[y, x] = value
    return out

class _Noise2D:
    """Mixin giving every 2D noise class the same derived-function surface.

    Subclasses only have to provide ``noise2``; fBm and the grid samplers
    follow. This existed as per-class copy-paste, which is how ValueNoise
    ended up with a single method while the others had four.
    """

    def fbm2(self, x: float, y: float, octaves: int = 4,
             lacunarity: float = 2.0, gain: float = 0.5) -> float:
        """Fractional Brownian motion: octaves of noise2 at rising frequency."""
        value, amplitude, frequency = 0.0, 1.0, 1.0
        for _ in range(octaves):
            value += amplitude * self.noise2(x * frequency, y * frequency)
            amplitude *= gain
            frequency *= lacunarity
        return value

    def ridge2(self, x: float, y: float, octaves: int = 4,
               lacunarity: float = 2.0, gain: float = 0.5) -> float:
        """Ridged fBm - the absolute value inverted, for sharp creases."""
        value, amplitude, frequency = 0.0, 1.0, 1.0
        for _ in range(octaves):
            n = 1.0 - abs(self.noise2(x * frequency, y * frequency))
            value += amplitude * n * n
            amplitude *= gain
            frequency *= lacunarity
        return value

    def noise2d_array(self, w: int, h: int, scale: float = 0.1,
                      ox: float = 0, oy: float = 0) -> list[list[float]]:
        """Sample a w*h grid of noise2.

        The default scale is 0.1, not 1.0, on purpose: gradient noise is
        exactly zero at every integer lattice point, so a scale of 1.0 over
        integer pixel indices returns an all-zero field. Callers who really
        want 1.0 should offset the origin instead.
        """
        return [[self.noise2((x + ox) * scale, (y + oy) * scale)
                 for x in range(w)] for y in range(h)]

    def fbm2d_array(self, w: int, h: int, scale: float = 0.1, ox: float = 0,
                    oy: float = 0, octaves: int = 4) -> list[list[float]]:
        return [[self.fbm2((x + ox) * scale, (y + oy) * scale, octaves)
                 for x in range(w)] for y in range(h)]


class PerlinNoise(_Noise2D):
    def __init__(self, seed: int = 0):
        rng = random.Random(seed)
        self.p = list(range(512))
        rng.shuffle(self.p)
        self.p = self.p + self.p

    @staticmethod
    def _fade(t: float) -> float:
        return t * t * t * (t * (t * 6 - 15) + 10)

    @staticmethod
    def _lerp(a: float, b: float, t: float) -> float:
        return a + t * (b - a)

    @staticmethod
    def _grad(hash: int, x: float, y: float = 0, z: float = 0) -> float:  # noqa: A002
        h = hash & 15
        u = x if h < 8 else y
        v = y if h < 4 else (x if h in (12, 14) else z)
        return (u if h & 1 == 0 else -u) + (v if h & 2 == 0 else -v)

    def noise2(self, x: float, y: float) -> float:
        X = math.floor(x) & 255
        Y = math.floor(y) & 255
        x -= math.floor(x)
        y -= math.floor(y)
        u, v = self._fade(x), self._fade(y)
        aa = self.p[self.p[X] + Y]
        ab = self.p[self.p[X] + Y + 1]
        ba = self.p[self.p[X + 1] + Y]
        bb = self.p[self.p[X + 1] + Y + 1]
        return self._lerp(
            self._lerp(self._grad(aa, x, y), self._grad(ba, x - 1, y), u),
            self._lerp(self._grad(ab, x, y - 1), self._grad(bb, x - 1, y - 1), u),
            v
        )

    def noise1(self, x: float) -> float:
        X = math.floor(x) & 255
        x -= math.floor(x)
        u = self._fade(x)
        return self._lerp(self._grad(self.p[X], x), self._grad(self.p[X + 1], x - 1), u)

    def fbm1(self, x: float, octaves: int = 4, lacunarity: float = 2.0, gain: float = 0.5) -> float:
        value, amplitude, frequency = 0.0, 1.0, 1.0
        for _ in range(octaves):
            value += amplitude * self.noise1(x * frequency)
            amplitude *= gain
            frequency *= lacunarity
        return value

    def ridge(self, x: float, y: float, octaves: int = 4) -> float:
        value = 0.0
        amplitude, frequency = 1.0, 1.0
        for _ in range(octaves):
            n = 1 - abs(self.noise2(x * frequency, y * frequency))
            value += amplitude * n * n
            amplitude *= 0.5
            frequency *= 2.0
        return value

    def fbm2d_grid(self, w: int, h: int, scale: float = 1.0,
                   ox: float = 0, oy: float = 0, octaves: int = 4) -> np.ndarray:
        p = np.array(self.p, dtype=np.int32)
        return _perlin_fbm_grid(w, h, scale, ox, oy, octaves, p)


class ValueNoise(_Noise2D):
    def __init__(self, seed: int = 0):
        rng = random.Random(seed)
        self.table = [rng.random() for _ in range(512)]

    def noise2(self, x: float, y: float) -> float:
        xi, yi = math.floor(x), math.floor(y)
        xf, yf = x - xi, y - yi
        u, v = xf * xf * (3 - 2 * xf), yf * yf * (3 - 2 * yf)
        # Bilinear blend of the four surrounding lattice values. The previous
        # version computed `a = self.table[xi] + yi` and then used `a & 511`
        # as an index, which is a float - every call raised TypeError.
        m = 512
        i = xi & (m - 1)
        v00 = self.table[i]
        v10 = self.table[(i + 1) & (m - 1)]
        v01 = self.table[(i + m) & (m - 1)]
        v11 = self.table[(i + m + 1) & (m - 1)]
        return v00 + (v10 - v00) * u + (v01 - v00) * v + (v00 - v10 - v01 + v11) * u * v


class WorleyNoise(_Noise2D):
    def __init__(self, seed: int = 0):
        self.seed = seed

    @staticmethod
    def _hash_int(x: int, y: int, seed: int) -> int:
        h = (x * 374761393 + y * 668265263 + seed) & 0x7fffffff
        h = ((h ^ (h >> 13)) * 1274126177) & 0x7fffffff
        return (h ^ (h >> 16)) & 0x7fffffff

    def noise2(self, x: float, y: float, k: int = 1) -> float:
        cx, cy = math.floor(x), math.floor(y)
        fx, fy = x - cx, y - cy
        min_d2 = 1e10
        for dx in range(-1, 2):
            for dy in range(-1, 2):
                base = self._hash_int(cx + dx, cy + dy, self.seed)
                h1 = ((base ^ (base >> 7)) * 1048577) & 0x7fffffff
                h2 = ((base ^ (base << 5)) * 2097153) & 0x7fffffff
                px = dx + h1 / 2147483648.0
                py = dy + h2 / 2147483648.0
                d2 = (fx - px) ** 2 + (fy - py) ** 2
                if d2 < min_d2:
                    min_d2 = d2
        return math.sqrt(min_d2) * 0.707


class OpenSimplexNoise(_Noise2D):
    def __init__(self, seed: int = 0):
        rng = random.Random(seed)
        self._perm = list(range(256))
        rng.shuffle(self._perm)
        self._perm = self._perm + self._perm
        self._grad2 = [(1, 0), (-1, 0), (0, 1), (0, -1),
                       (1, 1), (-1, 1), (1, -1), (-1, -1)]

    @staticmethod
    def _dot2(g, x, y):
        return g[0] * x + g[1] * y

    def _grad2_at(self, i, x, y):
        g = self._grad2[self._perm[i & 255] & 7]
        return self._dot2(g, x, y)

    def noise2(self, x: float, y: float) -> float:
        s = (x + y) * 0.3660254037844386
        i, j = math.floor(x + s), math.floor(y + s)
        t = (i + j) * 0.21132486540518713
        x0, y0 = x - (i - t), y - (j - t)
        i1, j1 = (1, 0) if x0 > y0 else (0, 1)
        x1, y1 = x0 - i1 + 0.21132486540518713, y0 - j1 + 0.21132486540518713
        x2, y2 = x0 - 0.5773502691896257, y0 - 0.5773502691896257
        n = 0.0
        for (di, _dj, dx, dy) in [(0, 0, x0, y0), (i1, j1, x1, y1), (1, 1, x2, y2)]:
            t2 = 0.5 - dx * dx - dy * dy
            if t2 > 0:
                n += (t2 * t2 * t2 * t2) * self._grad2_at(i + di, dx, dy)
        return n * 40.0
