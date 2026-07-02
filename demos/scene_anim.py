import math, random
from spore_engine.core.color import Color, WHITE, DIM
from spore_engine.anim.anim import Tween, Oscillator, Sequence, bounce_out, elastic_in_out, sine_in_out

SHADE = ' .:-=+*#%@'
_LS = None

def scene_anim(c, hr, t, pt, dt):
    global _LS
    if _LS is None:
        _LS = {
            'tweens': [
                Tween(2.0, 'bounce_out', yoyo=True),
                Tween(1.5, 'elastic_out', yoyo=True),
                Tween(2.5, 'cubic_in_out', yoyo=True, loop=True),
                Tween(1.8, 'back_out', yoyo=True),
                Tween(2.0, 'circ_out', yoyo=True),
            ],
            'seq': Sequence((1.0, 'quad_out'), (1.0, 'elastic_out'), (1.0, 'bounce_out')),
            'osc': Oscillator(2.0, 0, 1),
            'color_t': Tween(3.0, 'sine_in_out', loop=True),
        }
        _LS['tweens'][3].elapsed = 1.0  # staggered start

    c.clear()

    # Background
    for y in range(c.h):
        for x in range(c.w):
            c.set_pixel(x, y, ' ', bg=Color(5, 3, 15), z=-100)

    # ── TAB TITLE ─────────────────────────────────────────────────
    c.draw_text(2, 0, "Animation Demo", Color(255, 200, 100), z=100)

    # ── TWEEENS (bouncing balls, progress bars) ──────────────────
    for i, tw in enumerate(_LS['tweens']):
        tw.update(dt)
        v = tw.value
        bx = 8 + i * 15
        by = int(4 + (1 - v) * 12)

        # Ball
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if math.hypot(dx, dy) <= 1.5:
                    px, py = bx+dx, by+dy
                    if 0 <= px < c.w and 0 <= py < c.h:
                        c.set_pixel(px, py, '@' if dx==0 and dy==0 else 'O',
                                    Color(120+int(v*135), int(100*v)+80, 255), z=20)

        # Bar
        bw = 12
        filled = int(v * bw)
        for bx2 in range(bw):
            px = bx - bw//2 + bx2
            py = 18
            if 0 <= px < c.w:
                ch = '█' if bx2 < filled else '░'
                c.set_pixel(px, py, ch, Color(60+int(v*195), 60, 180), z=15)

        # Label
        names = ['bounce', 'elastic', 'cubic io', 'back', 'circ']
        c.draw_text(bx - 3, 20, names[i], DIM, z=100)

    # ── OSCILLATOR ───────────────────────────────────────────────
    ov = _LS['osc'].value(t)
    ox = int(4 + ov * (c.w - 8))
    oy = 5
    for dx in range(-2, 3):
        for dy in range(-1, 2):
            px, py = ox+dx, oy+dy
            if 0 <= px < c.w and 0 <= py < c.h:
                c.set_pixel(px, py, '#', Color(255, 100+int(ov*155), 100), z=20)
    c.draw_text(c.w//2-8, 0, "Oscillator:", DIM)
    c.set_pixel(c.w-3, 5 if ov > 0.5 else 4, '→' if ov > 0.5 else '←', WHITE)

    # ── SEQUENCE ─────────────────────────────────────────────────
    _LS['seq'].update(dt)
    sv = _LS['seq'].value
    if not _LS['seq'].done:
        sx = int(10 + sv * 50)
        sy = 10
        for dx in range(-2, 3):
            px = sx + dx
            if 0 <= px < c.w and 0 <= sy < c.h:
                c.set_pixel(px, sy, '■', Color(100+int(sv*155), 255, 100), z=20)
        c.draw_text(sx-4, 12, "seq→", DIM)
    else:
        if random.random() < dt:
            _LS['seq'].reset()
