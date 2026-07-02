import math
from spore_engine import *
from spore_engine.core.color import *

def scene_solar_flare(c, hr, t, pt, dt):
    w, h = c.w, c.h
    cx, cy = w / 2, h / 2

    for y in range(h):
        for x in range(w):
            c.set_pixel(x, y, ' ', bg=Color(0, 0, 3), z=-100)

    sun_r = min(w, h) * 0.15
    for dy in range(-int(sun_r*1.3), int(sun_r*1.3)+1):
        for dx in range(-int(sun_r*1.3), int(sun_r*1.3)+1):
            d = math.hypot(dx, dy)
            px, py = int(cx+dx), int(cy+dy)
            if 0 <= px < w and 0 <= py < h:
                if d <= sun_r:
                    t_ = d / sun_r
                    col = Color.from_hsv(0.08+0.04*d/sun_r, 0.9, 1-t_*0.3)
                    c.set_pixel(px, py, '█', col, z=10)
                elif d <= sun_r * 1.2:
                    t_ = (d - sun_r) / (sun_r * 0.2)
                    a = 1 - t_
                    col = Color.from_hsv(0.10, 0.8, 0.6*a)
                    c.set_pixel(px, py, '▓', col, z=9)

    for i in range(16):
        a = t * 0.2 + i * math.pi / 8
        for r in range(int(sun_r), int(sun_r*2.5)):
            d = r - sun_r
            flicker = 0.5 + 0.5 * math.sin(t * 3 + i * 2 + r * 0.3)
            if flicker < 0.6: continue
            px = int(cx + r * math.cos(a))
            py = int(cy + r * math.sin(a))
            if 0 <= px < w and 0 <= py < h:
                spread = d / (sun_r * 1.5)
                if spread < 1:
                    col = Color.from_hsv(0.07+spread*0.05, 0.9, 0.3+(1-spread)*0.5*flicker)
                    c.set_pixel(px, py, '░' if spread > 0.6 else '▒', col, z=8)
                    if spread < 0.4:
                        for dx, dy in [(-1,0),(1,0),(0,-1),(0,1)]:
                            if 0 <= px+dx < w and 0 <= py+dy < h:
                                c.set_pixel(px+dx, py+dy, '·', col.mul(0.3), z=7)

    for i in range(6):
        a = -t * 0.3 + i * math.pi / 3
        r_start = sun_r * 0.5
        for r in range(int(r_start), int(sun_r*3)):
            px = int(cx + r * math.cos(a + math.sin(t*0.5+i)*0.3))
            py = int(cy + r * math.sin(a + math.cos(t*0.5+i)*0.3))
            if 0 <= px < w and 0 <= py < h:
                spread = (r - r_start) / (sun_r * 2.5)
                if spread < 1:
                    a2 = 1 - spread
                    c.set_pixel(px, py, '·', Color.from_hsv(0.05, 0.9, 0.2*a2), z=6)
