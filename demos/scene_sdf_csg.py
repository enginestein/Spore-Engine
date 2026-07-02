import math
from spore_engine import *
from spore_engine.core.color import *
from spore_engine.render3d.sdf import *
from spore_engine.core.geom import Vec3


_g_scene = None
def scene_sdf_csg(c: Canvas, hr: HiResCanvas, t: float, pt, dt: float):
    global _g_scene
    if _g_scene is None:
        _g_scene = SDFScene()
        _g_scene.ambient = Color(20, 20, 35)

        def ground(p):
            return sd_plane(p, Vec3(0, 1, 0), -0.5)

        def infinite_pillars(p):
            rp = op_repeat(p, Vec3(3.5, 1000, 3.5))
            return sd_box(rp, Vec3(0, 1.5, 0), Vec3(0.35, 1.8, 0.35))

        def carved_sphere(p):
            d = math.hypot(p.x, p.z)
            box = sd_box(p, Vec3(0, 1.0, 0), Vec3(1.0, 1.0, 1.0))
            sphere = sd_sphere(p, Vec3(0, 1.0, 0), 0.65)
            return op_subtract(box, sphere)

        _g_scene.add(ground, Color(50, 50, 70), reflectivity=0.15)
        _g_scene.add(infinite_pillars, Color(170, 150, 130), reflectivity=0.25)
        _g_scene.add(carved_sphere, Color(80, 180, 255), reflectivity=0.3)

        _g_scene.add_light(Vec3(4, 6, -4), Color(255, 220, 200), 1.5)
        _g_scene.add_light(Vec3(-4, 4, 4), Color(150, 170, 255), 1.0)

    camera = Vec3(math.sin(t * 0.2) * 5, 2.0, math.cos(t * 0.2) * 5)
    target = Vec3(0, 1.0, 0)
    _g_scene.max_steps = 48
    _g_scene.max_dist = 25
    _g_scene.render(c, camera, target, 55)
    c.draw_text(2, 0, 'SDF CSG Gallery', Color(255, 200, 100), z=10)
    c.draw_text(2, c.h - 1, 'infinite pillars | carved sphere | reflections', DIM, z=10)
