from spore_engine import *
from spore_engine.core.color import *
from spore_engine.gen.erosion import ErosionSim

_ES = None

def scene_erosion(c, hr, t, pt, dt):
    global _ES
    w, h = c.w, c.h

    if _ES is None:
        sim = ErosionSim(w, h)
        sim.generate_heightmap(scale=0.04, octaves=6, seed=42, amplitude=1.0)
        _ES = {'sim': sim, 'phase': 0, 'step': 0}

    s = _ES
    sim = s['sim']
    sim.w, sim.h = w, h

    phase = int(t / 12) % 3

    if phase != s['phase']:
        s['phase'] = phase
        s['step'] = 0
        if phase == 0:
            sim.generate_heightmap(scale=0.04, octaves=6, seed=42, amplitude=1.0)
        elif phase == 1:
            sim.generate_heightmap(scale=0.03, octaves=4, seed=99, amplitude=0.8)
        else:
            sim.generate_heightmap(scale=0.06, octaves=3, seed=7, amplitude=1.2)

    if s['step'] < 5:
        count = [5000, 3000, 8000][phase]
        sim.erode(num_drops=count, rain_rate=0.01, evap_rate=0.04,
                  sediment_capacity=3.0, deposit_rate=0.3,
                  erosion_rate=0.04, gravity=4.0, max_steps=60)
        s['step'] += 1

    for y in range(h):
        for x in range(w):
            c.set_pixel(x, y, ' ', bg=Color(int(8 + y*6//h), int(4 + y*4//h), int(10 + y*8//h)), z=-100)

    sim.render_shaded(c, z=5)

    phases = ['Mountain Erosion', 'Valley Carving', 'Canyon Formation']
    name = phases[phase]
    info = f"Erosion passes: {s['step']}/5"
    c.draw_text(2, 0, f"Hydraulic Erosion: {name}", WHITE, z=100)
    c.draw_text(2, h - 1, info, DIM, z=100)
