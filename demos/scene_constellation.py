import math
import random
from spore_engine import *
from spore_engine.core.color import *

_CON = None


def _init():
    global _CON
    if _CON is not None:
        return
    rnd = random.Random(99)
    n = 90
    pts = []
    # fibonacci sphere for even distribution
    ga = math.pi * (3 - math.sqrt(5))
    for i in range(n):
        y = 1 - (i / (n - 1)) * 2
        r = math.sqrt(1 - y * y)
        theta = ga * i
        pts.append((math.cos(theta) * r, y, math.sin(theta) * r))
    edges = []
    for i in range(n):
        dists = []
        for j in range(n):
            if i == j:
                continue
            dx = pts[i][0] - pts[j][0]
            dy = pts[i][1] - pts[j][1]
            dz = pts[i][2] - pts[j][2]
            dists.append((dx * dx + dy * dy + dz * dz, j))
        dists.sort()
        for d, j in dists[:4]:
            if (j, i) not in edges and (i, j) not in edges:
                edges.append((i, j))
    _CON = {
        'pts': pts,
        'edges': edges,
        'bright': sorted(range(n),
                         key=lambda i: rnd.random())[:14],
        'palette': [(0.6, 0.9, 1.0), (0.95, 0.95, 1.0),
                    (1.0, 0.8, 0.5), (0.7, 0.8, 1.0)],
    }


def _rot(p, ay, ax):
    x, y, z = p
    cx, sx = math.cos(ay), math.sin(ay)
    x2 = x * cx + z * sx
    z2 = -x * sx + z * cx
    x, z = x2, z2
    cy, sy = math.cos(ax), math.sin(ax)
    y2 = y * cy - z * sy
    z3 = y * sy + z * cy
    return (x, y2, z3)


def _line(hr, x1, y1, x2, y2, fg, z=0):
    n = max(abs(x2 - x1), abs(y2 - y1))
    if n == 0:
        hr.set_pixel(x1, y1, '·', fg=fg, z=z)
        return
    for i in range(n + 1):
        tt = i / n
        hr.set_pixel(int(x1 + (x2 - x1) * tt), int(y1 + (y2 - y1) * tt),
                     '·', fg=fg, z=z)


def scene_constellation(c, hr, t, pt, dt):
    """Constellation - a rotating sphere of stars joined by constellation lines"""
    w, h = hr.w, hr.h
    _init()
    s = _CON

    cx, cy = c.w / 2, c.h / 2
    for y in range(c.h):
        for x in range(c.w):
            nx = (x - cx) / (c.w * 0.5)
            ny = (y - cy) / (c.h * 0.5)
            d = math.hypot(nx, ny)
            col = Color(4, 3, 12).lerp(Color(20, 8, 40), max(0, 1 - d * 0.9))
            c.set_pixel(x, y, ' ', bg=col, z=-100)

    cx, cy = w / 2, h / 2
    scale = min(w, h) * 0.34
    ay = t * 0.25
    ax = 0.4 + 0.25 * math.sin(t * 0.1)

    proj = []
    for p in s['pts']:
        x, y, z = _rot(p, ay, ax)
        persp = 1.0 / (1.0 + 0.5 * z)
        px = cx + x * scale * persp
        py = cy - y * scale * persp
        depth = (z + 1) * 0.5
        proj.append((px, py, depth))

    for i, j in s['edges']:
        x1, y1, d1 = proj[i]
        x2, y2, d2 = proj[j]
        dim = 0.05 + 0.18 * (1 - (d1 + d2) / 2)
        b = int(255 * dim)
        _line(hr, int(x1), int(y1), int(x2), int(y2),
              Color(b, int(b * 0.9), int(b * 1.25)), z=20)

    for i, p in enumerate(proj):
        px, py, depth = p
        tw = 0.5 + 0.5 * math.sin(t * 1.5 + i * 1.37)
        fade = 1.0 - depth * 0.55
        if i in s['bright']:
            col_i = i % len(s['palette'])
            r, g, b = s['palette'][col_i]
            bri = (0.55 + 0.45 * tw) * fade
            col = Color(int(r * 255 * bri), int(g * 255 * bri),
                        int(b * 255 * bri))
            ch = '✦' if tw > 0.7 else '·'
            hr.set_pixel(int(px), int(py), ch, fg=col, z=60)
            if tw > 0.85:
                hr.set_pixel(int(px), int(py - 1), '·',
                             fg=col.mul(0.4), z=55)
        else:
            bri = (0.2 + 0.5 * tw) * fade
            if bri < 0.1:
                continue
            col = Color(int(150 * bri), int(160 * bri), int(255 * bri))
            hr.set_pixel(int(px), int(py), '·', fg=col, z=50)

    hr.to_canvas(c)
    c.draw_text(2, 0, '✦ Constellation ✦', Color(200, 210, 255), z=100)
    c.draw_text(2, c.h - 1, 'star sphere | constellation lines', DIM, z=100)
