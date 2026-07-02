import math, random
from spore_engine import *
from spore_engine.core.color import *
from spore_engine.sim.noise import PerlinNoise

_AURORA = None

def scene_aurora(c, hr, t, pt, dt):
    global _AURORA
    if _AURORA is None:
        _AURORA = {
            'noise': PerlinNoise(42),
            'stars': [(random.random(), random.random(), random.random())
                      for _ in range(80)],
        }

    w, h = c.w, c.h

    for y in range(h):
        ty = y / h
        col = Color.from_hsv(0.65 - ty*0.1, 0.4, 0.02 + ty*0.06)
        for x in range(w):
            c.set_pixel(x, y, ' ', bg=col, z=-100)

    night = 0.8 + 0.2 * math.sin(t * 0.1)
    for sx, sy, phase in _AURORA['stars']:
        px = int(sx * w)
        py = int(sy * h * 0.5)
        if 0 <= px < w and 0 <= py < h:
            tw = 0.5 + 0.5 * math.sin(t * 2 + phase * 100)
            if tw > 0.6:
                b = int(80 + tw * 120 * night)
                c.set_pixel(px, py, '·' if tw < 0.8 else '✦', Color(b, b, int(b*1.1)), z=5)

    for band in range(5):
        hue_base = 0.7 + band * 0.05 + math.sin(t * 0.02) * 0.05
        for y in range(h // 3):
            gy = int(h * 0.05 + y * 0.6 + band * h * 0.04)
            if gy >= h: continue
            for x in range(w):
                n1 = _AURORA['noise'].noise2(x * 0.02 + t * 0.15, gy * 0.03 + band * 2.0)
                n2 = _AURORA['noise'].noise2(x * 0.04 - t * 0.08, gy * 0.05 + band)
                val = (n1 * 0.6 + n2 * 0.4) * 0.5 + 0.5
                val *= 1.0 - abs(y - h//6) / (h//6)
                val = max(0, min(1, val * 1.5))
                if val > 0.15:
                    hue = (hue_base + val * 0.1 + t * 0.005) % 1.0
                    bright = 0.2 + val * 0.6
                    ch = '░' if val < 0.3 else ('▒' if val < 0.5 else ('▓' if val < 0.7 else '█'))
                    c.set_pixel(x, gy, ch, Color.from_hsv(hue, 0.7, bright), z=10)

    for y in range(h // 2, h):
        ty = (y - h//2) / (h//2)
        for x in range(w):
            n = _AURORA['noise'].noise2(x * 0.05, y * 0.04) * 0.5 + 0.5
            dark = 0.3 + n * 0.7
            c.set_pixel(x, y, ' ', bg=Color(int(3*dark), int(8*dark), int(15*dark)), z=-50)
