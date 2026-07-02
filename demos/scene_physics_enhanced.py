import math, random
from spore_engine.core.color import Color, WHITE, RED, GREEN, BLUE, YELLOW, CYAN, ORANGE, DIM
from spore_engine.core.canvas import Canvas
from spore_engine.sim.physics import (
    PhysicsWorld, Body, Spring, Vec2 as PVec2, AABB,
    RectBody, ForceField, DistanceJoint, resolve_aabb
)

_LS = None

def scene_physics_enhanced(c, hr, t, pt, dt):
    global _LS
    if _LS is None:
        world = PhysicsWorld(gravity=6.0, bounds_x=c.w, bounds_y=c.h)
        bodies = []
        w, h = c.w, c.h
        for _ in range(8):
            b = Body(
                random.uniform(10, w - 10),
                random.uniform(3, h // 2),
                random.uniform(0.5, 1.5),
                random.uniform(0.5, 2.0),
                Color(random.randint(100, 255), random.randint(100, 255), random.randint(100, 255))
            )
            b.vel.x = random.uniform(-5, 5)
            world.add_body(b)
            bodies.append(b)

        rects = []
        for _ in range(4):
            rb = RectBody(
                random.uniform(5, w - 10),
                random.uniform(2, h // 3),
                random.uniform(2, 4),
                random.uniform(2, 4),
                random.uniform(1, 3),
                Color(random.randint(150, 255), random.randint(100, 200), random.randint(100, 200))
            )
            rb.vel.x = random.uniform(-3, 3)
            rects.append(rb)

        chain_bodies = PhysicsWorld.chain(world, w // 2, 2, 12, 2.5, 0.6, Color(180, 200, 255))

        force_field = ForceField(5, h - 6, 15, 5, fx=3, fy=-1, strength=2.0,
                                 color=Color(40, 80, 180))

        _LS = {
            'world': world,
            'bodies': bodies,
            'rects': rects,
            'chain_bodies': chain_bodies,
            'force_field': force_field,
            'time': 0.0,
            'mode': 0,
        }
    s = _LS
    s['time'] += dt

    world = s['world']
    rects = s['rects']

    world.step(dt, substeps=6)

    for rb in rects:
        rb.update(dt, world.gravity, AABB(0, 0, c.w, c.h))
        for body in world.bodies:
            if rb.aabb.overlaps(AABB(body.pos.x - body.radius, body.pos.y - body.radius,
                                     body.radius * 2, body.radius * 2)):
                overlap_x = min(rb.aabb.right - body.pos.x + body.radius,
                               body.pos.x + body.radius - rb.aabb.left)
                overlap_y = min(rb.aabb.bottom - body.pos.y + body.radius,
                               body.pos.y + body.radius - rb.aabb.top)
                if overlap_x < overlap_y:
                    if rb.aabb.cx < body.pos.x:
                        body.pos.x += overlap_x * 0.5
                        rb.aabb.x -= overlap_x * 0.5
                    else:
                        body.pos.x -= overlap_x * 0.5
                        rb.aabb.x += overlap_x * 0.5
                    body.vel.x, rb.vel.x = rb.vel.x * 0.5, body.vel.x * 0.5
                else:
                    if rb.aabb.cy < body.pos.y:
                        body.pos.y += overlap_y * 0.5
                        rb.aabb.y -= overlap_y * 0.5
                    else:
                        body.pos.y -= overlap_y * 0.5
                        rb.aabb.y += overlap_y * 0.5
                    body.vel.y, rb.vel.y = rb.vel.y * 0.5, body.vel.y * 0.5

        for rb2 in rects:
            if rb2 is not rb:
                resolve_aabb(rb, rb2)

    s['force_field'].aabb.x = 5 + 15 * (0.5 + 0.5 * math.sin(s['time'] * 0.2))

    for body in world.bodies:
        s['force_field'].apply_to(body)

    c.clear()
    for y in range(c.h):
        ty = y / c.h
        for x in range(c.w):
            n = (math.sin(x*0.03+t*0.15)+math.cos(y*0.04+t*0.1))*0.5+0.5
            c.set_pixel(x, y, ' ', bg=Color(int(4+n*8), int(2+n*6), int(12+n*18)), z=-100)

    s['force_field'].render(c, z=5)

    world.render(c, z=10, show_trails=True)

    for rb in rects:
        rb.render(c, z=10)

    b_clamped = []
    for i in range(len(s['chain_bodies'])):
        b = s['chain_bodies'][i]
        b.pos.x = max(0, min(c.w-1, b.pos.x))
        b.pos.y = max(0, min(c.h-1, b.pos.y))
        b.vel.x *= 0.98
        b.vel.y += 2.0 * dt

    for i in range(len(s['chain_bodies']) - 1):
        b1 = s['chain_bodies'][i]
        b2 = s['chain_bodies'][i + 1]
        x1, y1 = round(b1.pos.x), round(b1.pos.y)
        x2, y2 = round(b2.pos.x), round(b2.pos.y)
        if abs(x1-x2) < c.w and abs(y1-y2) < c.h:
            c.draw_line(x1, y1, x2, y2, '.', Color(150, 180, 255), z=5)

    c.draw_text(2, 0, "Enhanced Physics", WHITE, z=20)
    c.draw_text(2, 1, f"Bodies: {len(world.bodies)} | Rects: {len(rects)} | Chain: {len(s['chain_bodies'])}", DIM, z=20)
    c.draw_text(2, c.h - 1, "Force field (blue) pushes bodies | AABB + circle collision", DIM, z=20)
