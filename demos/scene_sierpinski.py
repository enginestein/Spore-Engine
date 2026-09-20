import math
import random
from spore_engine import *
from spore_engine.core.color import *
from spore_engine.render3d.engine3d import Mesh3D, render_mesh_solid

_ST = None


def _init(w, h):
    global _ST
    if _ST is not None:
        return
    rnd = random.Random(3)
    _ST = {
        'stars': [(rnd.uniform(0, w), rnd.uniform(0, h * 0.8),
                   rnd.uniform(0, 2 * math.pi), rnd.uniform(0.2, 1.0))
                  for _ in range(90)],
    }


def _mid(a, b):
    return ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, (a[2] + b[2]) / 2)


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])


def _sub_tetras(verts, depth, out):
    if depth == 0:
        out.append(verts)
        return
    a, b, c, d = verts
    ab, ac, ad = _mid(a, b), _mid(a, c), _mid(a, d)
    bc, bd, cd = _mid(b, c), _mid(b, d), _mid(c, d)
    _sub_tetras((a, ab, ac, ad), depth - 1, out)
    _sub_tetras((b, ab, bc, bd), depth - 1, out)
    _sub_tetras((c, ac, bc, cd), depth - 1, out)
    _sub_tetras((d, ad, bd, cd), depth - 1, out)


def _build_mesh(depth=3):
    size = 3.2
    a = (0.0, size * 0.942, 0.0)
    b = (-size * 0.5, -size * 0.314, size * 0.288)
    c = (size * 0.5, -size * 0.314, size * 0.288)
    d = (0.0, -size * 0.314, -size * 0.577)

    tetras = []
    _sub_tetras((a, b, c, d), depth, tetras)

    m = Mesh3D('sierpinski')
    verts = []
    index = {}
    for tet in tetras:
        a, b, c, d = tet
        centroid = ((a[0] + b[0] + c[0] + d[0]) / 4,
                    (a[1] + b[1] + c[1] + d[1]) / 4,
                    (a[2] + b[2] + c[2] + d[2]) / 4)
        for tri in ((a, b, c), (a, d, b), (a, c, d), (b, d, c)):
            v0, v1, v2 = tri
            n = _cross((v1[0] - v0[0], v1[1] - v0[1], v1[2] - v0[2]),
                       (v2[0] - v0[0], v2[1] - v0[1], v2[2] - v0[2]))
            face_mid = ((v0[0] + v1[0] + v2[0]) / 3,
                        (v0[1] + v1[1] + v2[1]) / 3,
                        (v0[2] + v1[2] + v2[2]) / 3)
            outward = ((face_mid[0] - centroid[0]) * n[0]
                       + (face_mid[1] - centroid[1]) * n[1]
                       + (face_mid[2] - centroid[2]) * n[2])
            if outward < 0:
                v0, v2 = v2, v0
            idx = []
            for p in (v0, v1, v2):
                key = (round(p[0], 4), round(p[1], 4), round(p[2], 4))
                if key not in index:
                    index[key] = len(verts)
                    verts.append(Vec3(p[0], p[1], p[2]))
                idx.append(index[key])
            m.faces.append(idx)
            cyc = (face_mid[1] / size) * 0.5 + 0.5
            m.face_colors.append(Color.from_hsv(0.55 + 0.35 * cyc, 0.8, 1.0))
    m.verts = verts
    return m


def scene_sierpinski(c, hr, t, pt, dt):
    """Sierpinski - a 3D tetrahedron fractal rendered with the z-buffer"""
    w, h = hr.w, hr.h
    _init(w, h)
    s = _ST

    for y in range(c.h):
        for x in range(c.w):
            c.set_pixel(x, y, ' ', bg=Color(3, 3, 12), z=-100)

    for sx, sy, ph, bri in s['stars']:
        tw = 0.5 + 0.5 * math.sin(t * 1.3 + ph * 5 + sx * 2.0)
        v = tw * bri
        if v < 0.15:
            continue
        b = int(min(255, v * 255))
        hr.set_pixel(int(sx), int(sy), '·',
                     fg=Color(b, b, min(255, int(b * 1.2))), z=40)

    mesh = _build_mesh(3)
    mesh = mesh.transform(
        Mat4.rotate_x(t * 0.18) @ Mat4.rotate_y(t * 0.3)
    )
    eye = Vec3(3.6 * math.sin(t * 0.07), 2.0 + 0.4 * math.sin(t * 0.11),
               3.6 * math.cos(t * 0.07))
    view = Mat4.look_at(eye, Vec3(0, 0, 0))
    proj = Mat4.perspective(1.0, w / h, 0.1, 30)
    ldir = Vec3(0.5, -0.7, -0.5).norm()
    render_mesh_solid(hr, mesh, view, proj, ldir, None)

    hr.to_canvas(c)
    c.draw_text(2, 0, '▲ Sierpinski ▲',
                Color.from_hsv((t * 0.02) % 1, 0.8, 1.0), z=100)
    c.draw_text(2, c.h - 1, '3D tetrahedron fractal | z-buffer', DIM, z=100)
