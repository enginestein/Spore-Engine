from __future__ import annotations
import math
import random
from typing import Optional
from ..core.geom import Vec3, Mat4
from ..core.color import Color, Gradient
from ..core.canvas import Canvas, HiResCanvas, SHADE_CHARS


LIGHT_DEFAULT = Vec3(0, 0, -1).norm()


class Mesh3D:
    def __init__(self, name: str = ''):
        self.name = name
        self.verts: list[Vec3] = []
        self.faces: list[list[int]] = []
        self.edges: list[tuple[int, int]] = []
        self.face_colors: list[Color] = []

    @property
    def center(self) -> Vec3:
        if not self.verts: return Vec3()
        return Vec3(
            sum(v.x for v in self.verts) / len(self.verts),
            sum(v.y for v in self.verts) / len(self.verts),
            sum(v.z for v in self.verts) / len(self.verts),
        )

    def transform(self, mat: Mat4) -> Mesh3D:
        m = Mesh3D(self.name)
        m.verts = [mat.transform(v) for v in self.verts]
        m.faces = self.faces[:]
        m.edges = self.edges[:]
        m.face_colors = self.face_colors[:]
        return m

    def face_normal(self, idx: int) -> Vec3:
        f = self.faces[idx]
        if len(f) < 3: return Vec3(0, 1, 0)
        v0, v1, v2 = self.verts[f[0]], self.verts[f[1]], self.verts[f[2]]
        return (v1 - v0).cross(v2 - v0).norm()

    def face_depth(self, idx: int) -> float:
        f = self.faces[idx]
        return sum(self.verts[vi].z for vi in f) / len(f)

    @staticmethod
    def cube(size: float = 1) -> Mesh3D:
        m = Mesh3D('cube')
        s = size / 2
        m.verts = [Vec3(x, y, z) for x in (-s, s) for y in (-s, s) for z in (-s, s)]
        idx = lambda x, y, z: x * 4 + y * 2 + z
        m.faces = [
            [idx(0,0,0),idx(0,1,0),idx(0,1,1),idx(0,0,1)],
            [idx(1,0,0),idx(1,0,1),idx(1,1,1),idx(1,1,0)],
            [idx(0,0,0),idx(1,0,0),idx(1,0,1),idx(0,0,1)],
            [idx(0,1,0),idx(0,1,1),idx(1,1,1),idx(1,1,0)],
            [idx(0,0,0),idx(0,0,1),idx(1,0,1),idx(1,0,0)],
            [idx(0,1,0),idx(1,1,0),idx(1,1,1),idx(0,1,1)],
        ]
        m.edges = [(0,1),(1,3),(3,2),(2,0),(4,5),(5,7),(7,6),(6,4),(0,4),(1,5),(2,6),(3,7)]
        m.face_colors = [Color(200,50,50),Color(50,200,50),Color(50,50,200),
                         Color(200,200,50),Color(200,50,200),Color(50,200,200)]
        return m

    @staticmethod
    def sphere(radius: float = 1, rings: int = 12, sectors: int = 16) -> Mesh3D:
        m = Mesh3D('sphere')
        for r in range(rings + 1):
            theta = math.pi * r / rings
            for s in range(sectors):
                phi = 2 * math.pi * s / sectors
                x = radius * math.sin(theta) * math.cos(phi)
                y = radius * math.cos(theta)
                z = radius * math.sin(theta) * math.sin(phi)
                m.verts.append(Vec3(x, y, z))
        for r in range(rings):
            for s in range(sectors):
                a = r * sectors + s
                b = a + sectors
                m.faces.append([a, (a + 1) % sectors + r * sectors,
                                (b + 1) % sectors + (r + 1) * sectors, b])
                m.face_colors.append(Color(100, 150, 255))
        return m

    @staticmethod
    def torus(major_r: float = 1.5, minor_r: float = 0.5,
              major_seg: int = 24, minor_seg: int = 12) -> Mesh3D:
        m = Mesh3D('torus')
        for i in range(major_seg):
            theta = 2 * math.pi * i / major_seg
            for j in range(minor_seg):
                phi = 2 * math.pi * j / minor_seg
                x = (major_r + minor_r * math.cos(phi)) * math.cos(theta)
                y = minor_r * math.sin(phi)
                z = (major_r + minor_r * math.cos(phi)) * math.sin(theta)
                m.verts.append(Vec3(x, y, z))
        for i in range(major_seg):
            for j in range(minor_seg):
                a = i * minor_seg + j
                b = ((i + 1) % major_seg) * minor_seg + j
                c = ((i + 1) % major_seg) * minor_seg + (j + 1) % minor_seg
                d = i * minor_seg + (j + 1) % minor_seg
                m.faces.append([a, b, c, d])
                hue = i / major_seg
                m.face_colors.append(Color.from_hsv(hue, 0.8, 1.0))
        return m

    @staticmethod
    def icosphere(radius: float = 1, subdivisions: int = 2) -> Mesh3D:
        t = (1 + math.sqrt(5)) / 2
        verts = [Vec3(-1, t, 0), Vec3(1, t, 0), Vec3(-1, -t, 0), Vec3(1, -t, 0),
                 Vec3(0, -1, t), Vec3(0, 1, t), Vec3(0, -1, -t), Vec3(0, 1, -t),
                 Vec3(t, 0, -1), Vec3(t, 0, 1), Vec3(-t, 0, -1), Vec3(-t, 0, 1)]
        faces = [[0,11,5],[0,5,1],[0,1,7],[0,7,10],[0,10,11],
                 [1,5,9],[5,11,4],[11,10,2],[10,7,6],[7,1,8],
                 [3,9,4],[3,4,2],[3,2,6],[3,6,8],[3,8,9],
                 [4,9,5],[2,4,11],[6,2,10],[8,6,7],[9,8,1]]

        def midpoint(v1, v2):
            return Vec3((v1.x+v2.x)/2, (v1.y+v2.y)/2, (v1.z+v2.z)/2).norm() * radius

        m = Mesh3D('icosphere')
        m.verts = [v.norm() * radius for v in verts]

        def subdivide(faces, level):
            if level == 0: return faces
            new_faces = []
            mid_cache = {}
            for tri in faces:
                a, b, c = tri
                ab = midpoint(m.verts[a], m.verts[b])
                bc = midpoint(m.verts[b], m.verts[c])
                ca = midpoint(m.verts[c], m.verts[a])
                for p in (ab, bc, ca):
                    if p not in m.verts:
                        m.verts.append(p)
                iab = m.verts.index(ab)
                ibc = m.verts.index(bc)
                ica = m.verts.index(ca)
                new_faces.append([a, iab, ica])
                new_faces.append([iab, b, ibc])
                new_faces.append([ica, ibc, c])
                new_faces.append([iab, ibc, ica])
            return subdivide(new_faces, level - 1)

        m.faces = subdivide(faces, subdivisions)
        return m

    @staticmethod
    def pyramid(size: float = 1) -> Mesh3D:
        m = Mesh3D('pyramid')
        s = size / 2
        m.verts = [Vec3(-s, -s, -s), Vec3(s, -s, -s), Vec3(s, -s, s), Vec3(-s, -s, s),
                   Vec3(0, s, 0)]
        m.faces = [[0,1,4],[1,2,4],[2,3,4],[3,0,4],[0,3,2,1]]
        m.face_colors = [Color(200,50,50),Color(50,200,50),Color(50,50,200),
                         Color(200,200,50),Color(100,100,100)]
        m.edges = [(0,1),(1,2),(2,3),(3,0),(0,4),(1,4),(2,4),(3,4)]
        return m


def render_mesh_wireframe(canvas: Canvas, mesh: Mesh3D, 
                          view_mat: Mat4, proj_mat: Mat4,
                          char: str = '#', fg: Optional[Color] = None,
                          z: float = 0):
    mat = proj_mat * view_mat
    projected = []
    for v in mesh.verts:
        p = mat.transform(v)
        sx = int((p.x + 1) * 0.5 * canvas.width)
        sy = int((1 - p.y) * 0.5 * canvas.height)
        projected.append((sx, sy, p.z))
    for i, j in mesh.edges:
        x1, y1, _ = projected[i]
        x2, y2, _ = projected[j]
        depth = (projected[i][2] + projected[j][2]) / 2
        if depth > 1: continue
        shade = max(0, min(1, (1 - depth)))
        ci = int(shade * (len(SHADE_CHARS) - 1))
        cf = fg or Color(200, 200, 200)
        canvas.draw_line(x1, y1, x2, y2, SHADE_CHARS[ci], cf, z=z)


def render_mesh_solid(hires: HiResCanvas, mesh: Mesh3D,
                      view_mat: Mat4, proj_mat: Mat4,
                      light_dir: Vec3 = LIGHT_DEFAULT,
                      color_override: Optional[list[Color]] = None,
                      z_offset: float = 0):
    mat = proj_mat * view_mat
    proj_verts = []
    for v in mesh.verts:
        p = mat.transform(v)
        sx = int((p.x + 1) * 0.5 * hires.w)
        sy = int((1 - p.y) * 0.5 * hires.h)
        proj_verts.append((sx, sy, p.z))
    
    face_data = []
    for fi, face in enumerate(mesh.faces):
        if len(face) < 3: continue
        normal = mesh.face_normal(fi)
        view_dir = Vec3(-view_mat[2,0], -view_mat[2,1], -view_mat[2,2]).norm()
        if normal.dot(view_dir) >= 0: continue
        depth = mesh.face_depth(fi)
        lighting = max(0.2, normal.dot(light_dir))
        fc = color_override[fi] if color_override and fi < len(color_override) else Color(200, 200, 200)
        shaded = fc.mul(lighting)
        pts = [proj_verts[v] for v in face]
        face_data.append((depth, pts, shaded, normal))
    
    face_data.sort(key=lambda x: x[0])  # painter's algorithm
    
    for depth, pts, color, normal in face_data:
        ys = [p[1] for p in pts]
        min_y = max(0, min(ys))
        max_y = min(hires.h - 1, max(ys))
        for iy in range(min_y, max_y + 1):
            xs = []
            n = len(pts)
            for i in range(n):
                x1, y1, _ = pts[i]
                x2, y2, _ = pts[(i + 1) % n]
                if y1 == y2:
                    if y1 == iy:
                        xs.append(x1); xs.append(x2)
                    continue
                if (y1 <= iy < y2) or (y2 <= iy < y1):
                    t = (iy - y1) / (y2 - y1)
                    xs.append(int(x1 + t * (x2 - x1)))
            xs.sort()
            for k in range(0, len(xs) - 1, 2):
                xa = max(0, xs[k])
                xb = min(hires.w - 1, xs[k + 1])
                for ix in range(xa, xb + 1):
                    hires.set_pixel_z(ix, iy, color, depth + z_offset)
