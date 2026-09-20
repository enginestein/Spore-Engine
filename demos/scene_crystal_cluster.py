import math
import random
from spore_engine import *
from spore_engine.core.color import *
from spore_engine.render3d.engine3d import Mesh3D, render_mesh_solid

_CC = None


def _octahedron(size=1.0):
    m = Mesh3D('octahedron')
    m.verts = [Vec3(1, 0, 0), Vec3(-1, 0, 0), Vec3(0, 1, 0), Vec3(0, -1, 0),
               Vec3(0, 0, 1), Vec3(0, 0, -1)]
    m.faces = [
        [0, 2, 4], [4, 2, 1], [1, 2, 5], [5, 2, 0],
        [4, 3, 0], [1, 3, 4], [5, 3, 1], [0, 3, 5],
    ]
    m.face_colors = [Color(220, 220, 255)] * len(m.faces)
    return m


def _init(w, h):
    global _CC
    if _CC is not None:
        return
    rnd = random.Random(42)
    _CC = {
        'stars': [(rnd.uniform(0, w), rnd.uniform(0, h * 0.8),
                   rnd.uniform(0, 2 * math.pi), rnd.uniform(0.3, 1.0))
                  for _ in range(110)],
        'sparkles': [(rnd.uniform(0, 2 * math.pi), rnd.uniform(1.6, 3.0),
                      rnd.uniform(0, 2 * math.pi))
                     for _ in range(24)],
    }


def _build_cluster(t):
    meshes = []

    core = Mesh3D.icosphere(0.9, 1)
    core = core.transform(Mat4.rotate_y(t * 0.35) @ Mat4.rotate_x(t * 0.22))
    meshes.append(core)

    cube_setup = [
        (Vec3(1.15, 0.2, 0.1), 1.1, Vec3(t * 0.5, t * 0.3, 0)),
        (Vec3(-1.0, -0.35, 0.45), 1.1, Vec3(-t * 0.4, t * 0.55, t * 0.2)),
        (Vec3(0.25, -1.05, -0.5), 1.1, Vec3(t * 0.6, -t * 0.35, t * 0.4)),
        (Vec3(-0.3, 0.95, -0.4), 1.1, Vec3(-t * 0.3, -t * 0.45, t * 0.5)),
    ]
    for pos, size, rot in cube_setup:
        cube = Mesh3D.cube(size)
        cube = cube.transform(
            Mat4.translate(pos.x, pos.y, pos.z)
            @ Mat4.rotate_x(rot.x) @ Mat4.rotate_y(rot.y) @ Mat4.rotate_z(rot.z)
        )
        meshes.append(cube)

    octa = _octahedron(1.35)
    octa = octa.transform(
        Mat4.translate(0.35, 0.55, -0.2)
        @ Mat4.rotate_x(t * 0.45 + 1.0) @ Mat4.rotate_z(t * 0.3)
    )
    meshes.append(octa)

    ring = Mesh3D.torus(1.7, 0.08, 36, 8)
    ring = ring.transform(
        Mat4.translate(-0.05, 0.0, 0.1)
        @ Mat4.rotate_x(math.pi * 0.5 + t * 0.2) @ Mat4.rotate_y(t * 0.15)
        @ Mat4.scale(1, 0.6, 1)
    )
    meshes.append(ring)

    hues = [0.6, 0.05, 0.5, 0.9, 0.75, 0.25, 0.45]
    for i, m in enumerate(meshes):
        m.face_colors = [Color.from_hsv(hues[i], 0.9, 1.0)] * len(m.faces)
    return meshes


def scene_crystal_cluster(c, hr, t, pt, dt):
    """Crystal Cluster - interpenetrating polyhedra resolved by the z-buffer"""
    w, h = hr.w, hr.h
    _init(w, h)
    s = _CC

    cx, cy = c.w / 2, c.h / 2
    for y in range(c.h):
        for x in range(c.w):
            nx = (x - cx) / (c.w * 0.5)
            ny = (y - cy) / (c.h * 0.5)
            d = math.hypot(nx, ny)
            ang = math.atan2(ny, nx)
            hue = (0.62 + ang / (2 * math.pi) + t * 0.008) % 1.0
            neb = Color.from_hsv(hue, 0.6, 0.10)
            deep = Color(2, 1, 8)
            glow = max(0.0, 1 - d * 1.1)
            col = deep.lerp(neb, min(1, 0.25 + glow * 0.75))
            c.set_pixel(x, y, ' ', bg=col, z=-100)

    cx, cy = w / 2, h / 2
    for sx, sy, ph, bri in s['stars']:
        tw = 0.5 + 0.5 * math.sin(t * 1.6 + ph * 5 + sx * 2.3)
        v = tw * bri
        if v < 0.15:
            continue
        b = int(min(255, v * 255))
        hr.set_pixel(int(sx), int(sy), '·' if v < 0.5 else '✦',
                     fg=Color(b, b, min(255, int(b * 1.2))), z=50)

    meshes = _build_cluster(t)
    eye = Vec3(4.1 * math.sin(t * 0.09), 1.1 + 0.5 * math.sin(t * 0.13),
               4.1 * math.cos(t * 0.09))
    view = Mat4.look_at(eye, Vec3(0, 0, 0))
    proj = Mat4.perspective(1.0, w / h, 0.1, 30)

    for i, m in enumerate(meshes):
        ldir = Vec3(math.sin(t * 0.3 + i * 1.7), -0.4,
                    math.cos(t * 0.3 + i * 1.7)).norm()
        render_mesh_solid(hr, m, view, proj, ldir, None)

    for ph, rad, spd in s['sparkles']:
        a = ph + t * spd
        px = cx + math.cos(a) * rad * (w / h)
        py = cy + math.sin(a) * rad * 0.5
        if 0 <= px < w and 0 <= py < h:
            tw = 0.5 + 0.5 * math.sin(t * 3 + ph * 7)
            col = Color.from_hsv((0.6 + ph / 6.28) % 1, 0.9, 0.4 + 0.6 * tw)
            hr.set_pixel(int(px), int(py), '✧', fg=col, z=70)

    hr.to_canvas(c)
    c.draw_text(2, 0, '◆ Crystal Cluster ◆',
                Color.from_hsv((t * 0.02) % 1, 0.8, 1.0), z=100)
    c.draw_text(2, c.h - 1,
                'intersecting polyhedra | per-pixel z-buffer', DIM, z=100)
