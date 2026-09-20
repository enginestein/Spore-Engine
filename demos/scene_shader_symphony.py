import math, random
from spore_engine import *
from spore_engine.core.color import *
from spore_engine.fx.shaders import (
    ShaderPipeline, WaveDistort, SwirlDistort,
    Posterize, Solarize, CelShade, HeatHaze, Emboss,
    PixelSort, Crystallize, ASCIIRemap, ChannelShift,
    Kaleidoscope, Warp, VHSGlitch, Ripple,
)


def _draw_rich_scene(c, t):
    """Draw a beautiful animated scene for shaders to transform"""
    w, h = c.w, c.h
    
    # 1. Background - nebula gradient
    for y in range(h):
        for x in range(w):
            nx, ny = x / w, y / h
            # Layered sine waves for organic nebula look
            v1 = math.sin(nx * 12 + t * 0.15) * math.cos(ny * 10 + t * 0.1)
            v2 = math.sin((nx + ny) * 8 + t * 0.2) * 0.5
            v3 = math.cos(nx * 20 - t * 0.3) * math.sin(ny * 18 + t * 0.25) * 0.3
            v = v1 * 0.5 + v2 + v3
            v = v * 0.5 + 0.5
            
            hue = (nx * 0.4 + ny * 0.3 + t * 0.008) % 1.0
            col = Color.from_hsv(hue, 0.6, 0.08 + v * 0.5)
            ch = ' ' if v < 0.15 else ('░' if v < 0.35 else ('▒' if v < 0.55 else ('▓' if v < 0.75 else '█')))
            c.set_pixel(x, y, ch, col, z=5)

    # 2. Spinning spiral arms
    cx, cy = w // 2, h // 2
    for arm in range(3):
        for i in range(60):
            a = arm * 2.094 + i * 0.08 + t * 0.15
            r = i * 0.5 + 3 * math.sin(i * 0.05 + t * 0.3)
            px = int(cx + r * math.cos(a))
            py = int(cy + r * math.sin(a) * 0.6)
            if 0 <= px < w and 0 <= py < h:
                hue2 = (arm / 3 + i * 0.01 + t * 0.01) % 1.0
                bright = 0.5 + 0.5 * math.sin(i * 0.1 - t)
                c.set_pixel(px, py, '♦', Color.from_hsv(hue2, 0.9, bright), z=10)

    # 3. Floating geometric shapes
    for i in range(12):
        a = i * 0.524 + t * 0.05
        r = 3 + 2 * math.sin(i * 1.7 + t * 0.4)
        px = int(cx + r * 6 * math.cos(a))
        py = int(cy + r * 3 * math.sin(a * 0.7))
        for j in range(6):
            a2 = j * 1.047 + t * 0.2
            r2 = 1.5 + 0.8 * math.sin(t + j * 0.5)
            sx = int(px + r2 * 4 * math.cos(a2))
            sy = int(py + r2 * 2 * math.sin(a2))
            if 0 <= sx < w and 0 <= sy < h:
                hue3 = (j / 6 + i * 0.05 + t * 0.02) % 1.0
                c.set_pixel(sx, sy, '◆', Color.from_hsv(hue3, 0.85, 0.9), z=12)

    # 4. Pulsing rings
    for i in range(3):
        r_ring = 8 + i * 4 + 2 * math.sin(t * 0.3 + i * 1.2)
        thickness = 2 + math.sin(t * 0.5 + i)
        for angle in range(0, 360, 3):
            a = math.radians(angle)
            px = int(cx + r_ring * math.cos(a))
            py = int(cy + r_ring * math.sin(a) * 0.5)
            if 0 <= px < w and 0 <= py < h:
                hue4 = (angle / 360 + i * 0.33 + t * 0.015) % 1.0
                c.set_pixel(px, py, '●', Color.from_hsv(hue4, 0.8, 0.9), z=8)

    # 5. Stars twinkling in background
    for _ in range(40):
        sx = random.randint(0, w - 1)
        sy = random.randint(0, h - 1)
        twinkle = 0.3 + 0.7 * math.sin(sx * 3.7 + sy * 7.3 + t * 2.0)
        if twinkle > 0.5:
            star_bright = (twinkle - 0.5) * 2
            c.set_pixel(sx, sy, '·', Color(
                int(200 * star_bright), 
                int(200 * star_bright), 
                int(255 * star_bright)
            ), z=3)


_SHADER_CONFIGS = [
    ([WaveDistort(amp_x=3, amp_y=2, freq_x=0.06, freq_y=0.05)], 'Wave Distort'),
    ([SwirlDistort(strength=0.025)], 'Swirl'),
    ([Kaleidoscope(segments=6)], 'Kaleidoscope'),
    ([Crystallize(cell_size=6)], 'Crystallize'),
    ([Ripple(amplitude=3, frequency=0.3, speed=1.5)], 'Ripple'),
    ([Warp(time_scale=0.6)], 'Warp'),
    ([Solarize(threshold=0.4)], 'Solarize'),
    ([Posterize(levels=4), WaveDistort(amp_x=1, amp_y=1)], 'Posterize + Wave'),
    ([CelShade(levels=3, edge_threshold=0.12)], 'Cel Shade'),
    ([ChannelShift(r_shift=2, g_shift=-1, b_shift=-3)], 'Channel Shift'),
    ([HeatHaze(amplitude=3, frequency=0.03, speed=1.2)], 'Heat Haze'),
    ([Emboss(intensity=1.2)], 'Emboss'),
    ([ASCIIRemap(invert=False)], 'ASCII Remap'),
    ([VHSGlitch(intensity=0.15)], 'VHS Glitch'),
    ([Ripple(amplitude=2, frequency=0.4, speed=2.0), WaveDistort(amp_x=1, amp_y=1)], 'Ripple + Wave'),
    ([Kaleidoscope(segments=4), Posterize(levels=3)], 'Kaleidoscope + Posterize'),
]


def scene_shader_symphony(c: Canvas, hr: HiResCanvas, t: float, pt, dt: float):
    """Shader Symphony - Rich animated scene transformed by a rotating gallery of shader pipelines"""
    w, h = c.w, c.h
    idx = int(t / 5) % len(_SHADER_CONFIGS)
    
    _draw_rich_scene(c, t)
    
    # Apply the current shader pipeline
    shaders, name = _SHADER_CONFIGS[idx]
    pipe = ShaderPipeline()
    for sh in shaders:
        pipe.add(sh)
    pipe.apply(c, t, dt)
    
    # Info overlay
    c.draw_text(2, 0, f'◈ Shader Symphony — {name}', WHITE, z=100)
    progress = (t % 5) / 5
    bar_len = 20
    filled = int(progress * bar_len)
    bar = '█' * filled + '░' * (bar_len - filled)
    c.draw_text(2, h - 1, f'[{bar}]  {idx+1}/{len(_SHADER_CONFIGS)}  press n/p', DIM, z=100)
