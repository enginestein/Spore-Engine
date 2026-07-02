from __future__ import annotations
import math
import random
from typing import Optional
from ..core.color import Color, Gradient, PALETTES
from ..core.canvas import Canvas, SHADE_CHARS


_SHADE = SHADE_CHARS


class Particle:
    def __init__(self, x: float, y: float, vx: float, vy: float,
                 life: float, max_life: float, color: Color,
                 size: float = 1.0, drag: float = 0.95, gravity: float = 2.5):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.life = life
        self.max_life = max_life
        self.color = color
        self.size = size
        self.drag = drag
        self.gravity = gravity
        self.start_color = color
        self.trail: list[tuple[float, float]] = []

    @property
    def alpha(self) -> float:
        return max(0, self.life / self.max_life)

    @property
    def dead(self) -> bool:
        return self.life <= 0

    def update(self, dt: float):
        self.trail.append((self.x, self.y))
        if len(self.trail) > 5:
            self.trail.pop(0)
        self.vy += self.gravity * dt
        self.vx *= self.drag
        self.vy *= self.drag
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.life -= dt

    def render(self, canvas: Canvas, z: float = 0):
        if self.dead:
            return
        a = self.alpha
        ci = min(len(_SHADE)-1, int(a * 9))
        col = self.start_color.mul(a)
        sx, sy = round(self.x), round(self.y)
        canvas.set_pixel(sx, sy, _SHADE[ci], col, z=z)
        
        # Render trail with fading
        for i, (tx, ty) in enumerate(self.trail):
            ta = a * (i / len(self.trail)) * 0.4
            if ta > 0.02:
                canvas.set_pixel(round(tx), round(ty), '.', self.start_color.mul(ta), z=z)


class Emitter:
    def __init__(self, x: float = 0, y: float = 0, max_particles: int = 100):
        self.x = x
        self.y = y
        self.max_particles = max_particles
        self.particles: list[Particle] = []
        self.active = True
        self.rate = 10
        self._timer = 0.0
        self._spawn_count = 1

    def set_rate(self, rate: int):
        self.rate = rate
        return self

    def set_spawn_count(self, count: int):
        self._spawn_count = count
        return self

    def _spawn(self, count: int):
        pass

    def update(self, dt: float, gravity: float = 2.0):
        if self.active and self.rate > 0:
            self._timer += dt
            interval = 1.0 / self.rate
            while self._timer >= interval:
                self._timer -= interval
                self._spawn(self._spawn_count)
        self.particles = [p for p in self.particles if not p.dead]
        if len(self.particles) > self.max_particles:
            self.particles = self.particles[-self.max_particles:]
        for p in self.particles:
            p.update(dt)

    def render(self, canvas: Canvas, z: float = 0):
        for p in self.particles:
            p.render(canvas, z)


class FountainEmitter(Emitter):
    def __init__(self, x: float, y: float, max_particles: int = 150,
                 colors: Optional[list[Color]] = None):
        super().__init__(x, y, max_particles)
        self.colors = colors or [Color(200, 220, 255), Color(180, 200, 255),
                                 Color(150, 180, 255), Color(255, 255, 255)]
        self.set_rate(20)

    def _spawn(self, count: int):
        for _ in range(count):
            angle = random.uniform(-math.pi * 0.8, -math.pi * 0.2)
            speed = random.uniform(2, 5)
            life = random.uniform(0.8, 2.0)
            color = random.choice(self.colors)
            self.particles.append(Particle(
                self.x, self.y,
                math.cos(angle) * speed,
                math.sin(angle) * speed,
                life, life, color
            ))


class StreamEmitter(Emitter):
    def __init__(self, x: float, y: float, angle: float = -math.pi / 2,
                 max_particles: int = 80, colors: Optional[list[Color]] = None):
        super().__init__(x, y, max_particles)
        self.angle = angle
        self.spread = 0.3
        self.speed = 4.0
        self.colors = colors or [Color(255, 200, 100), Color(255, 180, 80)]
        self.set_rate(15)

    def _spawn(self, count: int):
        for _ in range(count):
            a = self.angle + random.uniform(-self.spread, self.spread)
            s = self.speed * random.uniform(0.8, 1.2)
            life = random.uniform(0.5, 1.5)
            color = random.choice(self.colors)
            self.particles.append(Particle(
                self.x, self.y,
                math.cos(a) * s, math.sin(a) * s,
                life, life, color
            ))


class FireEmitter(Emitter):
    def __init__(self, x: float, y: float, max_particles: int = 60):
        super().__init__(x, y, max_particles)
        self.colors = [Color(255, 200, 50), Color(255, 150, 30),
                       Color(255, 80, 20), Color(200, 40, 10)]
        self.set_rate(25)

    def _spawn(self, count: int):
        for _ in range(count):
            vx = random.uniform(-0.5, 0.5)
            vy = -random.uniform(1, 4)
            life = random.uniform(0.3, 1.0)
            color = random.choice(self.colors)
            p = Particle(self.x, self.y, vx, vy, life, life, color)
            self.particles.append(p)


def burst_explosion(cx: float, cy: float, count: int = 40,
                    colors: Optional[list[Color]] = None,
                    speed: float = 4.0) -> list[Particle]:
    colors = colors or PALETTES['fire']
    parts = []
    for _ in range(count):
        angle = random.uniform(0, 2 * math.pi)
        s = speed * random.uniform(0.5, 1.5)
        life = random.uniform(0.5, 2.0)
        p = Particle(cx, cy, math.cos(angle) * s, math.sin(angle) * s,
                     life, life, random.choice(colors))
        parts.append(p)
    return parts


def burst_ring(cx: float, cy: float, count: int = 24,
               color: Color = Color(255, 200, 100),
               speed: float = 3.0) -> list[Particle]:
    parts = []
    for i in range(count):
        angle = 2 * math.pi * i / count
        s = speed * (0.9 + 0.2 * random.random())
        p = Particle(cx, cy, math.cos(angle) * s, math.sin(angle) * s,
                     0.8, 0.8, color)
        parts.append(p)
    return parts


def burst_directional(cx: float, cy: float, angle: float, spread: float = 0.5,
                      count: int = 20, color: Color = Color(255, 200, 100),
                      speed: float = 5.0) -> list[Particle]:
    parts = []
    for _ in range(count):
        a = angle + random.uniform(-spread, spread)
        s = speed * random.uniform(0.7, 1.3)
        life = random.uniform(0.3, 1.0)
        p = Particle(cx, cy, math.cos(a) * s, math.sin(a) * s,
                     life, life, color)
        parts.append(p)
    return parts


def plasma(canvas: Canvas, t: float, ox: int = 0, oy: int = 0,
           w: Optional[int] = None, h: Optional[int] = None,
           palette: str = 'neon', speed: float = 1):
    w = w or canvas.width
    h = h or canvas.height
    grad = Gradient.from_palette(palette)
    for y in range(h):
        for x in range(w):
            v1 = math.sin(x * 0.08 + t * speed * 0.5)
            v2 = math.sin(y * 0.08 + t * speed * 0.3)
            v3 = math.sin((x + y) * 0.06 + t * speed * 0.7)
            v4 = math.sin(math.hypot(x - w // 2, y - h // 2) * 0.06 + t * speed)
            v = (v1 + v2 + v3 + v4) * 0.25
            n = (v + 1) * 0.5
            color = grad.at((n + t * 0.02) % 1.0)
            ci = int(n * 9)
            canvas.set_pixel(x + ox, y + oy, _SHADE[ci], color)


def fire(canvas: Canvas, t: float, buffer: list[list[float]],
         ox: int = 0, oy: int = 0, w: Optional[int] = None, h: Optional[int] = None):
    buf_h = len(buffer)
    buf_w = len(buffer[0]) if buf_h else 0
    w = w or buf_w
    h = h or buf_h

    for x in range(w):
        if random.random() < 0.35:
            buffer[h - 1][x] = random.uniform(0.8, 1.0)
        else:
            buffer[h - 1][x] *= 0.85

    for y in range(h - 2, -1, -1):
        for x in range(w):
            v = (
                buffer[min(h - 1, y + 1)][max(0, x - 1)] * 0.2 +
                buffer[min(h - 1, y + 1)][x] * 0.4 +
                buffer[min(h - 1, y + 1)][min(w - 1, x + 1)] * 0.2 +
                buffer[y][max(0, x - 1)] * 0.05 +
                buffer[y][min(w - 1, x + 1)] * 0.05
            ) * 0.95
            buffer[y][x] = v

    for y in range(h):
        for x in range(w):
            v = buffer[y][x]
            if v < 0.03: continue
            ci = int(v * 10)
            ci = min(len(_SHADE) - 1, ci)
            r = min(255, int(255 * v))
            g = min(255, int(160 * v * v))
            b = min(120, int(50 * v * v * v))
            canvas.set_pixel(x + ox, y + oy, _SHADE[ci], Color(r, g, b))


class Burst:
    def __init__(self, cx: float, cy: float, count: int = 30,
                 colors: Optional[list[Color]] = None):
        self.cx = cx
        self.cy = cy
        self.alive = True
        self.particles: list[Particle] = []
        pal = colors or PALETTES['fire']
        for _ in range(count):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(1.5, 6.0)
            life = random.uniform(0.6, 2.2)
            self.particles.append(Particle(
                cx, cy,
                math.cos(angle) * speed,
                math.sin(angle) * speed,
                life, life, random.choice(pal)
            ))

    def update(self, dt: float):
        for p in self.particles:
            p.update(dt)
        self.particles = [p for p in self.particles if not p.dead]
        self.alive = bool(self.particles)

    def render(self, canvas: Canvas):
        for p in self.particles:
            p.render(canvas)


class ParticleSystem:
    def __init__(self, max_particles: int = 200):
        self.bursts: list[Burst] = []
        self.max = max_particles

    def emit(self, cx: float, cy: float, count: int = 20,
             colors: Optional[list[Color]] = None):
        if len(self.bursts) >= self.max // 20:
            self.bursts.pop(0)
        self.bursts.append(Burst(cx, cy, count, colors))

    def update(self, dt: float):
        self.bursts = [b for b in self.bursts if b.alive]
        for b in self.bursts:
            b.update(dt)

    def render(self, canvas: Canvas):
        for b in self.bursts:
            b.render(canvas)

    def update_and_render(self, canvas: Canvas, dt: float):
        self.update(dt)
        self.render(canvas)


def starfield(canvas: Canvas, t: float, stars: list[list[float]],
              cx: Optional[float] = None, cy: Optional[float] = None,
              speed: float = 1, count: int = 0):
    scx = cx if cx is not None else canvas.width // 2
    scy = cy if cy is not None else canvas.height // 2
    spd = max(0.5, 2 + math.sin(t * 0.3)) * speed

    for star in stars:
        star[2] -= spd * 0.02
        if star[2] < 0.1:
            star[0] = random.uniform(-1, 1) * 30
            star[1] = random.uniform(-1, 1) * 15
            star[2] = 2.0
            continue

        px = int(scx + star[0] / star[2])
        py = int(scy + star[1] / star[2])
        if 0 <= px < canvas.width and 0 <= py < canvas.height:
            b = min(1.0, 0.5 / (star[2] * star[2]))
            val = int(200 + 55 * b)
            canvas.set_pixel(px, py, _SHADE[int(b * 4)], Color(val, val, val))


def matrix_rain(canvas: Canvas, t: float, drops: list[dict]):
    KATA = 'アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワヲン'
    for drop in drops:
        x = drop['x']
        y = drop['y']
        speed = drop['speed']
        length = drop.get('len', drop.get('length', 15))
        
        y_int = int(y)
        for i in range(int(length)):
            dy = y_int - i
            if 0 <= dy < canvas.height:
                # The head is white, the rest is green
                if i == 0:
                    char = KATA[random.randint(0, len(KATA)-1)]
                    canvas.set_pixel(x, dy, char, Color(220, 255, 220))
                else:
                    # Fading green tail
                    alpha = 1.0 - (i / length)
                    g = int(255 * alpha)
                    if random.random() < 0.05: # Occasional character flicker
                        char = KATA[random.randint(0, len(KATA)-1)]
                    else:
                        char = KATA[(x + dy) % len(KATA)]
                    canvas.set_pixel(x, dy, char, Color(0, g, 0))
        
        drop['y'] += speed
        if drop['y'] - length > canvas.height:
            drop['y'] = random.uniform(-length, 0)
            drop['x'] = random.randint(0, canvas.width - 1)
            drop['speed'] = random.uniform(0.4, 1.2)
            drop['len'] = random.randint(8, 25)
            if 'length' in drop: drop['length'] = drop['len']
