"""Scene composition: a low-res canvas, an optional HiRes surface, and
stacked overlay layers, presented together in one incremental frame."""

from __future__ import annotations


from .canvas import Canvas, HiResCanvas

__all__ = ['Layer', 'Scene']


class Layer:
    """A low-res overlay canvas fixed to a Scene, drawn at a given depth.

    Attribute access falls through to the layer's own canvas, so
    ``layer.draw_text(...)`` works without going through ``layer.canvas``.
    """

    def __init__(self, scene: Scene, name: str, z: float):
        object.__setattr__(self, 'scene', scene)
        object.__setattr__(self, 'name', name)
        object.__setattr__(self, 'z', z)
        object.__setattr__(self, 'canvas', Canvas(scene.w, scene.h))
        object.__setattr__(self, 'visible', True)

    def __getattr__(self, key):
        # __getattr__ only runs when normal lookup fails, so the attributes
        # set in __init__ are always found directly and the explicit guard is
        # only a backstop. The important case is 'canvas' itself: if it is
        # missing (a __init__ that raised partway, or __new__ without __init__)
        # then getattr(self.canvas, key) would recurse forever.
        if key.startswith('_') or key in ('scene', 'name', 'z', 'canvas',
                                          'visible'):
            raise AttributeError(key)
        canvas = self.__dict__.get('canvas')
        if canvas is None:
            raise AttributeError(key)
        return getattr(canvas, key)

    def clear(self):
        """Blank the layer's canvas."""
        self.canvas.clear()

    def resize(self, width: int, height: int):
        """Resize the layer's canvas, preserving content."""
        self.canvas.resize(width, height)

    def __repr__(self):
        return f'Layer({self.name!r}, z={self.z})'


class Scene:
    """Compositing container: one Canvas + one HiResCanvas + overlay layers.

        sc = Scene(100, 40)
        sc.hr.set_pixel(40, 50, '*', fg=gold, z=50)     # hires actors
        sc.fill_sky(Gradient(BLUE, DARK))               # bg on main canvas
        sc.layer('hud', z=90).draw_text(1, 1, 'SCORE')  # fixed overlay
        sc.present(sys.stdout)                           # compose + draw

    Attribute access falls through to the main canvas, so ``sc.draw_circle(...)``
    draws straight onto it. Pass ``hires=False`` to skip the HiRes surface;
    :attr:`surface` is then ``None``.
    """

    def __init__(self, width: int, height: int, hires: bool = True):
        self.w = width
        self.h = height
        self.hires_enabled = hires
        self.canvas = Canvas(width, height)
        self.hr = HiResCanvas(width, height * 2) if hires else None
        self._layers: list = []

    @property
    def main(self) -> Canvas:
        """The low-resolution canvas (the compositing target)."""
        return self.canvas

    @property
    def surface(self):
        """The HiRes surface, or ``None`` when the scene was built with
        ``hires=False``."""
        return self.hr

    def __getattr__(self, key):
        if key.startswith('_'):
            raise AttributeError(key)
        # Guard against infinite recursion: if 'canvas' is not in __dict__ the
        # getattr below would call __getattr__ again with the same key.
        canvas = self.__dict__.get('canvas')
        if canvas is None:
            raise AttributeError(key)
        return getattr(canvas, key)

    def resize(self, width: int, height: int):
        """Resize the scene and every layer, preserving content.

        The HiRes surface keeps its 2x vertical resolution, so it becomes
        ``width x height * 2``. Call this from a ``ResizeEvent`` handler: the
        engine detects terminal resizes but never resizes a surface on its own.
        """
        self.w = width
        self.h = height
        self.canvas.resize(width, height)
        if self.hr is not None:
            self.hr.resize(width, height * 2)
        for lay in self._layers:
            lay.canvas.resize(width, height)

    def layer(self, name: str = 'layer', z: float = 0) -> Layer:
        """Create (or fetch) an overlay layer canvas by name."""
        for lay in self._layers:
            if lay.name == name:
                lay.z = z
                return lay
        lay = Layer(self, name, z)
        self._layers.append(lay)
        return lay

    def get_layer(self, name: str, z: float = 0) -> Layer:
        return self.layer(name, z)

    def clear(self):
        self.canvas.clear()
        if self.hr is not None:
            self.hr.clear()
        for lay in self._layers:
            lay.canvas.clear()

    def compose(self, z: float = 0):
        """Blit hires actors + overlay layers onto the main canvas.

        Empty hires cells are skipped, so low-res background remains intact;
        pass ``hr`` cells drawn at z >= ``z`` to stack them above it."""
        if self.hr is not None:
            self.hr.to_canvas(self.canvas, z=z)
        for lay in sorted((l for l in self._layers if l.visible), key=lambda l: l.z):
            self.canvas.blit_canvas(lay.canvas)

    def present(self, stream, z: float = 0, clear_first: bool = True):
        self.compose(z)
        self.canvas.render_to(stream, clear_first)

    def __repr__(self):
        return f'Scene({self.w}x{self.h}, {len(self._layers)} layers)'