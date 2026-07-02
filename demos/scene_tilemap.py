import math, random
from spore_engine.ui.tilemap import TileMap, Camera, generate_platformer, tile_collide
from spore_engine.core.color import Color, WHITE, DIM, GREEN, RED, BLUE

SHADE = ' .:-=+*#%@'
_LS = None

TILESET = {
    0: (' ', Color(10, 8, 20)),
    1: ('#', Color(60, 60, 80)),
    2: ('.', Color(40, 100, 40)),
    3: ('@', Color(180, 180, 60)),
    4: ('~', Color(30, 60, 120)),
}

def scene_tilemap(c, hr, t, pt, dt):
    global _LS
    if _LS is None:
        tm = generate_platformer(50, 18, 42)
        for x in range(10, 20):
            tm.set_tile(x, 10, 2)
            tm.set_collision(x, 10, False)
        for x in range(30, 35):
            for y in range(12, 15):
                tm.set_tile(x, y, 3)
                tm.set_collision(x, y, True)
        _LS = {
            'tm': tm,
            'cam': Camera(0, 0, c.w, c.h),
            'px': 3.0, 'py': 15.0,
            'pvx': 0.0, 'pvy': 0.0,
            'on_ground': False,
            'dir': 1,
            'collected': 0,
        }

    tm = _LS['tm']
    cam = _LS['cam']
    px = _LS['px']
    py = _LS['py']
    pvx = _LS['pvx']
    pvy = _LS['pvy']

    for y in range(c.h):
        ty = y / c.h
        for x in range(c.w):
            n = (math.sin(x*0.03+t*0.2)+math.cos(y*0.04+t*0.15))*0.5+0.5
            c.set_pixel(x, y, ' ', bg=Color(int(4+n*6), int(2+n*4), int(10+n*16)), z=-100)

    # Physics
    pvx *= 0.85
    if _LS['on_ground']:
        pvx += math.sin(t * 2.5) * 0.15
    pvy += 0.3
    px += pvx
    py += pvy

    # Floor collision
    if py > 16.5:
        py = 16.5
        pvy = 0
        _LS['on_ground'] = True
    else:
        _LS['on_ground'] = False

    # Wall collision
    if tile_collide(tm, px, py, 0.3):
        px -= pvx
        pvx *= -0.5
    if tile_collide(tm, px, py - 0.2, 0.3):
        py += abs(pvy) * 0.5
        pvy = 0
        _LS['on_ground'] = True

    # Wrap world
    if px < 0: px = 0
    if px > tm.width: px = 0

    _LS['px'] = px
    _LS['py'] = py

    # Camera follows player
    cam.follow(px, py, tm.width, tm.height, smooth=0.08)
    ox, oy = cam.ox, cam.oy

    # Render tilemap
    for ty in range(c.h):
        wy = ty + oy
        if wy < 0 or wy >= tm.height: continue
        for tx in range(c.w):
            wx = tx + ox
            if wx < 0 or wx >= tm.width: continue
            tid = tm.tiles[wy][wx]
            if tid in TILESET:
                ch, col = TILESET[tid]
                c.set_pixel(tx, ty, ch, col, z=10)

    # Player
    p_sx = int(px - ox)
    p_sy = int(py - oy)
    if 0 <= p_sx < c.w and 0 <= p_sy < c.h:
        c.set_pixel(p_sx, p_sy, '@', Color(255, 200, 100), z=20)
        c.set_pixel(p_sx, p_sy - 1, 'O' if _LS['on_ground'] else 'o', Color(255, 200, 100), z=20)

    # HUD
    c.draw_text(2, 0, "Tilemap (auto-scroll)", Color(180, 200, 100), z=100)
    c.draw_text(2, 1, f"pos: {px:.1f}, {py:.1f}", DIM, z=100)
    c.draw_text(c.w - 15, c.h - 1, "[auto-scroll]", DIM, z=100)
