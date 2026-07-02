from __future__ import annotations
import math, random
from typing import Optional
from ..core.canvas import Canvas
from ..core.color import Color
from ..core.geom import Vec2


class SteerAgent:
    __slots__ = ('pos', 'vel', 'heading', 'max_speed', 'max_force',
                 'mass', 'color', 'trail', 'trail_max')
    def __init__(self, x: float = 0, y: float = 0, color: Optional[Color] = None):
        self.pos = Vec2(x, y)
        self.vel = Vec2(random.uniform(-1, 1), random.uniform(-1, 1))
        self.heading = Vec2(1, 0)
        self.max_speed = 3
        self.max_force = 0.3
        self.mass = 1
        self.color = color or Color(200, 200, 100)
        self.trail: list[tuple[int, int]] = []
        self.trail_max = 30

    def seek(self, target: Vec2) -> Vec2:
        desired = (target - self.pos).norm() * self.max_speed
        force = desired - self.vel
        return self._truncate(force, self.max_force)

    def flee(self, target: Vec2) -> Vec2:
        desired = (self.pos - target).norm() * self.max_speed
        force = desired - self.vel
        return self._truncate(force, self.max_force)

    def arrive(self, target: Vec2, slowing_dist: float = 5) -> Vec2:
        to_target = target - self.pos
        d = to_target.length()
        if d < 0.5:
            self.vel = Vec2()
            return Vec2()
        desired = to_target * (self.max_speed * (min(d, slowing_dist) / slowing_dist) / d)
        force = desired - self.vel
        return self._truncate(force, self.max_force)

    def pursue(self, target: SteerAgent, look_ahead: float = 3) -> Vec2:
        future = target.pos + target.vel * look_ahead
        return self.seek(future)

    def evade(self, target: SteerAgent, look_ahead: float = 3) -> Vec2:
        future = target.pos + target.vel * look_ahead
        return self.flee(future)

    def wander(self, wander_theta: float) -> tuple[Vec2, float]:
        wander_r = 2
        wander_d = 4
        jitter = 0.3
        wander_theta += random.uniform(-1, 1) * jitter
        circle_pos = self.vel.norm() * wander_d
        offset = Vec2(math.cos(wander_theta) * wander_r, math.sin(wander_theta) * wander_r)
        target = self.pos + circle_pos + offset
        return self.seek(target), wander_theta

    def separate(self, neighbors: list[SteerAgent], desired_sep: float = 3) -> Vec2:
        force = Vec2()
        count = 0
        for n in neighbors:
            if n is self:
                continue
            d = self.pos.dist(n.pos)
            if d < desired_sep and d > 0:
                diff = (self.pos - n.pos).norm() * (1 / d)
                force = force + diff
                count += 1
        if count > 0:
            force = force * (1 / count)
            force = force.norm() * self.max_speed - self.vel
            force = self._truncate(force, self.max_force)
        return force

    def align(self, neighbors: list[SteerAgent], radius: float = 4) -> Vec2:
        avg = Vec2()
        count = 0
        for n in neighbors:
            if n is self:
                continue
            d = self.pos.dist(n.pos)
            if d < radius and d > 0:
                avg = avg + n.vel
                count += 1
        if count > 0:
            avg = avg * (1 / count)
            avg = avg.norm() * self.max_speed
            return self._truncate(avg - self.vel, self.max_force)
        return Vec2()

    def cohesion(self, neighbors: list[SteerAgent], radius: float = 4) -> Vec2:
        avg = Vec2()
        count = 0
        for n in neighbors:
            if n is self:
                continue
            d = self.pos.dist(n.pos)
            if d < radius and d > 0:
                avg = avg + n.pos
                count += 1
        if count > 0:
            avg = avg * (1 / count)
            return self.seek(avg)
        return Vec2()

    def flock(self, neighbors: list[SteerAgent],
              sep_weight: float = 1.5, ali_weight: float = 1,
              coh_weight: float = 1, radius: float = 4) -> Vec2:
        sep = self.separate(neighbors, radius * 0.5) * sep_weight
        ali = self.align(neighbors, radius) * ali_weight
        coh = self.cohesion(neighbors, radius) * coh_weight
        return sep + ali + coh

    def avoid_obstacles(self, obstacles: list[Vec2], look_ahead: float = 5) -> Vec2:
        if not obstacles:
            return Vec2()
        ahead = self.pos + self.vel.norm() * look_ahead
        ahead2 = self.pos + self.vel.norm() * look_ahead * 0.5
        closest = None
        closest_d = float('inf')
        for obs in obstacles:
            d = ahead.dist(obs)
            if d < closest_d:
                closest_d = d
                closest = obs
        if closest and closest_d < 2:
            force = (ahead - closest).norm() * self.max_speed - self.vel
            return self._truncate(force, self.max_force * 2)
        return Vec2()

    def follow_path(self, path: list[Vec2], path_idx: int) -> tuple[Vec2, int]:
        if not path:
            return Vec2(), path_idx
        target = path[path_idx % len(path)]
        if self.pos.dist(target) < 2:
            path_idx = (path_idx + 1) % len(path)
            target = path[path_idx % len(path)]
        return self.seek(target), path_idx

    def _truncate(self, v: Vec2, limit: float) -> Vec2:
        l = v.length()
        if l > limit:
            return v * (limit / l)
        return v

    def update(self, force: Vec2):
        self.vel = self.vel + force * (1 / self.mass)
        l = self.vel.length()
        if l > self.max_speed:
            self.vel = self.vel * (self.max_speed / l)
        if l > 0.01:
            self.heading = self.vel * (1 / l)
        self.pos = self.pos + self.vel
        if l > 0.1 and len(self.trail) < self.trail_max:
            self.trail.append((int(self.pos.x), int(self.pos.y)))

    def wrap(self, w: float, h: float):
        if self.pos.x < 0: self.pos.x += w
        if self.pos.x >= w: self.pos.x -= w
        if self.pos.y < 0: self.pos.y += h
        if self.pos.y >= h: self.pos.y -= h

    def bounce(self, w: float, h: float):
        if self.pos.x < 0: self.pos.x = 1; self.vel.x = -self.vel.x
        if self.pos.x >= w: self.pos.x = w - 2; self.vel.x = -self.vel.x
        if self.pos.y < 0: self.pos.y = 1; self.vel.y = -self.vel.y
        if self.pos.y >= h: self.pos.y = h - 2; self.vel.y = -self.vel.y

    def render(self, canvas: Canvas, ox: int = 0, oy: int = 0,
               show_trail: bool = True):
        if show_trail:
            for i, (tx, ty) in enumerate(self.trail):
                t = i / max(1, len(self.trail))
                c = self.color.lerp(Color(40, 40, 60), t)
                canvas.set_pixel(tx + ox, ty + oy, '·', c, z=1)
        sx, sy = int(self.pos.x) + ox, int(self.pos.y) + oy
        canvas.set_pixel(sx, sy, '●', self.color, z=3)
        hx = int(self.pos.x + self.heading.x * 2) + ox
        hy = int(self.pos.y + self.heading.y * 2) + oy
        canvas.draw_line(sx, sy, hx, hy, '·', self.color, z=2)


class SteerWorld:
    def __init__(self, width: float = 80, height: float = 40):
        self.agents: list[SteerAgent] = []
        self.obstacles: list[Vec2] = []
        self.width = width
        self.height = height
        self.wrap_mode = True

    def add_agent(self, x: float, y: float, color: Optional[Color] = None) -> SteerAgent:
        a = SteerAgent(x, y, color)
        self.agents.append(a)
        return a

    def add_obstacle(self, x: float, y: float):
        self.obstacles.append(Vec2(x, y))

    def step(self, dt: float = 1.0):
        for a in self.agents:
            force = Vec2()
            wander_force, theta = a.wander(getattr(a, '_wander_theta', 0.0))
            a._wander_theta = theta
            force = force + wander_force
            force = a._truncate(force, a.max_force)
            a.update(force)
            if self.wrap_mode:
                a.wrap(self.width, self.height)
            else:
                a.bounce(self.width, self.height)

    def render(self, canvas: Canvas, ox: int = 0, oy: int = 0):
        for obs in self.obstacles:
            canvas.set_pixel(int(obs.x) + ox, int(obs.y) + oy, '#', Color(150, 80, 80), z=0)
        for a in self.agents:
            a.render(canvas, ox, oy)
