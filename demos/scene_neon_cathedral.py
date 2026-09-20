import math
from spore_engine import *
from spore_engine.core.color import *
from spore_engine.render3d.engine3d import Mesh3D, render_mesh_solid


def scene_neon_cathedral(c: Canvas, hr: HiResCanvas, t: float, pt, dt: float):
    """Neon Cathedral - 3D rendered geometric cathedral with pulsing neon lights and floating orbs"""
    # Dramatic gradient background
    grad = Gradient(Color(3, 2, 15), Color(10, 5, 35), Color(18, 10, 50), Color(25, 12, 40))
    for y in range(c.h):
        for x in range(c.w):
            n = (math.sin(x * 0.015 + t * 0.2) + math.cos(y * 0.02 + t * 0.15)) * 0.5 + 0.5
            c.set_pixel(x, y, '█', grad.at((y + n * 0.2) / c.h), z=-100)

    # Build cathedral structure
    arch_w, arch_h, arch_d = 3.0, 3.5, 2.0
    meshes = []

    # Floor - scale a unit cube
    floor = Mesh3D.cube(1).transform(
        Mat4.scale(arch_w * 2 + 1, 0.1, arch_d * 2 + 2) *
        Mat4.translate(0, -1.5, 0)
    )
    meshes.append(floor)

    # Left wall
    lw = Mesh3D.cube(1).transform(
        Mat4.scale(0.1, arch_h, arch_d * 2 + 2) *
        Mat4.translate(-arch_w, 0.25, 0)
    )
    meshes.append(lw)

    # Right wall
    rw = Mesh3D.cube(1).transform(
        Mat4.scale(0.1, arch_h, arch_d * 2 + 2) *
        Mat4.translate(arch_w, 0.25, 0)
    )
    meshes.append(rw)

    # Back wall
    bw = Mesh3D.cube(1).transform(
        Mat4.scale(arch_w * 2 + 1, arch_h, 0.1) *
        Mat4.translate(0, 0.25, -arch_d - 1)
    )
    meshes.append(bw)

    # Ceiling vaults - a row of torus arches
    for i in range(-3, 4):
        arch_mesh = Mesh3D.torus(1.8, 0.08, 12, 6)
        arch_mesh = arch_mesh.transform(
            Mat4.translate(0, 1.8, i * 1.2) *
            Mat4.rotate_x(math.pi * 0.5) *
            Mat4.scale(1.2, 1, 0.4)
        )
        meshes.append(arch_mesh)

    # Pillars - row of columns using stacked torus rings
    for i in range(-3, 4):
        for side in [-1, 1]:
            pillar = Mesh3D.torus(0.12, 0.04, 8, 6)
            pillar = pillar.transform(
                Mat4.translate(side * (arch_w - 0.2), 0.6, i * 1.2) *
                Mat4.rotate_x(math.pi * 0.5) *
                Mat4.scale(1, 3.5, 1)
            )
            meshes.append(pillar)

    # Central altar - floating icosahedron
    altar = Mesh3D.icosphere(0.6, 2)
    altar = altar.transform(
        Mat4.translate(0, -0.5 + 0.2 * math.sin(t * 0.3), -1.0) *
        Mat4.rotate_y(t * 0.4) *
        Mat4.rotate_x(t * 0.2)
    )
    meshes.append(altar)

    # Floating orbs around altar
    for i in range(8):
        a = i * math.pi / 4 + t * 0.2
        r = 1.2 + 0.3 * math.sin(i * 1.3 + t * 0.5)
        orb = Mesh3D.sphere(0.1, 6, 8)
        orb = orb.transform(
            Mat4.translate(
                math.cos(a) * r,
                -0.4 + 0.3 * math.sin(i * 0.7 + t * 0.4),
                -1.0 + math.sin(a) * r
            )
        )
        meshes.append(orb)

    # Camera orbit
    cam_dist = 5.5 + 0.3 * math.sin(t * 0.07)
    cam_angle = t * 0.08
    eye = Vec3(
        cam_dist * math.sin(cam_angle),
        0.5 + 0.2 * math.sin(t * 0.1),
        cam_dist * math.cos(cam_angle)
    )
    view = Mat4.look_at(eye, Vec3(0, 0.2, -0.5))
    proj = Mat4.perspective(1.0, hr.w / hr.h, 0.1, 30)

    # Render each mesh with neon-colored lighting
    for idx, m in enumerate(meshes):
        hue = (idx * 0.07 + t * 0.01) % 1.0
        base_color = Color.from_hsv(hue, 0.8, 0.7)
        # Set face colors on mesh
        m.face_colors = [base_color] * len(m.faces)
        ldir = Vec3(
            math.sin(t * 0.3 + idx * 0.5),
            -0.3,
            math.cos(t * 0.3 + idx * 0.5)
        ).norm()
        render_mesh_solid(hr, m, view, proj, ldir, None)

    hr.to_canvas(c)

    # Title with color cycling
    title_hue = (t * 0.02) % 1.0
    c.draw_text(2, 0, '✧ Neon Cathedral ✧', Color.from_hsv(title_hue, 0.8, 1.0), z=100)
    c.draw_text(2, c.h - 1, '3D architecture | pulsing neon | floating orbs | altar', DIM, z=100)

