from __future__ import annotations
from dataclasses import dataclass
import math


@dataclass(frozen=True)
class Color:
    r: int
    g: int
    b: int

    def __post_init__(self):
        object.__setattr__(self, 'r', max(0, min(255, self.r)))
        object.__setattr__(self, 'g', max(0, min(255, self.g)))
        object.__setattr__(self, 'b', max(0, min(255, self.b)))

    def ansi_fg(self) -> str:
        return f'\033[38;2;{self.r};{self.g};{self.b}m'

    def ansi_bg(self) -> str:
        return f'\033[48;2;{self.r};{self.g};{self.b}m'

    @property
    def hex(self) -> str:
        return f'#{self.r:02x}{self.g:02x}{self.b:02x}'

    @property
    def luminance(self) -> float:
        return 0.299 * self.r + 0.587 * self.g + 0.114 * self.b

    @staticmethod
    def reset() -> str:
        return '\033[0m'

    @classmethod
    def from_hex(cls, s: str) -> Color:
        s = s.lstrip('#')
        return cls(int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))

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
        return cls(int(u * 255), int(v * 255), 128)

    def lerp(self, other: Color, t: float) -> Color:
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
        if self.r == self.g == self.b:
            return 232 + int(self.r / 10.2)
        r = round(self.r / 51)
        g = round(self.g / 51)
        b = round(self.b / 51)
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
    def __init__(self, *colors: Color):
        self.colors = colors

    def at(self, t: float) -> Color:
        t = max(0, min(1, t))
        if len(self.colors) == 1:
            return self.colors[0]
        idx = t * (len(self.colors) - 1)
        i = int(idx)
        f = idx - i
        if i >= len(self.colors) - 1:
            return self.colors[-1]
        return self.colors[i].lerp(self.colors[i + 1], f)

    @classmethod
    def from_palette(cls, name: str) -> Gradient:
        return cls(*PALETTES[name])


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
