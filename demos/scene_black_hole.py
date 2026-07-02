import math, random
from spore_engine import *
from spore_engine.core.color import *

_BH = None

def scene_black_hole(c, hr, t, pt, dt):
    global _BH
    w, h = c.w, c.h
    cx, cy = w / 2, h * 0.42

    if _BH is None:
        disc_parts = []
        for _ in range(200):
            dist = random.uniform(3, min(w, h) * 0.38)
            angle = random.uniform(0, 2 * math.pi)
            disc_parts.append({
                'dist': dist, 'angle': angle,
                'hue_shift': random.uniform(0, 1),
                'speed': 0.3 + 2.0 / max(1, dist * 0.5),
            })
        bg_stars = []
        for _ in range(150):
            sx = random.uniform(0, w)
            sy = random.uniform(0, h * 0.85)
            twinkle = random.uniform(0, 2 * math.pi)
            bg_stars.append({'x': sx, 'y': sy, 'phase': twinkle, 'size': random.uniform(0.3, 1.0)})
        jet_dirs = []
        for _ in range(60):
            jet_dirs.append({'ang': random.uniform(-0.15, 0.15), 'speed': random.uniform(0.5, 2.0), 'phase': random.uniform(0, 2*math.pi)})
        _BH = {'disc': disc_parts, 'stars': bg_stars, 'jets': jet_dirs}

    s = _BH

    for y in range(h):
        ty = y / h
        col = Color(0, int(ty * 4), int(ty * 6 + 2))
        for x in range(w):
            c.set_pixel(x, y, ' ', bg=col, z=-100)

    for star in s['stars']:
        px, py = int(star['x']), int(star['y'])
        dx = px - cx
        dy = py - cy
        dist = math.hypot(dx, dy)
        angle = math.atan2(dy, dx)

        if dist > 5:
            lensing = 1 + 8 / max(1, dist * 0.8)
            lens_dist = dist ** 0.85
            src_angle = angle + math.sin(angle * 2 - t * 0.1) * 2 / max(1, dist)
            src_x = cx + math.cos(src_angle) * lens_dist
            src_y = cy + math.sin(src_angle) * lens_dist
            if 0 <= src_x < w and 0 <= src_y < h:
                tw = 0.5 + 0.5 * math.sin(t * 1.2 + star['phase'])
                mag = 1 + 4 / max(1, dist * 0.6)
                brightness = min(1.0, tw * star['size'] * mag * 0.5)
                if brightness > 0.1:
                        col = Color(
                            int(180 * brightness) + int(40 * brightness * math.sin(t + px * 0.1)),
                            int(200 * brightness),
                            int(255 * brightness))
                        ch = '·' if brightness < 0.3 else ('✦' if brightness < 0.6 else '★')
                        c.set_pixel(px, py, ch, col, z=3)

    ev_horizon = min(w, h) * 0.045
    for dy in range(-int(ev_horizon * 1.5), int(ev_horizon * 1.5)):
        for dx in range(-int(ev_horizon * 1.5), int(ev_horizon * 1.5)):
            d = math.hypot(dx, dy)
            px, py2 = int(cx + dx), int(cy + dy)
            if 0 <= px < w and 0 <= py2 < h:
                if d <= ev_horizon:
                    c.set_pixel(px, py2, ' ', bg=Color(0, 0, 0), z=50)
                elif d <= ev_horizon * 1.4:
                    glow = 1 - (d - ev_horizon) / (ev_horizon * 0.4)
                    ph = 0.5 + 0.5 * math.sin(t * 2 + dx * 0.5 + dy * 0.5)
                    col = Color(int(60 * glow * ph), int(40 * glow * ph), int(100 * glow * ph))
                    c.set_pixel(px, py2, '·', col, z=49)

    for part in s['disc']:
        part['angle'] += part['speed'] * dt * 2.0
        if abs(part['dist'] - 4) < 1:
            part['angle'] += dt * 3.0
        dist = part['dist']
        angle = part['angle']
        x = cx + dist * math.cos(angle)
        y = cy + dist * math.sin(angle) * 0.35
        px, py2 = int(x), int(y)
        if 0 <= px < w and 0 <= py2 < h:
            vel_dir = -math.sin(angle), math.cos(angle) * 0.35
            doppler = 0.7 + 0.3 * math.cos(angle - math.atan2(vel_dir[1], vel_dir[0]))
            inner_glow = 1 - (dist - 3) / max(1, min(w, h) * 0.38 - 3)
            brightness = min(1.0, inner_glow * doppler)
            if brightness > 0.05:
                hue = (0.02 + inner_glow * 0.08 + part['hue_shift'] * 0.03 + t * 0.005) % 1.0
                sat = 0.6 + inner_glow * 0.4
                col = Color.from_hsv(hue, sat, min(1.0, brightness * 1.2))
                ch = '░' if brightness < 0.3 else ('▒' if brightness < 0.5 else ('▓' if brightness < 0.7 else '█'))
                c.set_pixel(px, py2, ch, col, z=20)

    for j in s['jets']:
        j_angle = j['ang'] + math.sin(t * 0.3 + j['phase']) * 0.05
        jet_speed = j['speed'] * (1 + 0.3 * math.sin(t * 0.5 + j['phase'] * 2))
        for dist in range(1, int(min(w, h) * 0.35)):
            r = dist * 0.015
            nx = cx + math.cos(-math.pi / 2 + j_angle) * dist
            ny = cy + math.sin(-math.pi / 2 + j_angle) * dist
            for spread in [-1, 0, 1]:
                sdx = nx + spread * r * dist * 0.05
                sdy = ny + spread * r * dist * 0.05
                px, py2 = int(sdx), int(sdy)
                if 0 <= px < w and 0 <= py2 < h:
                    pulse = 0.5 + 0.5 * math.sin(t * 1.5 - dist * 0.1 + j['phase'])
                    bright = max(0, (1 - dist / (min(w, h) * 0.35)) * pulse * 0.6)
                    if bright > 0.05:
                        hue = (0.65 + dist * 0.005 + t * 0.01) % 1.0
                        col = Color.from_hsv(hue, 0.8, bright)
                        c.set_pixel(px, py2, '·' if bright < 0.2 else ('░' if bright < 0.4 else '▒'), col, z=25)

        for dist in range(1, int(min(w, h) * 0.35)):
            r = dist * 0.015
            nx = cx + math.cos(math.pi / 2 + j_angle) * dist
            ny = cy + math.sin(math.pi / 2 + j_angle) * dist
            for spread in [-1, 0, 1]:
                sdx = nx + spread * r * dist * 0.05
                sdy = ny + spread * r * dist * 0.05
                px, py2 = int(sdx), int(sdy)
                if 0 <= px < w and 0 <= py2 < h:
                    pulse = 0.5 + 0.5 * math.sin(t * 1.5 - dist * 0.1 + j['phase'])
                    bright = max(0, (1 - dist / (min(w, h) * 0.35)) * pulse * 0.6)
                    if bright > 0.05:
                        hue = (0.65 + dist * 0.005 + t * 0.01) % 1.0
                        col = Color.from_hsv(hue, 0.8, bright)
                        c.set_pixel(px, py2, '·' if bright < 0.2 else ('░' if bright < 0.4 else '▒'), col, z=25)
