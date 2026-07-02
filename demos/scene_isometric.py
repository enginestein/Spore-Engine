import math
from spore_engine import *
from spore_engine.core.color import *
from spore_engine.render3d.isometric import IsoTile, IsoMap
from spore_engine.sim.noise import PerlinNoise

_IM = None

def scene_isometric(c, hr, t, pt, dt):
    global _IM
    w, h = c.w, c.h
    if _IM is None:
        noise = PerlinNoise(42)
        map_w, map_h = 20, 20
        hm = [[0.0] * map_h for _ in range(map_w)]
        for gy in range(map_h):
            for gx in range(map_w):
                hm[gy][gx] = noise.fbm2(gx * 0.15, gy * 0.15, octaves=3) * 0.5 + 0.5
        isomap = IsoMap(map_w, map_h, tile_w=4.0, tile_h=2.0)
        for gy in range(map_h):
            for gx in range(map_w):
                h_val = hm[gy][gx]
                z = int(h_val * 4)
                hue = 0.25 + h_val * 0.15
                b = 0.2 + h_val * 0.7
                col = Color.from_hsv(hue, 0.65, b)
                isomap.set_tile(gx, gy, z, IsoTile(gx, gy, z, '█', col, height=h_val))
                for iz in range(1, z + 1):
                    dark = col.mul(0.4 + 0.6 * (1 - iz / max(1, z)))
                    isomap.set_tile(gx, gy, iz, IsoTile(gx, gy, iz, '▓', dark, height=h_val))
        _IM = {'map': isomap, 'noise': noise}

    s = _IM
    isomap = s['map']

    for y in range(h):
        for x in range(w):
            c.set_pixel(x, y, ' ', bg=Color(int(3 + y/h*6), int(2 + y/h*4), int(8 + y/h*10)), z=-100)

    isomap.camera.ox = 0
    isomap.camera.oy = math.sin(t * 0.1) * 2
    isomap.camera.zoom = 1.0 + 0.1 * math.sin(t * 0.15)
    isomap.render(c)

    c.draw_text(2, 0, "Isometric Terrain", WHITE, z=100)
    c.draw_text(2, 1, "Camera orbits slowly", DIM, z=100)
