import math
from spore_engine import *
from spore_engine.core.color import *
from spore_engine.render3d.raytracer import RayScene, Box


_scene = None
def scene_raytracer_toybox(c: Canvas, hr: HiResCanvas, t: float, pt, dt: float):
    global _scene
    if _scene is None:
        _scene = RayScene()
        _scene.ambient = Color(30, 32, 50)
        _scene.bg_color = Color(10, 12, 25)
        _scene.objects.append(Box(-1.3, 0, 2.5, 1.3, 1.3, 1.3, Color(255, 50, 70), reflect=0.55))
        _scene.objects.append(Box(1.3, 0, 2.5, 1.3, 1.3, 1.3, Color(40, 190, 255), reflect=0.55))
        _scene.objects.append(Box(0, 1.3, 2.5, 1.3, 1.3, 1.3, Color(255, 220, 40), reflect=0.5))
        _scene.objects.append(Box(-1.3, 0, 0.8, 1.3, 1.3, 1.3, Color(50, 255, 100), reflect=0.5))
        _scene.objects.append(Box(1.3, 0, 0.8, 1.3, 1.3, 1.3, Color(255, 70, 190), reflect=0.5))
        _scene.objects.append(Box(0, -1.3, 0.8, 1.3, 1.3, 1.3, Color(255, 190, 50), reflect=0.45))
        _scene.lights.append((6, 10, 5, Color(255, 250, 240), 4.0))
        _scene.lights.append((-6, 8, -2, Color(220, 240, 255), 3.0))
        _scene.lights.append((0, -6, 4, Color(255, 220, 250), 2.0))
    base = [(-1.3, 0, 2.5), (1.3, 0, 2.5), (0, 1.3, 2.5),
            (-1.3, 0, 0.8), (1.3, 0, 0.8), (0, -1.3, 0.8)]
    for i in range(6):
        obj = _scene.objects[i]
        bx, by, bz = base[i]
        angle = t * 0.06 + i * 1.047
        obj.cx = bx + math.sin(angle) * 0.15
        obj.cz = bz + math.cos(angle * 0.7) * 0.15
        obj.cy = by + math.sin(t * 0.1 + i) * 0.12
    cam = (math.sin(t * 0.07) * 3.5, 0.15 + math.sin(t * 0.09) * 0.15, -4.0 + math.cos(t * 0.07) * 0.3)
    _scene.render(hr, cam, (0, 0.1, 1.8), 45)
    hr.to_canvas(c)
    c.draw_text(2, 0, 'Toy Box', Color(255, 180, 120), z=100)
    c.draw_text(2, c.h - 1, '6 boxes | 3 bright lights | high reflectivity | tight pack', DIM, z=100)
