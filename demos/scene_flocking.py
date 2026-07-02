import math, random
from spore_engine import *
from spore_engine.core.color import *

_FL = None

def scene_flocking(c, hr, t, pt, dt):
    global _FL
    w, h = c.w, c.h

    if _FL is None:
        boids = []
        for _ in range(40):
            boids.append({
                'x': random.uniform(w * 0.1, w * 0.9),
                'y': random.uniform(h * 0.1, h * 0.9),
                'vx': random.uniform(-0.5, 0.5),
                'vy': random.uniform(-0.5, 0.5),
                'hue': random.uniform(0.5, 0.9),
                'phase': random.uniform(0, 2*math.pi),
            })
        _FL = {'boids': boids,
               'perception': 12.0,
               'separation_dist': 4.0,
               'max_force': 0.05,
               'max_speed': 1.5}

    s = _FL

    for y in range(h):
        ty = y / h
        col = Color(int(ty * 5), int(ty * 8), int(ty * 15 + 3))
        for x in range(w):
            c.set_pixel(x, y, ' ', bg=col, z=-100)

    boids = s['boids']
    p_rad = s['perception']
    sep_dist = s['separation_dist']
    max_force = s['max_force']
    max_speed = s['max_speed']

    for b in boids:
        steer_x, steer_y = 0.0, 0.0
        align_x, align_y = 0.0, 0.0
        cohesion_x, cohesion_y = 0.0, 0.0
        total = 0

        for other in boids:
            if other is b: continue
            dx = other['x'] - b['x']
            dy = other['y'] - b['y']
            d = math.hypot(dx, dy)
            if d < p_rad and d > 0:
                if d < sep_dist:
                    steer_x -= dx / d * 2.0
                    steer_y -= dy / d * 2.0
                align_x += other['vx']
                align_y += other['vy']
                cohesion_x += other['x']
                cohesion_y += other['y']
                total += 1

        if total > 0:
            align_x = align_x / total - b['vx']
            align_y = align_y / total - b['vy']
            a_mag = math.hypot(align_x, align_y)
            if a_mag > 0:
                align_x = align_x / a_mag * max_force * 0.8
                align_y = align_y / a_mag * max_force * 0.8

            cohesion_x = cohesion_x / total - b['x']
            cohesion_y = cohesion_y / total - b['y']
            c_mag = math.hypot(cohesion_x, cohesion_y)
            if c_mag > 0:
                cohesion_x = cohesion_x / c_mag * max_force * 0.5
                cohesion_y = cohesion_y / c_mag * max_force * 0.5

        s_mag = math.hypot(steer_x, steer_y)
        if s_mag > 0:
            steer_x = steer_x / s_mag * max_force * 2.0
            steer_y = steer_y / s_mag * max_force * 2.0

        b['vx'] += steer_x + align_x + cohesion_x
        b['vy'] += steer_y + align_y + cohesion_y

        speed = math.hypot(b['vx'], b['vy'])
        if speed > max_speed:
            b['vx'] = b['vx'] / speed * max_speed
            b['vy'] = b['vy'] / speed * max_speed

        b['x'] += b['vx'] * dt * 8
        b['y'] += b['vy'] * dt * 8

        margin = 4
        if b['x'] < -margin: b['x'] = w + margin
        elif b['x'] > w + margin: b['x'] = -margin
        if b['y'] < -margin: b['y'] = h + margin
        elif b['y'] > h + margin: b['y'] = -margin

        px, py2 = int(b['x']), int(b['y'])
        if 0 <= px < w and 0 <= py2 < h:
            angle = math.atan2(b['vy'], b['vx'])
            hue = (b['hue'] + t * 0.01) % 1.0
            speed_norm = speed / max_speed
            bright = 0.4 + speed_norm * 0.6
            col = Color.from_hsv(hue, 0.8, bright)

            if abs(b['vx']) > 0.1 or abs(b['vy']) > 0.1:
                if angle > -math.pi * 0.75 and angle < -math.pi * 0.25:
                    c.set_pixel(px, py2, '▲', col, z=10)
                    c.set_pixel(px - 1, py2 + 1, '/', col.mul(0.6), z=9)
                    c.set_pixel(px + 1, py2 + 1, '\\', col.mul(0.6), z=9)
                elif angle > math.pi * 0.25 and angle < math.pi * 0.75:
                    c.set_pixel(px, py2, '▼', col, z=10)
                    c.set_pixel(px - 1, py2 - 1, '\\', col.mul(0.6), z=9)
                    c.set_pixel(px + 1, py2 - 1, '/', col.mul(0.6), z=9)
                elif angle > -math.pi * 0.25 and angle < math.pi * 0.25:
                    c.set_pixel(px, py2, '▶', col, z=10)
                    c.set_pixel(px - 1, py2 - 1, '\\', col.mul(0.6), z=9)
                    c.set_pixel(px - 1, py2 + 1, '/', col.mul(0.6), z=9)
                else:
                    c.set_pixel(px, py2, '◀', col, z=10)
                    c.set_pixel(px + 1, py2 - 1, '/', col.mul(0.6), z=9)
                    c.set_pixel(px + 1, py2 + 1, '\\', col.mul(0.6), z=9)

            glow_r = 2
            for gx in range(-glow_r, glow_r + 1):
                for gy2 in range(-glow_r, glow_r + 1):
                    gd = math.hypot(gx, gy2)
                    if gd <= glow_r:
                        px2, py3 = px + gx, py2 + gy2
                        if 0 <= px2 < w and 0 <= py3 < h:
                            a = (1 - gd / glow_r) * bright * 0.15
                            if a > 0.02:
                                c.set_pixel(px2, py3, ' ', bg=col.mul(a * 0.3), z=5)
