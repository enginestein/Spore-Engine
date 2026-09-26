"""Terminal capability detection, lifecycle and the single render clock."""

import io
import sys

import pytest

from spore_engine.core import term
from spore_engine.core.term import (CHAR_ASPECT, DEFAULT_TERM_SIZE, RawMode,
                                    TerminalSession, detect_color_depth,
                                    disable_mouse, enable_mouse, hide_cursor,
                                    is_tty, monotonic, show_cursor,
                                    supports_altscreen, terminal_size,
                                    write_stdout)


class FakeTTY(io.StringIO):
    """A StringIO that claims to be a terminal."""

    def isatty(self):
        return True


class FakePipe(io.StringIO):
    def isatty(self):
        return False


# --- clock -------------------------------------------------------------

def test_monotonic_is_monotonic_clock():
    a = monotonic()
    b = monotonic()
    assert isinstance(a, float)
    # A monotonic clock never goes backwards.
    assert b >= a


def test_monotonic_survives_wallclock_change(monkeypatch):
    import time as _time
    fake = {'now': 1000.0}
    monkeypatch.setattr(_time, 'monotonic', lambda: fake['now'])
    first = monotonic()
    fake['now'] = 900.0  # an NTP step or a manual clock change
    second = monotonic()
    assert second < first, 'monotonic() must track the monotonic clock only'


# --- colour depth ------------------------------------------------------

@pytest.mark.parametrize('env,expected', [
    ({'NO_COLOR': '1', 'TERM': 'xterm-256color', 'COLORTERM': 'truecolor'}, 0),
    ({'TERM': 'dumb'}, 0),
    ({'COLORTERM': 'truecolor'}, 3),
    ({'COLORTERM': '24bit'}, 3),
    ({'TERM': 'xterm-kitty'}, 3),
    ({'TERM': 'wezterm'}, 3),
    ({'TERM': 'alacritty'}, 3),
    ({'TERM': 'xterm-256color'}, 2),
])
def test_detect_color_depth_env(monkeypatch, env, expected):
    for key in ('NO_COLOR', 'TERM', 'COLORTERM'):
        monkeypatch.delenv(key, raising=False)
    for key, val in env.items():
        monkeypatch.setenv(key, val)
    assert detect_color_depth(FakeTTY()) == expected


def test_detect_color_depth_pipe_is_monochrome(monkeypatch):
    monkeypatch.delenv('NO_COLOR', raising=False)
    monkeypatch.setenv('COLORTERM', 'truecolor')
    # A pipe has no terminal to interpret escapes, so do not emit colour.
    assert detect_color_depth(FakePipe()) == 0


def test_detect_color_depth_empty_term_on_pipe(monkeypatch):
    for key in ('NO_COLOR', 'COLORTERM'):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv('TERM', '')
    assert detect_color_depth(FakePipe()) == 0


# --- tty / geometry ----------------------------------------------------

def test_is_tty_never_raises_on_broken_stream():
    class Broken:
        def isatty(self):
            raise OSError('gone')
    assert is_tty(Broken()) is False
    assert is_tty(None) == is_tty(sys.stdout)


def test_terminal_size_never_raises_and_honours_default(monkeypatch):
    import os as _os
    import shutil as _shutil
    monkeypatch.setattr(_os, 'get_terminal_size',
                        lambda: (_ for _ in ()).throw(OSError('no tty')))
    monkeypatch.setattr(_shutil, 'get_terminal_size',
                        lambda default=(80, 24): default)
    assert terminal_size() == DEFAULT_TERM_SIZE
    assert terminal_size((11, 7)) == (11, 7)


def test_terminal_size_rejects_nonsense_from_the_os(monkeypatch):
    import os as _os
    import shutil as _shutil
    monkeypatch.setattr(_os, 'get_terminal_size', lambda: (0, 0))
    monkeypatch.setattr(_shutil, 'get_terminal_size', lambda default=(80, 24): (0, 0))
    # A zero-sized report is not usable; fall through to the default.
    assert terminal_size() == DEFAULT_TERM_SIZE


def test_terminal_size_prefers_the_real_terminal(monkeypatch):
    import collections
    import os as _os
    import shutil as _shutil
    size = collections.namedtuple('terminal_size', 'columns lines')
    monkeypatch.setattr(_os, 'get_terminal_size', lambda: size(123, 45))
    monkeypatch.setattr(_shutil, 'get_terminal_size',
                        lambda default=(80, 24): (1, 1))
    assert terminal_size() == (123, 45)


def test_default_term_size_is_a_sane_pair():
    w, h = DEFAULT_TERM_SIZE
    assert w > 0 and h > 0


def test_char_aspect_in_range():
    # A terminal cell is taller than wide; the factor is used to undo that.
    assert 0 < CHAR_ASPECT < 1


# --- escape sequences --------------------------------------------------

def test_write_stdout_swallows_broken_pipe():
    class Broken:
        def write(self, _):
            raise BrokenPipeError('reader went away')
        def flush(self):
            pass
    write_stdout('x', Broken())  # must not raise


def test_cursor_helpers_noop_on_pipe(monkeypatch):
    out = FakePipe()
    hide_cursor(out)
    show_cursor(out)
    assert out.getvalue() == '', 'no escapes when not a terminal'


def test_cursor_helpers_write_on_tty():
    out = FakeTTY()
    hide_cursor(out)
    show_cursor(out)
    assert out.getvalue() == '\033[?25l\033[?25h'


def test_mouse_helpers_noop_on_pipe():
    out = FakePipe()
    enable_mouse(out)
    disable_mouse(out)
    assert out.getvalue() == ''


def test_mouse_helpers_write_on_tty():
    out = FakeTTY()
    enable_mouse(out)
    assert '1000h' in out.getvalue()
    out2 = FakeTTY()
    disable_mouse(out2)
    assert '1000l' in out2.getvalue()


def test_altscreen_refused_on_pipe(monkeypatch):
    monkeypatch.setenv('TERM', 'xterm-256color')
    assert supports_altscreen(FakePipe()) is False


def test_altscreen_refused_for_dumb_terminal(monkeypatch):
    monkeypatch.setenv('TERM', 'dumb')
    assert supports_altscreen(FakeTTY()) is False


def test_altscreen_entered_for_real_terminal(monkeypatch):
    monkeypatch.setenv('TERM', 'xterm-256color')
    out = FakeTTY()
    assert supports_altscreen(out) is True
    term.enter_altscreen(out)
    written = out.getvalue()
    assert '?1049h' in written  # alt screen on
    assert '?25l' in written    # cursor hidden
    assert '2J' in written      # cleared
    term.exit_altscreen(out)
    written = out.getvalue()
    assert '?25h' in written    # cursor back
    assert '?1049l' in written  # alt screen off


# --- raw mode ----------------------------------------------------------

def test_raw_mode_noop_without_terminal(monkeypatch):
    # On a pipe there is no tty to reconfigure; acquire must say so rather
    # than raise termios.error.
    assert RawMode.acquire(FakePipe()) is False


def test_raw_mode_context_manager_is_nestable_on_pipe():
    with RawMode() as outer:
        assert outer is False
        with RawMode() as inner:
            assert inner is False


def test_raw_mode_release_without_acquire_is_safe():
    RawMode.release()
    RawMode.release()


def test_raw_mode_refcounts(monkeypatch):
    calls = {'getattr': 0, 'setattr': 0}

    monkeypatch.setattr(term, 'posix_terminal_available', lambda *a, **k: True)
    monkeypatch.setattr(term, '_import_termios', _fake_termios(calls))
    # pytest replaces sys.stdin with an object that has no real fd, so give
    # the code under test something it can actually reconfigure.
    monkeypatch.setattr(sys, 'stdin', _FakeStdin())
    RawMode._depth = 0
    RawMode._saved = None
    RawMode._fd_owner = None

    assert RawMode.acquire() is True   # first: does the work
    assert calls['getattr'] == 1, 'one tcgetattr on the first acquire'
    assert calls['setattr'] == 1, 'one tcsetattr to enter raw mode'
    assert RawMode.acquire() is True   # second: just counts
    assert calls['getattr'] == 1, 'a nested acquire must not touch the terminal'
    assert calls['setattr'] == 1
    RawMode.release()                  # not the last: no restore
    assert calls['setattr'] == 1
    RawMode.release()                  # last: restores the saved state
    assert calls['setattr'] == 2
    assert RawMode._depth == 0
    RawMode._depth = 0


def test_raw_mode_survives_a_broken_fd(monkeypatch):
    class NoFd:
        def fileno(self):
            raise io.UnsupportedOperation('no fd')

    monkeypatch.setattr(term, 'posix_terminal_available', lambda *a, **k: True)
    monkeypatch.setattr(term, '_import_termios', _fake_termios({}))
    monkeypatch.setattr(sys, 'stdin', NoFd())
    RawMode._depth = 0
    # Best-effort: a terminal we cannot reconfigure is reported, not raised.
    assert RawMode.acquire() is False
    assert RawMode._depth == 0


class _FakeStdin:
    name = '<stdin>'

    def fileno(self):
        return 0


def _fake_termios(calls):
    """A stand-in with the real tcgetattr shape: a 7-element list of flags plus
    a control-character table, so ``new[tty.LFLAG] &= ...`` really works."""
    class FakeTermios:
        ECHO = 8
        ICANON = 2
        ISIG = 1
        VMIN = 6
        VTIME = 5
        TCSADRAIN = 1

        @staticmethod
        def tcgetattr(fd):
            calls['getattr'] = calls.get('getattr', 0) + 1
            return [0, 0, 0, 0, 0, 0, [0] * 32]

        @staticmethod
        def tcsetattr(fd, when, data):
            calls['setattr'] = calls.get('setattr', 0) + 1

    class FakeTty:
        LFLAG = 3
        CC = 6

    return lambda: (FakeTermios, FakeTty)


# --- session -----------------------------------------------------------

def test_terminal_session_is_noop_on_pipe():
    out = FakePipe()
    with TerminalSession(mouse=True, alt_screen=True, stream=out) as s:
        assert s.interactive is False
    assert out.getvalue() == '', 'a pipe must receive no escape codes'


def test_terminal_session_sets_up_and_restores(monkeypatch):
    monkeypatch.setenv('TERM', 'xterm-256color')
    out = FakeTTY()
    with TerminalSession(mouse=True, alt_screen=True, raw=False,
                         stream=out):
        mid = out.getvalue()
    after = out.getvalue()
    assert '?1049h' in mid, 'entered the alternate screen'
    assert '?1000h' in mid, 'enabled mouse reporting'
    assert '?1049l' in after, 'restored the main screen'
    assert '?25h' in after, 'restored the cursor'


def test_terminal_session_restores_on_exception(monkeypatch):
    monkeypatch.setenv('TERM', 'xterm-256color')
    out = FakeTTY()
    with pytest.raises(RuntimeError):
        with TerminalSession(mouse=True, alt_screen=True, raw=False, stream=out):
            raise RuntimeError('boom')
    assert '?1049l' in out.getvalue(), 'teardown ran despite the exception'


def test_terminal_session_cursor_opt_out(monkeypatch):
    monkeypatch.setenv('TERM', 'xterm-256color')
    out = FakeTTY()
    with TerminalSession(alt_screen=False, raw=False, cursor=True, stream=out):
        pass
    assert '?25l' not in out.getvalue(), 'cursor left visible when asked'


# --- resize signals ----------------------------------------------------

def test_resize_handler_install_and_remove():
    seen = []
    cb = seen.append
    term.install_resize_handler(cb)
    term.install_resize_handler(cb)  # idempotent
    assert term._resize_handlers.count(cb) == 1
    term.remove_resize_handler(cb)
    term.remove_resize_handler(cb)  # removing twice is safe
    assert cb not in term._resize_handlers


def test_resize_handler_swallows_callback_errors():
    calls = []

    def boom(_cols, _lines):
        raise RuntimeError('user callback failed')

    def ok(_cols, _lines):
        calls.append('ok')

    term.install_resize_handler(boom)
    term.install_resize_handler(ok)
    try:
        term._dispatch_resize()
    finally:
        term.remove_resize_handler(boom)
        term.remove_resize_handler(ok)
    # The failing handler did not prevent the later one from running.
    assert calls == ['ok']


def test_install_saves_the_previous_sigwinch_handler():
    """Removing our handler must give the signal back to whoever had it.

    install_resize_handler declared `global _signal_installed` but not
    `global _previous_sigwinch`, so the saved handler was assigned to a local
    and the module-level record stayed None. remove_resize_handler then had
    nothing to restore, and the process kept our dispatch lambda installed
    for good.
    """
    import signal

    if not hasattr(signal, 'SIGWINCH'):
        pytest.skip('no SIGWINCH on this platform')

    def preexisting(_signum, _frame):
        pass

    original = signal.getsignal(signal.SIGWINCH)
    signal.signal(signal.SIGWINCH, preexisting)
    try:
        cb = lambda c, l: None
        term.install_resize_handler(cb)
        assert signal.getsignal(signal.SIGWINCH) is not preexisting
        assert term._previous_sigwinch is preexisting

        term.remove_resize_handler(cb)
        assert signal.getsignal(signal.SIGWINCH) is preexisting
        assert term._signal_installed is False
    finally:
        term.remove_resize_handler(cb)
        signal.signal(signal.SIGWINCH, original)


def test_removing_the_last_handler_uninstalls_the_signal():
    import signal

    if not hasattr(signal, 'SIGWINCH'):
        pytest.skip('no SIGWINCH on this platform')

    original = signal.getsignal(signal.SIGWINCH)
    try:
        a = lambda c, l: None
        b = lambda c, l: None
        term.install_resize_handler(a)
        term.install_resize_handler(b)
        term.remove_resize_handler(a)
        # Still ours: one handler left, so the signal stays hooked up.
        assert signal.getsignal(signal.SIGWINCH) is not original
        term.remove_resize_handler(b)
        assert signal.getsignal(signal.SIGWINCH) is original
    finally:
        for h in (a, b):
            term.remove_resize_handler(h)
        signal.signal(signal.SIGWINCH, original)


def test_terminal_session_restores_sigwinch(monkeypatch):
    import signal

    if not hasattr(signal, 'SIGWINCH'):
        pytest.skip('no SIGWINCH on this platform')

    original = signal.getsignal(signal.SIGWINCH)
    try:
        cb = lambda cols, lines: None
        with TerminalSession(raw=False, mouse=False, alt_screen=False,
                             cursor=True, on_resize=cb, stream=FakeTTY()):
            assert signal.getsignal(signal.SIGWINCH) is not original
        assert signal.getsignal(signal.SIGWINCH) is original
        assert cb not in term._resize_handlers
    finally:
        signal.signal(signal.SIGWINCH, original)
