import math, random
from spore_engine import *
from spore_engine.core.color import *
from spore_engine.sim.powder import PowderSim, SAND, WATER, STONE, WOOD, FIRE, OIL, LAVA, ACID, PLANT, SALT, STEAM, SMOKE, EMPTY, MATERIAL_NAMES

_PD = None

def scene_powder(c, hr, t, pt, dt):
    global _PD
    w, h = c.w, c.h

    if _PD is None:
        sim = PowderSim(w, h)
        _PD = {'sim': sim, 'mode': 0, 'last_clear': 0, 'frame': 0, 'spawn_timer': 0}

    s = _PD
    sim = s['sim']

    s['frame'] += 1
    mode = int(t / 8) % 5
    if mode != s['mode']:
        sim.clear()
        s['mode'] = mode

    if mode == 0:
        _auto_spray(sim, t, SAND, w, h)
    elif mode == 1:
        _auto_spray(sim, t, WATER, w, h)
    elif mode == 2:
        _build_walls(sim, t, w, h)
        _auto_spray(sim, t, FIRE, w, h)
    elif mode == 3:
        _build_walls(sim, t, w, h)
        _auto_spray(sim, t, LAVA, w, h)
    elif mode == 4:
        _build_walls(sim, t, w, h)
        if int(t * 4) % 2 == 0:
            _auto_spray(sim, t, PLANT, w, h)
        else:
            _auto_spray(sim, t, ACID, w, h)

    sim.update()

    for y in range(h):
        for x in range(w):
            col = Color(8 + y * 2 // h * 5, 6 + y * 2 // h * 4, 12)
            c.set_pixel(x, y, ' ', bg=col, z=-100)

    sim.render(c)

    mode_names = ['Sand', 'Water', 'Fire', 'Lava + Stone', 'Plant vs Acid']
    c.draw_text(2, 0, f"Powder Toy: {mode_names[mode]}", WHITE, z=100)
    c.draw_text(2, h - 1, "Auto-demo cycles through materials", DIM, z=100)


def _auto_spray(sim, t, mat, w, h):
    for _ in range(3):
        x = random.randint(2, w - 2)
        sim.set_cell(x, 0, mat)


def _build_walls(sim, t, w, h):
    phase = int(t * 0.5) % 3
    if phase == 0:
        for y in range(h):
            sim.set_cell(w // 3, y, STONE)
            sim.set_cell(w * 2 // 3, y, STONE)
    elif phase == 1:
        for y in range(h // 2):
            sim.set_cell(w // 2, y, STONE)
    else:
        for y in range(h):
            sim.set_cell(1, y, STONE)
            sim.set_cell(w - 2, y, STONE)
