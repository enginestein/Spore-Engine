import math
from spore_engine import *
from spore_engine.core.color import *
from spore_engine.render3d.raytracer import Scene, Sphere


_scene = None
def scene_raytracer_system(c: Canvas, hr: HiResCanvas, t: float, pt, dt: float):
    global _scene
    if _scene is None:
        _scene = Scene()
        _scene.ambient = Color(5, 5, 15)
        _scene.bg_color = Color(2, 2, 8)
        _scene.objects.append(Sphere(0, 0, 0, 1.2, Color(255, 200, 80), reflect=0.1, emissive=1.0))
        planets = [
            (2.5, 0.4, Color(180, 120, 80), 0.2), (3.5, 0.6, Color(200, 160, 100), 0.3),
            (4.8, 0.8, Color(60, 120, 200), 0.4), (6.0, 0.5, Color(200, 80, 60), 0.35),
            (7.5, 0.3, Color(180, 160, 200), 0.5), (9.0, 0.2, Color(160, 200, 220), 0.55),
        ]
        for r, size, col, ref in planets:
            _scene.objects.append(Sphere(r, size * 0.5, 0, size, col, reflect=ref))
        _scene.lights.append((5, 8, 0, Color(255, 240, 220), 2.5))
        _scene.lights.append((-3, -2, 6, Color(150, 150, 255), 0.8))
    for i in range(6):
        obj = _scene.objects[1 + i]
        planets = [(2.5, 0.4), (3.5, 0.6), (4.8, 0.8), (6.0, 0.5), (7.5, 0.3), (9.0, 0.2)]
        r, _ = planets[i]
        a = t * (0.2 + 0.03 * i) + i * 1.0
        obj.cx = math.cos(a) * r
        obj.cz = math.sin(a) * r
        obj.cy = planets[i][1] * math.sin(t * 0.1 + i * 0.7)
    cam = (math.sin(t * 0.05) * 11, 2.0 + math.sin(t * 0.07) * 0.3, -3.0 + math.cos(t * 0.05) * 0.3)
    _scene.render(hr, cam, (0, 0.2, 0), 50)
    hr.to_canvas(c)
    c.draw_text(2, 0, 'Solar System', Color(255, 220, 120), z=100)
    c.draw_text(2, c.h - 1, 'emissive sun | 6 orbiting planets | reflections', DIM, z=100)
