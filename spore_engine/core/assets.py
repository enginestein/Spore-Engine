"""Uniform asset pipeline: sprites, palettes, meshes and text from files.

The whole engine loads game data the same way, through one store with memoized
loading. ``load_sprite``/``load_palette``/``load_model``/``load_text`` wrap the
module-level ``assets`` store; any dedicated ``Assets()`` gives a private cache.

Sprite files (``.spr``, ``.aa`` or plain text) support a small header::

    # a comment                        (leading '# ' only)
    fg=#ffcc00                         optional default foreground
    bg=#000033                         optional default background
    #*=#ff0000                         per-glyph foreground override
    ....*....
    ...**....

Palette files list one color per line as ``#rrggbb``, ``rrggbb`` or
``r,g,b`` (and ``r g b``).  Compute lines start with ``# ``.  Models are
plain Wavefront OBJ or PLY files routed to ``render3d.load_obj`` /
``load_ply``.  Files are loaded once and cached until the cache rules say
otherwise; call ``assets.clear()`` to drop everything.
"""

from __future__ import annotations
import os
from typing import Optional

from .canvas import Cell
from .color import Color
from .sprite import Sprite


def _parse_color(token: str) -> Optional[Color]:
    """One token to a Color: '#rrggbb'/'rrggbb', 'r,g,b' or 'r g b'."""
    t = token.strip()
    if t.startswith('#'):
        if len(t) == 7:
            return Color.from_hex(t)
        return None
    if ',' in t:
        parts = [int(p) for p in t.split(',')]
        if len(parts) == 3:
            return Color(*parts)
        return None
    if len(t) == 6:
        try:
            return Color.from_hex(t)
        except ValueError:
            return None
    return None


def _read_sprite(text: str, fg: Optional[Color], bg: Optional[Color],
                 overrides: dict[str, Color]) -> Sprite:
    rows = []
    for line in text.rstrip('\n').split('\n'):
        row = []
        for ch in line:
            cf = overrides.get(ch, fg)
            row.append(Cell(char=ch, fg=cf, bg=bg))
        rows.append(row)
    return Sprite(rows)


def load_sprite(path: str, fg: Optional[Color] = None,
                bg: Optional[Color] = None) -> Sprite:
    """Load a sprite file into a core :class:`Sprite`.

    Header lines (``# comment``, ``fg=``, ``bg=``, ``#<=color``) are consumed;
    the first non-header line starts the art, which is taken verbatim after
    that point.
    """
    fg_col = fg
    bg_col = bg
    overrides: dict[str, Color] = {}
    header_done = False
    body: list[str] = []
    with open(path) as f:
        for line in f:
            line = line.rstrip('\n')
            if not header_done:
                stripped = line.strip()
                if stripped == '' or stripped.startswith('# '):
                    continue
                if line.startswith('fg='):
                    val = _parse_color(line[3:])
                    if val is not None:
                        fg_col = val
                    continue
                if line.startswith('bg='):
                    val = _parse_color(line[3:])
                    if val is not None:
                        bg_col = val
                    continue
                if line.startswith('#') and '=' in line[1:]:
                    glyph, _, colors = line[1:].partition('=')
                    if len(glyph) == 1 and glyph != ' ':
                        val = _parse_color(colors)
                        if val is not None:
                            overrides[glyph] = val
                        continue
                header_done = True
            body.append(line)
    return _read_sprite('\n'.join(body), fg_col, bg_col, overrides)


def load_palette(path: str) -> list[Color]:
    """Load an ordered ramp of colors, one per line."""
    colors: list[Color] = []
    with open(path) as f:
        for line in f:
            stripped = line.strip()
            if not stripped or stripped.startswith('# '):
                continue
            if ' ' in stripped and ',' not in stripped:
                parts = stripped.split()
                try:
                    col = Color(int(parts[0]), int(parts[1]), int(parts[2]))
                except (ValueError, IndexError):
                    col = None
            else:
                col = _parse_color(stripped)
            if col is not None:
                colors.append(col)
    return colors


def load_model(path: str, scale: float = 1,
               color: Optional[Color] = None) -> Optional[object]:
    """Load an OBJ or PLY mesh into a ``render3d.Mesh3D`` (or None on failure)."""
    ext = os.path.splitext(path)[1].lower()
    if ext not in ('.obj', '.ply') or not os.path.exists(path):
        return None
    from ..render3d.model_loader import load_obj, load_ply
    if ext == '.obj':
        return load_obj(path, scale, color)
    return load_ply(path, scale, color)


def load_text(path: str) -> str:
    """Load a text file verbatim (glyph tables, levels, dialogue)."""
    with open(path) as f:
        return f.read()


class Assets:
    """Memorized loader store: each file is parsed at most once per key."""

    def __init__(self, cache: bool = True):
        self._cache: dict[tuple, object] = {} if cache else None

    def _get(self, key: tuple, loader):
        if self._cache is None:
            return loader()
        if key not in self._cache:
            self._cache[key] = loader()
        return self._cache[key]

    def load_sprite(self, path: str, fg: Optional[Color] = None,
                    bg: Optional[Color] = None) -> Sprite:
        return self._get(('sprite', path, str(fg), str(bg)),
                         lambda: load_sprite(path, fg, bg))

    def load_palette(self, path: str) -> list[Color]:
        return self._get(('palette', path), lambda: load_palette(path))

    def load_model(self, path: str, scale: float = 1,
                   color: Optional[Color] = None) -> Optional[object]:
        key = ('model', path, scale, str(color))
        return self._get(key, lambda: load_model(path, scale, color))

    def load_text(self, path: str) -> str:
        return self._get(('text', path), lambda: load_text(path))

    @property
    def cached(self) -> list[tuple]:
        return list(self._cache) if self._cache is not None else []

    def __len__(self):
        return len(self._cache) if self._cache is not None else 0

    def clear(self):
        if self._cache is not None:
            self._cache.clear()

    def __repr__(self):
        n = len(self)
        return f'Assets({n} cached)'


assets = Assets()