from __future__ import annotations
import math
import random
from .color import Color, Gradient
from .glyphs import LINE_CHARS, SHADE_CHARS


class DrawMixin:
    """Cell-buffer drawing primitives shared by :class:`Canvas` and
    :class:`HiResCanvas`.

    Every primitive honours the host surface's bounds check and z-depth
    ordering, because they all go through ``self.set_pixel`` (or
    ``self.set_pixel_exact``, which is the same thing with ``fg``/``bg``
    assigned even when ``None``).

    **Which one a primitive uses matters.** Line, text, shape and blit
    primitives use :meth:`set_pixel`, where ``fg=None`` means *leave the
    existing foreground alone* - so drawing an outline over a filled box keeps
    the fill's colour. The region primitives (:meth:`fill_rect`,
    :meth:`fill`, :meth:`fill_gradient_y`, :meth:`fill_gradient_radial`) use
    :meth:`set_pixel_exact`, where ``fg=None`` means *actively clear the
    foreground* - which is what you want when a gradient defines the whole
    area. Both surfaces implement both methods with these semantics.
    """

    def blit_canvas(self, src, dx: int = 0, dy: int = 0, z: float = 0):
        """Copy another buffer surface onto this one at offset ``dx``/``dy``.

        A source cell is copied when it has a non-``None`` ``fg``; cells with
        no foreground are treated as transparent and skipped, so a sprite's
        background is not blanked over. Note that "has an ``fg``" is the test,
        not "is not a space": a sprite authored with a default ``fg`` colours
        its interior spaces too, and those *will* be blitted. Use
        ``fg=None`` on the source sprite to keep its spaces transparent.
        """
        for sy in range(src.h):
            for sx in range(src.w):
                sc = src.buffer[sy][sx]
                if sc.fg is None:
                    continue
                self.set_pixel(sx + dx, sy + dy, sc.char, sc.fg, sc.bg, z)

    # -- filled regions -------------------------------------------------

    def fill_rect(self, x: int, y: int, w: int, h: int,
                  char: str = '#', fg: Color | None = None,
                  bg: Color | None = None, z: float = 0):
        """Fill a ``w`` x ``h`` rectangle at ``(x, y)``, clipped to bounds.

        Uses :meth:`set_pixel_exact`, so ``fg=None``/``bg=None`` clear the
        corresponding channel rather than preserving it.
        """
        x0 = max(0, x); x1 = min(self.width, x + w)
        y0 = max(0, y); y1 = min(self.height, y + h)
        for iy in range(y0, y1):
            row = self.buffer[iy]
            for ix in range(x0, x1):
                c = row[ix]
                if z >= c.z:
                    c.char = char; c.fg = fg; c.bg = bg; c.z = z

    def fill(self, x: int, y: int, char: str = '#',
             fg: Color | None = None, bg: Color | None = None,
             z: float = 0):
        from collections import deque
        target = self.get_pixel(x, y)
        if target is None:
            return
        target_char = target.char
        queue = deque([(x, y)])
        visited = set()
        while queue:
            cx, cy = queue.popleft()
            if (cx, cy) in visited:
                continue
            visited.add((cx, cy))
            cell = self.get_pixel(cx, cy)
            if cell is None or cell.char != target_char:
                continue
            self.set_pixel(cx, cy, char, fg, bg, z)
            queue.extend([(cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)])

    # -- text -----------------------------------------------------------

    def draw_text(self, x: int, y: int, text: str,
                  fg: Color | None = None, bg: Color | None = None,
                  z: float = 0):
        for i, ch in enumerate(text):
            self.set_pixel(x + i, y, ch, fg, bg, z)

    def draw_text_at(self, x: int, y: int, text: str,
                     fg: Color | None = None, bg: Color | None = None,
                     z: float = 0, anchor: str = 'nw'):
        """Draw text with an anchor. ``x``/``y`` are offsets from the anchor
        point: 'n'/'s' centre horizontally, 'e'/'w' align a side edge, 'c'
        centres both axes, 'nw' is plain top-left. Margins are positive
        toward the inside of the screen."""
        tw = len(text)
        th = 1
        if 'e' in anchor: ax = self.width - tw - x
        elif anchor in ('w', 'nw', 'sw'): ax = x
        else: ax = (self.width - tw) // 2 + x
        if 's' in anchor: ay = self.height - th - y
        elif anchor in ('n', 'nw', 'ne'): ay = y
        else: ay = (self.height - th) // 2 + y
        self.draw_text(ax, ay, text, fg, bg, z)
        return ax, ay

    def draw_text_centered(self, y: int, text: str,
                           fg: Color | None = None,
                           bg: Color | None = None, z: float = 0):
        return self.draw_text_at(0, y, text, fg, bg, z, anchor='n')

    # -- lines / outlines -----------------------------------------------

    def draw_line(self, x1: int, y1: int, x2: int, y2: int,
                  char: str = '#', fg: Color | None = None,
                  bg: Color | None = None, z: float = 0):
        # A non-finite endpoint used to hang the process: err becomes inf or
        # nan, neither end is ever reached, and the loop spins forever.
        if not all(math.isfinite(v) for v in (x1, y1, x2, y2)):
            return
        dx = abs(x2 - x1); dy = -abs(y2 - y1)
        sx = 1 if x1 < x2 else -1
        sy = 1 if y1 < y2 else -1
        err = dx + dy
        # The walk is monotone in both axes, so once it is more than one
        # surface's worth of steps from where it started it can never land on
        # the buffer again. Budgeting it here keeps a line to a coordinate like
        # 1e300 from spinning for effectively ever.
        budget = self.width + self.height + 2
        while True:
            self.set_pixel(x1, y1, char, fg, bg, z)
            if x1 == x2 and y1 == y2:
                break
            e2 = 2 * err
            if e2 >= dy: err += dy; x1 += sx
            if e2 <= dx: err += dx; y1 += sy
            budget -= 1
            if budget <= 0:
                break

    def draw_line_thick(self, x1, y1, x2, y2, thickness=2,
                        char='#', fg=None, bg=None, z=0):
        """Draw a line `thickness` cells wide.

        Stamps parallel copies offset along the segment normal. The previous
        version hard-coded exactly three passes (+0, +1, -1), so every
        thickness of 2 and every thickness above 3 rendered identically -
        a caller asking for an 8-wide beam got a 3-wide one.
        """
        thickness = max(1, int(thickness))
        if not all(math.isfinite(v) for v in (x1, y1, x2, y2)):
            return
        if thickness == 1:
            self.draw_line(x1, y1, x2, y2, char, fg, bg, z)
            return
        dx, dy = x2 - x1, y2 - y1
        norm = math.hypot(dx, dy) or 1.0
        nx, ny = -dy / norm, dx / norm
        # Integer offsets only. Fractional ones (k - (thickness-1)/2) round
        # ambiguously in a cell grid, which silently collapsed an even
        # thickness back down to half as many passes.
        base = thickness // 2
        for k in range(thickness):
            off = k - base
            self.draw_line(round(x1 + nx * off), round(y1 + ny * off),
                           round(x2 + nx * off), round(y2 + ny * off),
                           char, fg, bg, z)

    def draw_ray(self, x1: float, y1: float, x2: float, y2: float,
                 char: str = '#', fg: Color | None = None,
                 bg: Color | None = None, z: float = 0,
                 fade: bool = False):
        if not all(math.isfinite(v) for v in (x1, y1, x2, y2)):
            return
        dx, dy = x2 - x1, y2 - y1
        dist = math.hypot(dx, dy)
        # A cell grid cannot show more distinct cells than it has, and a ray
        # spanning e.g. 1e300 asked for a 300-digit loop. Cap the walk at the
        # surface's own diagonal.
        steps = min(max(1, int(dist)), self.width + self.height)
        for i in range(steps + 1):
            t = i / steps
            xx = round(x1 + dx * t)
            yy = round(y1 + dy * t)
            if fade and fg:
                a = 1 - t * 0.7
                cc = Color(int(fg.r * a), int(fg.g * a), int(fg.b * a))
                self.set_pixel(xx, yy, char, cc, bg, z)
            else:
                self.set_pixel(xx, yy, char, fg, bg, z)

    def draw_rect(self, x: int, y: int, w: int, h: int,
                  char: str = '#', fg: Color | None = None,
                  bg: Color | None = None, z: float = 0,
                  fill: bool = False, radius: int = 0):
        if fill:
            self.fill_rect(x, y, w, h, char, fg, bg, z)
            return
        if w <= 0 or h <= 0:
            return
        # Clip the edges to the surface. The outline used to be drawn at the
        # *requested* corners, so any rect reaching past the edge vanished
        # entirely: draw_rect(-2, -2, 20, 20) on a 4x4 canvas drew nothing.
        x0 = max(0, x); y0 = max(0, y)
        x2 = min(self.width - 1, x + w - 1)
        y2 = min(self.height - 1, y + h - 1)
        if x0 > x2 or y0 > y2:
            return
        if radius > 0:
            r = min(radius, (x2 - x0) // 2, (y2 - y0) // 2)
            for i in range(x0 + r, x2 - r + 1):
                self.set_pixel(i, y0, LINE_CHARS['h'], fg, bg, z)
                self.set_pixel(i, y2, LINE_CHARS['h'], fg, bg, z)
            for i in range(y0 + r, y2 - r + 1):
                self.set_pixel(x0, i, LINE_CHARS['v'], fg, bg, z)
                self.set_pixel(x2, i, LINE_CHARS['v'], fg, bg, z)
            # The corner glyphs belong at the *outer* corners. They used to be
            # placed a radius-step inside, which put a stray '╰ ╯' in the middle
            # of the shape and left the real corners blank.
            self.set_pixel(x0, y0, '╭', fg, bg, z)
            self.set_pixel(x2, y0, '╮', fg, bg, z)
            self.set_pixel(x0, y2, '╰', fg, bg, z)
            self.set_pixel(x2, y2, '╯', fg, bg, z)
            return
        for i in range(x0, x2 + 1):
            self.set_pixel(i, y0, char, fg, bg, z)
            self.set_pixel(i, y2, char, fg, bg, z)
        for i in range(y0 + 1, y2):
            self.set_pixel(x0, i, char, fg, bg, z)
            self.set_pixel(x2, i, char, fg, bg, z)

    def draw_circle(self, cx: int, cy: int, r: int,
                    char: str = '#', fg: Color | None = None,
                    bg: Color | None = None, z: float = 0,
                    fill: bool = False):
        x, y, d = 0, r, 1 - r

        # Every pass of the loop below plots a ring at radius >= 1, so the
        # centre was never visited: a radius-1 circle rendered as a hollow
        # plus with a hole in the middle.
        self.set_pixel(cx, cy, char, fg, bg, z)

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
            if d < 0:
                d += 2 * x + 3
            else:
                d += 2 * (x - y) + 5; y -= 1
            x += 1

    def draw_ellipse(self, cx: int, cy: int, rx: int, ry: int,
                     char: str = '#', fg: Color | None = None,
                     bg: Color | None = None, z: float = 0,
                     fill: bool = False):
        if rx <= 0 or ry <= 0:
            return
        x, y = 0, ry
        rx2, ry2 = rx * rx, ry * ry
        tworx2, twory2 = 2 * rx2, 2 * ry2
        px, py = 0, tworx2 * y
        d = ry2 - rx2 * ry + 0.25 * rx2
        while px < py:
            x += 1; px += twory2
            if d < 0:
                d += ry2 + px
            else:
                y -= 1; py -= tworx2; d += ry2 + px - py
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
            if d > 0:
                d += rx2 - py
            else:
                x += 1; px += twory2; d += rx2 - py + px
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
                      char: str = '#', fg: Color | None = None,
                      bg: Color | None = None, z: float = 0,
                      fill: bool = False):
        if not fill:
            self.draw_line(x1, y1, x2, y2, char, fg, bg, z)
            self.draw_line(x2, y2, x3, y3, char, fg, bg, z)
            self.draw_line(x3, y3, x1, y1, char, fg, bg, z)
            return
        pts = sorted([(x1, y1), (x2, y2), (x3, y3)], key=lambda p: p[1])
        ax, ay = pts[0]; bx, by = pts[1]; cx, cy = pts[2]
        total_h = cy - ay
        if total_h == 0:
            return
        for iy in range(max(0, ay), min(self.height, cy + 1)):
            seg = iy - ay
            if iy < by:
                xa = ax + (bx - ax) * seg // (by - ay) if by != ay else ax
            else:
                xa = bx + (cx - bx) * (iy - by) // (cy - by) if cy != by else bx
            xb = ax + (cx - ax) * seg // total_h
            if xa > xb:
                xa, xb = xb, xa
            xa = max(0, xa); xb = min(self.width - 1, xb)
            for ix in range(xa, xb + 1):
                self.set_pixel(ix, iy, char, fg, bg, z)

    def draw_polygon(self, points: list[tuple[int, int]],
                     char: str = '#', fg: Color | None = None,
                     bg: Color | None = None, z: float = 0,
                     fill: bool = False):
        n = len(points)
        if n < 3:
            return
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
                    char: str = '#', fg: Color | None = None,
                    bg: Color | None = None, z: float = 0):
        if len(pts) < 2:
            return
        if steps < 1:
            raise ValueError(f'draw_bezier needs steps >= 1, got {steps}')
        if not all(math.isfinite(v) for p in pts for v in p):
            return
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
                 end_angle: float, char: str = '#', fg: Color | None = None,
                 bg: Color | None = None, z: float = 0):
        if not all(math.isfinite(v) for v in (cx, cy, r, start_angle, end_angle)):
            return
        # Capped like draw_ray: a huge radius is a caller mistake and used to
        # cost int(r * sweep) iterations of pure waste, all off-buffer.
        steps = min(max(4, int(r * abs(end_angle - start_angle))),
                    4 * (self.width + self.height))
        for i in range(steps + 1):
            t = start_angle + (end_angle - start_angle) * i / steps
            x = round(cx + r * math.cos(t))
            y = round(cy + r * math.sin(t))
            self.set_pixel(x, y, char, fg, bg, z)

    # -- gradients ------------------------------------------------------

    def gradient_fill(self, x1: int, y1: int, x2: int, y2: int,
                      grad: Gradient, char_scheme: list[str] | None = None,
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
                self.set_pixel_exact(ix, iy, chars[ci], grad.at(t), None, z)

    def gradient_fill_radial(self, cx: int, cy: int, r: int,
                             grad: Gradient, z: float = 0):
        if r <= 0:
            return
        x1, y1 = max(0, cx - r), max(0, cy - r)
        # Inclusive on every side: the old +r made the disc a cell short on the
        # right and bottom, so a centred radial gradient had a flat edge.
        x2, y2 = min(self.width, cx + r + 1), min(self.height, cy + r + 1)
        for iy in range(y1, y2):
            for ix in range(x1, x2):
                d = math.hypot(ix - cx, iy - cy)
                t = max(0, min(1, d / r))
                self.set_pixel_exact(ix, iy, SHADE_CHARS[int(t * (len(SHADE_CHARS) - 1))],
                                     grad.at(t), None, z)

    def fill_gradient_x(self, x: int, y: int, w: int, h: int,
                        grad: Gradient, char: str = ' ', z: float = 0):
        """Horizontal background gradient: ' ' glyph, colour goes in bg."""
        x0 = max(0, x); x1 = min(self.width, x + w)
        y0 = max(0, y); y1 = min(self.height, y + h)
        span = max(1, x1 - x0 - 1)
        for iy in range(y0, y1):
            for ix in range(x0, x1):
                t = max(0, min(1, (ix - x0) / span))
                self.set_pixel_exact(ix, iy, char, None, grad.at(t), z)
        return self

    def fill_gradient_y(self, x: int, y: int, w: int, h: int,
                        grad: Gradient, char: str = ' ', z: float = 0):
        """Vertical background gradient: ' ' glyph, colour goes in bg."""
        x0 = max(0, x); x1 = min(self.width, x + w)
        y0 = max(0, y); y1 = min(self.height, y + h)
        span = max(1, y1 - y0 - 1)
        for iy in range(y0, y1):
            t = max(0, min(1, (iy - y0) / span))
            for ix in range(x0, x1):
                self.set_pixel_exact(ix, iy, char, None, grad.at(t), z)
        return self

    def fill_sky(self, grad: Gradient, horizon: float = 0.5,
                 char: str = ' ', z: float = 0):
        """Paint a sky above a flat ground colour.

        Rows from 0 to ``horizon`` (a 0-1 fraction of the height) sample
        ``grad`` from its first stop to its last. Everything below the horizon
        is filled with ``grad``'s *last* stop, read as the ground.

        The ground half is deliberately flat rather than a second gradient
        sweep - an earlier version passed a one-stop ``Gradient`` here while
        documenting a 1 -> last sweep, so the docstring described behaviour the
        code did not have.
        """
        x0, x1 = 0, self.width
        y0, y1 = 0, int(self.height * max(0, min(1, horizon)))
        span = max(1, y1 - y0 - 1)
        for iy in range(y0, y1):
            t = max(0, min(1, (iy - y0) / span))
            g = grad.at(t)
            for ix in range(x0, x1):
                self.set_pixel_exact(ix, iy, char, None, g, z)
        ground = grad.at(1.0)
        for iy in range(y1, self.height):
            for ix in range(x0, x1):
                self.set_pixel_exact(ix, iy, char, None, ground, z)
        return self

    # -- noise ----------------------------------------------------------

    def noise(self, x: int, y: int, w: int, h: int, seed: float = 0,
              fg: Color | None = None, bg: Color | None = None,
              z: float = 0):
        """Fill a region with random shade glyphs.

        Uses a private ``random.Random(seed)`` so the result is reproducible
        and does not disturb - or depend on - the global random state, which
        the previous implementation did.
        """
        rng = random.Random(seed)
        for iy in range(max(0, y), min(self.height, y + h)):
            for ix in range(max(0, x), min(self.width, x + w)):
                v = rng.random()
                ci = int(v * (len(SHADE_CHARS) - 1))
                self.set_pixel(ix, iy, SHADE_CHARS[ci], fg, bg, z)