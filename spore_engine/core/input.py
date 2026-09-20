from __future__ import annotations
import os
import select
import time
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Optional, Union

try:
    import termios
    import tty
    _HAVE_TERMIOS = True
except ImportError:  # e.g. Windows / non-POSIX Python
    termios = None
    tty = None
    _HAVE_TERMIOS = False

KEY_UP = 'up'
KEY_DOWN = 'down'
KEY_LEFT = 'left'
KEY_RIGHT = 'right'
KEY_ENTER = 'enter'
KEY_SPACE = 'space'
KEY_ESCAPE = 'escape'
KEY_TAB = 'tab'
KEY_SHIFT_TAB = 'shift-tab'
KEY_BACKSPACE = 'backspace'
KEY_DELETE = 'delete'
KEY_INSERT = 'insert'
KEY_HOME = 'home'
KEY_END = 'end'
KEY_PAGE_UP = 'pageup'
KEY_PAGE_DOWN = 'pagedown'
KEY_CTRL_C = 'ctrl-c'
KEY_CTRL_D = 'ctrl-d'
KEY_CTRL_Z = 'ctrl-z'

_F1_TO_F12 = [f'F{i}' for i in range(1, 13)]


@dataclass(frozen=True)
class KeyEvent:
    """One key state change. ``down=True`` is a press (or a terminal repeat
    while the key is held, in which case ``repeat`` is set); ``down=False``
    is a release synthesized by the engine when the key stops repeating."""

    key: str
    down: bool = True
    repeat: bool = False


@dataclass(frozen=True)
class MouseEvent:
    """SGR-mouse event decoded from the terminal (button / wheel).

    ``action`` is ``'press'`` | ``'release'`` | ``'move'`` | ``'scroll'``.
    For ``scroll``, the terminal y-axis grows downward: ``scroll_dy`` is
    ``+1`` for wheel *down* (toward the user) and ``-1`` for wheel *up*;
    ``scroll_dx`` is ``+1`` for wheel *right*, ``-1`` for *left*.
    """

    x: int = 0
    y: int = 0
    button: int = 0            # 0 left, 1 middle, 2 right
    action: str = 'press'      # 'press' | 'release' | 'move' | 'scroll'
    scroll_dx: int = 0
    scroll_dy: int = 0
    shift: bool = False
    alt: bool = False
    ctrl: bool = False


@dataclass(frozen=True)
class ResizeEvent:
    """Terminal size changed; width/height are cell dimensions."""

    width: int
    height: int


InputEvent = Union[KeyEvent, MouseEvent, ResizeEvent]


class Input:
    """Terminal input with escape-sequence decoding and a real event model.

    Use from a scene loop::

        inp = Input()
        with inp.raw():
            while running:
                for ev in inp.events(1 / 30):
                    if isinstance(ev, KeyEvent) and ev.down:
                        if ev.key == KEY_LEFT: move_left()

    ``Input`` is pull-based: call ``events()`` (or ``poll()``) from your frame
    loop and it produces a complete stream of ``KeyEvent`` / ``MouseEvent`` /
    ``ResizeEvent``. Terminals only ever report key *presses* (and, on
    terminals with key auto-repeat, repeats) - a release is silent, so the
    engine *synthesizes* one: a key that stops arriving for longer than
    ``release_delay`` seconds emits ``KeyEvent(down=False)``.

    Because that release is a timeout heuristic, holds do not strictly depend
    on terminal key repeat: a key held with auto-repeat is tracked exactly
    (it releases only once the repeats stop), while a key held on a terminal
    that never repeats simply degrades to a press followed by a synthesized
    release after ``release_delay``. ``repeat_grace`` absorbs jitter between
    repeats (a repeat that arrives just after a synthesized release is
    treated as a hold continuation, never as a brand-new press).

    Mouse tracking (``enable_mouse()``) decodes SGR mouse reports into
    ``MouseEvent`` (buttons, motion and wheel); terminal resize reports and
    polling both become ``ResizeEvent``. Raw mode requires ``termios``
    (POSIX); on non-POSIX platforms the module still imports and
    ``poll()``/``get()`` work on already-cooked input streams.
    """

    def __init__(self, fd: int = 0, clock=None, release_delay: float = 0.20,
                 repeat_grace: float = 0.45, mouse: bool = False):
        self.fd = fd
        self._clock = clock or time.monotonic
        self._release_delay = release_delay
        self._repeat_grace = repeat_grace
        self._held: dict[str, float] = {}
        self._released_at: dict[str, float] = {}
        self._mouse = mouse
        self._enabled_mouse = False
        self._last_size: Optional[tuple[int, int]] = None
        self._size_check = 0.0
        self._saved = None
        self._raw = 0

    # -- terminal state --------------------------------------------------

    @property
    def isatty(self) -> bool:
        try:
            return os.isatty(self.fd)
        except Exception:
            return False

    @property
    def raw_enabled(self) -> bool:
        return self._raw > 0

    @property
    def held_keys(self) -> set[str]:
        return set(self._held)

    def enter_raw(self):
        if not _HAVE_TERMIOS:
            raise RuntimeError(
                "raw terminal mode requires termios (POSIX / Unix-like "
                "platforms); on Windows terminals, run through SSH or use "
                "the cooked ``poll()`` path instead")
        self._saved = termios.tcgetattr(self.fd)
        tty.setraw(self.fd)
        self._raw += 1
        if self._mouse:
            self.enable_mouse()

    def exit_raw(self):
        if not self._raw:
            return
        self._raw -= 1
        if self._raw == 0:
            if self._mouse:
                self.disable_mouse()
            if self._saved is not None:
                termios.tcsetattr(self.fd, termios.TCSANOW, self._saved)
                self._saved = None

    @contextmanager
    def raw(self):
        self.enter_raw()
        try:
            yield self
        finally:
            self.exit_raw()

    # -- mouse -----------------------------------------------------------

    @property
    def mouse_enabled(self) -> bool:
        return self._enabled_mouse

    def enable_mouse(self):
        self._enabled_mouse = True
        self._write('\x1b[?1000h\x1b[?1002h\x1b[?1003h\x1b[?1006h\x1b[?1015h')

    def disable_mouse(self):
        self._enabled_mouse = False
        self._write('\x1b[?1000l\x1b[?1002l\x1b[?1003l\x1b[?1006l\x1b[?1015l')

    def _write(self, codes: str):
        if self.isatty:
            try:
                os.write(self.fd, codes.encode())
            except OSError:
                pass

    def _terminal_size(self):
        try:
            return os.get_terminal_size(self.fd)
        except (OSError, ValueError, AttributeError):
            return None

    # -- low-level reading ------------------------------------------------

    def available(self) -> bool:
        try:
            return bool(select.select([self.fd], [], [], 0)[0])
        except (OSError, ValueError):  # non-socket fd on Windows, closed fd
            return False

    def _read_byte(self, timeout: Optional[float]) -> int | None:
        try:
            if select.select([self.fd], [], [], timeout)[0]:
                data = os.read(self.fd, 1)
                if data:
                    return data[0]
        except (OSError, ValueError):  # non-socket fd on Windows, closed fd
            if timeout is not None and timeout > 0:
                try:
                    data = os.read(self.fd, 1)
                    if data:
                        return data[0]
                except OSError:
                    pass
        return None

    def _read_escape(self):
        c2 = self._read_byte(0.02)
        if c2 is None:
            return ('key', KEY_ESCAPE)
        if c2 == 0x5B:  # '['
            return self._read_csi()
        if 0x41 <= c2 <= 0x44:  # ESC A-D (SS3 arrows, some terms)
            return ('key', {0x41: KEY_UP, 0x42: KEY_DOWN, 0x43: KEY_RIGHT, 0x44: KEY_LEFT}[c2])
        if c2 == 0x4F:  # 'O'
            return self._read_ss3()
        ch = chr(c2)
        if ch in ('a', 'b', 'c', 'd'):
            return ('key', KEY_ESCAPE)
        return ('key', KEY_ESCAPE)

    def _read_csi(self):
        seq = []
        while len(seq) < 32:
            b = self._read_byte(0.02)
            if b is None:
                break
            seq.append(b)
            if 0x40 <= b <= 0x7E:
                break
        if not seq:
            return ('key', KEY_ESCAPE)
        final = chr(seq[-1])
        params = ''.join(chr(b) for b in seq[:-1])

        if params.startswith('<'):  # SGR extended mouse
            parts = params[1:].split(';')
            if len(parts) >= 3:
                try:
                    cb = int(parts[0])
                    x = int(parts[1]) - 1
                    y = int(parts[2]) - 1
                except ValueError:
                    return ('key', KEY_ESCAPE)
                return self._sgr_mouse(cb, x, y, final)
            return ('key', KEY_ESCAPE)

        if final == 'M':  # X10 mouse: ESC [ M cb x y  (3 more bytes)
            cb = self._read_byte(0.02)
            xb = self._read_byte(0.02)
            yb = self._read_byte(0.02)
            if None not in (cb, xb, yb):
                return self._x10_mouse(cb - 32, xb - 33, yb - 33)
            return ('key', KEY_ESCAPE)

        if final == 't' and params.startswith('8;'):
            try:
                rows, cols = params[2:].split(';')
                return ResizeEvent(int(cols), int(rows))
            except ValueError:
                return ('key', KEY_ESCAPE)

        p = params.replace(';', '')
        if final == 'A': return ('key', KEY_UP)
        if final == 'B': return ('key', KEY_DOWN)
        if final == 'C': return ('key', KEY_RIGHT)
        if final == 'D': return ('key', KEY_LEFT)
        if final == 'H': return ('key', KEY_HOME)
        if final == 'F': return ('key', KEY_END)
        if final == 'Z': return ('key', KEY_SHIFT_TAB)
        if final == '~':
            n = p
            if n == '1' or n == '7': return ('key', KEY_HOME)
            if n == '2': return ('key', KEY_INSERT)
            if n == '3': return ('key', KEY_DELETE)
            if n == '4' or n == '8': return ('key', KEY_END)
            if n == '5': return ('key', KEY_PAGE_UP)
            if n == '6': return ('key', KEY_PAGE_DOWN)
            if n in ('11', '12', '13', '14', '15', '17',
                     '18', '19', '20', '21', '23', '24'):
                return ('key', _F1_TO_F12[('11', '12', '13', '14', '15', '17',
                                           '18', '19', '20', '21', '23', '24').index(n)])
        return ('key', KEY_ESCAPE)

    def _read_ss3(self):
        b = self._read_byte(0.02)
        if b is None:
            return ('key', KEY_ESCAPE)
        if b == 0x41: return ('key', KEY_UP)
        if b == 0x42: return ('key', KEY_DOWN)
        if b == 0x43: return ('key', KEY_RIGHT)
        if b == 0x44: return ('key', KEY_LEFT)
        if b == 0x50: return ('key', 'F1')
        if b == 0x51: return ('key', 'F2')
        if b == 0x52: return ('key', 'F3')
        if b == 0x53: return ('key', 'F4')
        return ('key', KEY_ESCAPE)

    def _sgr_mouse(self, cb: int, x: int, y: int, final: str) -> MouseEvent:
        mods = dict(shift=bool(cb & 0x04), alt=bool(cb & 0x08), ctrl=bool(cb & 0x10))
        if cb & 0x40:
            # Scroll-wheel codes 64-67 set bit 6; bits 0-1 are the direction
            # (0 up, 1 down, 2 right, 3 left), bits 2-4 the modifiers.
            w = cb & 0x03
            return MouseEvent(x, y, action='scroll',
                              scroll_dy=1 if w == 1 else (-1 if w == 0 else 0),
                              scroll_dx=1 if w == 2 else (-1 if w == 3 else 0),
                              **mods)
        button = cb & 0x03
        if final == 'm':
            action = 'release'
        elif cb & 0x20 or button == 3:
            # bit 32 marks motion (drag with a button held, or a bare move)
            action = 'move'
            if button == 3:
                button = 0
        else:
            action = 'press'
        return MouseEvent(x, y, button=button, action=action, **mods)

    def _x10_mouse(self, cb: int, x: int, y: int) -> MouseEvent:
        if cb & 0x40:
            # X10 wheel codes (64-67). Note: X10 lacks a separate release
            # byte, so a left-button release (also 64) can alias to wheel-up
            # here; SGR mode (1006h) is preferred and avoids this entirely.
            w = cb & 0x03
            return MouseEvent(x, y, action='scroll',
                              scroll_dy=1 if w == 1 else (-1 if w == 0 else 0),
                              scroll_dx=1 if w == 2 else (-1 if w == 3 else 0),
                              shift=bool(cb & 0x04))
        if cb & 0x20:
            return MouseEvent(x, y, button=cb & 0x03, action='move', shift=bool(cb & 0x04))
        return MouseEvent(x, y, button=cb & 0x03, action='press', shift=bool(cb & 0x04))

    def _decode_utf8(self, first: int) -> str:
        if first < 0x80:
            return chr(first)
        n = 1 if first >> 5 == 0b110 else (2 if first >> 4 == 0b1110 else (3 if first >> 3 == 0b11110 else 0))
        tail = [self._read_byte(0.0) for _ in range(n)]
        expected = [b for b in tail if b is not None]
        if len(expected) != len(tail):
            return chr(first)
        data = bytes([first] + expected)
        return data.decode('utf-8', 'replace')

    def _read_sequence(self, timeout: Optional[float]):
        b = self._read_byte(timeout)
        if b is None:
            return None
        if b == 0x1B:
            return self._read_escape()
        if b in (0x0D, 0x0A):
            return ('key', KEY_ENTER)
        if b == 0x09:
            return ('key', KEY_TAB)
        if b == 0x7F or b == 0x08:
            return ('key', KEY_BACKSPACE)
        if b == 0x20:
            return ('key', KEY_SPACE)
        if b == 0x03:
            return ('key', KEY_CTRL_C)
        if b == 0x04:
            return ('key', KEY_CTRL_D)
        if b == 0x1A:
            return ('key', KEY_CTRL_Z)
        if b < 0x20:
            return ('key', chr(b))
        try:
            return ('key', self._decode_utf8(b))
        except Exception:
            return ('key', chr(b))

    def _drain(self, timeout: Optional[float] = 0.0):
        tokens = []
        while True:
            tok = self._read_sequence(0.0)
            if tok is None:
                break
            tokens.append(tok)
        if tokens or not (timeout is None or timeout > 0):
            return tokens
        tok = self._read_sequence(timeout)
        if tok is not None:
            tokens.append(tok)
            while True:
                t2 = self._read_sequence(0.0)
                if t2 is None:
                    break
                tokens.append(t2)
        return tokens

    # -- public event API ------------------------------------------------

    def events(self, timeout: Optional[float] = 0.0) -> list[InputEvent]:
        """Read all pending input as a list of KeyEvent / MouseEvent /
        ResizeEvent. Blocks up to ``timeout`` seconds (None = forever) for
        the first event, then drains anything else available.

        Releases are synthesized: any key we last saw more than
        ``release_delay`` seconds ago emits ``KeyEvent(down=False)``. A repeat
        that arrives while a key is *recently* released (within
        ``repeat_grace``) is treated as a hold continuation, so slow keyboard
        repeat rates never turn a held key into press/release flicker.
        """
        out: list[InputEvent] = []
        for tok in self._drain(timeout):
            if isinstance(tok, (MouseEvent, ResizeEvent)):
                out.append(tok)
            elif isinstance(tok, tuple) and tok[0] == 'key':
                name = tok[1]
                now = self._clock()
                if name in self._held:
                    self._held[name] = now
                    out.append(KeyEvent(name, down=True, repeat=True))
                elif name in self._released_at and now - self._released_at[name] <= self._repeat_grace:
                    del self._released_at[name]
                    self._held[name] = now
                    out.append(KeyEvent(name, down=True, repeat=True))
                else:
                    self._released_at.pop(name, None)
                    self._held[name] = now
                    out.append(KeyEvent(name, down=True, repeat=False))
        now = self._clock()
        for key in [k for k in list(self._held) if now - self._held[k] > self._release_delay]:
            del self._held[key]
            self._released_at[key] = now
            out.append(KeyEvent(key, down=False, repeat=False))
        for key in [k for k in list(self._released_at)
                    if now - self._released_at[k] > self._release_delay + self._repeat_grace]:
            del self._released_at[key]
        self._maybe_resize(now, out)
        return out

    def _maybe_resize(self, now: float, out: list):
        if now - self._size_check < 0.25:
            return
        self._size_check = now
        sz = self._terminal_size()
        if sz is None:
            return
        size = (sz.columns, sz.lines)
        if self._last_size is not None and size != self._last_size:
            out.append(ResizeEvent(*size))
        self._last_size = size

    def poll(self, timeout: Optional[float] = 0.0) -> str | None:
        """Read the next key *press* (or terminal repeat) name, blocking up
        to ``timeout`` seconds; None if nothing arrived. Synthesized releases
        and mouse/resize events are consumed internally, not returned -
        call :meth:`events` for the full stream."""
        for ev in self.events(timeout):
            if isinstance(ev, KeyEvent) and ev.down:
                return ev.key
        return None

    def get(self, timeout: Optional[float] = None) -> str | None:
        """Block until a key press is available and return its name."""
        return self.poll(timeout)


def open_input(fd: int = 0) -> Input:
    return Input(fd)


class KeyState:
    """Tracks held keys between frames. Feed it events from ``Input``::

        ks = KeyState()
        ks.update(inp.events(0))
        if ks.down('left'):  move_left()
        if 'space' in ks and ks.just_pressed('space'):  jump()

    ``update()`` records presses (non-repeat only) and synthesized releases,
    and resets the *just-pressed / just-released* edge flags so they reflect
    only the current frame.
    """

    def __init__(self):
        self._keys: set[str] = set()
        self._pressed: set[str] = set()
        self._released: set[str] = set()

    def update(self, events):
        self._pressed.clear()
        self._released.clear()
        for ev in events:
            if isinstance(ev, KeyEvent):
                if ev.down:
                    if not ev.repeat:
                        self._pressed.add(ev.key)
                    self._keys.add(ev.key)
                else:
                    self._released.add(ev.key)
                    self._keys.discard(ev.key)
        return self

    def press(self, key: str | None):
        if key:
            self._pressed.add(key)
            self._keys.add(key)

    def release(self, key: str | None):
        if key:
            self._released.add(key)
            self._keys.discard(key)

    def down(self, key: str) -> bool:
        return key in self._keys

    def just_pressed(self, key: str) -> bool:
        return key in self._pressed

    def just_released(self, key: str) -> bool:
        return key in self._released

    def held(self) -> list[str]:
        return sorted(self._keys)

    def clear(self):
        self._keys.clear()
        self._pressed.clear()
        self._released.clear()

    def __contains__(self, key: str) -> bool:
        return key in self._keys