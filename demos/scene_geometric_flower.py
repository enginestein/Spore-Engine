import math
import random
from spore_engine import *
from spore_engine.core.color import *

_GF = None


def _init(w, h):
    global _GF
    if _GF is not None:
        return
    rnd = random.Random(8)
    _GF = {
        'stars': [(rnd.uniform(0, w), rnd.uniform(0, h * 0.9),
                   rnd.uniform(0, 2 * math.pi), rnd.uniform(0.2, 1.0))
                  for _ in range(60)],
    }


def _dot(hr, x, y, col, z=50):
    px, py = int(x), int(y)
    if 0 <= px < hr.w and 0 <= py < hr.h:
        hr.set_pixel(px, py, '·', fg=col, z=z)


def scene_geometric_flower(c, hr, t, pt, dt):
    """Geometric Flower - layered rose curves blooming into a mandala"""
    w, h = hr.w, hr.h
    _init(w, h)
    s = _GF

    for y in range(c.h):
        ty = y / max(1, c.h)
        col = Color(5, 2, 14).lerp(Color(16, 8, 34), ty)
        for x in range(c.w):
            c.set_pixel(x, y, ' ', bg=col, z=-100)

    for sx, sy, ph, bri in s['stars']:
        tw = 0.5 + 0.5 * math.sin(t * 1.6 + ph * 4 + sx)
        v = tw * bri
        if v < 0.18:
            continue
        b = int(min(255, v * 255))
        hr.set_pixel(int(sx), int(sy), '·',
                     fg=Color(b, b, min(255, int(b * 1.2))), z=40)

    cx, cy = w / 2, h * 0.46
    aspect = h / w * 0.92
    max_r = min(w, h) * 0.40

    layers = [
        (5, 0.62, 0.05),
        (8, 0.42, -0.033),
        (13, 0.26, 0.022),
    ]

    for li, (k, R, sp) in enumerate(layers):
        n = 240
        rot = t * sp
        for i in range(n):
            ang = 2 * math.pi * i / n
            shape = abs(math.cos(k * ang / 2 + rot))
            r = R * max_r * shape
            x = cx + math.cos(ang) * r * aspect
            y = cy + math.sin(ang) * r
            hue = (ang / (2 * math.pi) + t * 0.015 + li * 0.08) % 1.0
            bri = 0.25 + 0.75 * shape
            col = Color.from_hsv(hue, 0.85, bri)
            _dot(hr, x, y, col, z=50 + li)
            if shape > 0.85:
                _dot(hr, x, y, col.mul(1.4), z=55)

    for ring in range(3):
        rr = max_r * (0.16 + ring * 0.10)
        for i in range(90):
            ang = 2 * math.pi * i / 90
            x = cx + math.cos(ang) * rr * aspect
            y = cy + math.sin(ang) * rr
            hue = (0.75 + ring * 0.08 + t * 0.02) % 1.0
            _dot(hr, x, y, Color.from_hsv(hue, 0.6, 0.25), z=45)

    for spoke in range(12):
        ang = spoke * math.pi / 6 + t * 0.06
        for rr in range(int(max_r * 0.25), int(max_r * 0.95)):
            fade = 1 - rr / (max_r * 0.95)
            if fade < 0.05:
                continue
            x = cx + math.cos(ang) * rr * aspect
            y = cy + math.sin(ang) * rr
            hue = (0.72 + spoke * 0.02 + t * 0.01) % 1.0
            _dot(hr, x, y, Color.from_hsv(hue, 0.7, fade * 0.5), z=42)

    hr.to_canvas(c)
    c.draw_text(2, 0, '❀ Geometric Flower ❀',
                Color.from_hsv((t * 0.02) % 1, 0.8, 1.0), z=100)
    c.draw_text(2, c.h - 1, 'rose curves | mandala bloom', DIM, z=100)
