import math
from spore_engine import *
from spore_engine.core.color import *
from spore_engine.render3d.sdf import *
from spore_engine.core.geom import Vec3


# Precomputed state — avoids recomputing ring/star trig inside SDF callbacks (huge perf win)
_cosmic_state = {
    'rings': [],  # list of (x, y, z, major_r) per ring
    'stars': [],  # list of (x, y, z) per star
    'cz': 0,
}


def scene_cosmic_tunnel(c: Canvas, hr: HiResCanvas, t: float, pt, dt: float):
    """Cosmic Tunnel — Psychedelic ray marched tunnel through space with warp drive effect"""
    global _cosmic_state
    cz = t * 0.6  # tunnel progress

    # Precompute ring/star positions ONCE per frame (not inside SDF callbacks!)
    rings = []
    for i in range(8):
        z_pos = cz + 1 + i * 1.5 + math.sin(t * 0.3 + i * 1.1) * 0.2
        rings.append((
            0.8 * math.cos(i * 1.2 + t * 0.5),
            0.8 * math.sin(i * 1.2 + t * 0.5),
            z_pos,
            0.75,
        ))

    stars = []
    for i in range(12):
        z_pos = cz + 0.5 + i * 1.2 + math.sin(t * 0.4 + i * 1.7) * 0.3
        stars.append((
            1.8 * math.cos(i * 3.7 + t * 1.2),
            1.8 * math.sin(i * 3.7 + t * 1.2),
            z_pos,
        ))

    _cosmic_state['rings'] = rings
    _cosmic_state['stars'] = stars
    _cosmic_state['cz'] = cz
    s = _cosmic_state

    _g_scene = SDFScene()
    _g_scene.ambient = Color(5, 3, 20)
    _g_scene.max_steps = 48
    _g_scene.max_dist = 35
    _g_scene.bg_color = Color(2, 1, 10)

    # SDF functions reference precomputed arrays — no trig inside callbacks
    def tunnel(p):
        radius = math.hypot(p.x, p.z)
        d = radius - 2.5
        rib = abs(math.sin(p.z * 4.0 - s['cz'] * 2.0)) * 0.12
        d = op_union(d, radius - (2.5 - rib))
        d += math.sin(p.z * 6.0 + p.x * 2.0 + s['cz'] * 3.0) * 0.08
        return d

    def end_glow(p):
        return sd_sphere(p, Vec3(0, 0, s['cz'] + 18), 1.8)

    def moving_rings(p):
        d = 1e9
        for rx, ry, rz, mr in s['rings']:
            d = op_union(d, sd_torus(p, Vec3(rx, ry, rz), mr, 0.04))
        return d

    def moving_stars(p):
        d = 1e9
        for sx, sy, sz in s['stars']:
            d = op_union(d, sd_sphere(p, Vec3(sx, sy, sz), 0.04))
        return d

    _g_scene.add(tunnel, Color(60, 40, 110), reflectivity=0.2)
    _g_scene.add(end_glow, Color(255, 220, 150), emissive=0.9)
    _g_scene.add(moving_rings, Color(100, 200, 255), reflectivity=0.3, emissive=0.15)
    _g_scene.add(moving_stars, Color(255, 255, 220), emissive=0.7)

    _g_scene.add_light(Vec3(2, 2, s['cz'] + 3), Color(255, 200, 180), 1.5)
    _g_scene.add_light(Vec3(-2, -2, s['cz'] + 8), Color(180, 200, 255), 1.2)
    _g_scene.add_light(Vec3(0, 0, s['cz'] + 20), Color(255, 220, 200), 2.0)

    camera = Vec3(0.3 * math.sin(t * 0.5), 0.3 * math.cos(t * 0.7), s['cz'])
    target = Vec3(0, 0, s['cz'] + 3)
    _g_scene.render(c, camera, target, 70)

    _apply_glow(c)

    hue = (t * 0.03) % 1.0
    c.draw_text(2, 0, '✦ Cosmic Tunnel ✦', Color.from_hsv(hue, 0.7, 1.0), z=100)
    c.draw_text(2, c.h - 1, 'warp drive | tunnel vision | star stream | neon rings', DIM, z=100)


def _apply_glow(canvas: Canvas, intensity: float = 0.10):
    """Simple glow/bloom effect"""
    w, h = canvas.w, canvas.h
    buf = [[None] * w for _ in range(h)]
    for y in range(h):
        for x in range(w):
            cell = canvas.buffer[y][x]
            if cell.fg:
                buf[y][x] = (cell.fg.r, cell.fg.g, cell.fg.b)
    blurred = [[None] * w for _ in range(h)]
    for y in range(1, h - 1):
        for x in range(1, w - 1):
            r, g, b, n = 0, 0, 0, 0
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    px = buf[y + dy][x + dx]
                    if px:
                        r += px[0]; g += px[1]; b += px[2]; n += 1
            if n > 0:
                blurred[y][x] = (r // n, g // n, b // n)
    for y in range(h):
        for x in range(w):
            cell = canvas.buffer[y][x]
            bl = blurred[y][x]
            if bl and cell.fg:
                cell.fg = Color(
                    min(255, int(cell.fg.r + bl[0] * intensity)),
                    min(255, int(cell.fg.g + bl[1] * intensity)),
                    min(255, int(cell.fg.b + bl[2] * intensity)),
                )

