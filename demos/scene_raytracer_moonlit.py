import math
from spore_engine import *
from spore_engine.core.color import *
from spore_engine.render3d.raytracer import Scene, Sphere, Plane


_scene = None
def scene_raytracer_moonlit(c: Canvas, hr: HiResCanvas, t: float, pt, dt: float):
    global _scene
    if _scene is None:
        _scene = Scene()
        _scene.ambient = Color(10, 12, 30)
        _scene.objects.append(Plane(0, 1, 0, -2.8, Color(25, 28, 45), reflect=0.55))
        _scene.objects.append(Plane(0, -1, 0, -2.8, Color(20, 22, 40), reflect=0.45))
        _scene.objects.append(Plane(0, 0, 1, 4.0, Color(22, 24, 40), reflect=0.3))
        colors = [
            Color(200, 220, 255), Color(180, 200, 255), Color(220, 200, 255),
            Color(200, 230, 240), Color(210, 190, 255), Color(190, 210, 250),
            Color(230, 210, 240), Color(200, 220, 230),
        ]
        for i in range(8):
            a = i * math.pi / 4 + 0.5
            x = math.cos(a) * 2.0
            z = math.sin(a) * 2.0 + 0.5
            y = -0.5 + math.sin(i * 1.7) * 0.6
            sz = 0.35 + 0.1 * (1 - abs(y) / 1.5)
            ref = 0.4 + 0.3 * (1 - abs(y) / 1.5)
            _scene.objects.append(Sphere(x, y, z, sz, colors[i], reflect=ref))
        _scene.lights.append((5, 6, -2, Color(200, 220, 255), 2.5))
    light_angle = t * 0.06
    _scene.lights[0] = (math.cos(light_angle) * 5, 6 + math.sin(t * 0.1) * 0.5, math.sin(light_angle) * 5,
                        Color(200, 220, 255), 2.5)
    for i in range(8):
        obj = _scene.objects[3 + i]
        a = i * math.pi / 4 + t * 0.03 + 0.5
        obj.cx = math.cos(a) * 2.0
        obj.cz = math.sin(a) * 2.0 + 0.5
        obj.cy = -0.5 + 0.7 * math.sin(t * 0.08 + i * 1.7)
    cam = (math.sin(t * 0.07) * 5.5, 0.3 + math.sin(t * 0.09) * 0.15, -5.0 + math.cos(t * 0.07) * 0.3)
    _scene.render(hr, cam, (0, -0.1, 1.0), 55)
    hr.to_canvas(c)
    c.draw_text(2, 0, 'Moonlit', Color(180, 200, 255), z=100)
    c.draw_text(2, c.h - 1, 'single light | cool palette | high contrast reflections', DIM, z=100)
