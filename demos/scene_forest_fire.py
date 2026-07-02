import math, random
from spore_engine import *
from spore_engine.core.color import *

_FF = None

def scene_forest_fire(c, hr, t, pt, dt):
    global _FF
    w, h = c.w, c.h

    if _FF is None:
        trees = []
        for x in range(0, w, 3):
            th = random.randint(3, 10)
            tw = random.randint(2, 4)
            green = random.randint(30, 80)
            trees.append({
                'x': x, 'w': tw, 'h': th,
                'col': Color(10, green, 5),
                'burn': random.uniform(0, 1),
                'burn_speed': random.uniform(0.1, 0.4),
            })
        embers = []
        for _ in range(30):
            embers.append({
                'x': random.uniform(0, w), 'y': random.uniform(0, h),
                'vx': random.uniform(-1, 1), 'vy': random.uniform(-2, 0.5),
                'life': random.uniform(0.5, 2.0),
                'age': random.uniform(0, 2),
            })
        _FF = {'trees': trees, 'embers': embers}

    s = _FF

    for y in range(h):
        ty = y / h
        col = Color(int(8+ty*6), int(5+ty*4), int(12+ty*8))
        for x in range(w):
            c.set_pixel(x, y, ' ', bg=col, z=-100)

    fire_spread = 0.5 + 0.5 * math.sin(t * 0.15)

    for tr in s['trees']:
        tr['burn'] = min(1.0, tr['burn'] + tr['burn_speed'] * dt * fire_spread * random.uniform(0.5, 1.5))
        if tr['burn'] > 0.9 and random.random() < 0.001:
            tr['burn'] = 1.0

        for dy in range(tr['h']):
            py = h - 2 - dy
            for dx in range(tr['w']):
                px = tr['x'] + dx
                if 0 <= px < w and 0 <= py < h:
                    burn = tr['burn']
                    if burn < 0.3:
                        c.set_pixel(px, py, '▲' if dy < 2 else '█', tr['col'], z=5)
                    elif burn < 0.6:
                        t_ = (burn - 0.3) / 0.3
                        col = tr['col'].lerp(Color(200, 80, 20), t_)
                        ch = '▒' if t_ < 0.5 else '▓'
                        c.set_pixel(px, py, ch, col, z=5)
                    else:
                        t_ = (burn - 0.6) / 0.4
                        col = Color(200, 80, 20).lerp(Color(60, 20, 10), t_)
                        c.set_pixel(px, py, '▓', col, z=5)

        if tr['burn'] > 0.5 and random.random() < tr['burn'] * 0.1:
            for _ in range(2):
                ex = tr['x'] + random.randint(0, tr['w']-1)
                ey = h - 2 - int(tr['h'] * random.random())
                if 0 <= ex < w and 0 <= ey < h:
                    c.set_pixel(ex, ey, '·', Color(255, 150, 50).mul(random.uniform(0.5, 1.0)), z=15)

    for e in s['embers']:
        e['x'] += e['vx'] * dt * 10
        e['y'] += e['vy'] * dt * 10
        e['age'] += dt
        e['vy'] -= 0.5 * dt
        if e['age'] >= e['life'] or e['y'] < -5:
            e['x'] = random.uniform(w*0.1, w*0.9)
            e['y'] = random.uniform(h*0.3, h*0.7)
            e['vx'] = random.uniform(-0.5, 0.5)
            e['vy'] = random.uniform(-1.5, -0.3)
            e['life'] = random.uniform(1.0, 3.0)
            e['age'] = 0
        px, py = int(e['x']), int(e['y'])
        if 0 <= px < w and 0 <= py < h:
            life = 1 - e['age']/e['life']
            col = Color.from_hsv(0.07, 0.9, 0.4+0.6*life)
            c.set_pixel(px, py, '·' if life < 0.4 else '●', col, z=20)
