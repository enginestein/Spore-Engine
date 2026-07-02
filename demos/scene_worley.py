import math
from spore_engine import *
from spore_engine.core.color import *
from spore_engine.sim.noise import WorleyNoise, OpenSimplexNoise

_WN = None

def scene_worley(c, hr, t, pt, dt):
    global _WN
    w, h = c.w, c.h
    if _WN is None:
        _WN = {'worley': WorleyNoise(42), 'osimplex': OpenSimplexNoise(99)}

    for y in range(h):
        for x in range(w):
            nx, ny = x * 0.06 + t * 0.01, y * 0.06 + t * 0.008
            mode = int(t * 0.15) % 3
            if mode == 0:
                v = _WN['worley'].noise2(nx, ny)
            elif mode == 1:
                v = _WN['worley'].fbm2(nx, ny, octaves=3)
            else:
                v = _WN['osimplex'].fbm2(nx, ny, octaves=4)
            v = max(-1, min(1, v))
            hue = (v * 0.15 + 0.6 + t * 0.005) % 1.0
            bright = 0.08 + abs(v) * 0.5
            col = Color.from_hsv(hue, 0.7, bright)
            ch = ' ' if abs(v) < 0.05 else ('░' if abs(v) < 0.2 else ('▒' if abs(v) < 0.4 else '▓'))
            c.set_pixel(x, y, ch if ch != ' ' else ' ', bg=col if ch == ' ' else None,
                       fg=col if ch != ' ' else None, z=5)

    mode_names = ['Worley (cellular)', 'Worley fbm', 'OpenSimplex']
    c.draw_text(2, 0, f"Noise: {mode_names[int(t*0.15)%3]}", WHITE, z=100)
    c.draw_text(2, h - 1, "Cycles through 3 noise types", DIM, z=100)
