import math
from spore_engine.core.color import Color, WHITE, YELLOW, ORANGE, DIM
from spore_engine.core.canvas import Canvas
from spore_engine.fx.lighting import Light, LightManager, cast_ray_dda, render_shadows

_LS = None

def scene_shadows(c, hr, t, pt, dt):
    global _LS
    if _LS is None:
        w, h = 80, 24
        walls = set()
        for x in range(w):
            walls.add((x, 0))
            walls.add((x, h - 1))
        for y in range(h):
            walls.add((0, y))
            walls.add((w - 1, y))
        for cx, cy in [(15, 12), (30, 10), (45, 14), (55, 8), (65, 12)]:
            for dx in range(-2, 3):
                for dy in range(-2, 3):
                    if abs(dx) <= 1 or abs(dy) <= 1:
                        walls.add((cx + dx, cy + dy))
        _LS = {
            'walls': walls,
            'w': w, 'h': h,
            'time': 0.0,
            'light_x': 20.0, 'light_y': 12.0,
        }

    s = _LS
    s['time'] += dt

    lx = 20 + 25 * (0.5 + 0.5 * math.sin(s['time'] * 0.3))
    ly = 12 + 5 * (0.5 + 0.5 * math.sin(s['time'] * 0.5 + 1))

    def solid(tx, ty):
        return (tx, ty) in s['walls']

    c.clear()
    for y in range(s['h']):
        ty = y / s['h']
        for x in range(s['w']):
            n = (math.sin(x*0.05+t*0.1)+math.cos(y*0.04+t*0.08))*0.5+0.5
            c.set_pixel(x, y, ' ', bg=Color(int(3+n*4), int(2+n*3), int(8+n*12)), z=-10)

    radius = 18 + 4 * math.sin(s['time'] * 0.2)
    render_shadows(c, lx, ly, radius, solid, z=10,
                  wall_color=Color(100, 100, 130),
                  bg_color=Color(8, 6, 18))

    for wx, wy in s['walls']:
        if 0 <= wx < s['w'] and 0 <= wy < s['h']:
            dx = wx - lx
            dy = wy - ly
            dist = math.hypot(dx, dy)
            if dist < radius:
                b = 0.5 + 0.5 * (1 - dist / radius)
                col = Color(int(80 * b), int(80 * b), int(110 * b))
                c.set_pixel(wx, wy, '#', col, z=15)

    c.set_pixel(round(lx), round(ly), '@', YELLOW, z=20)
    gl = 6
    for dx in range(-gl, gl + 1):
        for dy in range(-gl, gl + 1):
            d = math.hypot(dx, dy)
            if d <= gl:
                cx, cy = round(lx) + dx, round(ly) + dy
                if 0 <= cx < s['w'] and 0 <= cy < s['h']:
                    alpha = 1 - d / gl
                    col = Color(255, 255, 200).mul(alpha * 0.3)
                    existing = c.get_pixel(cx, cy)
                    if existing and existing.bg:
                        bg = existing.bg
                    else:
                        bg = Color(8, 6, 18)
                    c.set_pixel(cx, cy, ' ', bg=col, z=5)

    c.draw_text(2, 0, "2D Raycasting + Shadows", WHITE, z=30)
    c.draw_text(2, 1, f"Light moves in circle | {int(radius)}px radius", DIM, z=30)
    c.draw_text(2, c.h - 1, "FPS-style shadow mapping from point light", DIM, z=30)
