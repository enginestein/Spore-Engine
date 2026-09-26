"""Second-layer input tests: raw-mode ownership, byte-level escape decoding,
UTF-8, release synthesis, resize polling and KeyState edge flags.

``tests/test_input.py`` covers the common key and mouse paths; this file
concentrates on the paths that only run with a real fd, an awkward escape
sequence, or a nested raw-mode scope.
"""

from __future__ import annotations

import os
import pty
import termios

import pytest

from spore_engine import Input, KeyEvent, KeyState, MouseEvent, ResizeEvent
from spore_engine.core.input import HAVE_TERMIOS, _HAVE_TERMIOS


class FakeClock:
    def __init__(self, t=1000.0):
        self.t = t

    def __call__(self):
        return self.t

    def advance(self, dt):
        self.t += dt


def make_input(clock=None, **kw):
    """An Input whose reads come from an in-memory list of byte values."""
    r, w = os.pipe()
    os.close(w)
    inp = Input(r, clock=clock, **kw)
    buf = []

    def feed(data):
        if isinstance(data, str):
            data = data.encode()
        buf.extend(data)

    inp._buf = buf
    inp._read_byte = lambda timeout: buf.pop(0) if buf else None
    inp.feed = feed
    os.close(r)
    return inp


def keys(inp, *seqs, timeout=0.0):
    return inp.events(timeout)


# -------------------------------------------------------------------
# raw mode ownership
# -------------------------------------------------------------------

@pytest.mark.skipif(not _HAVE_TERMIOS, reason='needs termios')
def test_raw_mode_is_reference_counted():
    master, slave = pty.openpty()
    try:
        before = termios.tcgetattr(slave)
        inp = Input(fd=slave)
        assert inp.raw_enabled is False
        inp.enter_raw()
        assert inp.raw_enabled is True
        assert termios.tcgetattr(slave) != before, 'raw mode was not applied'
        inp.exit_raw()
        assert inp.raw_enabled is False
        assert termios.tcgetattr(slave) == before
    finally:
        os.close(master)
        os.close(slave)


@pytest.mark.skipif(not _HAVE_TERMIOS, reason='needs termios')
def test_nested_raw_scopes_restore_the_original_attributes():
    """The inner enter_raw used to re-snapshot the *raw* attributes, so the
    matching exit_raw restored raw mode and left the shell unusable."""
    master, slave = pty.openpty()
    try:
        before = termios.tcgetattr(slave)
        inp = Input(fd=slave)
        with inp.raw():
            raw_attrs = termios.tcgetattr(slave)
            with inp.raw():
                assert inp.raw_enabled is True
            assert inp.raw_enabled is True, 'the inner scope left raw mode early'
            assert termios.tcgetattr(slave) == raw_attrs
        assert termios.tcgetattr(slave) == before, \
            'the terminal was left in raw mode after balanced nesting'
    finally:
        os.close(master)
        os.close(slave)


@pytest.mark.skipif(not _HAVE_TERMIOS, reason='needs termios')
def test_three_deep_nesting_round_trips():
    master, slave = pty.openpty()
    try:
        before = termios.tcgetattr(slave)
        inp = Input(fd=slave)
        inp.enter_raw()
        inp.enter_raw()
        inp.enter_raw()
        assert inp.raw_enabled is True
        inp.exit_raw()
        inp.exit_raw()
        assert inp.raw_enabled is True
        assert termios.tcgetattr(slave) != before
        inp.exit_raw()
        assert termios.tcgetattr(slave) == before
    finally:
        os.close(master)
        os.close(slave)


@pytest.mark.skipif(not _HAVE_TERMIOS, reason='needs termios')
def test_extra_exit_raw_is_a_no_op():
    master, slave = pty.openpty()
    try:
        before = termios.tcgetattr(slave)
        inp = Input(fd=slave)
        inp.exit_raw()          # never entered
        inp.enter_raw()
        inp.exit_raw()
        inp.exit_raw()          # one too many
        assert inp.raw_enabled is False
        assert termios.tcgetattr(slave) == before
    finally:
        os.close(master)
        os.close(slave)


@pytest.mark.skipif(not _HAVE_TERMIOS, reason='needs termios')
def test_raw_context_manager_restores_on_an_exception():
    master, slave = pty.openpty()
    try:
        before = termios.tcgetattr(slave)
        inp = Input(fd=slave)
        with pytest.raises(ZeroDivisionError):
            with inp.raw():
                raise ZeroDivisionError
        assert termios.tcgetattr(slave) == before
        assert inp.raw_enabled is False
    finally:
        os.close(master)
        os.close(slave)


def test_raw_mode_on_a_pipe_raises_a_clear_error():
    r, w = os.pipe()
    try:
        inp = Input(fd=r)
        with pytest.raises(RuntimeError) as ei:
            inp.enter_raw()
        assert 'not a terminal' in str(ei.value)
        assert inp.raw_enabled is False
    finally:
        os.close(r)
        os.close(w)


def test_have_termios_is_a_bool():
    assert isinstance(HAVE_TERMIOS, bool)
    assert isinstance(_HAVE_TERMIOS, bool)


def test_isatty_is_false_for_a_pipe_and_never_raises():
    r, w = os.pipe()
    try:
        assert Input(fd=r).isatty is False
        assert Input(fd=9999).isatty is False
    finally:
        os.close(r)
        os.close(w)


@pytest.mark.skipif(not _HAVE_TERMIOS, reason='needs termios')
def test_mouse_is_enabled_and_disabled_with_the_raw_scope():
    master, slave = pty.openpty()
    try:
        inp = Input(fd=slave, mouse=True)
        assert inp.mouse_enabled is False
        with inp.raw():
            assert inp.mouse_enabled is True
        assert inp.mouse_enabled is False
    finally:
        os.close(master)
        os.close(slave)


# -------------------------------------------------------------------
# available() / _terminal_size() on odd fds
# -------------------------------------------------------------------

def test_available_on_a_pipe():
    r, w = os.pipe()
    try:
        inp = Input(fd=r)
        assert inp.available() is False
        os.write(w, b'x')
        assert inp.available() is True
    finally:
        os.close(r)
        os.close(w)


def test_available_on_a_closed_fd_is_false():
    r, w = os.pipe()
    os.close(r)
    os.close(w)
    assert Input(fd=r).available() is False


def test_terminal_size_of_a_pipe_is_none():
    r, w = os.pipe()
    try:
        assert Input(fd=r)._terminal_size() is None
    finally:
        os.close(r)
        os.close(w)


@pytest.mark.skipif(not _HAVE_TERMIOS, reason='needs termios')
def test_terminal_size_of_a_pty():
    master, slave = pty.openpty()
    try:
        assert Input(fd=slave)._terminal_size() is not None
    finally:
        os.close(master)
        os.close(slave)


def test_write_to_a_non_tty_is_ignored():
    r, w = os.pipe()
    try:
        Input(fd=r)._write('\x1b[?1000h')     # must not raise
    finally:
        os.close(r)
        os.close(w)


# -------------------------------------------------------------------
# escape decoding corner cases
# -------------------------------------------------------------------

def test_bare_escape_is_the_escape_key():
    inp = make_input()
    inp.feed('\x1b')
    assert [e.key for e in inp.events()] == ['escape']


def test_escape_followed_by_an_unknown_byte():
    inp = make_input()
    inp.feed('\x1bZ')
    assert [e.key for e in inp.events()] == ['escape']


def test_escape_followed_by_a_letter():
    """Alt+letter is not mapped; it must degrade to a lone Escape, not hang."""
    inp = make_input()
    inp.feed('\x1bx')
    evs = inp.events()
    assert [e.key for e in evs] == ['escape']


@pytest.mark.parametrize('final,key', [
    ('A', 'up'), ('B', 'down'), ('C', 'right'), ('D', 'left'),
    ('H', 'home'), ('F', 'end'), ('Z', 'shift-tab'),
])
def test_csi_letters(final, key):
    inp = make_input()
    inp.feed(f'\x1b[{final}')
    assert [e.key for e in inp.events()] == [key]


@pytest.mark.parametrize('code,key', [
    ('1', 'home'), ('7', 'home'), ('2', 'insert'), ('3', 'delete'),
    ('4', 'end'), ('8', 'end'), ('5', 'pageup'), ('6', 'pagedown'),
])
def test_csi_tilde_codes(code, key):
    inp = make_input()
    inp.feed(f'\x1b[{code}~')
    assert [e.key for e in inp.events()] == [key]


@pytest.mark.parametrize('code,key', [
    ('11', 'F1'), ('12', 'F2'), ('13', 'F3'), ('14', 'F4'),
    ('15', 'F5'), ('17', 'F6'), ('18', 'F7'), ('19', 'F8'),
    ('20', 'F9'), ('21', 'F10'), ('23', 'F11'), ('24', 'F12'),
])
def test_csi_function_keys(code, key):
    inp = make_input()
    inp.feed(f'\x1b[{code}~')
    assert [e.key for e in inp.events()] == [key]


def test_csi_with_a_modifier_still_maps_the_key():
    inp = make_input()
    inp.feed('\x1b[1;5~')            # ctrl+home
    assert [e.key for e in inp.events()] == ['home']


def test_csi_with_an_unrecognised_code_is_escape():
    inp = make_input()
    inp.feed('\x1b[99~')
    assert [e.key for e in inp.events()] == ['escape']


def test_csi_with_a_mouse_prefix_but_too_few_params():
    inp = make_input()
    inp.feed('\x1b[<35M')
    assert [e.key for e in inp.events()] == ['escape']


def test_csi_with_unparsable_mouse_params():
    """'a' is a final byte, so the sequence ends there and degrades to a
    lone Escape; the leftovers are then ordinary keys."""
    inp = make_input()
    inp.feed('\x1b[<ab;cd;efM')
    evs = inp.events()
    assert isinstance(evs[0], KeyEvent) and evs[0].key == 'escape'
    assert not [e for e in evs if isinstance(e, MouseEvent)]


def test_truncated_csi_is_escape():
    inp = make_input()
    inp.feed('\x1b[')               # no final byte arrives
    assert [e.key for e in inp.events()] == ['escape']


def test_csi_with_a_truncated_resize_report():
    inp = make_input()
    inp.feed('\x1b[8;abc;t')
    evs = inp.events()
    assert not [e for e in evs if isinstance(e, ResizeEvent)]


def test_x10_mouse_press():
    inp = make_input()
    inp.feed(b'\x1b[M\x20\x21\x21')
    evs = [e for e in inp.events() if isinstance(e, MouseEvent)]
    assert len(evs) == 1
    assert (evs[0].x, evs[0].y) == (0, 0)
    assert evs[0].action == 'press'


def test_x10_mouse_motion():
    inp = make_input()
    inp.feed(b'\x1b[M\x40\x21\x21')          # raw 0x40 -> cb 0x20 = motion
    evs = [e for e in inp.events() if isinstance(e, MouseEvent)]
    assert evs and evs[0].action == 'move'


def test_x10_mouse_wheel():
    inp = make_input()
    inp.feed(b'\x1b[M\x61\x21\x21')          # raw 0x61 -> cb 0x41 = wheel | down
    evs = [e for e in inp.events() if isinstance(e, MouseEvent)]
    assert evs and evs[0].action == 'scroll'
    assert evs[0].scroll_dy == 1


def test_truncated_x10_mouse_is_escape():
    inp = make_input()
    inp.feed(b'\x1b[M\x20')
    evs = inp.events()
    assert not [e for e in evs if isinstance(e, MouseEvent)]
    assert [e.key for e in evs if isinstance(e, KeyEvent)] == ['escape']


@pytest.mark.parametrize('byte,key', [
    ('P', 'F1'), ('Q', 'F2'), ('R', 'F3'), ('S', 'F4'),
])
def test_ss3_function_keys(byte, key):
    inp = make_input()
    inp.feed(f'\x1bO{byte}')
    assert [e.key for e in inp.events()] == [key]


@pytest.mark.parametrize('byte,key', [
    ('A', 'up'), ('B', 'down'), ('C', 'right'), ('D', 'left'),
])
def test_ss3_arrows(byte, key):
    inp = make_input()
    inp.feed(f'\x1bO{byte}')
    assert [e.key for e in inp.events()] == [key]


def test_ss3_with_nothing_after_it():
    inp = make_input()
    inp.feed('\x1bO')
    assert [e.key for e in inp.events()] == ['escape']


def test_ss3_with_an_unknown_final_byte():
    inp = make_input()
    inp.feed('\x1bOX')
    assert [e.key for e in inp.events()] == ['escape']


@pytest.mark.parametrize('raw,key', [
    ('\r', 'enter'), ('\n', 'enter'), ('\t', 'tab'),
    ('\x7f', 'backspace'), ('\x08', 'backspace'), (' ', 'space'),
    ('\x03', 'ctrl-c'), ('\x04', 'ctrl-d'), ('\x1a', 'ctrl-z'),
])
def test_control_bytes(raw, key):
    inp = make_input()
    inp.feed(raw)
    assert [e.key for e in inp.events()] == [key]


def test_other_control_byte_passes_through():
    inp = make_input()
    inp.feed('\x01')
    assert [e.key for e in inp.events()] == ['\x01']


def test_plain_ascii():
    inp = make_input()
    inp.feed('a')
    assert [e.key for e in inp.events()] == ['a']


# -------------------------------------------------------------------
# UTF-8
# -------------------------------------------------------------------

@pytest.mark.parametrize('text', ['é', '£', '→', '☃', '𝄞', '😀'])
def test_utf8_round_trip(text):
    inp = make_input()
    inp.feed(text)
    assert [e.key for e in inp.events()] == [text]


def test_multibyte_text_arrives_as_one_event_per_character():
    inp = make_input()
    inp.feed('ñandú')
    assert [e.key for e in inp.events()] == list('ñandú')


def test_utf8_split_across_reads():
    """A multi-byte char arriving one byte at a time must still decode: the
    lead byte must not be emitted on its own."""
    inp = make_input()
    evs = []
    for b in '😀'.encode():
        inp.feed(bytes([b]))
        evs.extend(inp.events())
    assert [e.key for e in evs] == ['😀']


def test_truncated_utf8_waits_for_the_rest():
    """A lead byte with no continuation yet emits nothing and is remembered;
    the rest of the character decodes when it arrives."""
    inp = make_input()
    inp.feed('é'.encode()[:1])
    assert inp.events() == [], 'a partial character was reported as a key'
    inp.feed('é'.encode()[1:])
    assert [e.key for e in inp.events()] == ['é']


def test_lone_continuation_byte_is_a_replacement_char():
    inp = make_input()
    inp.feed(b'\x80')
    assert [e.key for e in inp.events()] == ['\ufffd']


def test_invalid_utf8_does_not_raise():
    inp = make_input()
    inp.feed(b'\xff\xfe')
    assert len(inp.events()) == 2


def test_a_partial_character_does_not_swallow_the_next_key():
    inp = make_input()
    inp.feed(b'\xf0')                # lead byte, continuation never arrives
    assert inp.events() == []
    inp.feed(b'a')
    keys = [e.key for e in inp.events()]
    assert 'a' in keys, f'the parked lead byte ate a real key: {keys}'


# -------------------------------------------------------------------
# the event model
# -------------------------------------------------------------------

def test_a_paste_becomes_many_events():
    inp = make_input()
    inp.feed('hello')
    assert [e.key for e in inp.events()] == list('hello')


def test_poll_returns_every_queued_key():
    """events() drains the whole read, so poll() used to keep one key and
    throw the rest of the burst away."""
    inp = make_input()
    inp.feed('abcdef')
    assert [inp.poll() for _ in range(6)] == list('abcdef')
    assert inp.poll() is None


def test_poll_spanning_two_reads():
    inp = make_input()
    inp.feed('ab')
    assert inp.poll() == 'a'
    inp.feed('cd')
    assert [inp.poll() for _ in range(3)] == ['b', 'c', 'd']


def test_poll_consumes_releases_without_returning_them():
    clock = FakeClock()
    inp = make_input(clock=clock, release_delay=0.2)
    inp.feed('a')
    assert inp.poll() == 'a'
    clock.advance(1.0)
    assert inp.poll() is None, 'a synthesized release leaked out of poll()'


def test_get_is_poll_with_a_default_timeout():
    inp = make_input()
    inp.feed('z')
    assert inp.get() == 'z'
    assert inp.get(0.0) is None


def test_repeat_is_flagged_while_held():
    clock = FakeClock()
    inp = make_input(clock=clock)
    inp.feed('a')
    first = inp.events()[0]
    assert (first.down, first.repeat) == (True, False)
    inp.feed('a')
    second = inp.events()[0]
    assert (second.down, second.repeat) == (True, True)


def test_release_is_synthesized_after_the_delay():
    clock = FakeClock()
    inp = make_input(clock=clock, release_delay=0.2)
    inp.feed('a')
    assert [e.down for e in inp.events()] == [True]
    clock.advance(0.1)
    assert inp.events() == [], 'released too early'
    clock.advance(0.2)
    evs = inp.events()
    assert [(e.key, e.down, e.repeat) for e in evs] == [('a', False, False)]


def test_a_repeat_inside_the_grace_window_is_not_a_new_press():
    clock = FakeClock()
    inp = make_input(clock=clock, release_delay=0.1, repeat_grace=0.5)
    inp.feed('a')
    inp.events()
    clock.advance(0.2)               # past release_delay: a release is emitted
    assert [e.down for e in inp.events()] == [False]
    inp.feed('a')                   # the keyboard's slow repeat kicks in
    evs = inp.events()
    assert [(e.down, e.repeat) for e in evs] == [(True, True)], \
        'a slow keyboard repeat was seen as a fresh press'


def test_a_press_after_the_grace_window_is_a_new_press():
    clock = FakeClock()
    inp = make_input(clock=clock, release_delay=0.1, repeat_grace=0.2)
    inp.feed('a')
    inp.events()
    clock.advance(1.0)
    assert [e.down for e in inp.events()] == [False]   # the release, at t=1.0
    clock.advance(1.0)                                 # now well past the grace
    inp.feed('a')
    evs = [e for e in inp.events() if e.down]
    assert [(e.down, e.repeat) for e in evs] == [(True, False)]


def test_held_keys_tracks_the_current_holds():
    clock = FakeClock()
    inp = make_input(clock=clock, release_delay=5.0)
    inp.feed('ab')
    inp.events()
    assert inp.held_keys == {'a', 'b'}
    clock.advance(10.0)
    inp.events()
    assert inp.held_keys == set()


def test_mixed_keys_and_mouse_in_one_read():
    inp = make_input()
    inp.feed('a\x1b[<0;5;5M')
    evs = inp.events()
    assert next(e for e in evs if isinstance(e, KeyEvent)).key == 'a'
    assert [e for e in evs if isinstance(e, MouseEvent)]


def test_resize_is_emitted_once_per_change():
    clock = FakeClock()
    inp = make_input(clock=clock)
    inp._terminal_size = lambda: os.terminal_size((80, 24))
    inp.events()
    assert not [e for e in inp.events() if isinstance(e, ResizeEvent)], \
        'a resize was reported without a change'
    clock.advance(1.0)
    inp._terminal_size = lambda: os.terminal_size((100, 30))
    resizes = [e for e in inp.events() if isinstance(e, ResizeEvent)]
    assert len(resizes) == 1
    assert (resizes[0].width, resizes[0].height) == (100, 30)


def test_resize_is_rate_limited_to_four_per_second():
    clock = FakeClock()
    inp = make_input(clock=clock)
    inp._terminal_size = lambda: os.terminal_size((80, 24))
    inp.events()
    clock.advance(0.1)
    inp._terminal_size = lambda: os.terminal_size((90, 24))
    assert not [e for e in inp.events() if isinstance(e, ResizeEvent)], \
        'the size was re-checked inside the 0.25s window'


def test_no_resize_when_the_size_is_unknown():
    clock = FakeClock()
    inp = make_input(clock=clock)
    inp._terminal_size = lambda: None
    inp.events()
    clock.advance(1.0)
    assert not [e for e in inp.events() if isinstance(e, ResizeEvent)]


def test_blocking_poll_returns_nothing_when_nothing_arrives():
    inp = make_input()
    assert inp.poll(0.0) is None


# -------------------------------------------------------------------
# KeyState
# -------------------------------------------------------------------

def test_keystate_press_and_release():
    ks = KeyState()
    ks.update([KeyEvent('a', down=True)])
    assert 'a' in ks
    assert ks.down('a') and ks.just_pressed('a')
    ks.update([KeyEvent('a', down=False)])
    assert 'a' not in ks
    assert ks.just_released('a')


def test_keystate_repeat_does_not_count_as_a_fresh_press():
    ks = KeyState()
    ks.update([KeyEvent('a', down=True)])
    ks.update([KeyEvent('a', down=True, repeat=True)])
    assert ks.just_pressed('a') is False, 'a repeat re-triggered just_pressed'
    assert ks.down('a')


def test_keystate_edges_last_exactly_one_update():
    ks = KeyState()
    ks.update([KeyEvent('a', down=True)])
    ks.update([])
    assert ks.just_pressed('a') is False
    assert ks.down('a'), 'the key stopped being held'


def test_keystate_direct_press_and_release():
    ks = KeyState()
    ks.press('x')
    assert ks.down('x') and ks.just_pressed('x')
    ks.release('x')
    assert not ks.down('x') and ks.just_released('x')


def test_keystate_ignores_none():
    ks = KeyState()
    ks.press(None)
    ks.release(None)
    assert ks.held() == []


def test_keystate_held_is_sorted():
    ks = KeyState()
    for k in ('c', 'a', 'b'):
        ks.press(k)
    assert ks.held() == ['a', 'b', 'c']


def test_keystate_clear():
    ks = KeyState()
    ks.press('a')
    ks.clear()
    assert ks.held() == [] and not ks.just_pressed('a')


def test_keystate_update_ignores_mouse_and_resize():
    ks = KeyState()
    ks.update([MouseEvent(1, 1), ResizeEvent(80, 24), KeyEvent('a', down=True)])
    assert ks.held() == ['a']


def test_keystate_update_returns_self_for_chaining():
    ks = KeyState()
    assert ks.update([]) is ks


def test_keystate_missing_key_is_false_not_an_error():
    ks = KeyState()
    assert ks.down('nope') is False
    assert ks.just_pressed('nope') is False
    assert ks.just_released('nope') is False
    assert 'nope' not in ks
