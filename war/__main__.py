#!/usr/bin/env python3
import sys
import time
import os
import select
import tty
import termios
from spore_engine import Canvas, HiResCanvas, ParticleSystem, Color
from .menu import Menu
from .scene import scene_war_battlefield, reset
from .sound import SoundEngine
from . import ground

FPS = 30
FRAME = 1.0 / FPS
MAX_COLS = 240
MAX_ROWS = 80


def termsize():
    try:
        size = os.get_terminal_size()
        return size.columns, size.lines
    except OSError:
        return 100, 40


def configure_colors():
    ct = os.environ.get('COLORTERM', '').lower()
    if 'truecolor' in ct or '24bit' in ct:
        return

    def to_256(r, g, b):
        def idx(v):
            if v < 48:
                return 0
            if v < 115:
                return 1
            return (v - 35) // 40

        if r == g == b:
            if r < 8:
                return 16
            if r > 238:
                return 231
            return 232 + round((r - 8) / 10)
        return 16 + 36 * idx(r) + 6 * idx(g) + idx(b)

    def ansi_fg(self):
        return '\033[38;5;{}m'.format(to_256(self.r, self.g, self.b))

    def ansi_bg(self):
        return '\033[48;5;{}m'.format(to_256(self.r, self.g, self.b))

    Color.ansi_fg = ansi_fg
    Color.ansi_bg = ansi_bg


def read_key():
    if not select.select([sys.stdin], [], [], 0.016)[0]:
        return None
    raw = os.read(sys.stdin.fileno(), 1)
    if not raw:
        return None
    ch = raw.decode('utf-8', 'replace')
    if ch == '\x1b':
        if select.select([sys.stdin], [], [], 0.05)[0]:
            c2 = os.read(sys.stdin.fileno(), 1).decode('utf-8', 'replace')
            if c2 == '[' and select.select([sys.stdin], [], [], 0.05)[0]:
                c3 = os.read(sys.stdin.fileno(), 1).decode('utf-8', 'replace')
                if c3 == 'A':
                    return 'up'
                if c3 == 'B':
                    return 'down'
                if c3 == 'C':
                    return 'right'
                if c3 == 'D':
                    return 'left'
            elif c2 in ('a', 'b'):
                return 'escape'
        return 'escape'
    if ch in ('\r', '\n'):
        return 'enter'
    if ch in ('q', 'Q'):
        return 'q'
    return ch


def make_canvas(cols, rows):
    return (Canvas(cols, rows), HiResCanvas(cols, rows * 2), Menu(cols, rows))


def run_diag():
    print('TERM=%s' % os.environ.get('TERM', ''))
    print('COLORTERM=%s' % os.environ.get('COLORTERM', ''))
    print('stdin tty=%s  stdout tty=%s' % (sys.stdin.isatty(), sys.stdout.isatty()))
    try:
        size = os.get_terminal_size()
        print('os.get_terminal_size() -> columns=%d lines=%d' % (size.columns, size.lines))
    except OSError:
        print('os.get_terminal_size() -> OSError')
    print('glyph test: %s' % '█ ▄ ▀ ░ ▒ ▓ ● ☄ ─ · ↑ → ►')
    print('truecolor red:   \033[38;2;255;0;0mXXX\033[0m')
    print('256-color red:   \033[38;5;196mXXX\033[0m')
    print('basic red:       \033[31mXXX\033[0m')
    print('grid test (8 cols x 4 rows):')
    for _ in range(4):
        print(''.join('█' for _ in range(8)))
    print('If the glyph line shows boxes/? or the color samples look garbled,'
          ' tell me which lines were wrong.')


def main():
    if '--diag' in sys.argv:
        run_diag()
        return
    configure_colors()

    sound = SoundEngine()
    ground.set_sound(sound)

    cols, rows = termsize()
    cols = max(20, min(cols, MAX_COLS))
    rows = max(10, min(rows, MAX_ROWS))
    c, hr, menu = make_canvas(cols, rows)
    pt = ParticleSystem(500)
    _resize_streak = 0

    is_tty = sys.stdin.isatty() and sys.stdout.isatty()
    old = None
    if is_tty:
        old = termios.tcgetattr(sys.stdin)
        tty.setraw(sys.stdin)

    try:
        if is_tty:
            print('\033[?1049h\033[2J\033[?25l', end='', flush=True)
        else:
            print('=== War Battlefield (standalone) ===', file=sys.stderr)

        state = 'menu'
        t0 = time.time()
        last_frame = time.time()
        paused_time = 0.0
        running = True

        while running:
            now = time.time()
            dt = now - last_frame
            last_frame = now
            if dt > 0.1:
                dt = 0.033
            elapsed = now - t0
            if state == 'menu':
                paused_time = 0.0
            t = max(0, elapsed - paused_time)

            if is_tty:
                nc, nr = termsize()
                if nc >= 20 and nr >= 10:
                    # only honour a genuine, stable resize.  During the middle
                    # of a live resize the terminal can transiently report a
                    # degenerate size (e.g. 0); treating that as a real resize
                    # would wipe the whole battlefield and make it flicker.
                    # Debounce too: a brief one-frame size hiccup, which would
                    # reset() the world and make every soldier vanish then
                    # respawn, must not be able to wipe the battle.
                    nc = max(20, min(nc, MAX_COLS))
                    nr = max(10, min(nr, MAX_ROWS))
                    if (nc, nr) != (cols, rows):
                        _resize_streak += 1
                        if _resize_streak >= 4:
                            cols, rows = nc, nr
                            c, hr, menu = make_canvas(cols, rows)
                            if state == 'game':
                                reset()
                                t0 = time.time()
                            print('\033[2J', end='', flush=True)
                            _resize_streak = 0
                    else:
                        _resize_streak = 0

            key = read_key() if is_tty else None

            c.clear()
            hr.clear()

            if state == 'menu':
                menu.update(dt)
                menu.render(c, hr, t)
                if key is not None:
                    menu.handle_key(key)
                action = menu.pop_action()
                if action == 'start':
                    reset()
                    t0 = time.time()
                    state = 'game'
                elif action == 'quit':
                    running = False

            else:
                scene_war_battlefield(c, hr, t, pt, dt)
                if key == 'q' or key == 'escape':
                    state = 'menu'
                elif key == ' ':
                    pass
                elif key == 'm':
                    sound.toggle_mute()
                elif ground._WB is not None and key in ('left', 'right', 'up', 'down'):
                    if key == 'left':
                        ground._WB['cam_off'] -= 22
                    elif key == 'right':
                        ground._WB['cam_off'] += 22
                    elif key == 'up':
                        ground._WB['cam_y'] = min(12, ground._WB['cam_y'] + 2)
                    elif key == 'down':
                        ground._WB['cam_y'] = max(0, ground._WB['cam_y'] - 2)

            if is_tty:
                c.render_to(sys.stdout)
            else:
                c.render_to(sys.stdout, clear_first=True)
                time.sleep(0.033)

            remaining = FRAME - (time.time() - now)
            if remaining > 0:
                time.sleep(remaining)

    except KeyboardInterrupt:
        pass
    finally:
        sound.close()
        if old:
            termios.tcsetattr(sys.stdin, termios.TCSANOW, old)
        print('\033[?25h\033[0m\033[?1049l', end='', flush=True)
        print('\nWar Battlefield ended.')


if __name__ == '__main__':
    main()
