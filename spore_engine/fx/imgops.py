"""Array-level image pipeline: the intermediate representation the cell API
lacks.

Every visual in this engine used to be built straight into :class:`Cell`
objects. That works for a sprite, but a *picture* wants a different order of
operations: generate scalar and colour fields, combine them as light, grade the
result, and only then quantise into cells. Writing that against
:meth:`Canvas.set_pixel` means a per-cell Python loop, and it puts the
expensive things - bloom, tonemap, vignette - after the point where the half
block fold has already thrown half the image away.

The cell-level :mod:`spore_engine.fx.postfx` filters cannot fix that. Eight of
the nine read and write ``Cell.fg`` only, and on a folded surface each cell is
``char='▀', fg=top sub-cell, bg=bottom sub-cell``, so they light the top half
and leave the bottom sharp. :func:`to_cells` is the single exit from this
module, and it writes both halves.

Two types carry the whole pipeline:

``Field``
    A scalar field: a ``(h, w)`` or ``(w,)`` float32 array over a pixel grid.
    Generators live on it as static methods (``Field.fbm``, ``Field.plasma``,
    ``Field.radial``, ...) so they add no module-level names, and so a field
    reads as one value from beginning to end.

``Image``
    A linear-light colour image: a ``(h, w, 3)`` float32 array with values
    nominally in 0-255 to match :class:`~spore_engine.Color`. Combination is
    photometric - :meth:`Image.add` is light addition, :meth:`Image.over` is
    alpha compositing, :meth:`Image.absorb` is the Beer-Lambert-ish lerp a
    mirror or a fog needs. Grading is :meth:`Image.tonemap`,
    :meth:`Image.bloom`, :meth:`Image.vignette`.

    ::

        img = Image.ramp('y', sky_gradient, h, w)
        img.add(Field.radial(h, w, cx, cy, r) * palette)
        img = img.tonemap().bloom(0.8, 2, 0.5).vignette(0.5)
        img.to_cells(hr, cache=cache)

Values are *linear* light, not gamma-encoded, which is why the grade reads
``Rec.709`` on the raw array and why ``to_cells`` is the only place a
quantisation decision is made.
"""

from __future__ import annotations

import math
import random
import weakref

import numpy as np

from ..core.canvas import HiResCanvas
from ..core.color import WHITE, Color, Gradient, fast_color
from ..sim.noise import PerlinNoise

__all__ = [
    'CellCache',
    'Field',
    'Image',
    'StarField',
    'to_cells',
]

#: Rec.709 luma weights, the one expression this codebase has otherwise
#: copy-pasted into nine places.
_LUMA = np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)

_new = object.__new__
_set = object.__setattr__


def _f32(a, name='array'):
    """Coerce to a C-contiguous float32 array, with a clear error on junk."""
    arr = np.asarray(a, dtype=np.float32)
    if arr.dtype != np.float32:            # pragma: no cover - defensive
        raise TypeError(f'{name} must be float32, got {arr.dtype}')
    return np.ascontiguousarray(arr)


def _fit(a: np.ndarray, shape) -> np.ndarray:
    """Match a gain/mask field to ``shape``, broadcasting before resizing.

    A per-row ``(h, 1)`` or per-column ``(1, w)`` field is a *broadcast* in
    numpy terms and almost always what the caller means - one value per row,
    held across the width. Resizing it instead silently interpolates a single
    column into a gradient, which produces a wrong picture and no error. So
    broadcast first and only fall back to a resize when the shape genuinely
    cannot be broadcast.
    """
    if a.shape == shape:
        return a
    try:
        return np.broadcast_to(a, shape)
    except ValueError:
        return Field(a).resized(*shape).a


def _operand(other, shape):
    """Resolve a composite operand to an array that broadcasts over ``shape``.

    An :class:`Image` is used as it is and a :class:`Field` gains a channel
    axis. A colour becomes a *broadcast view*, never a materialised full-frame
    copy - tinting a frame with three numbers should not cost a frame of
    allocation and memory traffic. A 1-D array is read as one value per column.
    """
    if isinstance(other, Image):
        return other.a
    if isinstance(other, Field):
        return other.a[..., None]
    if isinstance(other, Color) or np.isscalar(other):
        return np.broadcast_to(_vec3(other), shape)
    arr = np.asarray(other, dtype=np.float32)
    if arr.ndim == 1:
        return arr[None, :, None]
    return arr[..., None]


def _as_field(other):
    """Coerce a number or an array to a ``Field``; pass a ``Field`` through."""
    if isinstance(other, Field):
        return other
    if np.isscalar(other):
        return Field(np.full((), float(other), dtype=np.float32))
    return Field(other)


def _vec3(color, gain=1.0):
    if isinstance(color, Color):
        return np.array([color.r, color.g, color.b], dtype=np.float32) * gain
    arr = np.asarray(color, dtype=np.float32)
    if arr.shape not in ((3,), ()):
        raise ValueError(f'colour must have 3 channels, got shape {arr.shape}')
    return arr.reshape(3) * gain


#: Baked ramps, keyed weakly by the :class:`Gradient` they came from. Sampling a
#: ramp costs 256 ``Gradient.at`` calls - about 0.6ms - and a frame that walks
#: an aurora through a ramp per layer asked for the same table three times a
#: frame, every frame. A weak key means a ramp built inside a function is still
#: collected with it.
_LUT_CACHE: weakref.WeakKeyDictionary = weakref.WeakKeyDictionary()


def _gradient_lut(stops, n: int) -> np.ndarray:
    """Sample a colour ramp into an (n, 3) table - one pass, not one per cell."""
    if not isinstance(stops, Gradient):
        stops = Gradient(*stops)
    if n < 1:
        raise ValueError(f'a ramp needs at least one sample, got {n}')
    cached = _LUT_CACHE.get(stops)
    if cached is not None and cached.shape[0] == n:
        return cached
    span = max(1, n - 1)
    lut = np.array([(stops.at(i / span).r, stops.at(i / span).g,
                     stops.at(i / span).b) for i in range(n)], dtype=np.float32)
    _LUT_CACHE[stops] = lut
    return lut


def _integral(a):
    """Summed-area table with a zero row and column, so a window sum is O(1)."""
    out = np.zeros((a.shape[0] + 1, a.shape[1] + 1), dtype=np.float64)
    out[1:, 1:] = a.astype(np.float64).cumsum(axis=0).cumsum(axis=1)
    return out


def _window(ii, y0, y1, x0, x1):
    """Sum over the half-open box [y0, y1) x [x0, x1) of a summed-area table."""
    return ii[y1, x1] - ii[y0, x1] - ii[y1, x0] + ii[y0, x0]


def _grid(w, h):
    """Pixel-centre coordinate grids, shaped for broadcasting against (h, w)."""
    return (np.arange(w, dtype=np.float32)[None, :],
            np.arange(h, dtype=np.float32)[:, None])


# ---------------------------------------------------------------------------
# Field
# ---------------------------------------------------------------------------

class Field:
    """A scalar field over a pixel grid: a float32 array of shape (h, w) or (w,).

    Arithmetic is elementwise and returns a new ``Field``; a bare number is
    broadcast. Operations that produce a colour return an :class:`Image`.
    """

    __slots__ = ('a',)

    def __init__(self, a):
        self.a = _f32(a, 'Field')

    # -- construction ------------------------------------------------------

    @classmethod
    def zeros(cls, shape) -> Field:
        return cls(np.zeros(shape, dtype=np.float32))

    @classmethod
    def full(cls, shape, value=0.0) -> Field:
        return cls(np.full(shape, value, dtype=np.float32))

    # -- generators --------------------------------------------------------

    @classmethod
    def fbm_line(cls, noise: PerlinNoise, width: int, freq: float, drift: float = 0.0,
                 offset: float = 0.0, octaves: int = 3, gain: float = 1.0) -> Field:
        """A 1-D fBm trace of length ``width``, via the engine's grid sampler.

        Every silhouette in the engine wants a per-column fBm, and a frame wants
        a dozen of them. Looping ``PerlinNoise.fbm1`` per column costs about
        0.5ms at 200 columns; the JIT-compiled grid kernel costs about 0.03ms.
        """
        if freq == 0.0 or width < 1:
            return cls.full((max(1, width),), 0.5 * gain)
        grid = noise.fbm2d_grid(width, 1, scale=freq, ox=(drift + offset) / freq,
                                oy=offset * 0.37, octaves=octaves)
        return cls((grid[0] * 0.5 + 0.5).astype(np.float32) * gain)

    @classmethod
    def fbm(cls, noise: PerlinNoise, height: int, width: int, scale: float = 0.01,
            ox: float = 0.0, oy: float = 0.0, octaves: int = 4,
            gain: float = 1.0) -> Field:
        """A 2-D fBm field over an (h, w) grid."""
        grid = noise.fbm2d_grid(width, height, scale=scale, ox=ox, oy=oy, octaves=octaves)
        return cls(grid.astype(np.float32) * gain)

    @classmethod
    def plasma(cls, height: int, width: int, terms=((1.0, 0.6, 0.0, 1.0, 0.5, 0.0),),
               t: float = 0.0) -> Field:
        """Multi-sine interference, normalised to roughly 0-1.

        ``terms`` is a sequence of ``(kx, ky, kr, omega, amp, phase)`` triples.
        This is the single most reused generator in the demo corpus - five of the
        hand-written scenes inline a variant of it, and ``fx.effects.plasma`` is
        a sixth.
        """
        xx, yy = _grid(width, height)
        total = np.zeros((height, width), dtype=np.float32)
        norm = 0.0
        for kx, ky, kr, omega, amp, phase in terms:
            v = (kx * xx + ky * yy + kr * np.hypot(xx - width * 0.5,
                                                   yy - height * 0.5))
            total += amp * np.sin(v + t * omega + phase)
            norm += abs(amp)
        if norm == 0.0:
            return cls.zeros((height, width))
        return cls(total / (2.0 * norm) + 0.5)

    @classmethod
    def radial(cls, height: int, width: int, cx: float, cy: float,
               sx: float, sy: float | None = None, power: float = 2.0) -> Field:
        """A normalised radial falloff, 1.0 at the centre and 0 at the rim."""
        xx, yy = _grid(width, height)
        sy = sx if sy is None else sy
        if sx == 0 or sy == 0:
            raise ValueError('radial() needs a non-zero radius')
        d = np.sqrt(((xx - cx) / sx) ** 2 + ((yy - cy) / sy) ** 2)
        return cls(np.clip(1.0 - d, 0.0, 1.0) ** power)

    @classmethod
    def gauss(cls, height: int, width: int, cx: float, cy: float,
              sigma: float, gain: float = 1.0) -> Field:
        """An isotropic Gaussian blob, unbounded."""
        xx, yy = _grid(width, height)
        d2 = (xx - cx) ** 2 + (yy - cy) ** 2
        return cls(np.exp(-d2 / (2.0 * sigma * sigma)).astype(np.float32) * gain)

    @classmethod
    def waves(cls, height: int, width: int, octaves: int = 4, t: float = 0.0,
              direction: str = 'y') -> Field:
        """A band-limited sine sum - the base of most water and shimmer."""
        xx, yy = _grid(width, height)
        acc = np.zeros((height, width), dtype=np.float32)
        norm = 0.0
        for k in range(octaves):
            f = 0.05 * (2.0 ** k)
            amp = 0.6 ** k
            phase = xx * f * 6.28318 + yy * f * 3.1 + t * (0.5 + 0.3 * k)
            acc += amp * (np.sin(phase) if direction == 'both' or direction == 'y'
                          else np.cos(phase))
            norm += amp
        return cls(acc / norm * 0.5 + 0.5)

    # -- shape / access ----------------------------------------------------

    @property
    def shape(self):
        return self.a.shape

    def copy(self) -> Field:
        return Field(self.a.copy())

    def resized(self, height: int, width: int) -> Field:
        """Nearest-neighbour resample of a ``(w,)`` or ``(h, w)`` field.

        A colour block is not a field - its trailing axis is channels, not
        space - so :meth:`Image.resized` indexes its own axes instead.
        """
        a = self.a
        if a.ndim == 1:
            xi = np.arange(width, dtype=np.int32) * a.shape[0] // max(1, width)
            return Field(a[xi])
        if a.ndim != 2:
            raise ValueError(f'resized() needs a 1-D or 2-D field, got shape {a.shape}')
        h, w = a.shape
        if (h, w) == (height, width):
            return self.copy()
        yi = np.arange(height, dtype=np.int32) * h // max(1, height)
        xi = np.arange(width, dtype=np.int32) * w // max(1, width)
        return Field(a[yi[:, None], xi[None, :]])

    def row(self, index) -> np.ndarray:
        """The raw 1-D array of a ``(w,)`` field, for fast per-column maths."""
        if self.a.ndim != 1:
            raise ValueError(f'row() needs a 1-D field, got shape {self.a.shape}')
        return self.a[index]

    # -- elementwise maths -------------------------------------------------

    def _binop(self, other, op):
        o = other.a if isinstance(other, Field) else np.float32(other)
        try:
            return Field(op(self.a, o))
        except ValueError as exc:
            raise ValueError(f'shape mismatch {self.a.shape} vs {np.shape(o)}') from exc

    def __add__(self, other):
        return self._binop(other, np.add)

    __radd__ = __add__

    def __sub__(self, other):
        return self._binop(other, np.subtract)

    def __rsub__(self, other):
        return Field(np.subtract(np.float32(other), self.a))

    def __mul__(self, other):
        return self._binop(other, np.multiply)

    __rmul__ = __mul__

    def __truediv__(self, other):
        return self._binop(other, np.divide)

    def __neg__(self):
        return Field(-self.a)

    def __pow__(self, p):
        return Field(np.power(self.a, p, dtype=np.float32))

    def __getitem__(self, key):
        return Field(self.a[key])

    def __repr__(self):
        return f'Field(shape={self.a.shape})'

    # -- shaping -----------------------------------------------------------

    def clip(self, lo: float = 0.0, hi: float = 1.0) -> Field:
        return Field(np.clip(self.a, lo, hi, dtype=np.float32))

    def abs(self) -> Field:
        return Field(np.abs(self.a))

    def sqrt(self) -> Field:
        return Field(np.sqrt(np.maximum(self.a, 0.0), dtype=np.float32))

    def smoothstep(self, lo: float = 0.0, hi: float = 1.0) -> Field:
        """Hermite ease, flat at both ends."""
        t = np.clip((self.a - lo) / (hi - lo if hi != lo else 1.0), 0.0, 1.0)
        return Field((t * t * (3.0 - 2.0 * t)).astype(np.float32))

    def threshold(self, lo: float, hi: float | None = None) -> Field:
        """A linear ramp from 0 at ``lo`` to 1 at ``hi`` (instant if ``hi`` is
        omitted). The workhorse for masking a highlight out of a sum."""
        if hi is None:
            return Field((self.a > lo).astype(np.float32))
        return Field(np.clip((self.a - lo) / (hi - lo if hi != lo else 1.0), 0.0, 1.0))

    def shifted(self, dx: float, dy: float = 0.0) -> Field:
        """Translate by whole pixels, filling the gap with zeros.

        Offsets are rounded to integers: a sub-pixel shift is a resample, and
        :meth:`Image.displaced` is that. This is the cheap one, for wrapping a
        field inside a frame.
        """
        dx, dy = round(dx), round(dy)
        out = np.zeros_like(self.a)
        h, w = self.a.shape[-2], self.a.shape[-1]
        sx0, sx1 = max(0, dx), min(w, w + dx)
        sy0, sy1 = max(0, dy), min(h, h + dy)
        if sx1 > sx0 and sy1 > sy0:
            out[..., sy0:sy1, sx0:sx1] = self.a[..., sy0 - dy:sy1 - dy, sx0 - dx:sx1 - dx]
        return Field(out)

    def dilate(self, radius: int = 1, op: str = 'max') -> Field:
        """Square max- or min-dilation - the morphological bloom halo."""
        if radius < 1:
            return self.copy()
        fn = np.maximum if op == 'max' else np.minimum
        if op not in ('max', 'min'):
            raise ValueError(f"dilate() op must be 'max' or 'min', got {op!r}")
        a = self.a
        for _ in range(radius):
            m = a.copy()
            m[..., 1:, :] = fn(m[..., 1:, :], a[..., :-1, :])
            m[..., :-1, :] = fn(m[..., :-1, :], a[..., 1:, :])
            m[..., :, 1:] = fn(m[..., :, 1:], a[..., :, :-1])
            m[..., :, :-1] = fn(m[..., :, :-1], a[..., :, 1:])
            a = m
        return Field(a)

    def blurred(self, radius: int = 1) -> Field:
        """A separable box blur, edge-padded.

        The running sum needs a zero column prepended, or the first window is
        short by one and the whole field shifts down the image.
        """
        if radius < 1:
            return self.copy()
        k = 2 * radius + 1
        a = self.a.astype(np.float64)
        for axis in (-2, -1):
            pad_width = [(0, 0)] * a.ndim
            pad_width[axis] = (radius, radius)
            padded = np.pad(a, pad_width, mode='edge')
            running = np.cumsum(padded, axis=axis)
            running = np.concatenate(
                [np.zeros_like(np.take(running, [0], axis=axis)), running], axis=axis)
            a = (np.take(running, np.arange(k, running.shape[axis]), axis=axis)
                 - np.take(running, np.arange(0, running.shape[axis] - k), axis=axis)) / k
        return Field(a.astype(np.float32))

    # -- to colour ---------------------------------------------------------

    def tinted(self, color, gain: float = 1.0) -> Image:
        """This field's shape, scaled by ``gain``, filled with one colour."""
        v = _vec3(color) * gain
        return Image(self.a[..., None] * v)

    def palette(self, gradient) -> Image:
        """Map this field through a :class:`Gradient` to a colour image.

        The ramp is sampled once and cached against the :class:`Gradient`, so
        calling this per layer per frame - an aurora walking a curtain ramp -
        costs a gather rather than 256 ramp evaluations.
        """
        if not isinstance(gradient, Gradient):
            gradient = Gradient(*(gradient if isinstance(gradient, (list, tuple))
                                   else [gradient]))
        n = 256
        lut = _gradient_lut(gradient, n)
        idx = np.clip(self.a * (n - 1), 0, n - 1).astype(np.int32)
        return Image(lut[idx])

    def to_cells(self, surface, z: float = 0, cache: CellCache | None = None) -> None:
        """Write this field as a greyscale image."""
        self.tinted(WHITE).to_cells(surface, z, cache)


# ---------------------------------------------------------------------------
# Image
# ---------------------------------------------------------------------------

class Image:
    """A linear-light colour image: float32 ``(h, w, 3)``, nominally 0-255.

    Combination is photometric. :meth:`add` is light addition (a star, an
    emissive surface, a bloom); :meth:`over` is alpha compositing (a silhouette
    in front of a sky); :meth:`absorb` and :meth:`mix` are the lerps a mirror
    or a fog needs.
    """

    __slots__ = ('a',)

    def __init__(self, a):
        arr = np.asarray(a, dtype=np.float32)
        if arr.ndim != 3 or arr.shape[2] != 3:
            raise ValueError(f'Image needs shape (h, w, 3), got {arr.shape}')
        self.a = _f32(arr, 'Image')

    # -- construction ------------------------------------------------------

    @classmethod
    def zeros(cls, shape) -> Image:
        return cls(np.zeros((*shape, 3), dtype=np.float32))

    @classmethod
    def full(cls, shape, color=(0, 0, 0)) -> Image:
        return cls(np.broadcast_to(_vec3(color), (*shape, 3)).copy())

    @classmethod
    def gradient(cls, axis: str, stops, height: int, width: int) -> Image:
        """A 1-D colour gradient broadcast to fill an (h, w) image.

        ``stops`` is a :class:`Gradient` or a list of colours, sampled once per
        row or column rather than once per cell.
        """
        if axis not in ('x', 'y'):
            raise ValueError(f"gradient() axis must be 'x' or 'y', got {axis!r}")
        lut = _gradient_lut(stops, height if axis == 'y' else width)
        # tile positionally against the array's own dims, so a 2-D lut needs a
        # middle axis inserted before the y case can broadcast across width
        column = (np.tile(lut[:, None, :], (1, width, 1)) if axis == 'y'
                  else np.tile(lut[None, :, :], (height, 1, 1)))
        return Image(column)

    @classmethod
    def from_field(cls, field, color=(255, 255, 255), gain: float = 1.0) -> Image:
        return Field(field).tinted(color, gain)

    @classmethod
    def from_surface(cls, surface) -> Image:
        """Read a surface back into a linear-light image.

        The inverse of :meth:`to_cells`, and the escape hatch for a picture that
        mixes array work with something that draws into cells directly - a 3-D
        pass such as :func:`~spore_engine.render3d.render_mesh_solid`, which
        shades and z-buffers itself and so cannot be an array op.

        Lossy in one specific way: glyphs and depth are dropped, and what comes
        back is the colour of each sub-cell. A hi-res surface gives two samples
        per terminal cell, so the round trip is lossless for colour; a low-res
        canvas gives one.
        """
        h = getattr(surface, 'h', None) or surface.height
        w = getattr(surface, 'w', None) or surface.width
        out = np.zeros((h, w, 3), dtype=np.float32)
        sub_is_fg = _sub_cell(surface)
        for y in range(h):
            row = surface.buffer[y]
            for x in range(w):
                cell = row[x]
                color = cell.fg if sub_is_fg else (cell.bg or cell.fg)
                if color is not None:
                    out[y, x] = (color.r, color.g, color.b)
        return cls(out)

    # -- shape / access ----------------------------------------------------

    @property
    def shape(self):
        return self.a.shape[:2]

    def copy(self) -> Image:
        return Image(self.a.copy())

    def rows(self, start: int, stop: int) -> Image:
        """A row slice, for building a picture in bands."""
        return Image(self.a[start:stop])

    def resized(self, height: int, width: int) -> Image:
        """Nearest-neighbour resample. Indexes axes 0 and 1 - the trailing axis
        is channels, so this cannot go through :meth:`Field.resized`."""
        h, w = self.shape
        if (h, w) == (height, width):
            return self.copy()
        yi = np.arange(height, dtype=np.int32) * h // max(1, height)
        xi = np.arange(width, dtype=np.int32) * w // max(1, width)
        return Image(self.a[yi[:, None], xi[None, :], :])

    def scattered(self, points) -> Image:
        """Black image with additive ``(x, y, r, g, b)`` points stamped in.

        Duplicate coordinates accumulate, which is what a star field wants when
        two stars land on one sub-cell.
        """
        h, w = self.shape
        out = np.zeros((h, w, 3), dtype=np.float32)
        if not len(points):
            return Image(out)
        arr = np.asarray(points, dtype=np.float32).reshape(-1, 5)
        xi = np.clip(arr[:, 0].astype(np.int32), 0, w - 1)
        yi = np.clip(arr[:, 1].astype(np.int32), 0, h - 1)
        for ch in range(3):
            np.add.at(out[:, :, ch], (yi, xi), arr[:, 2 + ch])
        return Image(out)

    def placed(self, other, y: int, x: int = 0) -> Image:
        """``other`` composited over this image at (y, x), clipped to bounds."""
        out = self.copy()
        h, w = out.shape
        oh, ow = other.shape
        y0, x0 = max(0, y), max(0, x)
        y1, x1 = min(h, y + oh), min(w, x + ow)
        if y1 <= y0 or x1 <= x0:
            return out
        out.a[y0:y1, x0:x1] = other.a[y0 - y:y1 - y, x0 - x:x1 - x]
        return out

    def stacked(self, other) -> Image:
        """This image above ``other`` - a sky above a sea."""
        if self.shape[1] != other.shape[1]:
            raise ValueError(f'width mismatch {self.shape[1]} vs {other.shape[1]}')
        return Image(np.concatenate((self.a, other.a), axis=0))

    def __getitem__(self, key):
        return Image(self.a[key])

    def __mul__(self, other):
        return self.scaled(other)

    __rmul__ = __mul__

    def __truediv__(self, k):
        return self.scaled(1.0 / float(k))

    def __repr__(self):
        return f'Image(shape={self.shape})'

    # -- photometric combination -------------------------------------------

    def add(self, other, gain=1.0) -> Image:
        """Additive light. The default way to put something in a picture.

        Dispatch is on the type of ``other``, which is never ambiguous:

        - an :class:`Image` is added, scaled by ``gain``;
        - a :class:`Field` or array is a *scalar* field - grey light, scaled by
          ``gain``, or tinted by a :class:`Color` or 3-sequence ``gain``, so
          ``img.add(f, Color(0, 255, 120))`` reads the way it looks;
        - a colour is broadcast, scaled by ``gain``.

        Every path costs one frame of allocation: the result is built with
        ``np.multiply(..., out=v)`` and accumulated into, rather than as
        ``a + b * gain`` which allocates the scaled copy *and* the sum.
        """
        v = np.empty_like(self.a)
        if isinstance(other, Image):
            np.multiply(other.a, np.float32(gain), out=v)
        elif isinstance(other, (Field, np.ndarray)):
            field = other.a if isinstance(other, Field) else other
            if field.ndim == 2:
                # broadcast first: a per-row (h, 1) or per-column (1, w) field
                # is a view until it is multiplied, and the product then has to
                # be full-size for the in-place accumulate below
                field = np.broadcast_to(_fit(field, self.shape), self.shape)
            if isinstance(gain, Color) or (isinstance(gain, (tuple, list))
                                           and len(gain) == 3):
                np.multiply(field[..., None], _vec3(gain), out=v)
            else:
                v[:] = (field * np.float32(gain))[..., None]
        else:
            v[:] = _vec3(other, float(gain))
        v += self.a
        return Image(v)

    def over(self, other, alpha=1.0) -> Image:
        """Alpha composite ``other`` over this image."""
        a = _as_field(alpha).a
        if a.ndim == 1:
            a = a[:, None]
        k = np.clip(_fit(a, self.shape), 0.0, 1.0)[..., None] * np.float32(1.0)
        o = _operand(other, self.a.shape)
        v = self.a * (1.0 - k)
        v += o * k
        return Image(v)

    def mix(self, other, t=0.5) -> Image:
        """Linear interpolation towards ``other``."""
        tt = _as_field(t).a
        if tt.ndim == 1:
            tt = tt[:, None]
        tt = np.clip(_fit(tt, self.shape), 0.0, 1.0)[..., None]
        o = _operand(other, self.a.shape)
        v = self.a * (1.0 - tt)
        v += o * tt
        return Image(v)

    def absorb(self, color, amount) -> Image:
        """Lerp towards ``color`` by a per-pixel ``amount`` - a medium that
        something shines through."""
        return self.mix(color, amount)

    def scaled(self, gain) -> Image:
        g = _as_field(gain).a
        if g.ndim == 1:
            g = g[:, None]
        if g.shape != self.shape:
            g = _fit(g, self.shape)
        return Image(self.a * g[..., None])

    def luma(self) -> Field:
        """Rec.709 luminance as a :class:`Field`."""
        return Field(self.a @ _LUMA)

    def palette(self, gradient) -> Image:
        """Re-map this image's luminance through a :class:`Gradient`."""
        return self.luma().palette(gradient)

    def posterized(self, levels: int = 4) -> Image:
        if levels < 2:
            raise ValueError(f'posterize() needs levels >= 2, got {levels}')
        step = np.float32(255.0 / (levels - 1))
        return Image(np.round(np.clip(self.a, 0, 255) / step) * step)

    def scanlined(self, intensity: float = 0.3) -> Image:
        """Darken every other row - a CRT read."""
        a = self.a.copy()
        a[1::2] *= np.float32(1.0 - intensity)
        return Image(a)

    def pixelated(self, block: int = 3) -> Image:
        """Average each ``block x block`` tile down to one colour."""
        if block < 1:
            raise ValueError(f'pixelate() needs block >= 1, got {block}')
        if block == 1:
            return self.copy()
        h, w = self.shape
        bh, bw = -(-h // block), -(-w // block)
        padded = np.zeros((bh * block, bw * block, 3), dtype=np.float32)
        padded[:h, :w] = self.a
        tiles = padded.reshape(bh, block, bw, block, 3).mean(axis=(1, 3))
        return Image(np.repeat(np.repeat(tiles, block, axis=0), block, axis=1)[:h, :w])

    def chromatic(self, offset: int = 1) -> Image:
        """Split the channels sideways, scaled by distance from the centre."""
        if offset == 0:
            return self.copy()
        h, w = self.shape
        out = self.a.copy()
        xs = np.arange(w)
        out[:, xs, 0] = self.a[:, np.clip(xs + offset, 0, w - 1), 0]
        out[:, xs, 2] = self.a[:, np.clip(xs - offset, 0, w - 1), 2]
        return Image(out)

    def edged(self, strength: float = 0.35) -> Image:
        """Darken where luminance changes fast - a Sobel ink pass."""
        if strength == 0.0:
            return self.copy()
        luma = self.luma().a
        h, w = luma.shape
        # central differences by hand: np.gradient refuses a one-pixel axis
        gy = np.zeros_like(luma)
        gx = np.zeros_like(luma)
        if h > 1:
            gy[1:-1] = (luma[2:] - luma[:-2]) * 0.5
            gy[0], gy[-1] = luma[1] - luma[0], luma[-1] - luma[-2]
        if w > 1:
            gx[:, 1:-1] = (luma[:, 2:] - luma[:, :-2]) * 0.5
            gx[:, 0], gx[:, -1] = luma[:, 1] - luma[:, 0], luma[:, -1] - luma[:, -2]
        magnitude = np.hypot(gx, gy) * 4.0
        return self.scaled(1.0 - strength * np.clip(magnitude / 128.0, 0.0, 1.0))

    def blurred(self, radius: int = 1) -> Image:
        """A separable box blur over the colour channels."""
        if radius < 1:
            return self.copy()
        return Image(np.stack(
            [Field(self.a[:, :, ch]).blurred(radius).a for ch in range(3)], axis=2))

    def kuwahara(self, radius: int = 2) -> Image:
        """Painterly smoothing: per pixel, keep the flattest of four quadrants.

        A flattened-region estimate, which turns a noisy field into flat patches
        with hard boundaries. The cell-level
        :class:`~spore_engine.fx.shaders.KuwaharaFilter` was reaching for the
        same look, except that it reads only ``Cell.fg`` - so on a folded
        half-block surface it smoothed the top sub-cell and left the bottom
        sharp.
        """
        if radius < 1:
            return self.copy()
        h, w = self.shape
        r = radius + 1
        a = np.clip(self.a, 0.0, 255.0)
        luma = a @ _LUMA
        ii_luma = _integral(luma)
        ii_luma_sq = _integral(luma * luma)
        ii_chan = [_integral(a[:, :, ch]) for ch in range(3)]

        ys = np.arange(h)
        xs = np.arange(w)
        y0, y1 = np.clip(ys - r, 0, h)[:, None], np.clip(ys + 1, 0, h)[:, None]
        x0, x1 = np.clip(xs - r, 0, w)[None, :], np.clip(xs + 1, 0, w)[None, :]
        # the near edge of each quadrant is the pixel *inclusive*, or the window
        # is empty at the origin and the mean collapses to zero
        ym, xm = ys[:, None] + 1, xs[None, :] + 1
        quadrants = ((y0, ym, x0, xm), (y0, ym, xm, x1),
                     (ym, y1, x0, xm), (ym, y1, xm, x1))

        means = np.empty((4, h, w, 3), dtype=np.float32)
        variance = np.empty((4, h, w), dtype=np.float32)
        for qi, (qy0, qy1, qx0, qx1) in enumerate(quadrants):
            area = (qy1 - qy0) * (qx1 - qx0)
            count = np.maximum(area, 1).astype(np.float32)
            m1 = _window(ii_luma, qy0, qy1, qx0, qx1) / count
            m2 = _window(ii_luma_sq, qy0, qy1, qx0, qx1) / count
            # an empty window has zero variance and would always win the argmin,
            # so give it infinite variance and fall back to the pixel itself
            variance[qi] = np.where(area > 0, np.maximum(m2 - m1 * m1, 0.0), np.inf)
            for ch in range(3):
                quad = _window(ii_chan[ch], qy0, qy1, qx0, qx1) / count
                means[qi, :, :, ch] = np.where(area > 0, quad, a[:, :, ch])
        return Image(np.take_along_axis(means, np.argmin(variance, axis=0)[None, :, :, None],
                                        axis=0)[0])

    # -- resampling --------------------------------------------------------

    def sample_rows(self, rows) -> Image:
        """Gather rows of this image: ``rows[x]`` picks the source row for
        column ``x`` (a 1-D field), or a full ``(h, w)`` index field for a
        per-pixel gather.

        This is the mirror. A reflection about a horizon is a per-column row
        lookup plus a vertical squeeze, and doing it as an index rather than a
        per-pixel loop is what makes a real reflection affordable.
        """
        h, w = self.shape
        idx = np.clip(np.asarray(_as_field(rows).a, dtype=np.int32), 0, h - 1)
        if idx.ndim == 1:
            if idx.shape[0] != w:
                raise ValueError(f'sample_rows() got {idx.shape[0]} rows for {w} columns')
            # indexing axis 1 gives exactly out[y, x] == a[y, idx[x], :]
            return Image(self.a[:, idx, :])
        if idx.shape != (h, w):
            raise ValueError(f'sample_rows() index must be ({w},) or ({h}, {w}), '
                             f'got {idx.shape}')
        return Image(self.a[idx, np.arange(w, dtype=np.int32)[None, :]])

    def displaced(self, dx, dy=None, mode: str = 'clamp') -> Image:
        """Bilinear resample through a per-pixel offset field.

        The general form of what the six distort shaders in
        :mod:`spore_engine.fx.shaders` each hand-roll: wave, ripple, swirl,
        heat haze, warp, kaleidoscope. Offsets are in pixels, sampled at the
        destination.
        """
        if mode not in ('clamp', 'wrap'):
            raise ValueError(f"displaced() mode must be 'clamp' or 'wrap', got {mode!r}")
        h, w = self.shape
        yy, xx = np.meshgrid(np.arange(h, dtype=np.float32),
                             np.arange(w, dtype=np.float32), indexing='ij')
        sx = xx + _as_field(dx).resized(h, w).a
        sy = yy + (_as_field(dy).resized(h, w).a if dy is not None else np.float32(0))
        if mode == 'wrap':
            sx = np.mod(sx, w)
            sy = np.mod(sy, h)
        else:
            sx = np.clip(sx, 0, w - 1)
            sy = np.clip(sy, 0, h - 1)
        x0 = np.floor(sx)
        y0 = np.floor(sy)
        x1 = np.clip(x0 + 1, 0, w - 1)
        y1 = np.clip(y0 + 1, 0, h - 1)
        fx = (sx - x0)[..., None]
        fy = (sy - y0)[..., None]
        a = self.a
        return Image((a[np.floor(y0).astype(np.int32), x0.astype(np.int32)]
                      * (1 - fx) + a[np.floor(y0).astype(np.int32), x1.astype(np.int32)] * fx)
                     * (1 - fy)
                     + (a[y1.astype(np.int32), x0.astype(np.int32)]
                        * (1 - fx) + a[y1.astype(np.int32), x1.astype(np.int32)] * fx) * fy)

    # -- grading (still linear light) --------------------------------------

    def tonemapped(self, knee: float = 172.0) -> Image:
        """Roll off highlights exponentially above ``knee``.

        Below the knee the image is untouched, so a carefully built palette
        survives; above it, an over-bright region approaches white smoothly
        instead of clipping to a flat block.
        """
        span = 255.0 - knee
        a = self.a
        return Image(np.where(a <= knee, a,
                              knee + span * (1.0 - np.exp(-(a - knee) / span))))

    def bloomed(self, threshold: float = 205.0, radius: int = 2,
                intensity: float = 0.5, tint=(1.0, 0.96, 0.90)) -> Image:
        """Additive glare from the brightest regions.

        Two dilation radii, each squared, so the halo falls off fast instead of
        hazing the whole frame. Threshold high enough that only genuinely
        blown pixels bloom.
        """
        bright = self.luma().threshold(threshold, 255.0)
        near = bright.dilate(1, 'max') ** 2 * 0.62
        far = bright.dilate(radius, 'max') ** 2 * 0.30
        return self.add((near + far).tinted(tint, 255.0 * intensity))

    def vignetted(self, intensity: float = 0.5, power: float = 2.2) -> Image:
        """Darken toward the corners."""
        h, w = self.shape
        yv = (np.arange(h, dtype=np.float32) - (h - 1) * 0.5) / max(1.0, (h - 1) * 0.5)
        xv = (np.arange(w, dtype=np.float32) - (w - 1) * 0.5) / max(1.0, (w - 1) * 0.5)
        rad = np.sqrt(xv[None, :] ** 2 + yv[:, None] ** 2) * 0.72
        return self.scaled(1.0 - intensity * np.clip(rad, 0, 1) ** power)

    # -- the exit ----------------------------------------------------------

    def to_cells(self, surface, z: float = 0, cache: CellCache | None = None) -> None:
        """Quantise into a :class:`Canvas` or :class:`HiResCanvas`.

        The single point where an image becomes cells, and the only place a
        quantisation decision is made. On a hi-res surface the colour goes to
        ``fg`` and the half-block fold pairs it with the sub-cell below; on a
        low-res canvas it goes to ``bg`` with a blank glyph, which is the only
        way to show a solid colour in text mode.

        The image must be *exactly* the surface's size - it is not scaled or
        padded. A smaller image would silently leave the rest of the surface
        holding the previous frame, which is a worse failure than an error here.

        Pass a :class:`CellCache` to reuse ``Color`` objects across frames - see
        that class for why it matters.
        """
        h, w = self.shape
        if h == 0 or w == 0:
            return
        if getattr(surface, 'h', getattr(surface, 'height', 0)) != h or \
           getattr(surface, 'w', getattr(surface, 'width', 0)) != w:
            raise ValueError(
                f'image is {h}x{w} (h x w) but surface is '
                f'{surface.height}x{surface.width} (h x w); to_cells needs an '
                f'exact match - resample the image, or paint into a matching '
                f'surface')
        if cache is not None and cache.matches(h, w):
            cache.paint(self.a, surface, z)
        else:
            _paint_plain(self.a, surface, z)


def _sub_cell(surface):
    """Where a surface keeps a single colour: ``fg`` on hi-res, ``bg`` on low-res.

    ``HiResCanvas`` folds its pairs into ``char='▀', fg=top, bg=bottom``, so a
    hi-res sub-cell is a foreground. A ``Canvas`` cell has only one colour
    region that can be a solid fill, and that is the background - a blank glyph
    over a coloured ``bg``.
    """
    return isinstance(surface, HiResCanvas)


def _write_cell(cell, color, sub_is_fg, z):
    if sub_is_fg:
        cell.char = ' '
        cell.fg = color
        cell.bg = None
    else:
        cell.char = ' '
        cell.fg = None
        cell.bg = color
    cell.z = z


def _paint_plain(rgb, surface, z):
    """Write every cell with a freshly built Color. Correct, and allocation-heavy."""
    h, w = rgb.shape[:2]
    r8 = np.clip(rgb[:, :, 0], 0, 255).astype(np.uint8).tobytes()
    g8 = np.clip(rgb[:, :, 1], 0, 255).astype(np.uint8).tobytes()
    b8 = np.clip(rgb[:, :, 2], 0, 255).astype(np.uint8).tobytes()
    sub_is_fg = _sub_cell(surface)
    buf = surface.buffer
    for y in range(h):
        row = buf[y]
        off = y * w
        for x in range(w):
            k = off + x
            color = fast_color(r8[k], g8[k], b8[k])
            cell = row[x]
            _write_cell(cell, color, sub_is_fg, z)


# ---------------------------------------------------------------------------
# The colour cache
# ---------------------------------------------------------------------------

class CellCache:
    """Per-surface cache of immutable :class:`Color` objects, reused across frames.

    A frame that repaints every sub-cell allocates one ``Color`` per cell. At
    20k sub-cells that churn is enough to drive a full cyclic-GC pass every few
    frames, which measured as more than the whole rest of the render. ``Color``
    is immutable and hashed by value, so a sub-cell whose 8-bit value has not
    moved can keep the object it already holds - and in a slowly animating
    picture roughly four fifths of them have not moved.

    Sized to a surface; :meth:`matches` reports whether it still fits, so a
    resize is detected rather than indexing off the end.
    """

    __slots__ = ('colors', 'height', 'keys', 'width')

    def __init__(self, height: int, width: int):
        if height < 1 or width < 1:
            raise ValueError(f'CellCache needs a positive size, got {height}x{width}')
        self.height = height
        self.width = width
        self.keys = np.zeros((height, width), dtype=np.uint32)
        self.colors: list = [None] * (height * width)

    def matches(self, height: int, width: int) -> bool:
        return self.height == height and self.width == width

    def clear(self) -> None:
        self.keys[:] = 0
        self.colors = [None] * (self.height * self.width)

    def paint(self, rgb, surface, z: float = 0) -> None:
        """Write ``rgb`` into ``surface``, rebuilding only changed colours."""
        h, w = rgb.shape[:2]
        if not self.matches(h, w):
            raise ValueError(f'cache is {self.height}x{self.width}, image is {h}x{w}')
        r8 = np.clip(rgb[:, :, 0], 0, 255).astype(np.uint8)
        g8 = np.clip(rgb[:, :, 1], 0, 255).astype(np.uint8)
        b8 = np.clip(rgb[:, :, 2], 0, 255).astype(np.uint8)
        key = ((r8.astype(np.int32) << 16) | (g8.astype(np.int32) << 8)
               | b8.astype(np.int32)).astype(np.uint32)
        sub_is_fg = _sub_cell(surface)
        buf = surface.buffer
        new, set_attr = _new, _set
        colors, keys = self.colors, self.keys
        for y in range(h):
            row = buf[y]
            off = y * w
            krow, prow = key[y], keys[y]
            for x in range(w):
                k = off + x
                p = krow[x]
                color = colors[k]
                if color is None or p != prow[x]:
                    color = new(Color)
                    set_attr(color, 'r', r8[y, x])
                    set_attr(color, 'g', g8[y, x])
                    set_attr(color, 'b', b8[y, x])
                    colors[k] = color
                    prow[x] = p
                _write_cell(row[x], color, sub_is_fg, z)

    def __len__(self):
        return sum(1 for c in self.colors if c is not None)

    def __repr__(self):
        return f'CellCache({self.height}x{self.width}, {len(self)} colours built)'


def to_cells(image: Image, surface, z: float = 0, cache: CellCache | None = None) -> None:
    """Module-level alias for :meth:`Image.to_cells`."""
    image.to_cells(surface, z, cache)


# ---------------------------------------------------------------------------
# Stars
# ---------------------------------------------------------------------------

class StarField:
    """A twinkling star field with retained state.

    The demo corpus had three divergent implementations of this - one in
    :func:`spore_engine.fx.starfield` taking mutable ``[x, y, z]`` lists, one
    clone in ``scene_fx``, and one in a numpy scene. They disagreed on
    projection, brightness curve and lifetime.

    Positions are 0-1 *fractions* of the surface, so a resize rescales the
    field instead of indexing off the end of a list sized for the first frame.
    """

    def __init__(self, count: int = 300, seed: int = 0x5EED, warm: float = 0.12,
                 twinkle: float = 1.5, drift: float = 0.0):
        if count < 0:
            raise ValueError(f'StarField count must be >= 0, got {count}')
        rnd = random.Random(seed)
        self.warm = warm
        self.twinkle = twinkle
        self.drift = drift
        self.stars = [(rnd.random(), rnd.random() ** 1.4, rnd.random() * math.tau,
                        rnd.random() ** 2.6, rnd.random() < warm)
                      for _ in range(count)]

    def sample(self, t: float, width: int, height: int, gain: float = 130.0,
               threshold: float = 0.42):
        """Yield ``(x, y, r, g, b)`` for every star currently visible."""
        if width < 1 or height < 1:
            return []
        out = []
        for u, v, phase, brightness, warm in self.stars:
            tw = 0.5 + 0.5 * math.sin(t * self.twinkle + phase * 5.0 + u * 37.0)
            mag = tw * brightness
            if mag < threshold:
                continue
            x = int((u + t * self.drift) % 1.0 * width)
            y = int(min(v, 0.999) * height)
            if 0 <= x < width and 0 <= y < height:
                out.append((x, y, mag * gain * (1.18 if warm else 1.0),
                            mag * gain * 0.94,
                            mag * gain * (0.86 if warm else 1.28)))
        return out

    def draw(self, image: Image, t: float, **kwargs) -> Image:
        """Add the field to an :class:`Image` (additive light)."""
        h, w = image.shape
        return image.add(Image.zeros((h, w)).scattered(self.sample(t, w, h, **kwargs)))

    def draw_cells(self, surface, t: float, z: float = 40, gain: float = 200.0,
                   **kwargs) -> None:
        """Stamp the field straight into a surface, for effects that are not
        array-based, or that must land *on top of* a finished frame.

        The default gain is higher than :meth:`draw`'s because a sub-cell is
        half a terminal cell tall, so a star has to be brighter to read.
        """
        h = getattr(surface, 'h', surface.height)
        w = getattr(surface, 'w', surface.width)
        fg = _sub_cell(surface)
        for x, y, r, g, b in self.sample(t, w, h, gain=gain, **kwargs):
            if not (0 <= x < w and 0 <= y < h):
                continue
            cell = surface.buffer[y][x]
            color = fast_color(int(min(255, r)), int(min(255, g)), int(min(255, b)))
            if fg:
                cell.char = ' '
                cell.fg = color
                cell.bg = None
            else:
                cell.char = '·'
                cell.fg = color
            cell.z = z

    def __len__(self):
        return len(self.stars)

    def __repr__(self):
        return f'StarField({len(self.stars)} stars)'
