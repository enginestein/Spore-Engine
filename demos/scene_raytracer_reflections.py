import math
from spore_engine import *
from spore_engine.core.color import *
from spore_engine.render3d.raytracer import RayScene, Sphere, Plane


_scene = None
def scene_raytracer_reflections(c: Canvas, hr: HiResCanvas, t: float, pt, dt: float):
    global _scene
    if _scene is None:
        _scene = RayScene()
        _scene.ambient = Color(20, 20, 30)
        # Floor
        _scene.objects.append(Plane(0, 1, 0, -2.2, Color(40, 40, 60), reflect=0.5))
        # Back wall (behind spheres, facing camera)
        _scene.objects.append(Plane(0, 0, 1, 4.5, Color(50, 45, 60), reflect=0.55))
        # Left wall
        _scene.objects.append(Plane(1, 0, 0, -3.5, Color(45, 50, 60), reflect=0.5))
        # Right wall
        _scene.objects.append(Plane(-1, 0, 0, -3.5, Color(45, 50, 60), reflect=0.5))
        # Ceiling
        _scene.objects.append(Plane(0, -1, 0, -3.0, Color(35, 35, 50), reflect=0.4))
        # Spheres - cluster near back of room
        colors = [
            Color(255, 60, 60), Color(60, 255, 60), Color(60, 60, 255),
            Color(255, 255, 60), Color(255, 140, 20), Color(200, 60, 255),
        ]
        for i in range(6):
            a = i * math.pi / 3 + t * 0.03
            x = math.cos(a) * 1.6
            z = math.sin(a) * 1.6 + 1.0
            _scene.objects.append(Sphere(x, -0.8 + math.sin(t * 0.2 + i) * 0.2, z, 0.55 + 0.05 * i,
                                          colors[i], reflect=0.6 + 0.05 * i))
        _scene.lights.append((3, 5, 2, Color(255, 240, 220), 2.0))
        _scene.lights.append((-3, 3, 1, Color(180, 180, 255), 1.5))
    # Update sphere positions over time for gentle motion
    for i in range(6):
        obj = _scene.objects[5 + i]  # skip 5 planes
        if isinstance(obj, Sphere):
            a = i * math.pi / 3 + t * 0.03
            obj.cx = math.cos(a) * 1.6
            obj.cz = math.sin(a) * 1.6 + 1.0
            obj.cy = -0.8 + math.sin(t * 0.2 + i) * 0.2
    cam = (math.sin(t * 0.12) * 4.0, 0.5 + math.sin(t * 0.15) * 0.2, -5.0 + math.cos(t * 0.1) * 0.3)
    _scene.render(hr, cam, (0, 0.2, 1.5), 60)
    hr.to_canvas(c)
    c.draw_text(2, 0, 'Hall of Mirrors', Color(255, 200, 150), z=100)
    c.draw_text(2, c.h - 1, '6 spheres | 5 reflective surfaces | nested reflections', DIM, z=100)
