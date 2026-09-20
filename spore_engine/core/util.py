from __future__ import annotations
import math
from typing import Iterable
from .canvas import SHADE_CHARS
from .color import Color, Gradient


def clamp(value, lo, hi):
    return max(lo, min(hi, value))


def lerp(a, b, t):
    return a + (b - a) * t


def ir(x) -> int:
    """round to nearest int (safe on floats and vectors)."""
    return int(round(x))


def ramp(v: float, chars: str | None = None) -> str:
    """Map 0..1 to a single shade glyph (full ramp ' .:-=+*#%@')."""
    v = clamp(v, 0.0, 1.0)
    cc = chars or SHADE_CHARS
    return cc[int(v * (len(cc) - 1))]


def phase(t: float, speed: float = 1.0, offset: float = 0.0) -> float:
    """Saw wave 0..1 repeating: ``phase(t, 2pi/4)`` is a 4s loop."""
    return ((t * speed + offset) % 1.0 + 1.0) % 1.0


def wave(t: float, speed: float = 1.0, offset: float = 0.0,
         lo: float = 0.0, hi: float = 1.0) -> float:
    """Smooth sine oscillation between ``lo`` and ``hi``."""
    return lo + (hi - lo) * 0.5 * (1 + math.sin(t * speed + offset))


def osc(t: float, period: float = 1.0, offset: float = 0.0,
        lo: float = 0.0, hi: float = 1.0) -> float:
    """Sine oscillation with a period in seconds (alias of wave)."""
    return wave(t, 2 * math.pi / period, offset, lo, hi)


def in_bounds(x, y, w, h) -> bool:
    return 0 <= x < w and 0 <= y < h


def approach(value, target, step):
    if value < target:
        return min(target, value + step)
    return max(target, value - step)


def move_toward(value, target, step):
    return approach(value, target, step)


def bounce(t: float, period: float = 1.0, offset: float = 0.0,
           lo: float = 0.0, hi: float = 1.0) -> float:
    """Triangle wave: up-down repeat over a period in seconds."""
    tt = ((t + offset * period) % period) / period
    return lo + (hi - lo) * (1 - abs(2 * tt - 1))


def dist(ax, ay, bx, by) -> float:
    return math.hypot(ax - bx, ay - by)


def lerp_color(c1: Color, c2: Color, t: float) -> Color:
    if c1 is None:
        return c2
    if c2 is None:
        return c1
    t = clamp(t, 0.0, 1.0)
    return Color(
        int(c1.r + (c2.r - c1.r) * t),
        int(c1.g + (c2.g - c1.g) * t),
        int(c1.b + (c2.b - c1.b) * t),
    )


def smoothstep(t: float) -> float:
    t = clamp(t, 0.0, 1.0)
    return t * t * (3 - 2 * t)


def ramp_color(t: float, *colors: Color) -> Color:
    """Sample a Colour across a list of stops (t 0..1)."""
    n = len(colors)
    if n == 0:
        return Color(0, 0, 0)
    if n == 1:
        return colors[0]
    t = clamp(t, 0.0, 1.0)
    f = t * (n - 1)
    i = min(n - 2, int(f))
    return lerp_color(colors[i], colors[i + 1], f - i)