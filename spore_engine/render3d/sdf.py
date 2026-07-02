from __future__ import annotations
import math
from typing import Callable, Optional
from ..core.geom import Vec3
from ..core.color import Color, Gradient
from ..core.canvas import Canvas


SDF = Callable[[Vec3], float]


def sd_sphere(p: Vec3, center: Vec3, r: float) -> float:
    return p.dist(center) - r


def sd_box(p: Vec3, center: Vec3, size: Vec3) -> float:
    q = Vec3(abs(p.x - center.x) - size.x / 2,
             abs(p.y - center.y) - size.y / 2,
             abs(p.z - center.z) - size.z / 2)
    return math.sqrt(max(0, q.x) ** 2 + max(0, q.y) ** 2 + max(0, q.z) ** 2) + min(0, max(q.x, q.y, q.z))


def sd_torus(p: Vec3, center: Vec3, major_r: float, minor_r: float) -> float:
    q = Vec3(p.x - center.x, p.y - center.y, p.z - center.z)
    q2 = Vec3(math.sqrt(q.x ** 2 + q.z ** 2) - major_r, q.y, 0)
    return math.sqrt(q2.x ** 2 + q2.y ** 2) - minor_r


def sd_cylinder(p: Vec3, center: Vec3, r: float, h: float) -> float:
    q = Vec3(abs(p.x - center.x), abs(p.y - center.y), abs(p.z - center.z))
    d = Vec3(math.sqrt(q.x ** 2 + q.z ** 2) - r, q.y - h / 2, 0)
    return min(max(d.x, d.y), 0) + math.sqrt(max(0, d.x) ** 2 + max(0, d.y) ** 2)


def sd_plane(p: Vec3, n: Vec3, d: float) -> float:
    return p.dot(n) - d


def op_union(a: float, b: float) -> float:
    return min(a, b)


def op_subtract(a: float, b: float) -> float:
    return max(a, -b)


def op_intersect(a: float, b: float) -> float:
    return max(a, b)


def op_smooth_union(a: float, b: float, k: float) -> float:
    h = max(0, min(1, 0.5 + (b - a) / (2 * k)))
    return b + (a - b) * h - k * h * (1 - h)


def op_round(sdf: SDF, r: float) -> SDF:
    return lambda p: sdf(p) - r


def op_repeat(p: Vec3, c: Vec3) -> Vec3:
    return Vec3(
        p.x - c.x * round(p.x / c.x),
        p.y - c.y * round(p.y / c.y),
        p.z - c.z * round(p.z / c.z),
    )


class SDFScene:
    def __init__(self):
        self.objects: list[tuple[SDF, Color, float, float]] = []
        self.lights: list[tuple[Vec3, Color, float]] = []
        self.ambient = Color(30, 30, 40)
        self.max_steps = 64
        self.max_dist = 100
        self.epsilon = 0.001
        self.bg_color = Color(10, 10, 20)

    def add(self, sdf: SDF, color: Color, reflectivity: float = 0, emissive: float = 0):
        self.objects.append((sdf, color, reflectivity, emissive))

    def add_light(self, pos: Vec3, color: Color, intensity: float = 1):
        self.lights.append((pos, color, intensity))

    def _scene_sdf(self, p: Vec3) -> tuple[float, Color, float, float]:
        min_d = self.max_dist
        hit_color = self.bg_color
        hit_reflect = 0.0
        hit_emissive = 0.0
        for sdf, color, reflectivity, emissive in self.objects:
            d = sdf(p)
            if d < min_d:
                min_d = d
                hit_color = color
                hit_reflect = reflectivity
                hit_emissive = emissive
        return min_d, hit_color, hit_reflect, hit_emissive

    def _normal(self, p: Vec3) -> Vec3:
        eps = 0.001
        d, _, _, _ = self._scene_sdf(p)
        return Vec3(
            self._scene_sdf(Vec3(p.x + eps, p.y, p.z))[0] - d,
            self._scene_sdf(Vec3(p.x, p.y + eps, p.z))[0] - d,
            self._scene_sdf(Vec3(p.x, p.y, p.z + eps))[0] - d,
        ).norm()

    def _shadow(self, origin: Vec3, light_dir: Vec3, light_dist: float) -> float:
        t = 0.01
        while t < light_dist:
            d, _, _, _ = self._scene_sdf(origin + light_dir * t)
            if d < self.epsilon:
                return 0.3
            t += d
        return 1.0

    def trace(self, origin: Vec3, direction: Vec3, depth: int = 0) -> Color:
        t = 0.01
        for _ in range(self.max_steps):
            pos = origin + direction * t
            d, hit_color, reflectivity, emissive = self._scene_sdf(pos)
            if d < self.epsilon:
                n = self._normal(pos)
                result = Color(emissive * 255, emissive * 255, emissive * 255)
                for lpos, lcol, lint in self.lights:
                    light_dir = (lpos - pos).norm()
                    light_dist = pos.dist(lpos)
                    shadow = self._shadow(pos, light_dir, light_dist)
                    diff = max(0, n.dot(light_dir)) * lint * shadow
                    view_dir = (pos - origin).norm()
                    h = (light_dir + view_dir).norm()
                    spec = max(0, n.dot(h)) ** 32 * lint * 0.5 * shadow
                    lc = Color(
                        min(255, int(lcol.r * diff + lcol.r * spec)),
                        min(255, int(lcol.g * diff + lcol.g * spec)),
                        min(255, int(lcol.b * diff + lcol.b * spec)),
                    )
                    result = Color(
                        min(255, result.r + lc.r),
                        min(255, result.g + lc.g),
                        min(255, result.b + lc.b),
                    )
                result = Color(
                    min(255, result.r + self.ambient.r),
                    min(255, result.g + self.ambient.g),
                    min(255, result.b + self.ambient.b),
                )
                result = Color(
                    min(255, int(result.r * hit_color.r / 255)),
                    min(255, int(result.g * hit_color.g / 255)),
                    min(255, int(result.b * hit_color.b / 255)),
                )
                if reflectivity > 0 and depth < 4:
                    reflected = direction - n * (2 * direction.dot(n))
                    rcol = self.trace(pos + n * 0.01, reflected, depth + 1)
                    result = Color(
                        int(result.r * (1 - reflectivity) + rcol.r * reflectivity),
                        int(result.g * (1 - reflectivity) + rcol.g * reflectivity),
                        int(result.b * (1 - reflectivity) + rcol.b * reflectivity),
                    )
                return result
            if t > self.max_dist:
                break
            t += d
        return self.bg_color

    def render(self, canvas: Canvas, camera_pos: Vec3, camera_target: Vec3,
               fov: float = 90):
        w, h = canvas.w, canvas.h
        aspect = w / h
        forward = (camera_target - camera_pos).norm()
        world_up = Vec3(0, 1, 0)
        right = forward.cross(world_up).norm()
        up = right.cross(forward)
        tan_fov = math.tan(math.radians(fov) / 2)

        lm = int(w * h * 0.15)
        step = max(1, int(math.sqrt(w * h / lm)))
        samples = 0

        for y in range(0, h, step):
            for x in range(0, w, step):
                sx = (2 * (x + 0.5) / w - 1) * aspect * tan_fov
                sy = (1 - 2 * (y + 0.5) / h) * tan_fov
                rd = (forward + right * sx + up * sy).norm()
                col = self.trace(camera_pos, rd)
                for dy in range(min(step, h - y)):
                    for dx in range(min(step, w - x)):
                        canvas.set_pixel(x + dx, y + dy, '█', col)
                samples += 1

        if step > 1:
            for y in range(h):
                for x in range(w):
                    px = canvas.get_pixel(x, y)
                    if px and px.fg is None:
                        neighbors = []
                        for dx, dy in [(-1,0),(1,0),(0,-1),(0,1)]:
                            nx, ny = x + dx, y + dy
                            np = canvas.get_pixel(nx, ny)
                            if np and np.fg:
                                neighbors.append(np.fg)
                        if neighbors:
                            avg = Color(
                                sum(c.r for c in neighbors) // len(neighbors),
                                sum(c.g for c in neighbors) // len(neighbors),
                                sum(c.b for c in neighbors) // len(neighbors),
                            )
                            canvas.set_pixel(x, y, '█', avg)

    def render_preview(self, canvas: Canvas, camera_pos: Vec3,
                       camera_target: Vec3, fov: float = 90):
        w, h = canvas.w, canvas.h
        aspect = w / h
        forward = (camera_target - camera_pos).norm()
        world_up = Vec3(0, 1, 0)
        right = forward.cross(world_up).norm()
        up = right.cross(forward)
        tan_fov = math.tan(math.radians(fov) / 2)
        shade = ' .:-=+*#%@'

        for y in range(h):
            for x in range(w):
                sx = (2 * x / w - 1) * aspect * tan_fov
                sy = (1 - 2 * y / h) * tan_fov
                rd = (forward + right * sx + up * sy).norm()
                col = self.trace(camera_pos, rd)
                lum = col.luminance
                ci = min(9, int(lum / 28))
                canvas.set_pixel(x, y, shade[ci], col)
