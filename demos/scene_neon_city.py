import math
import random
from spore_engine import *
from spore_engine.core.color import *

_NC = None


def _hash(x, y):
    v = math.sin(x * 127.1 + y * 311.7) * 43758.5453
    return v - math.floor(v)


def _init(w, h):
    global _NC
    if _NC is not None:
        return
    rnd = random.Random(33)
    sky_h = int(h * 0.72)
    buildings = []
    x = 0
    while x < w:
        bw = rnd.randint(4, 9)
        bh = rnd.randint(int(h * 0.10), int(h * 0.42))
        sign = rnd.random() < 0.28
        buildings.append({'x': x, 'w': bw, 'h': bh, 'sign': sign,
                          'sign_color': rnd.choice([0.9, 0.5, 0.15])})
        x += bw + rnd.randint(0, 2)
    _NC = {
        'sky_h': sky_h,
        'buildings': buildings,
        'stars': [(rnd.uniform(0, w), rnd.uniform(0, sky_h * 0.6),
                   rnd.uniform(0, 2 * math.pi), rnd.uniform(0.2, 1.0))
                  for _ in range(70)],
    }


def _draw_sky(c, hr, s, t):
    for y in range(s['sky_h']):
        ty = y / max(1, s['sky_h'])
        col = Color(4, 5, 18).lerp(Color(22, 12, 48), ty)
        for x in range(c.w):
            c.set_pixel(x, y, ' ', bg=col, z=-100)

    glow_y = s['sky_h'] - 1
    for x in range(c.w):
        glow = Color(30, 20, 60).lerp(Color(60, 40, 90), 0.5 + 0.5 * math.sin(x * 0.1))
        c.set_pixel(x, glow_y, ' ', bg=glow, z=5)

    for sx, sy, ph, bri in s['stars']:
        tw = 0.5 + 0.5 * math.sin(t * 1.5 + ph * 4 + sx * 2.0)
        v = tw * bri
        if v < 0.18:
            continue
        b = int(min(255, v * 255))
        hr.set_pixel(int(sx), int(sy), '·',
                     fg=Color(b, b, min(255, int(b * 1.2))), z=40)

    mx, my = int(c.w * 0.78), int(s['sky_h'] * 0.22)
    r = int(c.h * 0.05)
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            d = math.hypot(dx, dy)
            if d > r:
                continue
            px, py = mx + dx, my + dy
            if 0 <= px < c.w and 0 <= py < c.h:
                shade = 0.9 + 0.1 * math.sin(t * 0.5 + d)
                c.set_pixel(px, py, ' ',
                            bg=Color(int(230 * shade), int(235 * shade),
                                     int(245 * shade)), z=45)


def _draw_city(c, s, t):
    base = Color(10, 8, 26)
    ground = Color(6, 5, 18)
    for b in s['buildings']:
        bx, bw, bh = b['x'], b['w'], b['h']
        top = s['sky_h'] - bh
        for y in range(top, s['sky_h']):
            for x in range(bx, min(bx + bw, c.w)):
                c.set_pixel(x, y, ' ', bg=base, z=10)

        for wy in range(top + 1, s['sky_h'] - 1, 2):
            for wx in range(bx + 1, bx + bw - 1):
                if wx >= c.w:
                    break
                lit = _hash(wx, wy)
                if lit > 0.82:
                    hue = 0.12 if lit > 0.96 else (0.5 if lit > 0.9 else 0.12)
                    flick = 0.5 + 0.5 * math.sin(t * 3 + wx * 7 + wy * 3)
                    if flick < 0.2:
                        continue
                    col = Color.from_hsv(hue, 0.7, 0.5 + 0.5 * flick)
                    c.set_pixel(wx, wy, '·', fg=col, z=20)

        if b['sign']:
            hue = b['sign_color']
            for wx in range(bx + 1, min(bx + bw, c.w)):
                if wx >= c.w:
                    break
                pulse = 0.5 + 0.5 * math.sin(t * 2.2 + wx * 1.5)
                col = Color.from_hsv(hue, 0.9, 0.35 + 0.65 * pulse)
                c.set_pixel(wx, top, '█', fg=col, z=30)

    for x in range(c.w):
        for y in range(s['sky_h'], c.h):
            c.set_pixel(x, y, ' ', bg=ground, z=10)


def _draw_traffic(c, s, t):
    for lane in range(3):
        y = s['sky_h'] + 2 + lane
        if y >= c.h:
            break
        off = (t * (2.2 + lane * 1.3)) % (c.w + 20)
        for k in range(4):
            px = int((off + k * (c.w + 20) / 4) % c.w)
            hue = 0.5 if lane % 2 == 0 else 0.08
            col = Color.from_hsv(hue, 0.9, 0.7)
            c.set_pixel(px, y, '·', fg=col, z=35)


def _draw_shooting_star(hr, s, t):
    cycle = 9.0
    ph = (t % cycle) / cycle
    x0 = int(ph * (hr.w + 80)) - 40
    y0 = int(s['sky_h'] * 0.2 + math.sin(t * 0.3) * 20)
    for i in range(14):
        px, py = x0 - i * 2, y0 + i
        if px < 0 or px >= hr.w or py < 0 or py >= hr.h:
            continue
        b = max(0, 1 - i / 14)
        col = Color(int(255 * b), int(255 * b), int(255 * b))
        hr.set_pixel(px, py, '·', fg=col, z=60)


def scene_neon_city(c, hr, t, pt, dt):
    """Neon City - a night skyline with lit windows and moving traffic"""
    w, h = hr.w, hr.h
    _init(w, h)
    s = _NC
    _draw_sky(c, hr, s, t)
    _draw_city(c, s, t)
    _draw_traffic(c, s, t)
    _draw_shooting_star(hr, s, t)

    hr.to_canvas(c)
    c.draw_text(2, 0, '✦ Neon City ✦', Color.from_hsv(0.85, 0.9, 1.0), z=100)
    c.draw_text(2, c.h - 1, 'night skyline | lit windows | traffic', DIM, z=100)
