import math, random
from spore_engine.core.color import Color, WHITE, RED, GREEN, BLUE, YELLOW, CYAN, ORANGE, DIM, PALETTES
from spore_engine.core.canvas import Canvas
from spore_engine.anim.anim import Entity, Animator, Path, PathFollower, Tween, Oscillator, lerp_color

_LS = None

def scene_anim_path(c, hr, t, pt, dt):
    global _LS
    if _LS is None:
        entity = Entity(c.w // 2, c.h // 2)
        path = Path()
        pts = 8
        for i in range(pts):
            angle = 2 * math.pi * i / pts
            r = 10 + 5 * (1 if i % 2 == 0 else 0)
            path.add_point(c.w // 2 + r * math.cos(angle),
                           c.h // 2 + 5 * math.sin(angle))
        follower = PathFollower(path, duration=5.0, loop=True, easing='sine_in_out')
        follower2 = PathFollower(path, duration=7.0, loop=True, easing='linear')

        bounce = Tween(duration=1.2, easing='bounce_out', loop=True, yoyo=True)
        elastic = Tween(duration=2.0, easing='elastic_out', loop=True, yoyo=True)
        osc = Oscillator(period=0.8, min_val=0.0, max_val=1.0)

        _LS = {
            'entity': entity,
            'path': path,
            'follower': follower,
            'follower2': follower2,
            'bounce': bounce,
            'elastic': elastic,
            'osc': osc,
            'time': 0.0,
            'balls': [],
        }
        for i in range(6):
            _LS['balls'].append({
                'x': 10 + i * 12,
                'base_y': c.h // 2 + 6,
                'tween': Tween(duration=0.8 + i * 0.2,
                              easing=['bounce_out', 'elastic_out', 'back_out',
                                      'cubic_in_out', 'sine_in_out', 'quad_in_out'][i],
                              loop=True, yoyo=True),
                'color': [RED, GREEN, BLUE, YELLOW, CYAN, ORANGE][i],
                'label': ['bounce', 'elastic', 'back', 'cubic', 'sine', 'quad'][i],
            })
    s = _LS

    s['time'] += dt
    s['follower'].update(dt)
    s['follower2'].update(dt)
    s['bounce'].update(dt)
    s['elastic'].update(dt)

    c.clear()
    for y in range(c.h):
        ty = y / c.h
        for x in range(c.w):
            n = (math.sin(x*0.02+t*0.2)+math.cos(y*0.03+t*0.15))*0.5+0.5
            c.set_pixel(x, y, ' ', bg=Color(int(3+n*6), int(1+n*4), int(8+n*18)), z=-100)

    s['path'].render(c, '.', Color(40, 40, 60), z=5)

    px, py = s['follower'].get_position()
    c.set_pixel(round(px), round(py), '@', WHITE, z=15)
    c.draw_text(round(px) + 1, round(py), 'sine', DIM, z=15)

    px2, py2 = s['follower2'].get_position()
    c.set_pixel(round(px2), round(py2), '♦', Color(200, 100, 255), z=15)
    c.draw_text(round(px2) + 1, round(py2), 'linear', DIM, z=15)

    for ball in s['balls']:
        ball['tween'].update(dt)
        v = ball['tween'].value
        by = ball['base_y'] - v * 8
        c.set_pixel(round(ball['x']), round(by), '●', ball['color'], z=10)
        bar_w = int(v * 10)
        for bx in range(bar_w):
            c.set_pixel(round(ball['x']) - 5 + bx, round(by) + 2, '▄', ball['color'].mul(0.5), z=5)
        c.draw_text(round(ball['x']) - 3, round(by) - 2, ball['label'], DIM, z=10)

    elastic_v = s['elastic'].value
    bounce_v = s['bounce'].value
    c.draw_rect(c.w // 2 - 25, c.h - 5, 20, 2, ' ', bg=RED.mul(0.3), z=5, fill=True)
    for i in range(20):
        tgt = int(20 * bounce_v)
        if i < tgt:
            c.set_pixel(c.w // 2 - 25 + i, c.h - 5, '█', RED, z=10)

    c.draw_text(2, 0, "Animation System | Path following + tweens", WHITE, z=20)
    c.draw_text(2, 1, f"Path points: {len(s['path'].points)} | Loop: 5s/7s", DIM, z=20)
    easing_names = ['bounce', 'elastic', 'back', 'cubic', 'sine', 'quad']
    c.draw_text(2, c.h - 1, "Balls show different easing functions", DIM, z=20)
