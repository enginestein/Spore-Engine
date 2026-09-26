from __future__ import annotations
from dataclasses import dataclass

__all__ = [
    'BLACK',
    'BLUE',
    'CYAN',
    'DIM',
    'GREEN',
    'MAGENTA',
    'ORANGE',
    'PALETTES',
    'PINK',
    'PURPLE',
    'RED',
    'WHITE',
    'YELLOW',
    'Color',
    'Gradient',
    'fast_color',
]


def _channel(value: int | float, name: str) -> int:
    """Coerce one colour channel to a valid 0-255 int.

    ``bool`` is rejected explicitly (``True`` would silently become 1) and
    non-integral floats are rejected rather than silently truncated, because
    ``Color(1.5, 0, 0).hex`` used to raise an opaque ``ValueError`` much later
    inside a format string. Out-of-range ints are clamped, which is the
    documented and long-relied-on behaviour.
    """
    if isinstance(value, bool):
        raise TypeError(
            f'Color channel {name!r} must be a number, got bool '
            f'({value!r}); pass 0 or 1 explicitly')
    if isinstance(value, float):
        if value != int(value):
            raise ValueError(
                f'Color channel {name!r} must be a whole number in 0-255, '
                f'got {value!r}')
        value = int(value)
    elif not isinstance(value, int):
        raise TypeError(
            f'Color channel {name!r} must be an int, got '
                f'{type(value).__name__} ({value!r})')
    return max(0, min(255, value))


@dataclass(frozen=True)
class Color:
    """An immutable 8-bit-per-channel RGB colour.

    Channels are clamped to 0-255 on construction, so ``Color(300, -5, 0)`` is
    ``Color(255, 0, 0)``. Non-integral floats and non-numeric values are
    rejected with a clear error instead of failing later inside a format
    string.

    Equality and hashing are by value, so colours can be used as dict keys or
    put in sets - which is what makes the incremental renderer fast.
    """

    r: int
    g: int
    b: int

    def __post_init__(self):
        object.__setattr__(self, 'r', _channel(self.r, 'r'))
        object.__setattr__(self, 'g', _channel(self.g, 'g'))
        object.__setattr__(self, 'b', _channel(self.b, 'b'))

    def ansi_fg(self, depth: int = 3) -> str:
        """Foreground SGR sequence. ``depth`` 3 = truecolor, 2 = 256 colour,
        1/0 = plain (the caller is expected to have degraded already)."""
        if depth >= 3:
            return f'\033[38;2;{self.r};{self.g};{self.b}m'
        if depth == 2:
            return f'\033[38;5;{self.to_ansi_256()}m'
        return ''

    def ansi_bg(self, depth: int = 3) -> str:
        """Background SGR sequence. See :meth:`ansi_fg` for ``depth``."""
        if depth >= 3:
            return f'\033[48;2;{self.r};{self.g};{self.b}m'
        if depth == 2:
            return f'\033[48;5;{self.to_ansi_256()}m'
        return ''

    @property
    def hex(self) -> str:
        return f'#{self.r:02x}{self.g:02x}{self.b:02x}'

    @property
    def luminance(self) -> float:
        """Rec. 601 perceived brightness, 0 (black) to 255 (white)."""
        return 0.299 * self.r + 0.587 * self.g + 0.114 * self.b

    @staticmethod
    def reset() -> str:
        """The SGR sequence that clears all attributes. The canonical
        definition of this string; the renderer and the UI toolkit both use it
        instead of hardcoding ``'\\033[0m'``."""
        return '\033[0m'

    @classmethod
    def from_hex(cls, s: str) -> Color:
        """Parse ``'#rrggbb'`` or ``'rrggbb'`` (the ``#`` is optional).

        Raises ``ValueError`` with an explicit message on a wrong length or a
        non-hex digit, instead of the bare ``int()`` failure that a short
        string used to produce.
        """
        t = s.strip()
        if t.startswith('#'):
            t = t[1:]
        if len(t) != 6:
            raise ValueError(
                f'expected 6 hex digits for a colour, got {len(t)} '
                f'({s!r}); use the form "#rrggbb"')
        try:
            return cls(int(t[0:2], 16), int(t[2:4], 16), int(t[4:6], 16))
        except ValueError:
            raise ValueError(
                f'{s!r} is not a valid hex colour; use the form "#rrggbb"') from None

    @classmethod
    def from_hsv(cls, h: float, s: float = 1, v: float = 1) -> Color:
        h = h % 1.0
        s = max(0, min(1, s))
        v = max(0, min(1, v))
        i = int(h * 6)
        f = h * 6 - i
        p = v * (1 - s)
        q = v * (1 - f * s)
        t = v * (1 - (1 - f) * s)
        r, g, b = [(v, t, p), (q, v, p), (p, v, t),
                    (p, q, v), (t, p, v), (v, p, q)][i % 6]
        return cls(int(r * 255), int(g * 255), int(b * 255))

    @classmethod
    def from_uv(cls, u: float, v: float) -> Color:
        """Two-axis colour lookup: ``u`` drives red, ``v`` drives green, and
        blue is pinned to a mid tone (128). Intended for procedural ramps
        where the third axis is unused."""
        return cls(int(u * 255), int(v * 255), 128)

    def lerp(self, other: Color, t: float) -> Color:
        """Linearly interpolate towards ``other``; ``t`` is clamped to 0-1."""
        t = max(0, min(1, t))
        return Color(
            int(self.r + (other.r - self.r) * t),
            int(self.g + (other.g - self.g) * t),
            int(self.b + (other.b - self.b) * t),
        )

    def mul(self, factor: float) -> Color:
        factor = max(0, min(2, factor))
        return Color(int(self.r * factor), int(self.g * factor), int(self.b * factor))

    def blend(self, other: Color, alpha: float) -> Color:
        return self.lerp(other, alpha)

    def to_hsv(self) -> tuple[float, float, float]:
        r, g, b = self.r / 255, self.g / 255, self.b / 255
        mx = max(r, g, b)
        mn = min(r, g, b)
        d = mx - mn
        if mx == mn:
            h = 0.0
        elif mx == r:
            h = ((g - b) / d) % 6
        elif mx == g:
            h = (b - r) / d + 2
        else:
            h = (r - g) / d + 4
        h /= 6
        s = 0 if mx == 0 else d / mx
        v = mx
        return (h % 1.0, s, v)

    def to_ansi_256(self) -> int:
        """Nearest xterm-256 palette index.

        Greys use the 232-255 ramp (24 steps) and hues the 6x6x6 cube at
        16-231. The result is always in 0-255; the grey branch used to return
        257 for pure white because the divisor was too small.
        """
        if self.r == self.g == self.b:
            # 232..255 inclusive is 24 steps spanning 0..255.
            return 232 + min(23, int(self.r * 24 / 256))
        r = min(5, round(self.r / 51))
        g = min(5, round(self.g / 51))
        b = min(5, round(self.b / 51))
        return 16 + r * 36 + g * 6 + b


PALETTES = {
    'fire': [Color.from_hex(c) for c in ['#1a0000', '#3d0000', '#7f0000', '#bf0000',
                                           '#ff0000', '#ff4000', '#ff8000', '#ffbf00',
                                           '#ffff00', '#ffff80', '#ffffff']],
    'ice': [Color.from_hex(c) for c in ['#000033', '#000066', '#000099', '#0000cc',
                                          '#0066ff', '#0099ff', '#00ccff', '#66ffff',
                                          '#99ffff', '#ccffff', '#ffffff']],
    'neon': [Color.from_hex(c) for c in ['#ff00ff', '#ff00cc', '#ff0099', '#ff0066',
                                           '#ff00ff', '#cc00ff', '#9900ff', '#6600ff',
                                           '#3300ff', '#0033ff', '#0066ff']],
    'ocean': [Color.from_hex(c) for c in ['#001a33', '#003366', '#005299', '#0070cc',
                                            '#0088ff', '#00aaff', '#00ccff', '#33ddff',
                                            '#66eeff', '#99ffff', '#ccffff']],
    'forest': [Color.from_hex(c) for c in ['#001a00', '#003300', '#005200', '#007000',
                                             '#008800', '#00aa00', '#33bb33', '#66cc66',
                                             '#99dd99', '#bbeeaa', '#ddffcc']],
    'sunset': [Color.from_hex(c) for c in ['#1a0033', '#330066', '#520099', '#7000b0',
                                             '#8f00b0', '#bf0080', '#df4060', '#ff8040',
                                             '#ffbf20', '#ffdf40', '#ffff80']],
    'grayscale': [Color(i, i, i) for i in range(0, 256, 25)],
}


class Gradient:
    """An ordered list of colour stops sampled by a 0-1 position.

    A gradient needs at least one stop - an empty ``Gradient()`` used to defer
    its failure to the first :meth:`at` call, where it raised an opaque
    ``IndexError`` from deep inside a render loop.

        Gradient(BLACK, RED, WHITE).at(0.5)   # mid grey-ish red
    """

    def __init__(self, *colors: Color):
        if not colors:
            raise ValueError(
                'Gradient() needs at least one colour stop; '
                'pass e.g. Gradient(BLACK, WHITE)')
        self.colors = colors

    def __len__(self) -> int:
        return len(self.colors)

    def at(self, t: float) -> Color:
        """Sample at ``t`` (clamped to 0-1), interpolating between the two
        nearest stops. This is the engine's only multi-stop colour sampler;
        ``util.ramp_color`` delegates here."""
        t = max(0, min(1, t))
        n = len(self.colors)
        if n == 1:
            return self.colors[0]
        idx = t * (n - 1)
        i = int(idx)
        if i >= n - 1:
            return self.colors[-1]
        return self.colors[i].lerp(self.colors[i + 1], idx - i)

    @classmethod
    def from_palette(cls, name: str) -> Gradient:
        """Build a gradient from a name in :data:`PALETTES`.

        Raises ``KeyError`` listing the valid names rather than an opaque
        ``KeyError: 'ocen'``."""
        try:
            stops = PALETTES[name]
        except KeyError:
            raise KeyError(
                f'unknown palette {name!r}; available: '
                f'{", ".join(sorted(PALETTES))}') from None
        return cls(*stops)

    def __repr__(self) -> str:
        return f'Gradient({len(self.colors)} stops)'


BLACK = Color(0, 0, 0)
WHITE = Color(255, 255, 255)
RED = Color(255, 0, 0)
GREEN = Color(0, 255, 0)
BLUE = Color(0, 0, 255)
YELLOW = Color(255, 255, 0)
CYAN = Color(0, 255, 255)
MAGENTA = Color(255, 0, 255)
ORANGE = Color(255, 128, 0)
PURPLE = Color(160, 32, 240)
PINK = Color(255, 192, 203)
DIM = Color(64, 64, 64)

_new = object.__new__
_set = object.__setattr__


def fast_color(r: int, g: int, b: int) -> Color:
    """A :class:`Color` from three ints, skipping the validating constructor.

    ``Color.__post_init__`` rejects ``bool``, rejects non-integral floats and
    clamps, which is right for a value that might come from anywhere and wrong
    for one that a hot loop has just clipped itself. A full-screen surface holds
    one ``Color`` per cell, and at 20k cells the difference between this and
    ``Color(r, g, b)`` is several milliseconds a frame.

    The caller is responsible for the range: pass ints in 0-255. Anything else
    produces a ``Color`` that breaks its own type contract, which is the one
    thing this function trades away.
    """
    c = _new(Color)
    _set(c, 'r', r)
    _set(c, 'g', g)
    _set(c, 'b', b)
    return c
