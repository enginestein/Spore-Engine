"""The engine's glyph tables.

These are plain data with no dependencies, so both :mod:`~spore_engine.core.canvas`
and :mod:`~spore_engine.core.draw` can import them without an import cycle.
Every module that needs a shade ramp or a box-drawing character imports it from
here - previously the same ramp string was hardcoded in fourteen files.
"""

from __future__ import annotations

__all__ = [
           'BAR_CHARS',
           'BLOCK_CHARS',
           'LINE_CHARS',
           'SHADE_CHARS',
           'SHADE_DENSE',
           'SHADE_SPARSE',
]

#: Default dark-to-bright ramp used for luminance shading. NUL-last ordering is
#: deliberate: the ramp must be usable as a string *and* its last entry must be
#: the brightest glyph.
SHADE_CHARS = ' .:-=+*#%@'

#: Coarser ramps for low-resolution or high-contrast output.
SHADE_SPARSE = ' .:=#'
SHADE_DENSE = ' .\'`^",:;Il!i><~+_-?][}{1)(|\\/tfjrxnuvczXYUJCLQ0OZmwqpdbkhao*#MW&8%B@$'

#: Solid/partial block glyphs for high-resolution shading. The first four are
#: the sextant-free quadrants and upper blocks; the rest descend in density.
BLOCK_CHARS = '█▓▒░▀▄▌▐■□'

#: Single/vertical bar glyphs for sparklines and meters.
BAR_CHARS = '▁▂▃▄▅▆▇█'

#: Box-drawing characters keyed by their role in a frame.
LINE_CHARS = {'h': '─', 'v': '│', 'tl': '┌', 'tr': '┐', 'bl': '└', 'br': '┘',
              'tr_h': '┬', 'tl_h': '┴', 'cr': '├', 'cl': '┤', 'cross': '┼'}
