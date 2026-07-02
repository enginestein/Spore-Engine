import math, random
from spore_engine import *
from spore_engine.core.color import *

_AS = None

def scene_aurora_storm(c, hr, t, pt, dt):
    global _AS
    w, h = c.w, c.h

    if _AS is None:
        freqs = []
        for _ in range(12):
            freqs.append({
                'freq_x': random.uniform(0.005, 0.025),
                'freq_y': random.uniform(0.01, 0.04),
                'freq_t': random.uniform(0.02, 0.08),
                'phase': random.uniform(0, 2*math.pi),
                'amp': random.uniform(0.3, 1.0),
                'hue': random.uniform(0.6, 0.9),
                'speed': random.uniform(0.3, 1.5),
            })
        columns = []
        for _ in range(20):
            columns.append({
                'x': random.uniform(0, w),
                'width': random.uniform(2, 8),
                'hue': random.uniform(0.65, 0.85),
                'phase': random.uniform(0, 2*math.pi),
                'pulse_speed': random.uniform(0.3, 1.0),
            })
        spikes = []
        for _ in range(40):
            spikes.append({
                'x': random.uniform(0, w),
                'hue': random.uniform(0.0, 0.15),
                'phase': random.uniform(0, 2*math.pi),
                'height': random.uniform(0.1, 0.4),
            })
        _AS = {'freqs': freqs, 'columns': columns, 'spikes': spikes}

    s = _AS

    for y in range(h):
        ty = y / h
        col = Color(int(2 + ty * 8), int(ty * 6), int(5 + ty * 20))
        for x in range(w):
            c.set_pixel(x, y, ' ', bg=col, z=-100)

    aurora_h = int(h * 0.55)
    for y in range(aurora_h):
        gy = int(h * 0.02 + y * 0.6)
        if gy >= h: continue
        ty = y / aurora_h
        falloff = math.sin(ty * math.pi)
        for x in range(w):
            val = 0
            for f in s['freqs']:
                n = math.sin(x * f['freq_x'] + gy * f['freq_y'] + t * f['freq_t'] + f['phase'])
                n += math.sin(x * f['freq_x'] * 2.3 + gy * f['freq_y'] * 1.7 - t * f['freq_t'] * 0.7 + f['phase'] * 1.3)
                val += n * f['amp'] * 0.3
            val = val / len(s['freqs']) * 0.5 + 0.5
            val = min(1.0, val * 1.8)
            val *= falloff

            if val > 0.08:
                for f in s['freqs']:
                    if f['amp'] > 0.7:
                        hue = f['hue'] + ty * 0.1 + val * 0.08 + t * 0.005
                        break
                else:
                    hue = 0.7 + ty * 0.15 + val * 0.05 + t * 0.003
                hue = hue % 1.0
                bright = 0.15 + val * 0.7
                ch = '░' if val < 0.25 else ('▒' if val < 0.45 else ('▓' if val < 0.7 else '█'))
                c.set_pixel(x, gy, ch, Color.from_hsv(hue, 0.75, bright), z=10)

    for col in s['columns']:
        col_pulse = 0.5 + 0.5 * math.sin(t * col['pulse_speed'] + col['phase'])
        if col_pulse < 0.3: continue
        col_width = int(col['width'] * (0.5 + 0.5 * col_pulse))
        for xx in range(int(col['x']) - col_width, int(col['x']) + col_width + 1):
            if 0 <= xx < w:
                dist = abs(xx - col['x']) / max(1, col_width)
                for yy in range(int(h * 0.1), int(h * 0.55)):
                    gy = int(h * 0.02 + (yy / (h * 0.45)) * 0.6 * h * 0.55)
                    gy = min(gy, h - 1)
                    ty = (yy - int(h * 0.1)) / max(1, int(h * 0.45))
                    falloff = math.sin(ty * math.pi) * (1 - dist * 0.6)
                    if falloff < 0.1: continue
                    flicker = 0.7 + 0.3 * math.sin(t * 3 + xx * 2 + gy * 1.5 + col['phase'])
                    bright = min(1.0, col_pulse * falloff * flicker * 0.8)
                    if bright > 0.1:
                        hue = (col['hue'] + ty * 0.05 + t * 0.01) % 1.0
                        ch = '░' if bright < 0.3 else ('▒' if bright < 0.5 else '▓')
                        c.set_pixel(xx, gy, ch, Color.from_hsv(hue, 0.8, bright), z=12)

    for sp in s['spikes']:
        sp_pulse = 0.3 + 0.7 * (0.5 + 0.5 * math.sin(t * 1.2 + sp['phase']))
        height = int(h * sp['height'] * sp_pulse)
        base_x = int(sp['x'])
        for yy in range(height):
            gy = int(h * 0.05 + yy * 0.6)
            if gy >= h: break
            ty = yy / height
            width = max(1, int(3 * (1 - ty * 0.7)))
            for xx in range(base_x - width, base_x + width + 1):
                if 0 <= xx < w:
                    d = abs(xx - base_x) / max(1, width)
                    flicker = 0.6 + 0.4 * math.sin(t * 5 + xx * 3 + yy + sp['phase'])
                    bright = sp_pulse * (1 - ty * 0.5) * (1 - d * 0.5) * flicker
                    if bright > 0.15:
                        hue = (sp['hue'] + ty * 0.06 + t * 0.02) % 1.0
                        ch = '│' if width < 2 else ('░' if ty > 0.6 else '▒')
                        c.set_pixel(xx, gy, ch, Color.from_hsv(hue, 0.9, bright), z=15)
