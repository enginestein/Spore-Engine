import math, random
from spore_engine import *
from spore_engine.core.color import *

_UW = None

def scene_underwater(c, hr, t, pt, dt):
    global _UW
    w, h = c.w, c.h

    if _UW is None:
        fish = []
        for _ in range(8):
            fish.append({
                'x': random.uniform(0, w), 'y': random.uniform(h*0.15, h*0.7),
                'vx': random.uniform(-1, 1), 'vy': random.uniform(-0.3, 0.3),
                'hue': random.random(), 'size': random.uniform(1, 2.5),
                'tail_phase': random.uniform(0, 2*math.pi),
            })
        bubbles = []
        for _ in range(15):
            bubbles.append({
                'x': random.uniform(0, w), 'y': random.uniform(0, h),
                'speed': random.uniform(0.3, 1.0), 'size': random.randint(0, 2),
                'sway': random.uniform(0, 2*math.pi),
            })
        coral = []
        for bx in range(0, w, random.randint(3, 6)):
            bh = random.randint(2, 6)
            col = Color.from_hsv(random.uniform(0.0, 0.1), 0.8, 0.3+0.4*random.random())
            coral.append({'x': bx, 'h': bh, 'col': col})
        _UW = {'fish': fish, 'bubbles': bubbles, 'coral': coral}

    s = _UW

    for y in range(h):
        ty = y / h
        col = Color.from_hsv(0.58-ty*0.08, 0.6, 0.05+ty*0.25)
        for x in range(w):
            caustic = math.sin(x*0.1+t*1.5)*math.sin(y*0.08+t*1.2)*0.5+0.5
            c.set_pixel(x, y, ' ', bg=col.mul(0.8+0.2*caustic), z=-100)

    # At least 1: int(w * 0.08) is 0 for any canvas narrower than 13
    # columns, and the Gaussian below divides by this.
    light_w = max(1, int(w * 0.08))
    for lx in range(w):
        lf = math.exp(-((lx-w/2)/light_w)**2) * 0.3
        for ly in range(int(h*0.15)):
            flicker = 0.5+0.5*math.sin(t*2+lx*0.5)
            if 0 <= ly < h:
                c.set_pixel(lx, ly, ' ', bg=Color(180, 220, 255).mul(lf*flicker*0.5), z=1)

    for c_ in s['coral']:
        cx_, ch, col = c_['x'], c_['h'], c_['col']
        for dy in range(ch):
            py = h - 2 - dy
            sway = int(math.sin(t*0.8+cx_*0.5+dy*0.3)*1.5)
            px = cx_ + sway
            if 0 <= px < w and 0 <= py < h:
                if dy == ch-1:
                    ch_ = '▲' if ch > 3 else '╿'
                    c.set_pixel(px, py, ch_, col.mul(1.2), z=10)
                elif dy % 2 == 0:
                    c.set_pixel(px, py, '║', col, z=10)
                else:
                    c.set_pixel(px, py, '▒', col.mul(0.8), z=10)

    for f in s['fish']:
        f['x'] += f['vx'] * dt * 20
        f['y'] += f['vy'] * dt * 15
        if f['x'] < -5: f['x'] = w+5; f['vx'] = abs(f['vx'])
        if f['x'] > w+5: f['x'] = -5; f['vx'] = -abs(f['vx'])
        f['y'] = max(h*0.1, min(h*0.75, f['y']))
        if f['y'] < h*0.12 or f['y'] > h*0.73:
            f['vy'] *= -1
        px, py = int(f['x']), int(f['y'])
        if 0 <= px < w and 0 <= py < h:
            size = int(f['size'])
            tail = int(math.sin(t*4+f['tail_phase'])*1.5)
            col = Color.from_hsv(f['hue']+t*0.01, 0.8, 0.8)
            for dx in range(-size, size+1):
                for dy_ in range(-max(1,size//2), max(1,size//2)+1):
                    d = math.hypot(dx, dy_)
                    if d <= size:
                        pp = px+dx+tail
                        if 0 <= pp < w and 0 <= py+dy_ < h:
                            ch = '█' if d < size-0.5 else '▒'
                            c.set_pixel(pp, py+dy_, ch, col.mul(1-d/size*0.3), z=15)
            if 0 <= px-size-1 < w:
                c.set_pixel(px-size-1, py, '>', col, z=15)

    for b in s['bubbles']:
        b['y'] -= b['speed'] * dt * 20
        b['x'] += math.sin(t*2+b['sway']) * 0.3 * dt * 10
        if b['y'] < -2:
            b['y'] = h+2
            b['x'] = random.uniform(5, w-5)
        px, py = int(b['x']), int(b['y'])
        if 0 <= px < w and 0 <= py < h:
            if b['size'] == 0:
                c.set_pixel(px, py, '○', Color(200, 220, 255).mul(0.6), z=20)
            elif b['size'] == 1:
                c.set_pixel(px, py, '○', Color(200, 220, 255).mul(0.5), z=20)
            else:
                c.set_pixel(px, py, '〇', Color(200, 230, 255).mul(0.4), z=20)
