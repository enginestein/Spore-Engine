"""Character-cell surfaces: :class:`Canvas` and :class:`HiResCanvas`.

A surface is a grid of :class:`Cell` objects. :class:`Canvas` is one cell per
terminal cell; :class:`HiResCanvas` holds two stacked cells per terminal cell
so a scene can draw sub-cell detail that is composited into half-block glyphs.
Both share :class:`~spore_engine.core.draw.DrawMixin` for the drawing
primitives.
"""

from __future__ import annotations


from .color import Color
from .draw import DrawMixin
from .glyphs import LINE_CHARS, SHADE_CHARS
from .term import detect_color_depth

__all__ = ['LINE_CHARS', 'SHADE_CHARS', 'Canvas', 'Cell', 'HiResCanvas']

# Re-exported from .glyphs for backwards compatibility: these two names have
# always been importable from spore_engine.core.canvas.
_SHADE_CHARS = SHADE_CHARS

_INF = float('inf')

#: Depth of a cell nothing has claimed. ``+inf``, because depth is
#: lower-is-nearer: a real depth then always beats "unset", the same way a
#: higher z beats the ``-inf`` that :attr:`Cell.z` starts at.
_NO_DEPTH = _INF


class Cell:
    """One character cell: a glyph, optional fg/bg colours, a depth and a z.

    ``z`` is a painter's-algorithm depth. Higher wins; a draw with a lower
    ``z`` than the cell already holds is discarded. ``fg``/``bg`` of ``None``
    mean "the terminal default".

    ``depth`` is *perspective* depth, kept separate because the two were
    sharing one field and wanted opposite things. ``z`` orders the UI: a
    background at ``-100``, a HUD at ``100``, with nothing in between having
    any opinion about distance. ``render_mesh_solid`` wants a NDC z in 0-1 so
    intersecting meshes resolve. Any renderer that wrote a 0-1 value into ``z``
    therefore landed *below* every piece of chrome in the engine - which is why
    four of the five 3-D paths ended up writing ``z=0`` and quietly losing to
    whatever was drawn next.

    Nothing reads ``depth`` yet: the half-block fold still flattens geometry
    depth to the scalar ``z`` passed to :meth:`HiResCanvas.to_canvas`. It exists
    so a renderer *can* record real depth per sub-cell without corrupting layer
    order. ``depth`` is not part of equality, so the incremental diff - which
    keys on glyph and colour - is unaffected.
    """

    __slots__ = ('bg', 'char', 'depth', 'fg', 'z')

    def __init__(self, char: str = ' ', fg: Color | None = None,
                 bg: Color | None = None, z: float = 0,
                 depth: float = _NO_DEPTH):
        self.char = char
        self.fg = fg
        self.bg = bg
        self.z = z
        self.depth = depth

    def __eq__(self, other) -> bool:
        if not isinstance(other, Cell):
            return NotImplemented
        return (self.char == other.char and self.fg == other.fg
                and self.bg == other.bg and self.z == other.z)

    def __repr__(self) -> str:
        return f'Cell({self.char!r}, fg={self.fg}, bg={self.bg}, z={self.z})'


#: Upper bound on buffer allocation, so a computed or user-supplied size can
#: never request an unbounded amount of memory.
_MAX_CELLS = 8_000_000


def _check_dimensions(width: int, height: int, cls: str) -> tuple:
    """Validate a surface size.

    Sizes must be positive integers. A negative size used to build a canvas
    with an empty or negative buffer that rendered three bytes forever, which is
    far harder to diagnose than an immediate error; an unbounded size is how a
    graphics library gets a memory-exhaustion bug, so there is a cap.
    """
    if isinstance(width, bool) or isinstance(height, bool):
        raise TypeError(f'{cls} size must be integers, got bool')
    if not isinstance(width, int) or not isinstance(height, int):
        raise TypeError(
            f'{cls} size must be integers, got '
            f'{type(width).__name__}/{type(height).__name__}')
    if width <= 0 or height <= 0:
        raise ValueError(
            f'{cls} size must be positive, got {width}x{height}')
    if width * height > _MAX_CELLS:
        raise ValueError(
            f'{cls} size {width}x{height} is {width * height} cells, over the '
            f'{_MAX_CELLS} cell limit')
    return width, height


class Canvas(DrawMixin):
    """A character-cell drawing surface, one cell per terminal cell.

        c = Canvas(80, 24)
        c.draw_text(2, 2, 'hello', Color(255, 128, 0))
        c.render_to(sys.stdout)

    Only cells whose ``(char, fg, bg)`` actually changed since the last
    :meth:`render_to` are re-emitted, so a static frame costs a few bytes and
    a one-cell change costs a cursor move plus that cell. Size changes go
    through :meth:`resize`, which preserves content and forces one full
    redraw.

    **Colour semantics:** in :meth:`set_pixel`, ``fg=None`` means *leave the
    existing foreground alone* and ``bg=None`` means *leave the background
    alone*; the cell is only touched if the corresponding argument is given.
    This matches :class:`HiResCanvas` and the ``DrawMixin`` primitives. Use
    :meth:`set_pixel_exact` when you need to actively clear a colour.
    """

    def __init__(self, width: int, height: int, color_depth: int | None = None):
        width, height = _check_dimensions(width, height, 'Canvas')
        self.width = width
        self.height = height
        self.w = width
        self.h = height
        self.buffer = [[Cell(' ', None, None, -_INF) for _ in range(width)]
                       for _ in range(height)]
        # None = auto-detect from the stream at render time.
        self.color_depth = color_depth
        self._prev_render = None
        self._last_stats = None

    def clear(self, char: str = ' '):
        """Reset every cell to ``char`` with no colours and the lowest depth."""
        for y in range(self.height):
            row = self.buffer[y]
            for x in range(self.width):
                cell = row[x]
                cell.char = char
                cell.fg = None
                cell.bg = None
                cell.z = -_INF
                cell.depth = _NO_DEPTH

    def set_pixel(self, x: int, y: int, char: str = '#',
                  fg: Color | None = None, bg: Color | None = None,
                  z: float = 0):
        """Draw one cell, keeping any colour whose argument is ``None``.

        Out-of-bounds coordinates are a no-op, and a ``z`` below the cell's
        current depth is rejected."""
        if x < 0 or x >= self.width or y < 0 or y >= self.height:
            return
        c = self.buffer[y][x]
        if z < c.z:
            return
        c.char = char
        if fg is not None: c.fg = fg
        if bg is not None: c.bg = bg
        c.z = z

    def set_pixel_exact(self, x: int, y: int, char: str = '#',
                        fg: Color | None = None, bg: Color | None = None,
                        z: float = 0):
        """Like :meth:`set_pixel` but assigns ``fg``/``bg`` even when ``None``,
        actively clearing a colour. This is the semantics the fill/gradient
        primitives use."""
        if x < 0 or x >= self.width or y < 0 or y >= self.height:
            return
        c = self.buffer[y][x]
        if z < c.z:
            return
        c.char = char
        c.fg = fg
        c.bg = bg
        c.z = z

    def set_pixel_depth(self, x: int, y: int, depth: float, char: str = ' ',
                        fg: Color | None = None, bg: Color | None = None,
                        z: float = 0):
        """Write a cell and record *perspective* depth, nearest wins.

        The counterpart to using ``z`` for distance. Depth here is compared
        against ``Cell.depth`` only, so geometry cannot be hidden by a HUD at
        ``z=100`` nor fall behind a background at ``z=-100``.

        Out-of-bounds coordinates are a no-op, and a ``depth`` greater than the
        cell's current one is discarded. Nothing reads ``Cell.depth`` yet - see
        that attribute's documentation for why it exists and what still has to
        change before it does.
        """
        if x < 0 or x >= self.width or y < 0 or y >= self.height:
            return
        c = self.buffer[y][x]
        if depth > c.depth:          # something nearer is already here
            return
        c.char = char
        c.fg = fg
        c.bg = bg
        c.z = z
        c.depth = depth

    def get_pixel(self, x: int, y: int) -> Cell | None:
        """The :class:`Cell` at ``(x, y)``, or ``None`` if out of bounds."""
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.buffer[y][x]
        return None

    def set_pixel_f(self, x: float, y: float, char: str = '#',
                    fg: Color | None = None, bg: Color | None = None,
                    z: float = 0):
        """:meth:`set_pixel` with float coordinates, rounded to nearest."""
        self.set_pixel(round(x), round(y), char, fg, bg, z)

    def half_block(self, x: int, y: int,
                   top_char: str, bottom_char: str,
                   top_fg: Color | None, bottom_fg: Color | None,
                   top_bg: Color | None = None, bottom_bg: Color | None = None,
                   z: float = 0):
        """Combine a top/bottom glyph pair into one half-block cell."""
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

    def half_block_pixel(self, x: int, y: int, top: Color | None,
                         bottom: Color | None, z: float = 0):
        """Paint two vertical sub-cells into one half-block cell.

        Out-of-bounds coordinates are a no-op; without the guard a negative
        ``y`` silently wrote to the *last* row via Python's negative indexing.
        """
        if x < 0 or x >= self.width or y < 0 or y >= self.height:
            return
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

    def resize(self, width: int, height: int) -> None:
        """Resize the surface, preserving existing content.

        The new size must be positive. Content outside the new bounds is
        dropped, new cells start blank, and the frame diff is invalidated so
        the next :meth:`render_to` repaints everything - the terminal really
        did reflow, so a partial update would be wrong.
        """
        width, height = _check_dimensions(width, height, 'Canvas')
        if width == self.width and height == self.height:
            return
        new_buffer = [[Cell(' ', None, None, -_INF) for _ in range(width)]
                      for _ in range(height)]
        copy_h = min(self.height, height)
        copy_w = min(self.width, width)
        for y in range(copy_h):
            src = self.buffer[y]
            dst = new_buffer[y]
            for x in range(copy_w):
                s = src[x]
                d = dst[x]
                d.char, d.fg, d.bg, d.z = s.char, s.fg, s.bg, s.z
                d.depth = s.depth
        self.buffer = new_buffer
        self.width = self.w = width
        self.height = self.h = height
        self._prev_render = None

    def render_to(self, stream, clear_first: bool = True, force_full: bool = False):
        """Emit the frame to ``stream``, writing only what changed.

        ``clear_first`` homes the cursor first. ``force_full`` repaints every
        cell regardless of the diff - use it after a terminal desync.
        """
        self._render_impl(stream, clear_first, force_full)

    def full_redraw(self):
        """Force the next :meth:`render_to` to rewrite every cell (invalidate
        the incremental frame diff, used after a terminal desync or resize)."""
        self._prev_render = None

    @property
    def render_stats(self):
        """Stats for the last render: ``cells``/``rows``/``bytes`` emitted plus
        ``full``, which is ``True`` when every cell was rewritten (first frame,
        ``force_full``, or a resize). Useful to prove incrementality in demos
        and tests."""
        return self._last_stats

    def _render_impl(self, stream, clear_first: bool, force_full: bool = False):
        w = self.width
        h = self.height
        depth = self.color_depth
        if depth is None:
            depth = detect_color_depth(stream)
        reset = Color.reset()
        # canonical key for a cell: (char, fg, bg) with None->(-1,-1,-1)
        def key(cell):
            fg = cell.fg
            bg = cell.bg
            return (cell.char if cell.char else ' ',
                    (fg.r, fg.g, fg.b) if fg is not None else (-1, -1, -1),
                    (bg.r, bg.g, bg.b) if bg is not None else (-1, -1, -1))

        prev = self._prev_render
        full = prev is None
        # A shape change means the terminal itself reflowed, so every cell has
        # to be repainted. This is the same situation as force_full, and
        # render_stats must report it as such.
        if prev is None or len(prev) != h or any(len(r) != w for r in prev):
            prev = [[None] * w for _ in range(h)]
            clear_first = True
            full = True
        elif force_full:
            prev = [[None] * w for _ in range(h)]
            full = True

        cells_written = 0
        rows_written = 0
        bytes_written = 0
        if clear_first:
            stream.write('\033[H')
            bytes_written += 3

        buffer = self.buffer
        for y in range(h):
            row = buffer[y]
            prow = prev[y]
            # collect changed columns
            changed = []
            for x in range(w):
                k = key(row[x])
                if k != prow[x]:
                    changed.append((x, k))
            if not changed:
                continue
            rows_written += 1
            # segment the changed columns into contiguous runs
            segs = []
            start = changed[0][0]
            prevx = start
            for x, _k in changed[1:]:
                if x == prevx + 1:
                    prevx = x
                else:
                    segs.append((start, prevx))
                    start = x
                    prevx = x
            segs.append((start, prevx))

            # seek to row start once if this row has any change
            move = f'\033[{y + 1};1H'
            stream.write(move)
            bytes_written += len(move)
            target = 0
            for (x0, x1) in segs:
                if x0 > target:
                    move = f'\033[{y + 1};{x0 + 1}H'
                    stream.write(move)
                    bytes_written += len(move)
                # write the segment with minimal color transitions
                last_fg = last_bg = None
                seg_parts = []
                for x in range(x0, x1 + 1):
                    cell = row[x]
                    ch = cell.char if cell.char else ' '
                    fg = cell.fg
                    bg = cell.bg
                    if fg != last_fg or bg != last_bg:
                        if fg is None and bg is None:
                            seg_parts.append(reset)
                        else:
                            parts = []
                            if fg: parts.append(fg.ansi_fg(depth))
                            if bg: parts.append(bg.ansi_bg(depth))
                            seg_parts.append(''.join(parts))
                        last_fg, last_bg = fg, bg
                    seg_parts.append(ch)
                cells_written += (x1 - x0 + 1)
                seg_parts.append(reset)
                seg_str = ''.join(seg_parts)
                stream.write(seg_str)
                bytes_written += len(seg_str)
                target = x1 + 1
            # update prev for this row - only the cells we just emitted, so a
            # changed row costs one key() per changed cell instead of one per
            # cell in the row.
            for x, k in changed:
                prow[x] = k
        stream.flush()
        self._prev_render = prev
        self._last_stats = {
            'cells': cells_written,
            'rows': rows_written,
            'bytes': bytes_written,
            'full': full,
        }

    def copy(self) -> Canvas:
        """A deep copy: mutating the result never touches this canvas."""
        new_canvas = Canvas(self.width, self.height, self.color_depth)
        for y in range(self.height):
            row = self.buffer[y]
            nrow = new_canvas.buffer[y]
            for x in range(self.width):
                s = row[x]
                d = nrow[x]
                d.char, d.fg, d.bg, d.z = s.char, s.fg, s.bg, s.z
                d.depth = s.depth
        return new_canvas

    def __repr__(self):
        return f'Canvas({self.width}x{self.height})'


class HiResCanvas(DrawMixin):
    """A surface with two stacked sub-cells per terminal cell.

    Give it ``height * 2`` rows for a full-height buffer; :meth:`to_canvas`
    folds each pair into one half-block glyph, which is how the engine gets
    vertical resolution the terminal grid does not have.

    Colour semantics match :class:`Canvas`: ``fg=None``/``bg=None`` in
    :meth:`set_pixel` mean *leave that channel alone*, and
    :meth:`set_pixel_exact` is the clearing variant.
    """

    def __init__(self, width: int, height: int):
        width, height = _check_dimensions(width, height, 'HiResCanvas')
        self.w = width
        self.h = height
        self.width = width
        self.height = height
        self.buffer = [[Cell() for _ in range(width)] for _ in range(height)]

    def set_pixel(self, x: int, y: int, char: str = '#',
                  fg: Color | None = None, bg: Color | None = None,
                  z: float = 0):
        """Draw one sub-cell, keeping any colour whose argument is ``None``."""
        if x < 0 or x >= self.w or y < 0 or y >= self.h:
            return
        c = self.buffer[y][x]
        if z < c.z: return
        c.char = char
        if fg is not None: c.fg = fg
        if bg is not None: c.bg = bg
        c.z = z

    def set_pixel_exact(self, x: int, y: int, char: str = '#',
                        fg: Color | None = None, bg: Color | None = None,
                        z: float = 0):
        """Like :meth:`set_pixel` but assigns ``fg``/``bg`` even when ``None``."""
        if x < 0 or x >= self.w or y < 0 or y >= self.h:
            return
        c = self.buffer[y][x]
        if z < c.z: return
        c.char = char; c.fg = fg; c.bg = bg; c.z = z

    def set_pixel_z(self, x: int, y: int, fg: Color | None, z: float):
        """Shade-only sub-cell: the glyph follows the brightness of ``fg``."""
        if x < 0 or x >= self.w or y < 0 or y >= self.h: return
        c = self.buffer[y][x]
        c.char = '@'; c.fg = fg; c.bg = None; c.z = z

    def set_pixel_depth(self, x: int, y: int, depth: float, char: str = ' ',
                        fg: Color | None = None, bg: Color | None = None,
                        z: float = 0):
        """Write a cell and record *perspective* depth, nearest wins.

        The counterpart to :meth:`set_pixel_z`, which conflated the two. Depth
        here is compared against ``Cell.depth`` only, so a piece of geometry
        cannot be hidden by a HUD drawn at ``z=100`` or fall behind a
        background at ``z=-100``.

        Out-of-bounds coordinates are a no-op, and a ``depth`` greater than the
        cell's current one is discarded. The per-pixel z-buffer in
        :func:`~spore_engine.render3d.engine3d.render_mesh_solid` still goes
        through :meth:`set_pixel_z`; this is for a renderer that has separated
        the two.
        """
        if x < 0 or x >= self.w or y < 0 or y >= self.h:
            return
        c = self.buffer[y][x]
        if depth > c.depth:          # something nearer is already here
            return
        c.char = char
        c.fg = fg
        c.bg = bg
        c.z = z
        c.depth = depth

    def get_pixel(self, x: int, y: int) -> Cell | None:
        """The :class:`Cell` at ``(x, y)``, or ``None`` if out of bounds."""
        if 0 <= x < self.w and 0 <= y < self.h:
            return self.buffer[y][x]
        return None

    def clear(self, z: float = -_INF):
        """Reset every sub-cell to a blank at depth ``z``."""
        for y in range(self.h):
            row = self.buffer[y]
            for x in range(self.w):
                c = row[x]
                c.char = ' '; c.fg = None; c.bg = None; c.z = z
                c.depth = _NO_DEPTH

    def resize(self, width: int, height: int) -> None:
        """Resize, preserving content in the overlapping region."""
        width, height = _check_dimensions(width, height, 'HiResCanvas')
        if width == self.w and height == self.h:
            return
        new_buffer = [[Cell() for _ in range(width)] for _ in range(height)]
        for y in range(min(self.h, height)):
            src = self.buffer[y]
            dst = new_buffer[y]
            for x in range(min(self.w, width)):
                s = src[x]
                d = dst[x]
                d.char, d.fg, d.bg, d.z = s.char, s.fg, s.bg, s.z
                d.depth = s.depth
        self.buffer = new_buffer
        self.w = self.width = width
        self.h = self.height = height

    def to_canvas(self, canvas: Canvas, z: float = 0, blank: bool = False):
        """Fold each sub-cell pair into one half-block on ``canvas``.

        Empty sub-cells are skipped so a low-res background underneath shows
        through, unless ``blank`` is set, in which case they actively clear.
        """
        rows = canvas.height if canvas.height < self.h // 2 else self.h // 2
        cols = canvas.width if canvas.width < self.w else self.w
        for y in range(rows):
            t = self.buffer[y * 2]
            b = self.buffer[y * 2 + 1]
            for x in range(cols):
                top = t[x]
                bot = b[x]
                if top.fg is not None and bot.fg is not None:
                    canvas.set_pixel_exact(x, y, '▀', top.fg, bot.fg, z)
                elif top.fg is not None:
                    canvas.set_pixel_exact(x, y, '▀', top.fg, None, z)
                elif bot.fg is not None:
                    canvas.set_pixel_exact(x, y, '▄', bot.fg, None, z)
                elif blank:
                    canvas.set_pixel_exact(x, y, ' ', None, None, z)

    def copy(self) -> HiResCanvas:
        """A deep copy: mutating the result never touches this surface."""
        new_canvas = HiResCanvas(self.w, self.h)
        for y in range(self.h):
            row = self.buffer[y]
            nrow = new_canvas.buffer[y]
            for x in range(self.w):
                s = row[x]
                d = nrow[x]
                d.char, d.fg, d.bg, d.z = s.char, s.fg, s.bg, s.z
                d.depth = s.depth
        return new_canvas

    def __repr__(self):
        return f'HiResCanvas({self.w}x{self.h})'

