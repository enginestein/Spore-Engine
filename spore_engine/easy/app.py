from __future__ import annotations
import sys, time, os, select, tty, termios, math
from ..core.canvas import Canvas, HiResCanvas
from ..core.color import Color, Gradient, WHITE, DIM, BLACK
from .sprite import Sprite


def _termsize():
    try:
        return os.get_terminal_size().columns, os.get_terminal_size().lines
    except:
        return 100, 40


class App:
    def __init__(self, width=None, height=None, title="Spore App", fps=30, colors=True):
        if width is None or height is None:
            tw, th = _termsize()
            width = width or tw
            height = height or th
        self.width = width
        self.height = height
        self.title = title
        self.fps = fps
        self.colors = colors
        self.canvas = Canvas(width, height)
        self.hr = HiResCanvas(width, height * 2)
        self._sprites = []
        self._bg_color = None
        self._bg_gradient = None
        self._t = 0.0
        self._dt = 0.0
        self._running = False
        self._paused = False
        self._tick_handlers = []
        self._key_handlers = {}
        self._any_key_handlers = []
        self._click_handlers = []
        self._init_handlers = []
        self._widgets = []
        self._focused_widget = None
        self._is_tty = sys.stdin.isatty() and sys.stdout.isatty()
        self._old_term = None
        self._last_frame = 0.0
        self._bg_art = None
        self._bg_art_scroll_x = 0.0
        self._bg_art_scroll_y = 0.0

    @property
    def w(self):
        return self.width

    @property
    def h(self):
        return self.height

    @property
    def t(self):
        return self._t

    @property
    def dt(self):
        return self._dt

    @property
    def paused(self):
        return self._paused

    @paused.setter
    def paused(self, v):
        self._paused = v

    def add(self, *sprites):
        for s in sprites:
            if s not in self._sprites:
                self._sprites.append(s)

    def remove(self, sprite):
        if sprite in self._sprites:
            self._sprites.remove(sprite)

    def clear(self):
        self._sprites = []

    def bg(self, color=None):
        self._bg_color = color

    def bg_gradient(self, *colors):
        self._bg_gradient = Gradient(*colors) if colors else None

    def bg_art(self, art, scroll_x=0.0, scroll_y=0.0):
        self._bg_art = Sprite(art)
        self._bg_art_scroll_x = scroll_x
        self._bg_art_scroll_y = scroll_y

    def on_tick(self, handler):
        self._tick_handlers.append(handler)
        return handler

    def on_key(self, key, handler=None):
        if handler is None:
            return lambda h: self._key_handlers.update({key: h}) or h
        self._key_handlers[key] = handler
        return handler

    def on_any_key(self, handler):
        self._any_key_handlers.append(handler)
        return handler

    def on_click(self, handler):
        self._click_handlers.append(handler)
        return handler

    def on_init(self, handler):
        self._init_handlers.append(handler)
        return handler

    def sprite(self, art, x=0, y=0, fg=None, bg=None, z=0):
        s = Sprite(art, x, y, fg, bg, z)
        self.add(s)
        return s

    def text(self, text, x=0, y=0, fg=None, z=0):
        s = Sprite("", x, y, fg, z=z)
        s.draw_text(0, 0, text, fg)
        self.add(s)
        return s

    def rect(self, w, h, x=0, y=0, char='#', fg=None, bg=None, z=0):
        s = Sprite.rect(w, h, char, fg, bg)
        s.x = x
        s.y = y
        s.z = z
        self.add(s)
        return s

    def run(self):
        for h in self._init_handlers:
            h(self)
        self._running = True
        self._last_frame = time.time()
        if self._is_tty:
            self._setup_terminal()
        try:
            self._main_loop()
        except KeyboardInterrupt:
            pass
        finally:
            self._cleanup()

    def stop(self):
        self._running = False

    def _setup_terminal(self):
        self._old_term = termios.tcgetattr(sys.stdin)
        tty.setraw(sys.stdin)
        print('\033[?25l\033[2J', end='', flush=True)

    def _cleanup(self):
        if self._old_term:
            termios.tcsetattr(sys.stdin, termios.TCSANOW, self._old_term)
        print('\033[?25h\033[0m', end='', flush=True)

    def _fill_bg(self):
        if self._bg_gradient:
            for y in range(self.height):
                t = y / self.height if self.height > 0 else 0
                bg = self._bg_gradient.at(t)
                for x in range(self.width):
                    self.canvas.set_pixel(x, y, ' ', bg=bg, z=0)
        elif self._bg_color:
            for y in range(self.height):
                for x in range(self.width):
                    self.canvas.set_pixel(x, y, ' ', bg=self._bg_color, z=0)
        elif self._bg_art:
            s = self._bg_art
            off_x = int(self._t * self._bg_art_scroll_x) % max(s.width, 1)
            off_y = int(self._t * self._bg_art_scroll_y) % max(s.height, 1)
            for ty in range(0, self.height, max(s.height, 1)):
                for tx in range(0, self.width, max(s.width, 1)):
                    for cell in s._cells:
                        ch, dx, dy = cell[0], cell[1], cell[2]
                        px = (tx + dx + off_x) % self.width
                        py = (ty + dy + off_y) % self.height
                        self.canvas.set_pixel(px, py, ch, s.fg, s.bg, 0)

    def _main_loop(self):
        frame_time = 1.0 / self.fps
        while self._running:
            now = time.time()
            self._dt = now - self._last_frame
            self._last_frame = now
            if self._dt > 0.1:
                self._dt = frame_time
            if not self._paused:
                self._t += self._dt
            self._handle_input()
            if not self._paused:
                self._update(self._dt)
            self._render()
            elapsed = time.time() - now
            sleep_time = frame_time - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

    def _handle_input(self):
        if not self._is_tty:
            return
        if select.select([sys.stdin], [], [], 0)[0]:
            ch = sys.stdin.read(1)
            if ch in self._key_handlers:
                self._key_handlers[ch](self)
            for h in self._any_key_handlers:
                h(self, ch)
            if ch == 'q':
                self._running = False

    def _update(self, dt):
        for s in self._sprites:
            s.update(dt)
        for h in self._tick_handlers:
            h(self, dt)

    def _render(self):
        self.canvas.clear()
        self._fill_bg()
        sorted_sprites = sorted(self._sprites, key=lambda s: s.z)
        for s in sorted_sprites:
            s.render(self.canvas)
        if self._is_tty and self.title:
            self.canvas.draw_text(2, self.height - 1, f" {self.title} ", DIM, z=999)
        self.canvas.render_to(sys.stdout)
