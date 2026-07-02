import math, random
from spore_engine import *
from spore_engine.core.color import *
from spore_engine.sim.noise import PerlinNoise

_FF = None

def scene_flowfield(c, hr, t, pt, dt):
    global _FF
    w, h = c.w, c.h

    if _FF is None:
        noise = PerlinNoise(123)
        particles = []
        for _ in range(120):
            particles.append({
                'x': random.uniform(0, w),
                'y': random.uniform(0, h),
                'vx': 0.0, 'vy': 0.0,
                'hue': random.uniform(0.5, 1.0),
                'phase': random.uniform(0, 2*math.pi),
                'trail': [],
                'life': random.uniform(0.5, 1.0),
            })
        _FF = {'noise': noise, 'particles': particles, 'trail_max': 30}

    s = _FF

    for y in range(h):
        ty = y / h
        col = Color(int(ty * 3), int(ty * 2), int(ty * 8))
        for x in range(w):
            c.set_pixel(x, y, ' ', bg=col, z=-100)

    noise = s['noise']
    z_offset = t * 0.05

    field_scale = 0.03
    force_mag = 2.5

    for p in s['particles']:
        n_x = p['x'] * field_scale
        n_y = p['y'] * field_scale
        angle = noise.noise2(n_x + z_offset * 0.5, n_y + z_offset * 0.3) * math.pi * 3

        target_vx = math.cos(angle) * force_mag
        target_vy = math.sin(angle) * force_mag

        p['vx'] += (target_vx - p['vx']) * dt * 3
        p['vy'] += (target_vy - p['vy']) * dt * 3

        p['x'] += p['vx'] * dt * 6
        p['y'] += p['vy'] * dt * 6

        px, py2 = int(p['x']), int(p['y'])
        p['trail'].append((px, py2))
        if len(p['trail']) > s['trail_max']:
            p['trail'].pop(0)

        if p['x'] < -5 or p['x'] > w + 5 or p['y'] < -5 or p['y'] > h + 5:
            p['x'] = random.uniform(0, w)
            p['y'] = random.uniform(0, h)
            p['vx'] = 0
            p['vy'] = 0
            p['trail'] = []

        for i, (tx, ty2) in enumerate(p['trail']):
            if 0 <= tx < w and 0 <= ty2 < h:
                prog = i / len(p['trail'])
                bright = prog * 0.5
                if bright > 0.02:
                    hue = (p['hue'] + prog * 0.2 + t * 0.01) % 1.0
                    col = Color.from_hsv(hue, 0.6, bright)
                    ch = '·' if prog < 0.3 else ('░' if prog < 0.6 else '▒')
                    c.set_pixel(tx, ty2, ch, col, z=5)

        if 0 <= px < w and 0 <= py2 < h:
            speed = math.hypot(p['vx'], p['vy'])
            if speed > 0.5:
                hue = (p['hue'] + t * 0.01) % 1.0
                col = Color.from_hsv(hue, 0.8, min(1.0, speed * 0.4))
                c.set_pixel(px, py2, '·' if speed < 1.0 else '○', col, z=10)

    field_step = 20
    for fx in range(0, w, field_step):
        for fy in range(0, h, field_step):
            n_x = fx * field_scale
            n_y = fy * field_scale
            angle = noise.noise2(n_x + z_offset * 0.5, n_y + z_offset * 0.3) * math.pi * 3
            dx2 = math.cos(angle)
            dy2 = math.sin(angle)
            ex = int(fx + dx2 * 4)
            ey = int(fy + dy2 * 4)
            if 0 <= ex < w and 0 <= ey < h and 0 <= fx < w and 0 <= fy < h:
                hue = (0.6 + angle / (math.pi * 3) * 0.3 + t * 0.005) % 1.0
                c.set_pixel(fx, fy, '·', Color.from_hsv(hue, 0.3, 0.08), z=2)
                c.set_pixel(ex, ey, '·', Color.from_hsv(hue, 0.4, 0.12), z=2)
