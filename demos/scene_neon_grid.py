import math
from spore_engine import *
from spore_engine.core.color import *

def scene_neon_grid(c, hr, t, pt, dt):
    w, h = c.w, c.h

    for y in range(h):
        ty = y / h
        bg = Color(0, 0, 2+int(ty*10))
        for x in range(w):
            c.set_pixel(x, y, ' ', bg=bg, z=-100)

    horizon = int(h * 0.55)
    for y in range(horizon, h):
        ty = (y - horizon) / max(1, h - horizon)
        speed = 2.0 + ty * 2.0
        offset = t * speed
        vanish_x = w / 2 + math.sin(t * 0.3) * w * 0.05

        for i in range(-10, 11):
            px = vanish_x + (i * 8 + (offset * 30) % 8) * (0.3 + ty * 2.5)
            col = Color.from_hsv(0.78 + abs(i)*0.015, 0.8, 0.15 + ty * 0.5 * (1-abs(i)*0.08))
            px1, px2 = int(px - 1), int(px + 1)
            if 0 <= px1 < w:
                c.set_pixel(px1, y, '║', col, z=5)
            if 0 <= px2 < w:
                c.set_pixel(px2, y, '║', col, z=5)

        hor_pos = (offset * 50) % 20
        for bx in range(-5, w+5, 4):
            px = int(vanish_x + (bx - w/2) * (0.05 + ty * 0.8))
            if 0 <= px < w:
                c.set_pixel(px, y, '═', Color(100, 50, 180).mul(0.1+0.2*ty), z=4)

    glow_y = int(horizon * 0.7)
    for x in range(w):
        for dy in range(-3, 4):
            py = glow_y + dy
            if 0 <= py < h:
                a = 1 - abs(dy)/4
                c.set_pixel(x, py, ' ', bg=Color(100, 0, 200).mul(a*0.1), z=1)

    cx, cy = w//2, h//2
    for i in range(8):
        a = t * 0.5 + i * math.pi / 4
        r = min(w, h) * 0.2
        px, py = int(cx + r*math.cos(a)), int(cy + r*math.sin(a))
        if 0 <= px < w and 0 <= py < h:
            c.set_pixel(px, py, '●', Color(200, 100, 255), z=10)
        if 0 <= px+1 < w:
            c.set_pixel(px+1, py, '·', Color(200, 100, 255).mul(0.4), z=9)
        if 0 <= px-1 < w:
            c.set_pixel(px-1, py, '·', Color(200, 100, 255).mul(0.4), z=9)
