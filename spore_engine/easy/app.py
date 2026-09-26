from __future__ import annotations
import sys
import time
import math
from ..core.canvas import Canvas, HiResCanvas
from ..core.color import Color, Gradient, DIM
from ..core.input import Input, KeyState, KeyEvent, MouseEvent, ResizeEvent
from ..core.term import (DEFAULT_TERM_SIZE, TerminalSession, monotonic,
                         posix_terminal_available, terminal_size)
from ..core.util import clamp
from ..core.camera import Camera  # noqa: F401  (re-exported for the subpackage API)
from ..fx.screenfx import ScreenFX
from ..fx.transitions import Transition
from .sprite import GameSprite

__all__ = ['App']


def _default_assets():
    """The process-wide default asset store, resolved lazily.

    Imported inside the function so ``easy`` does not pull in the asset
    machinery (and its caches) unless an app is actually constructed."""
    from ..core.assets import default_store
    return default_store



class App:
    """A batteries-included game loop.

        app = App(width=80, height=30, title='Hello')
        app.bg(Color(10, 10, 40))
        app.on_key('space', lambda a: a.stop())
        app.run()

    Lifecycle is handled for you: raw mode, the alternate screen, a hidden
    cursor and optional mouse reporting are all entered on :meth:`run` and
    restored in a ``finally``, so Ctrl-C or a crashing update still hands the
    user back a working shell.

    When stdin or stdout is not a terminal (a pipe, a test, a notebook),
    :meth:`run` refuses to spin: there is no key to read and rendering into a
    pipe would flood it. Call :meth:`run_headless` if you want frames anyway.
    """

    def __init__(self, width=None, height=None, title="Spore App", fps=30,
                 colors=True, mouse=False, alt_screen=True,
                 assets=None):
        if width is None or height is None:
            tw, th = terminal_size(DEFAULT_TERM_SIZE)
            width = width or tw
            height = height or th
        self.width = width
        self.height = height
        self.title = title
        self.fps = fps
        if fps <= 0:
            raise ValueError(f'fps must be positive, got {fps}')
        self.colors = colors
        self.canvas = Canvas(width, height)
        self.hr = HiResCanvas(width, height * 2)
        self.camera = None
        self._sprites = []
        self._bg_color = None
        self._bg_gradient = None
        self._t = 0.0
        self._dt = 0.0
        self._running = False
        self._paused = False
        self._frames = 0
        self._max_frames = None
        self._tick_handlers = []
        self._key_handlers = {}
        self._any_key_handlers = []
        self._click_handlers = []
        self._wheel_handlers = []
        self._resize_handlers = []
        self._init_handlers = []
        self._widgets = []
        self._focused_widget = None
        self._last_frame = 0.0
        self._bg_art = None
        self._bg_art_scroll_x = 0.0
        self._bg_art_scroll_y = 0.0
        self._input = Input(0, mouse=mouse)
        self.keys = KeyState()
        self.screen_fx = ScreenFX()
        self._transition = None
        self._transition_t = 0.0
        self._prev_canvas = None
        #: Injected asset store, or the process-wide default. Passing one keeps
        #: a test or a second app from sharing caches with the first.
        self.assets = assets if assets is not None else _default_assets()
        self._alt_screen = alt_screen
        self._mouse = mouse
        self._session = None

    @property
    def interactive(self) -> bool:
        """Whether this app can actually read keys from a real terminal."""
        return posix_terminal_available()

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
    def frames(self) -> int:
        """How many frames have been rendered by the last :meth:`run`."""
        return self._frames

    @property
    def paused(self):
        return self._paused

    @paused.setter
    def paused(self, v):
        self._paused = v

    @property
    def fx(self):
        return self.screen_fx

    # -- convenience effect triggers -----------------------------------

    def add_shake(self, power: float, duration: float = 1.1):
        self.screen_fx.add_shake(power, duration)

    def add_flash(self, alpha: float, duration: float = 0.5):
        self.screen_fx.add_flash(alpha, duration)

    def add_fade(self, color=Color(0, 0, 0), duration: float = 1.0,
                 inverse: bool = False):
        self.screen_fx.add_fade(color, duration, inverse)

    def transition_to(self, transition: Transition, duration: float = 0.5,
                      keep_scene: bool = False):
        if not keep_scene:
            self._prev_canvas = self.canvas.copy()
        self._transition = transition
        self._transition_t = 0.0
        self._transition_dur = max(0.01, duration)

    # -- sprite management ---------------------------------------------

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
        self._bg_art = GameSprite(art)
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
        """Called with ``handler(app, event)`` for every ``KeyEvent`` (presses,
        repeats, and synthesized releases)."""
        self._any_key_handlers.append(handler)
        return handler

    def on_click(self, handler):
        """Called with ``handler(app, x, y)`` on left-button press."""
        self._click_handlers.append(handler)
        return handler

    def on_wheel(self, handler):
        """Called with ``handler(app, dx, dy)`` on mouse-wheel scroll."""
        self._wheel_handlers.append(handler)
        return handler

    def on_resize(self, handler):
        """Called with ``handler(app, width, height)`` when the terminal
        reports a size change."""
        self._resize_handlers.append(handler)
        return handler

    def on_init(self, handler):
        self._init_handlers.append(handler)
        return handler

    def is_down(self, key: str) -> bool:
        return self.keys.down(key)

    def sprite(self, art, x=0, y=0, fg=None, bg=None, z=0, hires=False):
        s = GameSprite(art, x, y, fg, bg, z)
        s.hires = hires
        self.add(s)
        return s

    def text(self, text, x=0, y=0, fg=None, z=0, hires=False):
        s = GameSprite("", x, y, fg, z=z)
        s.hires = hires
        s.draw_text(0, 0, text, fg)
        self.add(s)
        return s

    def rect(self, w, h, x=0, y=0, char='#', fg=None, bg=None, z=0, hires=False):
        s = GameSprite.rect(w, h, char, fg, bg)
        s.x = x
        s.y = y
        s.z = z
        s.hires = hires
        self.add(s)
        return s

    # -- lifecycle ------------------------------------------------------

    def run(self, max_frames: int | None = None):
        """Run until :meth:`stop` is called, ``q`` is pressed, or Ctrl-C.

        With a non-terminal stdin or stdout this raises ``RuntimeError``
        instead of looping forever - see :meth:`run_headless`. ``max_frames``
        bounds the loop, which is what the tests and demos use.
        """
        if not self.interactive:
            raise RuntimeError(
                'App.run() needs a real terminal on both stdin and stdout; '
                'this process has a pipe or a redirected stream. Use '
                'run_headless(max_frames=...) to render frames anyway.')

        for h in self._init_handlers:
            h(self)

        self._running = True
        self._max_frames = max_frames
        self._last_frame = monotonic()
        self._session = TerminalSession(
            mouse=self._mouse, alt_screen=self._alt_screen,
            raw=True, on_resize=self._on_resize_signal, stream=sys.stdout)
        try:
            with self._session:
                self._input.enter_raw()
                self._main_loop()
        except KeyboardInterrupt:
            pass
        finally:
            # Belt and braces: the session already restores the terminal, but a
            # failure inside __exit__ must not leave raw mode on.
            try:
                self._input.exit_raw()
            except Exception:
                pass

    def run_headless(self, max_frames: int = 1):
        """Render ``max_frames`` frames with no terminal setup and no output.

        Intended for tests and for driving an app from another program. Nothing
        is written to stdout, so this is safe to call under a pipe."""
        if max_frames < 0:
            raise ValueError(f'max_frames must be non-negative, got {max_frames}')
        for h in self._init_handlers:
            h(self)
        self._running = True
        self._max_frames = max_frames
        self._last_frame = monotonic()
        try:
            self._main_loop(echo=False)
        finally:
            self._running = False
        return self._frames

    def stop(self):
        self._running = False

    def _on_resize_signal(self, cols, lines):
        """SIGWINCH handler: adopt the new size and tell subscribers."""
        self._apply_resize(cols, lines)

    def _apply_resize(self, cols, lines):
        if cols <= 0 or lines <= 0:
            return
        if (cols, lines) == (self.width, self.height):
            return
        self.width = cols
        self.height = lines
        self.canvas.resize(cols, lines)
        if self.hr is not None:
            self.hr.resize(cols, lines * 2)
        for h in self._resize_handlers:
            h(self, cols, lines)

    # -- rendering ------------------------------------------------------

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

    def _sprite_pos(self, s: GameSprite):
        if self.camera is not None:
            return self.camera.to_screen(s.x, s.y)
        return round(s.x), round(s.y)

    def _draw_sprite(self, s: GameSprite, hires: bool = False):
        if not s._visible or s._opacity <= 0:
            return
        use_hr = hires or getattr(s, 'hires', False)
        target = self.hr if use_hr else self.canvas
        if use_hr:
            sx, sy = self.camera.to_screen(s.x, s.y) if self.camera is not None \
                else (round(s.x), round(s.y))
            ox, oy = sx * 2, sy * 2
        else:
            ox, oy = self._sprite_pos(s)
        fg = s._fg
        bg = s._bg
        mult = 2 if use_hr else 1
        if s._opacity < 1 and fg:
            fg = Color(int(fg.r * s._opacity), int(fg.g * s._opacity), int(fg.b * s._opacity))
        for cell in s._cells:
            char, dx, dy = cell[0], cell[1], cell[2]
            px = ox + int(dx * s._scale_x)
            py = oy + int(dy * s._scale_y) * mult
            if s._rotation != 0:
                cw = s._width * s._scale_x
                chh = s._height * s._scale_y * mult
                rx = px - (ox + cw / 2)
                ry = py - (oy + chh / 2)
                cos_a = math.cos(s._rotation)
                sin_a = math.sin(s._rotation)
                px = int(ox + cw / 2 + rx * cos_a - ry * sin_a)
                py = int(oy + chh / 2 + rx * sin_a + ry * cos_a)
            if use_hr:
                target.set_pixel(px, py, char, fg, bg, s._z)
                target.set_pixel(px, py + 1, char, fg, bg, s._z)
            else:
                target.set_pixel(px, py, char, fg, bg, s._z)

    def _main_loop(self, echo: bool = True):
        frame_time = 1.0 / self.fps
        while self._running:
            # Checked before rendering, not after: a while-loop would otherwise
            # always produce one frame, so max_frames=0 would mean "one frame".
            if self._max_frames is not None and self._frames >= self._max_frames:
                break
            now = monotonic()
            self._dt = now - self._last_frame
            self._last_frame = now
            if self._dt > 0.1:
                # A long stall (breakpoint, swap, NTP step) must not teleport
                # every animation; clamp to one frame so it looks like a hitch.
                self._dt = frame_time
            if not self._paused:
                self._t += self._dt
            self.screen_fx.tick(self._dt)
            self._handle_input()
            if not self._paused:
                self._update(self._dt)
            self._render(echo=echo)
            self._frames += 1
            sleep_time = frame_time - (monotonic() - now)
            if sleep_time > 0:
                time.sleep(sleep_time)

    def _handle_input(self):
        if not self.interactive:
            return
        events = self._input.events(0)
        if not events:
            return
        self.keys.update(events)
        for ev in events:
            if isinstance(ev, KeyEvent):
                for h in self._any_key_handlers:
                    h(self, ev)
                if ev.down and ev.key in self._key_handlers:
                    self._key_handlers[ev.key](self)
                if ev.down and ev.key == 'q' and 'q' not in self._key_handlers:
                    # Only a built-in quit if the app has not claimed 'q'
                    # itself; a game that binds 'q' to something else keeps it.
                    self._running = False
            elif isinstance(ev, MouseEvent):
                if ev.action == 'press' and ev.button == 0:
                    for h in self._click_handlers:
                        h(self, ev.x, ev.y)
                elif ev.action == 'scroll':
                    for h in self._wheel_handlers:
                        h(self, ev.scroll_dx, ev.scroll_dy)
            elif isinstance(ev, ResizeEvent):
                self._apply_resize(ev.width, ev.height)
                for h in self._resize_handlers:
                    h(self, ev.width, ev.height)

    def _update(self, dt):
        if self.camera is not None:
            self.camera.clamp()
        for s in self._sprites:
            s.update(dt)
        for h in self._tick_handlers:
            h(self, dt)

    def _render_frame(self):
        self.canvas.clear()
        if self.hr is not None:
            self.hr.clear()
        self._fill_bg()
        sorted_sprites = sorted(self._sprites, key=lambda s: s.z)
        for s in sorted_sprites:
            self._draw_sprite(s)
        if self.hr is not None:
            self.hr.to_canvas(self.canvas)
        if self.interactive and self.title:
            self.canvas.draw_text(2, self.height - 1, f" {self.title} ", DIM, z=999)
        if self._transition is not None and self._prev_canvas is not None:
            self._transition_t += self._dt / self._transition_dur
            self._transition.apply(self.canvas, self._prev_canvas,
                                   clamp(self._transition_t, 0, 1))
            if self._transition_t >= 1:
                self._transition = None
                self._prev_canvas = None
        self.screen_fx.apply(self.canvas, seed=int(self._t * 100))

    def _render(self, echo: bool = True):
        self._render_frame()
        if echo:
            self.canvas.render_to(sys.stdout)
