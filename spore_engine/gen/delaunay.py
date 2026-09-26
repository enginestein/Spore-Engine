from __future__ import annotations
import math
import random
from ..core.canvas import Canvas
from ..core.color import Color


class Point:
    __slots__ = ('x', 'y', 'z')
    def __init__(self, x: float, y: float, z: float = 0):
        self.x = x
        self.y = y
        self.z = z

    def dist(self, o: Point) -> float:
        return math.hypot(self.x - o.x, self.y - o.y)

    def __eq__(self, o): return isinstance(o, Point) and self.x == o.x and self.y == o.y
    def __hash__(self): return hash((self.x, self.y))


class Triangle:
    __slots__ = ('a', 'b', 'c', 'circum_r2', 'circum_x', 'circum_y')
    def __init__(self, a: Point, b: Point, c: Point):
        self.a = a
        self.b = b
        self.c = c
        self.circum_x = 0
        self.circum_y = 0
        self.circum_r2 = 0
        self._compute_circumcircle()

    def _compute_circumcircle(self):
        d = 2 * (self.a.x * (self.b.y - self.c.y) +
                 self.b.x * (self.c.y - self.a.y) +
                 self.c.x * (self.a.y - self.b.y))
        if abs(d) < 1e-10:
            return
        ax2 = self.a.x * self.a.x + self.a.y * self.a.y
        bx2 = self.b.x * self.b.x + self.b.y * self.b.y
        cx2 = self.c.x * self.c.x + self.c.y * self.c.y
        self.circum_x = ((ax2 * (self.b.y - self.c.y) +
                          bx2 * (self.c.y - self.a.y) +
                          cx2 * (self.a.y - self.b.y)) / d)
        self.circum_y = ((ax2 * (self.c.x - self.b.x) +
                          bx2 * (self.a.x - self.c.x) +
                          cx2 * (self.b.x - self.a.x)) / d)
        dx = self.a.x - self.circum_x
        dy = self.a.y - self.circum_y
        self.circum_r2 = dx * dx + dy * dy

    def in_circumcircle(self, p: Point) -> bool:
        dx = p.x - self.circum_x
        dy = p.y - self.circum_y
        return dx * dx + dy * dy <= self.circum_r2

    def has_vertex(self, p: Point) -> bool:
        return self.a == p or self.b == p or self.c == p

    def edges(self) -> list[tuple[Point, Point]]:
        return [(self.a, self.b), (self.b, self.c), (self.c, self.a)]


class Delaunay:
    def __init__(self):
        self.points: list[Point] = []
        self.triangles: list[Triangle] = []

    def add_point(self, x: float, y: float) -> Point:
        p = Point(x, y)
        self.points.append(p)
        return p

    def triangulate(self, points: list[Point] | None = None) -> list[Triangle]:
        if points is not None:
            self.points = points
        pts = self.points
        if len(pts) < 3:
            return []

        xs = [p.x for p in pts]
        ys = [p.y for p in pts]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        dx = max_x - min_x or 1
        dy = max_y - min_y or 1
        margin = max(dx, dy) * 10

        super_a = Point(min_x - margin, min_y - margin)
        super_b = Point(max_x + margin, min_y - margin)
        super_c = Point((min_x + max_x) / 2, max_y + margin)
        super_tri = Triangle(super_a, super_b, super_c)

        tris = [super_tri]

        for p in pts:
            bad_tris = []
            for t in tris:
                if t.in_circumcircle(p):
                    bad_tris.append(t)

            edges: list[tuple[Point, Point]] = []
            for t in bad_tris:
                for e in t.edges():
                    shared = False
                    for ot in bad_tris:
                        if ot == t:
                            continue
                        if e in ot.edges() or (e[1], e[0]) in ot.edges():
                            shared = True
                            break
                    if not shared:
                        edges.append(e)

            for t in bad_tris:
                tris.remove(t)

            for e in edges:
                tris.append(Triangle(e[0], e[1], p))

        self.triangles = [t for t in tris if not (
            t.has_vertex(super_a) or t.has_vertex(super_b) or t.has_vertex(super_c))]
        return self.triangles

    def voronoi(self) -> list[tuple[Point, list[Point]]]:
        regions: dict[Point, list[Point]] = {p: [] for p in self.points}
        for t in self.triangles:
            cp = Point(t.circum_x, t.circum_y)
            for v in [t.a, t.b, t.c]:
                if v in regions:
                    regions[v].append(cp)
        cells = []
        for p, verts in regions.items():
            if len(verts) >= 3:
                angles = sorted(verts, key=lambda v: math.atan2(v.y - p.y, v.x - p.x))
                cells.append((p, angles))
        return cells

    def render(self, canvas: Canvas, ox: int = 0, oy: int = 0,
               show_vertices: bool = True, show_edges: bool = True,
               color: Color | None = None):
        col = color or Color(100, 200, 255)
        if show_edges:
            for t in self.triangles:
                for a, b in t.edges():
                    canvas.draw_line(
                        int(a.x) + ox, int(a.y) + oy,
                        int(b.x) + ox, int(b.y) + oy,
                        '+', col, z=1,
                    )
        if show_vertices:
            for p in self.points:
                canvas.set_pixel(int(p.x) + ox, int(p.y) + oy, '●', Color(255, 200, 100), z=2)

    def render_voronoi(self, canvas: Canvas, ox: int = 0, oy: int = 0,
                       color: Color | None = None):
        col = color or Color(100, 255, 150)
        cells = self.voronoi()
        for _, verts in cells:
            if len(verts) < 2:
                continue
            for i in range(len(verts)):
                a, b = verts[i], verts[(i + 1) % len(verts)]
                canvas.draw_line(
                    int(a.x) + ox, int(a.y) + oy,
                    int(b.x) + ox, int(b.y) + oy,
                    '.', col, z=1,
                )

    @staticmethod
    def random_points(count: int, w: float, h: float, seed: int = 0) -> list[Point]:
        rng = random.Random(seed)
        return [Point(rng.random() * w, rng.random() * h) for _ in range(count)]
