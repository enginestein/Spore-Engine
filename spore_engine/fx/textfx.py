from __future__ import annotations
import math
import random
from ..core.canvas import Canvas
from ..core.glyphs import SHADE_CHARS
from ..core.color import Color, Gradient, WHITE


#: Re-exported from core.glyphs so the ramp is defined once.
SHADE = SHADE_CHARS


def glitch_text(canvas: Canvas, x: int, y: int, text: str, t: float,
                fg: Color | None = None):
    color = fg or WHITE
    for i, ch in enumerate(text):
        offset = 0
        if random.random() < 0.03:
            ch = random.choice('!@#$%^&*()_+{}|:"<>?`~')
        if random.random() < 0.02:
            offset = random.choice([-1, 1])
        if random.random() < 0.01:
            color = Color.from_hsv(random.random(), 1, 1)
        canvas.set_pixel(x + i, y + offset, ch, color)


def typewriter_text(canvas: Canvas, x: int, y: int, text: str, t: float,
                    chars_per_sec: float = 10, fg: Color | None = None,
                    cursor: bool = True):
    color = fg or WHITE
    visible = min(len(text), int(t * chars_per_sec))
    for i in range(visible):
        canvas.set_pixel(x + i, y, text[i], color)
    if cursor and visible < len(text):
        if int(t * 4) % 2:
            canvas.set_pixel(x + visible, y, '█', color)


def sine_text(canvas: Canvas, x: int, y: int, text: str, t: float,
              amplitude: float = 2, frequency: float = 2, fg: Color | None = None):
    color = fg or WHITE
    for i, ch in enumerate(text):
        offset = round(math.sin(t * frequency + i * 0.5) * amplitude)
        canvas.set_pixel(x + i, y + offset, ch, color)


def rainbow_text(canvas: Canvas, x: int, y: int, text: str, t: float,
                 saturation: float = 0.9, value: float = 1.0):
    for i, ch in enumerate(text):
        hue = (i / len(text) + t * 0.1) % 1.0
        canvas.set_pixel(x + i, y, ch, Color.from_hsv(hue, saturation, value))


def gradient_text(canvas: Canvas, x: int, y: int, text: str, t: float,
                  grad: Gradient | None = None):
    g = grad or Gradient(Color(255, 0, 0), Color(255, 255, 0), Color(0, 255, 255))
    for i, ch in enumerate(text):
        t_ = i / max(1, len(text) - 1)
        canvas.set_pixel(x + i, y, ch, g.at(t_))


def scroll_text(canvas: Canvas, text: str, t: float,
                height: int = 0, speed: float = 2, fg: Color | None = None,
                bg: Color | None = None):
    color = fg or WHITE
    h = height or canvas.height
    offset = int(t * speed) % (len(text) + canvas.width)
    for i in range(canvas.width):
        idx = (i + offset) % len(text)
        canvas.set_pixel(i, h - 1, text[idx], color, bg)


def star_wars_crawl(canvas: Canvas, lines: list[str], t: float,
                    fg: Color | None = None):
    col = fg or Color(255, 200, 50)
    for i, line in enumerate(lines):
        y = canvas.height - 1 - int(t * 3 + i * 2)
        if 0 <= y < canvas.height:
            x = (canvas.width - len(line)) // 2
            scale = 1.0 - (canvas.height - y) / canvas.height
            if scale > 0:
                c = col.mul(scale)
                canvas.draw_text(x, y, line, c)


def matrix_code_rain(canvas: Canvas, t: float, fg: Color | None = None):
    col = fg or Color(0, 255, 0)
    for x in range(canvas.width):
        seed = x * 13 + int(t * 10)
        rng = random.Random(seed)
        y = int((t * 2 + x * 0.7) % (canvas.height + 5)) - 5
        for i in range(rng.randint(3, 8)):
            dy = y - i
            if 0 <= dy < canvas.height:
                ch = chr(0x30A0 + rng.randint(0, 95))
                if i == 0:
                    canvas.set_pixel(x, dy, ch, Color(200, 255, 200))
                else:
                    canvas.set_pixel(x, dy, ch, col.mul(1 - i * 0.12))


def wave_text(canvas: Canvas, x: int, y: int, text: str, t: float,
              amplitude: float = 3, fg: Color | None = None):
    color = fg or WHITE
    chars = list(text)
    n = len(chars)
    for i in range(n):
        ch = chars[i]
        if ch == ' ':
            continue
        wave = math.sin(t * 3 + i * 0.8) * amplitude
        hue = (i / n + t * 0.05) % 1.0
        c = color if fg else Color.from_hsv(hue, 0.8, 1.0)
        canvas.set_pixel(x + i, y + round(wave), ch, c)


def fire_text(canvas: Canvas, x: int, y: int, text: str, t: float):
    for i, ch in enumerate(text):
        flicker = random.random() * 0.3 + 0.7
        r = min(255, int(255 * flicker))
        g = min(255, int(180 * flicker * flicker))
        b = min(100, int(60 * flicker * flicker * flicker))
        canvas.set_pixel(x + i, y, ch, Color(r, g, b))


def zoom_text(canvas: Canvas, text: str, t: float,
              fg: Color | None = None):
    color = fg or WHITE
    cx, cy = canvas.width // 2, canvas.height // 2
    scale = 1 + math.sin(t) * 2
    for i, ch in enumerate(text):
        px = cx + (i - len(text) / 2) * scale
        py = cy
        if 0 <= px < canvas.width:
            canvas.set_pixel(round(px), round(py), ch, color)


def bounce_text(canvas: Canvas, x: int, y: int, text: str, t: float,
                fg: Color | None = None):
    color = fg or WHITE
    for i, ch in enumerate(text):
        ty = y + abs(math.sin(t * 2 + i * 0.5)) * 3
        canvas.set_pixel(x + i, round(ty), ch, color)
