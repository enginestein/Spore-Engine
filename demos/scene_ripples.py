import math
from spore_engine import *
from spore_engine.core.color import *

def scene_ripples(c, hr, t, pt, dt):
    w, h = c.w, c.h

    for y in range(h):
        for x in range(w):
            dx = x - w/2
            dy = y - h/2
            d = math.hypot(dx, dy) / max(w, h)

            r1 = math.sin(d * 12 - t * 2.5) * 0.5 + 0.5
            r2 = math.sin(d * 8 + t * 1.8 + 1.2) * 0.5 + 0.5
            r3 = math.sin((dx*0.08+dy*0.06)*6 + t*1.2) * 0.5 + 0.5

            val = r1 * 0.4 + r2 * 0.3 + r3 * 0.3
            val = max(0, min(1, val))

            hue = (d * 1.5 + val * 0.3 + t * 0.03) % 1.0
            sat = 0.5 + val * 0.4
            bright = 0.1 + val * 0.8

            if d > 0.7:
                bg = Color.from_hsv(0.65, 0.3, 0.03)
                c.set_pixel(x, y, ' ', bg=bg, z=-100)
            else:
                ch = ' ' if val < 0.15 else ('░' if val < 0.35 else ('▒' if val < 0.55 else ('▓' if val < 0.75 else '█')))
                c.set_pixel(x, y, ch, Color.from_hsv(hue, sat, bright), z=0)

    cx, cy = w // 2, h // 2
    for r in range(1, int(min(w, h) * 0.35), 3):
        a = r * 0.5 + t * 2
        px = int(cx + r * math.cos(a))
        py = int(cy + r * math.sin(a))
        if 0 <= px < w and 0 <= py < h:
            hue = (r*0.02 + t*0.05) % 1.0
            c.set_pixel(px, py, '○', Color.from_hsv(hue, 0.9, 0.7), z=5)
