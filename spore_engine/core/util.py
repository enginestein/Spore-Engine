"""Small scalar helpers shared by every layer of the engine.

These are the *same objects* everywhere: ``anim`` and ``easy`` re-export them
rather than defining their own, so a name like ``clamp`` can never mean two
different things in two subpackages.

``ramp_color`` is a thin alias for :meth:`Gradient.at` - the engine has exactly
one multi-stop colour sampler.
"""

from __future__ import annotations

import math
from typing import TypeVar, Union

from .color import Color, Gradient
from .glyphs import SHADE_CHARS

__all__ = [
    'approach',
    'bounce',
    'clamp',
    'dist',
    'in_bounds',
    'ir',
    'lerp',
    'lerp_color',
    'move_toward',
    'osc',
    'phase',
    'ramp',
    'ramp_color',
    'rows_for_width',
    'smoothstep',
    'wave',
]

T = TypeVar('T', int, float)

Number = Union[int, float]  # noqa: UP007  (runtime alias, must stay Union)


def clamp(value: T, lo: T, hi: T) -> T:
    """Constrain ``value`` to ``[lo, hi]``."""
    return max(lo, min(hi, value))


def lerp(a: float, b: float, t: float) -> float:
    """Linear interpolation. ``t`` is *not* clamped - use :func:`clamp` on it
    first if you need extrapolation control."""
    return a + (b - a) * t


def ir(x: Number) -> int:
    """Round to the nearest int. Works on floats and on anything with
    ``__round__`` (e.g. a :class:`~spore_engine.core.geom.Vec2`)."""
    return round(x)


def ramp(v: float, chars: str | None = None) -> str:
    """Map 0..1 to a single shade glyph.

    ``chars`` defaults to the full ``' .:-=+*#%@'`` ramp. An explicitly empty
    string is an error rather than a silent fallback to the default ramp,
    which is what an empty ``ramp(0.5, '')`` used to do.
    """
    v = clamp(v, 0.0, 1.0)
    cc = SHADE_CHARS if chars is None else chars
    if not cc:
        raise ValueError('ramp() needs at least one shade character')
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
    """Sine oscillation with a period in seconds (alias of :func:`wave`).

    ``period`` must be non-zero; ``0`` used to raise ``ZeroDivisionError`` from
    the division below.
    """
    if period == 0:
        raise ValueError('osc() needs a non-zero period')
    return wave(t, 2 * math.pi / period, offset, lo, hi)


def in_bounds(x: int, y: int, w: int, h: int) -> bool:
    """Whether ``(x, y)`` is inside a ``w`` x ``h`` region."""
    return 0 <= x < w and 0 <= y < h


def approach(value: float, target: float, step: float) -> float:
    """Move ``value`` towards ``target`` by at most ``step``."""
    if value < target:
        return min(target, value + step)
    return max(target, value - step)


def move_toward(value: float, target: float, step: float) -> float:
    """Alias of :func:`approach`, spelled the way game code usually reads."""
    return approach(value, target, step)


def bounce(t: float, period: float = 1.0, offset: float = 0.0,
           lo: float = 0.0, hi: float = 1.0) -> float:
    """Triangle wave: up-down repeat over a period in seconds."""
    if period == 0:
        raise ValueError('bounce() needs a non-zero period')
    tt = ((t + offset * period) % period) / period
    return lo + (hi - lo) * (1 - abs(2 * tt - 1))


def dist(ax: float, ay: float, bx: float, by: float) -> float:
    """Euclidean distance between two 2D points."""
    return math.hypot(ax - bx, ay - by)


def lerp_color(c1: Color | None, c2: Color | None, t: float) -> Color | None:
    """Interpolate between two colours; ``t`` is clamped to 0-1.

    A ``None`` endpoint passes the other through, so this is safe to call on
    optional colours. Delegates to :meth:`Color.lerp`, which is the engine's
    only colour interpolation.
    """
    if c1 is None:
        return c2
    if c2 is None:
        return c1
    return c1.lerp(c2, clamp(t, 0.0, 1.0))


def smoothstep(t: float) -> float:
    """Hermite ease of 0..1, flat at both ends. Clamps ``t`` first."""
    t = clamp(t, 0.0, 1.0)
    return t * t * (3 - 2 * t)


def ramp_color(t: float, *colors: Color) -> Color | None:
    """Sample a list of colour stops at position ``t`` (0..1).

    A thin wrapper over :class:`~spore_engine.core.color.Gradient`, which is
    the engine's only multi-stop sampler. Returns ``None`` for no stops.
    """
    if not colors:
        return None
    return Gradient(*colors).at(t)


def rows_for_width(width: int) -> int:
    """Rows needed to show a ``width``-wide image without stretching it.

    A terminal cell is roughly twice as tall as it is wide
    (:data:`~spore_engine.core.term.CHAR_ASPECT`), so the row count is about
    half the column count. This replaced the same constant duplicated at six
    call sites in the media converters.
    """
    from .term import CHAR_ASPECT
    if width <= 0:
        raise ValueError(f'width must be positive, got {width}')
    return max(1, int(width * CHAR_ASPECT))
