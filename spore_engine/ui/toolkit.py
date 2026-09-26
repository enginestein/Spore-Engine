from __future__ import annotations
import sys
import select
import os
from collections.abc import Callable
from ..core.color import Color, WHITE, DIM
from ..core.canvas import Canvas
from ..core.term import (DEFAULT_TERM_SIZE, TerminalSession, monotonic,
                         posix_terminal_available, terminal_size, write_stdout)
from .widgets import Widget, WidgetManager, Button, TextField, Checkbox


# -------------------------------------------------------------------
# TERMINAL EVENT LOOP
# -------------------------------------------------------------------
#
# Raw mode, the alternate screen, cursor visibility and mouse reporting are all
# owned by core.term now. This module used to import termios/tty at module scope
# (breaking the whole package on Windows) and kept its own `_defs` global
# alongside an `self._old_term` attribute, so it saved and restored terminal
# state twice and could restore the wrong one.


_KEYS = {
    '\x1b[A': 'up', '\x1b[B': 'down', '\x1b[C': 'right', '\x1b[D': 'left',
    '\x1b[Z': 'tab_back',
    '\x1b[H': 'home', '\x1b[F': 'end',
    '\x1b[2~': 'insert', '\x1b[3~': 'delete', '\x1b[5~': 'page_up',
    '\x1b[6~': 'page_down',
    '\x7f': 'backspace', '\x1b': 'escape',
    '\t': '\t', '\r': 'enter',
}


def _is_sgr_mouse(seq: str) -> bool:
    """True for an SGR mouse report such as ``\\x1b[<0;10;5M``."""
    return len(seq) > 3 and seq.startswith('\x1b[<') and seq[-1] in ('M', 'm')


def _read_key(timeout: float = 0.01) -> str | None:
    if not select.select([sys.stdin], [], [], timeout)[0]:
        return None
    ch = os.read(sys.stdin.fileno(), 1).decode('utf-8', errors='replace')
    if not ch:
        # EOF: select() keeps reporting the descriptor as ready, so this must
        # read as "no key" rather than as a character.
        return None
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
    # A click is an escape-prefixed sequence too. Reporting it as 'escape' made
    # every mouse click quit the app or close the top dialog, so hand it to
    # _read_mouse_events() via the 'mouse' sentinel instead.
    if _is_sgr_mouse(seq):
        return 'mouse'
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
                        # A release is reported with a lowercase 'm'
                        # terminator, so the button code has to be consulted
                        # before the callback bits. Without this, mouse_up was
                        # never delivered and clicks on a button never fired:
                        # Button only triggers on mouse_up.
                        if ch == 'm' or cb & 64:
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
        self._on_tick: Callable | None = None
        self._draw_callback: Callable | None = None
        self._tick_rate = 0.033
        self._raw_mode = False
        self._session: TerminalSession | None = None
        self._max_ticks: int | None = None
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
        dialog.on_dismiss = self._on_dialog_dismissed
        self.manager.add(dialog)
        for btn in dialog._buttons:
            self.manager.add(btn, focusable=True)
        for cw in dialog._content_widgets:
            self.manager.add(cw)
        self.manager.focus_first()

    def _on_dialog_dismissed(self, dialog: Dialog):
        # A dismissed dialog left itself on the stack, so it kept swallowing
        # keys and its widgets leaked into the manager on every cycle.
        if dialog in self._dialog_stack:
            self._unregister_dialog(dialog)

    def pop_dialog(self):
        if self._dialog_stack:
            self._unregister_dialog(self._dialog_stack[-1])

    def _unregister_dialog(self, dialog: Dialog):
        self._dialog_stack.remove(dialog)
        self.manager.remove(dialog)
        for btn in dialog._buttons:
            self.manager.remove(btn)
        for cw in dialog._content_widgets:
            self.manager.remove(cw)

    def run(self, max_ticks: int | None = None):
        """Run the event loop until :meth:`stop`.

        Terminal setup and teardown are handled by a
        :class:`~spore_engine.core.term.TerminalSession`, so raw mode, the
        alternate screen, the cursor and mouse reporting are always restored
        even if the loop raises.

        With a non-terminal stdin this raises ``RuntimeError`` rather than
        spinning with no way to read a key. ``max_ticks`` bounds the loop for
        tests.
        """
        if not posix_terminal_available():
            raise RuntimeError(
                'TerminalApp.run() needs a real terminal on stdin; this '
                'process has a pipe or a redirected stream.')
        self.running = True
        self._max_ticks = max_ticks
        self._session = TerminalSession(mouse=True, alt_screen=True, raw=True)
        try:
            with self._session:
                self._loop()
        except KeyboardInterrupt:
            pass
        finally:
            self._cleanup()

    def _cleanup(self):
        # The session restores the terminal; this only clears our own flags.
        self._raw_mode = False
        write_stdout('\033[0m')

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
        write_stdout(''.join(output))

    def _get_term_size(self):
        return terminal_size(DEFAULT_TERM_SIZE)

    def _loop(self):
        last_tick = monotonic()
        ticks = 0
        while self.running:
            now = monotonic()
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
                ticks += 1
                if self._max_ticks is not None and ticks >= self._max_ticks:
                    break

    def _handle_key(self, key: str):
        if self._dialog_stack:
            top = self._dialog_stack[-1]
            if key == 'escape':
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


# -------------------------------------------------------------------
# FORM - layout container with labelled fields
# -------------------------------------------------------------------

class Form(Widget):
    def __init__(self, x: int, y: int, width: int = 40,
                 title: str = 'Form',
                 fg: Color = WHITE, accent: Color = Color(100, 200, 255),
                 submit_callback: Callable[[dict], None] | None = None,
                 cancel_callback: Callable[[], None] | None = None):
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
        if isinstance(widget, TextField):
            widget.callback = lambda t, l=label: self._set_value(l, t)
        elif isinstance(widget, Checkbox):
            widget.callback = lambda v, l=label: self._set_value(l, v)
        self._field_y += 2
        self.height = self._field_y - self.y + 2
        self._focusables.append(widget)
        # Returned for parity with Dialog.add_button and TerminalApp.add, so a
        # caller can keep a reference without indexing self.fields.
        return widget

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


# -------------------------------------------------------------------
# DIALOG - modal overlay
# -------------------------------------------------------------------

class Dialog(Widget):
    def __init__(self, x: int, y: int, width: int = 40, height: int = 10,
                 title: str = 'Dialog',
                 fg: Color = WHITE, bg: Color = Color(20, 20, 35),
                 border_fg: Color = Color(100, 150, 255),
                 callback: Callable[[str | None], None] | None = None):
        super().__init__(x, y, width, height)
        self.title = title
        self.fg = fg
        self.bg = bg
        self.border_fg = border_fg
        self.callback = callback
        self.result: str | None = None
        # Set by TerminalApp.push_dialog so dismissing a dialog also takes it
        # off the stack and unregisters its widgets.
        self.on_dismiss: Callable[[Dialog], None] | None = None
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

    def dismiss(self, result: str | None):
        self.result = result
        self.visible = False
        if self.callback:
            self.callback(result)
        if self.on_dismiss:
            self.on_dismiss(self)

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
