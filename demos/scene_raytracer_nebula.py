import math
from spore_engine import *
from spore_engine.core.color import *
from spore_engine.render3d.raytracer import RayScene, Sphere


_scene = None
def scene_raytracer_nebula(c: Canvas, hr: HiResCanvas, t: float, pt, dt: float):
    global _scene
    if _scene is None:
        _scene = RayScene()
        _scene.ambient = Color(10, 8, 20)
        _scene.bg_color = Color(3, 3, 10)
        colors = [
            Color(255, 50, 80), Color(80, 200, 255), Color(255, 220, 40),
            Color(200, 60, 255), Color(255, 150, 20), Color(40, 255, 150),
            Color(255, 80, 200), Color(100, 255, 220), Color(120, 100, 255),
            Color(255, 255, 100),
        ]
        for i in range(10):
            a = i * 2.399  # golden angle
            r = 0.3 + 0.7 * math.sin(i * 0.7)
            x = math.cos(a) * r * 2.5
            z = math.sin(a) * r * 2.5
            y = (i / 9 - 0.5) * 3
            e = 0.4 + 0.5 * (1 - r)
            _scene.objects.append(Sphere(x, y, z, 0.25 + r * 0.3, colors[i], reflect=0.2, emissive=e))
        _scene.lights.append((4, 3, -3, Color(255, 200, 200), 1.8))
        _scene.lights.append((-4, 1, 4, Color(200, 200, 255), 1.5))
        _scene.lights.append((0, -3, 2, Color(200, 255, 200), 1.0))
    for i in range(10):
        obj = _scene.objects[i]
        a = i * 2.399 + t * 0.04
        r = 0.3 + 0.7 * math.sin(i * 0.7)
        obj.cx = math.cos(a) * r * 2.5
        obj.cz = math.sin(a) * r * 2.5
        obj.cy = (i / 9 - 0.5) * 3 + 0.3 * math.sin(t * 0.12 + i * 0.5)
    cam = (math.sin(t * 0.08) * 5.5, math.sin(t * 0.1) * 1.0, -4.5 + math.cos(t * 0.08) * 0.5)
    _scene.render(hr, cam, (0, 0, 0), 60)
    hr.to_canvas(c)
    c.draw_text(2, 0, 'Neon Nebula', Color(255, 100, 180), z=100)
    c.draw_text(2, c.h - 1, '10 emissive spheres | 3 colored lights | deep space', DIM, z=100)
