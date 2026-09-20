import math
from spore_engine import *
from spore_engine.core.color import *
from spore_engine.render3d.raytracer import RayScene, Cylinder, Sphere, Plane


_scene = None
def scene_raytracer_alien(c: Canvas, hr: HiResCanvas, t: float, pt, dt: float):
    global _scene
    if _scene is None:
        _scene = RayScene()
        _scene.ambient = Color(18, 22, 35)
        _scene.objects.append(Plane(0, 1, 0, -3.0, Color(25, 35, 30), reflect=0.3))
        trunks = [
            (-2.0, 1.2, 1.5), (2.2, 0.8, 1.0), (0.0, 1.5, -1.0),
            (-1.8, 1.0, -1.5), (2.5, 1.2, -1.2), (-0.8, 0.7, 2.5),
        ]
        colors = [
            Color(100, 220, 100), Color(80, 200, 255), Color(255, 200, 60),
            Color(200, 80, 255), Color(255, 140, 40), Color(60, 255, 180),
        ]
        for i, (cx, ch, cz) in enumerate(trunks):
            _scene.objects.append(Cylinder(cx, ch, cz, 0.25, ch * 2, Color(120, 80, 50), reflect=0.2))
            _scene.objects.append(Sphere(cx, ch * 2 + 0.2, cz, 0.5 + 0.1 * i, colors[i], reflect=0.4, emissive=0.15))
        _scene.lights.append((5, 8, 3, Color(255, 240, 220), 2.2))
        _scene.lights.append((-5, 3, 0, Color(150, 180, 255), 1.2))
    for i in range(6):
        trunk = _scene.objects[1 + i * 2]
        top = _scene.objects[1 + i * 2 + 1]
        offset = math.sin(t * 0.08 + i * 0.7) * 0.3
        trunk.sy = (0.8 + offset * 0.5) if i == 0 else (0.8 + offset * 0.3)
        top.cy = trunk.cy * 2 + 0.2 + offset * 0.2
    cam = (math.sin(t * 0.07) * 6.5, 0.8 + math.sin(t * 0.1) * 0.2, -5.0 + math.cos(t * 0.07) * 0.5)
    _scene.render(hr, cam, (0, -0.3, 1.0), 58)
    hr.to_canvas(c)
    c.draw_text(2, 0, 'Alien Grove', Color(120, 255, 140), z=100)
    c.draw_text(2, c.h - 1, 'cylinders | spheres | alien flora | bioluminescence', DIM, z=100)
