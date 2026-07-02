from __future__ import annotations
import math
from typing import Optional
from ..core.canvas import Canvas
from ..core.color import Color, DIM


def _sanitize(v: float, fallback: float = 0) -> float:
    return v if math.isfinite(v) else fallback


GRAVITY = 9.8
DEFAULT_RESTITUTION = 0.6


class Vec2:
    __slots__ = ('x', 'y')
    def __init__(self, x: float = 0, y: float = 0):
        self.x, self.y = x, y
    def __add__(self, o: Vec2) -> Vec2: return Vec2(self.x + o.x, self.y + o.y)
    def __sub__(self, o: Vec2) -> Vec2: return Vec2(self.x - o.x, self.y - o.y)
    def __mul__(self, s: float) -> Vec2: return Vec2(self.x * s, self.y * s)
    def __truediv__(self, s: float) -> Vec2: return Vec2(self.x / s, self.y / s) if s else Vec2()
    def __neg__(self) -> Vec2: return Vec2(-self.x, -self.y)
    def dot(self, o: Vec2) -> float: return self.x * o.x + self.y * o.y
    def length(self) -> float: return math.hypot(self.x, self.y)
    def length_sq(self) -> float: return self.x * self.x + self.y * self.y
    def norm(self) -> Vec2:
        l = self.length()
        return Vec2(self.x / l, self.y / l) if l else Vec2()
    def dist(self, o: Vec2) -> float: return (self - o).length()


class Body:
    __slots__ = ('pos', 'vel', 'mass', 'inv_mass', 'radius', 'color',
                 'restitution', 'friction', 'locked', 'trail', 'trail_len')
    def __init__(self, x: float = 0, y: float = 0, radius: float = 1,
                 mass: float = 1, color: Optional[Color] = None):
        self.pos = Vec2(x, y)
        self.vel = Vec2(0, 0)
        self.mass = mass
        self.inv_mass = 1 / mass if mass > 0 else 0
        self.radius = radius
        self.color = color or Color(200, 200, 200)
        self.restitution = DEFAULT_RESTITUTION
        self.friction = 0.01
        self.locked = False
        self.trail: list[tuple[int, int]] = []
        self.trail_len = 0

    def apply_force(self, fx: float, fy: float):
        if not self.locked:
            self.vel.x += fx * self.inv_mass
            self.vel.y += fy * self.inv_mass

    def update(self, dt: float, gravity: float = GRAVITY, bounds_x: int = 0, bounds_y: int = 0):
        if self.locked:
            return
        self.vel.y += gravity * dt
        self.vel.x *= (1 - self.friction)
        self.pos.x += self.vel.x * dt
        self.pos.y += self.vel.y * dt
        self.pos.x = _sanitize(self.pos.x)
        self.pos.y = _sanitize(self.pos.y)
        self.vel.x = _sanitize(self.vel.x)
        self.vel.y = _sanitize(self.vel.y)
        vel_mag = abs(self.vel.x) + abs(self.vel.y)
        if vel_mag > 500:
            scale = 500 / max(1, vel_mag)
            self.vel.x *= scale
            self.vel.y *= scale
        if bounds_x > 0:
            if self.pos.x - self.radius < 0:
                self.pos.x = self.radius
                self.vel.x = -self.vel.x * self.restitution
            elif self.pos.x + self.radius >= bounds_x:
                self.pos.x = bounds_x - self.radius
                self.vel.x = -self.vel.x * self.restitution
        if bounds_y > 0:
            if self.pos.y - self.radius < 0:
                self.pos.y = self.radius
                self.vel.y = -self.vel.y * self.restitution
            elif self.pos.y + self.radius >= bounds_y:
                self.pos.y = bounds_y - self.radius
                self.vel.y = -self.vel.y * self.restitution

    def overlaps(self, other: Body) -> bool:
        return self.pos.dist(other.pos) < self.radius + other.radius


class AABB:
    __slots__ = ('x', 'y', 'w', 'h')
    def __init__(self, x: float = 0, y: float = 0, w: float = 1, h: float = 1):
        self.x, self.y, self.w, self.h = x, y, w, h

    @property
    def left(self) -> float: return self.x

    @property
    def right(self) -> float: return self.x + self.w

    @property
    def top(self) -> float: return self.y

    @property
    def bottom(self) -> float: return self.y + self.h

    @property
    def cx(self) -> float: return self.x + self.w / 2

    @property
    def cy(self) -> float: return self.y + self.h / 2

    def overlaps(self, other: AABB) -> bool:
        return (self.left < other.right and self.right > other.left
                and self.top < other.bottom and self.bottom > other.top)

    def contains(self, px: float, py: float) -> bool:
        return self.left <= px <= self.right and self.top <= py <= self.bottom

    def expand(self, other: AABB) -> AABB:
        return AABB(min(self.x, other.x), min(self.y, other.y),
                    max(self.right, other.right) - min(self.x, other.x),
                    max(self.bottom, other.bottom) - min(self.y, other.y))


class RectBody:
    __slots__ = ('aabb', 'vel', 'mass', 'inv_mass', 'color',
                 'restitution', 'friction', 'locked')
    def __init__(self, x: float = 0, y: float = 0, w: float = 1, h: float = 1,
                 mass: float = 1, color: Optional[Color] = None):
        self.aabb = AABB(x, y, w, h)
        self.vel = Vec2(0, 0)
        self.mass = mass
        self.inv_mass = 1 / mass if mass > 0 else 0
        self.color = color or Color(180, 180, 200)
        self.restitution = DEFAULT_RESTITUTION
        self.friction = 0.01
        self.locked = False

    def apply_force(self, fx: float, fy: float):
        if not self.locked:
            self.vel.x += fx * self.inv_mass
            self.vel.y += fy * self.inv_mass

    def update(self, dt: float, gravity: float = GRAVITY, bounds: Optional[AABB] = None):
        if self.locked:
            return
        self.vel.y += gravity * dt
        self.vel.x *= (1 - self.friction)
        self.aabb.x += self.vel.x * dt
        self.aabb.y += self.vel.y * dt
        if bounds:
            if self.aabb.x < bounds.x:
                self.aabb.x = bounds.x
                self.vel.x = -self.vel.x * self.restitution
            elif self.aabb.right > bounds.right:
                self.aabb.x = bounds.right - self.aabb.w
                self.vel.x = -self.vel.x * self.restitution
            if self.aabb.y < bounds.y:
                self.aabb.y = bounds.y
                self.vel.y = -self.vel.y * self.restitution
            elif self.aabb.bottom > bounds.bottom:
                self.aabb.y = bounds.bottom - self.aabb.h
                self.vel.y = -self.vel.y * self.restitution

    def render(self, canvas: Canvas, z: float = 0):
        x, y = round(self.aabb.x), round(self.aabb.y)
        w, h = round(self.aabb.w), round(self.aabb.h)
        canvas.draw_rect(x, y, w, h, '#', self.color, z=z)


def resolve_collision(a: Body, b: Body):
    normal = b.pos - a.pos
    dist = normal.length()
    if not math.isfinite(dist) or dist == 0:
        return
    normal = normal * (1 / dist)
    overlap = a.radius + b.radius - dist
    if overlap <= 0:
        return
    if a.inv_mass + b.inv_mass == 0:
        return
    a.pos.x -= normal.x * overlap * (a.inv_mass / (a.inv_mass + b.inv_mass))
    a.pos.y -= normal.y * overlap * (a.inv_mass / (a.inv_mass + b.inv_mass))
    b.pos.x += normal.x * overlap * (b.inv_mass / (a.inv_mass + b.inv_mass))
    b.pos.y += normal.y * overlap * (b.inv_mass / (a.inv_mass + b.inv_mass))
    rel_vel = b.vel - a.vel
    vel_along_normal = rel_vel.dot(normal)
    if vel_along_normal > 0:
        return
    e = min(a.restitution, b.restitution)
    j = -(1 + e) * vel_along_normal / (a.inv_mass + b.inv_mass)
    impulse = normal * j
    a.vel.x -= impulse.x * a.inv_mass
    a.vel.y -= impulse.y * a.inv_mass
    b.vel.x += impulse.x * b.inv_mass
    b.vel.y += impulse.y * b.inv_mass


def resolve_aabb(a: RectBody, b: RectBody):
    if not a.aabb.overlaps(b.aabb):
        return
    if a.inv_mass + b.inv_mass == 0:
        return
    overlap_x = min(a.aabb.right - b.aabb.left, b.aabb.right - a.aabb.left)
    overlap_y = min(a.aabb.bottom - b.aabb.top, b.aabb.bottom - a.aabb.top)
    if overlap_x < overlap_y:
        sign = 1 if a.aabb.cx < b.aabb.cx else -1
        a.aabb.x -= sign * overlap_x * (a.inv_mass / (a.inv_mass + b.inv_mass))
        b.aabb.x += sign * overlap_x * (b.inv_mass / (a.inv_mass + b.inv_mass))
        rel_v = b.vel.x - a.vel.x
        if rel_v > 0: return
        e = min(a.restitution, b.restitution)
        j = -(1 + e) * rel_v / (a.inv_mass + b.inv_mass)
        a.vel.x -= j * a.inv_mass
        b.vel.x += j * b.inv_mass
    else:
        sign = 1 if a.aabb.cy < b.aabb.cy else -1
        a.aabb.y -= sign * overlap_y * (a.inv_mass / (a.inv_mass + b.inv_mass))
        b.aabb.y += sign * overlap_y * (b.inv_mass / (a.inv_mass + b.inv_mass))
        rel_v = b.vel.y - a.vel.y
        if rel_v > 0: return
        e = min(a.restitution, b.restitution)
        j = -(1 + e) * rel_v / (a.inv_mass + b.inv_mass)
        a.vel.y -= j * a.inv_mass
        b.vel.y += j * b.inv_mass


class RayCast:
    def __init__(self, ox: float, oy: float, dx: float, dy: float):
        self.ox = ox
        self.oy = oy
        self.dx = dx
        self.dy = dy
        self.end_x = ox + dx
        self.end_y = oy + dy

    def intersect_circle(self, body: Body) -> Optional[tuple[float, float, float]]:
        fx = self.end_x - self.ox
        fy = self.end_y - self.oy
        cx = body.pos.x - self.ox
        cy = body.pos.y - self.oy
        a = fx * fx + fy * fy
        if a == 0:
            return None
        b = 2 * (cx * fx + cy * fy)
        c = cx * cx + cy * cy - body.radius * body.radius
        disc = b * b - 4 * a * c
        if disc < 0:
            return None
        sqrt_disc = math.sqrt(disc)
        t1 = (-b - sqrt_disc) / (2 * a)
        t2 = (-b + sqrt_disc) / (2 * a)
        t = t1 if 0 <= t1 <= 1 else t2 if 0 <= t2 <= 1 else -1
        if 0 <= t <= 1:
            return (self.ox + fx * t, self.oy + fy * t, t)
        return None

    def render(self, canvas: Canvas, z: float = 0, fg: Optional[Color] = None):
        canvas.draw_line(round(self.ox), round(self.oy),
                         round(self.end_x), round(self.end_y), '.', fg, z=z)


class ForceField:
    def __init__(self, x: float, y: float, w: float, h: float,
                 fx: float = 0, fy: float = 0, strength: float = 1.0,
                 color: Optional[Color] = None):
        self.aabb = AABB(x, y, w, h)
        self.fx = fx
        self.fy = fy
        self.strength = strength
        self.color = color or Color(40, 60, 120)

    def apply_to(self, body: Body):
        if self.aabb.contains(body.pos.x, body.pos.y):
            body.apply_force(self.fx * self.strength, self.fy * self.strength)

    def render(self, canvas: Canvas, z: float = 0):
        x, y = round(self.aabb.x), round(self.aabb.y)
        w, h = round(self.aabb.w), round(self.aabb.h)
        canvas.draw_rect(x, y, w, h, ':', self.color, z=z, fill=False)


class DistanceJoint:
    def __init__(self, a: Body, b: Body, distance: float = -1,
                 stiffness: float = 100):
        self.a = a
        self.b = b
        self.distance = distance if distance > 0 else a.pos.dist(b.pos)
        self.stiffness = stiffness

    def update(self, dt: float):
        delta = self.b.pos - self.a.pos
        dist = delta.length()
        if dist < 0.001 or not math.isfinite(dist):
            return
        diff = dist - self.distance
        if abs(diff) < 0.001:
            return
        dir_vec = delta * (1 / dist)
        correction = dir_vec * diff * self.stiffness * 0.01
        if not self.a.locked:
            self.a.pos.x += correction.x * 0.5
            self.a.pos.y += correction.y * 0.5
        if not self.b.locked:
            self.b.pos.x -= correction.x * 0.5
            self.b.pos.y -= correction.y * 0.5


class Spring:
    __slots__ = ('a', 'b', 'rest_length', 'stiffness', 'damping')
    def __init__(self, a: Body, b: Body, rest_length: float = -1,
                 stiffness: float = 100, damping: float = 2):
        self.a = a
        self.b = b
        self.rest_length = rest_length if rest_length > 0 else a.pos.dist(b.pos)
        self.stiffness = stiffness
        self.damping = damping

    def update(self, dt: float):
        delta = self.b.pos - self.a.pos
        dist = delta.length()
        if not math.isfinite(dist) or dist < 0.001:
            self.a.pos.x = _sanitize(self.a.pos.x)
            self.a.pos.y = _sanitize(self.a.pos.y)
            self.b.pos.x = _sanitize(self.b.pos.x)
            self.b.pos.y = _sanitize(self.b.pos.y)
            return
        direction = delta * (1 / dist)
        displacement = dist - self.rest_length
        force_mag = -self.stiffness * displacement
        rel_vel = self.b.vel - self.a.vel
        damping_force = -self.damping * rel_vel.dot(direction)
        force_mag += damping_force
        force = direction * force_mag
        self.a.apply_force(force.x, force.y)
        self.b.apply_force(-force.x, -force.y)


class PhysicsWorld:
    def __init__(self, gravity: float = GRAVITY,
                 bounds_x: int = 0, bounds_y: int = 0):
        self.bodies: list[Body] = []
        self.springs: list[Spring] = []
        self.gravity = gravity
        self.bounds_x = bounds_x
        self.bounds_y = bounds_y
        self.time = 0.0

    def add_body(self, body: Body):
        self.bodies.append(body)
        return body

    def add_spring(self, spring: Spring):
        self.springs.append(spring)
        return spring

    def remove_body(self, body: Body):
        if body in self.bodies:
            self.bodies.remove(body)

    def clear(self):
        self.bodies.clear()
        self.springs.clear()

    def step(self, dt: float, substeps: int = 4):
        sub_dt = dt / substeps
        for _ in range(substeps):
            for spring in self.springs:
                spring.update(sub_dt)
            for body in self.bodies:
                body.update(sub_dt, self.gravity, self.bounds_x, self.bounds_y)
            for i in range(len(self.bodies)):
                for j in range(i + 1, len(self.bodies)):
                    resolve_collision(self.bodies[i], self.bodies[j])
            for body in self.bodies:
                if not math.isfinite(body.pos.x) or not math.isfinite(body.pos.y):
                    body.pos.x = _sanitize(body.pos.x, 10)
                    body.pos.y = _sanitize(body.pos.y, 10)
                    body.vel.x = 0
                    body.vel.y = 0
        self.time += dt

    def render(self, canvas: Canvas, z: float = 0, show_trails: bool = False):
        for body in self.bodies:
            if not math.isfinite(body.pos.x) or not math.isfinite(body.pos.y):
                continue
            if show_trails and len(body.trail) > 1:
                for i in range(1, len(body.trail)):
                    x1, y1 = body.trail[i - 1]
                    x2, y2 = body.trail[i]
                    canvas.draw_line(x1, y1, x2, y2, '.', color=body.color.mul(0.3), z=z)
            if body.radius >= 1:
                canvas.draw_circle(
                    round(body.pos.x), round(body.pos.y),
                    max(1, round(body.radius)),
                    '#', body.color, z=z
                )
            else:
                canvas.set_pixel_f(body.pos.x, body.pos.y, '@', body.color, z=z)

    @staticmethod
    def chain(world: PhysicsWorld, x: float, y: float, links: int = 10,
              spacing: float = 2, radius: float = 0.5, color: Optional[Color] = None) -> list[Body]:
        bodies = []
        c = color or Color(180, 200, 255)
        for i in range(links):
            b = Body(x, y + i * spacing, radius, 0.5 if i > 0 else 0, c)
            if i == 0:
                b.locked = True
            world.add_body(b)
            bodies.append(b)
            if i > 0:
                world.add_spring(Spring(bodies[i - 1], b, spacing, 200, 5))
        return bodies

    @staticmethod
    def cloth(world: PhysicsWorld, x: float, y: float, cols: int = 8, rows: int = 6,
              spacing: float = 1.8, radius: float = 0.2, color: Optional[Color] = None) -> list[list[Body]]:
        c = color or Color(150, 200, 255)
        grid: list[list[Body]] = []
        for r in range(rows):
            row: list[Body] = []
            for col in range(cols):
                b = Body(x + col * spacing, y + r * spacing, radius, 0.3, c)
                if r == 0:
                    b.locked = True
                world.add_body(b)
                row.append(b)
            grid.append(row)
        for r in range(rows):
            for col in range(cols):
                if col < cols - 1:
                    world.add_spring(Spring(grid[r][col], grid[r][col + 1], spacing, 300, 3))
                if r < rows - 1:
                    world.add_spring(Spring(grid[r][col], grid[r + 1][col], spacing, 300, 3))
                if col < cols - 1 and r < rows - 1:
                    world.add_spring(Spring(grid[r][col], grid[r + 1][col + 1], spacing * 1.4, 100, 1))
                    world.add_spring(Spring(grid[r][col + 1], grid[r + 1][col], spacing * 1.4, 100, 1))
        return grid


# ═══════════════════════════════════════════════════════════════════
# ENHANCED: Rotation, angular velocity
# ═══════════════════════════════════════════════════════════════════

class RigidBody(Body):
    def __init__(self, x: float = 0, y: float = 0, radius: float = 1,
                 mass: float = 1, color: Optional[Color] = None):
        super().__init__(x, y, radius, mass, color)
        self.angle = 0.0
        self.ang_vel = 0.0
        self.moment = mass * radius * radius * 0.5
        self.inv_moment = 1 / self.moment if self.moment > 0 else 0
        self.torque = 0.0

    def apply_torque(self, t: float):
        if not self.locked:
            self.torque += t

    def update(self, dt: float, gravity: float = GRAVITY,
               bounds_x: int = 0, bounds_y: int = 0):
        super().update(dt, gravity, bounds_x, bounds_y)
        if not self.locked:
            self.ang_vel += self.torque * self.inv_moment * dt
            self.ang_vel *= (1 - self.friction * 0.1)
            self.angle += self.ang_vel * dt
            self.torque = 0.0

    def render(self, canvas: Canvas, z: float = 0):
        cx, cy = round(self.pos.x), round(self.pos.y)
        r = max(1, round(self.radius))
        if not math.isfinite(self.angle):
            self.angle = 0
        dir_x = round(cx + math.cos(self.angle) * r)
        dir_y = round(cy + math.sin(self.angle) * r)
        canvas.draw_circle(cx, cy, r, '#', self.color, z=z)
        canvas.draw_line(cx, cy, dir_x, dir_y, '@', self.color, z=z + 1)


# ═══════════════════════════════════════════════════════════════════
# POLYGON BODY — convex polygon with SAT collision
# ═══════════════════════════════════════════════════════════════════

class PolyBody:
    def __init__(self, vertices: list[tuple[float, float]],
                 mass: float = 1, color: Optional[Color] = None,
                 pos: tuple[float, float] = (0, 0)):
        self._local_verts = list(vertices)
        self.verts: list[tuple[float, float]] = list(vertices)
        self.pos = Vec2(pos[0], pos[1])
        self.vel = Vec2(0, 0)
        self.angle = 0.0
        self.ang_vel = 0.0
        self.mass = mass
        self.inv_mass = 1 / mass if mass > 0 else 0
        self.color = color or Color(180, 160, 200)
        self.restitution = 0.4
        self.friction = 0.3
        self.locked = False
        self.group = 0
        self._recalc_center()
        self._compute_moment()

    def _recalc_center(self):
        if not self.verts:
            return
        cx = sum(v[0] for v in self._local_verts) / len(self._local_verts)
        cy = sum(v[1] for v in self._local_verts) / len(self._local_verts)
        self._local_verts = [(v[0] - cx, v[1] - cy) for v in self._local_verts]
        self._update_verts()

    def _compute_moment(self):
        area = 0
        moment = 0
        n = len(self._local_verts)
        for i in range(n):
            x1, y1 = self._local_verts[i]
            x2, y2 = self._local_verts[(i + 1) % n]
            cross = x1 * y2 - x2 * y1
            area += cross
            moment += (x1 ** 2 + x1 * x2 + x2 ** 2 + y1 ** 2 + y1 * y2 + y2 ** 2) * cross
        area *= 0.5
        if abs(area) > 1e-6:
            moment = abs(moment) / 12
        else:
            moment = 1
        self.moment = moment * self.mass
        self.inv_moment = 1 / self.moment if self.moment > 0 else 0

    def _update_verts(self):
        c, s = math.cos(self.angle), math.sin(self.angle)
        self.verts = [
            (self.pos.x + vx * c - vy * s,
             self.pos.y + vx * s + vy * c)
            for vx, vy in self._local_verts
        ]

    def apply_force(self, fx: float, fy: float):
        if not self.locked:
            self.vel.x += fx * self.inv_mass
            self.vel.y += fy * self.inv_mass

    def apply_impulse(self, ix: float, iy: float, px: float = 0, py: float = 0):
        if self.locked:
            return
        self.vel.x += ix * self.inv_mass
        self.vel.y += iy * self.inv_mass
        if self.inv_moment > 0:
            rx, ry = px - self.pos.x, py - self.pos.y
            self.ang_vel += (rx * iy - ry * ix) * self.inv_moment

    def update(self, dt: float, gravity: float = GRAVITY,
               bounds_x: int = 0, bounds_y: int = 0):
        if self.locked:
            return
        self.vel.y += gravity * dt
        self.vel.x *= (1 - self.friction * 0.1)
        self.pos.x += self.vel.x * dt + self.ang_vel * -self.vel.y * dt * 0.01
        self.pos.y += self.vel.y * dt + self.ang_vel * self.vel.x * dt * 0.01
        self.angle += self.ang_vel * dt
        self.ang_vel *= (1 - self.friction * 0.05)
        self._update_verts()
        if bounds_x > 0:
            for i, (vx, vy) in enumerate(self.verts):
                if vx < 0:
                    self.pos.x += (0 - vx)
                    self.vel.x = -self.vel.x * self.restitution
                elif vx >= bounds_x:
                    self.pos.x -= (vx - bounds_x + 1)
                    self.vel.x = -self.vel.x * self.restitution
                if vy < 0:
                    self.pos.y += (0 - vy)
                    self.vel.y = -self.vel.y * self.restitution
                elif vy >= bounds_y:
                    self.pos.y -= (vy - bounds_y + 1)
                    self.vel.y = -self.vel.y * self.restitution
            self._update_verts()

    def render(self, canvas: Canvas, z: float = 0):
        self._update_verts()
        for i in range(len(self.verts)):
            x1, y1 = self.verts[i]
            x2, y2 = self.verts[(i + 1) % len(self.verts)]
            canvas.draw_line(round(x1), round(y1), round(x2), round(y2),
                             '#', self.color, z=z)

    def support(self, axis: tuple[float, float]) -> tuple[float, float]:
        best_dot = float('-inf')
        best_v = self.verts[0]
        ax, ay = axis
        for vx, vy in self.verts:
            d = vx * ax + vy * ay
            if d > best_dot:
                best_dot = d
                best_v = (vx, vy)
        return best_v


def sat_collide(a: PolyBody, b: PolyBody) -> Optional[tuple[float, float, float]]:
    axes: list[tuple[float, float]] = []
    for verts in (a.verts, b.verts):
        for i in range(len(verts)):
            x1, y1 = verts[i]
            x2, y2 = verts[(i + 1) % len(verts)]
            ex, ey = x2 - x1, y2 - y1
            length = math.hypot(ex, ey)
            if length > 0:
                axes.append((-ey / length, ex / length))
    overlap = float('inf')
    mtv_axis = (0, 0)
    for ax, ay in axes:
        min_a = min(vx * ax + vy * ay for vx, vy in a.verts)
        max_a = max(vx * ax + vy * ay for vx, vy in a.verts)
        min_b = min(vx * ax + vy * ay for vx, vy in b.verts)
        max_b = max(vx * ax + vy * ay for vx, vy in b.verts)
        if max_a <= min_b or max_b <= min_a:
            return None
        o = min(max_a - min_b, max_b - min_a)
        if o < overlap:
            overlap = o
            mtv_axis = (ax, ay)
    ax, ay = mtv_axis
    ca = Vec2(sum(v[0] for v in a.verts) / len(a.verts), sum(v[1] for v in a.verts) / len(a.verts))
    cb = Vec2(sum(v[0] for v in b.verts) / len(b.verts), sum(v[1] for v in b.verts) / len(b.verts))
    if (cb.x - ca.x) * ax + (cb.y - ca.y) * ay < 0:
        ax, ay = -ax, -ay
    return (ax, ay, overlap)


def resolve_poly_poly(a: PolyBody, b: PolyBody):
    result = sat_collide(a, b)
    if result is None:
        return
    ax, ay, overlap = result
    if a.inv_mass + b.inv_mass == 0:
        return
    total_inv = a.inv_mass + b.inv_mass
    a.pos.x -= ax * overlap * (a.inv_mass / total_inv)
    a.pos.y -= ay * overlap * (a.inv_mass / total_inv)
    b.pos.x += ax * overlap * (b.inv_mass / total_inv)
    b.pos.y += ay * overlap * (b.inv_mass / total_inv)
    a._update_verts()
    b._update_verts()
    rel_vel_x = b.vel.x - a.vel.x
    rel_vel_y = b.vel.y - a.vel.y
    rel_n = rel_vel_x * ax + rel_vel_y * ay
    if rel_n > 0:
        return
    e = min(a.restitution, b.restitution)
    j = -(1 + e) * rel_n / total_inv
    a.vel.x -= ax * j * a.inv_mass
    a.vel.y -= ay * j * a.inv_mass
    b.vel.x += ax * j * b.inv_mass
    b.vel.y += ay * j * b.inv_mass


def resolve_circle_poly(circle: Body, poly: PolyBody):
    cx, cy = circle.pos.x, circle.pos.y
    best_d = float('inf')
    best_n = (0, 0)
    verts = poly.verts
    for i in range(len(verts)):
        x1, y1 = verts[i]
        x2, y2 = verts[(i + 1) % len(verts)]
        ex, ey = x2 - x1, y2 - y1
        le = ex * ex + ey * ey
        if le == 0:
            continue
        t = max(0, min(1, ((cx - x1) * ex + (cy - y1) * ey) / le))
        px = x1 + ex * t
        py = y1 + ey * t
        dx, dy = cx - px, cy - py
        d_sq = dx * dx + dy * dy
        if d_sq < best_d:
            best_d = d_sq
            le_n = math.sqrt(le)
            if t == 0 or t == 1:
                n_len = math.sqrt(d_sq) if d_sq > 0 else 1
                best_n = (dx / n_len, dy / n_len)
            else:
                best_n = (-ey / le_n, ex / le_n)
                if dx * best_n[0] + dy * best_n[1] < 0:
                    best_n = (-best_n[0], -best_n[1])
    d = math.sqrt(best_d) if best_d > 0 else 0
    if d >= circle.radius:
        return
    overlap = circle.radius - d
    nx, ny = best_n
    if d < 0.001:
        return
    total_inv = circle.inv_mass + poly.inv_mass
    if total_inv == 0:
        return
    if not circle.locked:
        circle.pos.x += nx * overlap * (circle.inv_mass / total_inv)
        circle.pos.y += ny * overlap * (circle.inv_mass / total_inv)
    if not poly.locked:
        poly.pos.x -= nx * overlap * (poly.inv_mass / total_inv)
        poly.pos.y -= ny * overlap * (poly.inv_mass / total_inv)
        poly._update_verts()
    rel_vx = poly.vel.x - circle.vel.x
    rel_vy = poly.vel.y - circle.vel.y
    rel_n = rel_vx * nx + rel_vy * ny
    if rel_n > 0:
        return
    e = min(circle.restitution, poly.restitution)
    j = -(1 + e) * rel_n / total_inv
    if not circle.locked:
        circle.vel.x -= nx * j * circle.inv_mass
        circle.vel.y -= ny * j * circle.inv_mass
    if not poly.locked:
        poly.vel.x += nx * j * poly.inv_mass
        poly.vel.y += ny * j * poly.inv_mass


def resolve_circle_aabb(circle: Body, rect: RectBody):
    n = Vec2(
        max(rect.aabb.left - circle.pos.x, 0, circle.pos.x - rect.aabb.right),
        max(rect.aabb.top - circle.pos.y, 0, circle.pos.y - rect.aabb.bottom),
    )
    if n.length_sq() >= circle.radius * circle.radius:
        return
    if n.length_sq() == 0:
        cx = max(rect.aabb.left, min(circle.pos.x, rect.aabb.right))
        cy = max(rect.aabb.top, min(circle.pos.y, rect.aabb.bottom))
        n = Vec2(circle.pos.x - cx, circle.pos.y - cy)
        if n.length_sq() == 0:
            return
    d = n.length()
    overlap = circle.radius - d
    if overlap <= 0:
        return
    n = n * (1 / d)
    total_inv = circle.inv_mass + rect.inv_mass
    if total_inv == 0:
        return
    if not circle.locked:
        circle.pos.x += n.x * overlap * (circle.inv_mass / total_inv)
        circle.pos.y += n.y * overlap * (circle.inv_mass / total_inv)
    if not rect.locked:
        rect.aabb.x -= n.x * overlap * (rect.inv_mass / total_inv)
        rect.aabb.y -= n.y * overlap * (rect.inv_mass / total_inv)
    rvx = rect.vel.x - circle.vel.x
    rvy = rect.vel.y - circle.vel.y
    rn = rvx * n.x + rvy * n.y
    if rn > 0:
        return
    e = min(circle.restitution, rect.restitution)
    j = -(1 + e) * rn / total_inv
    if not circle.locked:
        circle.vel.x -= n.x * j * circle.inv_mass
        circle.vel.y -= n.y * j * circle.inv_mass
    if not rect.locked:
        rect.vel.x += n.x * j * rect.inv_mass
        rect.vel.y += n.y * j * rect.inv_mass


# ═══════════════════════════════════════════════════════════════════
# COMPOUND BODY — composite of multiple shapes
# ═══════════════════════════════════════════════════════════════════

class CompoundBody:
    def __init__(self, x: float = 0, y: float = 0, mass: float = 1,
                 color: Optional[Color] = None):
        self.pos = Vec2(x, y)
        self.vel = Vec2(0, 0)
        self.angle = 0.0
        self.ang_vel = 0.0
        self.mass = mass
        self.inv_mass = 1 / mass if mass > 0 else 0
        self.color = color or Color(180, 200, 220)
        self.locked = False
        self.restitution = 0.3
        self.friction = 0.3
        self.group = 0
        self._shapes: list[dict] = []
        self._total_mass = 0

    def add_circle(self, lx: float, ly: float, radius: float,
                   mass: float = 1):
        self._shapes.append({
            'type': 'circle', 'lx': lx, 'ly': ly, 'radius': radius,
            'mass': mass,
        })
        self._total_mass += mass
        return self

    def add_rect(self, lx: float, ly: float, w: float, h: float,
                 mass: float = 1):
        self._shapes.append({
            'type': 'rect', 'lx': lx, 'ly': ly, 'w': w, 'h': h,
            'mass': mass,
        })
        self._total_mass += mass
        return self

    def add_poly(self, lx: float, ly: float,
                 vertices: list[tuple[float, float]], mass: float = 1):
        self._shapes.append({
            'type': 'poly', 'lx': lx, 'ly': ly, 'verts': vertices,
            'mass': mass,
        })
        self._total_mass += mass
        return self

    def apply_force(self, fx: float, fy: float):
        if not self.locked:
            self.vel.x += fx * self.inv_mass
            self.vel.y += fy * self.inv_mass

    def update(self, dt: float, gravity: float = GRAVITY,
               bounds_x: int = 0, bounds_y: int = 0):
        if self.locked:
            return
        self.vel.y += gravity * dt
        self.vel.x *= (1 - self.friction * 0.1)
        self.pos.x += self.vel.x * dt
        self.pos.y += self.vel.y * dt
        self.angle += self.ang_vel * dt

    def get_world_shapes(self) -> list[dict]:
        c, s = math.cos(self.angle), math.sin(self.angle)
        result = []
        for shape in self._shapes:
            wx = self.pos.x + shape['lx'] * c - shape['ly'] * s
            wy = self.pos.y + shape['lx'] * s + shape['ly'] * c
            entry = dict(shape)
            entry['wx'] = wx
            entry['wy'] = wy
            result.append(entry)
        return result

    def render(self, canvas: Canvas, z: float = 0):
        for shape in self.get_world_shapes():
            if shape['type'] == 'circle':
                canvas.draw_circle(
                    round(shape['wx']), round(shape['wy']),
                    max(1, round(shape['radius'])),
                    '#', self.color, z=z,
                )
            elif shape['type'] == 'rect':
                canvas.draw_rect(
                    round(shape['wx'] - shape['w'] / 2),
                    round(shape['wy'] - shape['h'] / 2),
                    round(shape['w']), round(shape['h']),
                    '#', self.color, z=z,
                )
            elif shape['type'] == 'poly':
                verts = shape['verts']
                c2, s2 = math.cos(self.angle), math.sin(self.angle)
                for i in range(len(verts)):
                    x1, y1 = verts[i]
                    x2, y2 = verts[(i + 1) % len(verts)]
                    wx1 = shape['wx'] + x1 * c2 - y1 * s2
                    wy1 = shape['wy'] + x1 * s2 + y1 * c2
                    wx2 = shape['wx'] + x2 * c2 - y2 * s2
                    wy2 = shape['wy'] + x2 * s2 + y2 * c2
                    canvas.draw_line(round(wx1), round(wy1),
                                     round(wx2), round(wy2),
                                     '#', self.color, z=z)


class EnhancedPhysicsWorld(PhysicsWorld):
    def __init__(self, gravity: float = GRAVITY,
                 bounds_x: int = 0, bounds_y: int = 0):
        super().__init__(gravity, bounds_x, bounds_y)
        self.poly_bodies: list[PolyBody] = []
        self.compound_bodies: list[CompoundBody] = []

    def add_body(self, body):
        if isinstance(body, PolyBody):
            self.poly_bodies.append(body)
            return body
        elif isinstance(body, CompoundBody):
            self.compound_bodies.append(body)
            return body
        return super().add_body(body)

    def step(self, dt: float, substeps: int = 4):
        sub_dt = dt / substeps
        for _ in range(substeps):
            for spring in self.springs:
                spring.update(sub_dt)
            for body in self.bodies:
                if isinstance(body, RectBody):
                    ba = None
                    if self.bounds_x > 0:
                        ba = AABB(0, 0, self.bounds_x, self.bounds_y)
                    body.update(sub_dt, self.gravity, ba)
                else:
                    body.update(sub_dt, self.gravity, self.bounds_x, self.bounds_y)
            for body in self.poly_bodies:
                body.update(sub_dt, self.gravity, self.bounds_x, self.bounds_y)
            for body in self.compound_bodies:
                body.update(sub_dt, self.gravity, self.bounds_x, self.bounds_y)
            for i in range(len(self.bodies)):
                for j in range(i + 1, len(self.bodies)):
                    a, b = self.bodies[i], self.bodies[j]
                    if isinstance(a, RectBody) and isinstance(b, RectBody):
                        resolve_aabb(a, b)
                    elif isinstance(a, RectBody) and isinstance(b, Body):
                        resolve_circle_aabb(b, a)
                    elif isinstance(a, Body) and isinstance(b, RectBody):
                        resolve_circle_aabb(a, b)
                    elif isinstance(a, Body) and isinstance(b, Body):
                        resolve_collision(a, b)
            for i in range(len(self.bodies)):
                for j in range(len(self.poly_bodies)):
                    a, b = self.bodies[i], self.poly_bodies[j]
                    if isinstance(a, Body):
                        resolve_circle_poly(a, b)
                    elif isinstance(a, RectBody):
                        pass
            for i in range(len(self.poly_bodies)):
                for j in range(i + 1, len(self.poly_bodies)):
                    resolve_poly_poly(self.poly_bodies[i], self.poly_bodies[j])
        self.time += dt

    def render(self, canvas: Canvas, z: float = 0, show_trails: bool = False):
        for body in self.bodies:
            if isinstance(body, RectBody):
                body.render(canvas, z)
                continue
            if not math.isfinite(body.pos.x) or not math.isfinite(body.pos.y):
                continue
            if show_trails and len(body.trail) > 1:
                for i in range(1, len(body.trail)):
                    x1, y1 = body.trail[i - 1]
                    x2, y2 = body.trail[i]
                    canvas.draw_line(x1, y1, x2, y2, '.', color=body.color.mul(0.3), z=z)
            if body.radius >= 1:
                canvas.draw_circle(
                    round(body.pos.x), round(body.pos.y),
                    max(1, round(body.radius)),
                    '#', body.color, z=z
                )
            else:
                canvas.set_pixel_f(body.pos.x, body.pos.y, '@', body.color, z=z)
        for poly in self.poly_bodies:
            poly.render(canvas, z)
        for comp in self.compound_bodies:
            comp.render(canvas, z)
