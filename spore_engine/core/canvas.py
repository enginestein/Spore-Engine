from __future__ import annotations
import unicodedata
from typing import Optional
from .color import Color
from .draw import DrawMixin


SHADE_CHARS = ' .:-=+*#%@'
BRAILLE_CHARS = '⠀⢀⡀⣀⠠⢠⡠⣠⠤⢤⡤⣤⠴⢴⡴⣴⠰⢰⡰⣰⠸⢸⡸⣸⢺⡺⣺⠼⢼⡼⣼⠾⢾⡾⣾⡿⢿⡿⣿'


def _char_width(ch: str) -> int:
    """Terminal display width of a single glyph.

    Measured on the target terminal (GNOME Terminal probe_width.py): every
    glyph this game emits - ASCII, block shades (NUL-last shade ramp), box
    drawing (double/single lines), bullets, arrows - advances exactly ONE
    column.  Counting them as 2 (the East-Asian ambiguous default) made rows
    terminate short of the right edge (ragged right-side distortion) and let
    wide rows wrap, shoving the whole page down to the ground for a frame.
    The game renders all glyphs at width 1; only true fullwidth CJK (never
    emitted) would be 2.
    """
    w = unicodedata.east_asian_width(ch)
    return 2 if w in ('F', 'W') else 1

LINE_CHARS = {'h': '─', 'v': '│', 'tl': '┌', 'tr': '┐', 'bl': '└', 'br': '┘',
              'tr_h': '┬', 'tl_h': '┴', 'cr': '├', 'cl': '┤', 'cross': '┼'}


class Cell:
    __slots__ = ('char', 'fg', 'bg', 'z')
    def __init__(self, char: str = ' ', fg: Optional[Color] = None,
                 bg: Optional[Color] = None, z: float = 0):
        self.char = char
        self.fg = fg
        self.bg = bg
        self.z = z


class Canvas(DrawMixin):
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.w = width
        self.h = height
        self.buffer = [[Cell(' ', None, None, -float('inf')) for _ in range(width)]
                       for _ in range(height)]
        self._dirty = True
        self._prev_render = None

    def clear(self, char: str = ' '):
        for y in range(self.height):
            row = self.buffer[y]
            for x in range(self.width):
                cell = row[x]
                cell.char = char
                cell.fg = None
                cell.bg = None
                cell.z = -float('inf')
        self._dirty = True
        self._prev_render = None

    def set_pixel(self, x: int, y: int, char: str = '#',
                  fg: Optional[Color] = None, bg: Optional[Color] = None,
                  z: float = 0):
        if x < 0 or x >= self.width or y < 0 or y >= self.height:
            return
        c = self.buffer[y][x]
        if z < c.z:
            return
        c.char = char
        if fg is not None: c.fg = fg
        if bg is not None: c.bg = bg
        c.z = z

    def get_pixel(self, x: int, y: int) -> Optional[Cell]:
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.buffer[y][x]
        return None

    def set_pixel_f(self, x: float, y: float, char: str = '#',
                    fg: Optional[Color] = None, bg: Optional[Color] = None,
                    z: float = 0):
        self.set_pixel(round(x), round(y), char, fg, bg, z)

    def half_block(self, x: int, y: int,
                   top_char: str, bottom_char: str,
                   top_fg: Optional[Color], bottom_fg: Optional[Color],
                   top_bg: Optional[Color] = None, bottom_bg: Optional[Color] = None,
                   z: float = 0):
        if top_char == ' ' and bottom_char == ' ':
            bg = bottom_bg or top_bg
            self.set_pixel(x, y, ' ', fg=None, bg=bg, z=z)
            return
        if bottom_char == ' ' or bottom_char is None:
            self.set_pixel(x, y, '▀', fg=top_fg, bg=top_bg, z=z)
            return
        if top_char == ' ' or top_char is None:
            self.set_pixel(x, y, '▄', fg=bottom_fg, bg=bottom_bg, z=z)
            return
        self.set_pixel(x, y, '▀', fg=top_fg, bg=bottom_fg, z=z)

    def half_block_pixel(self, x: int, y: int, top: Optional[Color],
                         bottom: Optional[Color], z: float = 0):
        c = self.buffer[y][x]
        if z < c.z:
            return
        if top and bottom:
            c.char = '▀'
            c.fg = top
            c.bg = bottom
        elif top:
            c.char = '▀'
            c.fg = top
            c.bg = None
        elif bottom:
            c.char = '▄'
            c.fg = bottom
            c.bg = None
        else:
            c.char = ' '
            c.fg = None
            c.bg = None
        c.z = z

    def render_to(self, stream, clear_first: bool = True):
        self._render_impl(stream, clear_first)

    def _render_impl(self, stream, clear_first: bool):
        reset = '\033[0m'
        width = max(1, self.width)
        h = self.height
        # canonical key for a cell: (char, r, g, b) with None->(-1,-1,-1)
        def key(cell):
            fg = cell.fg
            return (cell.char if cell.char else ' ',
                    (fg.r, fg.g, fg.b) if fg is not None else (-1, -1, -1))

        prev = self._prev_render
        if prev is None or len(prev) != h or any(len(r) != self.width for r in prev):
            prev = [[None] * self.width for _ in range(h)]
            clear_first = True

        home = False
        if clear_first:
            stream.write('\033[H')
            home = True

        emit_row = 0
        for y in range(h):
            row = self.buffer[y]
            prow = prev[y]
            # collect changed columns
            changed = []
            for x in range(self.width):
                k = key(row[x])
                if k != prow[x]:
                    changed.append(x)
            if not changed:
                continue
            # segment the changed columns into contiguous runs
            segs = []
            start = changed[0]
            prevx = start
            for x in changed[1:]:
                if x == prevx + 1:
                    prevx = x
                else:
                    segs.append((start, prevx))
                    start = x
                    prevx = x
            segs.append((start, prevx))

            # seek to row start once if this row has any change
            stream.write(f'\033[{y + 1};1H')
            emit_row = y
            target = 0
            for (x0, x1) in segs:
                if x0 > target:
                    stream.write(f'\033[{y + 1};{x0 + 1}H')
                # write the segment with minimal color transitions
                last_fg = last_bg = None
                seg_parts = []
                disp = x0
                for x in range(x0, x1 + 1):
                    cell = row[x]
                    ch, fg = cell.char if cell.char else ' ', cell.fg
                    bg = cell.bg
                    if fg != last_fg or bg != last_bg:
                        if fg is None and bg is None:
                            seg_parts.append(reset)
                        else:
                            parts = []
                            if fg: parts.append(fg.ansi_fg())
                            if bg: parts.append(bg.ansi_bg())
                            seg_parts.append(''.join(parts))
                        last_fg, last_bg = fg, bg
                    seg_parts.append(ch)
                    disp += 1
                seg_parts.append(reset)
                stream.write(''.join(seg_parts))
                target = x1 + 1
            # update prev for this row
            for x in range(self.width):
                prow[x] = key(row[x])
        stream.flush()
        self._prev_render = prev

    def copy(self) -> Canvas:
        new_canvas = Canvas(self.width, self.height)
        for y in range(self.height):
            for x in range(self.width):
                sc = self.buffer[y][x]
                dc = new_canvas.buffer[y][x]
                dc.char, dc.fg, dc.bg, dc.z = sc.char, sc.fg, sc.bg, sc.z
        return new_canvas

    def __repr__(self):
        return f'Canvas({self.width}x{self.height})'


class HiResCanvas(DrawMixin):
    def __init__(self, width: int, height: int):
        self.w = width
        self.h = height
        self.width = width
        self.height = height
        self.buffer = [[Cell() for _ in range(width)] for _ in range(height)]

    def set_pixel(self, x: int, y: int, char: str = '#',
                  fg: Optional[Color] = None, bg: Optional[Color] = None,
                  z: float = 0):
        if x < 0 or x >= self.w or y < 0 or y >= self.h:
            return
        c = self.buffer[y][x]
        if z < c.z: return
        c.char = char; c.fg = fg; c.bg = bg; c.z = z

    def set_pixel_z(self, x: int, y: int, fg: Optional[Color], z: float):
        if x < 0 or x >= self.w or y < 0 or y >= self.h: return
        c = self.buffer[y][x]
        if z < c.z: return
        c.char = '@'; c.fg = fg; c.bg = None; c.z = z

    def get_pixel(self, x: int, y: int) -> Optional[Cell]:
        if 0 <= x < self.w and 0 <= y < self.h:
            return self.buffer[y][x]
        return None

    def clear(self, z: float = -float('inf')):
        for y in range(self.h):
            for x in range(self.w):
                c = self.buffer[y][x]
                c.char = ' '; c.fg = None; c.bg = None; c.z = z

    def to_canvas(self, canvas: Canvas, z: float = 0, blank: bool = False):
        for y in range(min(canvas.height, self.h // 2)):
            for x in range(min(canvas.width, self.w)):
                t = self.buffer[y * 2][x]
                b = self.buffer[y * 2 + 1][x]
                top_filled = t.fg is not None
                bot_filled = b.fg is not None
                if top_filled and bot_filled:
                    canvas.set_pixel(x, y, '▀', t.fg, b.fg, z)
                elif top_filled:
                    canvas.set_pixel(x, y, '▀', t.fg, z=z)
                elif bot_filled:
                    canvas.set_pixel(x, y, '▄', b.fg, z=z)
                elif blank:
                    d = canvas.buffer[y][x]
                    if z >= d.z:
                        d.char = ' '
                        d.fg = None
                        d.bg = None
                        d.z = z

    def copy(self) -> HiResCanvas:
        new_canvas = HiResCanvas(self.w, self.h)
        for y in range(self.h):
            for x in range(self.w):
                sc = self.buffer[y][x]
                dc = new_canvas.buffer[y][x]
                dc.char, dc.fg, dc.bg, dc.z = sc.char, sc.fg, sc.bg, sc.z
        return new_canvas
