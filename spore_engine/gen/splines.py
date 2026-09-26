from __future__ import annotations
from ..core.canvas import Canvas
from ..core.color import Color, WHITE, DIM, RED, GREEN, BLUE


def lerp_point(a: tuple[float, float], b: tuple[float, float], t: float) -> tuple[float, float]:
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)


def quadratic_bezier(p0, p1, p2, t: float) -> tuple[float, float]:
    return lerp_point(lerp_point(p0, p1, t), lerp_point(p1, p2, t), t)


def cubic_bezier(p0, p1, p2, p3, t: float) -> tuple[float, float]:
    return lerp_point(quadratic_bezier(p0, p1, p2, t), quadratic_bezier(p1, p2, p3, t), t)


def catmull_rom(p0, p1, p2, p3, t: float) -> tuple[float, float]:
    t2 = t * t
    t3 = t2 * t
    x = 0.5 * ((2 * p1[0]) + (-p0[0] + p2[0]) * t +
               (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2 +
               (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3)
    y = 0.5 * ((2 * p1[1]) + (-p0[1] + p2[1]) * t +
               (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2 +
               (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3)
    return (x, y)


def render_bezier(c: Canvas, pts: list[tuple[float, float]], steps: int = 30,
                  fg: Color = WHITE, z: float = 10, show_control: bool = True,
                  show_decasteljau: bool = False, t_progress: float = -1):
    if len(pts) < 2:
        return
    if len(pts) == 2:
        c.draw_line(int(pts[0][0]), int(pts[0][1]),
                    int(pts[1][0]), int(pts[1][1]), '─', fg, z=z)
        return
    if show_control:
        for i in range(len(pts)):
            px, py = int(pts[i][0]), int(pts[i][1])
            c.set_pixel(px, py, '●', RED if i == 0 or i == len(pts)-1 else BLUE, z=z+1)
            if i < len(pts) - 1:
                c.draw_line(px, py, int(pts[i+1][0]), int(pts[i+1][1]),
                           '·', DIM, z=z-1)
    if show_decasteljau and t_progress >= 0:
        working = list(pts)
        colors = [Color.from_hsv(0.05 * i, 0.8, 0.6) for i in range(len(pts))]
        level = 0
        while len(working) > 1:
            nxt = []
            for i in range(len(working) - 1):
                p = lerp_point(working[i], working[i+1], t_progress)
                px, py = int(p[0]), int(p[1])
                if 0 <= px < c.w and 0 <= py < c.h:
                    c.set_pixel(px, py, '○', colors[level], z=z+2)
                    c.draw_line(int(working[i][0]), int(working[i][1]),
                               int(working[i+1][0]), int(working[i+1][1]),
                               '·', colors[level].mul(0.5), z=z-1)
                nxt.append(p)
            working = nxt
            level += 1
    cubic_bezier if len(pts) == 4 else quadratic_bezier
    for i in range(steps + 1):
        t = i / steps
        if len(pts) == 4:
            p = cubic_bezier(pts[0], pts[1], pts[2], pts[3], t)
        else:
            p = quadratic_bezier(pts[0], pts[1], pts[2], t)
        px, py = int(p[0]), int(p[1])
        if 0 <= px < c.w and 0 <= py < c.h:
            if t_progress < 0 or t <= t_progress:
                c.set_pixel(px, py, '▓', fg, z=z)


def render_catmull_rom(c: Canvas, pts: list[tuple[float, float]], steps: int = 30,
                       fg: Color = WHITE, z: float = 10, closed: bool = False,
                       show_control: bool = True):
    if len(pts) < 2:
        return
    if show_control:
        for _i, (px, py) in enumerate(pts):
            c.set_pixel(int(px), int(py), '●', GREEN, z=z+1)
    n = len(pts)
    segments = list(range(n - 1))
    if closed and n >= 3:
        segments = list(range(n))
    for i in segments:
        p0 = pts[(i - 1) % n]
        p1 = pts[i]
        p2 = pts[(i + 1) % n]
        p3 = pts[(i + 2) % n]
        for j in range(steps + 1):
            t = j / steps
            p = catmull_rom(p0, p1, p2, p3, t)
            px, py = int(p[0]), int(p[1])
            if 0 <= px < c.w and 0 <= py < c.h:
                c.set_pixel(px, py, '▓', fg, z=z)
