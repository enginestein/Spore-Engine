from __future__ import annotations
import math, random
from typing import Optional
from ..core.color import Color, BLACK, WHITE


def shake(canvas, intensity: float = 2.0, seed: int = 0):
    rng = random.Random(seed)
    ox = rng.uniform(-intensity, intensity)
    oy = rng.uniform(-intensity, intensity)
    buffer = [[None] * canvas.w for _ in range(canvas.h)]
    for y in range(canvas.h):
        for x in range(canvas.w):
            sx = x + int(ox)
            sy = y + int(oy)
            if 0 <= sx < canvas.w and 0 <= sy < canvas.h:
                buffer[y][x] = canvas.buffer[sy][sx]
    for y in range(canvas.h):
        for x in range(canvas.w):
            if buffer[y][x] is not None:
                c = canvas.buffer[y][x]
                src = buffer[y][x]
                c.char, c.fg, c.bg, c.z = src.char, src.fg, src.bg, src.z


def fade_overlay(canvas, alpha: float,
                 color: Color = BLACK, z: float = 1000):
    a = max(0, min(1, alpha))
    for y in range(canvas.h):
        for x in range(canvas.w):
            c = canvas.buffer[y][x]
            if c.fg is not None and a > 0:
                c.fg = c.fg.blend(color, a)
            if c.bg is not None and a > 0:
                c.bg = c.bg.blend(color, a)


def flash(canvas, alpha: float, z: float = 1000):
    a = max(0, min(1, alpha))
    if a <= 0:
        return
    col = Color(int(255 * a), int(255 * a), int(255 * a))
    for y in range(canvas.h):
        for x in range(canvas.w):
            c = canvas.buffer[y][x]
            if c.fg is not None:
                c.fg = c.fg.blend(WHITE, a)
            if c.bg is not None:
                c.bg = c.bg.blend(WHITE, a)


def crossfade(dst, src, alpha: float):
    a = max(0, min(1, alpha))
    for y in range(min(dst.h, src.h)):
        for x in range(min(dst.w, src.w)):
            dc = dst.buffer[y][x]
            sc = src.buffer[y][x]
            if sc.fg is None: continue
            if dc.fg is None:
                dc.fg = sc.fg
                dc.bg = sc.bg if sc.bg else None
                dc.char = sc.char
                continue
            dc.fg = dc.fg.blend(sc.fg, a) if dc.fg else sc.fg
            if sc.bg:
                dc.bg = dc.bg.blend(sc.bg, a) if dc.bg else sc.bg
            dc.char = sc.char if a > 0.5 else dc.char


def color_overlay(canvas, color: Color, alpha: float = 0.3, z: float = 1000):
    a = max(0, min(1, alpha))
    for y in range(canvas.h):
        for x in range(canvas.w):
            c = canvas.buffer[y][x]
            if c.fg is not None:
                c.fg = c.fg.blend(color, a)


def vignette(canvas, radius: Optional[float] = None, z: float = 1000):
    cx, cy = canvas.w / 2, canvas.h / 2
    max_d = math.hypot(cx, cy)
    r = radius or max_d
    for y in range(canvas.h):
        for x in range(canvas.w):
            d = math.hypot(x - cx, y - cy) / r
            if d > 1: d = 1
            c = canvas.buffer[y][x]
            if c.fg is not None:
                c.fg = c.fg.mul(1 - d * 0.5)


def scanlines(canvas, intensity: float = 0.3):
    for y in range(0, canvas.h, 2):
        for x in range(canvas.w):
            c = canvas.buffer[y][x]
            if c.fg is not None:
                c.fg = c.fg.mul(1 - intensity)
