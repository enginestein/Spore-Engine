import math
from spore_engine import *
from spore_engine.core.color import *

def scene_stained_glass(c, hr, t, pt, dt):
    w, h = c.w, c.h
    cx, cy = w // 2, h // 2

    for y in range(h):
        col = Color(int(4+y*20//h), int(3+y*12//h), int(6+y*30//h))
        for x in range(w):
            c.set_pixel(x, y, ' ', bg=col, z=-100)

    r = min(w, h) * 0.48
    r2 = r * r
    for y in range(h):
        dy = y - cy
        dy2 = dy * dy
        for x in range(w):
            dx = x - cx
            d2 = dx*dx + dy2
            if d2 > r2 * 1.15:
                continue
            d = math.sqrt(d2)
            a = math.atan2(dy, dx)
            if a < 0:
                a += 2 * math.pi
            segs = 12
            seg_i = int(a / (2 * math.pi / segs))
            ring = int(d / (r / 8)) if d < r else 8

            hue = (seg_i / segs + ring * 0.04 + t * 0.008) % 1.0
            sat = 0.5 + 0.4 * (1 - ring / 9.0)
            bright = 0.15 + 0.7 * (1 - d / (r * 1.15))

            lead = abs((a + math.pi/12) % (2*math.pi/segs) - math.pi/segs) < 0.06
            lead = lead or abs(d - int(d/r*8+0.5)*r/8) < 1.0
            lead = lead or abs(d - r) < 1.5

            if lead:
                c.set_pixel(x, y, '▓', Color(8, 6, 12), z=5)
            elif d < r * 0.93:
                ch = ' ' if bright < 0.2 else ('░' if bright < 0.35 else ('▒' if bright < 0.5 else ('▓' if bright < 0.65 else '█')))
                c.set_pixel(x, y, ch, Color.from_hsv(hue, sat, bright), z=3)

    for i in range(segs * 2):
        a = i * math.pi / segs + t * 0.15
        for r2_val in range(int(r*0.65), int(r*0.95)):
            px = int(cx + r2_val * math.cos(a + math.sin(r2_val*0.05+t*0.3)*0.4))
            py = int(cy + r2_val * math.sin(a + math.cos(r2_val*0.05+t*0.3)*0.4))
            if 0 <= px < w and 0 <= py < h:
                hue = (i/(segs*2) + t*0.015) % 1.0
                a2 = 1 - (r2_val - r*0.65)/(r*0.3)
                c.set_pixel(px, py, '·', Color.from_hsv(hue, 0.9, 0.5*a2), z=10)

    if 0 <= cy < h and 0 <= cx < w:
        c.set_pixel(cx, cy, '●', Color(255, 230, 200), z=15)
        for dx, dy in [(-1,0),(1,0),(0,-1),(0,1),(-1,-1),(-1,1),(1,-1),(1,1)]:
            if 0 <= cx+dx < w and 0 <= cy+dy < h:
                c.set_pixel(cx+dx, cy+dy, '·', Color(255, 230, 200).mul(0.5), z=14)

    for y in range(h):
        for x in range(w):
            d = math.hypot(x-cx, y-cy)
            if d > r:
                n = (math.sin(x*0.05+t*0.2)*math.cos(y*0.03+t*0.15))*0.5+0.5
                if n > 0.8:
                    c.set_pixel(x, y, '·', Color(60, 40, 80).mul(n*0.15), z=1)
