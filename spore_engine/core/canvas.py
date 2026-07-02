from __future__ import annotations
import math
from collections import deque
from typing import Optional
from .color import Color, Gradient, BLACK
from .geom import Vec2


SHADE_CHARS = ' .:-=+*#%@'
BRAILLE_CHARS = '⠀⢀⡀⣀⠠⢠⡠⣠⠤⢤⡤⣤⠴⢴⡴⣴⠰⢰⡰⣰⠸⢸⡸⣸⢺⡺⣺⠼⢼⡼⣼⠾⢾⡾⣾⡿⢿⡿⣿'
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


class Canvas:
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.w = width
        self.h = height
        self.buffer = [[Cell() for _ in range(width)] for _ in range(height)]
        self._dirty = True

    def clear(self, char: str = ' '):
        for y in range(self.height):
            row = self.buffer[y]
            for x in range(self.width):
                cell = row[x]
                cell.char = char
                cell.fg = None
                cell.bg = None
                cell.z = 0
        self._dirty = True

    def fill_rect(self, x: int, y: int, w: int, h: int,
                  char: str = '#', fg: Optional[Color] = None,
                  bg: Optional[Color] = None, z: float = 0):
        x0 = max(0, x); x1 = min(self.width, x + w)
        y0 = max(0, y); y1 = min(self.height, y + h)
        for iy in range(y0, y1):
            row = self.buffer[iy]
            for ix in range(x0, x1):
                c = row[ix]
                if z >= c.z:
                    c.char = char; c.fg = fg; c.bg = bg; c.z = z
        self._dirty = True

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

    def draw_text(self, x: int, y: int, text: str,
                  fg: Optional[Color] = None, bg: Optional[Color] = None,
                  z: float = 0):
        for i, ch in enumerate(text):
            self.set_pixel(x + i, y, ch, fg, bg, z)

    def draw_line(self, x1: int, y1: int, x2: int, y2: int,
                  char: str = '#', fg: Optional[Color] = None,
                  bg: Optional[Color] = None, z: float = 0):
        dx = abs(x2 - x1); dy = -abs(y2 - y1)
        sx = 1 if x1 < x2 else -1
        sy = 1 if y1 < y2 else -1
        err = dx + dy
        while True:
            self.set_pixel(x1, y1, char, fg, bg, z)
            if x1 == x2 and y1 == y2:
                break
            e2 = 2 * err
            if e2 >= dy: err += dy; x1 += sx
            if e2 <= dx: err += dx; y1 += sy

    def draw_line_thick(self, x1, y1, x2, y2, thickness=2,
                        char='#', fg=None, bg=None, z=0):
        self.draw_line(x1, y1, x2, y2, char, fg, bg, z)
        if thickness >= 2:
            self.draw_line(x1, y1 + 1, x2, y2 + 1, char, fg, bg, z)
            self.draw_line(x1, y1 - 1, x2, y2 - 1, char, fg, bg, z)

    def draw_rect(self, x: int, y: int, w: int, h: int,
                  char: str = '#', fg: Optional[Color] = None,
                  bg: Optional[Color] = None, z: float = 0,
                  fill: bool = False, radius: int = 0):
        if fill:
            self.fill_rect(x, y, w, h, char, fg, bg, z)
            return
        if w <= 0 or h <= 0:
            return
        x2 = x + w - 1; y2 = y + h - 1
        if radius > 0:
            r = min(radius, w // 2, h // 2)
            for i in range(x + r, x2 - r + 1):
                self.set_pixel(i, y, '─', fg, bg, z)
                self.set_pixel(i, y2, '─', fg, bg, z)
            for i in range(y + r, y2 - r + 1):
                self.set_pixel(x, i, '│', fg, bg, z)
                self.set_pixel(x2, i, '│', fg, bg, z)
            self.set_pixel(x + r, y + r, '╭', fg, bg, z)
            self.set_pixel(x2 - r, y + r, '╮', fg, bg, z)
            self.set_pixel(x + r, y2 - r, '╰', fg, bg, z)
            self.set_pixel(x2 - r, y2 - r, '╯', fg, bg, z)
            return
        for i in range(x, x2 + 1):
            self.set_pixel(i, y, char, fg, bg, z)
            self.set_pixel(i, y2, char, fg, bg, z)
        for i in range(y + 1, y2):
            self.set_pixel(x, i, char, fg, bg, z)
            self.set_pixel(x2, i, char, fg, bg, z)

    def draw_circle(self, cx: int, cy: int, r: int,
                    char: str = '#', fg: Optional[Color] = None,
                    bg: Optional[Color] = None, z: float = 0,
                    fill: bool = False):
        x, y, d = 0, r, 1 - r
        def p4(cx, cy, x, y):
            self.set_pixel(cx + x, cy + y, char, fg, bg, z)
            self.set_pixel(cx - x, cy + y, char, fg, bg, z)
            self.set_pixel(cx + x, cy - y, char, fg, bg, z)
            self.set_pixel(cx - x, cy - y, char, fg, bg, z)
        def p8(cx, cy, x, y):
            p4(cx, cy, x, y); p4(cx, cy, y, x)
        while x <= y:
            if fill:
                for i in range(-x, x + 1):
                    self.set_pixel(cx + i, cy + y, char, fg, bg, z)
                    self.set_pixel(cx + i, cy - y, char, fg, bg, z)
                for i in range(-y, y + 1):
                    self.set_pixel(cx + i, cy + x, char, fg, bg, z)
                    self.set_pixel(cx + i, cy - x, char, fg, bg, z)
            else:
                p8(cx, cy, x, y)
            if d < 0: d += 2 * x + 3
            else: d += 2 * (x - y) + 5; y -= 1
            x += 1

    def draw_ellipse(self, cx: int, cy: int, rx: int, ry: int,
                     char: str = '#', fg: Optional[Color] = None,
                     bg: Optional[Color] = None, z: float = 0,
                     fill: bool = False):
        if rx <= 0 or ry <= 0: return
        x, y = 0, ry
        rx2, ry2 = rx * rx, ry * ry
        tworx2, twory2 = 2 * rx2, 2 * ry2
        px, py = 0, tworx2 * y
        d = ry2 - rx2 * ry + 0.25 * rx2
        while px < py:
            x += 1; px += twory2
            if d < 0: d += ry2 + px
            else: y -= 1; py -= tworx2; d += ry2 + px - py
            if fill:
                for i in range(-x, x + 1):
                    self.set_pixel(cx + i, cy + y, char, fg, bg, z)
                    self.set_pixel(cx + i, cy - y, char, fg, bg, z)
            else:
                self.set_pixel(cx + x, cy + y, char, fg, bg, z)
                self.set_pixel(cx - x, cy + y, char, fg, bg, z)
                self.set_pixel(cx + x, cy - y, char, fg, bg, z)
                self.set_pixel(cx - x, cy - y, char, fg, bg, z)
        d = ry2 * (x + 0.5) ** 2 + rx2 * (y - 1) ** 2 - rx2 * ry2
        while y > 0:
            y -= 1; py -= tworx2
            if d > 0: d += rx2 - py
            else: x += 1; px += twory2; d += rx2 - py + px
            if fill:
                for i in range(-x, x + 1):
                    self.set_pixel(cx + i, cy + y, char, fg, bg, z)
                    self.set_pixel(cx + i, cy - y, char, fg, bg, z)
            else:
                self.set_pixel(cx + x, cy + y, char, fg, bg, z)
                self.set_pixel(cx - x, cy + y, char, fg, bg, z)
                self.set_pixel(cx + x, cy - y, char, fg, bg, z)
                self.set_pixel(cx - x, cy - y, char, fg, bg, z)

    def draw_triangle(self, x1: int, y1: int, x2: int, y2: int, x3: int, y3: int,
                      char: str = '#', fg: Optional[Color] = None,
                      bg: Optional[Color] = None, z: float = 0,
                      fill: bool = False):
        if not fill:
            self.draw_line(x1, y1, x2, y2, char, fg, bg, z)
            self.draw_line(x2, y2, x3, y3, char, fg, bg, z)
            self.draw_line(x3, y3, x1, y1, char, fg, bg, z)
            return
        pts = sorted([(x1, y1), (x2, y2), (x3, y3)], key=lambda p: p[1])
        ax, ay = pts[0]; bx, by = pts[1]; cx, cy = pts[2]
        total_h = cy - ay
        if total_h == 0: return
        for iy in range(max(0, ay), min(self.height, cy + 1)):
            seg = iy - ay
            if iy < by:
                xa = ax + (bx - ax) * seg // (by - ay) if by != ay else ax
            else:
                xa = bx + (cx - bx) * (iy - by) // (cy - by) if cy != by else bx
            xb = ax + (cx - ax) * seg // total_h
            if xa > xb: xa, xb = xb, xa
            xa = max(0, xa); xb = min(self.width - 1, xb)
            for ix in range(xa, xb + 1):
                self.set_pixel(ix, iy, char, fg, bg, z)

    def draw_polygon(self, points: list[tuple[int, int]],
                     char: str = '#', fg: Optional[Color] = None,
                     bg: Optional[Color] = None, z: float = 0,
                     fill: bool = False):
        n = len(points)
        if n < 3: return
        if not fill:
            for i in range(n):
                x1, y1 = points[i]
                x2, y2 = points[(i + 1) % n]
                self.draw_line(x1, y1, x2, y2, char, fg, bg, z)
            return
        ys = [p[1] for p in points]
        min_y, max_y = max(0, min(ys)), min(self.height - 1, max(ys))
        for iy in range(min_y, max_y + 1):
            xs = []
            for i in range(n):
                x1, y1 = points[i]
                x2, y2 = points[(i + 1) % n]
                if y1 == y2:
                    if y1 == iy:
                        xs.append(x1); xs.append(x2)
                    continue
                if (y1 <= iy < y2) or (y2 <= iy < y1):
                    t = (iy - y1) / (y2 - y1)
                    xs.append(int(x1 + t * (x2 - x1)))
            xs.sort()
            for k in range(0, len(xs) - 1, 2):
                xa = max(0, xs[k])
                xb = min(self.width - 1, xs[k + 1])
                for ix in range(xa, xb + 1):
                    self.set_pixel(ix, iy, char, fg, bg, z)

    def draw_bezier(self, pts: list[tuple[float, float]], steps: int = 30,
                    char: str = '#', fg: Optional[Color] = None,
                    bg: Optional[Color] = None, z: float = 0):
        n = len(pts) - 1
        prev = None
        for i in range(steps + 1):
            t = i / steps
            x, y = 0.0, 0.0
            for j, (px, py) in enumerate(pts):
                coeff = math.comb(n, j) * (t ** j) * ((1 - t) ** (n - j))
                x += coeff * px
                y += coeff * py
            if prev:
                self.draw_line(round(prev[0]), round(prev[1]),
                               round(x), round(y), char, fg, bg, z)
            prev = (x, y)

    def draw_arc(self, cx: int, cy: int, r: int, start_angle: float,
                 end_angle: float, char: str = '#', fg: Optional[Color] = None,
                 bg: Optional[Color] = None, z: float = 0):
        steps = max(4, int(r * abs(end_angle - start_angle)))
        for i in range(steps + 1):
            t = start_angle + (end_angle - start_angle) * i / steps
            x = round(cx + r * math.cos(t))
            y = round(cy + r * math.sin(t))
            self.set_pixel(x, y, char, fg, bg, z)

    def gradient_fill(self, x1: int, y1: int, x2: int, y2: int,
                      grad: Gradient, char_scheme: Optional[list[str]] = None,
                      horizontal: bool = True, z: float = 0):
        chars = char_scheme or SHADE_CHARS
        if x1 > x2: x1, x2 = x2, x1
        if y1 > y2: y1, y2 = y2, y1
        for iy in range(max(0, y1), min(self.height, y2)):
            for ix in range(max(0, x1), min(self.width, x2)):
                if horizontal:
                    t = (ix - x1) / (x2 - x1) if x2 != x1 else 0
                else:
                    t = (iy - y1) / (y2 - y1) if y2 != y1 else 0
                t = max(0, min(1, t))
                ci = int(t * (len(chars) - 1))
                self.set_pixel(ix, iy, chars[ci], grad.at(t), z=z)

    def fill(self, x: int, y: int, char: str = '#',
             fg: Optional[Color] = None, bg: Optional[Color] = None,
             z: float = 0):
        target = self.get_pixel(x, y)
        if target is None: return
        queue = deque([(x, y)])
        visited = set()
        while queue:
            cx, cy = queue.popleft()
            if (cx, cy) in visited: continue
            visited.add((cx, cy))
            cell = self.get_pixel(cx, cy)
            if cell is None or cell.char != target.char: continue
            self.set_pixel(cx, cy, char, fg, bg, z)
            queue.extend([(cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)])

    def draw_ray(self, x1: float, y1: float, x2: float, y2: float,
                  char: str = '#', fg: Optional[Color] = None,
                  bg: Optional[Color] = None, z: float = 0,
                  fade: bool = False):
        dx, dy = x2 - x1, y2 - y1
        dist = math.hypot(dx, dy)
        steps = max(1, int(dist))
        for i in range(steps + 1):
            t = i / steps
            x = round(x1 + dx * t)
            y = round(y1 + dy * t)
            if fade and fg:
                a = 1 - t * 0.7
                c = Color(int(fg.r * a), int(fg.g * a), int(fg.b * a))
                self.set_pixel(x, y, char, c, bg, z)
            else:
                self.set_pixel(x, y, char, fg, bg, z)

    def gradient_fill_radial(self, cx: int, cy: int, r: int,
                              grad: Gradient, z: float = 0):
        if r <= 0: return
        x1, y1 = max(0, cx - r), max(0, cy - r)
        x2, y2 = min(self.width, cx + r), min(self.height, cy + r)
        for iy in range(y1, y2):
            for ix in range(x1, x2):
                d = math.hypot(ix - cx, iy - cy)
                t = max(0, min(1, d / r))
                self.set_pixel(ix, iy, SHADE_CHARS[int(t * (len(SHADE_CHARS) - 1))],
                               grad.at(t), z=z)

    def noise(self, x: int, y: int, w: int, h: int, seed: float = 0,
              fg: Optional[Color] = None, bg: Optional[Color] = None,
              z: float = 0):
        import random as _r
        for iy in range(max(0, y), min(self.height, y + h)):
            for ix in range(max(0, x), min(self.width, x + w)):
                v = _r.random()
                ci = int(v * (len(SHADE_CHARS) - 1))
                self.set_pixel(ix, iy, SHADE_CHARS[ci], fg, bg, z)

    def render_to(self, stream, clear_first: bool = True):
        self._render_impl(stream, clear_first)

    def _render_impl(self, stream, clear_first: bool):
        reset = '\033[0m'
        if clear_first:
            stream.write('\033[H')
        for y in range(self.height):
            row = self.buffer[y]
            line_parts = []
            last_fg = None
            last_bg = None
            for x in range(self.width):
                cell = row[x]
                if cell.fg != last_fg or cell.bg != last_bg:
                    if cell.fg is None and cell.bg is None:
                        line_parts.append(reset)
                    else:
                        parts = []
                        if cell.fg: parts.append(cell.fg.ansi_fg())
                        if cell.bg: parts.append(cell.bg.ansi_bg())
                        line_parts.append(''.join(parts))
                    last_fg = cell.fg
                    last_bg = cell.bg
                line_parts.append(cell.char if cell.char else ' ')
            if last_fg or last_bg:
                line_parts.append(reset)
            stream.write(''.join(line_parts))
        stream.flush()

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


class HiResCanvas:
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

    def clear(self, z: float = -float('inf')):
        for y in range(self.h):
            for x in range(self.w):
                c = self.buffer[y][x]
                c.char = ' '; c.fg = None; c.bg = None; c.z = z

    def to_canvas(self, canvas: Canvas, z: float = 0):
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
                else:
                    canvas.set_pixel(x, y, ' ', z=z)

    def copy(self) -> HiResCanvas:
        new_canvas = HiResCanvas(self.w, self.h)
        for y in range(self.h):
            for x in range(self.w):
                sc = self.buffer[y][x]
                dc = new_canvas.buffer[y][x]
                dc.char, dc.fg, dc.bg, dc.z = sc.char, sc.fg, sc.bg, sc.z
        return new_canvas
