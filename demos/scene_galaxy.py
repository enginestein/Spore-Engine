import math, random
from spore_engine import *
from spore_engine.core.color import *

_GAL = None

def scene_galaxy(c, hr, t, pt, dt):
    global _GAL
    w, h = c.w, c.h
    cx, cy = w / 2, h / 2

    if _GAL is None:
        stars = []
        for _ in range(300):
            angle = random.random() * 2 * math.pi
            dist = math.sqrt(random.random()) * min(w, h) * 0.45
            arm_offset = random.gauss(0, 0.3)
            spiral_angle = angle + dist * 0.08 + arm_offset
            sx = cx + dist * math.cos(spiral_angle)
            sy = cy + dist * math.sin(spiral_angle)
            if 0 <= sx < w and 0 <= sy < h:
                stars.append({
                    'x': sx, 'y': sy, 'dist': dist, 'angle': angle,
                    'size': random.uniform(0.3, 1.0),
                    'hue_shift': random.uniform(0, 1),
                    'twinkle_phase': random.uniform(0, 2*math.pi),
                })
                stars.append({
                    'x': sx, 'y': sy, 'dist': dist,
                    'angle': angle + 0.5*math.pi,
                    'size': random.uniform(0.3, 1.0),
                    'hue_shift': random.uniform(0, 1)+0.5,
                    'twinkle_phase': random.uniform(0, 2*math.pi),
                })
        _GAL = {'stars': stars}

    s = _GAL

    for y in range(h):
        ty = y / h
        col = Color.from_hsv(0.72-ty*0.1, 0.5, 0.01+ty*0.04)
        for x in range(w):
            c.set_pixel(x, y, ' ', bg=col, z=-100)

    for y in range(h):
        for x in range(w):
            dx = (x - cx) / (w * 0.4)
            dy = (y - cy) / (h * 0.4)
            dist = math.hypot(dx, dy)
            angle = math.atan2(dy, dx)
            spiral = math.sin(dist * 5 - angle * 3 - t * 0.4) * 0.5 + 0.5
            glow = math.exp(-dist * 1.5) * 0.4
            if dist < 2.0:
                nebula = spiral * glow
                if nebula > 0.1:
                    hue = (0.7 + dist * 0.1 + t * 0.005) % 1.0
                    bright = 0.1 + nebula * 0.4
                    c.set_pixel(x, y, '░' if nebula<0.2 else ('▒' if nebula<0.3 else '▓'),
                               Color.from_hsv(hue, 0.8, bright), z=2)

    for s in _GAL['stars']:
        tw = 0.5 + 0.5 * math.sin(t * 1.5 + s['twinkle_phase'])
        if tw > 0.4:
            px, py = int(s['x']), int(s['y'])
            if 0 <= px < w and 0 <= py < h:
                hue = (s['hue_shift'] + t * 0.01) % 1.0
                b = 0.3 + tw * 0.7 * s['size']
                ch = '·' if s['size'] < 0.5 else ('★' if s['size'] > 0.8 else '✦')
                c.set_pixel(px, py, ch, Color.from_hsv(hue, 0.6, b), z=5)
                if s['size'] > 0.7 and tw > 0.7:
                    for dx, dy in [(-1,0),(1,0),(0,-1),(0,1)]:
                        c.set_pixel(px+dx, py+dy, '·',
                                   Color.from_hsv(hue, 0.4, b*0.3), z=4)

    core_r = int(min(w, h) * 0.05)
    for r in range(core_r, 0, -1):
        alpha = 0.5 * (1 - r/core_r)
        for dx in range(-r, r+1):
            for dy in range(-r, r+1):
                if math.hypot(dx, dy) <= r:
                    px, py = int(cx+dx), int(cy+dy)
                    if 0 <= px < w and 0 <= py < h:
                        col = Color.from_hsv(0.08, 1.0, 0.6+0.4*(1-r/core_r))
                        c.set_pixel(px, py, ' ', bg=col, z=1)
