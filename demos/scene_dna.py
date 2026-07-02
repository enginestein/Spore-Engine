import math
from spore_engine import *
from spore_engine.core.color import *

def scene_dna(c, hr, t, pt, dt):
    w, h = c.w, c.h
    cx, cy = w / 2, h / 2

    for y in range(h):
        ty = y / h
        col = Color.from_hsv(0.65-ty*0.1, 0.4, 0.02+ty*0.04)
        for x in range(w):
            c.set_pixel(x, y, ' ', bg=col, z=-100)

    helix_len = h * 0.8
    start_y = int(h * 0.1)
    freq = 0.2
    twist = t * 0.6
    rungs = 30

    for i in range(rungs):
        prog = i / rungs
        y = start_y + helix_len * prog
        angle = prog * 4 * math.pi + twist
        r = min(w, h) * 0.12

        x1 = int(cx + r * math.cos(angle))
        x2 = int(cx + r * math.cos(angle + math.pi))

        if 0 <= y < h:
            z1 = 0.5 + 0.5 * math.cos(angle)
            z2 = 0.5 + 0.5 * math.cos(angle + math.pi)

            col1 = Color.from_hsv((prog + t*0.01) % 1.0, 0.8, 0.6+0.4*z1)
            col2 = Color.from_hsv((prog + 0.5 + t*0.01) % 1.0, 0.8, 0.6+0.4*z2)

            if 0 <= x1 < w:
                c.set_pixel(x1, int(y), '●' if z1 > 0.5 else '○', col1, z=10)
            if 0 <= x2 < w:
                c.set_pixel(x2, int(y), '●' if z2 > 0.5 else '○', col2, z=10)

            if z1 > 0.3 and z2 > 0.3:
                for dx in range(min(x1, x2)+1, max(x1, x2)):
                    if 0 <= dx < w:
                        t_ = (dx - min(x1,x2)) / max(1, abs(x2-x1))
                        col_r = col1.lerp(col2, t_)
                        c.set_pixel(dx, int(y), '░' if i % 2 == 0 else '▒', col_r, z=8)

            if z1 > 0.15:
                for dy in range(-1, 2):
                    if 0 <= x1 < w and 0 <= int(y)+dy < h and dy != 0:
                        c.set_pixel(x1, int(y)+dy, '·', col1.mul(0.3), z=7)
            if z2 > 0.15:
                for dy in range(-1, 2):
                    if 0 <= x2 < w and 0 <= int(y)+dy < h and dy != 0:
                        c.set_pixel(x2, int(y)+dy, '·', col2.mul(0.3), z=7)
