from __future__ import annotations
import math
from ..core.canvas import Canvas
from ..core.glyphs import SHADE_CHARS
from ..core.color import Color, Gradient


#: Re-exported from core.glyphs so the ramp is defined once.
SHADE = SHADE_CHARS


def canvas_from_text(text: str) -> Canvas:
    lines = text.rstrip('\n').split('\n')
    h = len(lines)
    w = max(len(l) for l in lines) if lines else 0
    if w < 1 or h < 1:
        # Canvas rejects a zero dimension, and it cannot tell the caller
        # whether the empty string or a zero-width line was the mistake.
        raise ValueError('text must contain at least one visible character')
    c = Canvas(w, h)
    for y, line in enumerate(lines):
        for x, ch in enumerate(line):
            c.set_pixel(x, y, ch)
    return c


def scale_canvas(src: Canvas, new_w: int, new_h: int) -> Canvas:
    dst = Canvas(new_w, new_h)
    for y in range(new_h):
        for x in range(new_w):
            sx = int(x / new_w * src.w)
            sy = int(y / new_h * src.h)
            cell = src.buffer[sy][sx]
            dst.set_pixel(x, y, cell.char, cell.fg, cell.bg)
    return dst


def canvas_to_ascii(canvas: Canvas, width: int,
                    use_color: bool = True) -> str:
    aspect = canvas.h / canvas.w
    h = max(1, int(width * aspect * 0.5))
    scaled = scale_canvas(canvas, width, h)
    lines = []
    for y in range(h):
        line = ''
        for x in range(width):
            cell = scaled.buffer[y][x]
            char = cell.char if cell.char and cell.char != ' ' else ' '
            if use_color and cell.fg:
                line += cell.fg.ansi_fg() + char + '\033[0m'
            else:
                line += char
        lines.append(line)
    return '\n'.join(lines)


class ImageConverter:
    def __init__(self, width: int, height: int):
        self.w = width
        self.h = height
        self.pixels: list[list[Color | None]] = [[None] * width for _ in range(height)]
        self.chars: list[list[str]] = [[' '] * width for _ in range(height)]

    def from_rgb(self, data: list[list[tuple[int, int, int]]]):
        for y in range(min(len(data), self.h)):
            for x in range(min(len(data[0]), self.w)):
                r, g, b = data[y][x]
                self.pixels[y][x] = Color(r, g, b)

    def apply_shade(self, char_map: str = SHADE):
        for y in range(self.h):
            for x in range(self.w):
                c = self.pixels[y][x]
                if c:
                    lum = c.luminance / 255
                    ci = int(lum * (len(char_map) - 1))
                    self.chars[y][x] = char_map[ci]

    def apply_edge_detect(self, threshold: float = 0.3):
        for y in range(1, self.h - 1):
            for x in range(1, self.w - 1):
                gx, gy = 0, 0
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        c = self.pixels[y + dy][x + dx]
                        lum = c.luminance if c else 0
                        sobel_x = (-1, 0, 1, -2, 0, 2, -1, 0, 1)
                        sobel_y = (-1, -2, -1, 0, 0, 0, 1, 2, 1)
                        idx = (dy + 1) * 3 + (dx + 1)
                        gx += lum * sobel_x[idx]
                        gy += lum * sobel_y[idx]
                mag = math.sqrt(gx * gx + gy * gy) / 1024
                self.chars[y][x] = '@' if mag > threshold else ' '

    def render(self, canvas: Canvas, ox: int = 0, oy: int = 0):
        for y in range(min(self.h, canvas.height - oy)):
            for x in range(min(self.w, canvas.width - ox)):
                if self.chars[y][x] != ' ' or self.pixels[y][x]:
                    canvas.set_pixel(x + ox, y + oy, self.chars[y][x], self.pixels[y][x])


def gradient_canvas(w: int, h: int, grad: Gradient,
                    horizontal: bool = True) -> Canvas:
    c = Canvas(w, h)
    for y in range(h):
        for x in range(w):
            t = x / w if horizontal else y / h
            ci = int(t * 9)
            c.set_pixel(x, y, SHADE[ci], grad.at(t))
    return c
