import math
from spore_engine import *
from spore_engine.core.color import *
from spore_engine.gen.splines import render_bezier, render_catmull_rom

_SD = None

def scene_spline_demo(c, hr, t, pt, dt):
    global _SD
    w, h = c.w, c.h
    if _SD is None:
        _SD = {'time': 0}

    _SD['time'] += dt

    for y in range(h):
        for x in range(w):
            col = Color(int(8 + y / h * 10), int(4 + y / h * 6), int(12 + y / h * 8))
            c.set_pixel(x, y, ' ', bg=col, z=-100)

    cx, cy = w // 4, h // 2 - 2
    phase = _SD['time'] * 0.3

    quad_pts = [
        (cx - 8, cy + 6),
        (cx + int(10 * math.sin(phase)), cy - 6),
        (cx + 8, cy + 4),
    ]
    render_bezier(c, quad_pts, steps=25, fg=Color.from_hsv(0.6, 0.8, 0.9),
                  z=10, show_control=True, show_decasteljau=False,
                  t_progress=-1)
    c.draw_text(cx - 6, cy + 8, "Quadratic Bezier", DIM, z=100)

    cx2 = w * 3 // 4
    cubic_pts = [
        (cx2 - 10, cy + 6),
        (cx2 - 5, cy - 6 - int(4 * math.sin(phase * 0.7))),
        (cx2 + 5, cy - 4 + int(4 * math.cos(phase * 0.9))),
        (cx2 + 10, cy + 4),
    ]
    t_prog = (math.sin(phase * 0.5) * 0.5 + 0.5) if _SD['time'] > 1 else -1
    render_bezier(c, cubic_pts, steps=30, fg=Color.from_hsv(0.85, 0.8, 0.9),
                  z=10, show_control=True, show_decasteljau=True,
                  t_progress=t_prog)
    c.draw_text(cx2 - 7, cy + 8, "Cubic Bezier", DIM, z=100)

    cy2 = h - 6
    cr_pts = []
    for i in range(5):
        angle = i / 5 * math.pi * 2 + phase * 0.2
        r = 8 + 3 * math.sin(i * 2.3 + phase * 0.5)
        cr_pts.append((w // 2 + r * math.cos(angle), cy2 + r * math.sin(angle) * 0.5))
    render_catmull_rom(c, cr_pts, steps=20, fg=Color.from_hsv(0.4, 0.8, 0.9),
                       z=10, closed=True, show_control=True)
    c.draw_text(w // 2 - 7, cy2 + 9, "Catmull-Rom (closed)", DIM, z=100)
