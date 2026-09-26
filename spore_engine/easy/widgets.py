from ..core.color import Color, WHITE
from .sprite import GameSprite


class SimpleButton:
    def __init__(self, text, x=0, y=0, width=None, fg=None, bg=None, on_click=None):
        self.text = text
        self.x = x
        self.y = y
        self.width = width or len(text) + 4
        self.fg = fg or WHITE
        self.bg = bg or Color(60, 60, 80)
        self._on_click = on_click
        self.hover = False
        self.pressed = False
        self._hover_fg = Color(255, 255, 255)
        self._hover_bg = Color(80, 80, 120)
        self._build_sprite()

    def _build_sprite(self):
        pad = 2
        inner_w = self.width - pad * 2
        text_padded = self.text[:inner_w].center(inner_w)
        lines = []
        border = '─' * self.width
        lines.append(f"┌{border}┐")
        lines.append(f"│{' ' * pad}{text_padded}{' ' * pad}│")
        lines.append(f"└{border}┘")
        self._sprite = GameSprite('\n'.join(lines), self.x, self.y, self.fg, self.bg, z=10)

    @property
    def bounds(self):
        return (self.x, self.y, self.x + self._sprite.width, self.y + self._sprite.height)

    def contains(self, px, py):
        bx, by, bx2, by2 = self.bounds
        return bx <= px < bx2 and by <= py < by2

    def click(self):
        if self._on_click:
            self._on_click()

    def render(self, canvas):
        if self.hover or self.pressed:
            self._sprite.fg = self._hover_fg
            self._sprite.bg = self._hover_bg
        else:
            self._sprite.fg = self.fg
            self._sprite.bg = self.bg
        self._sprite.render(canvas)

    def on_click(self, handler):
        self._on_click = handler
        return self


class SimpleLabel:
    def __init__(self, text, x=0, y=0, fg=None, z=0):
        self.text = text
        self.x = x
        self.y = y
        self.fg = fg or WHITE
        self.z = z

    def render(self, canvas):
        canvas.draw_text(self.x, self.y, self.text, self.fg, z=self.z)


class SimpleDialog:
    def __init__(self, title, message, x=None, y=None, width=None, height=None):
        self.title = title
        self.message = message
        self._buttons = []
        self.result = None
        self._x = x
        self._y = y
        self._width = width or 40
        self._height = height or 8

    def add_button(self, label, result):
        self._buttons.append((label, result))
        return self

    def render(self, canvas):
        w, h = self._width, self._height
        cx = self._x if self._x is not None else canvas.w // 2 - w // 2
        cy = self._y if self._y is not None else canvas.h // 2 - h // 2
        for iy in range(h):
            for ix in range(w):
                px, py = cx + ix, cy + iy
                if 0 <= px < canvas.w and 0 <= py < canvas.h:
                    ch = ' ' if 0 < ix < w - 1 and 0 < iy < h - 1 else '#'
                    canvas.set_pixel(px, py, ch, Color(200, 200, 220), Color(40, 40, 60), z=100)
        canvas.draw_text(cx + 2, cy + 1, f" {self.title} ", WHITE, z=101)
        msg_lines = self.message.split('\n') if isinstance(self.message, str) else [self.message]
        for i, line in enumerate(msg_lines):
            canvas.draw_text(cx + 2, cy + 3 + i, str(line), Color(180, 180, 200), z=101)
        for i, (label, _result) in enumerate(self._buttons):
            bx = cx + 2 + i * (len(str(label)) + 4)
            by = cy + h - 2
            canvas.draw_text(bx, by, f"[ {label} ]", WHITE, z=101)
