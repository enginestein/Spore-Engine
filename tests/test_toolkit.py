"""Tests for spore_engine.ui.toolkit: the event loop, Form and Dialog."""
from __future__ import annotations

import os
import sys

import pytest

import spore_engine.ui.toolkit as tk
from spore_engine import Canvas, Color
from spore_engine.ui.widgets import Button, Checkbox, Label, TextField


@pytest.fixture
def no_stdin(monkeypatch):
    """Point stdin at /dev/null so select() reports nothing readable.

    ``_read_key`` calls ``sys.stdin.fileno()``, and under pytest's capture
    ``sys.stdin`` is a pseudofile with none, so the module-level object has to
    be replaced as well as the file descriptor.
    """
    saved = os.dup(0)
    devnull = os.open(os.devnull, os.O_RDONLY)
    os.dup2(devnull, 0)
    handle = os.fdopen(devnull, 'rb')
    monkeypatch.setattr(sys, 'stdin', handle)
    try:
        yield
    finally:
        os.dup2(saved, 0)
        handle.close()
        os.close(saved)


@pytest.fixture
def feed_stdin(monkeypatch):
    """Feed bytes to stdin as if typed at a terminal."""
    saved = os.dup(0)
    r, w = os.pipe()
    os.dup2(r, 0)
    handle = os.fdopen(r, 'rb')
    monkeypatch.setattr(sys, 'stdin', handle)
    try:
        def _feed(data: bytes):
            os.write(w, data)
        yield _feed
    finally:
        os.close(w)
        os.dup2(saved, 0)
        handle.close()
        os.close(saved)


# -------------------------------------------------------------------
# key and mouse decoding
# -------------------------------------------------------------------

def test_read_key_returns_none_when_nothing_is_ready(no_stdin):
    assert tk._read_key(timeout=0) is None


@pytest.mark.parametrize('data,expected', [
    (b'a', 'a'),
    (b'Z', 'Z'),
    (b' ', ' '),
    (b'\x7f', 'backspace'),
    (b'\r', 'enter'),
    (b'\t', '\t'),
    (b'\x1b[A', 'up'),
    (b'\x1b[B', 'down'),
    (b'\x1b[C', 'right'),
    (b'\x1b[D', 'left'),
    (b'\x1b[Z', 'tab_back'),
    (b'\x1b[H', 'home'),
    (b'\x1b[F', 'end'),
    (b'\x1b[2~', 'insert'),
    (b'\x1b[3~', 'delete'),
    (b'\x1b[5~', 'page_up'),
    (b'\x1b[6~', 'page_down'),
    (b'\x1b', 'escape'),
])
def test_read_key_decodes_each_sequence(feed_stdin, data, expected):
    feed_stdin(data)
    assert tk._read_key(timeout=0.05) == expected


def test_read_key_falls_back_to_escape_for_unknown_sequences(feed_stdin):
    feed_stdin(b'\x1b[9;9~')
    assert tk._read_key(timeout=0.05) == 'escape'


@pytest.mark.parametrize('seq', [b'\x1b[<0;10;5M', b'\x1b[<0;10;5m'])
def test_a_mouse_click_is_not_reported_as_escape(feed_stdin, seq):
    """A click is escape-prefixed, so decoding it as 'escape' closed dialogs
    and quit the app on every press. It must return the 'mouse' sentinel."""
    feed_stdin(seq)
    assert tk._read_key(timeout=0.05) == 'mouse'


def test_is_sgr_mouse_rejects_ordinary_keys():
    assert not tk._is_sgr_mouse('\x1b[A')
    assert not tk._is_sgr_mouse('a')
    assert not tk._is_sgr_mouse('\x1b[')
    assert tk._is_sgr_mouse('\x1b[<0;1;1M')


def test_read_mouse_events_is_empty_when_nothing_is_ready(no_stdin):
    assert tk._read_mouse_events(timeout=0) == []


@pytest.mark.parametrize('data,expected', [
    (b'\x1b[<0;10;5M', [('mouse_down', 9, 4)]),
    (b'\x1b[<0;10;5m', [('mouse_up', 9, 4)]),
    (b'\x1b[<32;3;4M', [('mouse_move', 2, 3)]),
    (b'\x1b[<64;7;8M', [('mouse_up', 6, 7)]),
])
def test_read_mouse_events_decodes_sgr_reports(feed_stdin, data, expected):
    feed_stdin(data)
    assert tk._read_mouse_events(timeout=0.05) == expected


def test_read_mouse_events_parses_a_stretched_sequence(feed_stdin):
    feed_stdin(b'\x1b[<0;1;1M\x1b[<0;5;6M')
    assert tk._read_mouse_events(timeout=0.05) == [
        ('mouse_down', 0, 0), ('mouse_down', 4, 5)]


def test_read_mouse_events_ignores_malformed_reports(feed_stdin):
    feed_stdin(b'\x1b[<oops;1;1M')
    assert tk._read_mouse_events(timeout=0.05) == []


# -------------------------------------------------------------------
# TerminalApp lifecycle
# -------------------------------------------------------------------

def test_run_refuses_a_non_terminal_stdin(no_stdin):
    """Without a tty there is no way to read a key, so spin-looping is useless."""
    app = tk.TerminalApp(20, 6)
    with pytest.raises(RuntimeError, match='real terminal'):
        app.run(max_ticks=1)
    assert app.running is False


def test_set_theme_updates_only_the_given_keys():
    app = tk.TerminalApp(20, 6)
    before = dict(app._theme)
    app.set_theme(bg=Color(1, 2, 3))
    assert app._theme['bg'] == Color(1, 2, 3)
    assert app._theme['accent'] == before['accent']


def test_add_registers_and_returns_the_widget():
    app = tk.TerminalApp(20, 6)
    btn = app.add(Button(1, 1, 6, text='Go'))
    assert app.manager.widgets == [btn]


def test_on_tick_and_on_draw_are_stored():
    app = tk.TerminalApp(20, 6)
    tick = lambda dt: None
    draw = lambda c: None
    app.on_tick(tick)
    app.on_draw(draw)
    assert app._on_tick is tick
    assert app._draw_callback is draw


def test_render_paints_the_canvas_and_writes_escapes(monkeypatch):
    app = tk.TerminalApp(12, 4)
    written = []
    monkeypatch.setattr(tk, 'write_stdout', written.append)
    monkeypatch.setattr(app, '_get_term_size', lambda: (40, 20))
    app.render()
    # every cell got the theme background before anything drew on top
    assert app.canvas.buffer[0][0].bg == app._theme['bg']
    assert written, 'render produced no output'
    out = written[0]
    assert '\033[?25l' in out
    assert '\033[' in out


def test_render_centres_the_canvas(monkeypatch):
    app = tk.TerminalApp(10, 4)
    monkeypatch.setattr(tk, 'write_stdout', lambda s: None)
    monkeypatch.setattr(app, '_get_term_size', lambda: (40, 20))
    app.render()  # must not raise when the terminal is wider or taller


def test_render_clips_to_a_terminal_smaller_than_the_canvas(monkeypatch):
    app = tk.TerminalApp(30, 10)
    monkeypatch.setattr(tk, 'write_stdout', lambda s: None)
    monkeypatch.setattr(app, '_get_term_size', lambda: (10, 4))
    app.render()  # must not index past the canvas


def test_cleanup_writes_a_reset(monkeypatch):
    written = []
    monkeypatch.setattr(tk, 'write_stdout', written.append)
    app = tk.TerminalApp(20, 6)
    app._raw_mode = True
    app._cleanup()
    assert app._raw_mode is False
    assert '\033[0m' in written[0]


def test_stop_clears_running():
    app = tk.TerminalApp(20, 6)
    app.running = True
    app.stop()
    assert app.running is False


def test_handle_key_routes_plain_keys_to_the_manager():
    app = tk.TerminalApp(20, 6)
    seen = []
    app.manager.handle_event = lambda et, d: seen.append((et, d))
    app._handle_key('x')
    assert seen == [('key_down', 'x')]


def test_escape_stops_the_loop_when_no_dialog_is_open():
    app = tk.TerminalApp(20, 6)
    app.running = True
    app._handle_key('escape')
    assert app.running is False


def test_tab_and_shift_tab_move_focus():
    app = tk.TerminalApp(20, 6)
    a = app.add(Button(0, 0, 4, text='a'), focusable=True)
    b = app.add(Button(0, 2, 4, text='b'), focusable=True)
    app.manager.focus_first()
    assert app.manager.get_focused() is a
    app._handle_key('\t')
    assert app.manager.get_focused() is b
    app._handle_key('tab_back')
    assert app.manager.get_focused() is a


def test_loop_runs_ticks_and_renders(monkeypatch):
    app = tk.TerminalApp(12, 4)
    monkeypatch.setattr(tk, '_read_key', lambda timeout=0.01: None)
    monkeypatch.setattr(tk, '_read_mouse_events', lambda timeout=0.001: [])
    monkeypatch.setattr(tk, 'write_stdout', lambda s: None)
    monkeypatch.setattr(app, '_get_term_size', lambda: (40, 20))
    seen = []
    app.on_tick(seen.append)
    app.running = True
    app._tick_rate = 0.0
    app._max_ticks = 3
    app._loop()
    assert len(seen) == 3, 'the tick callback did not run once per tick'


def test_loop_forwards_mouse_coordinates_in_canvas_space(monkeypatch):
    app = tk.TerminalApp(10, 4)
    monkeypatch.setattr(tk, '_read_key', lambda timeout=0.01: None)
    monkeypatch.setattr(tk, 'write_stdout', lambda s: None)
    # A 40x20 terminal centres a 10x4 canvas at offset (15, 8).
    monkeypatch.setattr(app, '_get_term_size', lambda: (40, 20))
    events = []

    def fake_mouse(timeout=0.001):
        return events or [('mouse_down', 17, 9)]
    monkeypatch.setattr(tk, '_read_mouse_events', fake_mouse)
    app.manager.handle_event = lambda et, d: events.append((et, d))
    app.running = True
    app._tick_rate = 0.0
    app._max_ticks = 1
    app._loop()
    # (17, 9) minus the (15, 8) origin is (2, 1) in canvas space.
    assert ('mouse_down', (2, 1)) in events


def test_loop_ignores_the_mouse_key_sentinel(monkeypatch):
    app = tk.TerminalApp(12, 4)
    monkeypatch.setattr(tk, '_read_key', lambda timeout=0.01: 'mouse')
    monkeypatch.setattr(tk, '_read_mouse_events', lambda timeout=0.001: [])
    monkeypatch.setattr(tk, 'write_stdout', lambda s: None)
    monkeypatch.setattr(app, '_get_term_size', lambda: (40, 20))
    seen = []
    app.manager.handle_event = lambda et, d: seen.append((et, d))
    app.running = True
    app._tick_rate = 0.0
    app._max_ticks = 1
    app._loop()
    assert seen == [], 'a click must not be delivered as a key event'


def test_max_ticks_bounds_the_loop(monkeypatch):
    app = tk.TerminalApp(12, 4)
    monkeypatch.setattr(tk, '_read_key', lambda timeout=0.01: None)
    monkeypatch.setattr(tk, '_read_mouse_events', lambda timeout=0.001: [])
    monkeypatch.setattr(tk, 'write_stdout', lambda s: None)
    monkeypatch.setattr(app, '_get_term_size', lambda: (40, 20))
    app.running = True
    app._tick_rate = 0.0
    app._max_ticks = 3
    app._loop()
    assert app.running is True  # it exited on the tick budget, not on stop()


# -------------------------------------------------------------------
# dialog stacking
# -------------------------------------------------------------------

def test_push_dialog_registers_the_dialog_and_its_children():
    app = tk.TerminalApp(40, 12)
    dlg = tk.Dialog(2, 1, width=30, height=8, title='Confirm')
    dlg.add_button('OK', 'ok')
    dlg.add_content(Label(4, 3, 'really?'))
    app.push_dialog(dlg)

    assert app._dialog_stack == [dlg]
    assert dlg.visible is True
    assert dlg in app.manager.widgets
    assert all(b in app.manager.widgets for b in dlg._buttons)
    assert all(c in app.manager.widgets for c in dlg._content_widgets)
    assert app.manager.get_focused() in dlg._buttons


def test_dismissing_a_dialog_unregisters_it():
    """A dismissed dialog used to stay on the stack, so it kept swallowing
    keys and leaked its widgets on every open/close cycle."""
    app = tk.TerminalApp(40, 12)
    for _ in range(3):
        dlg = tk.Dialog(2, 1, width=30, height=8)
        dlg.add_button('OK', 'ok')
        dlg.add_content(Label(4, 3, 'hi'))
        app.push_dialog(dlg)
        before = len(app.manager.widgets)
        dlg.dismiss('ok')
        assert dlg.result == 'ok'
        assert dlg.visible is False
        assert app._dialog_stack == []
        assert len(app.manager.widgets) == before - 1 - len(dlg._buttons) - len(dlg._content_widgets)


def test_dismiss_calls_the_user_callback_with_the_result():
    seen = []
    dlg = tk.Dialog(0, 0, width=10, height=5, callback=seen.append)
    dlg.dismiss('yes')
    assert seen == ['yes']


def test_a_button_dismiss_returns_its_own_result():
    dlg = tk.Dialog(0, 0, width=20, height=6)
    btn = dlg.add_button('Yes', 'yes')
    btn.callback()
    assert dlg.result == 'yes'
    assert dlg.visible is False


def test_pop_dialog_removes_the_top_one():
    app = tk.TerminalApp(40, 12)
    first = tk.Dialog(0, 0, width=10, height=4)
    second = tk.Dialog(0, 6, width=10, height=4)
    app.push_dialog(first)
    app.push_dialog(second)
    app.pop_dialog()
    assert app._dialog_stack == [first]
    assert second not in app.manager.widgets
    app.pop_dialog()
    assert app._dialog_stack == []


def test_pop_dialog_on_an_empty_stack_is_a_no_op():
    app = tk.TerminalApp(40, 12)
    app.pop_dialog()
    assert app._dialog_stack == []


def test_escape_closes_the_top_dialog_and_stays_modal():
    app = tk.TerminalApp(40, 12)
    seen = []
    dlg = tk.Dialog(0, 0, width=20, height=6, callback=seen.append)
    dlg.add_button('OK', 'ok')
    app.push_dialog(dlg)

    app._handle_key('escape')
    assert dlg.result is None
    assert seen == [None]
    assert app._dialog_stack == []
    # The app itself is still running: escape closed the dialog, not the app.
    app.running = True
    app._handle_key('escape')
    assert app.running is False


def test_enter_activates_a_focused_dialog_button():
    app = tk.TerminalApp(40, 12)
    dlg = tk.Dialog(0, 0, width=20, height=6)
    dlg.add_button('Go', 'go')
    app.push_dialog(dlg)
    app.manager.focus_first()

    app._handle_key('enter')
    # the default callback dismisses the dialog with the button's result
    assert dlg.result == 'go'
    assert dlg.visible is False
    assert app._dialog_stack == []


def test_enter_calls_a_replaced_button_callback():
    app = tk.TerminalApp(40, 12)
    dlg = tk.Dialog(0, 0, width=20, height=6)
    dlg.add_button('Go', 'go')
    app.push_dialog(dlg)
    app.manager.focus_first()

    fired = []
    dlg._buttons[0].callback = lambda: fired.append(1)
    app._handle_key('enter')
    assert fired == [1]
    assert dlg.result is None, 'a replaced callback owns the dismissal'


def test_enter_with_no_focused_button_does_nothing():
    app = tk.TerminalApp(40, 12)
    dlg = tk.Dialog(0, 0, width=20, height=6)
    app.push_dialog(dlg)
    app.manager.get_focused = lambda: None
    app._handle_key('enter')  # must not raise
    assert dlg.result is None


def test_tab_cycles_within_a_dialog():
    app = tk.TerminalApp(40, 12)
    dlg = tk.Dialog(0, 0, width=30, height=6)
    first = dlg.add_button('A', 'a')
    second = dlg.add_button('B', 'b')
    app.push_dialog(dlg)
    app.manager.focus_first()
    assert app.manager.get_focused() is first
    app._handle_key('\t')
    assert app.manager.get_focused() is second
    app._handle_key('tab_back')
    assert app.manager.get_focused() is first


def test_keys_reach_the_fields_of_an_open_dialog():
    app = tk.TerminalApp(40, 12)
    seen = []
    dlg = tk.Dialog(0, 0, width=30, height=8)
    app.push_dialog(dlg)
    app.manager.handle_event = lambda et, d: seen.append((et, d))
    app._handle_key('q')
    assert seen == [('key_down', 'q')]


# -------------------------------------------------------------------
# Form
# -------------------------------------------------------------------

def test_form_add_field_lays_fields_out_and_tracks_values():
    form = tk.Form(0, 0, width=30, title='Login')
    name = form.add_field('Name', TextField(0, 0, width=10))
    ok = form.add_field('Ok', Checkbox(0, 0))

    assert [label for label, _ in form.fields] == ['Name', 'Ok']
    assert name.y < ok.y, 'fields must not overlap'
    assert name.x == 0 + len('Name') + 2
    assert form.values == {'Name': '', 'Ok': ''}
    assert form.height > 5


def test_form_wires_a_textfield_to_its_label():
    form = tk.Form(0, 0, width=30)
    field = form.add_field('Name', TextField(0, 0, width=10))
    field.callback('alice')
    assert form.values['Name'] == 'alice'


def test_form_wires_a_checkbox_to_its_label():
    form = tk.Form(0, 0, width=30)
    box = form.add_field('Agree', Checkbox(0, 0))
    box.callback(True)
    assert form.values['Agree'] is True


def test_form_labels_do_not_alias_each_other():
    """The closures capture the label, so two fields must not share a key."""
    form = tk.Form(0, 0, width=30)
    a = form.add_field('A', TextField(0, 0, width=5))
    b = form.add_field('B', TextField(0, 0, width=5))
    a.callback('one')
    b.callback('two')
    assert form.values == {'A': 'one', 'B': 'two'}


def test_form_submit_passes_the_collected_values():
    seen = []
    form = tk.Form(0, 0, width=30, submit_callback=seen.append)
    field = form.add_field('Name', TextField(0, 0, width=5))
    field.callback('bob')
    form.submit()
    assert seen == [{'Name': 'bob'}]


def test_form_cancel_calls_its_callback():
    seen = []
    form = tk.Form(0, 0, width=30, cancel_callback=lambda: seen.append(1))
    form.cancel()
    assert seen == [1]


def test_form_submit_and_cancel_without_callbacks_do_not_raise():
    tk.Form(0, 0, width=30).submit()
    tk.Form(0, 0, width=30).cancel()


def test_form_renders_a_box_with_a_title_and_field_labels():
    form = tk.Form(2, 1, width=34, title='Login')
    form.add_field('Name', TextField(0, 0, width=10))
    canvas = Canvas(40, 20)
    form.render(canvas)

    assert canvas.buffer[1][2].char == '┌'
    assert canvas.buffer[1][35].char == '┐'
    assert 'L' in ''.join(c.char for c in canvas.buffer[1])
    row = ''.join(c.char for c in canvas.buffer[form.fields[0][1].y])
    assert 'Name' in row


def test_form_render_skips_when_hidden():
    form = tk.Form(0, 0, width=20)
    form.visible = False
    canvas = Canvas(30, 12)
    form.render(canvas)
    assert all(c.char == ' ' for row in canvas.buffer for c in row)


def test_form_uses_the_accent_colour_when_focused():
    form = tk.Form(0, 0, width=20)
    canvas = Canvas(30, 12)
    form.render(canvas)
    unfocused = canvas.buffer[0][0].fg
    form.focused = True
    canvas.clear()
    form.render(canvas)
    assert canvas.buffer[0][0].fg == form.accent != unfocused


# -------------------------------------------------------------------
# Dialog rendering
# -------------------------------------------------------------------

def test_dialog_renders_a_double_line_box_with_a_title():
    dlg = tk.Dialog(2, 1, width=20, height=6, title='Quit')
    canvas = Canvas(40, 16)
    dlg.render(canvas)
    assert canvas.buffer[1][2].char == '╔'
    assert canvas.buffer[1][21].char == '╗'
    assert canvas.buffer[6][2].char == '╚'
    assert canvas.buffer[6][21].char == '╝'
    assert canvas.buffer[1][5].char == 'Q'
    # the body is filled so the dialog occludes what is behind it
    assert canvas.buffer[3][10].bg == dlg.bg


def test_dialog_render_clips_at_the_canvas_edge():
    """A dialog larger than, or hanging off, the canvas must not raise."""
    dlg = tk.Dialog(0, 0, width=40, height=12)
    dlg.add_button('OK', 'ok')
    canvas = Canvas(10, 5)
    dlg.render(canvas)


def test_dialog_render_skips_when_hidden():
    dlg = tk.Dialog(0, 0, width=10, height=4)
    dlg.visible = False
    canvas = Canvas(20, 8)
    dlg.render(canvas)
    assert all(c.char == ' ' for row in canvas.buffer for c in row)


def test_dialog_renders_its_buttons_and_content():
    dlg = tk.Dialog(0, 0, width=30, height=8, title='T')
    dlg.add_button('Ok', 'ok')
    dlg.add_button('No', 'no')
    dlg.add_content(Label(2, 2, 'BODY'))
    canvas = Canvas(40, 12)
    dlg.render(canvas)
    text = '\n'.join(''.join(c.char for c in row) for row in canvas.buffer)
    assert 'BODY' in text
    assert 'Ok' in text and 'No' in text
    assert 'T' in text


def test_dialog_buttons_are_spaced_apart():
    dlg = tk.Dialog(0, 0, width=40, height=8)
    a = dlg.add_button('A', 'a')
    b = dlg.add_button('B', 'b')
    assert b.x > a.x
    assert a.y == b.y == dlg.y + dlg.height - 3


def test_dialog_handle_event_is_inert():
    """Modal routing happens in TerminalApp; the widget itself ignores keys."""
    dlg = tk.Dialog(0, 0, width=10, height=4)
    dlg.handle_event('key_down', 'x')
    assert dlg.result is None


def test_terminal_app_exports_the_widgets_it_uses():
    for name in ('Button', 'Checkbox', 'TextField', 'Widget', 'WidgetManager'):
        assert hasattr(tk, name), f'toolkit no longer re-exports {name}'


def test_stdin_fixture_left_stdin_usable(no_stdin):
    assert sys.stdin is not None


# -------------------------------------------------------------------
# end-to-end mouse clicks through the real decoder
# -------------------------------------------------------------------

def _click(app, mgr, btn, data: bytes):
    """Push a raw terminal mouse report through the decoder and the manager."""
    saved = os.dup(0)
    r, w = os.pipe()
    os.dup2(r, 0)
    handle = os.fdopen(r, 'rb')
    real_stdin = sys.stdin
    sys.stdin = handle
    try:
        os.write(w, data)
        for et, mx, my in tk._read_mouse_events(timeout=0.05):
            mgr.handle_event(et, (mx, my))
    finally:
        sys.stdin = real_stdin
        os.close(w)
        os.dup2(saved, 0)
        handle.close()
        os.close(saved)


def test_a_click_without_a_prior_hover_still_presses_the_button():
    """Terminals report motion only while the pointer moves, so a click with
    the pointer already on the button used to arrive with hovered False and was
    dropped."""
    hits = []
    btn = Button(0, 0, 6, text='Go', callback=lambda: hits.append(1))
    mgr = tk.WidgetManager()
    mgr.add(btn, focusable=True)

    _click(None, mgr, btn, b'\x1b[<0;2;1M\x1b[<0;2;1m')
    assert hits == [1]
    assert btn.mouse_down_self is False
    assert btn.pressed is False


def test_a_click_after_a_hover_presses_the_button():
    hits = []
    btn = Button(0, 0, 6, text='Go', callback=lambda: hits.append(1))
    mgr = tk.WidgetManager()
    mgr.add(btn, focusable=True)

    _click(None, mgr, btn, b'\x1b[<35;2;1M\x1b[<0;2;1M\x1b[<0;2;1m')
    assert hits == [1]


def test_releasing_outside_the_button_does_not_activate_it():
    hits = []
    btn = Button(0, 0, 6, text='Go', callback=lambda: hits.append(1))
    mgr = tk.WidgetManager()
    mgr.add(btn, focusable=True)

    _click(None, mgr, btn, b'\x1b[<0;2;1M\x1b[<0;40;9m')
    assert hits == []


def test_a_release_without_a_press_does_nothing():
    hits = []
    btn = Button(0, 0, 6, text='Go', callback=lambda: hits.append(1))
    mgr = tk.WidgetManager()
    mgr.add(btn, focusable=True)

    _click(None, mgr, btn, b'\x1b[<0;2;1m')
    assert hits == []


def test_a_mouse_release_terminator_decodes_as_mouse_up(feed_stdin):
    """SGR reports a release with a lowercase 'm'; ignoring the case meant
    Button never saw mouse_up and no click could ever complete."""
    feed_stdin(b'\x1b[<0;5;5m')
    assert tk._read_mouse_events(timeout=0.05) == [('mouse_up', 4, 4)]
