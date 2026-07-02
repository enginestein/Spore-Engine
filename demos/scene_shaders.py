import math, random
from spore_engine import *
from spore_engine.core.color import *
from spore_engine.fx.shaders import (
    ShaderPipeline, WaveDistort, SwirlDistort, KuwaharaFilter,
    Posterize, Solarize, CelShade, HeatHaze, Emboss,
    PixelSort, Crystallize, ASCIIRemap, ChannelShift,
    Kaleidoscope, Warp, VHSGlitch, Ripple,
)

_SD = None

def _draw_test_scene(c, t):
    w, h = c.w, c.h
    for y in range(h):
        for x in range(w):
            nx, ny = x / w, y / h
            v = (math.sin(nx * 8 + t * 0.3) * math.cos(ny * 6 + t * 0.2)
                 + 0.5 * math.sin((nx + ny) * 5 + t * 0.4))
            v = v * 0.5 + 0.5
            hue = (nx * 0.3 + ny * 0.5 + t * 0.02) % 1.0
            col = Color.from_hsv(hue, 0.7, 0.15 + v * 0.7)
            ch = ' ' if v < 0.2 else ('░' if v < 0.4 else ('▒' if v < 0.6 else ('▓' if v < 0.8 else '█')))
            c.set_pixel(x, y, ch, col, z=5)

    cx, cy = w // 2, h // 2
    for i in range(6):
        a = i / 6 * math.pi * 2 + t * 0.2
        r = 6 + 3 * math.sin(i * 2.5 + t)
        px = int(cx + r * 8 * math.cos(a))
        py = int(cy + r * 3 * math.sin(a))
        for j in range(8):
            a2 = j / 8 * math.pi * 2 - t * 0.3
            r2 = 2 + math.sin(t + j)
            sx = int(px + r2 * 4 * math.cos(a2))
            sy = int(py + r2 * 2 * math.sin(a2))
            if 0 <= sx < w and 0 <= sy < h:
                col = Color.from_hsv(j / 8 + t * 0.01, 0.8, 0.9)
                c.set_pixel(sx, sy, '♦', col, z=10)

    for i in range(5):
        y = int(4 + i * 5 + 2 * math.sin(i * 1.3 + t * 0.5))
        for x in range(w):
            col = Color.from_hsv(i * 0.2 + t * 0.01, 0.8, 0.7 + 0.3 * math.sin(x * 0.1 + t))
            c.set_pixel(x, y, '─', col, z=3)


def scene_shaders(c, hr, t, pt, dt):
    global _SD
    w, h = c.w, c.h

    if _SD is None:
        _SD = {
            'pipeline': ShaderPipeline(),
            'current': 0,
            'last_switch': 0,
        }

    s = _SD
    dur = 6.0
    idx = int(t / dur) % 12

    if idx != s['current'] or s['last_switch'] == 0:
        s['current'] = idx
        s['last_switch'] = t
        pipe = ShaderPipeline()
        configs = [
            [WaveDistort(amp_x=2, amp_y=1, freq_x=0.08, freq_y=0.06)],
            [SwirlDistort(strength=0.03)],
            [Posterize(levels=4)],
            [Solarize(threshold=0.45)],
            [CelShade(levels=3, edge_threshold=0.15)],
            [Crystallize(cell_size=6, seed=42)],
            [ASCIIRemap(invert=False)],
            [ChannelShift(r_shift=2, g_shift=0, b_shift=-2)],
            [Kaleidoscope(segments=8)],
            [Warp(time_scale=0.8)],
            [Ripple(amplitude=2, frequency=0.4, speed=2.0)],
            [HeatHaze(amplitude=2, frequency=0.04, speed=1.5), WaveDistort(amp_x=1, amp_y=1)],
        ]
        for shader_cls in configs[idx]:
            pipe.add(shader_cls)
        _SD['pipeline'] = pipe

    _draw_test_scene(c, t)
    s['pipeline'].apply(c, t, dt)

    names = [
        'Wave Distort', 'Swirl', 'Posterize', 'Solarize',
        'Cel Shade', 'Crystallize', 'ASCII Remap',
        'Channel Shift', 'Kaleidoscope', 'Warp',
        'Ripple', 'Heat Haze + Wave',
    ]
    name = names[idx]
    c.draw_text(2, 0, f"Shader: {name}", WHITE, z=100)
    c.draw_text(2, h - 1, f"Pipeline: {s['pipeline']}", DIM, z=100)
