import math, random
from spore_engine import *
from spore_engine.core.color import *

_DP = None

def scene_double_pendulum(c, hr, t, pt, dt):
    global _DP
    w, h = c.w, c.h
    cx, cy = w // 2, int(h * 0.25)

    if _DP is None:
        pendulums = []
        for _ in range(6):
            a1 = random.uniform(1.5, 2.8)
            a2 = random.uniform(1.5, 2.8)
            pendulums.append({
                'a1': a1, 'a2': a2,
                'v1': 0.0, 'v2': 0.0,
                'm1': 10.0, 'm2': 10.0,
                'l1': random.uniform(4.0, 7.0),
                'l2': random.uniform(4.0, 7.0),
                'trail': [],
                'hue': random.uniform(0.0, 1.0),
                'g': 9.81,
            })
        _DP = {'pendulums': pendulums, 'trail_max': 100}

    s = _DP

    for y in range(h):
        ty = y / h
        col = Color(int(ty * 8), int(ty * 4), int(ty * 12 + 2))
        for x in range(w):
            c.set_pixel(x, y, ' ', bg=col, z=-100)

    dt_sim = min(dt * 6.0, 0.05)
    scale = min(w, h) * 0.045

    for p in s['pendulums']:
        a1, a2, v1, v2 = p['a1'], p['a2'], p['v1'], p['v2']
        m1, m2, l1, l2 = p['m1'], p['m2'], p['l1'], p['l2']
        g = p['g']

        for _ in range(3):
            num1 = -g * (2 * m1 + m2) * math.sin(a1)
            num2 = -m2 * g * math.sin(a1 - 2 * a2)
            num3 = -2 * math.sin(a1 - a2) * m2 * (v2 * v2 * l2 + v1 * v1 * l1 * math.cos(a1 - a2))
            den1 = l1 * (2 * m1 + m2 - m2 * math.cos(2 * a1 - 2 * a2))
            a1_acc = (num1 + num2 + num3) / den1 if abs(den1) > 0.001 else 0

            num4 = 2 * math.sin(a1 - a2)
            num5 = v1 * v1 * l1 * (m1 + m2) + g * (m1 + m2) * math.cos(a1)
            num6 = v2 * v2 * l2 * m2 * math.cos(a1 - a2)
            den2 = l2 * (2 * m1 + m2 - m2 * math.cos(2 * a1 - 2 * a2))
            a2_acc = num4 * (num5 + num6) / den2 if abs(den2) > 0.001 else 0

            v1 += a1_acc * dt_sim
            v2 += a2_acc * dt_sim
            v1 *= 0.999
            v2 *= 0.999
            a1 += v1 * dt_sim
            a2 += v2 * dt_sim

        p['a1'], p['a2'] = a1 % (2 * math.pi), a2 % (2 * math.pi)
        p['v1'], p['v2'] = v1, v2

        x1 = cx + l1 * scale * math.sin(a1)
        y1 = cy + l1 * scale * math.cos(a1)
        x2 = x1 + l2 * scale * math.sin(a2)
        y2 = y1 + l2 * scale * math.cos(a2)

        px1, py1 = int(x1), int(y1)
        px2, py2 = int(x2), int(y2)

        p['trail'].append((px2, py2))
        if len(p['trail']) > s['trail_max']:
            p['trail'].pop(0)

        for i, (tx, ty2) in enumerate(p['trail']):
            if 0 <= tx < w and 0 <= ty2 < h:
                prog = i / len(p['trail'])
                bright = prog * 0.6 * (0.5 + 0.5 * math.sin(t * 0.5 + i * 0.1))
                hue = (p['hue'] + prog * 0.1 + t * 0.005) % 1.0
                if bright > 0.05:
                    ch = '·' if bright < 0.2 else ('░' if bright < 0.4 else '▒')
                    c.set_pixel(tx, ty2, ch, Color.from_hsv(hue, 0.6, bright), z=3)

        if 0 <= px2 < w and 0 <= py2 < h:
            hue = (p['hue'] + t * 0.01) % 1.0
            c.set_pixel(px2, py2, '●', Color.from_hsv(hue, 0.8, 1.0), z=10)
            for dx, dy2 in [(-1,0),(1,0),(0,-1),(0,1)]:
                if 0 <= px2+dx < w and 0 <= py2+dy2 < h:
                    c.set_pixel(px2+dx, py2+dy2, '·', Color.from_hsv(hue, 0.5, 0.3), z=9)

        hue = (p['hue'] + t * 0.01) % 1.0
        c.set_pixel(px1, py1, '○', Color.from_hsv(hue, 0.5, 0.8), z=8)
        c.set_pixel(cx, cy, '●', Color(80, 80, 100), z=8)

        steps = max(1, int(math.hypot(px1 - cx, py1 - cy)))
        for i in range(steps + 1):
            frac = i / steps
            lx = int(cx + (px1 - cx) * frac)
            ly = int(cy + (py1 - cy) * frac)
            if 0 <= lx < w and 0 <= ly < h:
                c.set_pixel(lx, ly, '│', Color(60, 60, 80).mul(0.5 + 0.5 * (1 - frac)), z=6)

        steps = max(1, int(math.hypot(px2 - px1, py2 - py1)))
        for i in range(steps + 1):
            frac = i / steps
            lx = int(px1 + (px2 - px1) * frac)
            ly = int(py1 + (py2 - py1) * frac)
            if 0 <= lx < w and 0 <= ly < h:
                hue = (p['hue'] + frac * 0.1 + t * 0.01) % 1.0
                c.set_pixel(lx, ly, '│', Color.from_hsv(hue, 0.5, 0.5 + frac * 0.4), z=7)
