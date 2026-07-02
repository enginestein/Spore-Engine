import math, random
from spore_engine import *
from spore_engine.core.color import *

_CT = None

def scene_celestial_temple(c, hr, t, pt, dt):
    global _CT
    w, h = c.w, c.h

    if _CT is None:
        clouds = []
        for _ in range(15):
            clouds.append({
                'x': random.uniform(-w*0.2, w*1.2), 'y': random.uniform(h*0.05, h*0.25),
                'w': random.uniform(8, 20), 'vx': random.uniform(0.2, 0.8),
                'phase': random.uniform(0, 2*math.pi),
                'hue': random.uniform(0.0, 0.08),
            })
        floating_particles = []
        for _ in range(25):
            floating_particles.append({
                'x': random.uniform(0, w), 'y': random.uniform(0, h),
                'vx': random.uniform(-0.2, 0.2), 'vy': random.uniform(-0.3, -0.1),
                'phase': random.uniform(0, 2*math.pi),
            })
        _CT = {'clouds': clouds, 'particles': floating_particles}

    s = _CT

    for y in range(h):
        ty = y / h
        if ty < 0.6:
            hue = 0.08 - ty * 0.08
            sat = 0.2 + ty * 0.3
            bright = 0.05 + 0.45 * (1 - ty)
        else:
            t2 = (ty - 0.6) / 0.4
            hue = 0.04 + t2 * 0.03
            sat = 0.3 + t2 * 0.2
            bright = 0.2 * (1 - t2 * 0.5)
        col = Color.from_hsv(max(0, hue), min(1, sat), max(0.02, bright))
        for x in range(w):
            c.set_pixel(x, y, ' ', bg=col, z=-100)

    for cld in s['clouds']:
        cld['x'] += cld['vx'] * dt * 8
        if cld['x'] > w*1.2: cld['x'] = -cld['w']
        for dy in range(3):
            for dx in range(int(cld['w'])):
                px = int(cld['x']) + dx - int(cld['w']/2)
                py = int(cld['y']) + dy
                d = abs(dx - cld['w']/2) / (cld['w']/2)
                if d < 1 and 0 <= px < w and 0 <= py < h:
                    a = 1 - d
                    col = Color.from_hsv(cld['hue'], 0.3, 0.2+a*0.5)
                    c.set_pixel(px, py, '█', col, z=6)

    temple_base = int(h * 0.55)
    temple_cx = w // 2
    for y in range(temple_base, h):
        for x in range(w):
            dist_from_center = abs(x - temple_cx)
            width = int(20 + (h-1-y) * 0.5)
            if dist_from_center <= width:
                if y == temple_base:
                    c.set_pixel(x, y, '▄', Color(180, 170, 140), z=8)
                elif x == temple_cx - width or x == temple_cx + width:
                    c.set_pixel(x, y, '║', Color(160, 150, 120), z=8)
                elif abs(x - temple_cx) <= 2:
                    c.set_pixel(x, y, '║', Color(180, 170, 140), z=8)
                elif dist_from_center < width - 1:
                    col = Color(int(100+(h-1-y)*4), int(95+(h-1-y)*3), int(80+(h-1-y)*2))
                    c.set_pixel(x, y, '█', col, z=8)

    columns = [temple_cx - 12, temple_cx - 4, temple_cx + 4, temple_cx + 12]
    col_h = 12
    for col_x in columns:
        for dy in range(col_h):
            y = temple_base - dy
            if y >= 0:
                if 0 <= col_x < w and y < h:
                    c.set_pixel(col_x, y, '║', Color(180, 170, 140), z=10)
                if 0 <= col_x+1 < w and y < h:
                    c.set_pixel(col_x+1, y, '▓', Color(140, 130, 100), z=10)

    pediment_y = temple_base - col_h
    for dx in range(-18, 19):
        px = temple_cx + dx
        if 0 <= px < w and 0 <= pediment_y < h:
            if abs(dx) == 18:
                c.set_pixel(px, pediment_y, '║', Color(180, 170, 140), z=11)
            elif abs(dx) < 18 and pediment_y >= 0:
                c.set_pixel(px, pediment_y, '▀', Color(180, 170, 140), z=11)
        if 0 <= px < w and pediment_y-1 >= 0 and pediment_y-1 < h:
            slope = 18 - abs(dx)
            if slope > 10:
                c.set_pixel(px, pediment_y-1, '▲', Color(180, 170, 140), z=12)

    light_count = 7
    for i in range(light_count):
        a = (i / light_count) * 2 * math.pi + t * 0.1
        bx = temple_cx + int(25 * math.cos(a))
        by = temple_base - 20 + int(15 * math.sin(a))
        for r in range(3, 10):
            for ang in range(0, 360, 30):
                rad = r * 0.5
                lx = bx + int(rad * math.cos(ang*math.pi/180))
                ly = by + int(rad * math.sin(ang*math.pi/180))
                if 0 <= lx < w and 0 <= ly < h:
                    col = Color.from_hsv((i/light_count + t*0.01) % 1.0, 0.7, 0.3*(1-r/10))
                    c.set_pixel(lx, ly, '·', col, z=14)

    for p in s['particles']:
        p['x'] += p['vx'] * dt * 5 + math.sin(t*0.5+p['phase'])*0.2
        p['y'] += p['vy'] * dt * 5
        if p['y'] < -5: p['y'] = h+5
        if p['x'] < -5: p['x'] = w+5
        if p['x'] > w+5: p['x'] = -5
        px, py = int(p['x']), int(p['y'])
        if 0 <= px < w and 0 <= py < h:
            pulse = 0.3+0.7*(0.5+0.5*math.sin(t+px*0.5+p['phase']))
            c.set_pixel(px, py, '·', Color(255, 240, 200).mul(pulse*0.4), z=16)
