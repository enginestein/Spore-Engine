from __future__ import annotations
import math
from typing import Optional
from ..core.color import Color, BLACK, WHITE
from ..core.canvas import HiResCanvas


class Ray:
    __slots__ = ('origin', 'dir', 'depth')
    def __init__(self, ox: float, oy: float, oz: float,
                 dx: float, dy: float, dz: float, depth: int = 0):
        self.origin = (ox, oy, oz)
        self.dir = (dx, dy, dz)
        self.depth = depth


class Sphere:
    def __init__(self, cx: float, cy: float, cz: float, r: float,
                 color: Color, reflect: float = 0, refract: float = 0,
                 ior: float = 1.5, emissive: float = 0):
        self.cx, self.cy, self.cz = cx, cy, cz
        self.r = r
        self.color = color
        self.reflect = reflect
        self.refract = refract
        self.ior = ior
        self.emissive = emissive

    def intersect(self, ray: Ray) -> Optional[float]:
        ox, oy, oz = ray.origin
        dx, dy, dz = ray.dir
        ocx = ox - self.cx
        ocy = oy - self.cy
        ocz = oz - self.cz
        a = dx * dx + dy * dy + dz * dz
        b = 2 * (ocx * dx + ocy * dy + ocz * dz)
        c = ocx * ocx + ocy * ocy + ocz * ocz - self.r * self.r
        disc = b * b - 4 * a * c
        if disc < 0:
            return None
        sqrt_disc = math.sqrt(disc)
        t1 = (-b - sqrt_disc) / (2 * a)
        t2 = (-b + sqrt_disc) / (2 * a)
        if t1 > 0.001:
            return t1
        if t2 > 0.001:
            return t2
        return None

    def normal_at(self, x: float, y: float, z: float):
        nx = (x - self.cx) / self.r
        ny = (y - self.cy) / self.r
        nz = (z - self.cz) / self.r
        d = math.sqrt(nx * nx + ny * ny + nz * nz)
        return (nx / d, ny / d, nz / d)


class Plane:
    def __init__(self, nx: float, ny: float, nz: float, d: float,
                 color: Color, reflect: float = 0, emissive: float = 0):
        self.nx, self.ny, self.nz = nx, ny, nz
        self.d = d
        self.color = color
        self.reflect = reflect
        self.emissive = emissive

    def intersect(self, ray: Ray) -> Optional[float]:
        denom = self.nx * ray.dir[0] + self.ny * ray.dir[1] + self.nz * ray.dir[2]
        if abs(denom) < 0.0001:
            return None
        t = (self.d - (self.nx * ray.origin[0] + self.ny * ray.origin[1] + self.nz * ray.origin[2])) / denom
        return t if t > 0.001 else None

    def normal_at(self, x: float, y: float, z: float):
        d = math.sqrt(self.nx * self.nx + self.ny * self.ny + self.nz * self.nz)
        return (self.nx / d, self.ny / d, self.nz / d)


class Box:
    def __init__(self, cx: float, cy: float, cz: float,
                 sx: float, sy: float, sz: float,
                 color: Color, reflect: float = 0, emissive: float = 0):
        self.cx, self.cy, self.cz = cx, cy, cz
        self.sx, self.sy, self.sz = sx, sy, sz
        self.color = color
        self.reflect = reflect
        self.emissive = emissive

    def intersect(self, ray: Ray) -> Optional[float]:
        ox, oy, oz = ray.origin
        dx, dy, dz = ray.dir
        xmin = self.cx - self.sx / 2
        xmax = self.cx + self.sx / 2
        ymin = self.cy - self.sy / 2
        ymax = self.cy + self.sy / 2
        zmin = self.cz - self.sz / 2
        zmax = self.cz + self.sz / 2
        if dx == 0:
            if ox < xmin or ox > xmax: return None
            t1x, t2x = -1e99, 1e99
        elif dx > 0:
            t1x, t2x = (xmin - ox) / dx, (xmax - ox) / dx
        else:
            t1x, t2x = (xmax - ox) / dx, (xmin - ox) / dx
        if dy == 0:
            if oy < ymin or oy > ymax: return None
            t1y, t2y = -1e99, 1e99
        elif dy > 0:
            t1y, t2y = (ymin - oy) / dy, (ymax - oy) / dy
        else:
            t1y, t2y = (ymax - oy) / dy, (ymin - oy) / dy
        if dz == 0:
            if oz < zmin or oz > zmax: return None
            t1z, t2z = -1e99, 1e99
        elif dz > 0:
            t1z, t2z = (zmin - oz) / dz, (zmax - oz) / dz
        else:
            t1z, t2z = (zmax - oz) / dz, (zmin - oz) / dz
        tmin = max(t1x, t1y, t1z)
        tmax = min(t2x, t2y, t2z)
        if tmin > tmax: return None
        if tmax < 0: return None
        return tmin if tmin > 0.001 else (tmax if tmax > 0.001 else None)

    def normal_at(self, x: float, y: float, z: float):
        cx, cy, cz = self.cx, self.cy, self.cz
        hx, hy, hz = self.sx / 2, self.sy / 2, self.sz / 2
        dx = abs(x - cx) - hx
        dy = abs(y - cy) - hy
        dz = abs(z - cz) - hz
        eps = 0.0001
        if dx > -eps and dx < eps:
            return (1 if x > cx else -1, 0, 0)
        if dy > -eps and dy < eps:
            return (0, 1 if y > cy else -1, 0)
        if dz > -eps and dz < eps:
            return (0, 0, 1 if z > cz else -1)
        px, py, pz = abs(x - cx) / hx, abs(y - cy) / hy, abs(z - cz) / hz
        if px >= py and px >= pz: return (1 if x > cx else -1, 0, 0)
        if py >= pz: return (0, 1 if y > cy else -1, 0)
        return (0, 0, 1 if z > cz else -1)


class Cylinder:
    def __init__(self, cx: float, cy: float, cz: float,
                 r: float, h: float,
                 color: Color, reflect: float = 0, emissive: float = 0):
        self.cx, self.cy, self.cz = cx, cy, cz
        self.r = r
        self.h = h
        self.color = color
        self.reflect = reflect
        self.emissive = emissive

    def intersect(self, ray: Ray) -> Optional[float]:
        ox, oy, oz = ray.origin
        dx, dy, dz = ray.dir
        half_h = self.h / 2
        ocx, ocz = ox - self.cx, oz - self.cz
        a = dx * dx + dz * dz
        if a < 0.0001:
            return self._intersect_caps(ox, oy, oz, dx, dy, dz, half_h)
        b = 2 * (ocx * dx + ocz * dz)
        c = ocx * ocx + ocz * ocz - self.r * self.r
        disc = b * b - 4 * a * c
        if disc < 0:
            return self._intersect_caps(ox, oy, oz, dx, dy, dz, half_h)
        sqrt_disc = math.sqrt(disc)
        t1 = (-b - sqrt_disc) / (2 * a)
        t2 = (-b + sqrt_disc) / (2 * a)
        if t1 > t2: t1, t2 = t2, t1
        y1 = oy + t1 * dy
        if self.cy - half_h <= y1 <= self.cy + half_h and t1 > 0.001:
            return t1
        y2 = oy + t2 * dy
        if self.cy - half_h <= y2 <= self.cy + half_h and t2 > 0.001:
            return t2
        return self._intersect_caps(ox, oy, oz, dx, dy, dz, half_h)

    def _intersect_caps(self, ox, oy, oz, dx, dy, dz, half_h):
        best_t = None
        for sign, cy_face in [(1, self.cy + half_h), (-1, self.cy - half_h)]:
            if abs(dy) < 0.0001: continue
            t = (cy_face - oy) / dy
            if t <= 0.001: continue
            px = ox + t * dx
            pz = oz + t * dz
            if (px - self.cx) ** 2 + (pz - self.cz) ** 2 <= self.r ** 2:
                if best_t is None or t < best_t: best_t = t
        return best_t

    def normal_at(self, x: float, y: float, z: float):
        half_h = self.h / 2
        eps = 0.0001
        if abs(y - (self.cy + half_h)) < eps: return (0, 1, 0)
        if abs(y - (self.cy - half_h)) < eps: return (0, -1, 0)
        nx, nz = x - self.cx, z - self.cz
        d = math.sqrt(nx * nx + nz * nz)
        return (nx / d, 0, nz / d) if d else (0, 0, 1)


class TexturedQuad:
    def __init__(self, cx: float, cy: float, cz: float,
                 w: float, h: float, image_path: str,
                 reflect: float = 0, emissive: float = 0):
        self.cx, self.cy, self.cz = cx, cy, cz
        self.w, self.h = w, h
        self.reflect = reflect
        self.emissive = emissive
        self.nx, self.ny, self.nz = 0, 0, 1
        self._build_basis()
        from PIL import Image
        img = Image.open(image_path).convert('RGBA')
        self.img = img
        self.img_w, self.img_h = img.size
        self.pixels = list(img.getdata())

    def _build_basis(self):
        nx, ny, nz = self.nx, self.ny, self.nz
        up = (0, 1, 0) if abs(ny) < 0.9 else (0, 0, 1)
        rx = ny * up[2] - nz * up[1]
        ry = nz * up[0] - nx * up[2]
        rz = nx * up[1] - ny * up[0]
        rd = math.sqrt(rx*rx + ry*ry + rz*rz)
        self.rx, self.ry, self.rz = rx/rd, ry/rd, rz/rd
        self.ux = self.ry * nz - self.rz * ny
        self.uy = self.rz * nx - self.rx * nz
        self.uz = self.rx * ny - self.ry * nx
        ud = math.sqrt(self.ux*self.ux + self.uy*self.uy + self.uz*self.uz)
        self.ux, self.uy, self.uz = self.ux/ud, self.uy/ud, self.uz/ud

    def face_toward(self, tx: float, ty: float, tz: float):
        dx = tx - self.cx
        dy = ty - self.cy
        dz = tz - self.cz
        d = math.sqrt(dx*dx + dy*dy + dz*dz)
        if d == 0: return
        self.nx, self.ny, self.nz = dx/d, dy/d, dz/d
        self._build_basis()

    def intersect(self, ray: Ray):
        denom = self.nx * ray.dir[0] + self.ny * ray.dir[1] + self.nz * ray.dir[2]
        if abs(denom) < 0.0001: return None
        t = ((self.cx - ray.origin[0]) * self.nx +
             (self.cy - ray.origin[1]) * self.ny +
             (self.cz - ray.origin[2]) * self.nz) / denom
        if t < 0.001: return None
        px = ray.origin[0] + ray.dir[0] * t
        py = ray.origin[1] + ray.dir[1] * t
        pz = ray.origin[2] + ray.dir[2] * t
        dx = px - self.cx
        dy = py - self.cy
        dz = pz - self.cz
        u = dx * self.rx + dy * self.ry + dz * self.rz
        v = dx * self.ux + dy * self.uy + dz * self.uz
        if abs(u) > self.w/2 or abs(v) > self.h/2: return None
        return t

    def normal_at(self, x: float, y: float, z: float):
        return (self.nx, self.ny, self.nz)

    def color_at(self, x: float, y: float, z: float) -> Color:
        dx = x - self.cx
        dy = y - self.cy
        dz = z - self.cz
        u = dx * self.rx + dy * self.ry + dz * self.rz
        v = dx * self.ux + dy * self.uy + dz * self.uz
        px = int((u / self.w + 0.5) * (self.img_w - 1))
        py = int((0.5 - v / self.h) * (self.img_h - 1))
        px = max(0, min(px, self.img_w - 1))
        py = max(0, min(py, self.img_h - 1))
        r, g, b, a = self.pixels[py * self.img_w + px]
        return Color(r, g, b)


class RayScene:
    def __init__(self):
        self.objects: list = []
        self.lights: list[tuple[float, float, float, Color, float]] = []
        self.ambient = Color(30, 30, 50)
        self.bg_color = Color(10, 10, 30)
        self.max_depth = 3

    def trace(self, ray: Ray) -> Color:
        if ray.depth > self.max_depth:
            return self.bg_color
        hit_t = float('inf')
        hit_obj = None
        for obj in self.objects:
            t = obj.intersect(ray)
            if t and t < hit_t:
                hit_t = t
                hit_obj = obj
        if hit_obj is None:
            return self.bg_color
        px = ray.origin[0] + ray.dir[0] * hit_t
        py = ray.origin[1] + ray.dir[1] * hit_t
        pz = ray.origin[2] + ray.dir[2] * hit_t
        nx, ny, nz = hit_obj.normal_at(px, py, pz)
        surface_color = hit_obj.color_at(px, py, pz) if hasattr(hit_obj, 'color_at') else hit_obj.color
        color = self.ambient.lerp(surface_color, 0.3)
        for lx, ly, lz, lcol, lpower in self.lights:
            ldx = lx - px
            ldy = ly - py
            ldz = lz - pz
            ld = math.sqrt(ldx * ldx + ldy * ldy + ldz * ldz)
            if ld == 0:
                continue
            ldx /= ld; ldy /= ld; ldz /= ld
            dot = nx * ldx + ny * ldy + nz * ldz
            if dot > 0:
                shadow_ray = Ray(px + nx * 0.001, py + ny * 0.001, pz + nz * 0.001, ldx, ldy, ldz, ray.depth + 1)
                in_shadow = False
                for obj in self.objects:
                    if obj is hit_obj:
                        continue
                    t = obj.intersect(shadow_ray)
                    if t and t < ld:
                        in_shadow = True
                        break
                if not in_shadow:
                    diffuse = surface_color.mul(dot * lpower * 0.6)
                    color = Color(
                        min(255, color.r + diffuse.r),
                        min(255, color.g + diffuse.g),
                        min(255, color.b + diffuse.b),
                    )
            # specular
            if dot > 0:
                rdx = 2 * dot * nx - ldx
                rdy = 2 * dot * ny - ldy
                rdz = 2 * dot * nz - ldz
                vdot = -(rdx * ray.dir[0] + rdy * ray.dir[1] + rdz * ray.dir[2])
                if vdot > 0:
                    spec = pow(vdot, 32) * lpower * 0.5
                    color = Color(
                        min(255, color.r + int(255 * spec)),
                        min(255, color.g + int(255 * spec)),
                        min(255, color.b + int(255 * spec)),
                    )
        if hit_obj.emissive > 0:
            color = color.blend(surface_color, hit_obj.emissive)
        if hit_obj.reflect > 0 and ray.depth < self.max_depth:
            rdx = ray.dir[0] - 2 * (nx * ray.dir[0] + ny * ray.dir[1] + nz * ray.dir[2]) * nx
            rdy = ray.dir[1] - 2 * (nx * ray.dir[0] + ny * ray.dir[1] + nz * ray.dir[2]) * ny
            rdz = ray.dir[2] - 2 * (nx * ray.dir[0] + ny * ray.dir[1] + nz * ray.dir[2]) * nz
            rd = math.sqrt(rdx * rdx + rdy * rdy + rdz * rdz)
            reflect_ray = Ray(px + nx * 0.001, py + ny * 0.001, pz + nz * 0.001,
                              rdx / rd, rdy / rd, rdz / rd, ray.depth + 1)
            reflected = self.trace(reflect_ray)
            color = color.blend(reflected, hit_obj.reflect)
        return color

    def render(self, hires: HiResCanvas, cam_pos: tuple[float, float, float],
               cam_target: tuple[float, float, float], fov: float = 60):
        cpx, cpy, cpz = cam_pos
        forward = (cam_target[0] - cpx, cam_target[1] - cpy, cam_target[2] - cpz)
        fd = math.sqrt(forward[0] ** 2 + forward[1] ** 2 + forward[2] ** 2)
        forward = (forward[0] / fd, forward[1] / fd, forward[2] / fd)
        world_up = (0, 1, 0)
        right = (world_up[1] * forward[2] - world_up[2] * forward[1],
                 world_up[2] * forward[0] - world_up[0] * forward[2],
                 world_up[0] * forward[1] - world_up[1] * forward[0])
        rd = math.sqrt(right[0] ** 2 + right[1] ** 2 + right[2] ** 2)
        right = (right[0] / rd, right[1] / rd, right[2] / rd)
        up = (forward[1] * right[2] - forward[2] * right[1],
              forward[2] * right[0] - forward[0] * right[2],
              forward[0] * right[1] - forward[1] * right[0])
        aspect = hires.w / hires.h
        tan_fov = math.tan(math.radians(fov) * 0.5)
        for y in range(hires.h):
            for x in range(hires.w):
                sx = (2 * (x + 0.5) / hires.w - 1) * aspect * tan_fov
                sy = (1 - 2 * (y + 0.5) / hires.h) * tan_fov
                rdx = forward[0] + right[0] * sx + up[0] * sy
                rdy = forward[1] + right[1] * sx + up[1] * sy
                rdz = forward[2] + right[2] * sx + up[2] * sy
                rd = math.sqrt(rdx * rdx + rdy * rdy + rdz * rdz)
                ray = Ray(cpx, cpy, cpz, rdx / rd, rdy / rd, rdz / rd)
                color = self.trace(ray)
                hires.set_pixel(x, y, '@', color)
