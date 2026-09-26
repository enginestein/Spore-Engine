import math
import random
from spore_engine import *
from spore_engine.core.color import *

_SW = None


def _init(w, h):
    global _SW
    if _SW is not None:
        return
    rnd = random.Random(7)
    horizon = int(h * 0.60)
    _SW = {
        'horizon': horizon,
        'stars': [(rnd.uniform(0, w), rnd.uniform(0, horizon * 0.8),
                   rnd.uniform(0, 2 * math.pi), rnd.uniform(0.3, 1.0))
                  for _ in range(70)],
    }


def _line(hr, x1, y1, x2, y2, fg, z=0, char='█'):
    n = max(abs(x2 - x1), abs(y2 - y1))
    if n == 0:
        hr.set_pixel(x1, y1, char, fg=fg, z=z)
        return
    for i in range(n + 1):
        tt = i / n
        hr.set_pixel(int(x1 + (x2 - x1) * tt), int(y1 + (y2 - y1) * tt),
                     char, fg=fg, z=z)


def _draw_sky(c, hr, w, horizon, t):
    for y in range(horizon // 2):
        ty = y / max(1, horizon // 2)
        if ty < 0.45:
            col = Color.from_hsv(0.70, 0.55, 0.04 + ty * 0.10)
        elif ty < 0.75:
            col = Color.from_hsv(0.82, 0.9, 0.12 + (ty - 0.45) * 0.5)
        else:
            col = Color.from_hsv(0.06, 1.0, 0.30 + (ty - 0.75) * 1.2)
        for x in range(w):
            c.set_pixel(x, y, ' ', bg=col, z=-100)

    for sx, sy, ph, bri in _SW['stars']:
        tw = 0.5 + 0.5 * math.sin(t * 1.8 + ph * 5 + sx)
        v = tw * bri
        if v < 0.2:
            continue
        b = int(min(255, v * 255))
        hr.set_pixel(int(sx), int(sy), '·',
                     fg=Color(b, b, min(255, int(b * 1.25))), z=30)


def _draw_sun(hr, w, horizon, t):
    sun_r = int(horizon * 0.30)
    sx, sy = w // 2, horizon - int(sun_r * 0.72)
    for dy in range(-sun_r, sun_r + 1):
        if dy % 3 == 0 and dy > -sun_r // 2:
            continue
        row_w = int(math.sqrt(max(0, sun_r * sun_r - dy * dy)))
        for dx in range(-row_w, row_w + 1):
            d = math.hypot(dx, dy) / sun_r
            px, py = sx + dx, sy + dy
            if px < 0 or px >= w or py < 0:
                continue
            if d > 1:
                continue
            bri = (1 - d) ** 1.4
            pulse = 0.5 + 0.5 * math.sin(t * 0.1 + d * 3)
            hue = 0.10 - d * 0.10 + pulse * 0.02
            col = Color.from_hsv(hue % 1, 0.85, 0.35 + 0.65 * bri)
            ch = '█' if bri > 0.55 else ('▓' if bri > 0.3 else '▒')
            hr.set_pixel(px, py, ch, fg=col, z=40)


def _draw_grid(hr, w, h, horizon, t):
    pink = Color(255, 40, 160)
    floor_h = h - horizon
    vp_x = w // 2

    rows = 26
    for k in range(1, rows + 1):
        tt = (k / rows) ** 2.2
        y = horizon + int(tt * floor_h)
        if y >= h:
            continue
        fade = 0.12 + 0.88 * (k / rows)
        r = int(pink.r * fade); g = int(pink.g * fade); b = int(pink.b * fade)
        _line(hr, 0, y, w - 1, y, Color(r, g, b), z=20)

    cols = 30
    for i in range(-cols, cols + 1):
        xb = vp_x + i * int(w * 0.055)
        dist = abs(i) / cols
        fade = 0.15 + 0.85 * (1 - dist)
        r = int(pink.r * fade); g = int(pink.g * fade); b = int(pink.b * fade)
        _line(hr, xb, h - 1, vp_x, horizon, Color(r, g, b), z=20)


def _draw_ridge(c, w, horizon, t):
    base = Color(10, 2, 30)
    horizon_low = horizon // 2
    for x in range(w):
        # Closed form, not a list sized to the first canvas width.
        hgt = math.sin(x * 0.11) * 0.5 + math.sin(x * 0.043 + 2.0) * 0.3
        hgt += math.sin(t * 0.05 + x * 0.01) * 0.04
        top = horizon_low - int(hgt * horizon_low * 0.10)
        for y in range(top, horizon_low):
            c.set_pixel(x, y, ' ', bg=base, z=15)


def scene_synthwave(c, hr, t, pt, dt):
    """Synthwave - neon sunset, striped sun and a perspective grid floor"""
    w, h = hr.w, hr.h
    _init(w, h)
    _draw_sky(c, hr, w, _SW['horizon'], t)
    _draw_sun(hr, w, _SW['horizon'], t)
    _draw_ridge(c, w, _SW['horizon'], t)
    _draw_grid(hr, w, h, _SW['horizon'], t)

    hr.to_canvas(c)
    c.draw_text(2, 0, '✦ SYNTHWAVE ✦', Color.from_hsv(0.9, 0.9, 1.0), z=100)
    c.draw_text(2, c.h - 1,
                'retro neon | perspective grid | striped sun', DIM, z=100)
