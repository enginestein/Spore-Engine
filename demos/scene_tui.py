import math
import importlib
from spore_engine import *
from spore_engine.core.color import *
from spore_engine.ui.widgets import *

def _get_key():
    mod = importlib.import_module('demos')
    return mod.KEY_PRESSED

_wm = None
_state = {
    'status': 'Ready',
    'counter': 0,
    'tab': 'Form',
    'name_input': '',
}

_prev_key = None


def _refresh_status():
    global _wm, _state
    if _wm is None:
        return
    f = _wm.get_focused()
    fname = type(f).__name__ if f else None
    sb = None
    for w in _wm.widgets:
        if isinstance(w, StatusBar):
            sb = w
            break
    if sb:
        mode = f'Focus: {fname:<12}' if fname else 'No focus     '
        sb.set_left(f'{mode} Tab: cycle  Enter: act  Arrows: navigate')
        sb.set_right(f'{_state["status"][:36]}')


def _on_click(label):
    _state['counter'] += 1
    _state['status'] = f'{label} (#{_state["counter"]})'
    _refresh_status()


def scene_tui_demo(c, hr, t, pt, dt):
    global _wm, _state, _prev_key

    if _wm is None:
        _wm = WidgetManager()

        _wm.add(TabBar(
            2, 1, ['Form', 'Data', 'Settings', 'About'],
            callback=lambda i, s: _state.update(tab=s) or _on_click(f'Tab: {s}'),
        ), focusable=True)

        _wm.add(Frame(2, 3, 38, 16, title='Form Controls'))
        cb_labels = ['Enable Notifications', 'Dark Mode', 'Auto-save']
        for i, lab in enumerate(cb_labels):
            _wm.add(
                Checkbox(
                    4, 5 + i, lab, i % 2 == 0,
                    callback=lambda v, lab=lab: _on_click(
                        f'{"✓" if v else "✗"} {lab}'
                    ),
                ),
                focusable=True,
            )

        _wm.add(Label(4, 9, 'Display Mode:', fg=DIM))
        _wm.add(
            RadioGroup(
                4, 10, ['Standard', 'Compact', 'Fullscreen'], 0,
                callback=lambda i, s: _on_click(f'Mode: {s}'),
            ), focusable=True,
        )

        _wm.add(Label(4, 13, 'Volume:', fg=DIM))
        _wm.add(
            Slider(
                6, 14, 18, value=0.3,
                callback=lambda v: _on_click(f'Vol: {int(v*100)}%'),
            ), focusable=True,
        )

        _wm.add(Frame(42, 3, 38, 16, title='Data View'))
        tbl = _wm.add(
            Table(
                44, 5, headers=['Task', 'Status', '% Done'],
                col_widths=[10, 10, 8],
                callback=lambda i, r: _on_click(f'Row {i}: {r[0]}'),
            ), focusable=True,
        )
        tbl.set_rows([
            ['Sync', 'Active', '72%'],
            ['Build', 'Pending', '18%'],
            ['Deploy', 'Done', '100%'],
            ['Test', 'Active', '45%'],
            ['Review', 'Queue', '0%'],
        ])

        _wm.add(
            Button(44, 11, 10, 'Refresh',
                   callback=lambda: _on_click('Refresh')),
            focusable=True,
        )
        _wm.add(
            Button(56, 11, 8, 'Edit',
                   callback=lambda: _on_click('Edit')),
            focusable=True,
        )
        _wm.add(
            Button(66, 11, 10, 'Delete',
                   callback=lambda: _on_click('Delete')),
            focusable=True,
        )

        _wm.add(
            Toggle(
                44, 13, 'Auto-refresh', True,
                callback=lambda v: _on_click(f'Auto: {"ON" if v else "OFF"}'),
            ), focusable=True,
        )

        name_input = _wm.add(
            Input(
                44, 15, 16, 'Filter:', '',
                callback=lambda t: _on_click(f'Filter: {t}'),
            ), focusable=True,
        )

        _wm.add(Frame(2, 20, 78, 2, title='Monitor'))
        _wm.add(ProgressBar(4, 21, 30, fg=Color(80, 200, 80), label='CPU'))
        _wm.add(ProgressBar(38, 21, 30, fg=Color(80, 120, 240), label='RAM'))
        _wm.add(Label(2, 22, 'Tab: cycle focus  |  Enter: activate  |  Arrows: navigate  |  q: quit', fg=Color(60, 60, 80)))

        _wm.add(StatusBar(2, c.h - 2, c.w - 3))
        _wm.focus_next()
        _refresh_status()

    key = _get_key()

    if key and key != _prev_key:
        _prev_key = key

        if key == '\t':
            _wm.focus_next()
            _refresh_status()
        elif key == 'up':
            fw = _wm.get_focused()
            if fw and type(fw).__name__ in ('RadioGroup', 'Table', 'Menu'):
                _wm.handle_event('key_down', 'up')
            else:
                _wm.focus_prev()
            _refresh_status()
        elif key == 'down':
            fw = _wm.get_focused()
            if fw and type(fw).__name__ in ('RadioGroup', 'Table', 'Menu', 'TabBar'):
                _wm.handle_event('key_down', 'down')
            else:
                _wm.focus_next()
            _refresh_status()
        elif key in ('left', 'right'):
            _wm.handle_event('key_down', key)
            _refresh_status()
        elif key == '\r':
            _wm.handle_event('key_down', 'enter')
            _refresh_status()
        elif key == ' ':
            _wm.handle_event('key_down', ' ')
            _refresh_status()
        elif key == 'backspace':
            _wm.handle_event('key_down', 'backspace')
            _refresh_status()
        elif key and len(key) == 1:
            _wm.handle_event('key_down', key)
            _refresh_status()
    elif key is None:
        _prev_key = None

    for pb in _wm.widgets:
        if isinstance(pb, ProgressBar):
            if pb.label == 'CPU':
                pb.set_progress(0.35 + 0.3 * math.sin(t * 0.7))
            elif pb.label == 'RAM':
                pb.set_progress(0.50 + 0.25 * math.sin(t * 0.4 + 1.2))

    for y in range(c.h):
        ty = y / c.h
        for x in range(c.w):
            n = (math.sin(x*0.02+t*0.15)+math.cos(y*0.03+t*0.1))*0.5+0.5
            c.set_pixel(x, y, ' ', bg=Color(int(4+n*6), int(3+n*4), int(8+n*14)))

    _wm.render(c, z=30)

    c.draw_text(
        (c.w - 20) // 2, 0,
        ' TUI Toolkit Demo ',
        Color(200, 200, 255), z=100,
    )
