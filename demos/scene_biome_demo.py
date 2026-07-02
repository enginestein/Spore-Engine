import math
from spore_engine import *
from spore_engine.core.color import *
from spore_engine.gen.biome_terrain import BiomeMap

_BD = None

def scene_biome_demo(c, hr, t, pt, dt):
    global _BD
    w, h = c.w, c.h
    if _BD is None:
        bm = BiomeMap(w, h, seed=int(t * 10) % 1000)
        _BD = {'bm': bm, 'last_seed': 0}

    s = _BD
    new_seed = int(t * 0.15) % 1000
    if new_seed != s.get('last_seed', -1):
        s['bm'] = BiomeMap(w, h, seed=new_seed)
        s['last_seed'] = new_seed

    bm = s['bm']
    bm.render(c)

    c.draw_text(2, 0, "Multi-Biome Terrain", WHITE, z=100)
    c.draw_text(2, h - 1, "Regenerates every ~7s", DIM, z=100)
