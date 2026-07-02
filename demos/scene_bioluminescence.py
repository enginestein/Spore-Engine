import math, random
from spore_engine import *
from spore_engine.core.color import *

_BIO = None

def scene_bioluminescence(c, hr, t, pt, dt):
    global _BIO
    w, h = c.w, c.h

    if _BIO is None:
        jellies = []
        for _ in range(4):
            jellies.append({
                'x': random.uniform(0, w), 'y': random.uniform(h*0.15, h*0.6),
                'vx': random.uniform(-0.3, 0.3), 'vy': random.uniform(-0.15, 0.15),
                'hue': random.choice([0.55, 0.6, 0.65, 0.7, 0.75, 0.8]),
                'phase': random.uniform(0, 2*math.pi),
                'size': random.uniform(2, 4),
            })
        plankton = []
        for _ in range(40):
            plankton.append({
                'x': random.uniform(0, w), 'y': random.uniform(0, h),
                'hue': random.uniform(0.2, 0.8),
                'vx': random.uniform(-0.2, 0.2), 'vy': random.uniform(-0.1, -0.3),
                'bright': random.uniform(0.3, 0.8),
            })
        _BIO = {'jellies': jellies, 'plankton': plankton}

    s = _BIO

    for y in range(h):
        ty = y / h
        col = Color(int(2+ty*6), int(0+ty*2), int(5+ty*15))
        for x in range(w):
            c.set_pixel(x, y, ' ', bg=col, z=-100)

    for p in s['plankton']:
        p['x'] += p['vx'] * dt * 8
        p['y'] += p['vy'] * dt * 8
        if p['y'] < -2: p['y'] = h+2; p['x'] = random.uniform(2, w-2)
        if p['x'] < -2: p['x'] = w+2
        if p['x'] > w+2: p['x'] = -2
        px, py = int(p['x']), int(p['y'])
        if 0 <= px < w and 0 <= py < h:
            pulse = 0.5 + 0.5 * math.sin(t * 0.5 + p['hue'] * 10)
            b = p['bright'] * pulse
            col = Color.from_hsv(p['hue'], 0.7, b*0.4)
            c.set_pixel(px, py, '·', col, z=5)

    for j in s['jellies']:
        j['x'] += j['vx'] * dt * 12
        j['y'] += j['vy'] * dt * 10
        j['vy'] += math.sin(t*0.5+j['phase'])*dt*0.5
        j['x'] = max(2, min(w-3, j['x']))
        j['y'] = max(2, min(h-3, j['y']))
        px, py_ = int(j['x']), int(j['y'])
        sz = int(j['size'])
        hue = j['hue']
        pulse = 0.6 + 0.4 * math.sin(t * 1.5 + j['phase'])

        for dy in range(-sz*2, sz+1):
            for dx in range(-sz, sz+1):
                d = math.hypot(dx, dy)
                if d <= sz * 1.5:
                    pp, pyp = px+dx, py_+dy
                    if 0 <= pp < w and 0 <= pyp < h:
                        bell = d <= sz
                        if bell:
                            a = 1 - d/sz
                            col = Color.from_hsv(hue, 0.8, 0.2+a*0.6*pulse)
                            c.set_pixel(pp, pyp, '█' if a > 0.6 else '▒', col, z=10)
                        elif dy > 0:
                            tent = (d - sz) / (sz*0.5)
                            if tent < 1:
                                col = Color.from_hsv(hue, 0.9, 0.1+(1-tent)*0.3*pulse)
                                c.set_pixel(pp, pyp, '~' if dy % 3 == 0 else '·', col, z=9)
