import math
from spore_engine import *
from spore_engine.core.color import *

def scene_astral_cathedral(c, hr, t, pt, dt):
    w, h = c.w, c.h

    for y in range(h):
        ty = y / h
        col = Color(int(3+ty*12), int(2+ty*6), int(5+ty*25))
        for x in range(w):
            c.set_pixel(x, y, ' ', bg=col, z=-100)

    arch_centers = [w//4, w//2, 3*w//4]
    arch_widths = [w//6, w//5, w//6]
    arch_heights = [h//3, h//2 + h//6, h//3]

    for idx in range(3):
        cx_a = arch_centers[idx]
        aw = arch_widths[idx]
        ah = arch_heights[idx]
        col_pillar = Color(25+idx*5, 18+idx*3, 35+idx*10)
        col_pillar_dark = Color(12+idx*3, 8+idx*2, 18+idx*5)

        pillar_l = cx_a - aw
        pillar_r = cx_a + aw
        floor_y = h - 1
        arch_top = h - ah

        for y in range(arch_top, floor_y+1):
            ty_p = (y - arch_top) / max(1, floor_y - arch_top)
            for x in range(w):
                dx_l = abs(x - pillar_l)
                dx_r = abs(x - pillar_r)
                is_arch = False
                if x >= pillar_l - 2 and x < pillar_l:
                    c.set_pixel(x, y, '║', col_pillar, z=5)
                    is_arch = True
                elif x > pillar_r and x <= pillar_r + 2:
                    c.set_pixel(x, y, '║', col_pillar, z=5)
                    is_arch = True
                elif y < floor_y - 5 and (x < pillar_l - 2 or x > pillar_r + 2):
                    continue

            if y == floor_y:
                for x in range(w):
                    c.set_pixel(x, y, '═', col_pillar_dark, z=5)

        for y in range(arch_top - int(h*0.1), floor_y+1):
            for x in range(pillar_l, pillar_r+1):
                d = 0
                if y < arch_top:
                    dy_a = arch_top - y
                    curve = (1 - (dy_a / (h*0.15))**2) * aw
                    if abs(x - cx_a) > curve:
                        continue
                if y < floor_y - 1:
                    c.set_pixel(x, y, ' ', bg=Color.from_hsv(0.7+(y/h)*0.1, 0.4, 0.02+(y/h)*0.06), z=3)

    center_arch = arch_centers[1]
    cw = arch_widths[1]
    ch_ = arch_heights[1]
    apse_top = h - ch_
    apse_cy = center_arch
    apse_r = cw

    for y in range(h):
        for x in range(w):
            d = math.hypot(x - apse_cy, y - (apse_top + apse_r*0.3))
            if d < apse_r * 0.8:
                a = math.atan2(y - (apse_top + apse_r*0.3), x - apse_cy)
                hue = (a/(2*math.pi) + t*0.01) % 1.0
                sat = 0.5 + 0.4 * (1 - d/(apse_r*0.8))
                bright = 0.1 + 0.6 * (1 - d/(apse_r*0.8))
                ch = ' ' if bright < 0.15 else ('░' if bright < 0.3 else ('▒' if bright < 0.5 else ('▓' if bright < 0.65 else '█')))
                c.set_pixel(x, y, ch, Color.from_hsv(hue, sat, bright), z=4)

    for x in range(apse_cy - int(apse_r*0.7), apse_cy + int(apse_r*0.7)+1):
        for y in range(apse_top-int(h*0.05), apse_top+1):
            if 0 <= x < w and 0 <= y < h:
                dist = abs(x - apse_cy) / (apse_r*0.7)
                col = Color.from_hsv(0.15, 0.8, 0.1+0.4*(1-dist))
                c.set_pixel(x, y, '═' if y == apse_top else '║', col, z=6)

    row = apse_top + apse_r * 2 // 3
    for dx_val in range(-int(apse_r*0.5), int(apse_r*0.5)+1, 5):
        px = apse_cy + dx_val
        py = int(row)
        if 0 <= px < w and 0 <= py < h:
            c.set_pixel(px, py, '·', Color(200, 180, 150).mul(0.3), z=7)

    floor_y = h - 1
    for x in range(w):
        if 0 <= floor_y < h:
            c.set_pixel(x, floor_y, '═', Color(15, 12, 20), z=8)

    cloud_cols = [(60, 40, 80), (80, 50, 100), (100, 60, 120)]
    for y in range(int(h*0.12)):
        for x in range(w):
            n = math.sin(x*0.02+t*0.3+y*0.1)*0.5+0.5
            if n > 0.65:
                col = Color(cloud_cols[y%3][0], cloud_cols[y%3][1], cloud_cols[y%3][2]).mul((n-0.65)/0.35*0.3)
                c.set_pixel(x, y, '·' if n < 0.8 else '░', col, z=2)
