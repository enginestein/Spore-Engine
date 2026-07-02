import math, random
from spore_engine import *
from spore_engine.core.color import *

_MS = None

def scene_meteor(c, hr, t, pt, dt):
    global _MS
    w, h = c.w, c.h

    if _MS is None:
        meteors = []
        for _ in range(10):
            meteors.append({
                'x': random.uniform(-w*0.3, w*1.3),
                'y': random.uniform(-h*0.2, h*0.3),
                'vx': random.uniform(4, 12),
                'vy': random.uniform(2, 8),
                'bright': random.uniform(0.5, 1.0),
                'hue': random.uniform(0.0, 0.15),
                'trail': [],
                'life': random.uniform(2, 6),
                'age': random.uniform(0, 5),
            })
        _MS = {'meteors': meteors}

    s = _MS

    for y in range(h):
        ty = y / h
        col = Color.from_hsv(0.7-ty*0.1, 0.5, 0.01+ty*0.05)
        for x in range(w):
            c.set_pixel(x, y, ' ', bg=col, z=-100)

    for y in range(h):
        for x in range(w):
            n = (math.sin(x*0.05+t*0.2)+math.cos(y*0.04+t*0.15))*0.5+0.5
            if n > 0.85:
                c.set_pixel(x, y, '·', Color(150, 150, 180).mul(0.2), z=1)

    for m in s['meteors']:
        m['age'] += dt
        if m['age'] >= m['life']:
            m['x'] = random.uniform(-w*0.3, w*0.1)
            m['y'] = random.uniform(-h*0.2, h*0.1)
            m['vx'] = random.uniform(4, 12)
            m['vy'] = random.uniform(2, 8)
            m['bright'] = random.uniform(0.5, 1.0)
            m['hue'] = random.uniform(0.0, 0.15)
            m['trail'] = []
            m['age'] = 0
            m['life'] = random.uniform(2, 6)
        m['x'] += m['vx'] * dt * 5
        m['y'] += m['vy'] * dt * 5
        m['trail'].append((int(m['x']), int(m['y'])))
        if len(m['trail']) > 20:
            m['trail'].pop(0)

        progress = m['age'] / m['life']
        fade = 1.0 - progress * 0.7

        for i, (tx, ty) in enumerate(m['trail'][:-1]):
            a = i / max(1, len(m['trail'])) * fade
            if 0 <= tx < w and 0 <= ty < h:
                ch = '·' if a < 0.2 else ('░' if a < 0.4 else '▒')
                col = Color.from_hsv(m['hue'], 0.8, 0.1+a*0.6)
                c.set_pixel(tx, ty, ch, col, z=5)

        px, py = int(m['x']), int(m['y'])
        if 0 <= px < w and 0 <= py < h:
            b = m['bright'] * fade
            col = Color.from_hsv(m['hue'], 0.9, 0.7+0.3*b)
            c.set_pixel(px, py, '●', col, z=10)
            for dx, dy in [(-1,0),(1,0),(0,-1),(0,1)]:
                if 0 <= px+dx < w and 0 <= py+dy < h:
                    c.set_pixel(px+dx, py+dy, '·', col.mul(0.4*b), z=9)
            if b > 0.6:
                for dx, dy in [(-2,-1),(2,-1),(-1,-2),(1,-2)]:
                    if 0 <= px+dx < w and 0 <= py+dy < h:
                        c.set_pixel(px+dx, py+dy, '·', col.mul(0.2*b), z=8)
