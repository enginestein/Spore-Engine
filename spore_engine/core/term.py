"""Terminal capability detection and lifecycle helpers.

Everything the engine needs to know about the terminal it is drawing to lives
here, so no other module has to re-derive it: colour depth, tty detection, the
default size when the real size is unavailable, the character-cell aspect ratio
used to keep images un-stretched, and the alternate-screen / cursor / raw-mode
escape sequences.

The single source of truth for the render clock is :func:`monotonic`.
"""

from __future__ import annotations

import os
import shutil
import sys
import time

__all__ = [
    'CHAR_ASPECT',
    'DEFAULT_TERM_SIZE',
    'HAVE_TERMIOS',
    'ColorDepth',
    'RawMode',
    'TerminalSession',
    'clear_screen',
    'detect_color_depth',
    'disable_mouse',
    'enable_mouse',
    'enter_altscreen',
    'exit_altscreen',
    'hide_cursor',
    'install_resize_handler',
    'is_tty',
    'monotonic',
    'posix_terminal_available',
    'remove_resize_handler',
    'show_cursor',
    'supports_altscreen',
    'terminal_size',
    'write_stdout',
]

# Fallback geometry used when the real terminal size cannot be queried. One
# definition: previously three different pairs were hardcoded across app.py,
# toolkit.py and demo.py.
DEFAULT_TERM_SIZE = (80, 24)

# A terminal cell is roughly twice as tall as it is wide. Image and video
# converters use this to convert a target width into a target height so output
# is not vertically stretched. Previously duplicated at six call sites.
CHAR_ASPECT = 0.45

# --- colour capability -------------------------------------------------

# 0 = no colour at all, 1 = 16 colour, 2 = 256 colour, 3 = truecolor
ColorDepth = int

_TRUECOLOR_TERMS = ('xterm-kitty', 'kitty', 'ghostty', 'wezterm', 'alacritty',
                    'foot', 'contour', 'rio', 'xterm-ghostty')


def monotonic() -> float:
    """The engine's clock. Always :func:`time.monotonic` so a wall-clock
    adjustment (NTP step, DST, manual set) cannot produce a negative or huge
    ``dt``. ``App``, ``TerminalApp`` and ``Input`` all use this."""
    return time.monotonic()


def _colorize_enabled() -> bool:
    # https://no-color.org - any non-empty value disables colour.
    return not os.environ.get('NO_COLOR')


def detect_color_depth(stream=None) -> ColorDepth:
    """Best-effort colour depth for ``stream`` (default ``sys.stdout``).

    Returns 0 whenever colour would be wasted or harmful: ``NO_COLOR`` is set,
    ``TERM`` is ``dumb``, or the stream is a pipe or a file. A pipe has nothing
    to interpret the escapes, and writing them into a redirected file just
    corrupts it - which is why the tty check comes first.

    An explicit ``COLORTERM`` of ``truecolor``/``24bit`` is honoured even when
    ``TERM`` is unset, because it is a deliberate opt-in by whoever launched
    the process (common under tmux, where ``TERM`` is ``screen`` or unset).
    Otherwise a ``TERM`` naming a truecolor terminal -> 3, ``256color`` -> 2,
    any other colour ``TERM`` -> 1, else a conservative 3.

    Callers should treat this as advisory: the renderer never emits fewer bytes
    than the terminal asked for unless the result is 0.
    """
    if not _colorize_enabled():
        return 0
    # Not a terminal: nobody is going to render these escapes, and for a
    # redirected file they are literal garbage in the output.
    if not is_tty(stream):
        return 0
    colorterm = (os.environ.get('COLORTERM') or '').lower()
    if colorterm in ('truecolor', '24bit'):
        return 3
    term = (os.environ.get('TERM') or '').lower()
    if term in ('dumb', 'unknown', ''):
        # An empty TERM is common in CI; assume nothing.
        return 0
    for name in _TRUECOLOR_TERMS:
        if name in term:
            return 3
    if '256color' in term:
        return 2
    if 'color' in term:
        return 1
    return 3


def supports_altscreen(stream=None) -> bool:
    """Whether the alternate screen buffer can be assumed to work.

    Conservative: a pipe, a dumb terminal or a disabled colour stream never
    gets the alternate screen, because there is nothing to restore and the
    escape codes would only pollute captured output."""
    if not is_tty(stream):
        return False
    term = (os.environ.get('TERM') or '').lower()
    return term not in ('dumb', 'unknown', '')


# --- geometry ----------------------------------------------------------

def is_tty(stream=None) -> bool:
    """Whether ``stream`` (default ``sys.stdout``) is a real terminal.

    Never raises: a closed or invalid stream is simply not a tty."""
    if stream is None:
        stream = sys.stdout
    try:
        return stream.isatty()
    except Exception:
        return False


def terminal_size(default: tuple | None = None) -> tuple:
    """Terminal size in cells as ``(columns, lines)``.

    Falls back to ``COLUMNS``/``LINES`` and then to ``default`` (default:
    :data:`DEFAULT_TERM_SIZE`), so this never raises."""
    if default is None:
        default = DEFAULT_TERM_SIZE
    try:
        sz = os.get_terminal_size()
        if sz.columns > 0 and sz.lines > 0:
            return (sz.columns, sz.lines)
    except (OSError, ValueError, AttributeError):
        pass
    try:
        env = shutil.get_terminal_size(default)
        if env.columns > 0 and env.lines > 0:
            return (env.columns, env.lines)
    except (OSError, ValueError, AttributeError):
        pass
    return default


# --- escape sequences --------------------------------------------------

_ALT_ON = '\033[?1049h'
_ALT_OFF = '\033[?1049l'
_HIDE_CURSOR = '\033[?25l'
_SHOW_CURSOR = '\033[?25h'
_CLEAR = '\033[2J'
_RESET = '\033[0m'
_MOUSE_ON = '\033[?1000h\033[?1002h\033[?1003h\033[?1006h\033[?1015h'
_MOUSE_OFF = '\033[?1000l\033[?1002l\033[?1003l\033[?1006l\033[?1015l'


def write_stdout(text: str, stream=None) -> None:
    """Write an escape sequence to ``stream`` and flush.

    Swallows only the errors that mean "there is no terminal left" (a closed
    or broken pipe); anything else propagates."""
    if stream is None:
        stream = sys.stdout
    try:
        stream.write(text)
        stream.flush()
    except (BrokenPipeError, ValueError, OSError):
        pass


def enter_altscreen(stream=None) -> bool:
    """Switch to the alternate screen buffer. Returns whether it was issued."""
    if not supports_altscreen(stream):
        return False
    write_stdout(_ALT_ON + _HIDE_CURSOR + _CLEAR, stream)
    return True


def exit_altscreen(stream=None) -> None:
    """Leave the alternate screen buffer and restore the cursor."""
    write_stdout(_SHOW_CURSOR + _RESET + _ALT_OFF, stream)


def hide_cursor(stream=None) -> None:
    """Hide the cursor. No-op when not writing to a terminal, so redirected
    output never picks up stray escape codes."""
    if is_tty(stream):
        write_stdout(_HIDE_CURSOR, stream)


def show_cursor(stream=None) -> None:
    """Show the cursor. No-op when not writing to a terminal."""
    if is_tty(stream):
        write_stdout(_SHOW_CURSOR, stream)


def clear_screen(stream=None) -> None:
    write_stdout(_CLEAR, stream)


def enable_mouse(stream=None) -> None:
    """Ask the terminal for button, drag and SGR-encoded motion reports."""
    if is_tty(stream):
        write_stdout(_MOUSE_ON, stream)


def disable_mouse(stream=None) -> None:
    if is_tty(stream):
        write_stdout(_MOUSE_OFF, stream)


# --- raw mode ownership ------------------------------------------------

def _import_termios():
    """Import ``termios``/``tty`` if this platform has them.

    Both live behind a hard platform boundary: on Windows the import raises
    ``ImportError``, and importing them at module scope in a library makes the
    whole package unimportable there. Every caller goes through this.
    """
    try:
        import termios
        import tty
    except ImportError:
        return None, None
    return termios, tty


#: Whether raw terminal mode can be driven on this platform. ``False`` on
#: Windows and anywhere else without :mod:`termios`.
HAVE_TERMIOS = _import_termios()[0] is not None


def posix_terminal_available(stream=None) -> bool:
    """Whether raw mode can actually be applied to ``stream`` right now.

    Requires both POSIX ``termios`` *and* a real terminal - raw mode on a pipe
    raises ``termios.error``."""
    if not HAVE_TERMIOS:
        return False
    if not is_tty(stream):
        return False
    try:
        import sys as _sys
        target = _sys.stdin if stream is None else stream
        _import_termios()[0].tcgetattr(target.fileno())
    except Exception:
        return False
    return True


class RawMode:
    """Reference-counted raw-mode ownership.

    Raw mode is *process-global* terminal state, so two libraries each saving
    and restoring ``tcgetattr`` independently will clobber each other: the first
    to exit restores the state it saw, which is the other's raw state, not the
    user's original settings.

    This counts enters and exits and only touches ``tcsetattr`` on the first
    enter and the last exit, so nesting is safe. Use it as a context manager::

        with RawMode():
            ...

    or manually with :meth:`acquire` / :meth:`release`.
    """

    _depth = 0
    _saved = None
    _fd_owner = None

    def __init__(self, stream=None):
        self._stream = stream

    @classmethod
    def acquire(cls, stream=None) -> bool:
        """Enter raw mode if possible. Returns whether this call did the work."""
        if not posix_terminal_available(stream):
            return False
        if cls._depth == 0:
            termios, tty = _import_termios()
            target = cls._resolve_stream(stream)
            try:
                fd = target.fileno()
                # One read, two uses: the saved copy is what we restore to, and
                # `new` is the copy we mutate. Reading twice could in principle
                # capture a change made in between.
                original = termios.tcgetattr(fd)
                new = list(original)
                new[tty.LFLAG] &= ~(termios.ECHO | termios.ICANON | termios.ISIG)
                new[tty.CC][termios.VMIN] = 0
                new[tty.CC][termios.VTIME] = 1
                termios.tcsetattr(fd, termios.TCSADRAIN, new)
                cls._saved = original
                cls._fd_owner = fd
            except Exception:
                cls._saved = None
                cls._fd_owner = None
                return False
        cls._depth += 1
        return True

    @classmethod
    def release(cls) -> None:
        """Leave raw mode once the last holder releases it."""
        if cls._depth == 0:
            return
        cls._depth -= 1
        if cls._depth == 0 and cls._saved is not None:
            termios, _ = _import_termios()
            try:
                termios.tcsetattr(cls._fd_owner, termios.TCSADRAIN, cls._saved)
            except Exception:
                pass
            cls._saved = None
            cls._fd_owner = None

    @staticmethod
    def _resolve_stream(stream):
        # Raw mode is a property of the *input* terminal, not the output one.
        if stream is None:
            return sys.stdin
        name = getattr(stream, 'name', '')
        return stream if 'stdin' in str(name) else sys.stdin

    def __enter__(self):
        self._acquired = self.acquire(self._stream)
        return self._acquired

    def __exit__(self, *exc):
        if getattr(self, '_acquired', False):
            self.release()
        return False


# --- SIGWINCH -----------------------------------------------------------

_resize_handlers: list = []
_signal_installed = False
_previous_sigwinch = None


def _dispatch_resize() -> None:
    """Call every registered handler with the current terminal size.

    A handler that raises must not kill the render loop, so each call is
    isolated."""
    cols, lines = terminal_size()
    for handler in list(_resize_handlers):
        try:
            handler(cols, lines)
        except Exception:
            pass


def install_resize_handler(callback) -> None:
    """Call ``callback(cols, lines)`` on SIGWINCH, if this platform has signals.

    Idempotent - installing the same function twice registers it once. Requires
    the main thread (Python raises from ``signal`` otherwise), and is a no-op
    where SIGWINCH does not exist.
    """
    if callback not in _resize_handlers:
        _resize_handlers.append(callback)
    # Both must be declared global: without _previous_sigwinch here, the
    # assignment below binds a local and the module-level saved handler stays
    # None, so remove_resize_handler has nothing to restore.
    global _signal_installed, _previous_sigwinch
    if _signal_installed:
        return
    try:
        import signal
        if not hasattr(signal, 'SIGWINCH'):
            return
        _previous_sigwinch = signal.getsignal(signal.SIGWINCH)
        signal.signal(signal.SIGWINCH, lambda s, f: _dispatch_resize())
        _signal_installed = True
    except (ImportError, ValueError, OSError, RuntimeError):
        # Not the main thread, or no SIGWINCH. Callers fall back to polling.
        _signal_installed = False


def remove_resize_handler(callback) -> None:
    """Unregister a handler installed by :func:`install_resize_handler`.

    When the last handler goes away the SIGWINCH hook is removed and the
    handler that was installed before us is put back, so wrapping a library
    function in a session does not permanently steal the signal from the
    rest of the process.
    """
    global _signal_installed, _previous_sigwinch
    try:
        _resize_handlers.remove(callback)
    except ValueError:
        return
    if _resize_handlers or not _signal_installed:
        return
    try:
        import signal
        if hasattr(signal, 'SIGWINCH'):
            if _previous_sigwinch is not None:
                signal.signal(signal.SIGWINCH, _previous_sigwinch)
            else:
                signal.signal(signal.SIGWINCH, signal.SIG_DFL)
    except (ImportError, ValueError, OSError, RuntimeError, TypeError):
        pass
    _signal_installed = False
    _previous_sigwinch = None


class TerminalSession:
    """Owns everything a full-screen app changes about the terminal.

    Sets up, in order: raw mode, the alternate screen, a hidden cursor, and
    optional mouse reporting. On exit it undoes each step in reverse and
    restores the previous SIGWINCH handler, so an app that crashes or is
    interrupted with Ctrl-C still leaves the user's shell usable.

    ::

        with TerminalSession(mouse=True):
            while running:
                render()

    Every step is best-effort: on a pipe, on Windows, or when the terminal
    refuses a sequence, the session still works and simply does less.
    """

    def __init__(self, mouse: bool = False, alt_screen: bool = True,
                 cursor: bool = False, raw: bool = True,
                 on_resize=None, stream=None):
        self.mouse = mouse
        self.alt_screen = alt_screen
        self.cursor = cursor
        self.raw = raw
        self.on_resize = on_resize
        self.stream = stream
        self._raw_active = False
        self._alt_active = False
        self._entered = False
        self._saved_winch = None

    @property
    def interactive(self) -> bool:
        """Whether the app is driving a real terminal and can read keys."""
        return posix_terminal_available()

    def __enter__(self) -> TerminalSession:
        self._entered = True
        if self.raw:
            self._raw_active = RawMode.acquire(self.stream)
        if self.alt_screen:
            self._alt_active = enter_altscreen(self.stream)
        if not self.cursor:
            hide_cursor(self.stream)
        if self.mouse:
            enable_mouse(self.stream)
        if self.on_resize is not None:
            install_resize_handler(self.on_resize)
            self._saved_winch = True
        return self

    def __exit__(self, *exc):
        if self.mouse:
            disable_mouse(self.stream)
        if not self.cursor:
            show_cursor(self.stream)
        if self._alt_active:
            exit_altscreen(self.stream)
        if self._raw_active:
            RawMode.release()
        if self.on_resize is not None:
            remove_resize_handler(self.on_resize)
        self._raw_active = False
        self._alt_active = False
        self._entered = False
        return False

