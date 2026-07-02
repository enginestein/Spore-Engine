import math, random
from spore_engine import *
from spore_engine.core.color import *

_PR = None

def scene_phoenix(c, hr, t, pt, dt):
    global _PR
    w, h = c.w, c.h
    cx, cy = w // 2, h // 2

    if _PR is None:
        flames = []
        for _ in range(60):
            flames.append({
                'x': random.uniform(0, w), 'y': random.uniform(0, h),
                'vx': random.uniform(-2, 2), 'vy': random.uniform(-2, 2),
                'life': random.uniform(0.5, 3), 'age': random.uniform(0, 3),
                'size': random.uniform(0.3, 1.5),
            })
        _PR = {'flames': flames}

    s = _PR

    for y in range(h):
        col = Color(int(5+y*8//h*8), int(2+y*4//h*4), int(4+y*6//h*8))
        for x in range(w):
            c.set_pixel(x, y, ' ', bg=col, z=-100)

    body_pts = []
    for i in range(20):
        prog = i / 19
        angle = -math.pi/2 + math.sin(prog * math.pi * 3 + t*0.3) * 0.3
        rx = 5 + prog * 4
        ry = 2 + prog * 6
        px = int(cx + rx * math.cos(angle + math.pi/2))
        py = int(cy + ry * math.sin(angle - math.pi/4 + prog*2))
        body_pts.append((px, py))

    left_wing = []
    right_wing = []
    spread = 0.6 + 0.4 * math.sin(t * 0.5)
    for i in range(20):
        prog = i / 19
        wing_h = 15 * spread * (1 - prog*0.2)
        lx = cx - int(prog * 20)
        rx = cx + int(prog * 20)
        ly = cy - 2 + int(math.sin(prog*math.pi)*6)
        ry = cy - 2 + int(math.sin(prog*math.pi)*6)
        left_wing.append((lx, ly))
        right_wing.append((rx, ry))

    tail_pts = []
    for i in range(15):
        prog = i / 14
        px = cx + int(math.sin(prog*4 + t*0.5) * 5 * prog)
        py = cy + 5 + int(prog * 15)
        tail_pts.append((px, py))

    wing_feathers_l = []
    wing_feathers_r = []
    for i in range(8):
        prog = i / 7
        tip_x = -int(22 * spread * (0.5 + prog*0.5))
        len_ = 6 + prog * 8
        wing_feathers_l.append((cx + tip_x, cy - 4 + int(prog*6), len_, 1))
        wing_feathers_r.append((cx - tip_x, cy - 4 + int(prog*6), len_, -1))

    for y in range(h):
        for x in range(w):
            is_phoenix = False
            hue = 0.05
            bright = 0.0

            for i in range(len(body_pts)-1):
                x1, y1 = body_pts[i]; x2, y2 = body_pts[i+1]
                dist = abs((x2-x1)*(y1-y) - (x1-x)*(y2-y1)) / max(1, math.hypot(x2-x1, y2-y1))
                if dist < 2.5:
                    is_phoenix = True
                    bright = 0.7
                    hue = 0.05

            for i in range(len(left_wing)-1):
                x1, y1 = left_wing[i]; x2, y2 = left_wing[i+1]
                dist = abs((x2-x1)*(y1-y) - (x1-x)*(y2-y1)) / max(1, math.hypot(x2-x1, y2-y1))
                if dist < 4:
                    is_phoenix = True
                    bright = 0.6 * (1 - i/20)
                    hue = 0.07 + i*0.005

            for i in range(len(right_wing)-1):
                x1, y1 = right_wing[i]; x2, y2 = right_wing[i+1]
                dist = abs((x2-x1)*(y1-y) - (x1-x)*(y2-y1)) / max(1, math.hypot(x2-x1, y2-y1))
                if dist < 4:
                    is_phoenix = True
                    bright = 0.6 * (1 - i/20)
                    hue = 0.07 + i*0.005

            for i in range(len(tail_pts)-1):
                x1, y1 = tail_pts[i]; x2, y2 = tail_pts[i+1]
                dist = abs((x2-x1)*(y1-y) - (x1-x)*(y2-y1)) / max(1, math.hypot(x2-x1, y2-y1))
                if dist < 3:
                    is_phoenix = True
                    bright = 0.5 * (1 - i/15)
                    hue = 0.03 + i*0.01

            for fx, fy, fl, side in wing_feathers_l + wing_feathers_r:
                d = abs(math.hypot(x-fx, y-fy) - fl)
                if d < 2:
                    is_phoenix = True
                    bright = 0.5 * (1 - d/2)
                    hue = 0.08

            if is_phoenix:
                pulse = 0.8 + 0.2 * math.sin(t*2 + x*0.5 + y*0.3)
                ch = '░' if bright < 0.2 else ('▒' if bright < 0.35 else ('▓' if bright < 0.55 else '█'))
                c.set_pixel(x, y, ch, Color.from_hsv(hue % 1.0, 0.9, bright*pulse), z=8)

            d_from_body = 100
            for px_v, py_v in body_pts:
                d = math.hypot(x-px_v, y-py_v)
                d_from_body = min(d_from_body, d)
            if d_from_body < 8 and not is_phoenix:
                glow = 1 - d_from_body/8
                c.set_pixel(x, y, ' ', bg=Color.from_hsv(0.07, 0.8, glow*0.1), z=4)

    for f in s['flames']:
        f['x'] += f['vx'] * dt * 5
        f['y'] += f['vy'] * dt * 5
        f['age'] += dt
        if f['age'] >= f['life']:
            f['x'] = cx + random.uniform(-15, 15)
            f['y'] = cy + random.uniform(-10, 10)
            f['vx'] = random.uniform(-1, 1)
            f['vy'] = random.uniform(-2, -0.5)
            f['life'] = random.uniform(1, 3)
            f['age'] = 0
        px, py = int(f['x']), int(f['y'])
        if 0 <= px < w and 0 <= py < h:
            life = 1 - f['age']/f['life']
            col = Color.from_hsv(0.05+life*0.05, 0.9, life*0.6)
            c.set_pixel(px, py, '·', col, z=12)

    if 0 <= cx < w and 0 <= cy < h:
        c.set_pixel(cx, cy, '●', Color(255, 200, 100), z=15)
        c.set_pixel(cx, cy-1, '·', Color(255, 200, 100).mul(0.5), z=14)
        c.set_pixel(cx-1, cy, '·', Color(255, 200, 100).mul(0.5), z=14)
        c.set_pixel(cx+1, cy, '·', Color(255, 200, 100).mul(0.5), z=14)
