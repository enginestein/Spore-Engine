import math, random
from spore_engine import *
from spore_engine.core.color import *

_PG = None

def scene_phantom_galaxy(c, hr, t, pt, dt):
    global _PG
    w, h = c.w, c.h
    cx, cy = w // 2, h // 2

    if _PG is None:
        stars = []
        for _ in range(200):
            angle = random.uniform(0, 2*math.pi)
            rad = random.uniform(0, min(w, h)*0.45)
            stars.append({
                'angle': angle, 'rad': rad,
                'hue': random.uniform(0.55, 0.8),
                'phase': random.uniform(0, 2*math.pi),
                'bright': random.uniform(0.3, 1.0),
            })
        _PG = {'stars': stars}

    s = _PG

    for y in range(h):
        col = Color(int(1+y*3//h*6), int(0+y*2//h*4), int(3+y*5//h*12))
        for x in range(w):
            c.set_pixel(x, y, ' ', bg=col, z=-100)

    for py in range(h):
        for px in range(w):
            dx, dy = px - cx, py - cy
            d = math.hypot(dx, dy) / max(w, h)
            if d > 0.55:
                continue
            a = math.atan2(dy, dx)
            spiral = a + d * 8 + t * 0.15
            dust = 0.5 + 0.5 * math.sin(spiral * 2)
            dust = max(0, min(1, dust * (1 - d/0.55)))
            if dust > 0.05:
                hue = (d*4 + t*0.005 + 0.65) % 1.0
                sat = 0.4 + 0.5 * dust
                bright = 0.05 + dust * 0.5 * (1 - d/0.55)
                ch = ' ' if bright < 0.1 else ('░' if bright < 0.2 else ('▒' if bright < 0.35 else ('▓' if bright < 0.5 else '█')))
                c.set_pixel(px, py, ch, Color.from_hsv(hue, sat, bright), z=3)

    for st in s['stars']:
        st['angle'] += dt * (0.1 + 0.2 / max(0.1, st['rad']+1))
        px = int(cx + st['rad'] * math.cos(st['angle']))
        py = int(cy + st['rad'] * math.sin(st['angle']))
        if 0 <= px < w and 0 <= py < h:
            pulse = 0.5 + 0.5 * math.sin(t*0.5 + st['phase'])
            b = st['bright'] * pulse
            col = Color.from_hsv(st['hue'], 0.5, 0.2+0.6*b)
            c.set_pixel(px, py, '·' if b < 0.5 else '●', col, z=8)
            if b > 0.7:
                for dx, dy in [(-1,0),(1,0),(0,-1),(0,1)]:
                    if 0 <= px+dx < w and 0 <= py+dy < h:
                        c.set_pixel(px+dx, py+dy, '·', col.mul(0.3), z=7)

    core_r = min(w, h) * 0.05
    for dy in range(-int(core_r), int(core_r)+1):
        for dx in range(-int(core_r), int(core_r)+1):
            d = math.hypot(dx, dy)
            if d <= core_r and 0 <= cx+dx < w and 0 <= cy+dy < h:
                a = 1 - d/core_r
                col = Color.from_hsv((t*0.01+0.72)%1.0, 0.5, 0.2+a*0.8)
                c.set_pixel(cx+dx, cy+dy, '█', col, z=10)

    if 0 <= cy < h and 0 <= cx < w:
        c.set_pixel(cx, cy, '●', Color(255, 230, 220), z=15)

    for _ in range(5):
        px = random.randint(0, w-1)
        py = random.randint(0, h-1)
        c.set_pixel(px, py, '·', Color(200, 200, 255).mul(random.uniform(0.05, 0.2)), z=1)
