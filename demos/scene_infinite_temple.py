import math, random
from spore_engine import *
from spore_engine.core.color import *

_IT = None

def scene_infinite_temple(c, hr, t, pt, dt):
    global _IT
    w, h = c.w, c.h
    cx, cy = w / 2, h * 0.55

    if _IT is None:
        orbs = []
        for _ in range(25):
            orbs.append({
                'angle': random.uniform(0, 2*math.pi),
                'dist': random.uniform(0.08, 0.4) * min(w, h),
                'phase': random.uniform(0, 2*math.pi),
                'hue': random.uniform(0.5, 1.0),
                'speed': random.uniform(0.2, 0.6),
            })
        particles = []
        for _ in range(60):
            particles.append({
                'angle': random.uniform(0, 2*math.pi),
                'dist': random.uniform(0, min(w, h) * 0.4),
                'phase': random.uniform(0, 2*math.pi),
                'hue': random.uniform(0.0, 1.0),
            })
        _IT = {'orbs': orbs, 'particles': particles}

    s = _IT

    for y in range(h):
        ty = y / h
        hue = 0.72 + ty * 0.08
        bright = 0.01 + ty * 0.05
        col = Color.from_hsv(hue % 1.0, 0.5, bright)
        for x in range(w):
            c.set_pixel(x, y, ' ', bg=col, z=-100)

    num_arches = 12
    for i in range(num_arches):
        arch_prog = i / num_arches
        depth = i * 0.15
        arch_width = int((w * 0.45) * (0.92 ** i))
        arch_height = int((h * 0.35) * (0.92 ** i))
        arch_x = int(cx - arch_width / 2)
        arch_y = int(cy - arch_height)

        if arch_width < 3 or arch_height < 3: break

        col_base = 0.5 - depth * 0.15
        pulse = 0.5 + 0.5 * math.sin(t * 0.3 + arch_prog * math.pi * 4)
        col_val = Color.from_hsv((0.72 + depth * 0.1 + t * 0.005) % 1.0,
                                 0.4 + pulse * 0.2,
                                 max(0.1, col_base + pulse * 0.1))

        for xx in range(int(arch_x), int(arch_x + arch_width) + 1):
            for yy in [arch_y, int(cy)]:
                if 0 <= xx < w and 0 <= yy < h:
                    c.set_pixel(xx, yy, '═' if yy == int(cy) else '╤', col_val, z=5)

        for yy in range(arch_y, int(cy) + 1):
            if 0 <= int(arch_x) < w and 0 <= yy < h:
                c.set_pixel(int(arch_x), yy, '║', col_val, z=5)
            if 0 <= int(arch_x + arch_width) < w and 0 <= yy < h:
                c.set_pixel(int(arch_x + arch_width), yy, '║', col_val, z=5)

        arch_points = []
        for a in range(0, 181, 15):
            a_rad = math.radians(a)
            arc_x = arch_x + (arch_width / 2) * (1 - math.cos(a_rad))
            arc_y = arch_y + (arch_height / 2) * math.sin(a_rad)
            arch_points.append((int(arc_x), int(arc_y)))
        for j in range(len(arch_points) - 1):
            x1, y1 = arch_points[j]
            x2, y2 = arch_points[j + 1]
            steps = max(1, int(math.hypot(x2 - x1, y2 - y1)))
            for s_i in range(steps + 1):
                frac = s_i / steps
                px = int(x1 + (x2 - x1) * frac)
                py = int(y1 + (y2 - y1) * frac)
                if 0 <= px < w and 0 <= py < h:
                    glow = 0.5 + 0.5 * math.sin(t * 0.5 + px * 0.1 + py * 0.1 + i)
                    col = col_val.mul(1 + glow * 0.3)
                    c.set_pixel(px, py, '▓', col, z=8)

    for o in s['orbs']:
        o['angle'] += o['speed'] * dt * 1.5
        o_dist = o['dist']
        px = int(cx + o_dist * math.cos(o['angle']))
        py = int(cy - 5 + o_dist * math.sin(o['angle']) * 0.3)
        if 0 <= px < w and 0 <= py < h:
            twinkle = 0.5 + 0.5 * math.sin(t * 1.5 + o['phase'])
            brightness = 0.3 + twinkle * 0.7
            hue = (o['hue'] + t * 0.01) % 1.0
            col = Color.from_hsv(hue, 0.8, brightness)
            ch = '○' if brightness > 0.6 else '·'
            c.set_pixel(px, py, ch, col, z=30)
            if brightness > 0.7:
                for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    if 0 <= px + dx < w and 0 <= py + dy < h:
                        c.set_pixel(px + dx, py + dy, '·', col.mul(0.25), z=29)

    mandala_radius = min(w, h) * 0.08
    for ring in range(3):
        r = mandala_radius * (1 + ring * 0.8)
        num_pts = 6 + ring * 6
        hue = (0.08 + ring * 0.12 + t * 0.005) % 1.0
        for p_i in range(num_pts):
            a = p_i / num_pts * 2 * math.pi + t * 0.1 * (1 if ring % 2 == 0 else -1)
            px = int(cx + r * math.cos(a))
            py = int(cy + r * math.sin(a))
            if 0 <= px < w and 0 <= py < h:
                bright = 0.4 + 0.6 * (0.5 + 0.5 * math.sin(t * 1.5 + p_i * 2 + ring))
                col = Color.from_hsv(hue, 0.7, bright)
                c.set_pixel(px, py, '✦', col, z=35)
            for p_j in range(p_i + 1, min(p_i + 3, num_pts)):
                a2 = p_j / num_pts * 2 * math.pi + t * 0.1 * (1 if ring % 2 == 0 else -1)
                px2 = int(cx + r * math.cos(a2))
                py2 = int(cy + r * math.sin(a2))
                steps = max(1, int(math.hypot(px2 - px, py2 - py)))
                for s_i in range(steps + 1):
                    frac = s_i / steps
                    lx = int(px + (px2 - px) * frac)
                    ly = int(py + (py2 - py) * frac)
                    if 0 <= lx < w and 0 <= ly < h:
                        col = Color.from_hsv(hue, 0.5, bright * 0.3)
                        c.set_pixel(lx, ly, '·', col, z=34)

    for p in s['particles']:
        p['angle'] += dt * (0.5 + 0.5 * math.sin(t * 0.2 + p['phase']))
        p_dist = p['dist']
        drift = 0.2 * math.sin(t * 0.3 + p['phase'] * 1.5)
        px = int(cx + (p_dist + drift) * math.cos(p['angle']))
        py = int(cy + (p_dist + drift) * math.sin(p['angle']) * 0.3)
        if 0 <= px < w and 0 <= py < h:
            tw = 0.3 + 0.7 * (0.5 + 0.5 * math.sin(t * 0.7 + p['phase']))
            if tw > 0.3:
                hue = (p['hue'] + t * 0.005) % 1.0
                b = tw * 0.5
                col = Color.from_hsv(hue, 0.6, b)
                c.set_pixel(px, py, '·', col, z=15)

    for xx in range(w):
        for yy in range(int(cy), min(h, int(cy) + 3)):
            if 0 <= xx < w and 0 <= yy < h:
                dist = abs(xx - cx) / (w * 0.4)
                if dist < 1:
                    a = 1 - dist
                    c.set_pixel(xx, yy, '═' if yy < int(cy) + 2 else ' ', Color(80, 60, 120).mul(a * 0.5), z=40)
