from __future__ import annotations
from typing import Optional
from .canvas import Canvas, HiResCanvas


class Layer:
    """A low-res overlay canvas fixed to a Scene, drawn at a given depth."""

    def __init__(self, scene: 'Scene', name: str, z: float):
        self.scene = scene
        self.name = name
        self.z = z
        self.canvas = Canvas(scene.w, scene.h)
        self.visible = True

    def __getattr__(self, key):
        if key.startswith('_') or key in ('scene', 'name', 'z', 'canvas', 'visible'):
            raise AttributeError(key)
        return getattr(self.canvas, key)

    def __repr__(self):
        return f'Layer({self.name!r}, z={self.z})'


class Scene:
    """Compositing container: one Canvas + one HiResCanvas + overlay layers.

        sc = Scene(100, 40)
        sc.hr.set_pixel(40, 50, '*', fg=gold, z=50)     # hires actors
        sc.fill_sky(Gradient(BLUE, DARK))               # bg on main canvas
        sc.layer('hud', z=90).draw_text(1, 1, 'SCORE')  # fixed overlay
        sc.present(sys.stdout)                           # compose + draw
    """

    def __init__(self, width: int, height: int, hires: bool = True):
        self.w = width
        self.h = height
        self.hires_enabled = hires
        self.canvas = Canvas(width, height)
        self.hr = HiResCanvas(width, height * 2) if hires else None
        self._layers: list[Layer] = []

    @property
    def main(self) -> Canvas:
        return self.canvas

    @property
    def surface(self) -> HiResCanvas:
        return self.hr

    def __getattr__(self, key):
        if key.startswith('_'):
            raise AttributeError(key)
        return getattr(self.canvas, key)

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