import math
from spore_engine import *
from spore_engine.core.color import *
from spore_engine.render3d.raytracer import RayScene, Sphere, Plane


_scene = None
def scene_raytracer_jewel(c: Canvas, hr: HiResCanvas, t: float, pt, dt: float):
    global _scene
    if _scene is None:
        _scene = RayScene()
        _scene.ambient = Color(20, 18, 30)
        _scene.objects.append(Plane(0, 1, 0, -2.2, Color(35, 30, 55), reflect=0.55))
        _scene.objects.append(Plane(0, 0, 1, 3.5, Color(40, 35, 55), reflect=0.5))
        _scene.objects.append(Plane(1, 0, 0, -3.0, Color(35, 40, 55), reflect=0.5))
        _scene.objects.append(Plane(-1, 0, 0, -3.0, Color(35, 40, 55), reflect=0.5))
        colors = [
            Color(255, 50, 70), Color(50, 200, 255), Color(255, 200, 40),
            Color(200, 50, 255), Color(255, 140, 20), Color(50, 255, 140),
            Color(255, 70, 200), Color(70, 255, 200), Color(140, 100, 255),
            Color(255, 255, 60), Color(255, 160, 100), Color(100, 200, 255),
        ]
        for i in range(12):
            a = i * 2.094  # 120 deg / 3 per layer
            layer = i // 4
            r = 1.2 + layer * 0.5
            x = math.cos(a) * r
            z = math.sin(a) * r + 0.3
            y = -0.7 + layer * 0.8 - 0.3 * (i % 4) / 3
            sz = 0.25 + 0.06 * (4 - layer)
            _scene.objects.append(Sphere(x, y, z, sz, colors[i], reflect=0.5 + 0.04 * i, emissive=0.1))
        _scene.lights.append((3, 5, 2, Color(255, 240, 220), 2.2))
        _scene.lights.append((-3, 3, -1, Color(200, 200, 255), 1.8))
    for i in range(12):
        obj = _scene.objects[4 + i]
        layer = i // 4
        a = i * 2.094 + t * (0.03 + layer * 0.01)
        r = 1.2 + layer * 0.5
        obj.cx = math.cos(a) * r
        obj.cz = math.sin(a) * r + 0.3
        obj.cy = -0.7 + layer * 0.8 + 0.2 * math.sin(t * 0.1 + i)
    cam = (math.sin(t * 0.09) * 4.5, 0.3 + math.sin(t * 0.12) * 0.2, -5.0 + math.cos(t * 0.09) * 0.3)
    _scene.render(hr, cam, (0, 0.2, 0.5), 55)
    hr.to_canvas(c)
    c.draw_text(2, 0, 'Jewel Box', Color(255, 200, 150), z=100)
    c.draw_text(2, c.h - 1, '12 gems | 4 reflective walls | multi-layer rotation', DIM, z=100)
