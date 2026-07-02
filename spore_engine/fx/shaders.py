from __future__ import annotations
import math, random
from typing import Optional, Callable
from ..core.canvas import Canvas, Cell
from ..core.color import Color, BLACK, WHITE


SHADE_CHARS = ' .:-=+*#%@'


class Shader:
    name: str = 'shader'
    enabled: bool = True

    def apply(self, canvas: Canvas, t: float = 0, dt: float = 0):
        raise NotImplementedError


class ShaderPipeline:
    def __init__(self):
        self.shaders: list[Shader] = []

    def add(self, shader: Shader):
        self.shaders.append(shader)
        return self

    def remove(self, name: str):
        self.shaders = [s for s in self.shaders if s.name != name]

    def get(self, name: str) -> Optional[Shader]:
        for s in self.shaders:
            if s.name == name:
                return s
        return None

    def apply(self, canvas: Canvas, t: float = 0, dt: float = 0):
        for shader in self.shaders:
            if shader.enabled:
                shader.apply(canvas, t, dt)
        return canvas

    def __len__(self):
        return len(self.shaders)

    def __repr__(self):
        names = [f'{s.name}({"on" if s.enabled else "off"})' for s in self.shaders]
        return f'ShaderPipeline({", ".join(names)})'


class WaveDistort(Shader):
    def __init__(self, amp_x: float = 2.0, amp_y: float = 1.0,
                 freq_x: float = 0.1, freq_y: float = 0.08,
                 speed: float = 1.0):
        self.name = 'wave_distort'
        self.amp_x = amp_x
        self.amp_y = amp_y
        self.freq_x = freq_x
        self.freq_y = freq_y
        self.speed = speed

    def apply(self, canvas: Canvas, t: float = 0, dt: float = 0):
        w, h = canvas.width, canvas.height
        buf = [[Cell() for _ in range(w)] for _ in range(h)]
        for y in range(h):
            for x in range(w):
                buf[y][x] = Cell(canvas.buffer[y][x].char,
                                 canvas.buffer[y][x].fg,
                                 canvas.buffer[y][x].bg,
                                 canvas.buffer[y][x].z)
        for y in range(h):
            for x in range(w):
                sx = x + self.amp_x * math.sin(y * self.freq_y + t * self.speed)
                sy = y + self.amp_y * math.cos(x * self.freq_x + t * self.speed * 0.7)
                sx_i, sy_i = int(sx), int(sy)
                if 0 <= sx_i < w and 0 <= sy_i < h and 0 <= x < w and 0 <= y < h:
                    src = buf[sy_i][sx_i]
                    if src.fg is not None:
                        canvas.buffer[y][x].fg = src.fg
                        canvas.buffer[y][x].bg = src.bg
                        canvas.buffer[y][x].char = src.char
                    else:
                        canvas.buffer[y][x].fg = None
                        canvas.buffer[y][x].bg = None
                        canvas.buffer[y][x].char = ' '


class KuwaharaFilter(Shader):
    def __init__(self, radius: int = 2):
        self.name = 'kuwahara'
        self.radius = radius

    def apply(self, canvas: Canvas, t: float = 0, dt: float = 0):
        w, h = canvas.width, canvas.height
        r = self.radius
        buf = [[Cell() for _ in range(w)] for _ in range(h)]
        for y in range(h):
            for x in range(w):
                c = canvas.buffer[y][x]
                buf[y][x] = Cell(c.char, c.fg, c.bg, c.z)
        quadrants = [
            (-1, -1, 0, 0), (0, -1, r, 0),
            (-1, 0, 0, r), (0, 0, r, r),
        ]
        for y in range(h):
            for x in range(w):
                best_var = float('inf')
                best_color = buf[y][x].fg
                for qx, qy, qw, qh in quadrants:
                    r_sum, g_sum, b_sum, count = 0, 0, 0, 0
                    for dy in range(qy, qh + 1):
                        for dx in range(qx, qw + 1):
                            nx, ny = x + dx + (1 if qx == -1 else 0) - r // 2, y + dy + (1 if qy == -1 else 0) - r // 2
                            if 0 <= nx < w and 0 <= ny < h:
                                cell = buf[ny][nx]
                                if cell.fg:
                                    r_sum += cell.fg.r
                                    g_sum += cell.fg.g
                                    b_sum += cell.fg.b
                                    count += 1
                    if count > 0:
                        mean_r, mean_g, mean_b = r_sum / count, g_sum / count, b_sum / count
                        var = 0
                        for dy in range(qy, qh + 1):
                            for dx in range(qx, qw + 1):
                                nx, ny = x + dx + (1 if qx == -1 else 0) - r // 2, y + dy + (1 if qy == -1 else 0) - r // 2
                                if 0 <= nx < w and 0 <= ny < h:
                                    cell = buf[ny][nx]
                                    if cell.fg:
                                        var += (cell.fg.r - mean_r) ** 2 + (cell.fg.g - mean_g) ** 2 + (cell.fg.b - mean_b) ** 2
                        if var < best_var:
                            best_var = var
                            best_color = Color(int(mean_r), int(mean_g), int(mean_b))
                if best_color:
                    canvas.buffer[y][x].fg = best_color


class SwirlDistort(Shader):
    def __init__(self, strength: float = 0.02):
        self.name = 'swirl'
        self.strength = strength

    def apply(self, canvas: Canvas, t: float = 0, dt: float = 0):
        w, h = canvas.width, canvas.height
        cx, cy = w / 2, h / 2
        buf = [[Cell() for _ in range(w)] for _ in range(h)]
        for y in range(h):
            for x in range(w):
                c = canvas.buffer[y][x]
                buf[y][x] = Cell(c.char, c.fg, c.bg, c.z)
        radius = math.hypot(w, h) / 2
        for y in range(h):
            for x in range(w):
                dx, dy = x - cx, y - cy
                d = math.hypot(dx, dy)
                if d < 1:
                    continue
                angle = self.strength * d / radius + t * 0.2
                cos_a, sin_a = math.cos(angle), math.sin(angle)
                sx = int(cx + dx * cos_a - dy * sin_a)
                sy = int(cy + dx * sin_a + dy * cos_a)
                if 0 <= sx < w and 0 <= sy < h:
                    src = buf[sy][sx]
                    canvas.buffer[y][x].fg = src.fg
                    canvas.buffer[y][x].bg = src.bg
                    canvas.buffer[y][x].char = src.char


class Posterize(Shader):
    def __init__(self, levels: int = 4):
        self.name = 'posterize'
        self.levels = levels

    def apply(self, canvas: Canvas, t: float = 0, dt: float = 0):
        step = 255 // (self.levels - 1)
        for y in range(canvas.height):
            for x in range(canvas.width):
                cell = canvas.buffer[y][x]
                if cell.fg:
                    r = round(cell.fg.r / step) * step
                    g = round(cell.fg.g / step) * step
                    b = round(cell.fg.b / step) * step
                    cell.fg = Color(min(255, r), min(255, g), min(255, b))
                if cell.bg:
                    r = round(cell.bg.r / step) * step
                    g = round(cell.bg.g / step) * step
                    b = round(cell.bg.b / step) * step
                    cell.bg = Color(min(255, r), min(255, g), min(255, b))


class Solarize(Shader):
    def __init__(self, threshold: float = 0.5):
        self.name = 'solarize'
        self.threshold = threshold

    def apply(self, canvas: Canvas, t: float = 0, dt: float = 0):
        thresh = self.threshold * 255
        for y in range(canvas.height):
            for x in range(canvas.width):
                cell = canvas.buffer[y][x]
                if cell.fg:
                    lum = cell.fg.r * 0.299 + cell.fg.g * 0.587 + cell.fg.b * 0.114
                    if lum > thresh:
                        cell.fg = Color(255 - cell.fg.r, 255 - cell.fg.g, 255 - cell.fg.b)
                if cell.bg:
                    lum = cell.bg.r * 0.299 + cell.bg.g * 0.587 + cell.bg.b * 0.114
                    if lum > thresh:
                        cell.bg = Color(255 - cell.bg.r, 255 - cell.bg.g, 255 - cell.bg.b)


class CelShade(Shader):
    def __init__(self, levels: int = 3, edge_threshold: float = 0.2):
        self.name = 'cel_shade'
        self.levels = levels
        self.edge_threshold = edge_threshold

    def apply(self, canvas: Canvas, t: float = 0, dt: float = 0):
        w, h = canvas.width, canvas.height
        step = 1.0 / self.levels
        for y in range(h):
            for x in range(w):
                cell = canvas.buffer[y][x]
                if cell.fg:
                    lum = cell.fg.luminance / 255
                    quantized = round(lum / step) * step
                    cell.fg = cell.fg.mul(quantized)
        for y in range(1, h - 1):
            for x in range(1, w - 1):
                cell = canvas.buffer[y][x]
                if not cell.fg:
                    continue
                ex = any(
                    canvas.buffer[y + dy][x + dx].fg
                    and abs(cell.fg.luminance - canvas.buffer[y + dy][x + dx].fg.luminance) > self.edge_threshold * 255
                    for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1)]
                )
                if ex:
                    cell.fg = cell.fg.mul(0.3)


class HeatHaze(Shader):
    def __init__(self, amplitude: float = 2.0, frequency: float = 0.04, speed: float = 1.5):
        self.name = 'heat_haze'
        self.amplitude = amplitude
        self.frequency = frequency
        self.speed = speed

    def apply(self, canvas: Canvas, t: float = 0, dt: float = 0):
        w, h = canvas.width, canvas.height
        buf = [[Cell() for _ in range(w)] for _ in range(h)]
        for y in range(h):
            for x in range(w):
                c = canvas.buffer[y][x]
                buf[y][x] = Cell(c.char, c.fg, c.bg, c.z)
        for y in range(h):
            noise = math.sin(y * self.frequency + t * self.speed) * self.amplitude
            for x in range(w):
                sx = int(x + noise * (1 - y / h))
                if 0 <= sx < w:
                    src = buf[y][sx]
                    if src.fg:
                        canvas.buffer[y][x].fg = src.fg
                        canvas.buffer[y][x].bg = src.bg
                        canvas.buffer[y][x].char = src.char
                    else:
                        canvas.buffer[y][x].fg = None
                        canvas.buffer[y][x].bg = None
                        canvas.buffer[y][x].char = ' '


class Emboss(Shader):
    def __init__(self, intensity: float = 1.0):
        self.name = 'emboss'
        self.intensity = intensity

    def apply(self, canvas: Canvas, t: float = 0, dt: float = 0):
        w, h = canvas.width, canvas.height
        buf = [[0.0] * w for _ in range(h)]
        for y in range(h):
            for x in range(w):
                cell = canvas.buffer[y][x]
                buf[y][x] = cell.fg.luminance if cell.fg else 0
        for y in range(1, h - 1):
            for x in range(1, w - 1):
                val = (-buf[y - 1][x - 1] - buf[y - 1][x] - buf[y - 1][x + 1]
                       - buf[y][x - 1] + buf[y][x + 1]
                       + buf[y + 1][x - 1] + buf[y + 1][x] + buf[y + 1][x + 1])
                val = val / 255 * self.intensity
                val = max(-1, min(1, val))
                gray = int((val * 0.5 + 0.5) * 255)
                canvas.buffer[y][x].fg = Color(gray, gray, gray)
                canvas.buffer[y][x].bg = None
                canvas.buffer[y][x].char = '@'


class PixelSort(Shader):
    def __init__(self, axis: str = 'x'):
        self.name = 'pixel_sort'
        self.axis = axis

    def apply(self, canvas: Canvas, t: float = 0, dt: float = 0):
        w, h = canvas.width, canvas.height
        if self.axis == 'x':
            for y in range(h):
                row = [(canvas.buffer[y][x].fg, x) for x in range(w) if canvas.buffer[y][x].fg]
                row.sort(key=lambda p: p[0].luminance if p[0] else 0, reverse=True)
                sorted_fgs = [p[0] for p in row]
                for x in range(w):
                    cell = canvas.buffer[y][x]
                    if cell.fg and sorted_fgs:
                        cell.fg = sorted_fgs.pop(0)
        else:
            for x in range(w):
                col = [(canvas.buffer[y][x].fg, y) for y in range(h) if canvas.buffer[y][x].fg]
                col.sort(key=lambda p: p[0].luminance if p[0] else 0, reverse=True)
                sorted_fgs = [p[0] for p in col]
                for y in range(h):
                    cell = canvas.buffer[y][x]
                    if cell.fg and sorted_fgs:
                        cell.fg = sorted_fgs.pop(0)


class Crystallize(Shader):
    def __init__(self, cell_size: int = 8, seed: int = 42):
        self.name = 'crystallize'
        self.cell_size = cell_size
        self.seed = seed

    def apply(self, canvas: Canvas, t: float = 0, dt: float = 0):
        w, h = canvas.width, canvas.height
        cs = self.cell_size
        rng = random.Random(self.seed)
        points = {}
        for gy in range(-1, h // cs + 2):
            for gx in range(-1, w // cs + 2):
                rng = random.Random(self.seed + gx * 1000 + gy * 100000)
                ox = rng.uniform(0, cs)
                oy = rng.uniform(0, cs)
                points[(gx, gy)] = (gx * cs + ox, gy * cs + oy)
        for y in range(h):
            for x in range(w):
                best_d = float('inf')
                best_color = None
                for (gx, gy), (px, py) in points.items():
                    d = math.hypot(x - px, y - py)
                    if d < best_d:
                        best_d = d
                        sx = int(round(px))
                        sy = int(round(py))
                        if 0 <= sx < w and 0 <= sy < h:
                            cell = canvas.buffer[sy][sx]
                            if cell.fg:
                                best_color = cell.fg
                if best_color:
                    canvas.buffer[y][x].fg = best_color
                    canvas.buffer[y][x].char = '@'
                    canvas.buffer[y][x].bg = None


class ASCIIRemap(Shader):
    def __init__(self, invert: bool = False, use_bg: bool = False):
        self.name = 'ascii_remap'
        self.invert = invert
        self.use_bg = use_bg

    def apply(self, canvas: Canvas, t: float = 0, dt: float = 0):
        chars = SHADE_CHARS[::-1] if self.invert else SHADE_CHARS
        for y in range(canvas.height):
            for x in range(canvas.width):
                cell = canvas.buffer[y][x]
                src = cell.bg if self.use_bg else cell.fg
                if src:
                    lum = src.luminance / 255
                    idx = int(lum * (len(chars) - 1))
                    cell.char = chars[idx]
                elif not self.use_bg:
                    cell.char = ' '


class ChannelShift(Shader):
    def __init__(self, r_shift: int = 0, g_shift: int = 0, b_shift: int = 0):
        self.name = 'channel_shift'
        self.r_shift = r_shift
        self.g_shift = g_shift
        self.b_shift = b_shift

    def apply(self, canvas: Canvas, t: float = 0, dt: float = 0):
        w, h = canvas.width, canvas.height
        buf = [[Cell() for _ in range(w)] for _ in range(h)]
        for y in range(h):
            for x in range(w):
                c = canvas.buffer[y][x]
                buf[y][x] = Cell(c.char, c.fg, c.bg, c.z)
        for y in range(h):
            for x in range(w):
                cell = canvas.buffer[y][x]
                r_src = buf[y][max(0, min(w - 1, x + self.r_shift))].fg
                g_src = buf[y][max(0, min(w - 1, x + self.g_shift))].fg
                b_src = buf[y][max(0, min(w - 1, x + self.b_shift))].fg
                r = r_src.r if r_src else (cell.fg.r if cell.fg else 0)
                g = g_src.g if g_src else (cell.fg.g if cell.fg else 0)
                b = b_src.b if b_src else (cell.fg.b if cell.fg else 0)
                cell.fg = Color(r, g, b)


class Kaleidoscope(Shader):
    def __init__(self, segments: int = 8):
        self.name = 'kaleidoscope'
        self.segments = segments

    def apply(self, canvas: Canvas, t: float = 0, dt: float = 0):
        w, h = canvas.width, canvas.height
        buf = [[Cell() for _ in range(w)] for _ in range(h)]
        for y in range(h):
            for x in range(w):
                c = canvas.buffer[y][x]
                buf[y][x] = Cell(c.char, c.fg, c.bg, c.z)
        cx, cy = w / 2, h / 2
        for y in range(h):
            for x in range(w):
                dx, dy = x - cx, y - cy
                d = math.hypot(dx, dy)
                if d < 1:
                    continue
                angle = math.atan2(dy, dx)
                seg_angle = 2 * math.pi / self.segments
                mirrored_angle = angle % seg_angle
                if int(angle / seg_angle) % 2 == 1:
                    mirrored_angle = seg_angle - mirrored_angle
                sx = int(cx + d * math.cos(mirrored_angle))
                sy = int(cy + d * math.sin(mirrored_angle))
                if 0 <= sx < w and 0 <= sy < h:
                    src = buf[sy][sx]
                    canvas.buffer[y][x].fg = src.fg
                    canvas.buffer[y][x].bg = src.bg
                    canvas.buffer[y][x].char = src.char


class Warp(Shader):
    def __init__(self, time_scale: float = 0.5):
        self.name = 'warp'
        self.time_scale = time_scale

    def apply(self, canvas: Canvas, t: float = 0, dt: float = 0):
        w, h = canvas.width, canvas.height
        buf = [[Cell() for _ in range(w)] for _ in range(h)]
        for y in range(h):
            for x in range(w):
                c = canvas.buffer[y][x]
                buf[y][x] = Cell(c.char, c.fg, c.bg, c.z)
        for y in range(h):
            for x in range(w):
                nx = x + 3 * math.sin(y * 0.1 + t * self.time_scale) + 2 * math.cos(x * 0.05 + t * 0.3)
                ny = y + 2 * math.cos(x * 0.1 + t * self.time_scale * 0.7) + 3 * math.sin(y * 0.05 + t * 0.5)
                sx, sy = int(nx), int(ny)
                if 0 <= sx < w and 0 <= sy < h:
                    src = buf[sy][sx]
                    if src.fg:
                        canvas.buffer[y][x].fg = src.fg
                        canvas.buffer[y][x].bg = src.bg
                        canvas.buffer[y][x].char = src.char


class VHSGlitch(Shader):
    def __init__(self, intensity: float = 0.1):
        self.name = 'vhs_glitch'
        self.intensity = intensity
        self._phase = 0

    def apply(self, canvas: Canvas, t: float = 0, dt: float = 0):
        w, h = canvas.width, canvas.height
        self._phase += dt
        for y in range(h):
            if random.random() < self.intensity:
                shift = random.randint(-3, 3)
                offset = random.randint(0, max(0, int(self.intensity * 20)))
                if offset > 0 and y + offset < h:
                    for x in range(w):
                        src = canvas.buffer[y + offset][x]
                        canvas.buffer[y][x].fg = src.fg
                        canvas.buffer[y][x].bg = src.bg
                        canvas.buffer[y][x].char = src.char if x + shift < w else ' '
                else:
                    for x in range(w):
                        c = canvas.buffer[y][x]
                        if c.fg:
                            c.fg = Color(255 - c.fg.r, c.fg.g, c.fg.b)
            if random.random() < self.intensity * 0.5:
                row_start = random.randint(0, w - 10)
                row_len = random.randint(5, 15)
                for x in range(row_start, min(w, row_start + row_len)):
                    canvas.buffer[y][x].fg = Color(
                        random.randint(100, 255),
                        random.randint(100, 255),
                        random.randint(100, 255),
                    )


SCANLINES = ' ░▒▓█'


class Ripple(Shader):
    def __init__(self, amplitude: float = 1.5, frequency: float = 0.5, speed: float = 1.0):
        self.name = 'ripple'
        self.amplitude = amplitude
        self.frequency = frequency
        self.speed = speed

    def apply(self, canvas: Canvas, t: float = 0, dt: float = 0):
        w, h = canvas.width, canvas.height
        cx, cy = w / 2, h / 2
        buf = [[Cell() for _ in range(w)] for _ in range(h)]
        for y in range(h):
            for x in range(w):
                c = canvas.buffer[y][x]
                buf[y][x] = Cell(c.char, c.fg, c.bg, c.z)
        for y in range(h):
            for x in range(w):
                d = math.hypot(x - cx, y - cy)
                offset = self.amplitude * math.sin(d * self.frequency - t * self.speed)
                sx = int(x + offset * (x - cx) / max(1, d))
                sy = int(y + offset * (y - cy) / max(1, d))
                if 0 <= sx < w and 0 <= sy < h:
                    src = buf[sy][sx]
                    if src.fg:
                        canvas.buffer[y][x].fg = src.fg
                        canvas.buffer[y][x].bg = src.bg
                        canvas.buffer[y][x].char = src.char
