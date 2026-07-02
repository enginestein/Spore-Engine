import math, random
from spore_engine import *
from spore_engine.core.color import *

def scene_kaleidoscope(c, hr, t, pt, dt):
    w, h = c.w, c.h
    cx, cy = w / 2, h / 2
    segments = 6 + int(math.sin(t * 0.1) * 2)
    angle_step = 2 * math.pi / segments

    for py in range(h):
        for px in range(w):
            dx = px - cx
            dy = py - cy
            dist = math.hypot(dx, dy) / max(w, h) * 2

            angle = math.atan2(dy, dx)
            folded = abs(angle % angle_step - angle_step / 2) / (angle_step / 2)
            folded = min(folded, 1.0)

            n1 = math.sin(dist * 6 - t * 0.8 + folded * 3) * 0.5
            n2 = math.cos(dist * 4 + t * 0.5 + folded * 5) * 0.5
            n3 = math.sin((dx * 0.05 + dy * 0.03) * 3 + t * 0.6) * 0.5
            val = (n1 + n2 + n3) / 3 + 0.5

            hue = (folded * 0.3 + dist * 0.4 + t * 0.03) % 1.0
            bright = 0.3 + val * 0.7
            sat = 0.6 + val * 0.4

            if dist > 0.95:
                c.set_pixel(px, py, ' ', bg=Color(2, 1, 5), z=-100)
            else:
                c.set_pixel(px, py, '█', Color.from_hsv(hue, sat, bright), z=0)

    for i in range(segments):
        a = i * angle_step + t * 0.1
        for r in range(0, int(min(w, h) * 0.47), 3):
            px = int(cx + r * math.cos(a))
            py = int(cy + r * math.sin(a))
            if 0 <= px < w and 0 <= py < h:
                c.set_pixel(px, py, '·', Color(255, 255, 255).mul(0.3 + 0.2 * math.sin(t + i)), z=5)
