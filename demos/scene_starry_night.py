import math, random
from spore_engine import *
from spore_engine.core.color import *
from spore_engine.render3d.engine3d import Mesh3D, render_mesh_solid
from spore_engine.core.geom import Vec3, Mat4
from spore_engine.fx.shaders import KuwaharaFilter, Posterize, ShaderPipeline
from spore_engine.fx.effects import starfield

_stars = None
def scene_starry_night(c: Canvas, hr: HiResCanvas, t: float, pt, dt: float):
    global _stars
    if _stars is None:
        _stars = [[random.uniform(-1, 1) * 30, random.uniform(-1, 1) * 15, random.uniform(0.5, 3)]
                  for _ in range(60)]
    grad = Gradient(Color(5, 3, 25), Color(10, 8, 40), Color(18, 12, 55), Color(30, 20, 70))
    for y in range(c.h):
        for x in range(c.w):
            n = (math.sin(x * 0.015 + t * 0.3) + math.cos(y * 0.02 + t * 0.2)) * 0.5 + 0.5
            c.set_pixel(x, y, '█', grad.at((y + n * 0.4) / c.h), z=-100)

    vs = 12
    verts, faces, fcolors = [], [], []
    for iz in range(vs):
        for ix in range(vs):
            hx = ix / (vs - 1) - 0.5
            hz = iz / (vs - 1) - 0.5
            d = math.sqrt(hx * hx + hz * hz)
            h = math.exp(-d * d * 3) * (1.2 + 0.3 * math.sin(t * 0.4 + d * 5))
            h += 0.15 * (math.sin(ix * 0.7 + t * 0.3) + math.cos(iz * 0.5 + t * 0.2))
            verts.append(Vec3(hx * 6, h * 3, hz * 6))
    for iz in range(vs - 1):
        for ix in range(vs - 1):
            i = iz * vs + ix
            faces.append([i, i + 1, i + vs])
            faces.append([i + 1, i + vs + 1, i + vs])
            for _ in range(2):
                c1 = Color.from_hsv(0.65 - h * 0.15, 0.5 + h * 0.3, 0.6 + h * 0.4)
                fcolors.append(c1)
    mesh = Mesh3D()
    mesh.verts = verts
    mesh.faces = faces
    mesh.face_colors = fcolors

    view = Mat4.look_at(Vec3(math.sin(t * 0.1) * 4, 1.5, math.cos(t * 0.1) * 4), Vec3(0, 0.5, 0))
    proj = Mat4.perspective(1.0, hr.w / hr.h, 0.1, 20)
    light = Vec3(math.sin(t * 0.15), -0.5, math.cos(t * 0.15)).norm()
    render_mesh_solid(hr, mesh, view, proj, light)
    hr.to_canvas(c)

    pipe = ShaderPipeline()
    pipe.add(KuwaharaFilter(2))
    pipe.add(Posterize(5))
    pipe.apply(c, t, dt)

    starfield(c, t, _stars, speed=0.8)
    c.draw_text(2, 0, 'Starry Night', Color.from_hsv(0.62, 0.4, 0.9), z=100)
    c.draw_text(2, c.h - 1, 'low-poly terrain | Kuwahara + Posterize | stars', DIM, z=100)
