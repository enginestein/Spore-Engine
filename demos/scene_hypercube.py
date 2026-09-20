import math
import random
from spore_engine import *
from spore_engine.core.color import *

_HC = None


def _init(w, h):
    global _HC
    if _HC is not None:
        return
    rnd = random.Random(5)
    _HC = {
        'stars': [(rnd.uniform(0, w), rnd.uniform(0, h),
                   rnd.uniform(0, 2 * math.pi), rnd.uniform(0.2, 1.0))
                  for _ in range(120)],
    }


def _rot4(p, a, b, ang):
    c, s = math.cos(ang), math.sin(ang)
    q = list(p)
    q[a] = p[a] * c - p[b] * s
    q[b] = p[a] * s + p[b] * c
    return q


def _build_verts_edges():
    verts = []
    for i in range(16):
        v = []
        for k in range(4):
            v.append(-1 if (i >> k) & 1 else 1)
        verts.append(v)
    edges = []
    for i in range(16):
        for j in range(i + 1, 16):
            diff = i ^ j
            if diff & (diff - 1) == 0:
                axis = int(math.log2(diff))
                edges.append((i, j, axis))
    return verts, edges


_AXIS_HUE = [0.5, 0.85, 0.3, 0.12]


def _proj(p, t, cx, cy, scale):
    v = _rot4(p, 0, 3, t * 0.42)
    v = _rot4(v, 1, 3, t * 0.31)
    v = _rot4(v, 0, 1, t * 0.24)
    x, y, z, w = v
    f4 = 1.0 / (1.0 + 0.28 * w)
    x, y, z = x * f4, y * f4, z * f4

    c, s = math.cos(t * 0.15), math.sin(t * 0.15)
    x2 = x * c + z * s
    z2 = -x * s + z * c
    x, z = x2, z2

    persp = 1.0 / (1.0 + 0.42 * z)
    px = cx + x * persp * scale
    py = cy - y * persp * scale
    depth = (z + 1) * 0.5
    return px, py, depth


def scene_hypercube(c, hr, t, pt, dt):
    """Hypercube - a rotating 4D tesseract projected into 3D space"""
    w, h = hr.w, hr.h
    _init(w, h)
    s = _HC

    for y in range(c.h):
        for x in range(c.w):
            c.set_pixel(x, y, ' ', bg=Color(2, 2, 10), z=-100)

    for sx, sy, ph, bri in s['stars']:
        tw = 0.4 + 0.6 * (0.5 + 0.5 * math.sin(t * 1.2 + ph * 4 + sx * 2.1))
        v = tw * bri
        if v < 0.15:
            continue
        b = int(min(255, v * 255))
        hr.set_pixel(int(sx), int(sy), '·',
                     fg=Color(b, b, min(255, int(b * 1.25))), z=40)

    cx, cy = w / 2, h / 2
    scale = min(w, h) * 0.32

    verts, edges = _build_verts_edges()
    proj = [_proj(p, t, cx, cy, scale) for p in verts]

    for i, j, axis in edges:
        x1, y1, d1 = proj[i]
        x2, y2, d2 = proj[j]
        dim = 0.10 + 0.65 * (1 - (d1 + d2) / 2)
        hue = _AXIS_HUE[axis]
        col = Color.from_hsv((hue + t * 0.01) % 1, 0.9, dim)
        n = max(abs(int(x2) - int(x1)), abs(int(y2) - int(y1)))
        if n == 0:
            hr.set_pixel(int(x1), int(y1), '·', fg=col, z=50)
            continue
        for k in range(n + 1):
            tt = k / n
            hr.set_pixel(int(x1 + (x2 - x1) * tt), int(y1 + (y2 - y1) * tt),
                         '·', fg=col, z=50)

    for i, p in enumerate(proj):
        px, py, depth = p
        tw = 0.5 + 0.5 * math.sin(t * 2.5 + i * 1.3)
        dim = 0.35 + 0.65 * (1 - depth) * tw
        col = Color.from_hsv(0.55, 0.4, 0.3 + 0.7 * dim)
        hr.set_pixel(int(px), int(py), '●', fg=col, z=60)

    hr.to_canvas(c)
    c.draw_text(2, 0, '◈ Hypercube ◈', Color.from_hsv(0.55, 0.9, 1.0), z=100)
    c.draw_text(2, c.h - 1,
                '4D tesseract | projected | axis-colored', DIM, z=100)
