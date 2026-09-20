#!/usr/bin/env python3
import sys, time, os, random
import demos as _demos
from spore_engine import (Canvas, HiResCanvas, ParticleSystem, Color, DIM,
                          WHITE, Input, KeyEvent)
from spore_engine.fx.transitions import Fade, Wipe, Slide, Checkerboard, PixelDissolve
from demos import SCENES


def termsize():
    try: return os.get_terminal_size().columns, os.get_terminal_size().lines
    except: return 100, 40


def main():
    cols, rows = termsize()
    c = Canvas(cols, rows)
    prev_c = Canvas(cols, rows)
    hr = HiResCanvas(cols, rows * 2)
    pt = ParticleSystem(500)
    si = 0
    paused = False
    running = True
    t0 = time.time()
    paused_time = 0.0
    last_frame = time.time()
    
    # Transition state
    transition_obj = None
    transition_start = -1.0
    transition_duration = 0.8
    transitions = [
        Fade(), 
        Wipe('right'), Wipe('left'), Wipe('down'), Wipe('up'),
        Slide('right'), Slide('left'), Slide('down'), Slide('up'),
        Checkerboard(size=4), PixelDissolve()
    ]

    is_tty = sys.stdin.isatty() and sys.stdout.isatty()
    inp = Input(0)
    if is_tty:
        inp.enter_raw()

    try:
        if is_tty:
            print('\033[?25l\033[2J', end='', flush=True)
        else:
            print(f"=== Spore Engine — {len(SCENES)}-Scene Demo ===", file=sys.stderr)

        while running:
            now = time.time()
            dt = now - last_frame
            last_frame = now
            if dt > 0.1: dt = 0.033
            elapsed = now - t0
            if paused:
                paused_time += dt
            t = max(0, elapsed - paused_time)
            name, fn = SCENES[si]

            if not paused:
                # Clear both canvases before each scene
                c.clear()
                hr.clear()
                fn(c, hr, t, pt, dt)

            # Handle transition
            if transition_start > 0:
                trans_t = (now - transition_start) / transition_duration
                if trans_t >= 1.0:
                    transition_start = -1.0
                else:
                    # Apply transition from prev_c to c
                    transition_obj.apply(c, prev_c, trans_t)

            if is_tty:
                bar = " q=Quit Spc=Pause n=Next p=Prev "
                if paused: bar += "[PAUSED] "
                info = f"Scene {si+1}/{len(SCENES)}: {name}  |{bar}"
                c.draw_text(2, c.h-1, info[:c.w-4], DIM, z=100)
                c.draw_text(2, 0, f"{si+1}: {name}", WHITE, z=100)
                c.render_to(sys.stdout)
            else:
                c.render_to(sys.stdout, clear_first=(last_frame == now))

            if is_tty:
                _demos.KEY_PRESSED = None

                old_si = si
                for ev in inp.events(0.033):
                    if not isinstance(ev, KeyEvent) or not ev.down:
                        continue
                    ch = ev.key

                    if ch == 'q':
                        running = False

                    elif ch == ' ':
                        paused = not paused

                    elif ch == 'n':
                        si = (si + 1) % len(SCENES)

                    elif ch == 'p':
                        si = (si - 1) % len(SCENES)

                    else:
                        _demos.KEY_PRESSED = ch

                if si != old_si:
                        prev_c = c.copy()
                        transition_obj = random.choice(transitions)
                        transition_start = time.time()
                        paused_time = 0
                        t0 = time.time()

            else:
                time.sleep(0.033)

                if int(t / 5) != int((t - dt) / 5):
                    prev_c = c.copy()
                    si = (si + 1) % len(SCENES)
                    transition_obj = random.choice(transitions)
                    transition_start = time.time()
                    t0 = time.time()
                    paused_time = 0

    except KeyboardInterrupt:
        pass
    finally:
        inp.exit_raw()
        print('\033[?25h\033[0m', end='', flush=True)
        print(f'\nSpore Engine demo ended. {len(SCENES)} scenes total.')


if __name__ == '__main__':
    main()
