import math
from spore_engine import *
from spore_engine.core.color import *
from spore_engine.ui.widgets import *
from spore_engine.ui.toolkit import Form, Dialog
import demos as _d


scene_state = {}


def scene_terminal_app(c: Canvas, hr: HiResCanvas, t: float, pt, dt: float):
    w, h = c.w, c.h
    key = _d.KEY_PRESSED

    if 'initialized' not in scene_state:
        ss = {
            'initialized': True,
            'log': [],
            'cpus': [0.3, 0.5, 0.7],
            'mem': 0.45,
            'status': 'Ready',
            'dialog_open': False,
            'dialog_t': 0,
            'form_submitted': {},
            'edit_text': '',
            'active_btn': 0,
            'btn_hover': [False, False],
            'tab_idx': 0,
            'tabs': ['Main', 'Stats', 'Config'],
            'show_dialog': False,
            'show_settings': False,
        }
        scene_state.update(ss)

    s = scene_state

    if key == '\r':
        if s['show_dialog']:
            s['show_dialog'] = False
            s['log'].append('Dialog confirmed')
        elif s['show_settings']:
            s['show_settings'] = False
            s['log'].append('Settings saved')
        else:
            s['log'].append(f'Enter pressed (t={t:.1f})')
    elif key == 'escape':
        if s['show_dialog']:
            s['show_dialog'] = False
            s['log'].append('Dialog dismissed')
        elif s['show_settings']:
            s['show_settings'] = False
            s['log'].append('Settings closed')
    elif key == ' ' and not s['show_dialog'] and not s['show_settings']:
        s['show_dialog'] = True
        s['dialog_t'] = t
        s['log'].append('Opening dialog...')
    elif key == '\t':
        if s['show_settings']:
            s['tab_idx'] = (s['tab_idx'] + 1) % len(s['tabs'])
        else:
            s['active_btn'] = (s['active_btn'] + 1) % 4
    elif key == 'up':
        s['active_btn'] = max(0, s['active_btn'] - 1)
    elif key == 'down':
        s['active_btn'] = min(3, s['active_btn'] + 1)
    elif key == 'left' and s['show_settings']:
        s['tab_idx'] = (s['tab_idx'] - 1) % len(s['tabs'])
    elif key == 'right' and s['show_settings']:
        s['tab_idx'] = (s['tab_idx'] + 1) % len(s['tabs'])
    elif key and not s['show_dialog'] and not s['show_settings'] and len(key) == 1 and key.isprintable():
        s['edit_text'] += key
        s['log'].append(f'Key: {key}')
    elif key == 'backspace' and not s['show_dialog'] and not s['show_settings']:
        s['edit_text'] = s['edit_text'][:-1]
    elif key == 's' and not s['show_dialog']:
        s['show_settings'] = not s['show_settings']
        s['log'].append('Settings toggled')

    for y in range(h):
        for x in range(w):
            v = (x / w) * 0.5 + (y / h) * 0.3
            c.set_pixel(x, y, ' ', bg=Color(int(8 + v * 12), int(5 + v * 8), int(12 + v * 18)))

    form = Form(1, 2, width=28, title='Terminal App',
                fg=Color(180, 180, 220), accent=Color(100, 200, 255))
    name_input = TextField(0, 0, 14, placeholder='Enter name')
    name_input.text = s.get('edit_text', '')
    form.add_field('Name', name_input)
    age_input = TextField(0, 0, 5, placeholder='Age')
    form.add_field('Age', age_input)
    form.add_field('Enabled', Checkbox(0, 0, '', True))
    form.render(c, z=40)

    c.draw_rect(31, 2, 28, 16, '─', Color(100, 150, 200), z=20, fill=False)
    c.set_pixel(31, 2, '╔', Color(100, 150, 200), z=20)
    c.set_pixel(58, 2, '╗', Color(100, 150, 200), z=20)
    c.set_pixel(31, 17, '╚', Color(100, 150, 200), z=20)
    c.set_pixel(58, 17, '╝', Color(100, 150, 200), z=20)
    for i in range(1, 27):
        c.set_pixel(31 + i, 2, '═', Color(100, 150, 200), z=20)
        c.set_pixel(31 + i, 17, '═', Color(100, 150, 200), z=20)
    for i in range(1, 16):
        c.set_pixel(31, 2 + i, '║', Color(100, 150, 200), z=20)
        c.set_pixel(58, 2 + i, '║', Color(100, 150, 200), z=20)
    title2 = ' Monitor '
    for i, ch in enumerate(title2):
        c.set_pixel(33 + i, 2, ch, WHITE, z=21)

    tabs_x = 32
    for ti, tab_name in enumerate(s['tabs']):
        is_sel = ti == s['tab_idx']
        tab_color = Color(100, 200, 255) if is_sel else DIM
        tab_bg = Color(40, 40, 80) if is_sel else None
        c.draw_text(tabs_x + ti * 8, 3, f'[{tab_name}]', tab_color, tab_bg, z=30)
        if is_sel:
            c.draw_text(tabs_x + ti * 8, 3, f'[{tab_name}]', WHITE, Color(50, 50, 100), z=31)

    label_x = 32
    if s['tab_idx'] == 0:
        cpu_label = 'CPU:'
        for i, ch in enumerate(cpu_label):
            c.set_pixel(label_x + i, 5, ch, Color(180, 180, 200), z=30)
        for i in range(3):
            val = 0.3 + 0.6 * (t * (0.3 + i * 0.1) % 1.0)
            s['cpus'][i] = val
            bar_x = label_x + len(cpu_label) + 1 + i * 8
            bar_w = 7
            filled = int(val * bar_w)
            for j in range(bar_w):
                px = bar_x + j
                if j < filled:
                    intensity = 1 - j / bar_w
                    col = Color(int(60 + 180 * intensity), int(200 * (1 - intensity)), 60)
                else:
                    col = Color(20, 20, 30)
                c.set_pixel(px, 5, '█' if j < filled else '░', col, z=30)
            for j, ch in enumerate(f'CPU{i}'):
                c.set_pixel(bar_x + j, 6, ch, Color(120, 120, 150), z=30)

        mem_label = 'MEM:'
        for i, ch in enumerate(mem_label):
            c.set_pixel(label_x + i, 8, ch, Color(180, 180, 200), z=30)
        mem_v = 0.4 + 0.3 * math.sin(t * 0.3)
        s['mem'] = mem_v
        mem_bar_x = label_x + len(mem_label) + 1
        mem_filled = int(mem_v * 22)
        for j in range(22):
            if j < mem_filled:
                col = Color(80, 120 + int(130 * (1 - j / 22)), 200)
            else:
                col = Color(20, 20, 30)
            c.set_pixel(mem_bar_x + j, 8, '█' if j < mem_filled else '░', col, z=30)
        pct = f'{int(mem_v * 100)}%'
        for i, ch in enumerate(pct):
            c.set_pixel(mem_bar_x + 23 + i, 8, ch, Color(120, 180, 220), z=30)

        log_x = label_x
        c.draw_text(log_x, 10, 'Event Log', Color(100, 200, 255), z=30)
        log_entries = s['log'][-6:]
        for li, entry in enumerate(log_entries):
            c.draw_text(log_x, 11 + li, f' > {entry[:24]}', Color(160, 160, 180), z=30)

    elif s['tab_idx'] == 1:
        stats = [
            f'FPS: {1/max(dt, 0.001):.0f}',
            f'Time: {t:.1f}s',
            f'CPU Avg: {sum(s.get("cpus", [0,0,0]))/3*100:.0f}%',
            f'Memory: {int(s.get("mem", 0)*100)}%',
            f'Input: "{s.get("edit_text", "")[:12]}"',
            f'Events: {len(s.get("log", []))}',
        ]
        for i, line in enumerate(stats):
            c.draw_text(label_x, 5 + i, f'  {line}', Color(180, 200, 220), z=30)

    else:
        settings = ['Theme: Dark', 'Sound: OFF', 'Auto-save: ON', 'Debug: OFF']
        for i, item in enumerate(settings):
            sel = i == (int(t) % 4)
            fg = Color(100, 200, 255) if sel else Color(160, 160, 180)
            c.draw_text(label_x, 5 + i, f' {"▸" if sel else " "} {item}', fg, z=30)

    btn_y = 17
    btn_labels = ['Dialog', 'Settings', 'Action', 'Clear Log']
    for bi, bl in enumerate(btn_labels):
        is_active = bi == s['active_btn']
        bx = 31 + bi * 7
        bg = Color(50, 50, 100) if is_active else Color(30, 30, 50)
        c.draw_text(bx, btn_y, f'[{bl}]', WHITE if is_active else DIM, bg, z=30)

    input_line = f' Input: '
    for i, ch in enumerate(input_line):
        c.set_pixel(1, 19, ' ', bg=Color(15, 15, 30))
    c.draw_text(1, 19, f' Input: {s["edit_text"][:20]}', Color(100, 200, 255),
                Color(15, 15, 30), z=30)

    if s['show_dialog']:
        elapsed = t - s.get('dialog_t', t)
        dx, dy = 15, 5
        dw, dh = 30, 12
        for dy2 in range(dh):
            for dx2 in range(dw):
                px, py = dx + dx2, dy + dy2
                if 0 <= px < w and 0 <= py < h:
                    c.set_pixel(px, py, ' ', None, Color(15, 15, 30), z=100)
        bfg = Color(150, 200, 255)
        c.set_pixel(dx, dy, '╔', bfg, z=101)
        c.set_pixel(dx + dw - 1, dy, '╗', bfg, z=101)
        c.set_pixel(dx, dy + dh - 1, '╚', bfg, z=101)
        c.set_pixel(dx + dw - 1, dy + dh - 1, '╝', bfg, z=101)
        for i in range(1, dw - 1):
            c.set_pixel(dx + i, dy, '═', bfg, z=101)
            c.set_pixel(dx + i, dy + dh - 1, '═', bfg, z=101)
        for i in range(1, dh - 1):
            c.set_pixel(dx, dy + i, '║', bfg, z=101)
            c.set_pixel(dx + dw - 1, dy + i, '║', bfg, z=101)
        dialog_title = ' Confirm '
        for i, ch in enumerate(dialog_title):
            c.set_pixel(dx + 2 + i, dy, ch, WHITE, z=102)

        msg = 'Submit form data?'
        for i, ch in enumerate(msg):
            c.set_pixel(dx + 4 + i, dy + 3, ch, Color(200, 200, 220), z=102)

        details = f'Name: {s["edit_text"][:12] or "<empty>"}'
        for i, ch in enumerate(details):
            c.set_pixel(dx + 4 + i, dy + 5, ch, Color(150, 150, 180), z=102)

        btn_y = dy + dh - 3
        blink = elapsed % 0.5 < 0.25
        yes_bg = Color(40, 80, 40) if blink else Color(50, 100, 50)
        for i, ch in enumerate(' [ Yes ] '):
            c.set_pixel(dx + 4 + i, btn_y, ch, Color(100, 255, 100), yes_bg, z=102)
        for i, ch in enumerate(' [ No ]  '):
            c.set_pixel(dx + 14 + i, btn_y, ch, Color(255, 100, 100), Color(60, 30, 30), z=102)

        hint = 'Enter=Yes  Esc=No'
        for i, ch in enumerate(hint):
            c.set_pixel(dx + 8 + i, dy + dh - 2, ch, Color(80, 80, 100), z=102)

    if s['show_settings']:
        sx, sy = 10, 3
        sw, sh = 40, 16
        for dy2 in range(sh):
            for dx2 in range(sw):
                px, py = sx + dx2, sy + dy2
                if 0 <= px < w and 0 <= py < h:
                    c.set_pixel(px, py, ' ', None, Color(18, 18, 36), z=90)
        bfg2 = Color(180, 180, 100)
        c.set_pixel(sx, sy, '╔', bfg2, z=91)
        c.set_pixel(sx + sw - 1, sy, '╗', bfg2, z=91)
        c.set_pixel(sx, sy + sh - 1, '╚', bfg2, z=91)
        c.set_pixel(sx + sw - 1, sy + sh - 1, '╝', bfg2, z=91)
        for i in range(1, sw - 1):
            c.set_pixel(sx + i, sy, '═', bfg2, z=91)
            c.set_pixel(sx + i, sy + sh - 1, '═', bfg2, z=91)
        for i in range(1, sh - 1):
            c.set_pixel(sx, sy + i, '║', bfg2, z=91)
            c.set_pixel(sx + sw - 1, sy + i, '║', bfg2, z=91)
        stitle = ' Settings '
        for i, ch in enumerate(stitle):
            c.set_pixel(sx + 2 + i, sy, ch, WHITE, z=92)

        prefs = [
            'Display: Truecolor',
            'FPS Limit: 30',
            'Effects: Enabled',
            'Log Level: Info',
        ]
        for i, pref in enumerate(prefs):
            c.draw_text(sx + 3, sy + 3 + i, f'  {pref}', Color(180, 200, 220), z=92)

        hint2 = 'Esc=Close  Tab=Next'
        c.draw_text(sx + 10, sy + sh - 2, hint2, Color(80, 80, 100), z=92)

    c.draw_text(w // 2 - 11, 0, ' Native Terminal GUI ',
                Color(150, 200, 255), z=60)

    for x in range(w):
        for y in range(h):
            px = c.get_pixel(x, y)
            if px and px.fg:
                hr.set_pixel(x * 2, y, px.char, px.fg, px.z)
                hr.set_pixel(x * 2 + 1, y, px.char, px.fg, px.z)
