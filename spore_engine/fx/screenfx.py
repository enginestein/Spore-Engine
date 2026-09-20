from __future__ import annotations
import math, random
from typing import Optional
from ..core.color import Color, BLACK, WHITE
from ..core.util import clamp


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


class ScreenFX:
    """Timer-driven screen effects stored per-frame.

        fx = ScreenFX()
        fx.add_shake(2.5)          # on an explosion
        fx.add_flash(0.6)
        ...
        fx.tick(dt)                # decay timers each frame
        fx.apply(canvas, seed=int(t * 100))   # after the scene renders
    """

    def __init__(self):
        self.shake_t = 0.0
        self.shake_p = 0.0
        self.shake_dur = 1.1
        self.flash_t = 0.0
        self.flash_p = 0.0
        self.flash_dur = 0.5
        self.fade_t = 0.0
        self.fade_dur = 1.0
        self.fade_color = Color(0, 0, 0)
        self.fade_in = False
        self._fade_started = False

    def add_shake(self, power: float, duration: float = 1.1):
        self.shake_t = max(self.shake_t, duration)
        self.shake_p = max(self.shake_p, min(3.5, power))
        self.shake_dur = duration

    def add_flash(self, alpha: float, duration: float = 0.5):
        self.flash_t = max(self.flash_t, duration)
        self.flash_p = max(self.flash_p, min(1.0, alpha))
        self.flash_dur = duration

    def add_fade(self, color: Color = BLACK, duration: float = 1.0,
                 inverse: bool = False):
        self.fade_dur = max(0.01, duration)
        self.fade_t = 0.0
        self.fade_color = color
        self.fade_in = inverse
        self._fade_started = True

    @property
    def active(self) -> bool:
        return (self.shake_t > 0 or self.flash_t > 0
                or (self._fade_started and 0 <= self.fade_t < 1))

    def tick(self, dt: float):
        if self.shake_t > 0:
            self.shake_t -= dt
        if self.flash_t > 0:
            self.flash_t -= dt
        if 0 <= self.fade_t < 1:
            self.fade_t += dt / self.fade_dur

    def apply(self, canvas, seed: int = 0, z: float = 1000):
        if self.shake_t > 0:
            p = self.shake_p * min(1.0, self.shake_t / self.shake_dur)
            if p > 0.01:
                shake(canvas, p, seed=seed)
        if self.flash_t > 0:
            a = self.flash_p * min(1.0, self.flash_t / self.flash_dur)
            if a > 0.01:
                flash(canvas, a, z=z)
        if self.fade_dur and self._fade_started:
            a = clamp(self.fade_t, 0.0, 1.0)
            if self.fade_in:
                a = 1 - a
            if 0 < a < 1:
                fade_overlay(canvas, a, self.fade_color, z=z)
