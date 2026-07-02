import math
from spore_engine import *
from spore_engine.core.color import *

def scene_tunnel(c, hr, t, pt, dt):
    w, h = c.w, c.h
    cx, cy = w / 2, h / 2

    for py in range(h):
        for px in range(w):
            dx = (px - cx) / (w * 0.5)
            dy = (py - cy) / (h * 0.5)
            dist = math.hypot(dx, dy)
            angle = math.atan2(dy, dx)

            tunnel_dist = dist + t * 0.5
            wall_pattern = math.sin(tunnel_dist * 8 + t) * 0.5 + 0.5
            ring_pattern = math.sin(tunnel_dist * 20 - t * 2) * 0.5 + 0.5
            angle_pattern = math.sin(angle * 8 + t * 1.5) * 0.5 + 0.5

            val = wall_pattern * 0.4 + ring_pattern * 0.3 + angle_pattern * 0.3

            if dist < 0.05:
                val = 1.0

            hue = (angle * 0.15 + dist * 0.3 + t * 0.05) % 1.0
            sat = 0.7 + 0.3 * math.sin(dist * 3 + t)
            bright = max(0, min(1, val * (1.0 - dist * 0.3)))

            if dist > 1.4:
                bg_col = Color(2, 1, 5)
                c.set_pixel(px, py, ' ', bg=bg_col, z=-100)
            else:
                ch = ' ' if val < 0.15 else ('░' if val < 0.35 else ('▒' if val < 0.55 else ('▓' if val < 0.75 else '█')))
                c.set_pixel(px, py, ch, Color.from_hsv(hue, sat, bright), z=0)
