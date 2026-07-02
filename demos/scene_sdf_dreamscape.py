import math
from spore_engine import *
from spore_engine.core.color import *
from spore_engine.render3d.sdf import *
from spore_engine.core.geom import Vec3


_g_scene = None
def scene_sdf_dreamscape(c: Canvas, hr: HiResCanvas, t: float, pt, dt: float):
    """SDF Dreamscape — Floating islands, glowing crystals, volumetric fog, orbiting lights"""
    global _g_scene
    if _g_scene is None:
        _g_scene = SDFScene()
        _g_scene.ambient = Color(15, 12, 30)

        # Simpler island — 2 ops instead of 3
        def ground(p):
            return sd_plane(p, Vec3(0, 1, 0), -1.5)

        def floating_island(p):
            d1 = sd_sphere(p, Vec3(0, 0.1, 0), 2.0)
            d2 = sd_sphere(p, Vec3(0, 1.2, 0), 1.0)
            return op_union(d1, d2)

        def crystal_cluster(p):
            """3 fixed crystals (no per-frame trig inside SDF)"""
            d = 1e9
            d = op_union(d, sd_box(p, Vec3(1.1, 1.0, 0.9), Vec3(0.10, 0.8, 0.10)))
            d = op_union(d, sd_box(p, Vec3(-0.8, 0.9, -1.0), Vec3(0.10, 0.7, 0.10)))
            d = op_union(d, sd_box(p, Vec3(-0.3, 1.1, 1.2), Vec3(0.10, 0.6, 0.10)))
            return d

        def glowing_orb(p):
            return sd_sphere(p, Vec3(0, 1.8, 0), 0.3)

        _g_scene.add(ground, Color(30, 25, 50), reflectivity=0.1)
        _g_scene.add(floating_island, Color(60, 75, 120), reflectivity=0.1)
        _g_scene.add(crystal_cluster, Color(140, 220, 255), reflectivity=0.3, emissive=0.1)

        _g_scene.add_light(Vec3(3, 5, -3), Color(255, 200, 180), 2.0)
        _g_scene.add_light(Vec3(-3, 4, 4), Color(120, 180, 255), 1.5)

    # Animate the glowing orb position (separate from static scene)
    # Rebuild the orb each frame with animated position
    obx = 1.5 * math.cos(t * 0.2)
    obz = 1.5 * math.sin(t * 0.2)
    oby = 1.8 + 0.4 * math.sin(t * 0.3)

    # Replace the orb object at index 3
    def animated_orb(p):
        return sd_sphere(p, Vec3(obx, oby, obz), 0.3)

    objects = _g_scene.objects
    # Keep first 3 (ground, island, crystals), replace 4th (orb) and add animated light
    _g_scene.objects = objects[:3]
    _g_scene.add(animated_orb, Color(255, 180, 60), emissive=0.8)

    # Animate orbiting light
    lx = 4 * math.cos(t * 0.2)
    lz = 4 * math.sin(t * 0.2)
    _g_scene.lights[0] = (Vec3(lx, 5 + math.sin(t * 0.3), lz), Color(255, 200, 180), 2.0)

    # Camera orbits
    cx = 5.5 * math.cos(t * 0.12)
    cz = 5.5 * math.sin(t * 0.12)
    cy = 1.8 + 0.6 * math.sin(t * 0.08)
    camera = Vec3(cx, cy, cz)
    target = Vec3(0, 0.8, 0)

    # Faster rendering with fewer steps
    _g_scene.max_steps = 36
    _g_scene.render(c, camera, target, 60)
    c.draw_text(2, 0, '✦ SDF Dreamscape ✦', Color(255, 200, 100), z=10)
    c.draw_text(2, c.h - 1, 'floating island | crystals | glowing orb | orbiting light', DIM, z=10)

