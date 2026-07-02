from __future__ import annotations
import math
from ..core.color import Color
from ..core.canvas import Canvas


class Sprite:
    def __init__(self, art="", x=0, y=0, fg=None, bg=None, z=0, visible=True):
        self._x = float(x)
        self._y = float(y)
        self._fg = fg
        self._bg = bg
        self._z = z
        self._opacity = 1.0
        self._scale_x = 1.0
        self._scale_y = 1.0
        self._rotation = 0.0
        self._visible = visible
        self._art = ""
        self._cells = []
        self._width = 0
        self._height = 0
        self._anims = []
        self._data = {}
        if art:
            self.set_art(art)

    @property
    def x(self):
        return self._x

    @x.setter
    def x(self, v):
        self._x = float(v)

    @property
    def y(self):
        return self._y

    @y.setter
    def y(self, v):
        self._y = float(v)

    @property
    def z(self):
        return self._z

    @z.setter
    def z(self, v):
        self._z = v

    @property
    def opacity(self):
        return self._opacity

    @opacity.setter
    def opacity(self, v):
        self._opacity = max(0, min(1, v))

    @property
    def scale_x(self):
        return self._scale_x

    @scale_x.setter
    def scale_x(self, v):
        self._scale_x = max(0.01, v)

    @property
    def scale_y(self):
        return self._scale_y

    @scale_y.setter
    def scale_y(self, v):
        self._scale_y = max(0.01, v)

    @property
    def rotation(self):
        return self._rotation

    @rotation.setter
    def rotation(self, v):
        self._rotation = v

    @property
    def visible(self):
        return self._visible

    @visible.setter
    def visible(self, v):
        self._visible = v

    @property
    def width(self):
        return self._width

    @property
    def height(self):
        return self._height

    @property
    def fg(self):
        return self._fg

    @fg.setter
    def fg(self, v):
        self._fg = v

    @property
    def bg(self):
        return self._bg

    @bg.setter
    def bg(self, v):
        self._bg = v

    def set_art(self, art):
        lines = art.split('\n')
        start = 0
        end = len(lines)
        while start < end and lines[start].strip() == '':
            start += 1
        while end > start and lines[end - 1].strip() == '':
            end -= 1
        lines = lines[start:end]
        self._art = '\n'.join(lines)
        self._height = len(lines)
        self._width = max(len(line) for line in lines) if lines else 0
        self._cells = []
        for dy, line in enumerate(lines):
            for dx, ch in enumerate(line):
                if ch != ' ':
                    self._cells.append((ch, dx, dy, None, None))

    @property
    def bounds(self):
        return (self._x, self._y, self._x + self._width, self._y + self._height)

    def contains(self, px, py):
        bx, by, bx2, by2 = self.bounds
        return bx <= px < bx2 and by <= py < by2

    def copy(self):
        s = Sprite("", self._x, self._y, self._fg, self._bg, self._z, self._visible)
        s._cells = list(self._cells)
        s._width = self._width
        s._height = self._height
        s._art = self._art
        s._opacity = self._opacity
        s._scale_x = self._scale_x
        s._scale_y = self._scale_y
        s._rotation = self._rotation
        s._data = dict(self._data)
        return s

    def set_pixel(self, dx, dy, char='#', fg=None, bg=None):
        existing = None
        for i, cell in enumerate(self._cells):
            if cell[1] == dx and cell[2] == dy:
                existing = i
                break
        cell = (char, dx, dy, fg, bg)
        if existing is not None:
            self._cells[existing] = cell
        else:
            self._cells.append(cell)
        self._width = max(self._width, dx + 1)
        self._height = max(self._height, dy + 1)

    def draw_text(self, dx, dy, text, fg=None):
        for i, ch in enumerate(text):
            self.set_pixel(dx + i, dy, ch, fg or self._fg)

    def move_to(self, x, y, duration=None, easing=None):
        from .anim import Anim
        anim = Anim(self).to(x, y)
        if duration is not None:
            anim.over(duration)
        if easing is not None:
            anim.ease(easing)
        self._anims.append(anim)
        return anim

    def move_by(self, dx, dy, duration=None, easing=None):
        return self.move_to(self._x + dx, self._y + dy, duration, easing)

    def fade_to(self, opacity, duration=None, easing=None):
        from .anim import Anim
        anim = Anim(self).fade(opacity)
        if duration is not None:
            anim.over(duration)
        if easing is not None:
            anim.ease(easing)
        self._anims.append(anim)
        return anim

    def fade_in(self, duration=1.0, easing=None):
        self._opacity = 0
        return self.fade_to(1.0, duration, easing)

    def fade_out(self, duration=1.0, easing=None):
        return self.fade_to(0.0, duration, easing)

    def scale_to(self, scale, duration=None, easing=None):
        from .anim import Anim
        anim = Anim(self).scale(scale)
        if duration is not None:
            anim.over(duration)
        if easing is not None:
            anim.ease(easing)
        self._anims.append(anim)
        return anim

    def spin(self, speed=1.0):
        from .anim import Anim
        anim = Anim(self).spin(speed)
        self._anims.append(anim)
        return anim

    def pulse(self, min_scale=0.8, max_scale=1.2, period=1.0):
        from .anim import Anim
        anim = Anim(self).pulse(min_scale, max_scale, period)
        self._anims.append(anim)
        return anim

    def wobble(self, amount=2.0, period=1.0):
        from .anim import Anim
        anim = Anim(self).wobble(amount, period)
        self._anims.append(anim)
        return anim

    def wait(self, seconds):
        from .anim import Anim
        anim = Anim(self).wait(seconds)
        self._anims.append(anim)
        return anim

    def then(self, callback):
        from .anim import Anim
        self._anims[-1].then(callback)
        return self

    def clear_anims(self):
        self._anims = []

    def update(self, dt):
        self._anims = [a for a in self._anims if not a.done]
        for anim in self._anims:
            anim.update(dt)

    def render(self, canvas):
        if not self._visible or self._opacity <= 0:
            return
        ox = self._x
        oy = self._y
        for cell in self._cells:
            char, dx, dy = cell[0], cell[1], cell[2]
            px = int(ox + dx * self._scale_x)
            py = int(oy + dy * self._scale_y)
            if self._rotation != 0:
                cx = self._width * self._scale_x / 2
                cy = self._height * self._scale_y / 2
                rx = px - (ox + cx)
                ry = py - (oy + cy)
                cos_a = math.cos(self._rotation)
                sin_a = math.sin(self._rotation)
                px = int(ox + cx + rx * cos_a - ry * sin_a)
                py = int(oy + cy + rx * sin_a + ry * cos_a)
            fg = self._fg
            bg = self._bg
            if self._opacity < 1 and fg:
                fg = Color(int(fg.r * self._opacity), int(fg.g * self._opacity), int(fg.b * self._opacity))
            canvas.set_pixel(px, py, char, fg, bg, self._z)

    def __repr__(self):
        return f"Sprite({self._width}x{self._height} @ ({self._x:.0f},{self._y:.0f}))"

    @staticmethod
    def rect(w, h, char='#', fg=None, bg=None):
        art = '\n'.join([char * w for _ in range(h)])
        return Sprite(art, fg=fg, bg=bg)

    @staticmethod
    def circle(r, char='#', fg=None):
        art_lines = []
        for dy in range(-r, r + 1):
            line = ''
            for dx in range(-r, r + 1):
                if dx * dx + dy * dy <= r * r:
                    line += char
                else:
                    line += ' '
            art_lines.append(line)
        return Sprite('\n'.join(art_lines), fg=fg)

    @staticmethod
    def from_file(path):
        with open(path) as f:
            return Sprite(f.read())
