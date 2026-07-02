import math, random
from spore_engine.core.color import Color, Gradient, PALETTES, WHITE
from spore_engine.core.canvas import Canvas, HiResCanvas
from spore_engine.gen.scenery import (
    CloudLayer, MountainProfile, DayNightCycle,
    WaterSurface, Tree, render_sky, render_stars, render_moon
)

_LS = None

def scene_scenery(c, hr, t, pt, dt):
    global _LS
    if _LS is None:
        _LS = {
            'cycle': DayNightCycle(cycle_duration=45.0),
            'clouds': CloudLayer(count=10, min_y=2, max_y=7,
                                 min_w=8, max_w=22,
                                 color=Color(220, 220, 240)),
            'mountains': MountainProfile(160, 14, scale=35, octaves=5,
                                         color=Color(70, 60, 90),
                                         snow_color=Color(210, 210, 230)),
            'water': WaterSurface(16, 80, Color(30, 70, 150), wave_speed=1.2),
            'trees': [
                Tree(18, 18, 5, Color(50, 130, 50), Color(100, 70, 40)),
                Tree(35, 18, 7, Color(60, 140, 60), Color(110, 80, 50)),
                Tree(52, 18, 4, Color(40, 120, 40), Color(90, 60, 30)),
                Tree(68, 18, 6, Color(55, 135, 55), Color(105, 75, 45)),
                Tree(85, 18, 8, Color(45, 125, 45), Color(95, 65, 35)),
            ],
            'stars_positions': [],
            'time': 0.0,
        }
        rng = random.Random(42)
        for _ in range(60):
            _LS['stars_positions'].append((rng.random(), rng.random()))
    s = _LS

    s['time'] += dt
    s['cycle'].update(dt)
    s['clouds'].update(dt, c.w)

    sky = s['cycle'].sky_color
    brightness = s['cycle'].ambient_brightness

    hr.clear()
    for y in range(hr.h):
        ty = y / hr.h
        for x in range(hr.w):
            n = (math.sin(x*0.01+t*0.1)+math.cos(y*0.015+t*0.08))*0.5+0.5
            col = sky.mul(brightness * (0.8 + 0.2*n))
            hr.set_pixel(x, y, ' ', bg=col, z=-100)

    if not s['cycle'].is_day:
        for rx, ry in s['stars_positions']:
            sx = int(rx * hr.w)
            sy = int(ry * hr.h * 0.4)
            twinkle = 0.5 + 0.5 * math.sin(s['time'] * 2 + sx * 7 + sy * 13)
            if twinkle > 0.65:
                b = int(150 + 105 * (twinkle - 0.65) / 0.35)
                hr.set_pixel(sx, sy, '.', Color(b, b, b), z=0)

    phase = s['cycle'].phase
    if phase < 0.15 or phase > 0.85:
        render_moon(c, s['time'], phase, z=5)

    hr.set_pixel(hr.w - 12, 3, '@', Color(255, 220, 100), z=5)
    for dx in range(-3, 4):
        for dy in range(-2, 3):
            hr.set_pixel(hr.w - 12 + dx, 3 + dy, ' ',
                        bg=Color(255, 220, 100), z=4)

    s['mountains'].render(c, 0, z=10)

    for tree in s['trees']:
        tree.render(c, 0, z=15)

    s['water'].update(dt)
    s['water'].render(c, z=20)

    s['clouds'].render(c, 0, z=5)

    info = f"Scenery | Time: {phase*100:.0f}% | {'☀ Day' if s['cycle'].is_day else '☽ Night'}"
    c.draw_text(2, 0, info, WHITE, z=100)
    c.draw_text(2, c.h - 1, f"Clouds: {len(s['clouds'].clouds)} | Trees: {len(s['trees'])}", Color(150, 150, 170), z=100)
