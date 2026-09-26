from __future__ import annotations
import math
import numpy as np
from ..core._accel import njit
from ..core.canvas import Canvas
from ..core.glyphs import SHADE_CHARS
from ..core.color import Color as Col


#: Re-exported from core.glyphs so the ramp is defined once.
SHADE = SHADE_CHARS


@njit
def _set_bounds(b: int, x: np.ndarray, w: int, h: int):
    for i in range(1, h - 1):
        x[i * w] = -x[i * w + 1] if b == 1 else x[i * w + 1]
        x[i * w + w - 1] = -x[i * w + w - 2] if b == 1 else x[i * w + w - 2]
    for i in range(1, w - 1):
        x[i] = -x[w + i] if b == 2 else x[w + i]
        x[(h - 1) * w + i] = -x[(h - 2) * w + i] if b == 2 else x[(h - 2) * w + i]
    x[0] = 0.5 * (x[1] + x[w])
    x[w - 1] = 0.5 * (x[w - 2] + x[2 * w - 1])
    x[(h - 1) * w] = 0.5 * (x[(h - 2) * w] + x[(h - 1) * w + 1])
    x[h * w - 1] = 0.5 * (x[h * w - 2] + x[(h - 2) * w + w - 1])


@njit
def _lin_solve(b: int, x: np.ndarray, x0: np.ndarray, a: float, c: float,
               w: int, h: int, iterations: int):
    c_inv = 1.0 / c
    for _ in range(iterations):
        row = w
        for _j in range(1, h - 1):
            for i in range(1, w - 1):
                idx = i + row
                x[idx] = (x0[idx] + a * (x[idx - 1] + x[idx + 1] + x[idx - w] + x[idx + w])) * c_inv
            row += w
        _set_bounds(b, x, w, h)


@njit
def _advect(b: int, d: np.ndarray, d0: np.ndarray, u: np.ndarray, v: np.ndarray,
            dt: float, w: int, h: int):
    dtx = dt * (w - 2)
    dty = dt * (h - 2)
    for j in range(1, h - 1):
        row = j * w
        for i in range(1, w - 1):
            idx = i + row
            tmp1 = dtx * u[idx]
            tmp2 = dty * v[idx]
            x = i - tmp1
            y = j - tmp2
            if x < 0.5: x = 0.5
            if x > w - 1.5: x = w - 1.5
            i0 = int(x)
            i1 = i0 + 1
            if y < 0.5: y = 0.5
            if y > h - 1.5: y = h - 1.5
            j0 = int(y)
            j1 = j0 + 1
            s1 = x - i0
            s0 = 1.0 - s1
            t1 = y - j0
            t0 = 1.0 - t1
            d[idx] = (s0 * (t0 * d0[i0 + j0 * w] + t1 * d0[i0 + j1 * w]) +
                      s1 * (t0 * d0[i1 + j0 * w] + t1 * d0[i1 + j1 * w]))
    _set_bounds(b, d, w, h)


@njit
def _project_divergence(u: np.ndarray, v: np.ndarray, p: np.ndarray, div: np.ndarray,
                        w: int, h: int):
    h_inv = 1.0 / max(w, h)
    for j in range(1, h - 1):
        row = j * w
        for i in range(1, w - 1):
            idx = i + row
            div[idx] = -0.5 * h_inv * (u[idx + 1] - u[idx - 1] + v[idx + w] - v[idx - w])
            p[idx] = 0


@njit
def _project_gradient(u: np.ndarray, v: np.ndarray, p: np.ndarray, w: int, h: int):
    h_sc = max(w, h)
    for j in range(1, h - 1):
        row = j * w
        for i in range(1, w - 1):
            idx = i + row
            u[idx] -= 0.5 * h_sc * (p[idx + 1] - p[idx - 1])
            v[idx] -= 0.5 * h_sc * (p[idx + w] - p[idx - w])


@njit
def _vorticity_step(u: np.ndarray, v: np.ndarray, dt: float, strength: float,
                    w: int, h: int):
    curl = np.zeros(w * h, dtype=np.float64)
    for j in range(1, h - 1):
        row = j * w
        for i in range(1, w - 1):
            idx = i + row
            curl[idx] = (v[idx + 1] - v[idx - 1]) - (u[idx + w] - u[idx - w])
    for j in range(2, h - 2):
        row = j * w
        for i in range(2, w - 2):
            idx = i + row
            dx = abs(curl[idx + 1]) - abs(curl[idx - 1])
            dy = abs(curl[idx + w]) - abs(curl[idx - w])
            mag = math.sqrt(dx * dx + dy * dy) + 1e-5
            nx = dx / mag
            ny = dy / mag
            omega = curl[idx]
            u[idx] += dt * strength * ny * omega
            v[idx] -= dt * strength * nx * omega


class FluidSim:
    def __init__(self, width: int, height: int, viscosity: float = 0.0001, diffusion: float = 0.0001):
        self.w = width
        self.h = height
        self.size = width * height
        self.visc = viscosity
        self.diff = diffusion

        self.u = np.zeros(self.size, dtype=np.float64)
        self.v = np.zeros(self.size, dtype=np.float64)
        self.dye = np.zeros(self.size, dtype=np.float64)
        self.u_prev = np.zeros(self.size, dtype=np.float64)
        self.v_prev = np.zeros(self.size, dtype=np.float64)
        self.dye_prev = np.zeros(self.size, dtype=np.float64)

        self.dt = 0.1
        self.iterations = 20
        self.vorticity_strength = 0.15

    def _work(self, n: int) -> np.ndarray:
        return np.zeros(n, dtype=np.float64)

    def add_dye(self, x: int, y: int, amount: float, r: int = 3):
        w, h = self.w, self.h
        for dy in range(-r, r + 1):
            for dx in range(-r, r + 1):
                d_sq = dx * dx + dy * dy
                if d_sq <= r * r:
                    px, py = x + dx, y + dy
                    if 0 <= px < w and 0 <= py < h:
                        self.dye[py * w + px] += amount * (1.0 - math.sqrt(d_sq) / r)

    def add_velocity(self, x: int, y: int, ux: float, uy: float, r: int = 3):
        w, h = self.w, self.h
        for dy in range(-r, r + 1):
            for dx in range(-r, r + 1):
                if dx * dx + dy * dy <= r * r:
                    px, py = x + dx, y + dy
                    if 0 <= px < w and 0 <= py < h:
                        idx = py * w + px
                        self.u[idx] += ux
                        self.v[idx] += uy

    def _diffuse(self, b: int, x: np.ndarray, x0: np.ndarray, diff: float, dt: float):
        a = dt * diff * (self.w - 2) * (self.h - 2)
        _lin_solve(b, x, x0, a, 1 + 4 * a, self.w, self.h, self.iterations)

    def _project(self, u: np.ndarray, v: np.ndarray, p: np.ndarray, div: np.ndarray):
        _project_divergence(u, v, p, div, self.w, self.h)
        _set_bounds(0, div, self.w, self.h)
        _set_bounds(0, p, self.w, self.h)
        _lin_solve(0, p, div, 1, 4, self.w, self.h, self.iterations)
        _project_gradient(u, v, p, self.w, self.h)
        _set_bounds(1, u, self.w, self.h)
        _set_bounds(2, v, self.w, self.h)

    def step(self, dt: float = 0.1):
        self.dt = dt
        w, h = self.w, self.h

        self._diffuse(1, self.u_prev, self.u, self.visc, dt)
        self._diffuse(2, self.v_prev, self.v, self.visc, dt)
        self._project(self.u_prev, self.v_prev, self.u, self.v)
        _advect(1, self.u, self.u_prev, self.u_prev, self.v_prev, dt, w, h)
        _advect(2, self.v, self.v_prev, self.u_prev, self.v_prev, dt, w, h)
        _vorticity_step(self.u, self.v, dt, self.vorticity_strength, w, h)

        p = self._work(self.size)
        div = self._work(self.size)
        self._project(self.u, self.v, p, div)

        self._diffuse(0, self.dye_prev, self.dye, self.diff, dt)
        _advect(0, self.dye, self.dye_prev, self.u, self.v, dt, w, h)

        self.u_prev[:] = self.u
        self.v_prev[:] = self.v
        self.dye_prev[:] = self.dye

    def render(self, canvas: Canvas, ox: int = 0, oy: int = 0, t: float = 0, mode: str = 'dye'):
        w, h = self.w, self.h
        for y in range(min(h, canvas.height - oy)):
            for x in range(min(w, canvas.width - ox)):
                idx = y * w + x
                if mode == 'speed':
                    v = math.sqrt(self.u[idx] ** 2 + self.v[idx] ** 2) * 5.0
                else:
                    v = self.dye[idx]
                v = max(0, min(1, v))
                if v < 0.01:
                    continue
                hue = (0.6 + v * 0.2 + t * 0.02) % 1.0
                sat = 0.8 - v * 0.4
                val = 0.3 + v * 0.7
                color = Col.from_hsv(hue, sat, val)
                ci = int(v * (len(SHADE) - 1))
                canvas.set_pixel(x + ox, y + oy, SHADE[ci], color)


class WaveSim:
    def __init__(self, width: int, height: int, damping: float = 0.99):
        self.w = width
        self.h = height
        self.damping = damping
        self.current = np.zeros((height, width), dtype=np.float64)
        self.previous = np.zeros((height, width), dtype=np.float64)

    def splash(self, x: int, y: int, force: float = 2.0, r: int = 3):
        for dy in range(-r, r + 1):
            for dx in range(-r, r + 1):
                d = math.sqrt(dx * dx + dy * dy)
                if d <= r:
                    px, py = x + dx, y + dy
                    if 0 <= px < self.w and 0 <= py < self.h:
                        self.previous[py, px] += force * (1.0 - d / r)

    def step(self):
        w, h = self.w, self.h
        cur = self.current
        prev = self.previous
        damping = self.damping
        for y in range(1, h - 1):
            for x in range(1, w - 1):
                val = (prev[y - 1, x] + prev[y + 1, x] + prev[y, x - 1] + prev[y, x + 1]) * 0.5 - cur[y, x]
                cur[y, x] = val * damping
        self.current, self.previous = self.previous, self.current

    def render(self, canvas: Canvas, ox: int = 0, oy: int = 0, t: float = 0):
        w, h = self.w, self.h
        prev = self.previous
        for y in range(min(h, canvas.height - oy)):
            for x in range(min(w, canvas.width - ox)):
                v = prev[y, x]
                if abs(v) < 0.02:
                    continue
                intensity = min(1.0, abs(v))
                ci = int(intensity * (len(SHADE) - 1))
                if v > 0:
                    hue = 0.6
                    val = 0.4 + intensity * 0.6
                else:
                    hue = 0.55
                    val = 0.3 + intensity * 0.4
                color = Col.from_hsv(hue, 0.8 - intensity * 0.5, val)
                canvas.set_pixel(x + ox, y + oy, SHADE[ci], color)
