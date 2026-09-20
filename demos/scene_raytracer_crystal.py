import math
from spore_engine import *
from spore_engine.core.color import *
from spore_engine.render3d.raytracer import RayScene, Sphere, Plane


_scene = None
def scene_raytracer_crystal(c: Canvas, hr: HiResCanvas, t: float, pt, dt: float):
    global _scene
    if _scene is None:
        _scene = RayScene()
        _scene.ambient = Color(12, 12, 30)
        _scene.objects.append(Plane(0, 1, 0, -2.5, Color(30, 30, 50), reflect=0.5))
        _scene.objects.append(Plane(-0.707, 0, 0.707, 3.5, Color(45, 35, 55), reflect=0.55))
        _scene.objects.append(Plane(0.707, 0, 0.707, 3.5, Color(35, 45, 55), reflect=0.55))
        colors = [
            Color(255, 80, 100), Color(80, 220, 255), Color(255, 220, 60),
            Color(200, 80, 255), Color(255, 160, 30), Color(60, 255, 160),
            Color(255, 100, 220), Color(100, 200, 255),
        ]
        for i in range(8):
            a = i * math.pi / 4 + 0.3
            x = math.cos(a) * 1.8
            z = math.sin(a) * 1.8
            y = -0.8 + math.sin(i * 1.3) * 0.5
            _scene.objects.append(Sphere(x, y, z, 0.3 + 0.15 * (1 - abs(y) / 1.5),
                                          colors[i], reflect=0.5 + 0.05 * i, emissive=0.15))
        _scene.lights.append((4, 5, -2, Color(255, 220, 200), 2.0))
        _scene.lights.append((-4, 4, 2, Color(180, 200, 255), 1.5))
    for i in range(8):
        obj = _scene.objects[3 + i]
        a = i * math.pi / 4 + t * 0.03 + 0.3
        obj.cx = math.cos(a) * 1.8
        obj.cz = math.sin(a) * 1.8
        obj.cy = -0.8 + 0.6 * math.sin(t * 0.12 + i * 1.3)
    cam = (math.sin(t * 0.11) * 5, 0.8 + math.sin(t * 0.15) * 0.3, -4.5 + math.cos(t * 0.11) * 0.4)
    _scene.render(hr, cam, (0, -0.2, 1.0), 58)
    hr.to_canvas(c)
    c.draw_text(2, 0, 'Crystal Cave', Color(200, 180, 255), z=100)
    c.draw_text(2, c.h - 1, 'V-mirrors | 8 crystals | prismatic reflections', DIM, z=100)
