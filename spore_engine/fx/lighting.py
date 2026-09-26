from __future__ import annotations
import math
from ..core.color import Color, WHITE
from ..core.canvas import Canvas, SHADE_CHARS


class Ray2D:
    def __init__(self, ox: float, oy: float, dx: float, dy: float):
        self.ox = ox
        self.oy = oy
        self.dx = dx
        self.dy = dy

    def at(self, t: float) -> tuple[float, float]:
        return self.ox + self.dx * t, self.oy + self.dy * t


def cast_ray(ox: float, oy: float, angle: float, max_dist: float,
             solid_fn) -> tuple[float, float, float]:
    dx = math.cos(angle)
    dy = math.sin(angle)
    t = 0.0
    step = 0.5
    while t < max_dist:
        t += step
        x = ox + dx * t
        y = oy + dy * t
        if solid_fn(int(x), int(y)):
            return x, y, t
    return ox + dx * max_dist, oy + dy * max_dist, max_dist


def cast_ray_dda(ox: float, oy: float, dx: float, dy: float,
                 max_dist: float, solid_fn) -> tuple[float, float, float]:
    map_x = int(ox)
    map_y = int(oy)
    delta_dist_x = abs(1 / dx) if dx != 0 else 1e30
    delta_dist_y = abs(1 / dy) if dy != 0 else 1e30
    step_x = 1 if dx > 0 else -1
    step_y = 1 if dy > 0 else -1
    side_dist_x = (step_x * (map_x - ox + (step_x > 0))) * delta_dist_x if dx != 0 else 1e30
    side_dist_y = (step_y * (map_y - oy + (step_y > 0))) * delta_dist_y if dy != 0 else 1e30
    dist = 0.0
    for _ in range(100):
        if side_dist_x < side_dist_y:
            dist = side_dist_x
            side_dist_x += delta_dist_x
            map_x += step_x
        else:
            dist = side_dist_y
            side_dist_y += delta_dist_y
            map_y += step_y
        if dist > max_dist:
            return ox + dx * max_dist, oy + dy * max_dist, max_dist
        if solid_fn(map_x, map_y):
            return ox + dx * dist, oy + dy * dist, dist
    return ox + dx * max_dist, oy + dy * max_dist, max_dist


def visibility_polygon(ox: float, oy: float, radius: float,
                       solid_fn, rays: int = 60) -> list[tuple[float, float]]:
    pts = []
    for i in range(rays):
        angle = 2 * math.pi * i / rays
        dx = math.cos(angle)
        dy = math.sin(angle)
        hx, hy, _ = cast_ray_dda(ox, oy, dx, dy, radius, solid_fn)
        pts.append((hx, hy))
    return pts


class Light:
    def __init__(self, x: float, y: float, color: Color = WHITE,
                 intensity: float = 1.0, radius: float = 10.0):
        self.x = x
        self.y = y
        self.color = color
        self.intensity = intensity
        self.radius = radius

    def falloff(self, dist: float) -> float:
        if dist >= self.radius:
            return 0.0
        return (1 - (dist / self.radius) ** 2) * self.intensity


class LightManager:
    def __init__(self, ambient: Color = Color(10, 10, 20)):
        self.lights: list[Light] = []
        self.ambient = ambient

    def add(self, light: Light):
        self.lights.append(light)
        return light

    def render_to_canvas(self, canvas: Canvas, z: float = 0):
        """Modulate each cell's colour by the lights falling on it.

        Every lit channel is accumulated and used. The previous version
        computed the green and blue averages and then threw them away, and
        scaled red by ``avg / (avg + ambient)``, which darkened every lit cell
        towards black as ambient rose and threw away the light's hue entirely -
        a red torch and a blue torch produced identical output.
        """
        for y in range(canvas.h):
            for x in range(canvas.w):
                total_r, total_g, total_b = 0, 0, 0
                weight = 0.0
                for light in self.lights:
                    dist = math.hypot(x - light.x, y - light.y)
                    f = light.falloff(dist)
                    if f > 0:
                        total_r += light.color.r * f
                        total_g += light.color.g * f
                        total_b += light.color.b * f
                        weight += f
                if weight <= 0:
                    continue
                cell = canvas.buffer[y][x]
                if not cell.fg:
                    continue
                # Each channel is its own weighted average, so a strong red
                # light and a strong blue one differ.
                lr = min(255, total_r / weight)
                lg = min(255, total_g / weight)
                lb = min(255, total_b / weight)
                # Modulate: ambient is the floor, the light scales it up.
                cell.fg = Color(
                    min(255, int(cell.fg.r * (lr + self.ambient.r) / 255)),
                    min(255, int(cell.fg.g * (lg + self.ambient.g) / 255)),
                    min(255, int(cell.fg.b * (lb + self.ambient.b) / 255)),
                )

    def shade_char(self, intensity: float) -> str:
        if intensity <= 0:
            return ' '
        idx = int(intensity * (len(SHADE_CHARS) - 1))
        return SHADE_CHARS[min(idx, len(SHADE_CHARS) - 1)]


def render_shadows(canvas: Canvas, light_x: float, light_y: float,
                   radius: float, solid_fn, z: float = 0,
                   wall_color: Color | None = None,
                   bg_color: Color | None = None):
    wc = wall_color or Color(60, 60, 80)
    bc = bg_color or Color(8, 6, 18)
    for y in range(canvas.h):
        for x in range(canvas.w):
            dx = x - light_x
            dy = y - light_y
            dist = math.hypot(dx, dy)
            if dist > radius:
                canvas.set_pixel(x, y, ' ', bg=bc, z=z)
                continue
            hx, hy, hit_dist = cast_ray_dda(light_x, light_y,
                                            dx / dist, dy / dist,
                                            dist, solid_fn)
            if hit_dist < dist:
                canvas.set_pixel(x, y, ' ', bg=bc, z=z)
            else:
                intensity = max(0, 1 - dist / radius)
                ci = int(intensity * (len(SHADE_CHARS) - 1))
                canvas.set_pixel(x, y, SHADE_CHARS[ci], wc.mul(0.5 + 0.5 * intensity), z=z)
