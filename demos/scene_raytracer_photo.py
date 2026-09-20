import math, os
from spore_engine import *
from spore_engine.core.color import *
from spore_engine.render3d.raytracer import RayScene, TexturedQuad


_scene = None
_custom_path = os.path.join(os.path.dirname(__file__), 'image.jpg')


def scene_raytracer_photo(c: Canvas, hr: HiResCanvas, t: float, pt, dt: float):
    global _scene
    if _scene is None:
        _scene = RayScene()
        _scene.ambient = Color(25, 20, 35)
        _scene.bg_color = Color(5, 5, 18)
        path = _custom_path if os.path.isfile(_custom_path) else None
        if path:
            _scene.objects.append(TexturedQuad(0, 0, 0, 3.0, 2.25, path, reflect=0.15))
        _scene.lights.append((6, 10, 8, Color(255, 245, 230), 3.5))
        _scene.lights.append((-6, 4, 6, Color(220, 230, 255), 2.0))
        _scene.lights.append((0, -8, 4, Color(200, 180, 255), 1.0))
    if not _scene.objects:
        c.draw_text(2, c.h // 2, 'no image found', Color(255, 80, 80), z=100)
        return
    quad = _scene.objects[0]
    radius = 1.8
    quad.cx = math.sin(t * 0.06) * radius
    quad.cy = math.sin(t * 0.08 + 0.5) * 0.35
    quad.cz = math.cos(t * 0.06) * radius + 2.0
    quad.face_toward(0, 0.2, 0)
    cam_pos = (0, 0.2, -2.5)
    _scene.render(hr, cam_pos, (0, 0.1, 1.5), 40)
    hr.to_canvas(c)
    c.draw_text(2, 0, 'Photo Billboard', Color(255, 200, 130), z=100)
    c.draw_text(2, c.h - 1, f'source: {os.path.basename(_custom_path)} | orbiting | ray-traced', DIM, z=100)
