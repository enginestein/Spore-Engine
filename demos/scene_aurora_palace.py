import math, random
from spore_engine import *
from spore_engine.core.color import *

_AI = None

def scene_aurora_palace(c, hr, t, pt, dt):
    global _AI
    w, h = c.w, c.h

    if _AI is None:
        snowflakes = []
        for _ in range(40):
            snowflakes.append({
                'x': random.uniform(0, w), 'y': random.uniform(0, h),
                'vx': random.uniform(-0.2, 0.2), 'vy': random.uniform(0.3, 0.8),
                'size': random.randint(0, 1),
                'phase': random.uniform(0, 2*math.pi),
            })
        _AI = {'snowflakes': snowflakes}

    s = _AI

    for y in range(h):
        ty = y / h
        hue = 0.7 - ty * 0.05
        sat = 0.2 + ty * 0.2
        bright = 0.02 + ty * 0.08
        col = Color.from_hsv(hue % 1.0, sat, bright)
        for x in range(w):
            c.set_pixel(x, y, ' ', bg=col, z=-100)

    for y in range(int(h*0.05), int(h*0.35)):
        for x in range(w):
            offset = y * 0.05 + x * 0.02
            aurora = math.sin(offset + t * 0.3) * 0.5 + 0.5
            aurora2 = math.sin(offset * 1.5 + t * 0.5) * 0.5 + 0.5
            aurora3 = math.sin(offset * 0.7 + t * 0.2 + 1.5) * 0.5 + 0.5
            val = aurora * 0.5 + aurora2 * 0.3 + aurora3 * 0.2
            if val > 0.4:
                hue = 0.65 + val * 0.15
                ch = ' ' if val < 0.5 else ('░' if val < 0.6 else ('▒' if val < 0.75 else '▓'))
                c.set_pixel(x, y, ch, Color.from_hsv(hue % 1.0, 0.6, 0.1+val*0.5), z=3)

    stars_set = set()
    for _ in range(30):
        sx = random.randint(0, w-1)
        sy = random.randint(0, int(h*0.3)-1)
        if random.random() < 0.7:
            pulse = 0.5 + 0.5 * math.sin(t*1.5 + sx*3 + sy*7)
            c.set_pixel(sx, sy, '·', Color(200, 210, 255).mul(pulse*0.5), z=2)

    palace_cx = w // 2
    palace_base = h - 1
    center_tower_h = int(h * 0.4)
    side_towers = [(int(w*0.3), int(h*0.25)), (int(w*0.7), int(h*0.25))]
    center_w = 8

    for tower_x, tower_h in [(palace_cx, center_tower_h), side_towers[0], side_towers[1]]:
        tw = 5 if tower_x == palace_cx else 4
        for y in range(palace_base - tower_h, palace_base + 1):
            ty = (y - (palace_base - tower_h)) / max(1, tower_h)
            for x in range(tower_x - tw, tower_x + tw + 1):
                if 0 <= x < w and 0 <= y < h:
                    if y == palace_base - tower_h:
                        if tower_x == palace_cx:
                            c.set_pixel(x, y, '▲', Color(120, 140, 180).mul(1-ty*0.3), z=8)
                        else:
                            c.set_pixel(x, y, '▲', Color(100, 120, 160).mul(1-ty*0.3), z=8)
                    elif x == tower_x - tw or x == tower_x + tw or abs(x - tower_x) <= 1:
                        col = Color(int(80+ty*40), int(100+ty*50), int(140+ty*60)).mul(1-ty*0.2)
                        c.set_pixel(x, y, '║', col, z=8)
                    else:
                        col = Color(int(50+ty*30), int(70+ty*40), int(100+ty*50)).mul(1-ty*0.3)
                        c.set_pixel(x, y, '█', col, z=8)

    for tower_x, tower_h in [(palace_cx, center_tower_h), side_towers[0], side_towers[1]]:
        tw = 5 if tower_x == palace_cx else 4
        for wy in range(palace_base - tower_h + 3, palace_base - 1, random.randint(4, 7)):
            for wx in range(tower_x - tw + 2, tower_x + tw - 1, 3):
                if 0 <= wx < w and wy < h:
                    glow = 0.5 + 0.5 * math.sin(t*0.7 + wx*1.5 + wy*2.3)
                    col = Color.from_hsv(0.12, 0.8, 0.3+0.7*glow)
                    c.set_pixel(wx, wy, '█', col, z=10)
                    if glow > 0.6:
                        for ddx, ddy in [(-1,0),(1,0),(0,-1),(0,1)]:
                            if 0 <= wx+ddx < w and 0 <= wy+ddy < h:
                                c.set_pixel(wx+ddx, wy+ddy, '·', col.mul(0.3), z=9)

    for x in range(w):
        for y in range(palace_base-2, palace_base+1):
            if 0 <= y < h:
                c.set_pixel(x, y, '█', Color(30, 40, 60), z=6)

    for flake in s['snowflakes']:
        flake['x'] += flake['vx'] * dt * 8 + math.sin(t*0.5+flake['phase'])*0.3
        flake['y'] += flake['vy'] * dt * 10
        if flake['y'] > h+2:
            flake['y'] = -2
            flake['x'] = random.uniform(0, w)
        px, py = int(flake['x']), int(flake['y'])
        if 0 <= px < w and 0 <= py < h:
            c.set_pixel(px, py, '·' if flake['size'] == 0 else '°', Color(200, 220, 255).mul(0.5+0.5*random.random()), z=15)

    if 0 <= palace_cx < w and 0 <= palace_base - center_tower_h - 5 < h:
        c.set_pixel(palace_cx, palace_base - center_tower_h - 5, '●', Color(255, 220, 180).mul(0.6+0.4*math.sin(t)), z=12)
