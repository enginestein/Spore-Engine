import math, random
from spore_engine import *
from spore_engine.core.color import *

_LT = None

def scene_lightning(c, hr, t, pt, dt):
    global _LT
    w, h = c.w, c.h

    if _LT is None:
        _LT = {'strikes': [], 'next_strike': 0.5, 'flash': 0.0}

    s = _LT
    s['flash'] = max(0, s['flash'] - dt * 3)

    s['next_strike'] -= dt
    if s['next_strike'] <= 0:
        s['next_strike'] = random.uniform(1.0, 3.5)
        sx = random.randint(w//4, 3*w//4)
        branches = []
        segs = [(sx, 0)]
        cx, cy = sx, 0
        while cy < h * 0.6:
            cx += random.randint(-20, 20)
            cy += random.randint(3, 8)
            segs.append((cx, cy))
            if random.random() < 0.3:
                bx, by = cx, cy
                for _ in range(random.randint(3, 6)):
                    bx += random.randint(-15, 15)
                    by += random.randint(2, 5)
                    branches.append(((cx, cy), (bx, by)))
            if random.random() < 0.2 and len(segs) > 4:
                bx2, by2 = cx, cy
                for _ in range(random.randint(2, 4)):
                    bx2 += random.randint(-10, 10)
                    by2 += random.randint(2, 5)
                    branches.append(((cx, cy), (bx2, by2)))
        s['strikes'] = [segs, branches, 1.0]
        s['flash'] = 0.8

    for y in range(h):
        ty = y / h
        col = Color(int(3+ty*8), int(3+ty*6), int(10+ty*15))
        for x in range(w):
            c.set_pixel(x, y, ' ', bg=col, z=-100)

    if s['flash'] > 0.01:
        for y in range(h):
            for x in range(w):
                c.set_pixel(x, y, ' ', bg=Color(200, 200, 255).mul(s['flash']*0.3), z=1)

    for y in range(h):
        for x in range(w):
            n = (math.sin(x*0.03+t*0.5)+math.cos(y*0.04+t*0.3))*0.5+0.5
            if n > 0.85:
                c.set_pixel(x, y, '·', Color(100, 100, 120).mul(0.3+0.2*(n-0.85)/0.15), z=2)

    strikes = s['strikes']
    if strikes and strikes[2] > 0:
        segs, branches, life = strikes
        life -= dt * 2
        strikes[2] = life
        if life > 0:
            for i in range(len(segs)-1):
                x1, y1 = segs[i]
                x2, y2 = segs[i+1]
                alpha = life
                c.draw_line(x1, y1, x2, y2, '█', Color(200, 200, 255).mul(alpha), z=20)
                c.draw_line(x1-1, y1, x2-1, y2, ' ', bg=Color(150, 150, 255).mul(alpha*0.3), z=19)
                c.draw_line(x1+1, y1, x2+1, y2, ' ', bg=Color(150, 150, 255).mul(alpha*0.3), z=19)

            for (ax, ay), (bx, by) in branches:
                c.draw_line(ax, ay, bx, by, '▓', Color(180, 180, 255).mul(alpha*0.7), z=18)
        else:
            s['strikes'] = []
