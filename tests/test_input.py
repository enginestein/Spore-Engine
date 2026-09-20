"""Input escape-sequence decoding and the pull-based event model.

Run headless: feeds decoded bytes through a pipe with a fake clock so
release synthesis, repeat tracking, resize, and mouse/wheel all behave
deterministically without a real terminal.
"""

import os
import types

from spore_engine import Input, KeyEvent, MouseEvent, ResizeEvent, KeyState


def _make_input():
    r, w = os.pipe()
    inp = Input(r)
    inp._buf = []

    def feed(data):
        for b in data:
            inp._buf.append(b)

    inp._read_byte = lambda timeout: inp._buf.pop(0) if inp._buf else None
    return inp, feed


class FakeClock:
    def __init__(self, t=0.0):
        self.t = t

    def __call__(self):
        return self.t

    def advance(self, dt):
        self.t += dt


def _timed_input(release_delay=0.20, repeat_grace=0.45):
    r, w = os.pipe()
    clock = FakeClock()
    inp = Input(r, clock=clock, release_delay=release_delay,
                repeat_grace=repeat_grace)
    inp._buf = []
    inp._read_byte = lambda timeout: inp._buf.pop(0) if inp._buf else None
    return inp, clock


def test_arrows():
    inp, feed = _make_input()
    feed(b'\x1b[A')
    assert inp.poll() == 'up'
    feed(b'\x1b[B')
    assert inp.poll() == 'down'
    feed(b'\x1b[C')
    assert inp.poll() == 'right'
    feed(b'\x1b[D')
    assert inp.poll() == 'left'


def test_special_keys():
    inp, feed = _make_input()
    feed(b'\r')
    assert inp.poll() == 'enter'
    feed(b'\x1b')
    assert inp.poll() == 'escape'
    feed(b'\x1b[3~')
    assert inp.poll() == 'delete'
    feed(b'\x1b[Z')
    assert inp.poll() == 'shift-tab'
    feed(b'\x1b[H')
    assert inp.poll() == 'home'
    feed(b'\x1b[F')
    assert inp.poll() == 'end'
    feed(b'\x1b[5~')
    assert inp.poll() == 'pageup'
    feed(b'\x1b[6~')
    assert inp.poll() == 'pagedown'


def test_printable_and_ctrl():
    inp, feed = _make_input()
    feed(b'z')
    assert inp.poll() == 'z'
    feed(b' ')
    assert inp.poll() == 'space'
    feed(b'\x03')
    assert inp.poll() == 'ctrl-c'
    feed(b'\x7f')
    assert inp.poll() == 'backspace'


def test_multibyte_utf8():
    inp, feed = _make_input()
    feed('▓'.encode('utf-8'))
    assert inp.poll() == '▓'


def test_empty_poll():
    inp, feed = _make_input()
    assert inp.poll() is None


def test_key_state_hold():
    from spore_engine import KeyState
    ks = KeyState()
    ks.press('left')
    assert ks.down('left')
    ks.release('left')
    assert not ks.down('left')


# -- release synthesis / holds ----------------------------------------

def test_synthesized_release_without_terminal_repeat():
    """A key press is released after silence even if the terminal never
    repeats - holds do not depend on key auto-repeat."""
    inp, clock = _timed_input()
    inp._buf.extend(b'j')
    assert inp.events(0) == [KeyEvent('j', down=True)]
    clock.advance(0.25)
    assert inp.events(0) == [KeyEvent('j', down=False)]
    assert inp.events(0) == []


def test_hold_with_repeats_stays_down_until_silence():
    inp, clock = _timed_input()
    inp._buf.extend(b'a')
    assert inp.events(0) == [KeyEvent('a', down=True)]
    clock.advance(0.10)
    inp._buf.extend(b'a')
    assert inp.events(0) == [KeyEvent('a', down=True, repeat=True)]
    clock.advance(0.10)
    inp._buf.extend(b'a')
    assert inp.events(0) == [KeyEvent('a', down=True, repeat=True)]
    clock.advance(0.05)
    assert inp.events(0) == []
    clock.advance(0.20)
    assert inp.events(0) == [KeyEvent('a', down=False)]


def test_repeat_within_grace_continues_hold_not_new_press():
    inp, clock = _timed_input()
    inp._buf.extend(b'w')
    assert inp.events(0) == [KeyEvent('w', down=True)]
    clock.advance(0.25)          # past release_delay -> synthesized release
    assert inp.events(0) == [KeyEvent('w', down=False)]
    clock.advance(0.20)          # a repeat arrives within repeat_grace
    inp._buf.extend(b'w')
    ev = inp.events(0)
    assert ev == [KeyEvent('w', down=True, repeat=True)]


def test_keystate_edges():
    inp, clock = _timed_input()
    ks = KeyState()
    inp._buf.extend(b'z')
    ks.update(inp.events(0))
    assert ks.down('z') and ks.just_pressed('z') and not ks.just_released('z')
    clock.advance(0.10)
    inp._buf.extend(b'z')        # repeat -> held, not a fresh press
    ks.update(inp.events(0))
    assert ks.down('z') and not ks.just_pressed('z')
    clock.advance(0.25)
    ks.update(inp.events(0))     # synthesized release
    assert not ks.down('z') and ks.just_released('z')


def test_poll_consumes_release_events():
    inp, clock = _timed_input()
    inp._buf.extend(b'k')
    assert inp.poll() == 'k'
    clock.advance(0.25)
    assert inp.poll() is None    # synthesized release is consumed internally


# -- resize -----------------------------------------------------------

def test_csi_resize_event():
    inp, feed = _make_input()
    feed(b'\x1b[8;30;120t')
    assert inp.events(0) == [ResizeEvent(width=120, height=30)]


def test_polled_resize_event():
    inp, clock = _timed_input()
    sz = types.SimpleNamespace(columns=100, lines=40)
    inp._terminal_size = lambda: sz
    clock.advance(0.3)           # wait out the initial size-check guard
    assert inp.events(0) == []   # records baseline size, no event yet
    sz = types.SimpleNamespace(columns=80, lines=24)
    clock.advance(0.3)
    assert ResizeEvent(80, 24) in inp.events(0)


# -- mouse ------------------------------------------------------------

def test_sgr_mouse_wheel():
    inp, feed = _make_input()
    feed(b'\x1b[<65;5;10M')      # wheel down
    ev = inp.events(0)
    assert len(ev) == 1 and ev[0].action == 'scroll' and ev[0].scroll_dy == 1
    feed(b'\x1b[<64;5;10M')      # wheel up
    ev = inp.events(0)
    assert len(ev) == 1 and ev[0].action == 'scroll' and ev[0].scroll_dy == -1
    feed(b'\x1b[<66;5;10M')      # wheel right
    ev = inp.events(0)
    assert len(ev) == 1 and ev[0].action == 'scroll' and ev[0].scroll_dx == 1


def test_sgr_mouse_press_release_move():
    inp, feed = _make_input()
    feed(b'\x1b[<0;8;12M')
    assert inp.events(0) == [MouseEvent(x=7, y=11, button=0, action='press')]
    feed(b'\x1b[<0;8;12m')
    assert inp.events(0) == [MouseEvent(x=7, y=11, button=0, action='release')]
    feed(b'\x1b[<33;8;12M')      # motion with left button held
    ev = inp.events(0)
    assert len(ev) == 1 and ev[0].action == 'move' and ev[0].button == 1


def test_x10_mouse_scroll():
    inp, feed = _make_input()
    feed(b'\x1b[M`$+')           # X10 wheel-up
    ev = inp.events(0)
    assert len(ev) == 1 and ev[0].action == 'scroll' and ev[0].scroll_dy == -1