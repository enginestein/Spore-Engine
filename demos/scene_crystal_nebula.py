import math, random
from spore_engine import *
from spore_engine.core.color import *

_CN = None

def scene_crystal_nebula(c, hr, t, pt, dt):
    global _CN
    w, h = c.w, c.h
    cx, cy = w / 2, h / 2

    if _CN is None:
        crystals = []
        for _ in range(12):
            size = random.uniform(1.5, 5.0)
            crystals.append({
                'x': random.uniform(w * 0.1, w * 0.9),
                'y': random.uniform(h * 0.1, h * 0.9),
                'z': random.uniform(0.3, 1.0),
                'size': size,
                'rot': random.uniform(0, 2*math.pi),
                'rot_speed': random.uniform(-0.3, 0.3),
                'hue': random.uniform(0.55, 0.95),
                'hue_width': random.uniform(0.05, 0.2),
                'phase': random.uniform(0, 2*math.pi),
                'sharpness': random.uniform(0.5, 1.0),
            })
        floaters = []
        for _ in range(80):
            floaters.append({
                'x': random.uniform(0, w), 'y': random.uniform(0, h),
                'vx': random.uniform(-0.2, 0.2), 'vy': random.uniform(-0.2, 0.2),
                'hue': random.uniform(0.5, 1.0),
                'phase': random.uniform(0, 2*math.pi),
                'size': random.uniform(0.3, 1.0),
            })
        _CN = {'crystals': crystals, 'floaters': floaters}

    s = _CN

    for y in range(h):
        ty = y / h
        for x in range(w):
            dx = (x - cx) / (w * 0.4)
            dy = (y - cy) / (h * 0.4)
            d = math.hypot(dx, dy)
            bg_val = 0.01 + 0.03 * (0.5 + 0.5 * math.sin(d * 2 - t * 0.1 + x * 0.01 + y * 0.01))
            hue_bg = (0.7 + d * 0.05 + t * 0.002) % 1.0
            c.set_pixel(x, y, ' ', bg=Color.from_hsv(hue_bg, 0.4, bg_val), z=-100)

    nebula_bands = 4
    for band in range(nebula_bands):
        for y in range(h):
            ty = y / h
            for x in range(w):
                dx = (x - cx) / (w * 0.35)
                dy = (y - cy) / (h * 0.35)
                d = math.hypot(dx, dy)
                angle = math.atan2(dy, dx) + band * 1.5 + t * 0.05
                n = math.sin(d * 1.5 + angle * 2 + t * 0.15 + band) * 0.5 + 0.5
                n *= math.exp(-d * 1.2)
                if n > 0.04:
                    hue = (0.65 + band * 0.07 + d * 0.06 + t * 0.003) % 1.0
                    bright = n * 0.5
                    c.set_pixel(x, y, '░', Color.from_hsv(hue, 0.7, bright), z=1)

    c.set_pixel(0, 0, ' ', bg=Color(0, 0, 0), z=-100)

    sorted_crystals = sorted(s['crystals'], key=lambda cr: cr['z'])
    for cr in sorted_crystals:
        cr['rot'] += cr['rot_speed'] * dt
        sz = cr['size']
        rot = cr['rot']
        cx_cr, cy_cr = cr['x'], cr['y']
        pulse = 0.8 + 0.2 * math.sin(t * 0.5 + cr['phase'])
        sz_pulse = sz * pulse

        def crystal_face(cx, cy, rot, sz, hue_base, offset, z_val):
            points = []
            for i in range(6):
                a = rot + i * math.pi / 3 + offset
                r = sz * (0.7 + 0.3 * math.sin(i * 2.5 + rot))
                px = cx + r * math.cos(a)
                py = cy + r * math.sin(a) * 0.5
                points.append((px, py))
            for i in range(len(points) - 1):
                x1, y1 = points[i]
                x2, y2 = points[i + 1]
                segments = max(1, int(math.hypot(x2 - x1, y2 - y1)))
                for s_i in range(segments + 1):
                    frac = s_i / segments
                    px = int(x1 + (x2 - x1) * frac)
                    py = int(y1 + (y2 - y1) * frac)
                    if 0 <= px < w and 0 <= py < h:
                        dist_from_center = math.hypot(px - cx, (py - cy) * 2) / max(1, sz)
                        glow = 1 - min(1, dist_from_center * 0.4)
                        hue = (hue_base + dist_from_center * 0.1 + t * 0.01 + offset) % 1.0
                        bright = min(1.0, pulse * (0.5 + 0.5 * glow) * (1 - dist_from_center * 0.1))
                        col = Color.from_hsv(hue, 0.6 + 0.4 * glow, bright)
                        ch = '░' if glow < 0.3 else ('▒' if glow < 0.6 else '▓')
                        c.set_pixel(px, py, ch, col, z=int(z_val))

        crystal_face(cx_cr, cy_cr, rot, sz_pulse, cr['hue'], 0, 20)
        crystal_face(cx_cr, cy_cr, rot + 0.3, sz_pulse * 0.85, cr['hue'] + 0.15, 0.5, 18)
        crystal_face(cx_cr, cy_cr, rot - 0.3, sz_pulse * 0.7, cr['hue'] - 0.1, -0.5, 16)

        glow_r = int(sz_pulse * 1.5)
        for gx in range(-glow_r, glow_r + 1):
            for gy2 in range(-glow_r, glow_r + 1):
                gd = math.hypot(gx, gy2)
                if gd <= glow_r:
                    px, py2 = int(cx_cr + gx), int(cy_cr + gy2)
                    if 0 <= px < w and 0 <= py2 < h:
                        a = 1 - gd / glow_r
                        hue = (cr['hue'] + a * 0.1 + t * 0.01) % 1.0
                        bright = pulse * a * 0.15
                        if bright > 0.02:
                            c.set_pixel(px, py2, ' ', bg=Color.from_hsv(hue, 0.4, bright), z=14)

    for fl in s['floaters']:
        fl['x'] += fl['vx'] * dt * 15 + math.sin(t * 0.3 + fl['phase']) * 0.1
        fl['y'] += fl['vy'] * dt * 15 + math.cos(t * 0.2 + fl['phase'] * 1.3) * 0.1
        fl['x'] = fl['x'] % w
        fl['y'] = fl['y'] % h
        px, py2 = int(fl['x']), int(fl['y'])
        if 0 <= px < w and 0 <= py2 < h:
            tw = 0.3 + 0.7 * (0.5 + 0.5 * math.sin(t * 0.8 + fl['phase']))
            b = tw * fl['size'] * 0.5
            if b > 0.05:
                hue = (fl['hue'] + t * 0.005) % 1.0
                col = Color.from_hsv(hue, 0.6, b)
                ch = '·'
                c.set_pixel(px, py2, ch, col, z=5)
