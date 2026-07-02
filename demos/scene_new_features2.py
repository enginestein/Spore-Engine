from spore_engine import *
from spore_engine.core.color import *
from spore_engine.core.canvas import SHADE_CHARS
from spore_engine.gen.wfc import WFC
from spore_engine.gen.pathfinding import AStar
from spore_engine.gen.delaunay import Delaunay, Point
from spore_engine.gen.marching_cubes import marching_cubes, make_density_grid
from spore_engine.render3d.sdf import SDFScene, sd_sphere, sd_box, sd_torus, op_union, op_subtract
from spore_engine.render3d.model_loader import load_obj, load_ply
from spore_engine.render3d.engine3d import render_mesh_solid, render_mesh_wireframe, Mesh3D
from spore_engine.sim.physics3d import Body3D, PhysicsWorld3D, GRAVITY3D, BoxBody3D
from spore_engine.sim.softbody import SoftBody, SoftBodyWorld
from spore_engine.sim.steering import SteerAgent, SteerWorld
from spore_engine.fx.volumetric import VolumetricFog, LightCone, SmokePlume, VolumetricRenderer
from spore_engine.anim.ik import Skeleton, create_arm, create_leg, create_tentacle
from spore_engine.media.ansi_io import export_ansi, canvas_to_block_art, parse_ansi
import math, random


def scene_wfc(c: Canvas, hr: HiResCanvas, t: float, pt, dt: float):
    wfc = WFC.simple_path_tiles()
    wfc.w = min(c.w, 30)
    wfc.h = min(c.h, 15)
    wfc.generate(seed=int(t))
    ox = (c.w - wfc.w) // 2
    oy = (c.h - wfc.h) // 2
    wfc.render(c, ox, oy)
    c.draw_text(2, 0, 'Wave Function Collapse', Color(255, 200, 100), z=10)
    c.draw_text(2, c.h - 1, f'{wfc.w}x{wfc.h} tiles collapsed', DIM, z=10)


def scene_astar(c: Canvas, hr: HiResCanvas, t: float, pt, dt: float):
    w, h = min(c.w, 50), min(c.h, 25)
    ox, oy = (c.w - w) // 2, (c.h - h) // 2
    astar = AStar(w, h)
    rng = random.Random(int(t))
    for y in range(h):
        for x in range(w):
            if rng.random() < 0.25 and not (x == 0 and y == 0):
                astar.set_obstacle(x, y)
    astar.set_walkable(0, 0, True)
    astar.set_walkable(w - 1, h - 1, True)
    path = astar.find_path((0, 0), (w - 1, h - 1), diagonals=True)
    astar.render(c, ox, oy)
    c.draw_text(2, 0, f'A* Pathfinding: {len(path)} steps', Color(100, 255, 150), z=10)
    c.draw_text(2, c.h - 1, f'visited: {len(astar.visited)} cells', DIM, z=10)


def scene_physics3d(c: Canvas, hr: HiResCanvas, t: float, pt, dt: float):
    if not hasattr(scene_physics3d, 'world'):
        scene_physics3d.world = PhysicsWorld3D(bounds=(8, 5, 8))
        sphere = Body3D(Vec3(0, 4, 0), mass=1, radius=1, color=RED)
        sphere.vel = Vec3(0.5, 0, 0.3)
        sphere.restitution = 0.8
        box = BoxBody3D(Vec3(2.5, 0.5, 0), Vec3(1.5, 1.5, 1.5), mass=0, color=GREEN)
        box.locked = True
        box2 = BoxBody3D(Vec3(-2, 2.5, 1), Vec3(1, 2.5, 1), mass=0, color=Color(100, 100, 255))
        box2.locked = True
        scene_physics3d.world.add_body(sphere)
        scene_physics3d.world.add_body(box)
        scene_physics3d.world.add_body(box2)
        scene_physics3d.sphere = sphere
        scene_physics3d.box = box
        scene_physics3d.box2 = box2
    world = scene_physics3d.world
    sphere = scene_physics3d.sphere
    box = scene_physics3d.box
    box2 = scene_physics3d.box2
    world.step(dt, 4)

    meshes = []
    b_pos = sphere.pos
    b_mesh = Mesh3D.icosphere(0.9, 1)
    b_mesh = b_mesh.transform(Mat4.translate(b_pos.x, b_pos.y, b_pos.z))
    b_mesh.face_colors = [RED] * len(b_mesh.faces)
    meshes.append(b_mesh)
    for bx, col in [(box, GREEN), (box2, Color(100, 100, 255))]:
        bx_mesh = Mesh3D.cube(1)
        sx, sy, sz = bx.size.x, bx.size.y, bx.size.z
        bx_mesh = bx_mesh.transform(
            Mat4.translate(bx.pos.x, bx.pos.y, bx.pos.z) * Mat4.scale(sx, sy, sz))
        bx_mesh.face_colors = [col] * len(bx_mesh.faces)
        meshes.append(bx_mesh)
    ground = Mesh3D.cube(20)
    ground = ground.transform(Mat4.translate(0, -4, 0) * Mat4.scale(1, 0.1, 1))
    ground.face_colors = [Color(60, 60, 80)] * len(ground.faces)
    meshes.append(ground)

    view = Mat4.look_at(Vec3(5, 3, 7), Vec3(0, 0, 0))
    proj = Mat4.perspective(0.9, hr.w / hr.h, 0.1, 50)
    light = Vec3(1, 2, -1).norm()
    for m in meshes:
        render_mesh_solid(hr, m, view, proj, light)
    hr.to_canvas(c)
    c.draw_text(2, 0, '3D Physics', Color(200, 100, 255), z=10)
    c.draw_text(2, c.h - 1, f'sphere bouncing off boxes', DIM, z=10)


def scene_obj_loader(c: Canvas, hr: HiResCanvas, t: float, pt, dt: float):
    meshes = []
    names = ['Cube', 'Sphere', 'Torus', 'Icosphere', 'Pyramid']
    builders = [Mesh3D.cube, lambda: Mesh3D.sphere(1, 12, 16),
                lambda: Mesh3D.torus(1.2, 0.5, 20, 12),
                lambda: Mesh3D.icosphere(1, 2), Mesh3D.pyramid]
    positions = [(-3.5, 0, 0), (-1.8, 0, 0), (0, 0, 0), (1.8, 0, 0), (3.5, 0, 0)]
    angle = t * 0.4
    for name, builder, pos in zip(names, builders, positions):
        m = builder()
        m.face_colors = [Color.from_hsv((i * 0.618 + hash(name) * 0.1) % 1, 0.8, 1)
                         for i in range(max(1, len(m.faces)))]
        m = m.transform(
            Mat4.translate(pos[0], pos[1] + math.sin(t + pos[0]) * 0.3, pos[2]) *
            Mat4.rotate_y(angle + pos[0] * 0.3) *
            Mat4.rotate_x(angle * 0.5 + pos[1]))
        meshes.append(m)
    view = Mat4.look_at(Vec3(0, 0.5, 6), Vec3(0, 0, 0))
    proj = Mat4.perspective(1.0, hr.w / hr.h, 0.1, 20)
    light = Vec3(0, 1, -0.5).norm()
    for m in meshes:
        render_mesh_solid(hr, m, view, proj, light)
        render_mesh_wireframe(c, m, view, proj)
    hr.to_canvas(c)
    c.draw_text(2, 0, '3D Primitives', Color(100, 200, 255), z=10)
    c.draw_text(2, c.h - 1, 'OBJ/PLY loader also available', DIM, z=10)


def scene_sdf(c: Canvas, hr: HiResCanvas, t: float, pt, dt: float):
    scene = SDFScene()
    scene.add(lambda p: sd_sphere(p, Vec3(-2, 0.5 + math.sin(t) * 0.3, 0), 1.2), RED, reflectivity=0.3)
    scene.add(lambda p: sd_box(p, Vec3(2, 0.5 + math.cos(t * 0.7) * 0.3, 0), Vec3(1.5, 1.5, 1.5)), GREEN, reflectivity=0.2)
    scene.add(lambda p: sd_torus(p, Vec3(0, 2.5, 0), 1.2, 0.4), Color(255, 200, 100), reflectivity=0.4)
    scene.add(lambda p: sd_sphere(p, Vec3(0, -2.5, 0), 1.8), Color(80, 80, 100), reflectivity=0.1)
    scene.add_light(Vec3(4, 5, -5), WHITE, 1.5)
    scene.add_light(Vec3(-4, 3, 3), Color(150, 150, 255), 0.8)
    camera = Vec3(math.sin(t * 0.25) * 5, 1.5, math.cos(t * 0.25) * 5)
    target = Vec3(0, 0.8, 0)
    scene.max_steps = 64
    scene.max_dist = 30
    scene.render_preview(c, camera, target, 60)
    c.draw_text(2, 0, 'SDF Ray Marching', Color(255, 100, 200), z=10)
    c.draw_text(2, c.h - 1, 'sphere + box + torus with reflections & shadows', DIM, z=10)


def scene_ansi_io(c: Canvas, hr: HiResCanvas, t: float, pt, dt: float):
    block_art = Canvas(40, 12)
    for y in range(12):
        for x in range(40):
            hue = (x / 40 + y / 12 + t * 0.03) % 1
            block_art.set_pixel(x, y, ' ' if random.random() < 0.1 else SHADE_CHARS[min(9, int((math.sin(x*0.3+y*0.2+t*2)+1)*2))],
                                Color.from_hsv(hue, 0.8, 1), z=1)
    for y in range(0, 12, 4):
        for i, ch in enumerate('ANSI ART'):
            if y // 4 < 3 and i + 12 < 40:
                block_art.set_pixel(12 + i, y + 1, ch, WHITE, z=5)

    ansi_text = export_ansi(block_art)
    parsed = parse_ansi(ansi_text)
    block = canvas_to_block_art(block_art)

    lines = block.split('\n')
    ox, oy = (c.w - 60) // 2, 2
    for i, line in enumerate(lines):
        if i >= c.h - oy:
            break
        col_pos = 0
        j = 0
        while j < len(line) and col_pos < c.w - ox:
            if line[j] == '\033':
                end = line.find('m', j)
                if end > 0:
                    j = end + 1
                    continue
            if line[j] != '\033':
                c.set_pixel(col_pos + ox, i + oy, line[j], Color(200, 200, 200), z=2)
                col_pos += 1
            j += 1

    y_off = oy + len(lines) + 1
    for i in range(min(parsed.h, c.h - y_off - 2)):
        for j in range(min(parsed.w, c.w - 2)):
            px = parsed.get_pixel(j, i)
            if px and px.fg:
                c.set_pixel(j + 1, i + y_off, px.char, px.fg, z=2)

    c.draw_text(2, 0, 'ANSI Art Export/Import', Color(200, 100, 100), z=10)
    c.draw_text(2, c.h - 1, f'roundtrip: {len(ansi_text)}b', DIM, z=10)


def scene_softbody(c: Canvas, hr: HiResCanvas, t: float, pt, dt: float):
    if not hasattr(scene_softbody, 'world'):
        scene_softbody.world = SoftBodyWorld(c.w, c.h)
        scene_softbody.world.add(SoftBody.circle(20, 4, 3.5, 14, BLUE))
        scene_softbody.world.add(SoftBody.blob(45, 4, 3, RED))
        scene_softbody.world.add(SoftBody.square(62, 4, 5, 4, GREEN))
    world = scene_softbody.world
    world.step(dt)
    c.fill_rect(0, 0, c.w, c.h, ' ', bg=Color(10, 10, 20))
    for x in range(c.w):
        c.set_pixel(x, c.h - 1, '~', Color(40, 40, 60), z=0)
    world.render(c)
    c.draw_text(2, 0, 'Soft Body Physics', Color(100, 200, 255), z=10)
    c.draw_text(2, c.h - 1, 'pressure-based deformable bodies — circle, blob, square', DIM, z=10)


def scene_delaunay(c: Canvas, hr: HiResCanvas, t: float, pt, dt: float):
    d = Delaunay()
    rng = random.Random(int(t))
    points = [Point(rng.random() * 60 + 2, rng.random() * 15 + 3) for _ in range(25)]
    d.triangulate(points)
    phase = int(t * 0.25) % 4
    c.fill_rect(0, 0, c.w, c.h, ' ', bg=Color(5, 5, 15))

    for y in range(c.h):
        for x in range(c.w):
            c.set_pixel(x, y, '·', Color(5, 5, 12), z=-1)

    if phase == 0 or phase == 3:
        d.render(c, show_vertices=True, show_edges=True, color=Color(100, 200, 255))
    if phase == 1:
        d.render_voronoi(c, color=Color(100, 255, 150))
        d.render(c, show_vertices=True, show_edges=False, color=Color(255, 200, 100))
    if phase == 2:
        for tri in d.triangles:
            hue = (tri.a.x + tri.b.y + tri.c.x) * 0.02 % 1
            col = Color.from_hsv(hue, 0.7, 0.5)
            for a, b in tri.edges():
                c.draw_line(int(a.x), int(a.y), int(b.x), int(b.y), '+', col, z=1)

    labels = ['Delaunay Triangulation', 'Voronoi Diagram', 'Colored Triangles',
              f'{len(d.triangles)} triangles, {len(points)} points']
    c.draw_text(2, 0, labels[phase], Color(200, 200, 100), z=10)


def scene_steering(c: Canvas, hr: HiResCanvas, t: float, pt, dt: float):
    if not hasattr(scene_steering, 'world'):
        scene_steering.world = SteerWorld(c.w, c.h)
        scene_steering.world.wrap_mode = False
        for i in range(6):
            scene_steering.world.add_agent(
                8 + i * 3, 6, Color.from_hsv(i * 0.15, 0.9, 1))
        scene_steering.obstacles = [Vec2(35, 10), Vec2(45, 12), Vec2(55, 8)]
    world = scene_steering.world
    target_x = 40 + math.sin(t * 0.4) * 25
    target_y = 12 + math.sin(t * 0.25) * 6
    target = Vec2(target_x, target_y)
    for i, a in enumerate(world.agents):
        force = a.seek(target)
        force = force + a.separate(world.agents, 5) * 2
        force = force + a.avoid_obstacles(scene_steering.obstacles, 6)
        a.update(force)
        a.bounce(c.w, c.h)
    c.fill_rect(0, 0, c.w, c.h, ' ', bg=Color(5, 5, 15), z=-10)
    c.draw_circle(int(target.x), int(target.y), 2, '◉', RED, z=5)
    for obs in scene_steering.obstacles:
        c.set_pixel(int(obs.x), int(obs.y), '#', Color(180, 80, 80), z=1)
        c.set_pixel(int(obs.x) + 1, int(obs.y), '#', Color(150, 60, 60), z=1)
        c.set_pixel(int(obs.x), int(obs.y) + 1, '#', Color(150, 60, 60), z=1)
    world.render(c)
    c.draw_text(2, 0, 'Steering Behaviors', Color(200, 255, 100), z=10)
    c.draw_text(2, c.h - 1, 'seek + separation + obstacle avoidance', DIM, z=10)


def scene_marching_cubes(c: Canvas, hr: HiResCanvas, t: float, pt, dt: float):
    sz = 10
    grid = [[[0.0] * sz for _ in range(sz)] for _ in range(sz)]
    cx = cy = cz = sz / 2
    for z in range(sz):
        for y in range(sz):
            for x in range(sz):
                dx, dy, dz = x - cx, y - cy, z - cz
                base = math.sqrt(dx*dx + dy*dy + dz*dz) - sz * 0.32
                wave = math.sin(dz * 0.8 + t) * 0.4
                grid[z][y][x] = base + wave

    mesh = marching_cubes(grid, 0, Color.from_hsv((t * 0.08) % 1, 0.8, 1))
    c.fill_rect(0, 0, c.w, c.h, ' ', bg=Color(5, 5, 15), z=-10)
    if mesh.verts:
        angle = t * 0.35
        model = (Mat4.rotate_y(angle) * Mat4.rotate_x(0.3 + math.sin(t * 0.2) * 0.1) *
                 Mat4.scale(0.8, 0.8, 0.8) * Mat4.translate(-cx, -cy, -cz))
        mesh = mesh.transform(model)
        view = Mat4.look_at(Vec3(5, 3, 7), Vec3(0, 0, 0))
        proj = Mat4.perspective(0.9, hr.w / hr.h, 0.1, 30)
        light = Vec3(0, 1, -1).norm()
        render_mesh_solid(hr, mesh, view, proj, light)
        hr.to_canvas(c)
        c.draw_text(2, c.h - 1, f'{len(mesh.verts)} verts, {len(mesh.faces)} faces', DIM, z=10)
    c.draw_text(2, 0, 'Marching Cubes 3D', Color(255, 150, 100), z=10)


def scene_volumetric(c: Canvas, hr: HiResCanvas, t: float, pt, dt: float):
    if not hasattr(scene_volumetric, 'vren'):
        scene_volumetric.vren = VolumetricRenderer(c.w, c.h)
        scene_volumetric.vren.fog.color = Color(240, 220, 190)
        scene_volumetric.vren.fog.density = 0.4
        scene_volumetric.vren.add_cone(LightCone(10, 7, -0.6, 0.8, 30, Color(255, 200, 140)))
        scene_volumetric.vren.cones[0].intensity = 0.9
        scene_volumetric.vren.add_cone(LightCone(45, 6, 0.5, 0.7, 35, Color(180, 160, 255)))
        scene_volumetric.vren.cones[1].intensity = 0.8
        scene_volumetric.vren.add_cone(LightCone(70, 5, 0.9, 0.5, 25, Color(255, 150, 100)))
        scene_volumetric.vren.cones[2].intensity = 0.7
        scene_volumetric.vren.add_plume(SmokePlume(18, c.h - 4, Color(180, 170, 160)))
        scene_volumetric.vren.plumes[0].rate = 6
        scene_volumetric.vren.add_plume(SmokePlume(38, c.h - 6, Color(160, 120, 100)))
        scene_volumetric.vren.plumes[1].rate = 4
        scene_volumetric.vren.add_plume(SmokePlume(55, c.h - 4, Color(170, 180, 190)))
        scene_volumetric.vren.plumes[2].rate = 5
    vren = scene_volumetric.vren
    vren.update(dt)

    grad = Gradient(Color(10, 5, 18), Color(20, 12, 30), Color(35, 25, 45))
    for y in range(c.h):
        for x in range(c.w):
            c.set_pixel(x, y, '█', grad.at(y / c.h), z=-10)

    for x in range(c.w):
        c.set_pixel(x, c.h - 1, '█', Color(40, 35, 30), z=1)
        c.set_pixel(x, c.h - 2, '█', Color(55, 45, 35), z=1)
    for x in range(c.w):
        c.set_pixel(x, c.h - 3, '░', Color(60, 50, 40), z=1)
    for x in range(7, 22):
        c.set_pixel(x, c.h - 4, '|', Color(80, 65, 50), z=2)
        c.set_pixel(x, c.h - 5, '|', Color(75, 60, 45), z=2)
        c.set_pixel(x, c.h - 6, '|', Color(70, 55, 40), z=2)
    for x in range(6, 23):
        c.set_pixel(x, c.h - 7, '▔', Color(90, 70, 50), z=2)
    for x in range(35, 50):
        for dy in range(5):
            c.set_pixel(x, c.h - 4 - dy, '▌' if x < 42 else '▐', Color(70, 60, 55), z=2)
    for x in range(60, 75):
        c.set_pixel(x, c.h - 4, '|', Color(75, 65, 55), z=2)
        c.set_pixel(x, c.h - 5, '|', Color(70, 60, 50), z=2)
    for x in range(59, 76):
        c.set_pixel(x, c.h - 6, '▔', Color(85, 70, 55), z=2)

    for x in range(0, c.w, 4):
        shade = '.:.' if int(x / 4 + t) % 2 == 0 else '...'
        c.set_pixel(x, c.h - 3, shade[0], Color(60, 50, 40), z=1)

    vren.render(c, apply_to_scene=True)
    c.draw_text(2, 0, 'Volumetric Effects', Color(255, 200, 150), z=10)
    c.draw_text(2, c.h - 1, 'fog + light cones + smoke plumes', DIM, z=10)


def scene_ik(c: Canvas, hr: HiResCanvas, t: float, pt, dt: float):
    if not hasattr(scene_ik, 'arm'):
        scene_ik.arm = create_arm(20, 18, 4, 2.8, Color(220, 180, 120))
        scene_ik.leg = create_leg(50, 18, 3, 2.5, Color(200, 160, 100))
        scene_ik.tentacle = create_tentacle(68, 18, 10, 1.6, Color(100, 220, 180))
    arm = scene_ik.arm
    leg = scene_ik.leg
    tent = scene_ik.tentacle

    tx = 15 + math.sin(t * 0.6) * 10
    ty = 8 + math.cos(t * 0.4) * 5
    arm.solve_fabrik(Vec2(tx, ty))
    lx = 50 + math.sin(t * 0.35 + 1) * 8
    ly = 10 + math.cos(t * 0.5 + 2) * 4
    leg.solve_fabrik(Vec2(lx, ly))
    tx2 = 65 + math.sin(t * 0.25) * 10
    ty2 = 6 + math.sin(t * 0.45 + 1) * 4
    tent.solve_ccd(Vec2(tx2, ty2))

    c.fill_rect(0, 0, c.w, c.h, ' ', bg=Color(5, 5, 15))
    for x in range(c.w):
        c.set_pixel(x, 20, '~', Color(30, 30, 40), z=0)
    arm.render(c, bone_char='#', joint_char='◉', show_angles=False)
    leg.render(c, bone_char='#', joint_char='◆')
    tent.render(c, bone_char='~', joint_char='○')

    for label, x, y in [('Arm', 20, 18), ('Leg', 50, 18), ('Tentacle', 68, 18)]:
        c.set_pixel(x, y, '■', Color(255, 100, 100), z=4)
    c.draw_circle(int(tx), int(ty), 1, '●', Color(255, 80, 80), z=5)
    c.draw_circle(int(lx), int(ly), 1, '●', Color(255, 80, 80), z=5)
    c.draw_circle(int(tx2), int(ty2), 1, '●', Color(255, 80, 80), z=5)
    c.draw_text(2, 0, 'Inverse Kinematics: FABRIK + CCD', Color(150, 200, 255), z=10)
    c.draw_text(2, c.h - 1, 'arm, leg, tentacle tracking moving targets', DIM, z=10)
