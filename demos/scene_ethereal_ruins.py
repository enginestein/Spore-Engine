import math, random
from spore_engine import *
from spore_engine.core.color import *


# A beautiful ancient ruins map with arches and chambers
_RUINS_MAP = [
    "1111111111111111111111111111111111111",
    "1000000000000000000000000000000000001",
    "1000111110000011111100000111110000001",
    "1000100010000010000100000100010000001",
    "1000100010000010000100000100010000001",
    "1000100010000010000100000100010000001",
    "1000111010000011111100000111010000001",
    "1000000000000000000000000000000000001",
    "1000000000000000000000000000000000001",
    "1000110000111000000001110000111000001",
    "1000100000100000000000100000100000001",
    "1000100000100000000000100000100000001",
    "1000100000100000000000100000100000001",
    "1000110000111000000001110000111000001",
    "1000000000000000000000000000000000001",
    "1000000000000000000000000000000000001",
    "1000111000001111100000001111000010001",
    "1000100000001000100000001000000010001",
    "1000100000001000100000001000000010001",
    "1000100000001000100000001000000010001",
    "1000111000001111100000001111000010001",
    "1000000000000000000000000000000000001",
    "1000000000000000000000000000000000001",
    "1111111111111111111111111111111111111",
]


# Ethereal color palettes
_WALL_GRAD = Gradient(Color(50, 30, 80), Color(100, 60, 140), Color(160, 100, 200), Color(200, 160, 255))
_FLOOR_GRAD = Gradient(Color(8, 5, 20), Color(20, 12, 40), Color(35, 20, 60), Color(50, 30, 80))
_CEIL_GRAD = Gradient(Color(3, 3, 15), Color(8, 5, 30), Color(15, 10, 50), Color(25, 15, 60))

def _draw_minimap(c, m, px, py, pdx, pdy):
    """Draw a small minimap in the corner"""
    mw, mh = len(m[0]), len(m)
    s = min(c.w // (mw * 2 + 2), c.h // (mh * 2 + 2), 1)
    if s < 1:
        return
    ox, oy = c.w - mw * s - 3, c.h - mh * s - 3
    for my in range(mh):
        for mx in range(mw):
            ch = '█' if m[my][mx] == '1' else '·'
            col = Color(180, 120, 200) if m[my][mx] == '1' else Color(40, 30, 60)
            c.set_pixel(ox + mx * s, oy + my * s, ch, col, z=50)
    c.set_pixel(ox + int(px * s), oy + int(py * s), '@', CYAN, z=50)
    c.set_pixel(ox + int((px + pdx) * s), oy + int((py + pdy) * s), '♦', YELLOW, z=50)


def _is_wall(m, mx, my):
    """Check if a map cell is a wall (1)"""
    if mx < 0 or mx >= len(m[0]) or my < 0 or my >= len(m):
        return True
    return m[my][mx] == '1'


_ruins_state = None
def scene_ethereal_ruins(c: Canvas, hr: HiResCanvas, t: float, pt, dt: float):
    """Ethereal Ruins - Atmospheric raycaster through ancient glowing ruins"""
    global _ruins_state
    m = _RUINS_MAP
    mw, mh = len(m[0]), len(m)

    if _ruins_state is None:
        _ruins_state = {
            'px': 3.5, 'py': 12.5,
            'angle': 0.8,
            'turn_cooldown': 0,
            'speed': 2.2,
        }

    p = _ruins_state
    move_speed = p['speed'] * dt

    if p['turn_cooldown'] > 0:
        p['turn_cooldown'] -= dt

    # Sliding collision: try X and Y independently
    dx = math.cos(p['angle']) * move_speed
    dy = math.sin(p['angle']) * move_speed

    new_px = p['px'] + dx
    new_py = p['py'] + dy

    mx, my = int(new_px), int(p['py'])
    can_move_x = not _is_wall(m, mx, my) and not _is_wall(m, mx, int(p['py'])-1 if dy > 0 else -1) and not _is_wall(m, mx, int(p['py'])+1)

    mx, my = int(p['px']), int(new_py)
    can_move_y = not _is_wall(m, mx, my) and not _is_wall(m, int(p['px'])-1 if dx > 0 else -1, my) and not _is_wall(m, int(p['px'])+1, my)

    # Check if both axes blocked - stuck
    stuck = not can_move_x and not can_move_y

    if stuck:
        if p['turn_cooldown'] <= 0:
            p['angle'] += random.choice([-1, 1]) * random.uniform(1.4, 2.2)
            p['turn_cooldown'] = random.uniform(0.3, 0.8)
    else:
        if can_move_x:
            p['px'] = new_px
        if can_move_y:
            p['py'] = new_py

    # Smarter wandering: cast a feeler ray ahead and turn away from walls
    feeler_len = 2.0
    fx = p['px'] + math.cos(p['angle']) * feeler_len
    fy = p['py'] + math.sin(p['angle']) * feeler_len
    feeler_blocked = _is_wall(m, int(fx), int(fy))

    # Check left and right feelers too
    l_angle = p['angle'] + 0.5
    r_angle = p['angle'] - 0.5
    lx = p['px'] + math.cos(l_angle) * feeler_len * 0.7
    ly = p['py'] + math.sin(l_angle) * feeler_len * 0.7
    rx = p['px'] + math.cos(r_angle) * feeler_len * 0.7
    ry = p['py'] + math.sin(r_angle) * feeler_len * 0.7
    left_blocked = _is_wall(m, int(lx), int(ly))
    right_blocked = _is_wall(m, int(rx), int(ry))

    if feeler_blocked:
        # Turn away from what's ahead
        if left_blocked and not right_blocked:
            p['angle'] -= 0.08
        elif right_blocked and not left_blocked:
            p['angle'] += 0.08
        else:
            p['angle'] += 0.06
        p['turn_cooldown'] = max(p['turn_cooldown'], 0.15)
    elif left_blocked:
        p['angle'] += 0.03  # Slight turn right
    elif right_blocked:
        p['angle'] -= 0.03  # Slight turn left

    p['speed'] = 2.0 + 0.4 * math.sin(t * 0.5)
    px, py = p['px'], p['py']
    pdx, pdy = math.cos(p['angle']), math.sin(p['angle'])
    plane_x, plane_y = -pdy * 0.66, pdx * 0.66

    # Draw the world
    for x in range(c.w):
        camera_x = 2 * x / c.w - 1
        rdx = pdx + plane_x * camera_x
        rdy = pdy + plane_y * camera_x
        map_x, map_y = int(px), int(py)
        delta_dist_x = abs(1 / rdx) if rdx != 0 else 1e30
        delta_dist_y = abs(1 / rdy) if rdy != 0 else 1e30
        step_x = -1 if rdx < 0 else 1
        step_y = -1 if rdy < 0 else 1
        side_dist_x = (px - map_x) * delta_dist_x if rdx < 0 else (map_x + 1.0 - px) * delta_dist_x
        side_dist_y = (py - map_y) * delta_dist_y if rdy < 0 else (map_y + 1.0 - py) * delta_dist_y
        hit, side = False, 0
        while not hit:
            if side_dist_x < side_dist_y:
                side_dist_x += delta_dist_x
                map_x += step_x
                side = 0
            else:
                side_dist_y += delta_dist_y
                map_y += step_y
                side = 1
            if map_x < 0 or map_x >= mw or map_y < 0 or map_y >= mh:
                break
            if m[map_y][map_x] == '1':
                hit = True
        if not hit:
            for y in range(c.h):
                c.set_pixel(x, y, ' ')
            continue

        perp_dist = (side_dist_x - delta_dist_x) if side == 0 else (side_dist_y - delta_dist_y)
        perp_dist = max(0.01, perp_dist)
        lh = int(c.h / perp_dist)
        ds = max(0, -lh // 2 + c.h // 2)
        de = min(c.h - 1, lh // 2 + c.h // 2)

        shade = min(1, 3.0 / (perp_dist + 0.5))
        if side == 1:
            shade *= 0.65

        shimmer = 0.15 * math.sin(x * 0.3 + t * 2.0) + 0.15 * math.sin(map_x + map_y + t * 0.5)
        wall_t = max(0, min(1, shade + shimmer * 0.1))
        wcolor = _WALL_GRAD.at(wall_t)

        for y in range(ds, de + 1):
            c.set_pixel(x, y, '█', wcolor, z=10)

        for y in range(de + 1, c.h):
            d_ = (y - c.h / 2) / (c.h / 2)
            ft = min(1, d_ * 1.2)
            fcolor = _FLOOR_GRAD.at(ft)
            pattern = '▒' if (int(x / 2) + int(y)) % 3 == 0 else '░'
            c.set_pixel(x, y, pattern, fcolor, z=5)

        for y in range(ds):
            d_ = (c.h / 2 - y) / (c.h / 2)
            ct = min(1, d_ * 1.2)
            ccolor = _CEIL_GRAD.at(ct)
            c.set_pixel(x, y, '░', ccolor, z=5)

    # Add atmospheric fog particles
    for _ in range(3):
        fx = random.randint(0, c.w - 1)
        fy = random.randint(0, c.h - 1)
        cell = c.get_pixel(fx, fy)
        if cell and cell.fg:
            fog_bright = 0.08 + 0.04 * math.sin(t + fx + fy)
            c.set_pixel(fx, fy, cell.char, Color(
                min(255, cell.fg.r + int(30 * fog_bright)),
                min(255, cell.fg.g + int(20 * fog_bright)),
                min(255, cell.fg.b + int(40 * fog_bright)),
            ), z=cell.z)

    # Minimap
    _draw_minimap(c, m, px, py, pdx, pdy)

    # Title with glow effect
    hue = (t * 0.015) % 1.0
    c.draw_text(2, 0, '✧ Ethereal Ruins ✧', Color.from_hsv(hue, 0.6, 1.0), z=100)
    c.draw_text(2, c.h - 1, 'ancient chambers | glowing walls | atmospheric fog', DIM, z=100)
