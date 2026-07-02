from __future__ import annotations
import math, time
from typing import Optional, Callable, List
from ..core.color import Color, WHITE, BLACK, DIM
from ..core.canvas import Canvas, SHADE_CHARS

SHADE = SHADE_CHARS


class Widget:
    def __init__(self, x: int, y: int, width: int, height: int):
        self.x = x
        self.y = y
        self.width = max(1, width)
        self.height = max(1, height)
        self.focused = False
        self.hovered = False
        self.visible = True
        self.mouse_down_self = False

    def contains(self, mx: int, my: int) -> bool:
        return self.x <= mx < self.x + self.width and self.y <= my < self.y + self.height

    def handle_event(self, event_type: str, data: any):
        pass

    def render(self, canvas: Canvas, z: float = 0):
        pass


class Label(Widget):
    def __init__(self, x: int, y: int, text: str = '',
                 fg: Color = WHITE, bg: Optional[Color] = None):
        super().__init__(x, y, max(1, len(text)), 1)
        self.text = text
        self.fg = fg
        self.bg = bg

    def render(self, canvas: Canvas, z: float = 0):
        if not self.visible: return
        for i, ch in enumerate(self.text):
            px = self.x + i
            if 0 <= px < canvas.w and 0 <= self.y < canvas.h:
                canvas.set_pixel(px, self.y, ch, self.fg, self.bg, z=z)


class TextBox(Widget):
    def __init__(self, x: int, y: int, width: int, height: int,
                 fg: Color = WHITE, bg: Optional[Color] = None):
        super().__init__(x, y, width, height)
        self.fg = fg
        self.bg = bg
        self.lines: list[str] = []

    def set_text(self, text: str):
        words = text.split()
        lines = []
        current = ''
        for w in words:
            if len(current) + len(w) + 1 <= self.width:
                current += (' ' if current else '') + w
            else:
                if current:
                    lines.append(current)
                current = w
        if current:
            lines.append(current)
        self.lines = lines[:self.height]

    def render(self, canvas: Canvas, z: float = 0):
        if not self.visible: return
        for i, line in enumerate(self.lines):
            py = self.y + i
            if py >= canvas.h: break
            for j, ch in enumerate(line):
                px = self.x + j
                if px >= canvas.w: break
                canvas.set_pixel(px, py, ch, self.fg, self.bg, z=z)


class ProgressBar(Widget):
    def __init__(self, x: int, y: int, width: int,
                 fg: Color = Color(0, 200, 80),
                 bg: Color = Color(30, 30, 30),
                 label: str = ''):
        super().__init__(x, y, width, 1)
        self.fg = fg
        self.bg = bg
        self.label = label
        self.progress = 0.0

    def set_progress(self, value: float):
        self.progress = max(0, min(1, value))

    def render(self, canvas: Canvas, z: float = 0):
        if not self.visible: return
        filled = int(self.progress * self.width)
        for i in range(self.width):
            px = self.x + i
            if px >= canvas.w or self.y >= canvas.h: break
            if i < filled:
                canvas.set_pixel(px, self.y, '█', self.fg, z=z)
            else:
                canvas.set_pixel(px, self.y, '░', self.fg, self.bg, z=z)
        if self.label:
            for i, ch in enumerate(self.label):
                px = self.x + self.width + 2 + i
                if px < canvas.w:
                    canvas.set_pixel(px, self.y, ch, self.fg.mul(0.6), z=z)


class Button(Widget):
    def __init__(self, x: int, y: int, width: int, text: str = '',
                 fg: Color = WHITE, bg: Color = Color(60, 60, 80),
                 hover_bg: Color = Color(80, 80, 120),
                 press_bg: Color = Color(120, 120, 180),
                 callback: Optional[Callable] = None,
                 key: Optional[str] = None):
        super().__init__(x, y, width, 1)
        self.text = text
        self.fg = fg
        self.bg = bg
        self.hover_bg = hover_bg
        self.press_bg = press_bg
        self.callback = callback
        self.pressed = False
        self.key = key

    def handle_event(self, event_type: str, data: any):
        if event_type == 'mouse_move':
            mx, my = data
            self.hovered = self.contains(mx, my)
        elif event_type == 'mouse_down':
            mx, my = data
            if self.contains(mx, my):
                self.pressed = True
                self.mouse_down_self = True
        elif event_type == 'mouse_up':
            if self.pressed and self.mouse_down_self and self.hovered:
                if self.callback: self.callback()
            self.pressed = False
            self.mouse_down_self = False
        elif event_type == 'key_down':
            if self.focused and data in ('enter', '\r', ' '):
                if self.callback: self.callback()

    def render(self, canvas: Canvas, z: float = 0):
        if not self.visible: return
        bg = self.press_bg if self.pressed else (self.hover_bg if self.hovered else self.bg)
        if self.focused:
            bg = Color(min(bg.r + 30, 255), min(bg.g + 30, 255), min(bg.b + 30, 255))

        char_left = '[' if not self.pressed else '<'
        char_right = ']' if not self.pressed else '>'

        pad = max(0, (self.width - len(self.text) - 2) // 2)
        full_text = char_left + " " * pad + self.text + " " * (self.width - len(self.text) - 2 - pad) + char_right

        for i, ch in enumerate(full_text):
            px = self.x + i
            if px >= canvas.w or self.y >= canvas.h: break
            canvas.set_pixel(px, self.y, ch, self.fg, bg, z=z)


class Menu(Widget):
    def __init__(self, x: int, y: int, items: List[str] = None,
                 fg: Color = WHITE, bg: Color = Color(40, 40, 60),
                 selected_bg: Color = Color(80, 80, 140),
                 callback: Optional[Callable[[int, str], None]] = None):
        h = len(items) if items else 0
        w = max([len(i) for i in items]) + 4 if items else 10
        super().__init__(x, y, w, h)
        self.items = items or []
        self.fg = fg
        self.bg = bg
        self.selected_bg = selected_bg
        self.selected = 0
        self.callback = callback

    def handle_event(self, event_type: str, data: any):
        if event_type == 'key_down':
            if data == 'up':
                self.selected = (self.selected - 1) % len(self.items)
            elif data == 'down':
                self.selected = (self.selected + 1) % len(self.items)
            elif data == 'enter' or data == '\r' or data == ' ':
                if self.callback: self.callback(self.selected, self.items[self.selected])
        elif event_type == 'mouse_move':
            mx, my = data
            if self.contains(mx, my):
                self.selected = my - self.y
        elif event_type == 'mouse_up':
            mx, my = data
            if self.contains(mx, my):
                if self.callback: self.callback(self.selected, self.items[self.selected])

    def render(self, canvas: Canvas, z: float = 0):
        if not self.visible: return
        for i, item in enumerate(self.items):
            py = self.y + i
            if py >= canvas.h: break
            is_sel = i == self.selected
            bg = self.selected_bg if is_sel else self.bg
            if self.focused and is_sel:
                bg = Color(min(bg.r + 40, 255), min(bg.g + 40, 255), min(bg.b + 40, 255))

            for j in range(self.width):
                px = self.x + j
                if px < canvas.w:
                    canvas.set_pixel(px, py, ' ', self.fg, bg, z=z)

            for j, ch in enumerate(item):
                px = self.x + 2 + j
                if px >= canvas.w: break
                fg = self.fg if not is_sel else Color(255, 255, 255)
                canvas.set_pixel(px, py, ch, fg, bg, z=z)

            if is_sel:
                marker = '▶' if not self.focused else '▸'
                canvas.set_pixel(self.x, py, marker, Color(255, 255, 0), bg, z=z)


class Frame(Widget):
    def __init__(self, x: int, y: int, width: int, height: int,
                 title: str = '', fg: Color = DIM):
        super().__init__(x, y, width, height)
        self.title = title
        self.fg = fg

    def render(self, canvas: Canvas, z: float = 0):
        if not self.visible: return
        x, y, w, h = self.x, self.y, self.width, self.height
        if x >= canvas.w or y >= canvas.h: return
        active_fg = Color(180, 180, 255) if self.focused else self.fg
        chars = {'tl': '┏', 'tr': '┓', 'bl': '┗', 'br': '┛',
                 'h': '━', 'v': '┃'}

        canvas.set_pixel(x, y, chars['tl'], active_fg, z=z)
        canvas.set_pixel(x + w - 1, y, chars['tr'], active_fg, z=z)
        canvas.set_pixel(x, y + h - 1, chars['bl'], active_fg, z=z)
        canvas.set_pixel(x + w - 1, y + h - 1, chars['br'], active_fg, z=z)

        for i in range(1, w - 1):
            px = x + i
            if px < canvas.w:
                canvas.set_pixel(px, y, chars['h'], active_fg, z=z)
                canvas.set_pixel(px, y + h - 1, chars['h'], active_fg, z=z)
        for i in range(1, h - 1):
            py = y + i
            if py < canvas.h:
                canvas.set_pixel(x, py, chars['v'], active_fg, z=z)
                canvas.set_pixel(x + w - 1, py, chars['v'], active_fg, z=z)

        if self.title:
            t = f" {self.title} "
            for i, ch in enumerate(t):
                px = x + 2 + i
                if px < canvas.w:
                    canvas.set_pixel(px, y, ch, WHITE, z=z+1)


class Checkbox(Widget):
    def __init__(self, x: int, y: int, label: str = '', checked: bool = False,
                 fg: Color = WHITE, bg: Color = Color(30, 30, 40),
                 accent: Color = Color(100, 200, 255),
                 callback: Optional[Callable[[bool], None]] = None):
        text_w = len(label) + 4
        super().__init__(x, y, text_w, 1)
        self.label = label
        self.checked = checked
        self.fg = fg
        self.bg = bg
        self.accent = accent
        self.callback = callback

    def handle_event(self, event_type: str, data: any):
        if event_type == 'key_down' and self.focused:
            if data in ('enter', '\r', ' '):
                self.checked = not self.checked
                if self.callback: self.callback(self.checked)

    def render(self, canvas: Canvas, z: float = 0):
        if not self.visible: return
        bracket_fg = self.accent if self.focused else DIM
        check = 'x' if self.checked else ' '
        line = f'[{check}] {self.label}'
        for i, ch in enumerate(line):
            px = self.x + i
            if px >= canvas.w or self.y >= canvas.h: break
            if i == 0 or i == 2:
                canvas.set_pixel(px, self.y, ch, bracket_fg, self.bg, z=z)
            elif i == 1:
                fg = self.accent if self.checked else DIM
                canvas.set_pixel(px, self.y, 'x' if self.checked else ' ', fg, self.bg, z=z)
            else:
                canvas.set_pixel(px, self.y, ch, self.fg, self.bg, z=z)


class RadioGroup(Widget):
    def __init__(self, x: int, y: int, options: List[str] = None,
                 selected: int = 0,
                 fg: Color = WHITE, bg: Color = Color(30, 30, 40),
                 accent: Color = Color(255, 200, 80),
                 callback: Optional[Callable[[int, str], None]] = None):
        w = max(len(o) for o in (options or [''])) + 4
        h = len(options) if options else 0
        super().__init__(x, y, w, h)
        self.options = options or []
        self.selected = selected
        self.fg = fg
        self.bg = bg
        self.accent = accent
        self.callback = callback

    def handle_event(self, event_type: str, data: any):
        if event_type == 'key_down' and self.focused:
            if data == 'up':
                self.selected = (self.selected - 1) % len(self.options)
                if self.callback: self.callback(self.selected, self.options[self.selected])
            elif data == 'down':
                self.selected = (self.selected + 1) % len(self.options)
                if self.callback: self.callback(self.selected, self.options[self.selected])

    def render(self, canvas: Canvas, z: float = 0):
        if not self.visible: return
        for i, opt in enumerate(self.options):
            py = self.y + i
            if py >= canvas.h: break
            is_sel = i == self.selected
            sel_fg = self.accent if is_sel else DIM
            tag = '(*)' if is_sel else '( )'
            for j, ch in enumerate(f'{tag} {opt}'):
                px = self.x + j
                if px >= canvas.w: break
                if j == 1:
                    canvas.set_pixel(px, py, '*' if is_sel else ' ', sel_fg, self.bg, z=z)
                elif j in (0, 2):
                    canvas.set_pixel(px, py, ch, sel_fg, self.bg, z=z)
                else:
                    canvas.set_pixel(px, py, ch, self.fg, self.bg, z=z)


class TabBar(Widget):
    def __init__(self, x: int, y: int, tabs: List[str] = None,
                 fg: Color = WHITE, bg: Color = Color(40, 40, 55),
                 active_bg: Color = Color(80, 80, 140),
                 callback: Optional[Callable[[int, str], None]] = None):
        w = sum(len(t) + 4 for t in (tabs or []))
        super().__init__(x, y, w, 1)
        self.tabs = tabs or []
        self.fg = fg
        self.bg = bg
        self.active_bg = active_bg
        self.selected = 0
        self.callback = callback

    def handle_event(self, event_type: str, data: any):
        if event_type == 'key_down' and self.focused:
            if data == 'left':
                self.selected = (self.selected - 1) % len(self.tabs)
                if self.callback: self.callback(self.selected, self.tabs[self.selected])
            elif data == 'right':
                self.selected = (self.selected + 1) % len(self.tabs)
                if self.callback: self.callback(self.selected, self.tabs[self.selected])

    def render(self, canvas: Canvas, z: float = 0):
        if not self.visible: return
        ox = self.x
        for i, tab in enumerate(self.tabs):
            is_sel = i == self.selected
            bg = self.active_bg if is_sel else self.bg
            if self.focused and is_sel:
                bg = Color(min(bg.r + 40, 255), min(bg.g + 40, 255), min(bg.b + 40, 255))
            sep = '│'
            label = f' {tab} '
            for j, ch in enumerate(f' {label} '):
                px = ox + j
                if px >= canvas.w: break
                if ch == '│':
                    canvas.set_pixel(px, self.y, ch, DIM, z=z)
                else:
                    fg = WHITE if is_sel else DIM
                    canvas.set_pixel(px, self.y, ch, fg, bg, z=z)
            ox += len(label) + 2


class Slider(Widget):
    def __init__(self, x: int, y: int, width: int = 20,
                 label: str = '', value: float = 0.5,
                 fg: Color = Color(100, 200, 255),
                 bg: Color = Color(30, 30, 40),
                 callback: Optional[Callable[[float], None]] = None):
        super().__init__(x, y, width, 1)
        self.label = label
        self.value = value
        self.fg = fg
        self.bg = bg
        self.callback = callback

    def set_value(self, v: float):
        self.value = max(0.0, min(1.0, v))

    def handle_event(self, event_type: str, data: any):
        if event_type == 'key_down' and self.focused:
            if data == 'left':
                self.set_value(self.value - 0.05)
                if self.callback: self.callback(self.value)
            elif data == 'right':
                self.set_value(self.value + 0.05)
                if self.callback: self.callback(self.value)

    def render(self, canvas: Canvas, z: float = 0):
        if not self.visible: return
        if self.label:
            for i, ch in enumerate(self.label):
                px = self.x + i
                if px < canvas.w:
                    canvas.set_pixel(px, self.y, ch, self.fg.mul(0.8), z=z)
            lx = self.x + len(self.label) + 1
        else:
            lx = self.x

        bw = self.width - len(self.label) - 1 if self.label else self.width
        pos = int(self.value * (bw - 2))
        track = ['─'] * bw
        track[0] = '├'
        track[-1] = '┤'
        if self.focused:
            if 0 < pos + 1 < len(track):
                track[pos + 1] = '●'
        else:
            if 0 < pos + 1 < len(track):
                track[pos + 1] = '◆'
        for i, ch in enumerate(track):
            px = lx + i
            if px < canvas.w:
                fg = self.fg if self.focused else DIM
                canvas.set_pixel(px, self.y, ch, fg, self.bg, z=z)

        pct = f'{int(self.value * 100)}%'
        for i, ch in enumerate(pct):
            px = lx + bw + 1 + i
            if px < canvas.w:
                canvas.set_pixel(px, self.y, ch, self.fg.mul(0.7), z=z)


class Table(Widget):
    def __init__(self, x: int, y: int,
                 headers: List[str] = None,
                 col_widths: List[int] = None,
                 fg: Color = WHITE, bg: Color = Color(15, 15, 25),
                 header_bg: Color = Color(40, 40, 65),
                 select_bg: Color = Color(60, 60, 110),
                 callback: Optional[Callable[[int, List[str]], None]] = None):
        cw = col_widths or [10] * len(headers or [])
        w = sum(cw) + len(cw) + 1
        h = (len(headers) + 2) if headers else 3
        super().__init__(x, y, w, h)
        self.headers = headers or []
        self.col_widths = cw
        self.fg = fg
        self.bg = bg
        self.header_bg = header_bg
        self.select_bg = select_bg
        self.rows: List[List[str]] = []
        self.selected = 0
        self.callback = callback

    def set_rows(self, rows: List[List[str]]):
        self.rows = rows
        self.height = len(rows) + 2
        self.selected = 0

    def handle_event(self, event_type: str, data: any):
        if event_type == 'key_down' and self.focused:
            if data == 'up':
                self.selected = max(0, self.selected - 1)
            elif data == 'down':
                self.selected = min(len(self.rows) - 1, self.selected + 1)
            elif data in ('enter', '\r'):
                if self.callback and self.rows:
                    self.callback(self.selected, self.rows[self.selected])

    def _render_row(self, canvas, py, cells, is_header, is_select, z):
        x = self.x
        for ci, cell in enumerate(cells):
            cw = self.col_widths[ci] if ci < len(self.col_widths) else 10
            text = str(cell)[:cw].ljust(cw)
            bg = self.header_bg if is_header else (self.select_bg if is_select else self.bg)
            if self.focused and is_select:
                bg = Color(min(bg.r + 40, 255), min(bg.g + 40, 255), min(bg.b + 40, 255))

            canvas.set_pixel(x, py, '│', DIM, z=z)
            for j, ch in enumerate(text):
                px = x + 1 + j
                if px < canvas.w:
                    fg = WHITE if is_header else self.fg
                    canvas.set_pixel(px, py, ch, fg, bg, z=z)
            x += cw + 1
        if x < canvas.w:
            canvas.set_pixel(x, py, '│', DIM, z=z)

    def render(self, canvas: Canvas, z: float = 0):
        if not self.visible or not self.headers: return
        py = self.y
        self._render_row(canvas, py, self.headers, is_header=True, is_select=False, z=z)
        py += 1

        sep = '├' + '┼'.join(['─' * cw for cw in self.col_widths]) + '┤'
        for i, ch in enumerate(sep):
            px = self.x + i
            if px < canvas.w:
                canvas.set_pixel(px, py, ch, DIM, z=z)
        py += 1

        for ri, row in enumerate(self.rows):
            if py >= canvas.h: break
            self._render_row(canvas, py, row, is_header=False, is_select=(ri == self.selected), z=z)
            py += 1


class Input(Widget):
    def __init__(self, x: int, y: int, width: int = 20,
                 label: str = '', placeholder: str = '',
                 fg: Color = WHITE, bg: Color = Color(20, 20, 35),
                 accent: Color = Color(100, 200, 255),
                 callback: Optional[Callable[[str], None]] = None):
        super().__init__(x, y, width, 1)
        self.label = label
        self.placeholder = placeholder
        self.text = ''
        self.cursor = 0
        self.fg = fg
        self.bg = bg
        self.accent = accent
        self.callback = callback

    def handle_event(self, event_type: str, data: any):
        if not self.focused: return
        if event_type == 'key_down':
            if data == '\t':
                return
            if data in ('enter', '\r'):
                if self.callback: self.callback(self.text)
            elif data == 'backspace':
                if self.cursor > 0:
                    self.text = self.text[:self.cursor - 1] + self.text[self.cursor:]
                    self.cursor -= 1
            elif data == 'delete':
                self.text = self.text[:self.cursor] + self.text[self.cursor + 1:]
            elif data == 'home':
                self.cursor = 0
            elif data == 'end':
                self.cursor = len(self.text)
            elif data == 'left':
                self.cursor = max(0, self.cursor - 1)
            elif data == 'right':
                self.cursor = min(len(self.text), self.cursor + 1)
            else:
                if len(data) == 1 and len(self.text) < self.width - 1:
                    self.text = self.text[:self.cursor] + data + self.text[self.cursor:]
                    self.cursor += 1

    def render(self, canvas: Canvas, z: float = 0):
        if not self.visible: return
        lx = self.x
        if self.label:
            for i, ch in enumerate(self.label):
                px = self.x + i
                if px < canvas.w:
                    canvas.set_pixel(px, self.y, ch, self.fg.mul(0.8), z=z)
            lx = self.x + len(self.label) + 1

        if self.text:
            display = self.text[:self.width]
        else:
            display = self.placeholder[:self.width] if self.placeholder else ''
        display = display.ljust(self.width)

        cursor_visible = self.focused and (int(time.time() * 3) % 2 == 0)

        for i, ch in enumerate(display):
            px = lx + i
            if px >= canvas.w: break
            is_cursor = self.focused and i == self.cursor and self.text
            if is_cursor and cursor_visible:
                fg = self.accent
                ch = '▉'
            elif not self.text and not is_cursor:
                fg = DIM
            else:
                fg = self.fg
            bg = self.bg
            if self.focused:
                bg = Color(min(bg.r + 10, 255), min(bg.g + 10, 255), min(bg.b + 15, 255))
            canvas.set_pixel(px, self.y, ch, fg, bg, z=z)


class Toggle(Widget):
    def __init__(self, x: int, y: int, label: str = '', active: bool = True,
                 fg: Color = WHITE, bg: Color = Color(30, 30, 40),
                 on_fg: Color = Color(80, 200, 80),
                 off_fg: Color = Color(200, 80, 80),
                 callback: Optional[Callable[[bool], None]] = None):
        text_w = len(label) + 8 if label else 6
        super().__init__(x, y, text_w, 1)
        self.label = label
        self.active = active
        self.fg = fg
        self.bg = bg
        self.on_fg = on_fg
        self.off_fg = off_fg
        self.callback = callback

    def handle_event(self, event_type: str, data: any):
        if event_type == 'key_down' and self.focused:
            if data in ('enter', '\r', ' '):
                self.active = not self.active
                if self.callback: self.callback(self.active)
            elif data in ('left', 'right'):
                self.active = not self.active
                if self.callback: self.callback(self.active)

    def render(self, canvas: Canvas, z: float = 0):
        if not self.visible: return
        ox = self.x
        if self.label:
            for i, ch in enumerate(self.label + ' '):
                px = ox + i
                if px < canvas.w:
                    canvas.set_pixel(px, self.y, ch, self.fg.mul(0.8), z=z)
            ox += len(self.label) + 1

        on_fg = self.on_fg if self.active else DIM
        off_fg = self.off_fg if not self.active else DIM
        focus_glow = self.focused

        on_bg = Color(30, 60, 30) if focus_glow else Color(20, 35, 20)
        off_bg = Color(60, 30, 30) if focus_glow else Color(35, 20, 20)

        toggle = f'<{"ON" if self.active else "OFF"}>'
        for i, ch in enumerate(toggle):
            px = ox + i
            if px >= canvas.w: break
            bg = on_bg if self.active else off_bg
            fg = on_fg if self.active else off_fg
            if focus_glow:
                bg = Color(min(bg.r + 15, 255), min(bg.g + 15, 255), min(bg.b + 15, 255))
            canvas.set_pixel(px, self.y, ch, fg, bg, z=z)


class Divider(Widget):
    def __init__(self, x: int, y: int, width: int, vertical: bool = False,
                 fg: Color = DIM, char: str = '─'):
        if vertical:
            super().__init__(x, y, 1, width)
        else:
            super().__init__(x, y, width, 1)
        self.vertical = vertical
        self.fg = fg
        self.char = char

    def render(self, canvas: Canvas, z: float = 0):
        if not self.visible: return
        if self.vertical:
            for i in range(self.height):
                py = self.y + i
                if py < canvas.h:
                    canvas.set_pixel(self.x, py, '│', self.fg, z=z)
        else:
            for i in range(self.width):
                px = self.x + i
                if px < canvas.w:
                    canvas.set_pixel(px, self.y, self.char, self.fg, z=z)


class StatusBar(Widget):
    def __init__(self, x: int, y: int, width: int,
                 fg: Color = Color(200, 200, 220),
                 bg: Color = Color(20, 20, 40)):
        super().__init__(x, y, width, 1)
        self.fg = fg
        self.bg = bg
        self.left_text = ''
        self.right_text = ''

    def set_left(self, text: str):
        self.left_text = text

    def set_right(self, text: str):
        self.right_text = text

    def render(self, canvas: Canvas, z: float = 0):
        if not self.visible: return
        for i in range(self.width):
            px = self.x + i
            if px < canvas.w:
                canvas.set_pixel(px, self.y, ' ', self.fg, self.bg, z=z)

        for i, ch in enumerate(self.left_text):
            px = self.x + i
            if px < canvas.w:
                canvas.set_pixel(px, self.y, ch, self.fg, self.bg, z=z)

        right_x = self.x + self.width - len(self.right_text)
        for i, ch in enumerate(self.right_text):
            px = right_x + i
            if px < canvas.w:
                canvas.set_pixel(px, self.y, ch, self.fg.mul(0.7), self.bg, z=z)


class WidgetManager:
    def __init__(self):
        self.widgets: List[Widget] = []
        self.focusable: List[Widget] = []
        self.focused_idx = 0
        self.mouse_pos = (0, 0)
        self._mouse_down_widget: Optional[Widget] = None

    def add(self, widget: Widget, focusable: bool = False):
        self.widgets.append(widget)
        if focusable:
            self.focusable.append(widget)
        return widget

    def remove(self, widget: Widget):
        if widget in self.widgets:
            self.widgets.remove(widget)
        if widget in self.focusable:
            self.focusable.remove(widget)
            if self.focused_idx >= len(self.focusable):
                self.focused_idx = max(0, len(self.focusable) - 1)

    def clear(self):
        self.widgets.clear()
        self.focusable.clear()
        self.focused_idx = 0
        self._mouse_down_widget = None

    def focus_next(self):
        if not self.focusable: return
        self.focused_idx = (self.focused_idx + 1) % len(self.focusable)
        for i, w in enumerate(self.focusable):
            w.focused = (i == self.focused_idx)

    def focus_prev(self):
        if not self.focusable: return
        self.focused_idx = (self.focused_idx - 1) % len(self.focusable)
        for i, w in enumerate(self.focusable):
            w.focused = (i == self.focused_idx)

    def focus_first(self):
        if not self.focusable: return
        self.focused_idx = 0
        for i, w in enumerate(self.focusable):
            w.focused = (i == 0)

    def get_focused(self) -> Optional[Widget]:
        if self.focusable and self.focused_idx < len(self.focusable):
            return self.focusable[self.focused_idx]
        return None

    def handle_event(self, event_type: str, data: any):
        if event_type == 'mouse_move':
            self.mouse_pos = data
            for w in self.widgets:
                w.hovered = w.contains(data[0], data[1])
        elif event_type == 'mouse_down':
            mx, my = data
            self._mouse_down_widget = None
            for w in reversed(self.widgets):
                if not w.visible: continue
                if w.contains(mx, my):
                    self._mouse_down_widget = w
                    w.handle_event(event_type, data)
                    if isinstance(w, (Button, Checkbox, Toggle, Slider, Input)):
                        if w in self.focusable:
                            self.focused_idx = self.focusable.index(w)
                            for i, fw in enumerate(self.focusable):
                                fw.focused = (i == self.focused_idx)
                    break
        elif event_type == 'mouse_up':
            if self._mouse_down_widget:
                self._mouse_down_widget.handle_event(event_type, data)
            self._mouse_down_widget = None
        elif event_type == 'key_down':
            focused = self.get_focused()
            if focused:
                focused.handle_event(event_type, data)

    def render(self, canvas: Canvas, z: float = 0):
        for w in self.widgets:
            if w.visible:
                w.render(canvas, z)
