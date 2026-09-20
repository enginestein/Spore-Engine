import math
import random
from spore_engine import *
from spore_engine.core.color import *

_EC = None


def _init(w, h):
    global _EC
    if _EC is not None:
        return
    rnd = random.Random(21)
    _EC = {
        'stars': [(rnd.uniform(0, w), rnd.uniform(0, h * 0.9),
                   rnd.uniform(0, 2 * math.pi), rnd.uniform(0.2, 1.0))
                  for _ in range(130)],
    }


def scene_eclipse(c, hr, t, pt, dt):
    """Eclipse - moon crossing the sun, corona and diamond ring at totality"""
    w, h = hr.w, hr.h
    _init(w, h)
    s = _EC

    period = 48.0
    phase = (t % period) / period
    cx, cy = w // 2, int(h * 0.44)
    sun_r = int(h * 0.17)
    moon_r = int(sun_r * 0.97)

    mx = cx + (phase - 0.5) * w * 1.15
    dist = abs(mx - cx)
    coverage = max(0.0, min(1.0, (sun_r + moon_r - dist) / (2 * moon_r)))

    for y in range(c.h):
        ty = y / max(1, c.h)
        base = Color(4, 5, 18).lerp(Color(12, 10, 30), ty)
        dark = Color(1, 1, 8).lerp(Color(6, 5, 16), ty)
        col = base.lerp(dark, coverage)
        for x in range(c.w):
            c.set_pixel(x, y, ' ', bg=col, z=-100)

    for sx, sy, ph, bri in s['stars']:
        tw = 0.5 + 0.5 * math.sin(t * 1.4 + ph * 5 + sx * 2.2)
        v = tw * bri * (0.15 + 0.85 * coverage)
        if v < 0.12:
            continue
        b = int(min(255, v * 255))
        hr.set_pixel(int(sx), int(sy), '·',
                     fg=Color(b, b, min(255, int(b * 1.2))), z=40)

    corona_glow = int(4 + 18 * (0.5 + 0.5 * math.sin(coverage * math.pi)))
    for dy in range(-moon_r - corona_glow, moon_r + corona_glow + 1):
        for dx in range(-moon_r - corona_glow, moon_r + corona_glow + 1):
            d = math.hypot(dx, dy)
            px, py = cx + dx, cy + dy
            if px < 0 or px >= w or py < 0 or py >= h:
                continue
            covered = math.hypot(px - mx, py - cy) < moon_r
            if d < sun_r:
                if covered:
                    continue
                if d < sun_r * 0.75:
                    col = Color(255, 245, 200)
                    ch = '█'
                elif d < sun_r * 0.93:
                    col = Color(255, 200, 110)
                    ch = '▓'
                else:
                    col = Color(255, 150, 60)
                    ch = '▒'
                hr.set_pixel(px, py, ch, fg=col, z=50)
            elif d <= moon_r + corona_glow and coverage > 0.45:
                ring = max(0, 1 - abs(d - moon_r) / corona_glow)
                b = ring * coverage * 0.55
                if b < 0.06:
                    continue
                col = Color.from_hsv(0.08, 0.5, b)
                hr.set_pixel(px, py, '·' if b < 0.25 else '░',
                             fg=col, z=55)

    if 0.86 < coverage < 0.995:
        side = 1 if mx < cx else -1
        ring_px = cx - side * sun_r
        col = Color(255, 250, 220)
        for i in range(3):
            for j in range(3):
                gx, gy = ring_px - 1 + i, cy - 1 + j
                if 0 <= gx < w and 0 <= gy < h:
                    hr.set_pixel(gx, gy, '█', fg=col, z=70)

    hr.to_canvas(c)
    c.draw_text(2, 0, '☀ Solar Eclipse ☾', Color.from_hsv(0.6, 0.6, 1.0), z=100)
    c.draw_text(2, c.h - 1,
                'totality | corona | diamond ring', DIM, z=100)
