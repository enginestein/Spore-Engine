import math, random
from spore_engine import *
from spore_engine.core.color import *
from spore_engine.sim.physics import (
    Body, RectBody, PolyBody, CompoundBody,
    EnhancedPhysicsWorld, RigidBody,
    resolve_collision, resolve_poly_poly, resolve_circle_poly,
    resolve_circle_aabb,
)

_PH = None

def _make_polygon(n: int, r: float) -> list[tuple[float, float]]:
    return [
        (r * math.cos(i / n * math.pi * 2), r * math.sin(i / n * math.pi * 2))
        for i in range(n)
    ]

def scene_physics_rigid(c, hr, t, pt, dt):
    global _PH
    w, h = c.w, c.h

    if _PH is None:
        world = EnhancedPhysicsWorld(gravity=15, bounds_x=w, bounds_y=h)

        for i in range(6):
            rx = random.randint(5, w - 5)
            b = Body(rx, random.randint(-10, 0), random.uniform(1.0, 2.5),
                     random.uniform(0.5, 2), Color.from_hsv(i * 0.15, 0.7, 0.9))
            b.restitution = random.uniform(0.2, 0.6)
            world.add_body(b)

        for i in range(4):
            sides = random.choice([3, 4, 5, 6])
            r = random.uniform(2.0, 4.0)
            verts = _make_polygon(sides, r)
            px = random.randint(5, w - 5)
            poly = PolyBody(verts, random.uniform(1, 3),
                            Color.from_hsv(0.6 + i * 0.08, 0.7, 0.9),
                            pos=(px, random.randint(-15, -5)))
            poly.restitution = 0.3
            world.add_body(poly)

        for i in range(3):
            comp = CompoundBody(random.randint(5, w - 5), random.randint(-20, -10),
                                random.uniform(1, 3),
                                Color.from_hsv(0.8 + i * 0.1, 0.6, 0.9))
            comp.add_circle(0, 0, 1.5, 0.5)
            comp.add_rect(2.5, -0.5, 2, 1, 0.5)
            comp.add_poly(0, -2.5, _make_polygon(3, 1.5), 0.5)
            world.add_body(comp)

        floor = RectBody(0, h - 2, w, 2, mass=0, color=DIM)
        floor.locked = True
        world.add_body(floor)

        _PH = {'world': world, 'timer': 0}

    s = _PH
    world = s['world']
    world.bounds_x = w
    world.bounds_y = h

    s['timer'] += dt
    if s['timer'] > 2:
        s['timer'] = 0
        b = Body(random.randint(3, w - 3), -5,
                 random.uniform(0.8, 2.0), random.uniform(0.3, 1.5),
                 Color.from_hsv(random.random(), 0.7, 0.9))
        b.restitution = random.uniform(0.2, 0.7)
        world.add_body(b)

        if random.random() < 0.4:
            sides = random.choice([3, 4, 5, 6])
            r = random.uniform(1.5, 3.0)
            verts = _make_polygon(sides, r)
            poly = PolyBody(verts, random.uniform(0.5, 2),
                            Color.from_hsv(random.random(), 0.7, 0.9),
                            pos=(random.randint(3, w - 3), -8))
            world.add_body(poly)

    world.step(dt, substeps=8)

    for y in range(h):
        for x in range(w):
            col = Color(int(5 + y * 6 // h), int(3 + y * 3 // h), int(8 + y * 5 // h))
            c.set_pixel(x, y, ' ', bg=col, z=-100)

    world.render(c, z=5)

    for body in world.bodies:
        if isinstance(body, Body) and hasattr(body, 'radius'):
            r = max(1, round(body.radius))
            cx, cy = round(body.pos.x), round(body.pos.y)
            if isinstance(body, RigidBody):
                dx = round(cx + math.cos(body.angle) * r)
                dy = round(cy + math.sin(body.angle) * r)
                c.draw_line(cx, cy, dx, dy, '@', body.color.mul(1.3), z=10)

    c.draw_text(2, 0, "Rigid Body Physics", WHITE, z=100)
    c.draw_text(2, h - 1,
        f"Bodies:{len(world.bodies)} Poly:{len(world.poly_bodies)}",
        DIM, z=100)
