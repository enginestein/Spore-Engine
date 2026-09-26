from __future__ import annotations
from .canvas import Cell, Canvas
from .color import Color


class Sprite:
    def __init__(self, data: list[list[Cell]]):
        self.data = data
        self.width = len(data[0]) if data else 0
        self.height = len(data)

    @classmethod
    def from_string(cls, text: str, fg: Color | None = None,
                    bg: Color | None = None, scale: int = 1) -> Sprite:
        lines = text.rstrip('\n').split('\n')
        data = []
        for line in lines:
            row = []
            for c in line:
                for _ in range(scale):
                    row.append(Cell(char=c, fg=fg, bg=bg))
            if scale > 1:
                for _ in range(scale - 1):
                    data.append([Cell(char=c, fg=fg, bg=bg) for c in line for _ in range(scale)])
            data.append(row)
        return cls(data)

    @classmethod
    def from_file(cls, path: str, fg: Color | None = None,
                  bg: Color | None = None) -> Sprite:
        with open(path) as f:
            return cls.from_string(f.read(), fg, bg)

    def blit_to(self, canvas: Canvas, x: int, y: int,
                fg: Color | None = None, bg: Color | None = None,
                z: float = 0, transparent: str | None = ' ',
                scale: int = 1):
        for sy, row in enumerate(self.data):
            for sx, cell in enumerate(row):
                if transparent is not None and cell.char == transparent:
                    continue
                char = cell.char
                cf = fg if fg is not None else cell.fg
                cb = bg if bg is not None else cell.bg
                canvas.set_pixel(x + sx, y + sy, char, cf, cb, z)

    def mirrored(self) -> Sprite:
        data = [row[::-1] for row in self.data]
        return Sprite(data)

    def rotated(self, times: int = 1) -> Sprite:
        data = self.data
        for _ in range(times % 4):
            data = [list(r) for r in zip(*data[::-1], strict=False)]
        return Sprite(data)
