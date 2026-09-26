from __future__ import annotations
from ..core.geom import Vec3
from ..core.color import Color


GRAVITY3D = Vec3(0, -9.8, 0)


class Body3D:
    __slots__ = (
        'ang_vel',
        'color',
        'friction',
        'inertia',
        'inv_inertia',
        'inv_mass',
        'locked',
        'mass',
        'pos',
        'radius',
        'restitution',
        'rot',
        'shape',
        'vel',
    )
    def __init__(self, pos: Vec3 = Vec3(), mass: float = 1, radius: float = 1,
                 color: Color | None = None):
        self.pos = pos
        self.vel = Vec3()
        self.rot = Vec3()
        self.ang_vel = Vec3()
        self.mass = mass
        self.inv_mass = 1 / mass if mass > 0 else 0
        inrt = 0.4 * mass * radius * radius
        self.inertia = inrt
        self.inv_inertia = 1 / inrt if inrt > 0 else 0
        self.shape = 'sphere'
        self.radius = radius
        self.color = color or Color(150, 150, 200)
        self.restitution = 0.5
        self.friction = 0.3
        self.locked = False

    def apply_force(self, force: Vec3):
        if not self.locked:
            self.vel = self.vel + force * self.inv_mass

    def apply_torque(self, torque: Vec3):
        if not self.locked:
            self.ang_vel = self.ang_vel + torque * self.inv_inertia

    def update(self, dt: float, gravity: Vec3 = GRAVITY3D,
               bounds: tuple[float, float, float] | None = None):
        if self.locked:
            return
        self.vel = self.vel + gravity * dt
        self.pos = self.pos + self.vel * dt
        self.rot = self.rot + self.ang_vel * dt
        if bounds:
            bx, by, bz = bounds
            if abs(self.pos.x) + self.radius > bx:
                self.pos.x = (bx - self.radius) * (1 if self.pos.x > 0 else -1)
                self.vel.x = -self.vel.x * self.restitution
            if abs(self.pos.y) + self.radius > by:
                self.pos.y = (by - self.radius) * (1 if self.pos.y > 0 else -1)
                self.vel.y = -self.vel.y * self.restitution
            if abs(self.pos.z) + self.radius > bz:
                self.pos.z = (bz - self.radius) * (1 if self.pos.z > 0 else -1)
                self.vel.z = -self.vel.z * self.restitution

    def overlaps(self, other: Body3D) -> bool:
        return self.pos.dist(other.pos) < self.radius + other.radius


class BoxBody3D(Body3D):
    __slots__ = ('size', 'verts')
    def __init__(self, pos: Vec3 = Vec3(), size: Vec3 = Vec3(1, 1, 1),
                 mass: float = 1, color: Color | None = None):
        super().__init__(pos, mass, max(size.x, size.y, size.z) / 2, color)
        self.shape = 'box'
        self.size = size
        self.verts: list[Vec3] = []
        self._update_verts()
        inrt = mass * (size.x ** 2 + size.y ** 2 + size.z ** 2) / 12
        self.inertia = inrt
        self.inv_inertia = 1 / inrt if inrt > 0 else 0

    def _update_verts(self):
        s = self.size * 0.5
        self.verts = [
            Vec3(-s.x, -s.y, -s.z), Vec3(s.x, -s.y, -s.z),
            Vec3(s.x, s.y, -s.z), Vec3(-s.x, s.y, -s.z),
            Vec3(-s.x, -s.y, s.z), Vec3(s.x, -s.y, s.z),
            Vec3(s.x, s.y, s.z), Vec3(-s.x, s.y, s.z),
        ]


class Spring3D:
    __slots__ = ('a', 'b', 'damping', 'rest_len', 'stiffness')
    def __init__(self, a: Body3D, b: Body3D, rest_len: float,
                 stiffness: float = 50, damping: float = 2):
        self.a = a
        self.b = b
        self.rest_len = rest_len
        self.stiffness = stiffness
        self.damping = damping

    def update(self, dt: float):
        delta = self.b.pos - self.a.pos
        d = delta.length()
        if d < 0.001:
            return
        direction = delta * (1 / d)
        rel_vel = self.b.vel - self.a.vel
        displacement = d - self.rest_len
        force_mag = -self.stiffness * displacement - self.damping * rel_vel.dot(direction)
        force = direction * force_mag
        self.a.apply_force(force * (-1 if self.a.inv_mass > 0 else 0))
        self.b.apply_force(force)


class PhysicsWorld3D:
    def __init__(self, gravity: Vec3 = GRAVITY3D,
                 bounds: tuple[float, float, float] | None = None):
        self.gravity = gravity
        self.bounds = bounds or (20, 20, 20)
        self.bodies: list[Body3D] = []
        self.springs: list[Spring3D] = []

    def add_body(self, body: Body3D):
        self.bodies.append(body)
        return body

    def add_spring(self, spring: Spring3D):
        self.springs.append(spring)
        return spring

    def step(self, dt: float, substeps: int = 4):
        sub_dt = dt / substeps
        for _ in range(substeps):
            for spring in self.springs:
                spring.update(sub_dt)
            for body in self.bodies:
                body.update(sub_dt, self.gravity, self.bounds)
            for i in range(len(self.bodies)):
                for j in range(i + 1, len(self.bodies)):
                    self._resolve_collision(self.bodies[i], self.bodies[j])

    def _resolve_collision(self, a: Body3D, b: Body3D):
        if a.locked and b.locked:
            return
        if not a.overlaps(b):
            return
        delta = b.pos - a.pos
        d = delta.length()
        if d < 0.001:
            delta = Vec3(0, 1, 0)
            d = 1
        normal = delta * (1 / d)
        overlap = a.radius + b.radius - d
        if overlap <= 0:
            return
        total_inv = a.inv_mass + b.inv_mass
        if total_inv <= 0:
            return
        correction = normal * (overlap / total_inv)
        a.pos = a.pos - correction * a.inv_mass
        b.pos = b.pos + correction * b.inv_mass
        rel_vel = b.vel - a.vel
        vel_along = rel_vel.dot(normal)
        if vel_along > 0:
            return
        e = min(a.restitution, b.restitution)
        j = -(1 + e) * vel_along / total_inv
        impulse = normal * j
        a.vel = a.vel - impulse * a.inv_mass
        b.vel = b.vel + impulse * b.inv_mass

    def chain(self, x: float, y: float, z: float, links: int = 8,
              mass: float = 0.5, radius: float = 0.3, stiffness: float = 100) -> list[Body3D]:
        bodies = []
        prev: Body3D | None = None
        for i in range(links):
            body = Body3D(Vec3(x, y - i * radius * 2.2, z), mass, radius)
            body.restitution = 0.2
            if i == 0:
                body.locked = True
            self.add_body(body)
            bodies.append(body)
            if prev:
                rest = prev.pos.dist(body.pos)
                self.add_spring(Spring3D(prev, body, rest, stiffness, 3))
            prev = body
        return bodies
