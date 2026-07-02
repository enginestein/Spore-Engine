import math
from spore_engine import *
from spore_engine.core.color import *
from spore_engine.render3d.engine3d import Mesh3D, render_mesh_solid
from spore_engine.core.geom import Vec3, Mat4


def _noise(x: float, y: float) -> float:
    return math.sin(x * 1.3 + y * 0.7) * math.cos(y * 0.9 - x * 1.1)


def _fbm(x: float, y: float, octaves: int = 4) -> float:
    v, amp, freq = 0.0, 1.0, 1.0
    for _ in range(octaves):
        v += amp * _noise(x * freq, y * freq)
        amp *= 0.5
        freq *= 2.0
    return v


def scene_terrain_flyover(c: Canvas, hr: HiResCanvas, t: float, pt, dt: float):
    grad = Gradient(Color(10, 8, 30), Color(20, 15, 50), Color(40, 30, 70))
    for y in range(c.h):
        for x in range(c.w):
            n = (math.sin(x * 0.02 + t * 0.2) + math.cos(y * 0.025 + t * 0.15)) * 0.5 + 0.5
            c.set_pixel(x, y, '█', grad.at((y + n * 0.3) / c.h), z=-100)

    gs = 28
    verts, faces, fcolors = [], [], []
    for iz in range(gs):
        for ix in range(gs):
            hx = ix / (gs - 1) - 0.5
            hz = iz / (gs - 1) - 0.5
            h = _fbm(hx * 2.5 + 10.5, hz * 2.5 + 10.5) * 0.6
            h += 0.3 * math.exp(-((hx * 3) ** 2 + (hz * 3) ** 2))
            verts.append(Vec3(hx * 10, h * 4, hz * 10))
    for iz in range(gs - 1):
        for ix in range(gs - 1):
            i = iz * gs + ix
            faces.append([i, i + 1, i + gs])
            faces.append([i + 1, i + gs + 1, i + gs])
            for _ in range(2):
                nh = _fbm(ix / gs * 2.5 + 10.5, iz / gs * 2.5 + 10.5) * 0.6 + 0.3
                if nh < 0.15:
                    col = Color(60, 80, 180)
                elif nh < 0.3:
                    col = Color(200, 180, 120)
                elif nh < 0.55:
                    col = Color(50, 140, 40)
                elif nh < 0.75:
                    col = Color(100, 90, 80)
                else:
                    col = Color(230, 230, 240)
                fcolors.append(col)
    mesh = Mesh3D()
    mesh.verts = verts
    mesh.faces = faces
    mesh.face_colors = fcolors

    path_t = t * 0.06
    ex = math.sin(path_t * 0.7) * 6
    ez = math.cos(path_t * 0.5) * 6
    ey = 1.5 + 0.8 * math.sin(path_t * 0.3)
    view = Mat4.look_at(Vec3(ex, ey, ez), Vec3(0, 0.5, 0))
    proj = Mat4.perspective(1.0, hr.w / hr.h, 0.1, 30)
    light = Vec3(math.sin(t * 0.1 + 0.5), -0.4, math.cos(t * 0.1 + 0.5)).norm()
    render_mesh_solid(hr, mesh, view, proj, light)
    hr.to_canvas(c)

    c.draw_text(2, 0, 'Canyon Flyover', Color(200, 180, 140), z=100)
    c.draw_text(2, c.h - 1, f'fbm terrain | {gs*gs} verts | {len(faces)} triangles | flyover cam', DIM, z=100)
