import math
from spore_engine import *
from spore_engine.core.color import *
from spore_engine.render3d.sdf import *
from spore_engine.core.geom import Vec3


_g2_scene = None
def scene_sdf_glow(c: Canvas, hr: HiResCanvas, t: float, pt, dt: float):
    global _g2_scene
    if _g2_scene is None:
        _g2_scene = SDFScene()
        _g2_scene.ambient = Color(15, 15, 30)

        def ground(p):
            return sd_plane(p, Vec3(0, 1, 0), -0.6)

        def emerald_box(p):
            return sd_box(p, Vec3(2.0, 0.6 + math.sin(t * 0.6) * 0.2, -1.2), Vec3(0.7, 0.7, 0.7))

        def glowing_orb(p):
            return sd_sphere(p, Vec3(-1.8, 1.0 + math.sin(t * 0.4) * 0.2, -1.0), 0.6)

        def golden_torus(p):
            a = t * 0.5
            rx, rz = math.cos(a) * 1.5, math.sin(a) * 1.5
            return sd_torus(p, Vec3(rx, 1.8 + math.sin(t * 0.3) * 0.2, rz), 0.8, 0.25)

        _g2_scene.add(ground, Color(50, 50, 70), reflectivity=0.15)
        _g2_scene.add(emerald_box, Color(60, 220, 80), reflectivity=0.3)
        _g2_scene.add(glowing_orb, Color(255, 60, 60), reflectivity=0.4, emissive=0.5)
        _g2_scene.add(golden_torus, Color(255, 180, 50), reflectivity=0.5)

        _g2_scene.add_light(Vec3(4, 5, -3), Color(255, 200, 180), 1.5)
        _g2_scene.add_light(Vec3(-3, 4, 3), Color(180, 200, 255), 1.2)

    cx = math.sin(t * 0.2) * 4.5
    cz = math.cos(t * 0.2) * 4.5
    camera = Vec3(cx, 1.8, cz)
    target = Vec3(0, 1.0, 0)
    _g2_scene.max_steps = 48
    _g2_scene.max_dist = 25
    _g2_scene.render(c, camera, target, 55)
    c.draw_text(2, 0, 'Glowing SDF World', Color(255, 180, 80), z=10)
    c.draw_text(2, c.h - 1, 'emissive objects | colored lights | reflections', DIM, z=10)
