import math
from spore_engine import *
from spore_engine.core.color import *
from spore_engine.render3d.raytracer import Scene, Sphere, Plane


_scene = None
def scene_raytracer_infinity(c: Canvas, hr: HiResCanvas, t: float, pt, dt: float):
    global _scene
    if _scene is None:
        _scene = Scene()
        _scene.ambient = Color(15, 15, 25)
        _scene.objects.append(Plane(0, 1, 0, -2.8, Color(40, 35, 55), reflect=0.7))
        _scene.objects.append(Plane(0, -1, 0, -2.8, Color(35, 30, 50), reflect=0.7))
        _scene.objects.append(Plane(0, 0, 1, 5, Color(30, 30, 40), reflect=0.3))
        colors = [Color(255, 60, 80), Color(60, 200, 255), Color(255, 200, 40),
                  Color(140, 80, 255), Color(255, 120, 20), Color(60, 255, 120),
                  Color(255, 80, 200), Color(80, 255, 200)]
        for i in range(8):
            a = i * math.pi / 4 + t * 0.02
            x = math.cos(a) * 2.2
            z = math.sin(a) * 2.2 + 0.5
            y = -0.5 + 0.3 * i / 7
            _scene.objects.append(Sphere(x, y, z, 0.4 + 0.04 * i, colors[i], reflect=0.55 + 0.04 * i))
        _scene.lights.append((4, 5, 0, Color(255, 230, 210), 2.0))
        _scene.lights.append((-4, 3, 3, Color(180, 200, 255), 1.2))
    for i in range(8):
        obj = _scene.objects[3 + i]
        a = i * math.pi / 4 + t * 0.02
        obj.cx = math.cos(a) * 2.2
        obj.cz = math.sin(a) * 2.2 + 0.5
        obj.cy = -0.5 + 0.5 * math.sin(t * 0.15 + i)
    cam = (math.sin(t * 0.1) * 5, 0.0, -5.0 + math.cos(t * 0.1) * 0.5)
    _scene.render(hr, cam, (0, 0, 1), 55)
    hr.to_canvas(c)
    c.draw_text(2, 0, 'Infinity Room', Color(180, 200, 255), z=100)
    c.draw_text(2, c.h - 1, 'parallel mirrors | 8 floating spheres | infinite reflections', DIM, z=100)
