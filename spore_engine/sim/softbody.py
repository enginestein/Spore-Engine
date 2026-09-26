from __future__ import annotations
import math
from ..core.canvas import Canvas, SHADE_CHARS
from ..core.color import Color
from ..sim.physics import Vec2, _sanitize


class SoftBody:
    __slots__ = (
        '_vel',
        'base_volume',
        'color',
        'damping',
        'gravity',
        'links',
        'nodes',
        'pressure_k',
        'pressures',
    )
    def __init__(self, pos: Vec2 = Vec2(), color: Color | None = None):
        self.nodes: list[Vec2] = []
        self.links: list[tuple[int, int, float, float]] = []  # (i, j, rest, stiffness)
        self.pressures: list[tuple[list[int], float]] = []
        self.color = color or Color(100, 200, 255)
        self.base_volume = 0
        self.pressure_k = 50
        self.damping = 0.98
        self.gravity = 9.8

    def add_node(self, x: float, y: float) -> int:
        idx = len(self.nodes)
        self.nodes.append(Vec2(x, y))
        return idx

    def add_link(self, i: int, j: int, stiffness: float = 100):
        rest = self.nodes[i].dist(self.nodes[j])
        self.links.append((i, j, rest, stiffness))

    def add_pressure(self, indices: list[int]):
        vol = self._compute_volume(indices)
        self.pressures.append((indices, vol))

    def _compute_volume(self, indices: list[int]) -> float:
        if len(indices) < 3:
            return 0
        vol = 0
        for k in range(len(indices)):
            a = self.nodes[indices[k]]
            b = self.nodes[indices[(k + 1) % len(indices)]]
            vol += a.x * b.y - b.x * a.y
        return abs(vol) / 2

    @staticmethod
    def circle(cx: float, cy: float, radius: float, segments: int = 12,
               color: Color | None = None, stiffness: float = 200,
               pressure: float = 80) -> SoftBody:
        sb = SoftBody(Vec2(cx, cy), color)
        sb.pressure_k = pressure
        for i in range(segments):
            a = 2 * math.pi * i / segments
            sb.add_node(cx + radius * math.cos(a), cy + radius * math.sin(a))
        for i in range(segments):
            sb.add_link(i, (i + 1) % segments, stiffness)
            sb.add_link(i, (i + segments // 2) % segments, stiffness * 0.5)
        for i in range(segments):
            for j in range(2, segments - 1):
                sb.add_link(i, (i + j) % segments, stiffness * 0.3)
        sb.add_pressure(list(range(segments)))
        return sb

    @staticmethod
    def blob(cx: float, cy: float, size: float = 3,
             color: Color | None = None) -> SoftBody:
        nodes = [
            (cx, cy - size), (cx + size * 0.7, cy - size * 0.5),
            (cx + size, cy), (cx + size * 0.7, cy + size * 0.5),
            (cx, cy + size), (cx - size * 0.7, cy + size * 0.5),
            (cx - size, cy), (cx - size * 0.7, cy - size * 0.5),
        ]
        sb = SoftBody(Vec2(cx, cy), color)
        for x, y in nodes:
            sb.add_node(x, y)
        links = [(0,1),(1,2),(2,3),(3,4),(4,5),(5,6),(6,7),(7,0),
                 (0,2),(2,4),(4,6),(6,0),(1,3),(3,5),(5,7),(7,1)]
        for i, j in links:
            sb.add_link(i, j, 120)
        sb.add_pressure(list(range(8)))
        sb.pressure_k = 60
        return sb

    @staticmethod
    def square(x: float, y: float, w: float, h: float,
               color: Color | None = None) -> SoftBody:
        sb = SoftBody(Vec2(x + w / 2, y + h / 2), color)
        sb.add_node(x, y)
        sb.add_node(x + w, y)
        sb.add_node(x + w, y + h)
        sb.add_node(x, y + h)
        sb.add_link(0, 1, 150)
        sb.add_link(1, 2, 150)
        sb.add_link(2, 3, 150)
        sb.add_link(3, 0, 150)
        sb.add_link(0, 2, 100)
        sb.add_link(1, 3, 100)
        sb.add_pressure([0, 1, 2, 3])
        sb.pressure_k = 70
        return sb

    def update(self, dt: float, bounds_x: int = 0, bounds_y: int = 0):
        if not hasattr(self, '_vel') or len(self._vel) != len(self.nodes):
            self._vel = [Vec2() for _ in self.nodes]

        for i in range(len(self.nodes)):
            self._vel[i].y += self.gravity * dt
            self._vel[i] = self._vel[i] * (1 - self.damping * dt)
            if abs(self._vel[i].x) > 15: self._vel[i].x *= 0.9
            if abs(self._vel[i].y) > 15: self._vel[i].y *= 0.9
            self.nodes[i] = self.nodes[i] + self._vel[i]

        for _ in range(3):
            for i, j, rest, stiff in self.links:
                a, b = self.nodes[i], self.nodes[j]
                delta = b - a
                d = delta.length()
                if d < 0.001:
                    continue
                alpha = min(stiff * dt, 0.25)
                correction = delta * (d - rest) * alpha / (d + 0.001)
                self.nodes[i] = self.nodes[i] + correction * 0.5
                self.nodes[j] = self.nodes[j] - correction * 0.5

            for indices, base_vol in self.pressures:
                vol = abs(self._compute_volume(indices))
                if vol < 0.01:
                    continue
                normals = []
                total_grad_sq = 0.0
                for k in range(len(indices)):
                    a = self.nodes[indices[k]]
                    b = self.nodes[indices[(k + 1) % len(indices)]]
                    c = self.nodes[indices[(k - 1) % len(indices)]]
                    edge1 = b - a
                    edge2 = c - a
                    normal = Vec2(edge1.y - edge2.y, -(edge1.x - edge2.x)) * 0.5
                    normals.append(normal)
                    total_grad_sq += normal.length_sq()
                if total_grad_sq < 0.001:
                    continue
                lambda_ = (base_vol - vol) * self.pressure_k * dt / total_grad_sq
                lambda_ = max(-0.5, min(0.5, lambda_))
                for k in range(len(indices)):
                    self.nodes[indices[k]] = self.nodes[indices[k]] + normals[k] * lambda_

        for i in range(len(self.nodes)):
            self.nodes[i].x = _sanitize(self.nodes[i].x)
            self.nodes[i].y = _sanitize(self.nodes[i].y)

            for j in range(i + 1, len(self.nodes)):
                delta = self.nodes[j] - self.nodes[i]
                d = delta.length()
                if d < 0.5 and d > 0.001:
                    repel = delta * (0.5 - d) / d * 5 * dt
                    self.nodes[i] = self.nodes[i] - repel
                    self.nodes[j] = self.nodes[j] + repel

        if bounds_x > 0:
            for i, n in enumerate(self.nodes):
                if n.x < 1:
                    self._vel[i].x = -self._vel[i].x * 0.4
                    self.nodes[i].x = 1
                if n.x >= bounds_x - 1:
                    self._vel[i].x = -self._vel[i].x * 0.4
                    self.nodes[i].x = bounds_x - 2
        if bounds_y > 0:
            for i, n in enumerate(self.nodes):
                if n.y < 1:
                    self._vel[i].y = -self._vel[i].y * 0.4
                    self.nodes[i].y = 1
                if n.y >= bounds_y - 1:
                    self._vel[i].y = -self._vel[i].y * 0.4
                    self.nodes[i].y = bounds_y - 2

    def render(self, canvas: Canvas, ox: int = 0, oy: int = 0):
        for indices, _ in self.pressures:
            if len(indices) >= 3:
                ys = [self.nodes[i].y + oy for i in indices]
                min_y, max_y = int(min(ys)), int(max(ys))
                for iy in range(max(0, min_y), min(canvas.h, max_y + 1)):
                    xs = []
                    n = len(indices)
                    for k in range(n):
                        a = self.nodes[indices[k]]
                        b = self.nodes[indices[(k + 1) % n]]
                        x1, y1 = int(a.x) + ox, int(a.y) + oy
                        x2, y2 = int(b.x) + ox, int(b.y) + oy
                        if y1 == y2:
                            if y1 == iy:
                                xs.append(x1); xs.append(x2)
                            continue
                        if (y1 <= iy < y2) or (y2 <= iy < y1):
                            t = (iy - y1) / (y2 - y1) if (y2 - y1) != 0 else 0
                            xs.append(x1 + int(t * (x2 - x1)))
                    if len(xs) >= 2:
                        xs.sort()
                        for k in range(0, len(xs) - 1, 2):
                            for ix in range(max(0, xs[k]), min(canvas.w, xs[k + 1] + 1)):
                                dist = abs(iy - (min_y + max_y) / 2)
                                depth = max(0, 1 - dist / ((max_y - min_y) / 2 + 1))
                                ci = min(9, max(0, int(depth * 9)))
                                canvas.set_pixel(ix, iy, SHADE_CHARS[ci], self.color, z=1)
        for i, j, _, _ in self.links:
            a = self.nodes[i]
            b = self.nodes[j]
            canvas.draw_line(
                int(a.x) + ox, int(a.y) + oy,
                int(b.x) + ox, int(b.y) + oy,
                '.', self.color.mul(0.6), z=2,
            )
        for n in self.nodes:
            canvas.set_pixel(int(n.x) + ox, int(n.y) + oy, '●', self.color, z=3)


class SoftBodyWorld:
    def __init__(self, bounds_x: int = 80, bounds_y: int = 40):
        self.bodies: list[SoftBody] = []
        self.bounds_x = bounds_x
        self.bounds_y = bounds_y

    def add(self, body: SoftBody):
        self.bodies.append(body)

    def step(self, dt: float):
        for body in self.bodies:
            body.update(dt, self.bounds_x, self.bounds_y)

    def render(self, canvas: Canvas, ox: int = 0, oy: int = 0):
        for body in self.bodies:
            body.render(canvas, ox, oy)
