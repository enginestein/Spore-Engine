from __future__ import annotations
import math
from typing import Optional
from .canvas import Canvas, Cell


class Camera:
    """A 2D viewport onto a larger world.

    World coordinates map to the screen around the camera centre:
    ``screen = (world - centre + view/2) * zoom``.
    """

    def __init__(self, w: int, h: int, x: float = 0.0, y: float = 0.0,
                 zoom: float = 1.0, world_w: Optional[int] = None,
                 world_h: Optional[int] = None):
        self.w = w
        self.h = h
        self.x = x
        self.y = y
        self.zoom = zoom
        self.world_w = world_w
        self.world_h = world_h

    def to_screen(self, wx: float, wy: float) -> tuple[int, int]:
        sx = int(round((wx - self.x) * self.zoom + self.w / 2))
        sy = int(round((wy - self.y) * self.zoom + self.h / 2))
        return sx, sy

    def to_world(self, sx: float, sy: float) -> tuple[float, float]:
        return ((sx - self.w / 2) / self.zoom + self.x,
                (sy - self.h / 2) / self.zoom + self.y)

    @property
    def left(self) -> float:
        return self.x - self.w / (2 * self.zoom)

    @property
    def right(self) -> float:
        return self.x + self.w / (2 * self.zoom)

    @property
    def top(self) -> float:
        return self.y - self.h / (2 * self.zoom)

    @property
    def bottom(self) -> float:
        return self.y + self.h / (2 * self.zoom)

    def in_view(self, wx: float, wy: float, margin: float = 2) -> bool:
        return (self.left - margin <= wx <= self.right + margin
                and self.top - margin <= wy <= self.bottom + margin)

    def follow(self, wx: float, wy: float, dt: Optional[float] = None,
               rate: float = None):
        if dt is not None:
            r = min(1.0, rate if rate is not None else 8.0 * dt)
            self.x += (wx - self.x) * r
            self.y += (wy - self.y) * r
        else:
            self.x, self.y = wx, wy
        self.clamp()

    def clamp(self):
        if self.world_w is not None:
            hw = self.w / (2 * self.zoom)
            self.x = max(hw, min(self.world_w - hw, self.x))
        if self.world_h is not None:
            hh = self.h / (2 * self.zoom)
            self.y = max(hh, min(self.world_h - hh, self.y))

    def draw(self, canvas: Canvas, wx: float, wy: float, char: str = '#',
             fg=None, bg=None, z: float = 0):
        sx, sy = self.to_screen(wx, wy)
        canvas.set_pixel(sx, sy, char, fg, bg, z)

    def draws(self, canvas: Canvas, points, char: str = '#',
              fg=None, bg=None, z: float = 0):
        for wx, wy in points:
            if self.in_view(wx, wy, margin=1):
                sx, sy = self.to_screen(wx, wy)
                canvas.set_pixel(sx, sy, char, fg, bg, z)

    def draw_line(self, canvas: Canvas, x1: float, y1: float, x2: float, y2: float,
                  char: str = '#', fg=None, bg=None, z: float = 0):
        sx1, sy1 = self.to_screen(x1, y1)
        sx2, sy2 = self.to_screen(x2, y2)
        canvas.draw_line(sx1, sy1, sx2, sy2, char, fg, bg, z)

    def draw_text(self, canvas: Canvas, wx: float, wy: float, text: str,
                  fg=None, bg=None, z: float = 0):
        sx, sy = self.to_screen(wx, wy)
        canvas.draw_text(sx, sy, text, fg, bg, z)

    def __repr__(self):
        return f'Camera(centre=({self.x:.0f},{self.y:.0f}) {self.w}x{self.h})'