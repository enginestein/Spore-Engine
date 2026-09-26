from __future__ import annotations
import math
import random
from ..core.canvas import Canvas
from ..core.color import Color


class FieldSource:
    def __init__(self, x: float, y: float, strength: float = 1.0,
                 kind: str = 'vortex', radius: float = 20):
        self.x = x
        self.y = y
        self.strength = strength
        self.kind = kind
        self.radius = radius

    def velocity_at(self, px: float, py: float) -> tuple[float, float]:
        dx = px - self.x
        dy = py - self.y
        d = math.hypot(dx, dy)
        if d < 1: return (0, 0)
        if d > self.radius: return (0, 0)
        falloff = 1 - (d / self.radius) ** 2
        s = self.strength * falloff
        if self.kind == 'vortex':
            return (-dy / d * s, dx / d * s)
        elif self.kind == 'sink':
            return (-dx / d * s, -dy / d * s)
        elif self.kind == 'source':
            return (dx / d * s, dy / d * s)
        elif self.kind == 'swirl':
            angle = math.atan2(dy, dx) + d * 0.1
            return (math.cos(angle) * d * 0.01 - dy / d * s,
                    math.sin(angle) * d * 0.01 + dx / d * s)
        return (0, 0)


class VectorField:
    def __init__(self):
        self.sources: list[FieldSource] = []

    def add(self, source: FieldSource):
        self.sources.append(source)

    def velocity_at(self, x: float, y: float) -> tuple[float, float]:
        vx, vy = 0.0, 0.0
        for s in self.sources:
            sx, sy = s.velocity_at(x, y)
            vx += sx
            vy += sy
        return vx, vy


class FieldParticle:
    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y
        self.vx = 0.0
        self.vy = 0.0
        self.trail: list[tuple[int, int]] = []
        self.hue = random.uniform(0.5, 0.9)
        self.phase = random.uniform(0, 2 * math.pi)
        self.life = random.uniform(0.5, 1.0)
        self.age = 0.0
        self.trail_max = 40


class FieldSystem:
    def __init__(self, num_particles: int = 100, width: float = 80, height: float = 40):
        self.field = VectorField()
        self.particles = [FieldParticle(
            random.uniform(0, width),
            random.uniform(0, height)
        ) for _ in range(num_particles)]
        self.width = width
        self.height = height

    def update(self, dt: float):
        for p in self.particles:
            vx, vy = self.field.velocity_at(p.x, p.y)
            p.vx += (vx - p.vx) * dt * 4
            p.vy += (vy - p.vy) * dt * 4
            p.x += p.vx * dt * 8
            p.y += p.vy * dt * 8
            p.age += dt
            px, py = int(p.x), int(p.y)
            p.trail.append((px, py))
            if len(p.trail) > p.trail_max:
                p.trail.pop(0)
            margin = 5
            if p.x < -margin or p.x > self.width + margin or \
               p.y < -margin or p.y > self.height + margin or \
               p.age > p.life * 8:
                p.x = random.uniform(0, self.width)
                p.y = random.uniform(0, self.height)
                p.vx = 0
                p.vy = 0
                p.age = 0
                p.trail = []
                p.hue = random.uniform(0.5, 0.9)

    def render(self, c: Canvas, t: float):
        for p in self.particles:
            for i, (tx, ty) in enumerate(p.trail):
                if 0 <= tx < c.w and 0 <= ty < c.h:
                    prog = i / len(p.trail)
                    bright = prog * 0.45
                    if bright > 0.02:
                        hue = (p.hue + prog * 0.15 + t * 0.005) % 1.0
                        col = Color.from_hsv(hue, 0.65, bright)
                        ch = '·' if prog < 0.3 else ('░' if prog < 0.6 else '▒')
                        c.set_pixel(tx, ty, ch, col, z=5)
            px, py = int(p.x), int(p.y)
            if 0 <= px < c.w and 0 <= py < c.h:
                hue = (p.hue + t * 0.01) % 1.0
                col = Color.from_hsv(hue, 0.85, 0.9)
                c.set_pixel(px, py, '○', col, z=10)
