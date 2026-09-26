import math
from spore_engine import *
from spore_engine.core.color import *
from spore_engine.sim.physics import Body, DistanceJoint, PhysicsWorld, Vec2
import demos as _demos


H = 0; UT = 1; MT = 2; PL = 3
LUA = 4; LFA = 5; LH = 6
RUA = 7; RFA = 8; RH = 9
LTH = 10; LSH = 11; LF = 12
RTH = 13; RSH = 14; RF = 15

SKIN = Color(255, 210, 170)
SHIRT = Color(65, 130, 215)
PANTS = Color(50, 60, 95)
BOOTS = Color(50, 45, 40)
HAIR = Color(110, 70, 35)

BODY_DEFS = [
    ('Head',       0,   -7.5,  1.6, SKIN,   'O', 2.5),
    ('UpTorso',    0,   -4.5,  1.6, SHIRT,  '#', 4.0),
    ('MidTorso',   0,   -2.0,  1.4, SHIRT,  '#', 3.5),
    ('Pelvis',     0,    0.5,  1.2, PANTS,  '#', 3.0),
    ('LUpArm',    -2.8, -4.5,  0.7, SKIN,   'o', 1.2),
    ('LForearm',  -3.5, -2.0,  0.6, SKIN,   'o', 0.8),
    ('LHand',     -3.5,  0.0,  0.4, SKIN,   '.', 0.4),
    ('RUpArm',     2.8, -4.5,  0.7, SKIN,   'o', 1.2),
    ('RForearm',   3.5, -2.0,  0.6, SKIN,   'o', 0.8),
    ('RHand',      3.5,  0.0,  0.4, SKIN,   '.', 0.4),
    ('LThigh',    -1.2,  0.5,  0.9, PANTS,  'o', 2.0),
    ('LShin',     -1.2,  3.0,  0.7, PANTS,  'o', 1.2),
    ('LFoot',     -1.2,  5.0,  0.5, BOOTS,  '.', 0.6),
    ('RThigh',     1.2,  0.5,  0.9, PANTS,  'o', 2.0),
    ('RShin',      1.2,  3.0,  0.7, PANTS,  'o', 1.2),
    ('RFoot',      1.2,  5.0,  0.5, BOOTS,  '.', 0.6),
]

JOINT_DEFS = [
    (H, UT), (UT, MT), (MT, PL),
    (UT, LUA), (LUA, LFA), (LFA, LH),
    (UT, RUA), (RUA, RFA), (RFA, RH),
    (PL, LTH), (LTH, LSH), (LSH, LF),
    (PL, RTH), (RTH, RSH), (RSH, RF),
]

TORSOS = {UT, MT, PL}
HEAD = H
GROUND_TOP = Color(25, 70, 30)
GROUND_BTM = Color(15, 40, 20)
FLOOR_GRAD = Gradient(GROUND_TOP, GROUND_BTM)
SKY_TOP = Color(8, 8, 25)
SKY_BTM = Color(20, 15, 40)
SKY_GRAD = Gradient(SKY_TOP, SKY_BTM)

LIMB_COLORS = {
    H: SKIN, UT: SHIRT, MT: SHIRT, PL: PANTS,
    LUA: SKIN, LFA: SKIN, LH: SKIN,
    RUA: SKIN, RFA: SKIN, RH: SKIN,
    LTH: PANTS, LSH: PANTS, LF: BOOTS,
    RTH: PANTS, RSH: PANTS, RF: BOOTS,
}

JOINT_PAIRS = [
    (UT, LUA), (LUA, LFA), (LFA, LH),
    (UT, RUA), (RUA, RFA), (RFA, RH),
    (PL, LTH), (LTH, LSH), (LSH, LF),
    (PL, RTH), (RTH, RSH), (RSH, RF),
]


def _build_ragdoll(world, cx, cy):
    bodies = []
    for _, ox, oy, r, col, _, mass in BODY_DEFS:
        b = Body(cx + ox, cy + oy, r, mass, col)
        b.restitution = 0.15
        b.friction = 0.9
        world.add_body(b)
        bodies.append(b)

    for i, j in JOINT_DEFS:
        a, b = bodies[i], bodies[j]
        dj = DistanceJoint(a, b, a.pos.dist(b.pos), stiffness=85)
        world.add_spring(dj)

    return bodies


def _nearest_part(bodies, px, py):
    best_idx, best_d = -1, 1e9
    for i, b in enumerate(bodies):
        d = b.pos.dist(Vec2(px, py))
        if d < best_d:
            best_d, best_idx = d, i
    return best_idx, best_d


def _draw_thick_limb(c, x1, y1, x2, y2, color, z=0):
    dx, dy = x2 - x1, y2 - y1
    steps = round(max(abs(dx), abs(dy)))
    if steps == 0:
        return
    adx, ady = abs(dx), abs(dy)
    if ady > adx * 2:
        ch = '|'
        oy = -1 if dy < 0 else 1
        ox = 0
    elif adx > ady * 2:
        ch = '-'
        ox = -1 if dx < 0 else 1
        oy = 0
    elif (dx > 0 and dy < 0) or (dx < 0 and dy > 0):
        ch = '/'
        ox = 1 if dx > 0 else -1
        oy = -1 if dy < 0 else 1
    else:
        ch = '\\'
        ox = 1 if dx > 0 else -1
        oy = 1 if dy > 0 else -1

    dim = color.mul(0.6)
    for i in range(steps + 1):
        t = i / steps
        xi, yi = int(x1 + dx * t), int(y1 + dy * t)
        c.set_pixel(xi, yi, ch, color, z=z)
        c.set_pixel(xi + ox, yi + oy, ch, dim, z=z)


def _draw_torso(c, bodies, z=0):
    ut, mt, pl = [bodies[i] for i in (UT, MT, PL)]
    pts = [(round(b.pos.x), round(b.pos.y)) for b in (ut, mt, pl)]
    y1 = max(0, min(y for _, y in pts) - 2)
    y2 = min(c.h - 1, max(y for _, y in pts) + 2)
    xs_at_y = {}
    for y in range(y1, y2 + 1):
        hits = []
        for bx, by in pts:
            dy = y - by
            for b in (ut, mt, pl):
                r = round(b.radius + 0.3)
                if abs(dy) <= r:
                    hw = round(math.sqrt(max(0, r * r - dy * dy)))
                    hits.extend([round(b.pos.x) - hw, round(b.pos.x) + hw])
        if hits:
            xs_at_y[y] = (max(0, min(hits)), min(c.w - 1, max(hits)))

    for y, (lx, rx) in xs_at_y.items():
        for x in range(lx, rx + 1):
            col = SHIRT if (x + y) % 3 != 0 else SHIRT.mul(0.6)
            c.set_pixel(x, y, '#', col, z=z)


def scene_ragdoll(c, hr, t, pt, dt):
    st = getattr(scene_ragdoll, 'state', None)
    if st is None:
        world = PhysicsWorld(gravity=12.0, bounds_x=c.w, bounds_y=0)
        cx, cy = c.w // 2, c.h // 3
        bodies = _build_ragdoll(world, cx, cy)
        st = {
            'world': world,
            'bodies': bodies,
            'grab_idx': -1,
            'cursor_x': c.w // 2,
            'cursor_y': c.h // 4,
            'ground_y': c.h - 2,
            'respawn_timer': 0.0,
        }
        scene_ragdoll.state = st

    if c.w != st.get('last_w') or c.h != st.get('last_h'):
        st['last_w'] = c.w
        st['last_h'] = c.h
        st['world'].bounds_x = c.w
        st['ground_y'] = c.h - 2
        if st['cursor_x'] >= c.w:
            st['cursor_x'] = c.w // 2

    world = st['world']
    bodies = st['bodies']
    key = _demos.KEY_PRESSED if hasattr(_demos, 'KEY_PRESSED') else None

    speed = 2.5
    if key == 'left':
        st['cursor_x'] = max(1, st['cursor_x'] - speed)
    elif key == 'right':
        st['cursor_x'] = min(c.w - 1, st['cursor_x'] + speed)
    elif key == 'up':
        st['cursor_y'] = max(1, st['cursor_y'] - speed)
    elif key == 'down':
        st['cursor_y'] = min(c.h - 3, st['cursor_y'] + speed)
    elif key == '\r':
        if st['grab_idx'] >= 0:
            st['grab_idx'] = -1
        else:
            idx, dist = _nearest_part(bodies, st['cursor_x'], st['cursor_y'])
            if idx >= 0 and dist < 6.0:
                st['grab_idx'] = idx

    ground_y = st['ground_y']
    dt = min(dt, 0.033)

    world.step(dt, substeps=6)

    for b in bodies:
        if b.pos.y + b.radius > ground_y:
            b.pos.y = ground_y - b.radius
            b.vel.y *= -0.12
            b.vel.x *= 0.88

    c.gradient_fill(0, 0, c.w, ground_y, SKY_GRAD, horizontal=False, z=-100)
    c.gradient_fill(0, ground_y, c.w, c.h - ground_y, FLOOR_GRAD, horizontal=False, z=-100)

    for x in range(c.w):
        c.set_pixel(x, ground_y, '=', Color(40, 100, 40), z=-99)
        c.set_pixel(x, ground_y + 1, '.', Color(30, 80, 30), z=-99)

    _draw_torso(c, bodies, z=1)

    hb = bodies[H]
    hx, hy = round(hb.pos.x), round(hb.pos.y)
    hr_int = max(1, round(hb.radius + 0.3))
    if 0 < hx - hr_int and hx + hr_int < c.w and 0 < hy - hr_int and hy + hr_int < c.h:
        c.draw_circle(hx, hy, hr_int, fill=True, fg=SKIN, z=2)
        hair_col = HAIR
        for dy in (-hr_int, -hr_int + 1):
            for dx in range(-hr_int + 1, hr_int):
                nx, ny = hx + dx, hy + dy
                if 0 <= nx < c.w and 0 <= ny < c.h:
                    c.set_pixel(nx, ny, '#', hair_col, z=3)
        eye_col = Color(50, 40, 35)
        for ex, ey in [(-1, 0), (1, 0)]:
            nx, ny = hx + ex, hy + ey
            if 0 <= nx < c.w and 0 <= ny < c.h:
                c.set_pixel(nx, ny, '.', eye_col, z=3)

    for i, j in JOINT_PAIRS:
        a, b = bodies[i], bodies[j]
        _draw_thick_limb(c, a.pos.x, a.pos.y, b.pos.x, b.pos.y,
                         LIMB_COLORS[i], z=1)

    for i, (_, _, _, r, col, ch, _) in enumerate(BODY_DEFS):
        if i == H or i in TORSOS:
            continue
        b = bodies[i]
        x, y = round(b.pos.x), round(b.pos.y)
        if 0 <= x < c.w and 0 <= y < c.h:
            rr = max(1, round(r + 0.3))
            if rr >= 2:
                c.draw_circle(x, y, rr, fill=True, fg=col, z=3)
                c.set_pixel(x, y, ch, Color(255, 255, 255).mul(0.5), z=4)
            else:
                c.set_pixel(x, y, ch, col, z=3)

    if st['grab_idx'] >= 0:
        gb = bodies[st['grab_idx']]
        dx = st['cursor_x'] - gb.pos.x
        dy = st['cursor_y'] - gb.pos.y
        dist = math.sqrt(dx * dx + dy * dy)
        if dist > 0.5:
            pull = 80.0
            gb.apply_force(dx / dist * pull, dy / dist * pull)

        gx, gy = round(gb.pos.x), round(gb.pos.y)
        if 0 <= gx < c.w and 0 <= gy < c.h:
            c.set_pixel(gx, gy, '@', Color(255, 255, 100), z=5)

    st['respawn_timer'] += dt
    offscreen = any(b.pos.y > c.h + 30 for b in bodies)
    if offscreen and st['respawn_timer'] > 2.0:
        st['respawn_timer'] = 0.0
        cx, cy = c.w // 2, c.h // 3
        for i, b in enumerate(bodies):
            _, ox, oy, _, _, _, _ = BODY_DEFS[i]
            b.pos = Vec2(cx + ox, cy + oy)
            b.vel = Vec2(0, 0)
        st['grab_idx'] = -1

    if key == 'r':
        cx, cy = c.w // 2, c.h // 3
        for i, b in enumerate(bodies):
            _, ox, oy, _, _, _, _ = BODY_DEFS[i]
            b.pos = Vec2(cx + ox, cy + oy)
            b.vel = Vec2(0, 0)
        st['grab_idx'] = -1

    cx, cy = int(st['cursor_x']), int(st['cursor_y'])
    if 0 <= cx < c.w and 0 <= cy < c.h:
        for dy in (-2, -1, 1, 2):
            ny = cy + dy
            if 0 <= ny < c.h:
                c.set_pixel(cx, ny, '|', Color(255, 200, 80), z=10)
        for dx in (-2, -1, 1, 2):
            nx = cx + dx
            if 0 <= nx < c.w:
                c.set_pixel(nx, cy, '-', Color(255, 200, 80), z=10)
        c.set_pixel(cx, cy, '+', Color(255, 220, 60), z=10)

    grab_name = BODY_DEFS[st['grab_idx']][0] if st['grab_idx'] >= 0 else 'none'
    c.draw_text(2, 0, f'Ragdoll  |  Grab: {grab_name}  |  Arrows=move  Enter=grab  [R]espawn', WHITE, z=50)
    c.draw_text(2, c.h - 1, 'Click Enter to grab a body part near the cursor', DIM, z=50)
