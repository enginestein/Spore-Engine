import math
from spore_engine import *
from spore_engine.core.color import *
from spore_engine.anim.timeline import Timeline

_TL = None



def scene_timeline(c, hr, t, pt, dt):
    global _TL
    w, h = c.w, c.h

    if _TL is None:
        tl = Timeline(duration=8.0, loop=True, yoyo=False)
        tl.add_keyframe('x', 0, 2).add_keyframe('x', 4, w - 3, 'quad_out').add_keyframe('x', 8, 2, 'quad_in')
        tl.add_keyframe('y', 0, 3).add_keyframe('y', 4, h - 4, 'bounce_out').add_keyframe('y', 8, 3, 'quad_in')
        tl.add_keyframe('hue', 0, 0.0).add_keyframe('hue', 4, 0.7, 'sine_in_out').add_keyframe('hue', 8, 0.0, 'sine_in_out')
        tl.add_keyframe('scale', 0, 1.0).add_keyframe('scale', 2, 2.5, 'elastic_out').add_keyframe('scale', 4, 1.0, 'sine_in_out').add_keyframe('scale', 6, 0.5).add_keyframe('scale', 8, 1.0, 'bounce_out')
        tl.add_keyframe('orbits', 0, 3).add_keyframe('orbits', 4, 8, 'cubic_out').add_keyframe('orbits', 8, 3, 'cubic_in')
        tl2 = Timeline(duration=4.0, loop=True, yoyo=True)
        tl2.add_keyframe('r', 0, 0).add_keyframe('r', 2, 1.0, 'sine_in_out').add_keyframe('r', 4, 0, 'sine_in_out')
        tl2.add_keyframe('g', 0, 0).add_keyframe('g', 2, 1.0, 'expo_out').add_keyframe('g', 4, 0)
        _TL = {'tl': tl, 'tl2': tl2}

    s = _TL
    tl = s['tl']
    tl2 = s['tl2']

    tl.update(dt)
    tl2.update(dt)

    for y in range(h):
        for x in range(w):
            col = Color(int(6 + y * 8 // h), int(3 + y * 5 // h), int(12 + y * 12 // h))
            c.set_pixel(x, y, ' ', bg=col, z=-100)

    corners = [
        (1, 1, Color.from_hsv(0.6, 0.8, 0.9)),
        (w - 2, 1, Color.from_hsv(0.8, 0.8, 0.9)),
        (1, h - 2, Color.from_hsv(0.3, 0.8, 0.8)),
        (w - 2, h - 2, Color.from_hsv(0.0, 0.8, 0.9)),
    ]
    r_phase = tl2.get_value('r')
    g_phase = tl2.get_value('g')
    for cx, cy, col in corners:
        radius = 2 + int(r_phase * 4)
        for i in range(8):
            a = i / 8 * math.pi * 2 + tl.time * 0.5
            px = int(cx + radius * math.cos(a))
            py = int(cy + radius * math.sin(a) * 0.5)
            if 0 <= px < w and 0 <= py < h:
                c.set_pixel(px, py, '♦', col.mul(0.5 + 0.5 * g_phase), z=10)

    px = int(tl.get_value('x'))
    py = int(tl.get_value('y'))
    hue = tl.get_value('hue')
    scale = tl.get_value('scale')
    num_orbits = int(tl.get_value('orbits'))

    for i in range(num_orbits):
        a = i / num_orbits * math.pi * 2 + tl.time * 1.5
        r = 2 + scale * 3
        ox = int(px + r * math.cos(a) * 0.6)
        oy = int(py + r * math.sin(a) * 0.3)
        if 0 <= ox < w and 0 <= oy < h:
            orbit_hue = (i / num_orbits + tl.time * 0.05) % 1.0
            c.set_pixel(ox, oy, '*', Color.from_hsv(orbit_hue, 0.9, 0.9), z=10)

    if 0 <= px < w and 0 <= py < h:
        c.set_pixel(px, py, '@', Color.from_hsv(hue, 0.9, 1.0), z=15)
        if scale > 1:
            for i in range(4):
                a = math.pi * i / 2 + tl.time
                sx = int(px + scale * 2 * math.cos(a))
                sy = int(py + scale * 2 * math.sin(a) * 0.5)
                if 0 <= sx < w and 0 <= sy < h:
                    c.set_pixel(sx, sy, '·', Color.from_hsv(hue, 0.7, 0.6), z=10)

    bg_col = Color(int(20 * r_phase), 0, int(20 * g_phase))
    for x in range(w):
        c.set_pixel(x, 0, ' ', bg=bg_col, z=0)
        c.set_pixel(x, h - 1, ' ', bg=bg_col, z=0)

    c.draw_text(2, 0, "Animation Timeline", WHITE, z=100)
    c.draw_text(2, h - 1, f"t={tl.time:.1f}s | {tl}", DIM, z=100)
