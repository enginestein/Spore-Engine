import math, random
from spore_engine import *
from spore_engine.core.color import *

_GH = None

def scene_golden_city(c, hr, t, pt, dt):
    global _GH
    w, h = c.w, c.h

    if _GH is None:
        buildings = []
        bx = 0
        while bx < w:
            bw = random.randint(4, 12)
            bh = random.randint(5, min(h-4, h//2 + random.randint(0, h//3)))
            buildings.append({'x': bx, 'w': bw, 'h': bh, 'windows': []})
            for wy in range(h-bh+2, h-2, random.randint(2, 4)):
                for wx in range(bx+2, bx+bw-1, random.randint(2, 4)):
                    if random.random() < 0.6:
                        buildings[-1]['windows'].append((wx, wy, random.choice([0.3, 0.6, 0.9])))
            bx += bw + random.randint(1, 3)
        birds = []
        for _ in range(12):
            birds.append({
                'x': random.uniform(0, w), 'y': random.uniform(h*0.05, h*0.15),
                'vx': random.uniform(0.5, 2.0), 'vy': random.uniform(-0.1, 0.1),
                'phase': random.uniform(0, 2*math.pi),
            })
        _GH = {'buildings': buildings, 'birds': birds}

    s = _GH

    for y in range(h):
        ty = y / h
        sun_angle = (ty - 0.3) * 3
        if ty < 0.5:
            hue = 0.08 - ty*0.1
            sat = 0.3 + ty*0.5
            bright = 0.15 + 0.6 * (1 - abs(ty-0.3)*2)
        else:
            t2 = (ty - 0.5) * 2
            hue = 0.03 + t2*0.05
            sat = 0.5 + t2*0.2
            bright = 0.35 * (1 - t2*0.6)
        col = Color.from_hsv(max(0, hue), min(1, sat), max(0.02, bright))
        for x in range(w):
            c.set_pixel(x, y, ' ', bg=col, z=-100)

    sun_x = int(w * 0.7)
    sun_y = int(h * 0.35)
    for dy in range(-10, 11):
        for dx in range(-10, 11):
            d = math.hypot(dx, dy)
            if d <= 10:
                px, py = sun_x+dx, sun_y+dy
                if 0 <= px < w and 0 <= py < h:
                    a = 1 - d/10
                    col = Color.from_hsv(0.1, 0.8, 0.2+0.8*a)
                    ch = '█' if a > 0.8 else ('▓' if a > 0.5 else '░')
                    c.set_pixel(px, py, ch, col, z=2)

    for b in s['buildings']:
        bx, bw, bh = b['x'], b['w'], b['h']
        for y in range(h-bh, h):
            if y < 0:
                continue
            dist_from_edge = min(y - (h-bh), h-1 - y) / max(1, bh)
            for x in range(bx, min(bx+bw, w)):
                if x < 0 or y < 0 or x >= w or y >= h:
                    continue
                if y == h-bh:
                    c.set_pixel(x, y, '▀', Color(60, 40, 25), z=5)
                elif x == bx or x == bx+bw-1:
                    c.set_pixel(x, y, '║', Color(45, 30, 20), z=5)
                else:
                    col = Color(int(40+dist_from_edge*20), int(30+dist_from_edge*15), int(20+dist_from_edge*10))
                    c.set_pixel(x, y, '█', col, z=5)

    for b in s['buildings']:
        for wx, wy, bright_factor in b['windows']:
            if 0 <= wx < w and 0 <= wy < h:
                glow = bright_factor * (0.7 + 0.3 * math.sin(t*0.5 + wx*0.7 + wy*0.3))
                col = Color.from_hsv(0.1, 0.8, 0.3+0.7*glow)
                c.set_pixel(wx, wy, '█', col, z=8)
                if glow > 0.7:
                    for dx, dy in [(-1,0),(1,0),(0,-1),(0,1)]:
                        if 0 <= wx+dx < w and 0 <= wy+dy < h:
                            c.set_pixel(wx+dx, wy+dy, '·', col.mul(0.3), z=7)

    for x in range(w):
        for y in range(int(h*0.95), h):
            if 0 <= x < w and 0 <= y < h:
                c.set_pixel(x, y, '█', Color(20, 15, 12), z=3)

    for b in s['birds']:
        b['x'] += b['vx'] * dt * 10
        b['y'] += b['vy'] * dt * 5 + math.sin(t*0.5+b['phase'])*dt*0.5
        if b['x'] > w+5:
            b['x'] = -5
            b['y'] = random.uniform(h*0.05, h*0.15)
        px, py = int(b['x']), int(b['y'])
        wp = math.sin(t*3+b['phase'])
        if 0 <= px < w and 0 <= py < h:
            c.set_pixel(px, py, '>', Color(30, 25, 20), z=12)
            if 0 <= px-1 < w:
                c.set_pixel(px-1, py, '~' if wp > 0 else 'v', Color(30, 25, 20), z=12)
