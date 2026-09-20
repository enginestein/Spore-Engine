import math, random
from spore_engine import *
from spore_engine.core.color import *
from spore_engine.render3d.raytracer import RayScene, Sphere, Plane, Box, Cylinder


_scene = None
def scene_prism_raytracer(c: Canvas, hr: HiResCanvas, t: float, pt, dt: float):
    """Prism Raytracer - Refractive glass prisms, chromatic dispersion, atmospheric fog, glowing gems"""
    global _scene
    if _scene is None:
        _scene = RayScene()
        _scene.ambient = Color(25, 20, 40)
        _scene.bg_color = Color(8, 6, 25)

        # Floor - dark marble
        _scene.objects.append(Plane(0, 1, 0, -2.0, Color(40, 35, 55), reflect=0.25))
        # Back wall - deep atmospheric
        _scene.objects.append(Plane(0, 0, 1, 6.0, Color(20, 18, 40), reflect=0.1))
        # Ceiling
        _scene.objects.append(Plane(0, -1, 0, -4.0, Color(15, 12, 35), reflect=0.2))

        # Central glass sphere (refractive)
        _scene.objects.append(Sphere(0, 0.2, 2.5, 0.9, Color(200, 220, 255), 
                                      reflect=0.15, refract=0.85, ior=1.52))
        # Left sphere - ruby
        _scene.objects.append(Sphere(-1.8, -0.3, 1.8, 0.7, Color(255, 40, 40), 
                                      reflect=0.6, refract=0.0))
        # Right sphere - sapphire
        _scene.objects.append(Sphere(1.8, -0.1, 2.0, 0.6, Color(50, 80, 255), 
                                      reflect=0.5, refract=0.0))
        # Small floating crystal (refractive)
        _scene.objects.append(Sphere(0.5, 1.8, 1.5, 0.35, Color(255, 180, 60), 
                                      reflect=0.3, refract=0.5, ior=1.8))
        # Cylinder - emerald pillar
        _scene.objects.append(Cylinder(-1.0, -1.3, 4.0, 0.3, 1.8, Color(60, 255, 100), 
                                        reflect=0.35, emissive=0.1))
        # Box - golden platform
        _scene.objects.append(Box(0, -1.8, 3.0, 2.5, 0.2, 1.0, Color(200, 160, 80), 
                                   reflect=0.4))

        # Lights - colored for dramatic effect
        _scene.lights.append((-3, 5, 1, Color(255, 180, 150), 2.5))   # warm
        _scene.lights.append((3, 4, 2, Color(150, 180, 255), 2.0))    # cool
        _scene.lights.append((0, 3, -2, Color(255, 200, 255), 1.0))   # fill

    # Animate sphere positions gently
    objs = _scene.objects
    # Glass sphere oscillates slightly
    objs[3].cy = 0.2 + 0.15 * math.sin(t * 0.3)  # glass sphere
    objs[4].cy = -0.3 + 0.2 * math.sin(t * 0.2 + 1)  # ruby
    objs[5].cy = -0.1 + 0.15 * math.sin(t * 0.25 + 2)  # sapphire
    objs[6].cy = 1.8 + 0.3 * math.sin(t * 0.4 + 3)  # crystal
    objs[6].cz = 1.5 + 0.2 * math.cos(t * 0.3 + 1)  # crystal orbit

    # Animate lights with gentle movement
    lx1 = -3 + math.sin(t * 0.15) * 0.5
    lx2 = 3 + math.cos(t * 0.12) * 0.5
    _scene.lights[0] = (lx1, 5 + 0.3 * math.sin(t * 0.2), 1 + 0.3 * math.cos(t * 0.18), 
                        Color(255, 180, 150), 2.5)
    _scene.lights[1] = (lx2, 4 + 0.3 * math.cos(t * 0.22), 2 + 0.3 * math.sin(t * 0.15), 
                        Color(150, 180, 255), 2.0)

    # Camera orbits slowly
    cam_angle = t * 0.06
    cam_x = 4.5 * math.sin(cam_angle)
    cam_z = -3.5 + 1.5 * math.cos(cam_angle * 0.7)
    cam_y = 0.8 + 0.4 * math.sin(t * 0.1)
    _scene.render(hr, (cam_x, cam_y, cam_z), (0, 0.2, 2.5), 55)
    hr.to_canvas(c)
    c.draw_text(2, 0, '◆ Prism Raytracer ◆', Color(255, 220, 150), z=100)
    c.draw_text(2, c.h - 1, 'refractive glass | ruby | sapphire | emerald | colored lights', DIM, z=100)
