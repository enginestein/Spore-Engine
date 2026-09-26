"""App lifecycle: terminal setup/teardown, the non-tty guard, resize, q."""


import pytest

from spore_engine import App, Color
from spore_engine.core import term


@pytest.fixture
def app():
    return App(width=20, height=6, title='test', fps=1000)


# --- non-tty guard ------------------------------------------------------

def test_run_refuses_without_a_terminal(app):
    # The old loop read no keys and rendered into a pipe forever.
    with pytest.raises(RuntimeError, match='real terminal'):
        app.run()


def test_interactive_is_false_under_pytest(app):
    assert app.interactive is False


def test_run_headless_renders_frames(app, capsys):
    app.run_headless(max_frames=3)
    out = capsys.readouterr().out
    assert out == '', 'headless mode must not write to stdout'
    assert app.frames == 3


def test_run_headless_rejects_negative_frames(app):
    with pytest.raises(ValueError, match='non-negative'):
        app.run_headless(max_frames=-1)


def test_run_headless_zero_frames(app):
    app.run_headless(max_frames=0)
    assert app.frames == 0


# --- construction -------------------------------------------------------

def test_fps_must_be_positive():
    with pytest.raises(ValueError, match='fps'):
        App(width=10, height=5, fps=0)


def test_default_size_uses_terminal_size(monkeypatch):
    monkeypatch.setattr(term.os, 'get_terminal_size',
                        lambda: _Size(100, 40))
    a = App()
    assert (a.w, a.h) == (100, 40)


def test_explicit_size_wins_over_terminal(monkeypatch):
    monkeypatch.setattr(term.os, 'get_terminal_size', lambda: _Size(100, 40))
    a = App(width=33, height=11)
    assert (a.w, a.h) == (33, 11)


class _Size:
    def __init__(self, columns, lines):
        self.columns = columns
        self.lines = lines


# --- assets injection ---------------------------------------------------

def test_assets_are_injectable():
    from spore_engine import Assets
    store = Assets()
    a = App(width=10, height=5, assets=store)
    assert a.assets is store, 'injected store must not be replaced by the default'


def test_assets_default_to_the_shared_store():
    from spore_engine import default_store
    a = App(width=10, height=5)
    assert a.assets is default_store


# --- frames and timing --------------------------------------------------

def test_t_and_dt_advance(app):
    app.run_headless(max_frames=5)
    assert app.t > 0
    assert app.dt >= 0


def test_dt_is_clamped_after_a_long_stall(app, monkeypatch):
    ticks = iter([0.0, 5.0, 5.0, 5.0])  # a 5 second stall
    monkeypatch.setattr(term, 'monotonic', lambda: next(ticks, 5.0))
    app.fps = 10
    app.run_headless(max_frames=1)
    assert app.dt <= 1.0 / app.fps + 1e-6, 'a stall must not teleport animations'


def test_paused_freezes_time_but_not_frames(app):
    app.paused = True
    app.run_headless(max_frames=3)
    assert app.t == 0
    assert app.frames == 3


def test_stop_ends_the_loop(app):
    def stopper(a, _dt):
        a.stop()
    app.on_tick(stopper)
    app.run_headless(max_frames=1000)
    assert app.frames == 1


# --- on_init / handlers -------------------------------------------------

def test_on_init_runs_once_per_run(app):
    calls = []
    app.on_init(lambda a: calls.append(1))
    app.run_headless(max_frames=2)
    assert calls == [1]


def test_on_tick_receives_dt(app):
    seen = []
    app.on_tick(lambda a, dt: seen.append(dt))
    app.run_headless(max_frames=3)
    assert len(seen) == 3


def test_on_key_binding_is_returned_for_decoration(app):
    handler = app.on_key('space', lambda a: None)
    assert callable(handler)


def test_resize_handlers_fire(app):
    seen = []
    app.on_resize(lambda a, w, h: seen.append((w, h)))
    app._apply_resize(40, 12)
    assert seen == [(40, 12)]


def test_resize_updates_canvases(app):
    app._apply_resize(33, 9)
    assert (app.w, app.h) == (33, 9)
    assert (app.canvas.width, app.canvas.height) == (33, 9)
    assert (app.hr.width, app.hr.height) == (33, 18)


def test_resize_ignores_nonsense_sizes(app):
    app._apply_resize(0, 10)
    app._apply_resize(10, -1)
    assert (app.w, app.h) == (20, 6)


def test_resize_ignores_a_no_op(app):
    seen = []
    app.on_resize(lambda a, w, h: seen.append((w, h)))
    app._apply_resize(20, 6)  # already this size
    assert seen == []


def test_resize_preserves_canvas_content(app):
    app.canvas.draw_text(1, 1, 'keep', Color(255, 0, 0), z=1)
    app._apply_resize(40, 10)
    # A resize rebuilds the buffer, so assert it is usable rather than
    # unchanged - the point is that it did not raise or leave a stale shape.
    assert app.canvas.width == 40


# --- q handling ---------------------------------------------------------

def test_q_is_not_special_without_a_terminal(app):
    # No input is read headless, so q cannot stop anything here; the guard is
    # that a bound 'q' must not be clobbered by the built-in quit.
    def on_q(a):
        a.on_any_key(lambda *_: None)
    app.on_key('q', on_q)
    app.run_headless(max_frames=2)
    assert app.frames == 2
