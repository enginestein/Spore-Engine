from __future__ import annotations
import sys, tty, termios, select, os, signal, time, math
from typing import Optional, Callable
from ..core.color import Color, WHITE, DIM, BLACK
from ..core.canvas import Canvas
from .widgets import Widget, WidgetManager, Frame, Label, Button, Input, Checkbox


# ═══════════════════════════════════════════════════════════════════
# TERMINAL EVENT LOOP
# ═══════════════════════════════════════════════════════════════════

_defs = None


def _save_term():
    global _defs
    _defs = termios.tcgetattr(sys.stdin.fileno())


def _restore_term():
    global _defs
    if _defs:
        termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, _defs)


def _set_raw():
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    new = termios.tcgetattr(fd)
    new[tty.LFLAG] &= ~(termios.ECHO | termios.ICANON | termios.ISIG)
    new[tty.CC][termios.VMIN] = 0
    new[tty.CC][termios.VTIME] = 1
    termios.tcsetattr(fd, termios.TCSADRAIN, new)
    return old


def _enable_mouse():
    sys.stdout.write('\033[?1000h\033[?1002h\033[?1006h')
    sys.stdout.flush()


def _disable_mouse():
    sys.stdout.write('\033[?1000l\033[?1002l\033[?1006l')
    sys.stdout.flush()


_KEYS = {
    '\x1b[A': 'up', '\x1b[B': 'down', '\x1b[C': 'right', '\x1b[D': 'left',
    '\x1b[Z': 'tab_back',
    '\x1b[H': 'home', '\x1b[F': 'end',
    '\x1b[2~': 'insert', '\x1b[3~': 'delete', '\x1b[5~': 'page_up',
    '\x1b[6~': 'page_down',
    '\x7f': 'backspace', '\x1b': 'escape',
    '\t': '\t', '\r': 'enter',
}


def _parse_mouse(buf: str) -> Optional[tuple[str, int, int]]:
    try:
        if '\x1b[' not in buf:
            return None
        idx = buf.index('\x1b[')
        rest = buf[idx + 2:]
        if not rest:
            return None
        if rest[-1] not in ('M', 'm'):
            return None
        data = rest[:-1]
        if data.startswith('<'):
            data = data[1:]
        parts = data.split(';')
        if len(parts) == 3:
            cb = int(parts[0])
            mx = int(parts[1]) - 1
            my = int(parts[2]) - 1
            if cb & 64:
                return ('mouse_up', mx, my)
            elif cb & 32:
                return ('mouse_move', mx, my)
            else:
                return ('mouse_down', mx, my)
    except (ValueError, IndexError):
        pass
    return None


def _read_key(timeout: float = 0.01) -> Optional[str]:
    if not select.select([sys.stdin], [], [], timeout)[0]:
        return None
    ch = os.read(sys.stdin.fileno(), 1).decode('utf-8', errors='replace')
    if ch != '\x1b':
        if ch == '\x7f':
            return 'backspace'
        if ch == '\r':
            return 'enter'
        return ch
    seq = ch
    while select.select([sys.stdin], [], [], 0.03)[0]:
        b = os.read(sys.stdin.fileno(), 1).decode('utf-8', errors='replace')
        if not b:
            break
        seq += b
        if b.isalpha() and b not in '0123456789;':
            break
        if b == '~':
            break
        if b == 'M' or b == 'm':
            break
    if seq in _KEYS:
        return _KEYS[seq]
    return 'escape'


def _read_mouse_events(timeout: float = 0.001) -> list[tuple[str, int, int]]:
    events = []
    if not select.select([sys.stdin], [], [], timeout)[0]:
        return events
    data = os.read(sys.stdin.fileno(), 128).decode('utf-8', errors='replace')
    heads = data.split('\x1b[')
    for h in heads:
        if not h:
            continue
        for ch in ('M', 'm'):
            if ch in h:
                idx = h.index(ch)
                part = h[:idx]
                if part.startswith('<'):
                    part = part[1:]
                if part.count(';') == 2:
                    try:
                        parts = part.split(';')
                        cb, mx, my = int(parts[0]), int(parts[1]) - 1, int(parts[2]) - 1
                        if cb & 64:
                            events.append(('mouse_up', mx, my))
                        elif cb & 32:
                            events.append(('mouse_move', mx, my))
                        else:
                            events.append(('mouse_down', mx, my))
                    except (ValueError, IndexError):
                        pass
    return events


class TerminalApp:
    def __init__(self, canvas_w: int = 80, canvas_h: int = 24):
        self.width = canvas_w
        self.height = canvas_h
        self.canvas = Canvas(canvas_w, canvas_h)
        self.manager = WidgetManager()
        self.running = False
        self._on_tick: Optional[Callable] = None
        self._draw_callback: Optional[Callable] = None
        self._tick_rate = 0.033
        self._raw_mode = False
        self._old_term = None
        self._prev_buffer = None
        self._dialog_stack: list[Dialog] = []
        self._theme = {
            'bg': Color(12, 12, 24),
            'fg': WHITE,
            'accent': Color(100, 200, 255),
            'dim': DIM,
            'surface': Color(20, 20, 40),
            'border': Color(60, 60, 100),
        }

    def set_theme(self, **kwargs):
        self._theme.update(kwargs)

    def on_tick(self, callback: Callable):
        self._on_tick = callback

    def on_draw(self, callback: Callable):
        self._draw_callback = callback

    def add(self, widget: Widget, focusable: bool = False):
        self.manager.add(widget, focusable)
        return widget

    def push_dialog(self, dialog: Dialog):
        self._dialog_stack.append(dialog)
        dialog.visible = True
        self.manager.add(dialog)
        for btn in dialog._buttons:
            self.manager.add(btn, focusable=True)
        for cw in dialog._content_widgets:
            self.manager.add(cw)
        self.manager.focus_first()

    def pop_dialog(self):
        if not self._dialog_stack:
            return
        dialog = self._dialog_stack.pop()
        self.manager.remove(dialog)
        for btn in dialog._buttons:
            self.manager.remove(btn)
        for cw in dialog._content_widgets:
            self.manager.remove(cw)

    def run(self):
        self._old_term = _set_raw()
        self._raw_mode = True
        _enable_mouse()
        self.running = True
        _save_term()

        sys.stdout.write('\033[?25l')
        sys.stdout.flush()

        try:
            self._loop()
        finally:
            _restore_term()
            self._cleanup()

    def _cleanup(self):
        _disable_mouse()
        if self._raw_mode and self._old_term:
            try:
                termios.tcsetattr(sys.stdin.fileno(),
                                  termios.TCSADRAIN, self._old_term)
            except Exception:
                pass
        self._raw_mode = False
        sys.stdout.write('\033[?25h\033[0m')
        sys.stdout.flush()

    def stop(self):
        self.running = False

    def render(self):
        self.canvas.clear()
        theme = self._theme
        for y in range(self.height):
            for x in range(self.width):
                self.canvas.set_pixel(x, y, ' ', bg=theme['bg'])

        if self._draw_callback:
            self._draw_callback(self.canvas)
        self.manager.render(self.canvas, z=50)

        term_w, term_h = self._get_term_size()
        ox = max(0, (term_w - self.width) // 2)
        oy = max(0, (term_h - self.height) // 2)

        output = ['\033[0m\033[?25l']
        for y in range(min(self.height, term_h - oy)):
            output.append(f'\033[{oy + y + 1};{ox + 1}H')
            row = self.canvas.buffer[y]
            last_fg = None
            last_bg = None
            line_parts = []
            for x in range(min(self.width, term_w - ox)):
                cell = row[x]
                if cell.fg != last_fg or cell.bg != last_bg:
                    if cell.fg is None and cell.bg is None:
                        line_parts.append('\033[0m')
                    else:
                        parts = []
                        if cell.fg:
                            parts.append(f'\033[38;2;{cell.fg.r};{cell.fg.g};{cell.fg.b}m')
                        if cell.bg:
                            parts.append(f'\033[48;2;{cell.bg.r};{cell.bg.g};{cell.bg.b}m')
                        line_parts.append(''.join(parts))
                    last_fg = cell.fg
                    last_bg = cell.bg
                line_parts.append(cell.char if cell.char else ' ')
            if last_fg or last_bg:
                line_parts.append('\033[0m')
            output.append(''.join(line_parts))
        sys.stdout.write(''.join(output))
        sys.stdout.flush()

    def _get_term_size(self):
        try:
            import shutil
            return shutil.get_terminal_size((80, 24))
        except Exception:
            return (80, 24)

    def _loop(self):
        last_tick = time.time()
        while self.running:
            now = time.time()
            dt = now - last_tick
            if dt >= self._tick_rate:
                last_tick = now
                key = _read_key(timeout=0.001)
                if key:
                    if key == 'mouse':
                        pass
                    else:
                        self._handle_key(key)

                mouse_events = _read_mouse_events(timeout=0)
                for etype, mx, my in mouse_events:
                    term_w, term_h = self._get_term_size()
                    ox = max(0, (term_w - self.width) // 2)
                    oy = max(0, (term_h - self.height) // 2)
                    mx_adj = mx - ox
                    my_adj = my - oy
                    self.manager.handle_event(etype, (mx_adj, my_adj))

                if self._on_tick:
                    self._on_tick(dt)
                self.render()

    def _handle_key(self, key: str):
        if self._dialog_stack:
            top = self._dialog_stack[-1]
            if key == 'escape':
                self.pop_dialog()
                top.dismiss(None)
                return
            elif key == 'enter' or key == '\r':
                focused = self.manager.get_focused()
                if focused and isinstance(focused, Button) and focused in top._buttons:
                    if focused.callback:
                        focused.callback()
                    return
            elif key == '\t':
                self.manager.focus_next()
                return
            elif key == 'tab_back':
                self.manager.focus_prev()
                return
            self.manager.handle_event('key_down', key)
            return

        if key == 'escape':
            self.stop()
        elif key == '\t':
            self.manager.focus_next()
        elif key == 'tab_back':
            self.manager.focus_prev()
        else:
            self.manager.handle_event('key_down', key)


# ═══════════════════════════════════════════════════════════════════
# FORM — layout container with labelled fields
# ═══════════════════════════════════════════════════════════════════

class Form(Widget):
    def __init__(self, x: int, y: int, width: int = 40,
                 title: str = 'Form',
                 fg: Color = WHITE, accent: Color = Color(100, 200, 255),
                 submit_callback: Optional[Callable[[dict], None]] = None,
                 cancel_callback: Optional[Callable[[], None]] = None):
        self.fields: list[tuple[str, Widget]] = []
        self.values: dict[str, any] = {}
        self.title = title
        self.fg = fg
        self.accent = accent
        self.submit_callback = submit_callback
        self.cancel_callback = cancel_callback
        self._field_y = y + 2
        self._focusables: list[Widget] = []
        super().__init__(x, y, width, 5)

    def add_field(self, label: str, widget: Widget):
        self.fields.append((label, widget))
        field_x = self.x + len(label) + 2
        widget.x = field_x
        widget.y = self._field_y
        self.values[label] = ''
        if isinstance(widget, Input):
            widget.callback = lambda t, l=label: self._set_value(l, t)
        elif isinstance(widget, Checkbox):
            widget.callback = lambda v, l=label: self._set_value(l, v)
        self._field_y += 2
        self.height = self._field_y - self.y + 2
        self._focusables.append(widget)

    def _set_value(self, label: str, value: any):
        self.values[label] = value

    def submit(self):
        if self.submit_callback:
            self.submit_callback(self.values)

    def cancel(self):
        if self.cancel_callback:
            self.cancel_callback()

    def render(self, canvas: Canvas, z: float = 0):
        if not self.visible:
            return
        x, y, w = self.x, self.y, self.width
        fg = self.accent if self.focused else self.fg
        canvas.set_pixel(x, y, '┌', fg, z=z)
        canvas.set_pixel(x + w - 1, y, '┐', fg, z=z)
        canvas.set_pixel(x, y + self.height - 1, '└', fg, z=z)
        canvas.set_pixel(x + w - 1, y + self.height - 1, '┘', fg, z=z)
        for i in range(1, w - 1):
            canvas.set_pixel(x + i, y, '─', fg, z=z)
            canvas.set_pixel(x + i, y + self.height - 1, '─', fg, z=z)
        for i in range(1, self.height - 1):
            canvas.set_pixel(x, y + i, '│', fg, z=z)
            canvas.set_pixel(x + w - 1, y + i, '│', fg, z=z)
        title = f' {self.title} '
        for i, ch in enumerate(title):
            canvas.set_pixel(x + 2 + i, y, ch, WHITE, z=z + 1)

        for label, widget in self.fields:
            for i, ch in enumerate(label):
                canvas.set_pixel(x + 1 + i, widget.y, ch, self.fg.mul(0.7), z=z)
            canvas.set_pixel(x + len(label) + 1, widget.y, ':', self.fg, z=z)
            widget.render(canvas, z)

        btn_y = y + self.height - 2
        submit_x = x + w - 14
        for i, ch in enumerate('[ Submit ]'):
            fg = self.accent
            canvas.set_pixel(submit_x + i, btn_y, ch, fg, z=z + 2)
        cancel_x = x + w - 14
        for i, ch in enumerate(' [Cancel]'):
            canvas.set_pixel(cancel_x + i, btn_y, ch, DIM, z=z + 2)


# ═══════════════════════════════════════════════════════════════════
# DIALOG — modal overlay
# ═══════════════════════════════════════════════════════════════════

class Dialog(Widget):
    def __init__(self, x: int, y: int, width: int = 40, height: int = 10,
                 title: str = 'Dialog',
                 fg: Color = WHITE, bg: Color = Color(20, 20, 35),
                 border_fg: Color = Color(100, 150, 255),
                 callback: Optional[Callable[[Optional[str]], None]] = None):
        super().__init__(x, y, width, height)
        self.title = title
        self.fg = fg
        self.bg = bg
        self.border_fg = border_fg
        self.callback = callback
        self.result: Optional[str] = None
        self._buttons: list[Button] = []
        self._button_idx = 0
        self._content_widgets: list[Widget] = []

    def add_button(self, label: str, result: str = ''):
        btn_x = self.x + 2 + len(self._buttons) * 12
        btn = Button(btn_x, self.y + self.height - 3, len(label) + 2,
                     text=label,
                     callback=lambda r=result: self.dismiss(r))
        self._buttons.append(btn)
        return btn

    def add_content(self, widget: Widget):
        self._content_widgets.append(widget)

    def dismiss(self, result: Optional[str]):
        self.result = result
        self.visible = False
        if self.callback:
            self.callback(result)

    def render(self, canvas: Canvas, z: float = 0):
        if not self.visible:
            return
        x, y, w, h = self.x, self.y, self.width, self.height
        for dy in range(h):
            for dx in range(w):
                px, py = x + dx, y + dy
                if 0 <= px < canvas.w and 0 <= py < canvas.h:
                    canvas.set_pixel(px, py, ' ', None, self.bg, z=z)

        bfg = self.border_fg
        canvas.set_pixel(x, y, '╔', bfg, z=z + 1)
        canvas.set_pixel(x + w - 1, y, '╗', bfg, z=z + 1)
        canvas.set_pixel(x, y + h - 1, '╚', bfg, z=z + 1)
        canvas.set_pixel(x + w - 1, y + h - 1, '╝', bfg, z=z + 1)
        for i in range(1, w - 1):
            canvas.set_pixel(x + i, y, '═', bfg, z=z + 1)
            canvas.set_pixel(x + i, y + h - 1, '═', bfg, z=z + 1)
        for i in range(1, h - 1):
            canvas.set_pixel(x, y + i, '║', bfg, z=z + 1)
            canvas.set_pixel(x + w - 1, y + i, '║', bfg, z=z + 1)

        title = f' {self.title} '
        for i, ch in enumerate(title):
            canvas.set_pixel(x + 2 + i, y, ch, WHITE, z=z + 2)

        for widget in self._content_widgets:
            widget.render(canvas, z + 2)

        for btn in self._buttons:
            btn.render(canvas, z + 2)
