import math, random
from spore_engine import *
from spore_engine.core.color import *

_GRAV = None

class GravBody:
    def __init__(self, x, y, vx, vy, mass, color, name=''):
        self.x = x; self.y = y
        self.vx = vx; self.vy = vy
        self.mass = mass
        self.color = color
        self.name = name
        self.trail = [(x, y)]

def scene_gravity(c, hr, t, pt, dt):
    global _GRAV
    w, h = c.w, c.h

    if _GRAV is None:
        bodies = []
        cx, cy = w / 2, h / 2

        sun = GravBody(cx, cy, 0, 0, 5000, Color(255, 200, 50), 'SUN')
        bodies.append(sun)

        orbits = [
            (3, 3.5, 1.5, Color(180, 180, 200), 'Mercury'),
            (5, 2.2, 2.8, Color(220, 180, 120), 'Venus'),
            (7, 1.8, 3.5, Color(100, 180, 255), 'Earth'),
            (9, 1.5, 4.2, Color(255, 100, 50), 'Mars'),
            (12, 1.0, 5.5, Color(200, 180, 100), 'Jupiter'),
        ]
        for dist, speed, mass, color, name in orbits:
            angle = random.random() * 2 * math.pi
            px = cx + dist * math.cos(angle)
            py = cy + dist * math.sin(angle)
            vx = -speed * math.sin(angle)
            vy = speed * math.cos(angle)
            bodies.append(GravBody(px, py, vx, vy, mass * 3, color, name))

        for _ in range(30):
            angle = random.random() * 2 * math.pi
            dist = 2 + random.random() * 14
            px = cx + dist * math.cos(angle)
            py = cy + dist * math.sin(angle)
            orb_speed = math.sqrt(5000 * 0.5 / max(0.5, dist))
            vx = -orb_speed * math.sin(angle) + (random.random()-0.5)*0.2
            vy = orb_speed * math.cos(angle) + (random.random()-0.5)*0.2
            col = Color.from_hsv(random.random(), 0.8, 0.7 + 0.3*random.random())
            bodies.append(GravBody(px, py, vx, vy, 0.5 + random.random(), col))

        _GRAV = {'bodies': bodies, 'time': 0}

    s = _GRAV
    s['time'] += dt
    bodies = s['bodies']
    sub = 6

    for _ in range(sub):
        dt_sub = dt / sub
        for b in bodies:
            ax, ay = 0, 0
            for other in bodies:
                if other is b: continue
                dx = other.x - b.x
                dy = other.y - b.y
                dist = math.hypot(dx, dy) + 0.3
                force = other.mass * 1.5 / (dist * dist)
                ax += force * dx / dist
                ay += force * dy / dist
            b.vx += ax * dt_sub
            b.vy += ay * dt_sub

    for b in bodies:
        b.x += b.vx * dt
        b.y += b.vy * dt

    for y in range(h):
        ty = y / h
        for x in range(w):
            n = (math.sin(x*0.015+t*0.08)+math.cos(y*0.02+t*0.06))*0.5+0.5
            c.set_pixel(x, y, ' ', bg=Color(int(1+n*3), int(1+n*2), int(3+n*8)), z=-100)

    sun = bodies[0]
    for r in range(6, 0, -1):
        alpha = 0.4 * (1 - r/6)
        for dx in range(-r, r+1):
            for dy in range(-r, r+1):
                if math.hypot(dx, dy) <= r:
                    px, py = int(sun.x+dx), int(sun.y+dy)
                    if 0 <= px < w and 0 <= py < h:
                        c.set_pixel(px, py, ' ', bg=Color(255, 200, 50).mul(alpha), z=1)

    sun_px, sun_py = int(sun.x), int(sun.y)
    if 0 <= sun_px < w and 0 <= sun_py < h:
        for dx in range(-3, 4):
            for dy in range(-3, 4):
                d = math.hypot(dx, dy)
                if d <= 3:
                    px, py = sun_px+dx, sun_py+dy
                    if 0 <= px < w and 0 <= py < h:
                        b = 1.0 - d/3
                        c.set_pixel(px, py, '█' if d<1.5 else '░',
                                   Color.from_hsv(0.1, 0.8, 0.6+0.4*b), z=5)

    for b in bodies[1:]:
        for i, (tx, ty) in enumerate(b.trail[:-1]):
            alpha = i / max(1, len(b.trail))
            px, py = int(tx), int(ty)
            if 0 <= px < w and 0 <= py < h:
                c.set_pixel(px, py, '·', b.color.mul(alpha*0.6), z=3)

    for b in bodies[1:]:
        px, py = int(b.x), int(b.y)
        if 0 <= px < w and 0 <= py < h:
            size = max(1, min(3, int(b.mass / 2)))
            ch = '●' if size > 2 else ('○' if size > 1 else '·')
            c.set_pixel(px, py, ch, b.color, z=10)
            if size > 1:
                for dx, dy in [(-1,0),(1,0),(0,-1),(0,1)]:
                    if 0 <= px+dx < w and 0 <= py+dy < h:
                        c.set_pixel(px+dx, py+dy, '·', b.color.mul(0.4), z=8)

        if len(b.trail) == 0 or math.hypot(b.x-b.trail[-1][0], b.y-b.trail[-1][1]) > 0.3:
            b.trail.append((b.x, b.y))
        if len(b.trail) > 60:
            b.trail.pop(0)
