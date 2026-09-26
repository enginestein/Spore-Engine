import math
import random
from spore_engine import *
from spore_engine.core.color import *


def _init_state(w, h):
    st = scene_state('fireflies')
    if st.get('flies') is not None:
        return st
    rnd = random.Random(13)
    n = 42
    st.flies = [{
        'bx': rnd.uniform(0, w),
        'by': rnd.uniform(h * 0.30, h * 0.85),
        'phx': rnd.uniform(0, 2 * math.pi),
        'phy': rnd.uniform(0, 2 * math.pi),
        'sx': rnd.uniform(0.2, 0.7),
        'sy': rnd.uniform(0.15, 0.5),
        'fl': rnd.uniform(0, 2 * math.pi),
        'warm': rnd.random() < 0.25,
        'size': rnd.uniform(0.8, 1.4),
    } for _ in range(n)]
    return st


def _draw_sky(c, w, h, t):
    c.fill_sky(Gradient(Color(6, 10, 24), Color(24, 20, 46),
                        Color(38, 34, 66), Color(20, 40, 34)),
               horizon=0.1, z=-100)


def _draw_moon(c, w, h, t):
    mx, my = int(w * 0.78), int(h * 0.16)
    r = int(h * 0.07)
    for dy in range(-r - 4, r + 5):
        for dx in range(-r - 4, r + 5):
            d = math.hypot(dx, dy)
            px, py = mx + dx, my + dy
            if not in_bounds(px, py, w, h):
                continue
            if d <= r:
                shade = 0.92 + 0.08 * math.sin(t * 0.5 + d * 0.4)
                cc = Color(int(235 * shade), int(240 * shade), int(250 * shade))
                c.set_pixel(px, py, ' ', bg=cc, z=40)
            elif d <= r + 4:
                g = 1 - (d - r) / 4
                b = int(60 * g * g)
                c.set_pixel(px, py, ' ', bg=Color(b, b + 10, 90), z=38)


def _ground_at(x):
    """Ground profile at column x.

    Evaluated per column rather than cached in a list sized to the first
    canvas we saw, so a later resize cannot index past the end of it.
    """
    return math.sin(x * 0.09) * 0.5 + math.sin(x * 0.031 + 1.7) * 0.4


def _draw_ground(c, w, h, t):
    base = Color(10, 26, 20)
    for x in range(w):
        top = h - 2 - int((0.5 + _ground_at(x)) * h * 0.07)
        for y in range(top, h):
            c.set_pixel(x, y, ' ', bg=base, z=10)
        sparkle = wave(t, 1.2, x * 1.7)
        if sparkle > 0.85 and top - 1 >= 0:
            b = int((sparkle - 0.85) * 5 * 160)
            c.set_pixel(x, top - 1, '·', fg=Color(b, b + 30, b // 2), z=25)


def _draw_flies(hr, w, h, t):
    for f in scene_state('fireflies').flies:
        x = f['bx'] + math.sin(t * f['sx'] + f['phx']) * w * 0.06
        y = f['by'] + math.sin(t * f['sy'] + f['phy']) * h * 0.05
        flicker = 0.5 + 0.5 * math.sin(t * 3.0 + f['fl'] * 5)
        flicker = flicker ** 2.0 * f['size']
        px, py = int(x), int(y)
        if not in_bounds(px, py, w, h) or flicker < 0.12:
            continue

        if f['warm']:
            core = Color.from_hsv(0.10, 0.85, 0.5 + 0.5 * flicker)
        else:
            core = Color.from_hsv(0.30, 0.7, 0.5 + 0.5 * flicker)

        for gx in (-1, 0, 1):
            for gy in (-1, 0, 1):
                if gx == 0 and gy == 0:
                    continue
                d = math.hypot(gx, gy)
                gg = max(0, (1.4 - flicker * 0.8 - d) * 0.5)
                if gg <= 0:
                    continue
                gpx, gpy = px + gx, py + gy
                if in_bounds(gpx, gpy, w, h):
                    gb = int(core.r * gg * 0.35)
                    gc = int(core.g * gg * 0.35)
                    hr.set_pixel(gpx, gpy, '·', fg=Color(gb, gc, 0), z=45)

        b = flicker
        hr.set_pixel(px, py, '•', fg=core.mul(0.7 + 0.5 * b), z=50)


def scene_fireflies(c, hr, t, pt, dt):
    """Fireflies - a dusk meadow drifting with glowing insects"""
    w, h = hr.w, hr.h
    _init_state(w, h)
    _draw_sky(c, c.w, c.h, t)
    _draw_moon(c, c.w, c.h, t)
    _draw_ground(c, c.w, c.h, t)
    _draw_flies(hr, w, h, t)

    hr.to_canvas(c)
    c.draw_text(2, 0, '✦ Firefly Meadow ✦', Color(220, 240, 200), z=100)
    c.draw_text(2, c.h - 1,
                'glowing drifters | moonrise | dusk', DIM, z=100)