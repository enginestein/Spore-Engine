"""Uniform asset pipeline: sprites, palettes, meshes and text from files.

The whole engine loads game data the same way, through one store with
memoized loading. Any dedicated :class:`Assets` instance gives a private
cache; the module-level :data:`assets` store is a shared default for
convenience. The free functions (:func:`load_sprite`, :func:`load_palette`,
:func:`load_model`, :func:`load_text`) are the underlying loaders - the
``Assets`` *methods* are the ones that wrap the cache.

Sprite files (``.spr``, ``.aa`` or plain text) support a small header::

    # a comment                        (leading '# ' only)
    fg=#ffcc00                         optional default foreground
    bg=#000033                         optional default background
    #*=#ff0000                         per-glyph foreground override
    ....*....
    ...**....

Palette files list one colour per line as ``#rrggbb``, ``rrggbb`` or
``r,g,b`` (and ``r g b``).  Compute lines start with ``# ``.  Models are
plain Wavefront OBJ or PLY files routed to
:func:`~spore_engine.render3d.model_loader.load_obj` /
:func:`~spore_engine.render3d.model_loader.load_ply`.

Load failures are *not* memoized: a file that is missing now but created
later will load on the next call. Successful loads are cached until
:meth:`Assets.clear`.
"""

from __future__ import annotations

import os
from typing import Any
from collections.abc import Callable

from .canvas import Cell
from .color import Color
from .sprite import Sprite

__all__ = [
    'AssetError',
    'AssetNotFoundError',
    'AssetParseError',
    'Assets',
    'UnsupportedAssetError',
    'assets',
    'default_store',
    'load_model',
    'load_palette',
    'load_sprite',
    'load_text',
]


class AssetError(Exception):
    """Base class for asset-loading problems."""


class UnsupportedAssetError(AssetError):
    """The file extension is not one the engine can load."""


class AssetNotFoundError(AssetError):
    """The file does not exist (or could not be opened)."""


class AssetParseError(AssetError):
    """The file exists and its format is supported, but its contents are not
    valid - a truncated mesh, an unreadable header, a non-UTF-8 file."""


def _parse_color(token: str) -> Color | None:
    """One token to a Color: '#rrggbb'/'rrggbb', 'r,g,b' or 'r g b'.

    Returns ``None`` for anything unrecognised - the palette/sprite header
    loaders treat that as "skip this line" rather than an error, so a
    malformed optional header does not abort a load.
    """
    t = token.strip()
    if t.startswith('#'):
        if len(t) == 7:
            try:
                return Color.from_hex(t)
            except ValueError:
                return None
        return None
    if ',' in t:
        try:
            parts = [int(p) for p in t.split(',')]
        except ValueError:
            return None
        if len(parts) == 3:
            return Color(*parts)
        return None
    if ' ' in t:
        parts = t.split()
        try:
            if len(parts) == 3:
                return Color(int(parts[0]), int(parts[1]), int(parts[2]))
        except ValueError:
            return None
        return None
    if len(t) == 6:
        try:
            return Color.from_hex(t)
        except ValueError:
            return None
    return None


def _read_text(path: str) -> str:
    """Read a text asset, converting every failure into a typed AssetError.

    Callers used to see a bare ``FileNotFoundError``/``OSError``/
    ``UnicodeDecodeError`` and had to guess which was which; now a missing
    file, an unreadable file and a non-text file are all distinguishable.
    """
    try:
        with open(path, encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        raise AssetNotFoundError(f'asset not found: {path}') from None
    except IsADirectoryError:
        raise AssetNotFoundError(f'asset is a directory, not a file: {path}') from None
    except UnicodeDecodeError as exc:
        raise AssetParseError(
            f'asset is not valid UTF-8 text ({exc.reason}): {path}') from None
    except OSError as exc:
        raise AssetError(f'could not read asset {path}: {exc}') from None


def _read_sprite(text: str, fg: Color | None, bg: Color | None,
                 overrides: dict) -> Sprite:
    rows = []
    for line in text.rstrip('\n').split('\n'):
        row = []
        for ch in line:
            cf = overrides.get(ch, fg)
            row.append(Cell(char=ch, fg=cf, bg=bg))
        rows.append(row)
    return Sprite(rows)


def load_sprite(path: str, fg: Color | None = None,
                bg: Color | None = None) -> Sprite:
    """Load a sprite file into a core :class:`~spore_engine.core.sprite.Sprite`.

    Header lines (``# comment``, ``fg=``, ``bg=``, ``#<=color``) are consumed;
    the first non-header line starts the art, which is taken verbatim after
    that point.

    A blank or fully-commented file is a parse error, not an empty sprite: a
    silently zero-size sprite is nearly impossible to debug later.
    """
    text = _read_text(path)
    fg_col = fg
    bg_col = bg
    overrides: dict = {}
    header_done = False
    body: list = []
    for line in text.rstrip('\n').split('\n'):
        if not header_done:
            stripped = line.strip()
            if stripped == '' or stripped.startswith('# '):
                continue
            if line.startswith('fg='):
                val = _parse_color(line[3:])
                if val is None:
                    raise AssetParseError(
                        f'unreadable fg= header in {path}: {line[3:].strip()!r}')
                fg_col = val
                continue
            if line.startswith('bg='):
                val = _parse_color(line[3:])
                if val is None:
                    raise AssetParseError(
                        f'unreadable bg= header in {path}: {line[3:].strip()!r}')
                bg_col = val
                continue
            if line.startswith('#') and '=' in line[1:]:
                glyph, _, colors = line[1:].partition('=')
                if len(glyph) == 1 and glyph != ' ':
                    val = _parse_color(colors)
                    if val is None:
                        raise AssetParseError(
                            f'unreadable colour override for {glyph!r} in {path}')
                    overrides[glyph] = val
                    continue
            header_done = True
        body.append(line)
    if not body:
        raise AssetParseError(f'sprite file {path} contains no art')
    return _read_sprite('\n'.join(body), fg_col, bg_col, overrides)


def load_palette(path: str) -> list:
    """Load an ordered ramp of colors, one per line.

    A line may be a colour in any of the accepted forms (``#rrggbb``,
    ``rrggbb``, ``r,g,b``, ``r g b``) or a comment. ``#`` is ambiguous - it
    both starts a comment and a hex colour - so a ``#`` line is *tried* as a
    colour first and only treated as a comment if that fails.

    Blank lines and comments are ignored; any other line that is not a colour
    is an :class:`AssetParseError` with the line number, rather than being
    skipped - a palette that silently lost entries produces a ramp that is
    wrong everywhere and gives no clue why.
    """
    colors: list = []
    for lineno, line in enumerate(_read_text(path).split('\n'), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith('#') and _parse_color(stripped) is None:
            continue  # a genuine comment
        col = _parse_color(stripped)
        if col is None:
            raise AssetParseError(
                f'{path}:{lineno}: not a colour: {stripped!r}')
        colors.append(col)
    if not colors:
        raise AssetParseError(f'palette {path} contains no colors')
    return colors


def load_model(path: str, scale: float = 1,
               color: Color | None = None) -> Any:
    """Load an OBJ or PLY mesh into a ``render3d.Mesh3D``.

    Raises :class:`UnsupportedAssetError` for an extension the engine cannot
    load, :class:`AssetNotFoundError` if the file is missing, and
    :class:`AssetParseError` if the contents are not a valid mesh - the
    previous version returned a bare ``None`` for all three, so a typo in a
    path and a corrupt download looked identical at the call site.
    """
    ext = os.path.splitext(path)[1].lower()
    if ext not in ('.obj', '.ply'):
        raise UnsupportedAssetError(
            f'unsupported model format {ext!r} (expected .obj or .ply): {path}')
    if not os.path.isfile(path):
        raise AssetNotFoundError(f'model file not found: {path}')
    from ..render3d.model_loader import load_obj, load_ply
    try:
        mesh = (load_obj(path, scale, color) if ext == '.obj'
                else load_ply(path, scale, color))
    except (ValueError, IndexError) as exc:
        raise AssetParseError(f'malformed {ext} model {path}: {exc}') from None
    except OSError as exc:
        raise AssetError(f'could not read model {path}: {exc}') from None
    if mesh is None:
        # The mesh loaders swallow their own errors and return None, so
        # translate that back into the typed error the caller expects.
        raise AssetParseError(
            f'{ext} model {path} is malformed or contains no faces')
    return mesh


def load_text(path: str) -> str:
    """Load a text file verbatim (glyph tables, levels, dialogue)."""
    return _read_text(path)


class Assets:
    """Memoized loader store: each file is parsed at most once per key.

    Only *successful* loads are cached. A failure propagates as an
    :class:`AssetError` and is not remembered, so a file that appears on disk
    after a failed load will load correctly on the next call. Pass
    ``cache=False`` to disable memoization entirely.
    """

    def __init__(self, cache: bool = True):
        self._cache: dict | None = {} if cache else None

    def _get(self, key: tuple, loader: Callable[[], Any]) -> Any:
        if self._cache is None:
            return loader()
        if key in self._cache:
            return self._cache[key]
        value = loader()
        self._cache[key] = value
        return value

    def load_sprite(self, path: str, fg: Color | None = None,
                    bg: Color | None = None) -> Sprite:
        return self._get(('sprite', path, str(fg), str(bg)),
                         lambda: load_sprite(path, fg, bg))

    def load_palette(self, path: str) -> list:
        return self._get(('palette', path), lambda: load_palette(path))

    def load_model(self, path: str, scale: float = 1,
                   color: Color | None = None) -> Any:
        key = ('model', path, scale, str(color))
        return self._get(key, lambda: load_model(path, scale, color))

    def load_text(self, path: str) -> str:
        return self._get(('text', path), lambda: load_text(path))

    @property
    def cached(self) -> list:
        """The cache keys currently memoized."""
        return list(self._cache) if self._cache is not None else []

    def __len__(self) -> int:
        return len(self._cache) if self._cache is not None else 0

    def clear(self):
        """Drop every memoized load."""
        if self._cache is not None:
            self._cache.clear()

    def __repr__(self) -> str:
        return f'Assets({len(self)} cached)'


#: Shared default store. Prefer injecting your own :class:`Assets` into
#: long-lived objects (e.g. ``App(assets=Assets())``) so two engines in one
#: process do not share a cache.
assets = Assets()

#: Readable alias for :data:`assets`, so injection sites read as
#: ``App(assets=default_store)``.
default_store = assets
