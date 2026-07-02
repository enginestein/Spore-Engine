import math, random
from spore_engine import *
from spore_engine.core.color import *

_LAVA = None

def scene_lava(c, hr, t, pt, dt):
    global _LAVA
    w, h = c.w, c.h

    if _LAVA is None:
        blobs = []
        for _ in range(5):
            blobs.append({
                'cx': random.uniform(0, w), 'cy': random.uniform(0, h),
                'vx': random.uniform(-3, 3), 'vy': random.uniform(-3, 3),
                'r': random.uniform(3, 8),
                'phase': random.uniform(0, 2*math.pi),
                'hue': random.uniform(0, 0.12),
            })
        _LAVA = {'blobs': blobs}

    s = _LAVA

    for y in range(h):
        ty = y / h
        col = Color(int(2+ty*5), int(1+ty*3), int(4+ty*6))
        for x in range(w):
            c.set_pixel(x, y, ' ', bg=col, z=-100)

    for bl in s['blobs']:
        bl['cx'] += bl['vx'] * dt
        bl['cy'] += bl['vy'] * dt
        bl['cx'] += math.sin(t*0.7+bl['phase']) * dt * 2
        bl['cy'] += math.cos(t*0.5+bl['phase']) * dt * 2
        bl['vx'] += math.sin(t*0.3+bl['phase'])*dt*5
        bl['vy'] += math.cos(t*0.4+bl['phase']*1.3)*dt*5
        bl['vx'] *= 0.99
        bl['vy'] *= 0.99
        bl['cx'] = max(bl['r'], min(w-1-bl['r'], bl['cx']))
        bl['cy'] = max(bl['r'], min(h-1-bl['r'], bl['cy']))

    offscreen = [[0.0]*w for _ in range(h)]
    for y in range(h):
        for x in range(w):
            val = 0.0
            for bl in s['blobs']:
                dx = x - bl['cx']
                dy = y - bl['cy']
                d = math.hypot(dx, dy)
                blob_val = (bl['r'] * 2) / (d + 1)
                val += blob_val
            offscreen[y][x] = val

    for y in range(h):
        for x in range(w):
            val = offscreen[y][x]
            vn = offscreen[y-1][x] if y > 0 else 0
            vs = offscreen[y+1][x] if y < h-1 else 0
            ve = offscreen[y][x+1] if x < w-1 else 0
            vw = offscreen[y][x-1] if x > 0 else 0
            grad = abs(vn-vs) + abs(ve-vw)

            heat = min(1.0, val * 0.3)
            if heat > 0.1:
                hue = (0.05 + heat * 0.08 + t * 0.005) % 1.0
                sat = 0.7 + 0.3 * heat
                bright = 0.2 + heat * 0.8
                if grad > 0.5:
                    ch = '░' if heat < 0.3 else ('▒' if heat < 0.5 else ('▓' if heat < 0.7 else '█'))
                else:
                    ch = '█'
                c.set_pixel(x, y, ch, Color.from_hsv(hue, sat, bright), z=5)
            elif grad > 0.3:
                c.set_pixel(x, y, '░', Color(10, 5, 15).mul(0.5), z=3)

    for bl in s['blobs']:
        px, py = int(bl['cx']), int(bl['cy'])
        if 0 <= px < w and 0 <= py < h:
            c.set_pixel(px, py, '●', Color(255, 255, 200), z=10)
