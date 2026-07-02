import math, random
from spore_engine import *
from spore_engine.core.color import *
from spore_engine.render3d.voxel import VoxelScene

_voxel = None
_hm = None
_clouds = None
def scene_voxel_world(c: Canvas, hr: HiResCanvas, t: float, pt, dt: float):
    global _voxel, _hm, _clouds
    if _voxel is None:
        from spore_engine.gen.terrain import Terrain
        ter = Terrain(80, 80, seed=42)
        ter.generate_island(scale=0.04)
        _hm = ter.heightmap
        _voxel = VoxelScene(80, 80, _hm)
        _clouds = [(random.uniform(0, 80), random.uniform(0, 80), random.uniform(2, 6)) for _ in range(12)]

    c.clear()
    sky_hue = (0.58 + 0.08 * math.sin(t * 0.08)) % 1.0
    for y in range(c.h // 2 + 2):
        ty = y / (c.h * 0.5)
        col = Color.from_hsv(sky_hue, 0.5 - ty * 0.25, 0.25 + ty * 0.55)
        for x in range(c.w):
            c.set_pixel(x, y, ' ', bg=col)

    lx = t * 0.35
    sx = int(c.w * 0.75 + math.cos(lx) * 22)
    sy = int(c.h * 0.15 + math.sin(lx) * 12)
    if 0 <= sx < c.w and 0 <= sy < c.h:
        c.set_pixel(sx, sy, '☼', Color(255, 240, 200), z=50)
        for dx in range(-3, 4):
            for dy in range(-3, 4):
                d = math.hypot(dx, dy)
                if d <= 3:
                    c.set_pixel(sx + dx, sy + dy, '·', Color(255, 200, 100).mul(max(0, 0.35 - 0.1 * d)), z=49)

    _voxel.render(c, angle=t * 0.18, elevation=0.55 + 0.05 * math.sin(t * 0.1),
                  distance=90, light_angle=lx, amb=0.45)

    for cx, cy, r in _clouds:
        dcx = cx + math.sin(t * 0.02 + cy * 0.1) * 5
        dcy = cy + math.cos(t * 0.015 + cx * 0.08) * 3
        for dx in range(-int(r), int(r) + 1):
            for dy in range(-int(r * 0.5), int(r * 0.5) + 1):
                dd = math.hypot(dx, dy * 2) / r
                if dd < 0.9 and random.random() < 0.85:
                    px, py = int(dcx + dx), int(dcy + dy * 2)
                    if 0 <= px < c.w and 0 <= py < c.h // 3:
                        a = max(0, 0.5 - dd * 0.3)
                        c.set_pixel(px, py, '░', Color(220, 230, 255).mul(a), z=30)

    shore_y = int(c.h * 0.58 + math.sin(t * 0.5) * 1)
    for x in range(0, c.w, 2):
        wc = int(120 + 80 * math.sin(t * 1.5 + x * 0.3))
        c.set_pixel(x, shore_y + int(math.sin(t + x * 0.5) * 2), '~', Color(60, 100, wc), z=20)

    c.draw_text(2, 0, 'Voxel World', Color(200, 220, 255), z=100)
    c.draw_text(2, c.h - 1, 'animated terrain | clouds | sun | water shimmer', DIM, z=100)
