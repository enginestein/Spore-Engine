import math, random
from spore_engine import *
from spore_engine.core.color import *

_LO = None

def scene_lorenz(c, hr, t, pt, dt):
    global _LO
    w, h = c.w, c.h

    if _LO is None:
        sigma, rho, beta = 10.0, 28.0, 8.0 / 3.0
        attractors = []
        for _ in range(8):
            attractors.append({
                'x': random.uniform(-8, 8),
                'y': random.uniform(-8, 8),
                'z': random.uniform(20, 30),
                'trail': [],
                'hue': random.uniform(0.0, 1.0),
            })
        _LO = {'sigma': sigma, 'rho': rho, 'beta': beta,
               'attractors': attractors, 'rot': 0,
               'trail_max': 80}

    s = _LO
    s['rot'] += dt * 0.15
    scale = min(w, h) * 0.035
    cx, cy = w / 2, h * 0.45

    for y in range(h):
        ty = y / h
        col = Color(int(ty * 5), int(ty * 3), int(ty * 10 + 2))
        for x in range(w):
            c.set_pixel(x, y, ' ', bg=col, z=-100)

    dt_sim = min(dt * 3.0, 0.02)
    sub_steps = 4
    dt_sub = dt_sim / sub_steps
    rot = s['rot']

    for a in s['attractors']:
        sigma, rho, beta = s['sigma'], s['rho'], s['beta']
        x, y, z = a['x'], a['y'], a['z']

        for _ in range(sub_steps):
            dx = sigma * (y - x)
            dy = x * (rho - z) - y
            dz = x * y - beta * z
            x += dx * dt_sub
            y += dy * dt_sub
            z += dz * dt_sub

        if not (math.isfinite(x) and math.isfinite(y) and math.isfinite(z)):
            x = random.uniform(-8, 8)
            y = random.uniform(-8, 8)
            z = random.uniform(20, 30)
            a['trail'] = []

        a['x'], a['y'], a['z'] = x, y, z

        yz = y * math.cos(rot) - z * math.sin(rot)
        px = int(cx + x * scale)
        py = int(cy - yz * scale * 0.6)

        a['trail'].append((px, py))
        if len(a['trail']) > s['trail_max']:
            a['trail'].pop(0)

        for i, (tx, ty2) in enumerate(a['trail']):
            if 0 <= tx < w and 0 <= ty2 < h:
                prog = i / len(a['trail'])
                bright = prog * 0.7
                hue = (a['hue'] + prog * 0.15 + t * 0.005) % 1.0
                col = Color.from_hsv(hue, 0.7, bright)
                ch = '·' if prog < 0.3 else ('░' if prog < 0.5 else ('▒' if prog < 0.75 else '▓'))
                c.set_pixel(tx, ty2, ch, col, z=5)

        if 0 <= px < w and 0 <= py < h:
            hue = (a['hue'] + t * 0.01) % 1.0
            c.set_pixel(px, py, '●', Color.from_hsv(hue, 0.9, 1.0), z=10)
            for dx2, dy2 in [(-1,0),(1,0),(0,-1),(0,1)]:
                if 0 <= px+dx2 < w and 0 <= py+dy2 < h:
                    c.set_pixel(px+dx2, py+dy2, '·', Color.from_hsv(hue, 0.6, 0.3), z=9)

    for x in range(w):
        for y2 in range(int(cy + min(w, h) * 0.02), min(h, int(cy + min(w, h) * 0.025))):
            if 0 <= x < w and 0 <= y2 < h:
                c.set_pixel(x, y2, ' ', Color(0, 0, 0), z=-50)
