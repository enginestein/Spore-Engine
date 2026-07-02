import math, random
from spore_engine.core.color import Color, WHITE, RED, GREEN, YELLOW, CYAN, MAGENTA, ORANGE, DIM, PALETTES
from spore_engine.core.canvas import Canvas
from spore_engine.fx.effects import (
    Emitter, FountainEmitter, StreamEmitter, FireEmitter,
    burst_explosion, burst_ring, burst_directional, Particle
)

_LS = None

def scene_particles(c, hr, t, pt, dt):
    global _LS
    if _LS is None:
        w, h = c.w, c.h
        fountain = FountainEmitter(w // 2, h - 4, max_particles=120)
        stream = StreamEmitter(10, h // 2, angle=0, max_particles=60,
                               colors=[Color(100, 200, 255), Color(150, 220, 255)])
        stream.speed = 3.0
        stream.spread = 0.2
        stream.set_rate(12)
        fire = FireEmitter(w - 10, h - 4, max_particles=40)
        fire.set_rate(20)
        explosions = []
        burst_parts = []
        _LS = {
            'fountain': fountain,
            'stream': stream,
            'fire': fire,
            'explosions': explosions,
            'burst_parts': burst_parts,
            'time': 0.0,
            'phase': 0,
        }
    s = _LS
    s['time'] += dt

    c.clear()
    for y in range(c.h):
        ty = y / c.h
        for x in range(c.w):
            n = (math.sin(x*0.03+t*0.1)+math.cos(y*0.04+t*0.08))*0.5+0.5
            c.set_pixel(x, y, ' ', bg=Color(int(3+n*6), int(1+n*4), int(8+n*16)), z=-100)

    phase = int(s['time'] / 6) % 4
    s['phase'] = phase

    if phase == 0:
        s['fountain'].x = c.w // 2 + 20 * math.sin(s['time'] * 0.5)
        s['fountain'].update(dt, gravity=1.5)
        s['fountain'].render(c, z=10)
        label = "Fountain Emitter"
    elif phase == 1:
        s['stream'].x = 10 + 30 * (0.5 + 0.5 * math.sin(s['time'] * 0.3))
        s['stream'].y = c.h // 2 + 5 * math.sin(s['time'] * 0.7)
        s['stream'].update(dt, gravity=0.5)
        s['stream'].render(c, z=10)
        label = "Stream Emitter"
        for x in range(c.w):
            c.set_pixel(x, c.h // 2 + round(5 * math.sin(s['time'] * 0.7)), '_',
                       Color(40, 40, 60), z=0)
    elif phase == 2:
        s['fire'].update(dt, gravity=0)
        s['fire'].render(c, z=10)
        label = "Fire Emitter"
        for x in range(c.w):
            c.set_pixel(x, c.h - 3, '#', Color(60, 40, 30), z=0)
    else:
        if s['time'] % 6 < 0.5:
            cx = random.randint(15, c.w - 15)
            cy = random.randint(8, c.h - 8)
            colors = random.choice([PALETTES['fire'], PALETTES['neon'],
                                    PALETTES['ocean'], PALETTES['sunset']])
            s['burst_parts'].extend(burst_explosion(cx, cy, 30, colors, speed=5))
            s['burst_parts'].extend(burst_ring(cx, cy, 16, colors[0], speed=3))
        s['burst_parts'] = [p for p in s['burst_parts'] if not p.dead]
        for p in s['burst_parts']:
            p.update(dt, gravity=1.0, drag=0.96)
            p.render(c, z=10)
        label = f"Bursts: {len(s['burst_parts'])} particles"

    c.draw_text(2, 0, f"Particle FX | {label}", WHITE, z=20)
    c.draw_text(2, 1, f"Phase: {phase + 1}/4 (cycles every 6s)", DIM, z=20)
    phases = ["Fountain", "Stream", "Fire", "Bursts"]
    c.draw_text(2, c.h - 1, f"Next: {phases[(phase + 1) % 4]}", DIM, z=20)
