import math
import random
from spore_engine import *
from spore_engine.core.color import *
from .constants import *

_WB = None
_sound = None
_FIRE_G = Gradient.from_palette('fire')


def set_sound(eng):
    global _sound
    _sound = eng


def get_sound():
    return _sound


def _sfx(kind, x=None, vol=1.0, pitch=1.0):
    eng = _sound
    if eng is None:
        return
    try:
        eng.event(kind, x, vol, pitch)
    except Exception:
        pass


CRY_CHARS = ('!', '¡', '…', '☄')


def _war_cry(s, fac):
    """A random living soldier of a faction throws a battle cry - a shout with
    a tiny visible shout-mark so it reads on screen even without audio."""
    rnd = s['rnd']
    alive = [o for o in s['soldiers'] if not o['dead'] and o['faction'] == fac]
    if not alive:
        return
    shouter = rnd.choice(alive)
    x = shouter['x']
    _sfx('cry', x, 0.7, 1.0)
    ch = rnd.choice(CRY_CHARS)
    s['shouts'].append({'x': x, 'y': s['gy'] - 6, 'age': 0.0,
                        'life': 0.5, 'ch': ch, 'faction': fac})


def _update_shouts(s, hr, w, h, cam, dt):
    keep = []
    for sh in s['shouts']:
        sh['age'] += dt
        if sh['age'] >= sh['life']:
            continue
        rise = int(sh['age'] * 9)
        sx = int(sh['x'] - cam)
        py = int(sh['y']) - rise
        a = 1.0 - sh['age'] / sh['life']
        if 0 <= sx < w and 0 <= py < h:
            col = Color.from_hsv(FACTION_HUE[sh['faction']], 0.9, a)
            hr.set_pixel(sx, py, sh['ch'], fg=col, z=70)
        keep.append(sh)
    s['shouts'] = keep

__all__ = [
    '_WB', '_init', 'set_sound', 'get_sound', '_sfx',
    '_war_cry', '_update_shouts',
    '_spawn_missile', '_spawn_soldier', '_make_soldier', '_fire', '_kill',
    '_impact', '_think', '_update_soldiers', '_update_bullets', '_update_corpses',
    '_blast_soldiers', '_spawn_gunship', '_spawn_mother', '_spawn_tank',
    '_spawn_transport', '_spawn_chute', '_update_chutes', '_render_chute',
    '_spawn_drone', '_spawn_swarm', '_update_drones', '_render_drone',
    '_destroy_drone',
    '_spawn_hacker', '_update_hackers', '_render_hacker', '_render_pulse',
    '_spawn_sniper', '_update_snipers', '_render_sniper', '_destroy_sniper',
    '_spawn_builder', '_update_builders', '_render_builder', '_complete_bunker',
    '_spawn_driller', '_driller_target', '_driller_strike', '_driller_surface',
    '_update_drillers', '_render_driller',
    '_spawn_fighter', '_strafe_hit', '_target_active', '_fire_air',
    '_update_air', '_steer_fighter', '_fighter_target', '_update_planes',
    '_render_air', '_render_plane', '_render_tank', '_render_shell',
    '_render_wreck', '_render_mother', '_render_beam', '_shell_blast',
    '_destroy_tank', '_fire_shell', '_update_tanks', '_update_shells',
    '_spawn_mech', '_fire_mech_shell', '_destroy_mech', '_update_mechs',
    '_render_mech', '_fire_beam', '_update_beams', '_destroy_mother',
    '_update_mothers', '_spawn_zeppelin', '_zepp_drop', '_destroy_zeppelin',
    '_update_zeppelins', '_render_zeppelin', '_update_wrecks', '_update_flak',
    '_update_far_falls', '_start_tip', '_update_collapses',
    '_damage_structures', '_add_crater', '_explode', '_render_missile',
    '_render_soldier', '_render_bunker', '_render_corpse', '_render_bullet',
    '_render_buildings', '_composite_filled', '_render_craters', '_advance',
]


def _init(w, h):
    """Build the persistent battlefield: skyline, ruins, bunkers, spawners."""
    global _WB
    if _WB is not None:
        return
    rnd = random.Random(1337)
    gy = int(h * 0.74)                       # ground line in hires rows
    horizon = gy // 2                        # ground line in canvas rows
    gw = w * WORLD_SCREENS                   # full world strip
    W = gw
    gh = h // 2

    bg_grid = []
    for y in range(gh):
        row = []
        for x in range(gw):
            if y < horizon:
                col = Color(22, 16, 22).lerp(Color(88, 52, 26), y / max(1, horizon))
            else:
                t = (y - horizon) / max(1, gh - horizon)
                col = Color(52, 42, 30).lerp(Color(26, 20, 20), t)
            row.append(col)
        bg_grid.append(row)

    buildings = []
    windows_all = []

    # ---- far hazy skyline (deep layer) ------------------------------
    x = 0
    b_idx = 0
    while x < gw:
        bw = rnd.randint(5, 11)
        bh = rnd.randint(int(horizon * 0.38), max(int(horizon * 0.38) + 1,
                                                  int(horizon * 0.92)))
        landmark = rnd.random() < 0.1 and bh > int(horizon * 0.6)
        if landmark:
            bh = min(horizon - 1, int(bh * 1.15))
        cells = []
        for yy in range(horizon - bh, horizon):
            for xx in range(x, min(gw, x + bw)):
                cells.append((xx, yy, rnd.random()))
        buildings.append({'x': x, 'w': bw, 'h': bh, 'base': horizon,
                          'kind': 'far', 'damage': 0.0, 'fire': False,
                          'seed': rnd.uniform(0, 6.28), 'cells': cells,
                          'tint': rnd.uniform(0.86, 1.12),
                          'antenna': (rnd.random() < 0.35 and bh > 7) or landmark,
                          'roofbox': rnd.random() < 0.3 and bh > 5,
                          'teeth': [rnd.randint(0, 1) for _ in range(bw)],
                          'falling': None, 'fall_dur': 1.0, 'gone': False})
        b_idx += 1
        gap = rnd.randint(0, 2)
        if rnd.random() < 0.12:
            gap = rnd.randint(3, 6)
        x += bw + gap

    # ---- mid skyline (dense, some burning) --------------------------
    x = 0
    while x < gw:
        bw = rnd.randint(3, 8)
        bh = rnd.randint(3, max(3, int(horizon * 0.72)))
        if rnd.random() < 0.08:
            bh = min(horizon - 1, int(horizon * 0.92))
        fire = rnd.random() < 0.15
        cells = []
        for yy in range(horizon - bh, horizon):
            for xx in range(x, min(gw, x + bw)):
                cells.append((xx, yy, rnd.random()))
        buildings.append({'x': x, 'w': bw, 'h': bh, 'base': horizon,
                          'kind': 'skyline', 'damage': rnd.random() * 0.06,
                          'cells': cells, 'fire': fire,
                          'seed': rnd.uniform(0, 6.28),
                          'tint': rnd.uniform(0.9, 1.1),
                          'antenna': rnd.random() < 0.4 and bh > 5,
                          'roofbox': rnd.random() < 0.5 and bh > 3,
                          'teeth': [rnd.randint(0, 1) for _ in range(bw)],
                          'tip': 0.0, 'tip_v': 0.0, 'tip_dir': 0,
                          'collapsed': False, 'crushed': False})
        for wy in range(horizon - bh + 1, horizon - 1, 2):
            for wx in range(x + 1, min(gw, x + bw - 1)):
                if rnd.random() < 0.85:
                    windows_all.append([wx, wy, rnd.uniform(0, 20), b_idx,
                                        rnd.uniform(0.25, 1.0)])
        b_idx += 1
        gap = rnd.randint(0, 2)
        if rnd.random() < 0.14:
            gap = rnd.randint(3, 6)
        x += bw + gap

    win_osc = []
    for (wx, wy, seed, b_idx, lit) in windows_all:
        b = buildings[b_idx]
        if b['kind'] == 'skyline' and b['fire']:
            win_osc.append(Oscillator(2 * math.pi / 1.4, 0.0, 1.0, seed * 4 / 1.4))
        else:
            win_osc.append(Oscillator(2 * math.pi / 0.6, 0.0, 1.0, seed * 3.1 / 0.6))

    # mid-field ruined husks - fighters take cover here.
    # spread across the whole strip so each district has cover
    for frac in (0.16, 0.30, 0.44, 0.56, 0.70, 0.84):
        rx = int(gw * frac) + rnd.randint(-3, 3)
        bw = rnd.randint(5, 9)
        bh = rnd.randint(4, max(4, int(horizon * 0.6)))
        cells = []
        for yy in range(horizon - bh, horizon):
            for xx in range(rx, min(gw, rx + bw)):
                cells.append((xx, yy, rnd.random()))
        buildings.append({'x': rx, 'w': bw, 'h': bh, 'base': horizon,
                          'kind': 'ruin', 'damage': rnd.uniform(0.5, 0.8),
                          'cells': cells, 'fire': False,
                          'seed': rnd.uniform(0, 6.28),
                          'tint': rnd.uniform(0.9, 1.08),
                          'antenna': False, 'roofbox': False,
                          'teeth': [rnd.randint(0, 1) for _ in range(bw)]})
        b_idx += 1

    # sandbag bunkers at each end of the middle ground.
    # the middle ground spans [w, 2w]; blue's home is behind-left, red's behind-right.
    bunkers = []
    for fac, bx in ((0, int(w * 1.13)), (1, int(w * 1.87))):
        cells = []
        for dy in range(-2, 1):
            for dx in range(-3, 4):
                cells.append({'dx': dx, 'dy': dy, 'r': rnd.random(),
                              'slit': dy == -1 and dx == 0})
        bunkers.append({'faction': fac, 'x': bx, 'base': gy - 1,
                        'cells': cells, 'damage': 0.0})

    # elevated sniper perches: on rooftops or inside building windows
    sniper_spots = []
    for bi, b in enumerate(buildings):
        if b['kind'] == 'skyline':
            sniper_spots.append({'x': b['x'] + b['w'] // 2,
                                 'y': (b['base'] - b['h']) * 2,
                                 'kind': 'roof', 'b_idx': bi, 'sn': None})
    for (wx, wy, seed, b_idx, lit) in windows_all:
        if buildings[b_idx]['kind'] == 'skyline':
            sniper_spots.append({'x': wx, 'y': wy * 2,
                                 'kind': 'window', 'b_idx': b_idx, 'sn': None})

    _WB = {
        'rnd': rnd, 'gy': gy, 'horizon': horizon, 'gw': gw, 'gh': gh,
        'bg_grid': bg_grid, 'windows_all': windows_all, 'win_osc': win_osc,
        'buildings': buildings, 'bunkers': bunkers,
        'soldiers': [], 'bullets': [], 'corpses': [],
        'shouts': [],
        'cry_t': rnd.uniform(6, 12), 'cry_fac': 0,
        'bombs': [], 'missiles': [], 'explosions': [], 'shockwaves': [],
        'smoke': [], 'debris': [], 'craters': [],
        'planes': [], 'plane_t': 9.0, 'intercept_t': 0.0,
        'air': [], 'flak_t': 1.2, 'flak': [],
        'chutes': [], 'drop_t': rnd.uniform(22, 32),
        'drones': [], 'drone_t': rnd.uniform(12, 20), 'swarms': [],
        'hackers': [], 'hacker_t': rnd.uniform(15, 26),
        'snipers': [], 'sniper_t': rnd.uniform(10, 18),
        'sniper_spots': sniper_spots,
        'pulses': [],
        'builders': [], 'builder_t': rnd.uniform(16, 28),
        'built_bunkers': [0, 0],
        'drillers': [], 'driller_t': rnd.uniform(12, 20),
        'tanks': [], 'tank_t': 4.0, 'shells': [], 'wrecks': [],
        'mechs': [], 'mech_t': 18.0, 'zeppelins': [], 'zepp_t': 45.0,
        'mothers': [], 'mother_t': 50.0, 'beams': [],
        'ragdolls': [],
        'fall_t': 1e12,
        'front': [int(w * 1.42), int(w * 1.58)],
        'deaths': [0, 0],
        'soldier_t': 0.5, 'barrage_t': rnd.uniform(8, 15),
        'barrage_n': 0, 'barrage_gap': 0.0,
        'cam': float(w), 'cam_i': w, 'mid': float(w * 1.5),
        'cam_off': 0.0, 'cam_y': 0,
        'push': 0.0, 'drift': [0.0, 0.0], 'streak': [0, 0],
        'shake_t': 0.0, 'shake_p': 0.0, 'flash_t': 0.0,
        'adv_msg': None, 'banner': None,
    }


# ----------------------------------------------------------------------
# ordnance spawners
# ----------------------------------------------------------------------

def _spawn_missile(s, w, h):
    rnd = s['rnd']
    gy = s['gy']
    mid = (s['front'][0] + s['front'][1]) / 2.0
    if rnd.random() < 0.6:
        sx = rnd.uniform(mid - w * 0.55, mid + w * 0.55)
        sy = rnd.uniform(-h * 0.25, -4)
        tx = rnd.uniform(mid - w * 0.35, mid + w * 0.35)
        tt = rnd.uniform(1.0, 1.8)
        hue = rnd.uniform(0.02, 0.12)
        sat = 0.85
    else:
        side = rnd.choice([-1, 1])
        sx = mid + side * (w * 0.5 + 8)
        sy = gy - rnd.uniform(h * 0.15, h * 0.4)
        tx = mid + rnd.uniform(-w * 0.3, w * 0.3)
        tt = rnd.uniform(1.6, 2.6)
        hue = 0.0
        sat = 0.15
    ty = gy + rnd.uniform(-h * 0.05, 0)
    g = rnd.uniform(10, 18)
    s['missiles'].append({
        'x': sx, 'y': sy,
        'vx': (tx - sx) / tt,
        'vy': (ty - sy) / tt - 0.5 * g * tt,
        'g': g, 'tt': tt, 'age': 0.0, 'trail': [],
        'hue': hue, 'sat': sat,
    })
    _sfx('whistle', sx, 0.5)


# Role presets for the expanded ground roster.  Each role distils into a
# handful of tuning knobs the AI + renderer share, so adding a unit is just a
# new preset with a distinct silhouette + behaviour profile.
ROLE_STATS = {
    'attacker': {'hp': (1, 2), 'spd': 9.0, 'fire': (0.45, 1.15), 'pref': 9.0,
                 'per': 30, 'dmg': 1, 'gun': 1, 'kind': 'ball'},
    'defender': {'hp': (1, 2), 'spd': 6.5, 'fire': (0.55, 1.3), 'pref': 10.0,
                 'per': 30, 'dmg': 1, 'gun': 1, 'kind': 'ball'},
    # heavy support rifle - long bursts, but slow to walk
    'gunner': {'hp': (3, 4), 'spd': 5.0, 'fire': (0.16, 0.34), 'pref': 16.0,
               'per': 40, 'dmg': 1, 'gun': 3, 'kind': 'ball', 'heavy': True},
    # robotic laser shooter - fast accurate bolt, glass-cannon frame
    'laser': {'hp': (1, 2), 'spd': 6.0, 'fire': (0.5, 1.0), 'pref': 18.0,
              'per': 44, 'dmg': 2, 'gun': 1, 'kind': 'laser', 'robot': True},
    # parkour runner - lightning advance, hops, short-ranged jabs
    'parkour': {'hp': (1, 2), 'spd': 16.0, 'fire': (0.5, 1.1), 'pref': 5.0,
                'per': 34, 'dmg': 1, 'gun': 1, 'kind': 'ball', 'jump': True},
    # flamegunner - short-ranged cone of fire
    'flame': {'hp': (3, 4), 'spd': 6.0, 'fire': (0.12, 0.24), 'pref': 4.0,
              'per': 22, 'dmg': 1, 'gun': 1, 'kind': 'flame', 'heavy': True},
    # special-ops cyborg - fast, smart, regenerating, high-tech weapon
    'cyborg': {'hp': (5, 6), 'spd': 11.0, 'fire': (0.28, 0.5), 'pref': 13.0,
               'per': 46, 'dmg': 2, 'gun': 2, 'kind': 'laser', 'smart': True},
    # generic light droid - cheap frontline robot swarm
    'droid': {'hp': (1, 2), 'spd': 8.0, 'fire': (0.4, 1.0), 'pref': 9.0,
              'per': 30, 'dmg': 1, 'gun': 1, 'kind': 'ball', 'robot': True},
}

# which roles a faction mixes while it stays under the soldier cap
ROLE_POOL = ('attacker', 'attacker', 'defender', 'defender',
             'gunner', 'gunner', 'laser', 'parkour', 'flame', 'droid',
             'droid', 'cyborg')
# cap on smart cyborgs/robots alive per faction - rare and precious
SMART_CAP = 3


def _make_soldier(s, faction, x, role='attacker'):
    rnd = s['rnd']
    fac = 1 if faction == 0 else -1
    st = ROLE_STATS.get(role, ROLE_STATS['attacker'])
    heavy = st.get('heavy')
    return {
        'faction': faction, 'role': role,
        'heavy': bool(heavy), 'robot': st.get('robot', False),
        'smart': st.get('smart', False), 'jump': st.get('jump', False),
        'x': float(x), 'y': float(s['gy'] - 1),
        'vx': 0.0, 'facing': fac,
        'state': 'advance', 'target_x': float(x),
        'hp': rnd.randint(*st['hp']),
        'maxhp': st['hp'][1],
        'weapon': st['kind'],
        'cooldown': rnd.uniform(0.2, 1.0),
        'burst': 0, 'fire_hold': rnd.uniform(0.0, 0.4),
        'flash': 0.0, 'step': rnd.uniform(0, 6.28),
        'knock': 0.0, 'crouch': False,
        'dead': False, 'dead_t': 0.0,
        'think_t': rnd.uniform(0.1, 0.4),
        'target': None,
        'strafe_t': 0.0, 'strafe_dir': 0,
        'hop_t': 0.0, 'hop_vy': 0.0, 'hop_y': 0.0, 'squash': 0.0,
        'parachuted': False,
    }


def _spawn_soldier(s, faction, role=None):
    rnd = s['rnd']
    fac = 1 if faction == 0 else -1
    bu = s['bunkers'][faction]
    if role is None:
        # pick a role from the weighted pool, but thin the smart/robot roster
        # so high-tech units stay rare and special
        role = rnd.choice(ROLE_POOL)
        if role in ('cyborg', 'laser', 'droid'):
            smart_alive = sum(
                1 for o in s['soldiers']
                if not o['dead'] and o['faction'] == faction
                and (o['role'] in ('cyborg', 'laser', 'droid')))
            if smart_alive >= SMART_CAP:
                role = 'attacker'
    if role == 'defender':
        covers = sorted((b for b in s['buildings'] if b['kind'] == 'ruin'),
                        key=lambda b: abs(b['x'] - bu['x']))
        if covers:
            tgt = covers[0]
            target_x = tgt['x'] + fac * rnd.uniform(-2, 4)
        else:
            target_x = bu['x'] + fac * 2
    else:
        target_x = s['front'][faction] + fac * rnd.uniform(-3, 3)
    sol = _make_soldier(s, faction, bu['x'], role)
    sol['target_x'] = float(target_x)
    s['soldiers'].append(sol)
    return sol


# ----------------------------------------------------------------------
# combat
# ----------------------------------------------------------------------

def _fire(s, sol, enemy):
    rnd = s['rnd']
    st = ROLE_STATS.get(sol['role'], ROLE_STATS['attacker'])
    weapon = sol['weapon']
    mx = sol['x'] + sol['facing'] * 2.5
    my = sol['y'] - 2 - (sol.get('hop_y', 0.0))
    dist = max(1.0, abs(enemy['x'] - sol['x']))
    lead = enemy.get('vx', 0.0) * (0.25 + dist / 160.0)
    spread = rnd.uniform(-0.09, 0.09)
    if sol['crouch']:
        spread *= 0.55
    elif sol['state'] == 'retreat':
        spread *= 1.4
    if sol['smart']:
        # cyborgs sight the aim - almost no wobble under their coordinated fire
        spread *= 0.35

    def _make_ang(extra=0.0):
        return (math.atan2(enemy['y'] - 3 - my,
                           enemy['x'] + lead - mx) + spread + extra)

    if weapon == 'flame':
        # a short-lived cone of fire hosed toward the enemy
        shots = 4
        for i in range(shots):
            ex = rnd.uniform(-0.42, 0.42)
            ang = _make_ang(ex)
            sp = rnd.uniform(34, 46)
            s['bullets'].append({
                'x': mx, 'y': my, 'px': mx, 'py': my,
                'vx': math.cos(ang) * sp, 'vy': math.sin(ang) * sp,
                'faction': sol['faction'], 'life': rnd.uniform(0.28, 0.4),
                'dmg': st['dmg'], 'weapon': 'flame',
            })
        sol['flash'] = 0.10
        _sfx('flame', mx, 0.9)
        return

    if weapon == 'laser':
        # a fast straight bolt (step length > collision radius of a bullet)
        ang = _make_ang()
        sp = 120.0
        s['bullets'].append({
            'x': mx, 'y': my, 'px': mx, 'py': my,
            'vx': math.cos(ang) * sp, 'vy': math.sin(ang) * sp,
            'faction': sol['faction'], 'life': 1.1,
            'dmg': st['dmg'], 'weapon': 'laser',
        })
        sol['flash'] = 0.08
        _sfx('zap', mx, 0.7)
        return

    # conventional ball, but machine gunners lay down a spread volley
    n = st.get('gun', 1)
    for i in range(n):
        ex = rnd.uniform(-0.06, 0.06) * (1 + (n - 1) * 0.5)
        ang = _make_ang(ex)
        sp = rnd.uniform(40, 55)
        s['bullets'].append({
            'x': mx, 'y': my, 'px': mx, 'py': my,
            'vx': math.cos(ang) * sp, 'vy': math.sin(ang) * sp,
            'faction': sol['faction'], 'life': 1.4,
            'dmg': st['dmg'], 'weapon': 'ball',
        })
    sol['flash'] = 0.07
    _sfx('shot', mx, 1.0 if n == 1 else 0.9)


def _kill(s, sol, vx, vy, killer=None, spin=None):
    rnd = s['rnd']
    sol['dead'] = True
    s['deaths'][sol['faction']] += 1
    if killer is not None:
        s['streak'][killer] += 1
    s['corpses'].append({'x': sol['x'], 'y': sol['y'] - 2,
                         'vx': vx, 'vy': vy,
                         'rot': rnd.uniform(0, 6.28),
                         'spin': spin if spin is not None else rnd.uniform(-9, 9),
                         'faction': sol['faction'], 'age': 0.0,
                         'life': rnd.uniform(3, 5), 'bounces': 0,
                         'state': 'fly'})


def _impact(s, x, y, faction):
    rnd = s['rnd']
    for _ in range(4):
        a = rnd.uniform(0, 6.28)
        sp = rnd.uniform(1, 9)
        s['debris'].append({'x': x, 'y': y,
                            'vx': math.cos(a) * sp, 'vy': math.sin(a) * sp - 2,
                            'age': 0.0, 'life': rnd.uniform(0.15, 0.5),
                            'hue': 0.6 if faction == 0 else 0.05,
                            'hot': rnd.random() < 0.6})


def _think(s, sol):
    rnd = s['rnd']
    fac = sol['faction']
    st = ROLE_STATS.get(sol['role'], ROLE_STATS['attacker'])
    per = st['per']
    fog = 30 if not sol['smart'] else 40
    best = None
    bd = 1e9
    nf = 0
    ne = 0
    # cyborgs share a wider tactical picture: they sense farther and notice
    # allies/danger in a broader band, so they commit or break more decisively
    fov = 24 if not sol['smart'] else 32
    for o in s['soldiers']:
        if o['dead']:
            continue
        d = abs(o['x'] - sol['x'])
        if o['faction'] == fac:
            if d < fov:
                nf += 1
            continue
        if d < fog:
            ne += 1
        if d < bd:
            bd = d
            best = o
    cur = sol['target']
    if (cur is not None and not cur['dead']
            and abs(cur['x'] - sol['x']) < per
            and (best is None or abs(cur['x'] - sol['x']) <= bd * 1.6)):
        best = cur
    sol['target'] = best

    if best is not None and bd < per:
        hurt = sol['hp'] <= max(1, sol['maxhp'] * 0.32)
        overmatched = nf < ne
        if sol['smart']:
            # a cyborg only disengages when clearly beaten, then regroups
            if hurt and overmatched and nf == 0:
                sol['state'] = 'retreat'
            else:
                sol['state'] = 'fight'
        elif hurt and nf < ne:
            sol['state'] = 'retreat'
        else:
            sol['state'] = 'fight'
        return
    if sol['state'] == 'fight' and sol['role'] in ('attacker', 'parkour'):
        sol['target_x'] += sol['facing'] * 6
    elif sol['state'] == 'retreat':
        sol['target_x'] = s['front'][fac] + (1 if fac == 0 else -1) * rnd.uniform(-3, 3)
    elif sol['role'] == 'attacker' and abs(sol['x'] - sol['target_x']) < 2.0:
        sol['target_x'] += sol['facing'] * 8
    sol['state'] = 'advance'
    sol['crouch'] = False


def _update_soldiers(s, dt):
    rnd = s['rnd']
    w = s['gw']
    gy = s['gy']
    keep = []
    for sol in s['soldiers']:
        if sol['dead']:
            sol['dead_t'] += dt
            if sol['dead_t'] > 6.0:
                continue
            keep.append(sol)
            continue
        sol['step'] += dt * 9
        sol['flash'] = max(0.0, sol['flash'] - dt)
        sol['think_t'] -= dt
        if sol['think_t'] <= 0:
            sol['think_t'] = rnd.uniform(0.16, 0.4)
            _think(s, sol)

        # cyborgs slowly regenerate outside the thick of it - the payoff for
        # being the most valuable unit on the field
        if sol['smart'] and not sol['dead'] and sol['hp'] < sol['maxhp']:
            tgt = sol['target']
            if tgt is None or abs(tgt['x'] - sol['x']) > 18:
                sol['hp'] = min(sol['maxhp'], sol['hp'] + 2.0 * dt)

        if sol['knock']:
            sol['knock'] *= max(0.0, 1 - 3.5 * dt)
            if abs(sol['knock']) < 0.05:
                sol['knock'] = 0.0

        role = sol['role']
        st = ROLE_STATS.get(role, ROLE_STATS['attacker'])
        cap = st['spd']
        if sol['state'] == 'retreat':
            cap = max(cap, 11.0)

        tgt = sol['target']
        if tgt is not None and (tgt['dead'] or abs(tgt['x'] - sol['x']) > st['per'] * 1.4):
            sol['target'] = None
            tgt = None

        if tgt is not None:
            sol['facing'] = 1 if tgt['x'] > sol['x'] else -1
            if sol['state'] == 'retreat':
                bu = s['bunkers'][sol['faction']]
                ddx = (bu['x'] + (2 if sol['faction'] == 0 else -2)) - sol['x']
                d = 1 if ddx > 0 else -1
                sol['facing'] = d
                sol['vx'] += d * 11.0 * 4 * dt
            else:
                sol['cooldown'] -= dt
                if sol['cooldown'] <= 0:
                    bwidth = (rnd.uniform(*st['fire'])
                              * (1.35 if sol['crouch'] else 1.0))
                    if sol['smart']:
                        # cyborgs fire in disciplined 2-3 round bursts
                        sol['burst'] += 1
                        bwidth = 0.12 if sol['burst'] % 3 else 0.5
                    _fire(s, sol, tgt)
                    sol['cooldown'] = bwidth
                sol['crouch'] = (role in ('defender', 'gunner')
                                 or sol['hp'] <= max(1, sol['maxhp'] * 0.3))
                if sol['jump']:
                    # parkour runner bolts at the enemy and hops each stride
                    sol['vx'] += sol['facing'] * 8.0 * 2.5 * dt
                    if rnd.random() < dt * 2.4:
                        sol['hop_t'] = 0.34
                else:
                    sol['strafe_t'] -= dt
                    if sol['strafe_t'] <= 0:
                        nxt = [-1, -1, 0, 0, 1, 1]
                        if sol['smart']:
                            # cyborgs circle wide to open a flanking angle
                            nxt = [-1, -1, -1, 1, 1, 1, 2, -2]
                        sol['strafe_t'] = rnd.uniform(0.4, 1.1)
                        sol['strafe_dir'] = rnd.choice(nxt)
                    if sol['strafe_dir']:
                        sol['vx'] += sol['strafe_dir'] * 3.0 * 2.5 * dt
                    else:
                        sol['vx'] *= max(0.0, 1 - 5 * dt)
        else:
            sol['crouch'] = False
            tx = sol['target_x']
            if sol['state'] == 'retreat':
                bu = s['bunkers'][sol['faction']]
                tx = bu['x'] + (2 if sol['faction'] == 0 else -2)
                cap = max(cap, 11.0)
            ddx = tx - sol['x']
            sol['facing'] = 1 if ddx > 0 else -1
            if abs(ddx) < 1.5:
                sol['vx'] *= max(0.0, 1 - 6 * dt)
            elif sol['jump']:
                # parkour runners lunge in long aggressive bounds
                sp = st['spd'] * 1.35
                sol['vx'] += sol['facing'] * sp * 3.0 * dt
                if rnd.random() < dt * 3.0:
                    sol['hop_t'] = 0.3
            else:
                sp = rnd.uniform(0.0, 0.5) + st['spd']
                if sol['state'] == 'retreat':
                    sp = 11.0
                sol['vx'] += sol['facing'] * sp * 3.0 * dt

        # parkour hop arc (a simple ballistic bob that lands back on the ground)
        if sol['jump'] and sol['hop_t'] > 0:
            sol['hop_t'] -= dt
            sol['hop_vy'] -= 60 * dt
            sol['hop_y'] += sol['hop_vy'] * dt
            if sol['hop_y'] < 0:
                sol['hop_y'] = 0.0
                sol['hop_t'] = 0.0

        sol['vx'] = max(-cap, min(cap, sol['vx']))
        sol['x'] += (sol['vx'] + sol['knock']) * dt
        sol['y'] = gy - 1 - sol['hop_y']
        sol['x'] = max(1.0, min(w - 1.0, sol['x']))
        keep.append(sol)
    s['soldiers'] = keep


def _update_bullets(s, dt):
    rnd = s['rnd']
    gy = s['gy']
    W = s['gw']
    keep = []
    for b in s['bullets']:
        b['px'], b['py'] = b['x'], b['y']
        b['x'] += b['vx'] * dt
        b['y'] += b['vy'] * dt
        wtype = b.get('weapon', 'ball')
        if wtype == 'laser':
            # coherent bolt: near-light, almost no drop
            b['vy'] += 0.6 * dt
        elif wtype == 'flame':
            # gout of fire that clings low and spreads a little ember trail
            b['vy'] += 6 * dt
            b['vx'] *= max(0.0, 1 - 2.5 * dt)
            if rnd.random() < dt * 26:
                s['smoke'].append({'x': b['x'], 'y': b['y'] - 1,
                                   'vx': rnd.uniform(-0.4, 0.4),
                                   'vy': -rnd.uniform(0.5, 1.6),
                                   'age': 0.0, 'life': rnd.uniform(0.2, 0.5)})
        else:
            b['vy'] += 4 * dt
        b['life'] -= dt
        hit = False
        for sol in s['soldiers']:
            if sol['dead'] or sol['faction'] == b['faction']:
                continue
            if abs(sol['x'] - b['x']) < 1.5 and b['y'] > sol['y'] - 4.5 and b['y'] <= sol['y']:
                sol['hp'] -= b.get('dmg', 1)
                sol['flash'] = 0.14
                _impact(s, b['x'], b['y'], b['faction'])
                if sol['hp'] <= 0:
                    _kill(s, sol, b['vx'] * 0.08, -2.5, killer=b['faction'])
                hit = True
                break
        if not hit:
            for ch in s['chutes']:
                if ch['dead'] or ch['faction'] == b['faction']:
                    continue
                if abs(ch['x'] - b['x']) < 1.2 and b['y'] > ch['y'] - 4 and b['y'] <= ch['y'] + 2:
                    ch['dead'] = True
                    _impact(s, b['x'], b['y'], b['faction'])
                    s['smoke'].append({'x': ch['x'], 'y': ch['y'],
                                       'vx': rnd.uniform(-0.5, 0.5),
                                       'vy': rnd.uniform(0.2, 1.2),
                                       'age': 0.0, 'life': rnd.uniform(0.4, 0.8)})
                    hit = True
                    break
        if not hit:
            for sn in s['snipers']:
                if sn['dead'] or sn['faction'] == b['faction']:
                    continue
                if abs(sn['x'] - b['x']) < 1.6 and abs(sn['y'] - b['y']) < 3.5:
                    sn['hp'] -= b.get('dmg', 1)
                    sn['flash'] = 0.15
                    _impact(s, b['x'], b['y'], b['faction'])
                    if sn['hp'] <= 0:
                        _destroy_sniper(s, sn)
                    hit = True
                    break
        if not hit and b.get('sniper'):
            for dr in s['drones']:
                if dr['dead']:
                    continue
                if abs(dr['x'] - b['x']) < 1.6 and abs(dr['y'] - b['y']) < 2.8:
                    dr['hp'] -= b.get('dmg', 1)
                    dr['flash'] = 0.15
                    _impact(s, b['x'], b['y'], b['faction'])
                    if dr['hp'] <= 0:
                        _destroy_drone(s, dr)
                    hit = True
                    break
        if not hit:
            for bd in s['builders']:
                if bd['dead']:
                    continue
                if abs(bd['x'] - b['x']) < 2.0 and b['y'] > bd['y'] - 5 and b['y'] <= bd['y']:
                    bd['hp'] -= b.get('dmg', 1)
                    bd['flash'] = 0.14
                    _impact(s, b['x'], b['y'], b['faction'])
                    if bd['hp'] <= 0:
                        _destroy_builder(s, bd)
                    hit = True
                    break
        if hit:
            continue
        if b['x'] < 0 or b['x'] >= W or b['y'] >= gy - 1 or b['life'] <= 0:
            if b['y'] >= gy - 1:
                s['smoke'].append({'x': b['x'], 'y': gy - 2,
                                   'vx': rnd.uniform(-0.3, 0.3),
                                   'vy': -rnd.uniform(0.5, 1.5),
                                   'age': 0.0, 'life': rnd.uniform(0.2, 0.5)})
            _impact(s, b['x'], min(b['y'], gy - 1), b['faction'])
            continue
        keep.append(b)
    s['bullets'] = keep


def _update_corpses(s, dt):
    gy = s['gy']
    keep = []
    for cp in s['corpses']:
        cp['age'] += dt
        cp['rot'] += cp['spin'] * dt
        cp['spin'] *= max(0.0, 1 - 0.55 * dt)
        if cp['state'] in ('fly', 'slide'):
            cp['vy'] += 46 * dt
            cp['x'] += cp['vx'] * dt
            cp['y'] += cp['vy'] * dt
            if cp['y'] >= gy - 1:
                cp['y'] = gy - 1
                if cp['state'] == 'fly' and cp['bounces'] < 1 and cp['vy'] > 14:
                    cp['vy'] = -cp['vy'] * 0.42
                    cp['vx'] *= 0.6
                    cp['spin'] *= 0.7
                    cp['bounces'] += 1
                else:
                    cp['vy'] = 0.0
                    if abs(cp['vx']) > 1.6:
                        cp['state'] = 'slide'
                        cp['vx'] *= max(0.0, 1 - 4 * dt)
                    else:
                        cp['vx'] = 0.0
                        cp['state'] = 'ground'
        if cp['age'] >= cp['life']:
            continue
        keep.append(cp)
    s['corpses'] = keep
    if len(s['corpses']) > 40:
        s['corpses'] = s['corpses'][-40:]


def _blast_soldiers(s, x, y, radius):
    rnd = s['rnd']
    for sol in s['soldiers']:
        if sol['dead']:
            continue
        d = math.hypot(sol['x'] - x, (sol['y'] - 2 - y) * 2.0)
        if d < radius * 0.9:
            kx = (sol['x'] - x) / max(1.0, d) * rnd.uniform(10, 22)
            ky = -rnd.uniform(8, 18)
            _kill(s, sol, kx, ky, spin=rnd.uniform(-15, 15))
        elif d < radius * 1.3:
            k = min(5.0, (radius * 1.3 - d) * 0.7)
            sol['knock'] += k * (1 if sol['x'] > x else -1)
            sol['flash'] = max(sol['flash'], 0.05)


def _spawn_gunship(s, w, h):
    rnd = s['rnd']
    side = rnd.choice([-1, 1])
    mid = (s['front'][0] + s['front'][1]) / 2.0
    s['planes'].append({
        'kind': 'gunship',
        'x': mid + side * (w * 0.55),
        'y': h * 0.20 + rnd.uniform(-h * 0.04, h * 0.04),
        'vx': -side * rnd.uniform(22, 28), 'vy': 0.0,
        'base_y': h * 0.20 + rnd.uniform(-h * 0.04, h * 0.04),
        'hp': 6, 'gun_t': 0.0, 'aat_t': 0.0,
        'faction': rnd.choice([0, 1]),
        'flash': 0.0, 'phase': rnd.uniform(0, 6.28), 'age': 0.0,
        'trail': [], 'crash': False, 'retire': False,
    })


def _spawn_transport(s, w, h):
    rnd = s['rnd']
    side = rnd.choice([-1, 1])
    mid = (s['front'][0] + s['front'][1]) / 2.0
    s['planes'].append({
        'kind': 'transport',
        'x': mid + side * (w * 0.52),
        'y': h * 0.05 + rnd.uniform(-h * 0.02, h * 0.02),
        'vx': -side * rnd.uniform(20, 25), 'vy': 0.0,
        'base_y': h * 0.05 + rnd.uniform(-h * 0.02, h * 0.02),
        'hp': 4, 'drop_t': 0.6, 'to_drop': rnd.randint(3, 4),
        'faction': 0 if side == -1 else 1,
        'flash': 0.0, 'phase': rnd.uniform(0, 6.28), 'age': 0.0,
        'trail': [], 'crash': False, 'retire': False,
    })


def _spawn_chute(s, p):
    rnd = s['rnd']
    s['chutes'].append({
        'faction': p['faction'],
        'x': p['x'], 'y': p['y'] + 2,
        'vx': rnd.uniform(-1.2, 1.2), 'vy': rnd.uniform(4, 6),
        'sway': rnd.uniform(0, 6.28),
        'dead': False,
    })
    for _ in range(2):
        s['smoke'].append({'x': p['x'] + rnd.uniform(-1, 1), 'y': p['y'] + 1,
                           'vx': rnd.uniform(-0.6, 0.6),
                           'vy': rnd.uniform(0.2, 1.0),
                           'age': 0.0, 'life': rnd.uniform(0.4, 0.8)})


def _update_chutes(s, dt, w, h):
    rnd = s['rnd']
    gy = s['gy']
    keep = []
    for ch in s['chutes']:
        if ch['dead']:
            continue
        ch['sway'] += dt * 2.4
        ch['vy'] += 0.6 * dt
        ch['vx'] += math.sin(ch['sway']) * 2.8 * dt
        ch['vx'] *= max(0.0, 1 - 0.6 * dt)
        ch['x'] += ch['vx'] * dt
        ch['y'] += ch['vy'] * dt
        if ch['y'] >= gy - 1:
            _land_chute(s, ch)
            continue
        if ch['x'] < -w or ch['x'] > s['gw'] + w or ch['y'] > h + 20:
            continue
        keep.append(ch)
    s['chutes'] = keep


def _land_chute(s, ch):
    rnd = s['rnd']
    fac = ch['faction']
    x = max(1.0, min(s['gw'] - 1.0, ch['x']))
    sol = _make_soldier(s, fac, x, 'attacker')
    sol['target_x'] = s['front'][fac] + (1 if fac == 0 else -1) * rnd.uniform(-3, 3)
    sol['parachuted'] = True
    s['soldiers'].append(sol)
    for _ in range(3):
        s['smoke'].append({'x': x + rnd.uniform(-1.5, 1.5), 'y': s['gy'] - 3,
                           'vx': rnd.uniform(-1.0, 1.0),
                           'vy': -rnd.uniform(0.6, 1.8),
                           'age': 0.0, 'life': rnd.uniform(0.4, 0.9)})


# ----------------------------------------------------------------------
# drones, hackers, builders
# ----------------------------------------------------------------------

def _spawn_drone(s, w, h):
    """A low-flying strike drone that hovers over the front and strafes."""
    rnd = s['rnd']
    fac = rnd.randint(0, 1)
    dir_ = 1 if fac == 0 else -1
    front = s['front'][fac]
    d = {
        'faction': fac, 'state': 'roam',
        'x': front - dir_ * rnd.uniform(w * 0.22, w * 0.38),
        'y': float(s['gy'] - rnd.randint(4, 7)),
        'vx': dir_ * rnd.uniform(3.5, 5.5),
        'target_x': front - dir_ * rnd.uniform(-2, 6),
        'hp': 2, 'flash': 0.0, 'age': 0.0, 'life': rnd.uniform(18, 26),
        'fire_t': rnd.uniform(0.5, 1.5),
        'phase': rnd.uniform(0, 6.28), 'bob': rnd.uniform(0, 6.28),
        'hack': None, 'dead': False,
    }
    s['drones'].append(d)
    return d


def _spawn_swarm(s, w, h):
    """A fast formation of tiny strike drones that harass the front together.

    Each drone is either a `strike` drone - a kamikaze that dives onto an
    enemy soldier and detonates in a tiny blast - or a `gun` drone that
    strafes the ground with quick shots. Only hackers or enemy snipers can
    bring them down; regular rifle fire passes straight through them.
    """
    rnd = s['rnd']
    fac = rnd.randint(0, 1)
    dir_ = 1 if fac == 0 else -1
    front = s['front'][fac]
    sid = len(s['swarms'])
    sx = front - dir_ * rnd.uniform(w * 0.18, w * 0.30)
    sy = float(s['gy'] - rnd.randint(6, 9))
    s['swarms'].append({'id': sid, 'fac': fac, 'x': sx, 'y': sy,
                        'vx': dir_ * rnd.uniform(5.0, 8.0),
                        'ph': rnd.uniform(0, 6.28)})
    n = rnd.randint(6, 9)
    for i in range(n):
        a = rnd.uniform(0, 6.283)
        rr = rnd.uniform(4.0, 14.0)
        ox = math.cos(a) * rr
        oy = math.sin(a) * rr * 0.6
        s['drones'].append({
            'faction': fac, 'state': 'roam', 'tiny': True, 'swarm_id': sid,
            'role': 'strike' if rnd.random() < 0.55 else 'gun',
            'off': (ox, oy),
            'x': sx + ox, 'y': sy + oy, 'vx': 0.0,
            'hp': 1, 'flash': 0.0, 'age': -rnd.uniform(0, 2),
            'life': rnd.uniform(12, 18),
            'fire_t': rnd.uniform(0.4, 1.4),
            'phase': rnd.uniform(0, 6.28), 'bob': rnd.uniform(0, 6.28),
            'hack': None, 'dead': False,
        })
    _sfx('swarm', sx, 0.5)
    return s['swarms'][sid]


def _drone_strike(s, dr, sol):
    """A strike drone rams an enemy soldier and detonates in a tiny blast."""
    rnd = s['rnd']
    dr['dead'] = True
    sx, sy = sol['x'], sol['y']
    s['explosions'].append({'x': sx, 'y': sy - 2, 'age': 0.0,
                            'life': 0.3, 'radius_max': 3.2})
    s['shockwaves'].append({'x': sx, 'y': sy, 'age': 0.0,
                            'life': 0.4, 'radius_max': 3.0})
    for _ in range(6):
        a = rnd.uniform(0, 6.283)
        sp = rnd.uniform(1, 9)
        s['debris'].append({'x': sx, 'y': sy - 2,
                            'vx': math.cos(a) * sp, 'vy': math.sin(a) * sp - 4,
                            'age': 0.0, 'life': rnd.uniform(0.3, 0.8),
                            'hue': 0.08, 'hot': True})
    _sfx('boom', sx, 0.6, 0.7)
    if not sol['dead']:
        _kill(s, sol, rnd.uniform(-2, 2), -3.5,
              killer=dr['faction'], spin=rnd.uniform(-12, 12))
    for o in s['soldiers']:
        if o['dead'] or o is sol or o['faction'] == dr['faction']:
            continue
        if abs(o['x'] - sx) < 2.2 and o['y'] == sy:
            o['hp'] -= 2
            o['flash'] = 0.16
            if o['hp'] <= 0:
                _kill(s, o, rnd.uniform(-2, 2), -3.5,
                      killer=dr['faction'], spin=rnd.uniform(-12, 12))


def _destroy_drone(s, dr):
    rnd = s['rnd']
    dr['dead'] = True
    tiny = dr.get('tiny')
    if tiny:
        s['explosions'].append({'x': dr['x'], 'y': dr['y'], 'age': 0.0,
                                'life': 0.3, 'radius_max': 3.0})
        for _ in range(3):
            a = rnd.uniform(0, 6.283)
            sp = rnd.uniform(2, 7)
            s['debris'].append({'x': dr['x'], 'y': dr['y'],
                                'vx': math.cos(a) * sp, 'vy': math.sin(a) * sp - 2,
                                'age': 0.0, 'life': rnd.uniform(0.3, 0.7),
                                'hue': 0.1, 'hot': True})
        _sfx('boom', dr['x'], 0.5, 0.7)
        return
    s['explosions'].append({'x': dr['x'], 'y': dr['y'], 'age': 0.0,
                            'life': 0.5, 'radius_max': 5.0})
    for _ in range(5):
        a = rnd.uniform(0, 6.283)
        sp = rnd.uniform(2, 9)
        s['debris'].append({'x': dr['x'], 'y': dr['y'],
                            'vx': math.cos(a) * sp, 'vy': math.sin(a) * sp - 3,
                            'age': 0.0, 'life': rnd.uniform(0.4, 1.0),
                            'hue': 0.1, 'hot': True})
    for _ in range(2):
        s['smoke'].append({'x': dr['x'] + rnd.uniform(-1, 1), 'y': dr['y'],
                           'vx': rnd.uniform(-0.6, 0.6),
                           'vy': -rnd.uniform(0.8, 2.2),
                           'age': 0.0, 'life': rnd.uniform(0.6, 1.2)})


def _update_drones(s, dt, w, h):
    rnd = s['rnd']
    gy = s['gy']
    # drift each swarm centre fast toward its own front line, then push on
    # into no-man's-land so the swarm actually harasses the enemy
    for sw in s['swarms']:
        dir_ = 1 if sw['fac'] == 0 else -1
        tgt = s['front'][sw['fac']] + dir_ * rnd.uniform(w * 0.02, w * 0.10)
        sw['x'] += (tgt - sw['x']) * min(1.0, dt * 1.1)
        sw['ph'] += dt * 1.6
        sw['y'] = float(gy - 7.5 - 1.6 * math.sin(sw['ph']))
    keep = []
    for dr in s['drones']:
        if dr['dead']:
            continue
        dr['age'] += dt
        dr['flash'] = max(0.0, dr['flash'] - dt)
        dr['phase'] += dt * 9
        bob = math.sin(dr['phase'] * 0.5 + dr['bob'])
        tiny = dr.get('tiny')

        if dr['hack']:
            # hijacked by an enemy hacker - dive on its own faction and blow up
            tg = dr.get('dive_tgt')
            if tg is None or tg['dead'] or abs(tg['x'] - dr['x']) > 220:
                best = None
                bd = 1e9
                for sol in s['soldiers']:
                    if sol['dead'] or sol['faction'] == dr['faction']:
                        continue
                    d = abs(sol['x'] - dr['x'])
                    if d < bd:
                        bd = d
                        best = sol
                dr['dive_tgt'] = best
                tg = best
            dr['hack_t'] = dr.get('hack_t', 0) + dt
            if tg is not None:
                dr['state'] = 'dive'
                fac = 1 if tg['x'] > dr['x'] else -1
                dr['vx'] += fac * (24 if tiny else 34) * dt
                dr['vx'] = max(-14, min(14, dr['vx']))
                dr['y'] += (gy - 1 - dr['y']) * min(1.0, dt * 1.6)
                if abs(tg['x'] - dr['x']) < 3.0 or dr['hack_t'] > 7.0:
                    _explode(s, tg['x'], gy - 1, 1.0 if tiny else 2.0, True)
                    continue
            elif dr['hack_t'] > 1.2:
                _explode(s, dr['x'], gy - 1, 0.9 if tiny else 1.6, True)
                continue
        else:
            if dr['state'] == 'leave':
                dr['y'] -= 9 * dt
                dr['x'] += dr['vx'] * dt
                if dr['y'] < 1:
                    continue
            elif tiny:
                # find the nearest enemy soldier to commit against
                enemy = None
                ed = 1e9
                for sol in s['soldiers']:
                    if sol['dead'] or sol['faction'] == dr['faction']:
                        continue
                    d = abs(sol['x'] - dr['x'])
                    if d < ed:
                        ed = d
                        enemy = sol
                role = dr.get('role', 'gun')
                if role == 'strike' and enemy is not None and ed < 20:
                    # kamikaze: dive fast onto the soldier and detonate
                    dr['state'] = 'dive'
                    fac = 1 if enemy['x'] > dr['x'] else -1
                    dr['vx'] += fac * 46 * dt
                    dr['vx'] = max(-26, min(26, dr['vx']))
                    dr['x'] += dr['vx'] * dt
                    dr['y'] += (enemy['y'] - 1 - dr['y']) * min(1.0, dt * 2.6)
                    if (abs(enemy['x'] - dr['x']) < 1.6
                            and dr['y'] > enemy['y'] - 5):
                        _drone_strike(s, dr, enemy)
                        continue
                else:
                    # stay in formation around the swarm centre
                    sw = (s['swarms'][dr['swarm_id']]
                          if 0 <= dr['swarm_id'] < len(s['swarms']) else None)
                    if sw is None:
                        dr['state'] = 'leave'
                        dr['x'] += dr['vx'] * dt
                    else:
                        ox, oy = dr['off']
                        tx = sw['x'] + ox
                        ty = sw['y'] + oy + 0.8 * math.sin(dr['phase'])
                        dr['vx'] += (max(-6.0, min(6.0, tx - dr['x']))) * 4.5 * dt
                        dr['vx'] = max(-9.0, min(9.0, dr['vx']))
                        dr['x'] += dr['vx'] * dt
                        dr['y'] += (ty - dr['y']) * min(1.0, dt * 2.6)
                        if role == 'gun':
                            dr['fire_t'] -= dt
                            if dr['fire_t'] <= 0 and enemy is not None and ed < 20:
                                ang = math.atan2((enemy['y'] - 2) - dr['y'],
                                                 enemy['x'] - dr['x'])
                                sp = rnd.uniform(42, 52)
                                s['bullets'].append({
                                    'x': dr['x'], 'y': dr['y'],
                                    'px': dr['x'], 'py': dr['y'],
                                    'vx': math.cos(ang) * sp,
                                    'vy': math.sin(ang) * sp,
                                    'faction': dr['faction'], 'life': 1.0, 'dmg': 1,
                                })
                                _sfx('shot', dr['x'], 0.55)
                                dr['fire_t'] = rnd.uniform(0.4, 0.8)
                    if dr['age'] >= dr['life']:
                        dr['state'] = 'leave'
            else:
                tx = dr['target_x']
                dx = tx - dr['x']
                if abs(dx) < 1.0:
                    dr['target_x'] = tx + rnd.uniform(-15, 15)
                    dx = dr['target_x'] - dr['x']
                dr['vx'] += (1 if dx > 0 else -1) * 4.5 * dt
                dr['vx'] = max(-6.5, min(6.5, dr['vx']))
                dr['x'] += dr['vx'] * dt
                dr['y'] = gy - (4.5 + bob)
                dr['fire_t'] -= dt
                if dr['fire_t'] <= 0:
                    for sol in s['soldiers']:
                        if sol['dead'] or sol['faction'] == dr['faction']:
                            continue
                        if abs(sol['x'] - dr['x']) < 9 and dr['y'] > sol['y'] - 8:
                            ang = math.atan2((sol['y'] - 2) - dr['y'], sol['x'] - dr['x'])
                            sp = rnd.uniform(40, 52)
                            s['bullets'].append({
                                'x': dr['x'], 'y': dr['y'],
                                'px': dr['x'], 'py': dr['y'],
                                'vx': math.cos(ang) * sp, 'vy': math.sin(ang) * sp,
                                'faction': dr['faction'], 'life': 1.2, 'dmg': 1,
                            })
                            dr['fire_t'] = rnd.uniform(0.9, 1.6)
                            break
                    else:
                        dr['fire_t'] = 0.3
                if dr['age'] >= dr['life']:
                    dr['state'] = 'leave'
        dr['x'] = max(8.0, min(s['gw'] - 8.0, dr['x']))
        keep.append(dr)
    s['drones'] = keep
    alive_ids = {d.get('swarm_id') for d in keep if d.get('swarm_id') is not None}
    s['swarms'] = [sw for sw in s['swarms'] if sw['id'] in alive_ids]


def _spawn_hacker(s, fac):
    rnd = s['rnd']
    bu = s['bunkers'][fac]
    off = -3 if fac == 0 else 3
    hk = {
        'faction': fac, 'x': float(bu['x'] + off), 'y': float(s['gy'] - 1),
        'hp': 4, 'cd': 0.0, 'lock': None, 'lock_t': 0.0,
        'flash': 0.0, 'phase': rnd.uniform(0, 6.28), 'dead': False,
    }
    s['hackers'].append(hk)
    return hk


def _update_hackers(s, dt, w, h):
    rnd = s['rnd']
    range_ = w * 1.5
    for hk in s['hackers']:
        if hk['dead']:
            continue
        hk['phase'] += dt
        hk['flash'] = max(0.0, hk['flash'] - dt)
        hk['cd'] = max(0.0, hk['cd'] - dt)

        cur = hk['lock']
        if cur is not None and (cur['dead'] or cur.get('hack')
                                or cur.get('diverted')
                                or abs(cur['x'] - hk['x']) > range_):
            hk['lock'] = None
            cur = None
        if cur is None and hk['cd'] <= 0:
            best = None
            bd = 1e9
            # drones are the hackers' main target
            for d in s['drones']:
                if d['dead'] or d['hack'] or d['faction'] == hk['faction']:
                    continue
                dd = abs(d['x'] - hk['x'])
                if dd < range_ and dd < bd:
                    bd = dd
                    best = d
            # with no drones in reach, they scramble a driller's navigation -
            # but only when the driller is close, so it's a last-ditch counter
            if best is None:
                dr_range = range_ * 0.3
                for dr in s['drillers']:
                    if dr['dead'] or dr['diverted'] or dr['faction'] == hk['faction']:
                        continue
                    dd = abs(dr['x'] - hk['x'])
                    if dd < dr_range and dd < bd:
                        bd = dd
                        best = dr
            if best is not None:
                hk['lock'] = best
                hk['lock_t'] = rnd.uniform(0.7, 1.1)
                _sfx('blip', hk['x'], 0.45)

        cur = hk['lock']
        if cur is None or hk['cd'] > 0:
            continue
        hk['lock_t'] -= dt
        s['pulses'].append({'x1': hk['x'], 'y1': hk['y'] - 3,
                            'x2': cur['x'], 'y2': cur['y'],
                            'age': 0.0, 'life': 0.13, 'lock': True})
        if hk['lock_t'] <= 0:
            if cur.get('kind') == 'driller':
                # scrambled navigation: the driller burrows off course
                cur['diverted'] = True
                cur['diverge_x'] = cur['x'] + rnd.uniform(-26, 26)
            else:
                cur['hack'] = {'fac': hk['faction']}
                cur['hack_t'] = 0.0
            hk['cd'] = rnd.uniform(2.5, 4.5)
            hk['lock'] = None
            hk['flash'] = 0.22
            _sfx('blip', cur['x'], 0.8)
            s['pulses'].append({'x1': hk['x'], 'y1': hk['y'] - 3,
                                'x2': cur['x'], 'y2': cur['y'],
                                'age': 0.0, 'life': 0.5, 'hack': True})


def _spawn_sniper(s, fac, w):
    """A sharpshooter perched on a rooftop or inside a building window.

    They are the only ground units that can shoot drones down, and their
    high-calibre rounds drop regular soldiers in one hit.
    """
    rnd = s['rnd']
    front = s['front'][fac]
    bu = s['bunkers'][fac]['x']
    cand = []
    for sp in s['sniper_spots']:
        if sp['sn'] is not None:
            continue
        b = s['buildings'][sp['b_idx']]
        if (b.get('collapsed') or b.get('tip', 0) or b.get('gone')
                or b.get('falling') is not None or b['damage'] > 0.8):
            continue
        if fac == 0:
            if bu - w * 0.25 < sp['x'] < front - 1:
                cand.append(sp)
        else:
            if front + 1 < sp['x'] < bu + w * 0.25:
                cand.append(sp)
    if not cand:
        return None
    cand.sort(key=lambda sp: abs(sp['x'] - front))
    pool = cand[:min(8, len(cand))]
    sp = rnd.choice(pool)
    sn = {
        'faction': fac, 'x': float(sp['x']), 'y': float(sp['y']),
        'spot': sp, 'kind': sp['kind'],
        'hp': 3, 'flash': 0.0, 'cd': rnd.uniform(0.6, 1.6),
        'lock': None, 'aim': 1,
        'phase': rnd.uniform(0, 6.28), 'dead': False,
    }
    sp['sn'] = sn
    s['snipers'].append(sn)
    return sn


def _destroy_sniper(s, sn):
    rnd = s['rnd']
    sn['dead'] = True
    if sn.get('spot'):
        sn['spot']['sn'] = None
    s['explosions'].append({'x': sn['x'], 'y': sn['y'], 'age': 0.0,
                            'life': 0.35, 'radius_max': 3.0})
    for _ in range(4):
        a = rnd.uniform(0, 6.283)
        sp = rnd.uniform(1, 8)
        s['debris'].append({'x': sn['x'], 'y': sn['y'],
                            'vx': math.cos(a) * sp, 'vy': math.sin(a) * sp - 4,
                            'age': 0.0, 'life': rnd.uniform(0.3, 0.9),
                            'hue': 0.1, 'hot': True})
    _sfx('boom', sn['x'], 0.6, 0.8)


def _update_snipers(s, dt, w, h):
    rnd = s['rnd']
    keep = []
    for sn in s['snipers']:
        if sn['dead']:
            continue
        sn['flash'] = max(0.0, sn['flash'] - dt)
        sn['cd'] = max(0.0, sn['cd'] - dt)
        sn['phase'] += dt

        b = s['buildings'][sn['spot']['b_idx']]
        if (b.get('collapsed') or b.get('tip', 0) or b.get('gone')
                or b.get('falling') is not None or b['damage'] > 0.82):
            _destroy_sniper(s, sn)
            continue
        if sn['kind'] == 'window':
            tear = int(b['damage'] * b['h'] * 0.55)
            wy_c = int(sn['spot']['y']) // 2
            if wy_c < b['base'] - b['h'] + tear:
                _destroy_sniper(s, sn)
                continue

        cur = sn['lock']
        cur_is_drone = sn.get('lock_is_drone', False)
        if cur is not None and cur.get('dead'):
            sn['lock'] = None
            cur = None
        if cur is None:
            rng = w * 0.7
            best = None
            bd = rng
            for sol in s['soldiers']:
                if sol['dead'] or sol['faction'] == sn['faction']:
                    continue
                d = abs(sol['x'] - sn['x'])
                if d < bd:
                    bd = d
                    best = sol
            # snipers are the drone-hunters: prefer to engage a close drone
            drone_d = 1e9
            drone = None
            for dr in s['drones']:
                if dr['dead'] or dr['faction'] == sn['faction']:
                    continue
                d = abs(dr['x'] - sn['x'])
                if d < rng and d < drone_d:
                    drone_d = d
                    drone = dr
            if drone is not None and (best is None or drone_d < bd * 1.3):
                best = drone
                cur_is_drone = True
            else:
                cur_is_drone = False
            if best is not None:
                sn['lock'] = best
                sn['lock_is_drone'] = cur_is_drone
                if best is drone:
                    _sfx('blip', sn['x'], 0.35)

        cur = sn['lock']
        if cur is None:
            keep.append(sn)
            continue
        if sn['cd'] > 0:
            keep.append(sn)
            continue

        # high-calibre round with lead, tuned for the target's height
        if cur_is_drone:
            tx, ty = cur['x'], cur['y']
        else:
            tx, ty = cur['x'], cur['y'] - 3
        sx, sy = sn['x'], sn['y'] - 2
        dx, dy = tx - sx, ty - sy
        dist = max(1.0, math.hypot(dx, dy))
        if cur_is_drone:
            lead = cur.get('vx', 0.0) * (dist / 130.0)
            tx += lead
            dx = tx - sx
        sp = 130.0
        tt = dist / sp
        spread = rnd.uniform(-0.012, 0.012)
        ang = math.atan2(dy, dx) + spread
        vx = math.cos(ang) * sp
        vy = math.sin(ang) * sp - 0.5 * 4.0 * tt
        s['bullets'].append({
            'x': sx, 'y': sy, 'px': sx, 'py': sy,
            'vx': vx, 'vy': vy,
            'faction': sn['faction'], 'life': 2.2,
            'dmg': 4, 'sniper': True,
        })
        sn['flash'] = 0.12
        sn['aim'] = 1 if tx > sn['x'] else -1
        sn['cd'] = rnd.uniform(1.6, 2.8)
        _sfx('zap', sx, 0.6)
        keep.append(sn)
    s['snipers'] = keep


def _render_sniper(hr, sn, t, w, h, cam):
    # a lone, barely-visible speck in a window or on a rooftop - the size of
    # a building-window light, just a shade bigger so a keen eye can spot it
    x, y = int(sn['x'] - cam), int(sn['y'])
    hue = FACTION_HUE[sn['faction']]
    glint = 0.5 + 0.5 * math.sin(t * 3.5 + sn['phase'] * 6)
    hr.set_pixel(x, y - 2, '·', fg=Color.from_hsv(hue, 0.5, 0.85), z=27)
    hr.set_pixel(x, y - 1, '·', fg=Color.from_hsv(hue, 0.4, 0.45), z=26)
    if sn['flash'] > 0:
        hr.set_pixel(x + sn['aim'] * 2, y - 2, '·',
                     fg=Color(255, 255, 235), z=47)


def _spawn_builder(s, fac):
    rnd = s['rnd']
    bu = s['bunkers'][fac]
    off = -4 if fac == 0 else 4
    bd = {
        'faction': fac, 'state': 'walk',
        'x': float(bu['x'] + off), 'y': float(s['gy'] - 1),
        'vx': 0.0, 'target_x': 0.0,
        'build_t': 0.0, 'progress': 0.0, 'spark_t': 0.0,
        'hp': 6, 'flash': 0.0, 'phase': rnd.uniform(0, 6.28),
        'dead': False,
    }
    s['builders'].append(bd)
    return bd


def _complete_bunker(s, bd):
    rnd = s['rnd']
    cells = []
    for dy in range(-2, 1):
        for dx in range(-3, 4):
            cells.append({'dx': dx, 'dy': dy, 'r': rnd.random(),
                          'slit': dy == -1 and dx == 0})
    s['bunkers'].append({'faction': bd['faction'], 'x': float(bd['x']),
                         'base': s['gy'] - 1, 'cells': cells,
                         'damage': 0.0, 'built': True})
    s['built_bunkers'][bd['faction']] += 1
    for _ in range(5):
        s['smoke'].append({'x': bd['x'] + rnd.uniform(-1, 1), 'y': s['gy'] - 2,
                           'vx': rnd.uniform(-1.0, 1.0),
                           'vy': -rnd.uniform(1.0, 2.6),
                           'age': 0.0, 'life': rnd.uniform(0.6, 1.2),
                           'dust': True})


def _destroy_builder(s, bd):
    rnd = s['rnd']
    bd['dead'] = True
    s['explosions'].append({'x': bd['x'], 'y': bd['y'] - 2, 'age': 0.0,
                            'life': 0.6, 'radius_max': 6.0})
    s['shockwaves'].append({'x': bd['x'], 'y': bd['y'], 'age': 0.0,
                            'life': 0.5, 'radius_max': 8.0})
    for _ in range(6):
        a = rnd.uniform(0, 6.283)
        sp = rnd.uniform(2, 11)
        s['debris'].append({'x': bd['x'], 'y': bd['y'] - 2,
                            'vx': math.cos(a) * sp, 'vy': math.sin(a) * sp - 5,
                            'age': 0.0, 'life': rnd.uniform(0.4, 1.1),
                            'hue': 0.1, 'hot': True})


def _update_builders(s, dt, w):
    rnd = s['rnd']
    gy = s['gy']
    keep = []
    for bd in s['builders']:
        bd['phase'] += dt
        bd['flash'] = max(0.0, bd['flash'] - dt)
        if bd['dead']:
            continue
        if bd['state'] == 'walk':
            dx = bd['target_x'] - bd['x']
            bd['vx'] = max(-4.0, min(4.0, dx * 2.0))
            bd['x'] += bd['vx'] * dt
            if abs(dx) < 2.0:
                bd['state'] = 'build'
                bd['build_t'] = rnd.uniform(7, 10)
                bd['progress'] = 0.0
                s['smoke'].append({'x': bd['x'], 'y': gy - 2,
                                   'vx': rnd.uniform(-0.5, 0.5),
                                   'vy': -rnd.uniform(0.5, 1.5),
                                   'age': 0.0, 'life': 0.8, 'dust': True})
        else:
            bd['progress'] += dt / max(0.5, bd['build_t'])
            bd['spark_t'] -= dt
            if bd['spark_t'] <= 0:
                bd['spark_t'] = rnd.uniform(0.08, 0.2)
                s['debris'].append({'x': bd['x'] + 2, 'y': gy - 2,
                                    'vx': rnd.uniform(-0.5, 0.5),
                                    'vy': -rnd.uniform(0.5, 2.2),
                                    'age': 0.0, 'life': rnd.uniform(0.2, 0.5),
                                    'hue': 0.09, 'hot': True})
            if bd['progress'] >= 1.0:
                _complete_bunker(s, bd)
                continue
        keep.append(bd)
    s['builders'] = keep


def _spawn_driller(s, fac):
    """A burrowing combat robot that digs underground, tracks a big enemy
    unit, then erupts beneath it and pierces its underbelly.

    A hacker can hijack its navigation and divert its trajectory: the driller
    then surfaces at the wrong spot, wasting the strike.
    """
    rnd = s['rnd']
    bu = s['bunkers'][fac]
    s['drillers'].append({
        'kind': 'driller', 'faction': fac, 'state': 'dig', 'age': 0.0,
        'x': float(bu['x']) + (2 if fac == 0 else -2),
        'y': float(s['gy'] + 2),
        'dir': 1 if fac == 0 else -1,
        'tgt': None,
        'diverted': False, 'diverge_x': None, 'rise_t': 0.0,
        'phase': rnd.uniform(0, 6.28), 'flash': 0.0,
        'dead': False,
    })
    return s['drillers'][-1]


def _driller_target(s, dr):
    """Pick the best big enemy unit to pierce: mechs first, then heavy
    tanks, then anything armoured, nearest preferred."""
    foes = []
    for me in s['mechs']:
        if not me['dead'] and me['faction'] != dr['faction']:
            foes.append((abs(me['x'] - dr['x']), 0, me))
    for tk in s['tanks']:
        if tk['dead'] or tk['faction'] == dr['faction']:
            continue
        wgt = 0 if tk['kind'] == 'heavy' else 1
        foes.append((abs(tk['x'] - dr['x']), wgt, tk))
    if not foes:
        return None
    foes.sort(key=lambda t: (t[1], t[0]))
    return foes[0][2]


def _driller_strike(s, dr):
    """Erupt through the ground and punch the target's underbelly."""
    rnd = s['rnd']
    gy = s['gy']
    x = dr['x']
    tgt = dr['tgt']
    s['shockwaves'].append({'x': x, 'y': gy, 'age': 0.0, 'life': 0.5,
                            'radius_max': 10.0})
    s['explosions'].append({'x': x, 'y': gy - 1, 'age': 0.0, 'life': 0.5,
                            'radius_max': 6.0})
    for _ in range(12):
        a = rnd.uniform(0, 6.283)
        sp = rnd.uniform(2, 10)
        s['debris'].append({'x': x, 'y': gy - 1,
                            'vx': math.cos(a) * sp, 'vy': -abs(math.sin(a)) * sp - 2,
                            'age': 0.0, 'life': rnd.uniform(0.4, 1.1),
                            'hue': 0.09, 'hot': True})
    for _ in range(6):
        s['smoke'].append({'x': x + rnd.uniform(-2, 2), 'y': gy - 1,
                           'vx': rnd.uniform(-0.8, 0.8),
                           'vy': -rnd.uniform(2, 5),
                           'age': 0.0, 'life': rnd.uniform(0.5, 1.2)})
    s['craters'].append({'x': x, 'y': gy + 1, 'r': 3})
    if len(s['craters']) > 90:
        s['craters'].pop(0)
    _sfx('boom', x, 0.85, 1.6)
    if (tgt is not None and not tgt.get('dead')
            and tgt.get('hp', 1) > 0 and abs(tgt['x'] - x) < 3.5):
        if tgt.get('kind') == 'mech':
            tgt['hp'] -= 8
            tgt['flash'] = 0.2
            if tgt['hp'] <= 0:
                _destroy_mech(s, tgt)
        else:
            dmg = 5 if tgt['kind'] == 'heavy' else 4
            tgt['hp'] -= dmg
            tgt['flash'] = 0.2
            if tgt['hp'] <= 0:
                _destroy_tank(s, tgt)
    dr['dead'] = True


def _driller_surface(s, dr):
    """A disrupted driller pops out at the wrong place - a wasted strike."""
    rnd = s['rnd']
    gy = s['gy']
    x = dr['x']
    s['shockwaves'].append({'x': x, 'y': gy, 'age': 0.0, 'life': 0.4,
                            'radius_max': 7.0})
    for _ in range(8):
        s['smoke'].append({'x': x + rnd.uniform(-2, 2), 'y': gy - 1,
                           'vx': rnd.uniform(-1.2, 1.2),
                           'vy': -rnd.uniform(2, 6),
                           'age': 0.0, 'life': rnd.uniform(0.4, 1.0),
                           'dust': True})
        s['debris'].append({'x': x + rnd.uniform(-1, 1), 'y': gy - 1,
                            'vx': rnd.uniform(-2.5, 2.5),
                            'vy': -rnd.uniform(1, 6),
                            'age': 0.0, 'life': rnd.uniform(0.3, 0.7),
                            'hue': 0.09, 'hot': False})
    s['craters'].append({'x': x, 'y': gy + 1, 'r': 2})
    if len(s['craters']) > 90:
        s['craters'].pop(0)
    _sfx('flak', x, 0.5)
    dr['dead'] = True


def _update_drillers(s, dt, w, h):
    rnd = s['rnd']
    gy = s['gy']
    keep = []
    for dr in s['drillers']:
        if dr['dead']:
            continue
        dr['age'] += dt
        dr['phase'] += dt
        dr['flash'] = max(0.0, dr['flash'] - dt)
        if dr['state'] == 'dig':
            if dr['diverted']:
                # hacker scrambled the navigation: burrow toward a wrong spot
                if dr['diverge_x'] is None:
                    dr['diverge_x'] = dr['x'] + rnd.uniform(-26, 26)
                dx = dr['diverge_x'] - dr['x']
                if abs(dx) < 2.0:
                    dr['state'] = 'rise'
                    dr['rise_t'] = 0.6
                else:
                    dr['x'] += (1 if dx > 0 else -1) * 9.0 * dt
            else:
                tgt = dr['tgt']
                if tgt is None or tgt.get('dead') or tgt.get('hp', 1) <= 0:
                    dr['tgt'] = _driller_target(s, dr)
                    tgt = dr['tgt']
                if tgt is None or dr['age'] > 70:
                    # nothing worth piercing - give up and rise nearby
                    dr['diverted'] = True
                    dr['diverge_x'] = dr['x'] + rnd.uniform(-14, 14)
                    continue
                dx = tgt['x'] - dr['x']
                if abs(dx) < 2.2:
                    dr['state'] = 'rise'
                    dr['rise_t'] = 0.35
                else:
                    dr['x'] += (1 if dx > 0 else -1) * 9.5 * dt
            if rnd.random() < dt * 7:
                s['smoke'].append({'x': dr['x'] + rnd.uniform(-1, 1), 'y': gy - 1,
                                   'vx': rnd.uniform(-0.4, 0.4),
                                   'vy': -rnd.uniform(0.3, 1.1),
                                   'age': 0.0, 'life': rnd.uniform(0.3, 0.7),
                                   'dust': True})
        elif dr['state'] == 'rise':
            dr['rise_t'] -= dt
            dr['y'] -= 30 * dt
            if rnd.random() < dt * 26:
                s['smoke'].append({'x': dr['x'] + rnd.uniform(-1.5, 1.5),
                                   'y': gy - 1,
                                   'vx': rnd.uniform(-1.5, 1.5),
                                   'vy': -rnd.uniform(2, 6),
                                   'age': 0.0, 'life': rnd.uniform(0.4, 1.0),
                                   'dust': True})
                s['debris'].append({'x': dr['x'], 'y': gy - 1,
                                    'vx': rnd.uniform(-2, 2),
                                    'vy': -rnd.uniform(1, 5),
                                    'age': 0.0, 'life': rnd.uniform(0.3, 0.7),
                                    'hue': 0.09, 'hot': False})
            if dr['y'] <= gy - 1 or dr['rise_t'] <= 0:
                if dr['diverted']:
                    _driller_surface(s, dr)
                else:
                    _driller_strike(s, dr)
                continue
        keep.append(dr)
    s['drillers'] = keep


def _render_driller(hr, dr, t, w, h, gy, cam):
    x = int(dr['x'] - cam)
    if dr['state'] == 'dig':
        # a faint mound of disturbed earth crawling along the surface
        if 0 <= x < w and gy < h:
            hump = 0.5 + 0.5 * math.sin(t * 16 + dr['phase'])
            hr.set_pixel(x, gy - 1, '▄' if hump > 0.5 else '▒',
                         fg=Color.from_hsv(0.1, 0.5, 0.30 + 0.12 * hump), z=18)
            hr.set_pixel(x, gy, '▄', fg=Color.from_hsv(0.1, 0.4, 0.42), z=18)
    elif dr['state'] == 'rise':
        # drill spike tearing up through the soil
        if 0 <= x < w and gy - 1 < h:
            rise = max(0.0, min(1.0, (gy + 2 - dr['y']) / 3.0))
            spike = (Color(200, 200, 190) if not dr['diverted']
                     else Color(235, 170, 120))
            for k in range(int(rise * 5) + 1):
                yy = gy - 1 - k
                if yy < 0:
                    break
                hr.set_pixel(x, yy, '│', fg=spike, z=30)
            tip = '▲' if not dr['diverted'] else '¤'
            hr.set_pixel(x, gy - 1 - min(5, int(rise * 5)),
                         tip, fg=Color(255, 240, 190), z=30)


def _spawn_mother(s, w, h):
    rnd = s['rnd']
    mid = (s['front'][0] + s['front'][1]) / 2.0
    s['mothers'].append({
        'kind': 'mothership', 'faction': rnd.choice([0, 1]),
        'x': mid + rnd.uniform(-w * 0.15, w * 0.15),
        'y': h * 0.07 + rnd.uniform(-h * 0.02, h * 0.02),
        'vx': rnd.choice([-1, 1]) * rnd.uniform(6, 9),
        'hp': 260, 'beam_t': 2.0, 'aat_t': 0.0,
        'phase': rnd.uniform(0, 6.28), 'age': 0.0,
        'retire': False, 'dying': False, 'dead': False,
    })


def _spawn_tank(s, faction):
    rnd = s['rnd']
    bu = s['bunkers'][faction]
    heavy = rnd.random() < 0.3
    s['tanks'].append({
        'faction': faction, 'kind': 'heavy' if heavy else 'normal',
        'x': float(bu['x']) + (2 if faction == 0 else -2),
        'y': float(s['gy'] - 1),
        'hp': 9 if heavy else 3, 'state': 'advance',
        'target_x': float(s['front'][faction]),
        'fire_t': rnd.uniform(0.8, 2.0), 'facing': 1 if faction == 0 else -1,
        'flash': 0.0, 'dead': False,
    })


def _spawn_fighter(s, w, h, target):
    rnd = s['rnd']
    side = rnd.choice([-1, 1])
    mid = (s['front'][0] + s['front'][1]) / 2.0
    s['planes'].append({
        'kind': 'fighter',
        'x': mid + side * (w * 0.52),
        'y': h * 0.18 + rnd.uniform(-h * 0.06, h * 0.06),
        'vx': -side * rnd.uniform(24, 32), 'vy': 0.0,
        'hp': 5, 'gun_t': 0.3,
        'faction': 1 - target['faction'], 'tgt': target,
        'flash': 0.0, 'phase': rnd.uniform(0, 6.28), 'age': 0.0,
        'trail': [], 'crash': False, 'tgt': target,
    })


def _strafe_hit(s, gx):
    rnd = s['rnd']
    gy = s['gy']
    for i in range(3):
        s['debris'].append({'x': gx, 'y': gy - 1,
                            'vx': rnd.uniform(-0.8, 0.8),
                            'vy': -rnd.uniform(0.5, 3),
                            'age': 0.0, 'life': rnd.uniform(0.15, 0.4),
                            'hue': 0.09, 'hot': i == 0})
    s['smoke'].append({'x': gx, 'y': gy - 2,
                       'vx': rnd.uniform(-0.4, 0.4),
                       'vy': -rnd.uniform(0.6, 1.8),
                       'age': 0.0, 'life': rnd.uniform(0.3, 0.7)})
    for sol in s['soldiers']:
        if sol['dead']:
            continue
        if abs(sol['x'] - gx) < 1.2 and rnd.random() < 0.3:
            _kill(s, sol, rnd.uniform(-2, 2), -2)
            break
    for tk in s['tanks']:
        if not tk['dead'] and abs(tk['x'] - gx) < 2.5 and rnd.random() < 0.45:
            tk['hp'] -= 1
            tk['flash'] = 0.1
            if tk['hp'] <= 0:
                _destroy_tank(s, tk)


def _target_active(s, tg):
    if tg.get('crash') or tg.get('dead') or tg.get('dying'):
        return False
    if tg.get('kind') == 'mothership':
        return any(m is tg for m in s['mothers'])
    if tg.get('kind') == 'zeppelin':
        return any(z is tg for z in s['zeppelins'])
    return any(q is tg for q in s['planes'])


def _fire_air(s, src, tgt):
    rnd = s['rnd']
    ang = math.atan2(tgt['y'] - src['y'], tgt['x'] - src['x'])
    sp = rnd.uniform(46, 60)
    s['air'].append({
        'x': src['x'] + math.cos(ang) * 1.5,
        'y': src['y'] + math.sin(ang) * 1.5,
        'px': src['x'], 'py': src['y'],
        'vx': math.cos(ang) * sp, 'vy': math.sin(ang) * sp,
        'tgt': tgt, 'src': src, 'life': 0.9,
    })


def _update_air(s, dt, w, h):
    rnd = s['rnd']
    keep = []
    for a in s['air']:
        a['px'], a['py'] = a['x'], a['y']
        a['life'] -= dt
        tg = a['tgt']
        if not _target_active(s, tg):
            continue
        src = a.get('src')
        if src is not None and (src.get('crash') or src.get('dead') or src.get('dying')):
            continue
        dx, dy = tg['x'] - a['x'], tg['y'] - a['y']
        d = math.hypot(dx, dy)
        if d > 1:
            sp = 52.0
            a['vx'] += (dx / d * sp - a['vx']) * min(1.0, dt * 4)
            a['vy'] += (dy / d * sp - a['vy']) * min(1.0, dt * 4)
        a['x'] += a['vx'] * dt
        a['y'] += a['vy'] * dt
        if tg.get('kind') == 'mothership':
            hit_r = 3.0
        elif tg.get('kind') == 'zeppelin':
            hit_r = 10.0
        else:
            hit_r = 2.0
        if d < hit_r:
            if tg.get('kind') == 'fighter' and rnd.random() < 0.45:
                continue
            # armored hulls: most fighter rounds ping off big airships
            if tg.get('kind') in ('mothership', 'zeppelin') and rnd.random() < 0.6:
                for _ in range(2):
                    s['debris'].append({'x': tg['x'] + rnd.uniform(-4, 4),
                                        'y': tg['y'] + rnd.uniform(-2, 2),
                                        'vx': rnd.uniform(-2, 2),
                                        'vy': rnd.uniform(-1, 2),
                                        'age': 0.0, 'life': rnd.uniform(0.15, 0.35),
                                        'hue': 0.1, 'hot': False})
                continue
            tg['hp'] -= 1
            for _ in range(3):
                s['debris'].append({'x': tg['x'], 'y': tg['y'],
                                    'vx': rnd.uniform(-3, 3), 'vy': rnd.uniform(-3, 1),
                                    'age': 0.0, 'life': rnd.uniform(0.2, 0.5),
                                    'hue': 0.1, 'hot': True})
            if tg['hp'] <= 0:
                if tg.get('kind') == 'mothership':
                    continue
                if tg.get('kind') == 'zeppelin':
                    _destroy_zeppelin(s, tg)
                    continue
                if not tg['crash']:
                    tg['crash'] = True
                    tg['vy'] = rnd.uniform(0.5, 2)
            continue
        if a['life'] <= 0 or a['x'] < -w or a['x'] > s['gw'] + w or a['y'] < -8 or a['y'] > h + 8:
            continue
        keep.append(a)
    s['air'] = keep


def _steer_fighter(s, p, tg, dt, w, h):
    """Fly with real momentum: hold a fast cruise speed and bank through
    wide turns. Fighters pass their quarry and loop back instead of parking
    on top of it, so dogfights look like planes, not helicopters."""
    kind = tg['kind']
    wob = math.sin(p['age'] * 3 + p['phase'])
    if kind == 'mothership':
        side = 1 if p['x'] < tg['x'] else -1
        tx = tg['x'] + side * 9
        ty = tg['y'] + 5 + wob * 2.0
        cruise = 24.0
    elif kind == 'zeppelin':
        side = 1 if p['x'] < tg['x'] else -1
        tx = tg['x'] + side * 12
        ty = tg['y'] + 6 + wob * 2.0
        cruise = 24.0
    elif kind == 'fighter':
        # deflection shot: aim just past the enemy along its heading so we
        # roar through the merge instead of hovering on it
        hd = math.hypot(tg.get('vx', p['vx']), tg.get('vy', 0.0))
        hx = tg.get('vx', p['vx']) / max(1.0, hd)
        hy = tg.get('vy', 0.0) / max(1.0, hd)
        side = 1 if p['x'] < tg['x'] else -1
        tx = tg['x'] + hx * 8 + side * 6
        ty = tg['y'] + hy * 8 + 2 + wob * 1.5
        cruise = 34.0
    else:
        side = 1 if p['x'] < tg['x'] else -1
        tx = tg['x'] + side * 7
        ty = tg['y'] - 3 + wob * 1.2
        cruise = 30.0
    dx, dy = tx - p['x'], ty - p['y']
    dist = max(1.0, math.hypot(dx, dy))
    want = math.atan2(dy, dx)
    cur = math.atan2(p['vy'], p['vx'])
    # limited turn rate -> banking turns instead of teleport-style snapping
    da = (want - cur + math.pi) % (2.0 * math.pi) - math.pi
    turn = 3.4 * dt
    cur += max(-turn, min(turn, da))
    p['vx'] += (math.cos(cur) * cruise - p['vx']) * min(1.0, dt * 2.2)
    p['vy'] += (math.sin(cur) * cruise - p['vy']) * min(1.0, dt * 2.2)
    p['x'] += p['vx'] * dt
    p['y'] += p['vy'] * dt


def _fighter_target(s, p):
    pf = p.get('faction')
    foes = [q for q in s['planes'] if q is not p and q['kind'] == 'fighter'
            and q.get('faction') != pf and not q['crash']]
    if foes:
        foes.sort(key=lambda q: abs(q['x'] - p['x']))
        return foes[0]
    g = p['tgt']
    if (g is not None and any(q is g for q in s['planes'])
            and g['kind'] == 'gunship' and not g['crash']
            and g.get('faction') != pf):
        return g
    g = [q for q in s['planes'] if q['kind'] == 'gunship' and not q['crash']
         and q.get('faction') != pf]
    if g:
        g.sort(key=lambda q: abs(q['x'] - p['x']))
        return g[0]
    tr = [q for q in s['planes'] if q['kind'] == 'transport' and not q['crash']
          and q.get('faction') != pf]
    if tr:
        tr.sort(key=lambda q: abs(q['x'] - p['x']))
        return tr[0]
    ze = [z for z in s['zeppelins'] if not z['dead'] and z['faction'] != pf]
    if ze:
        return ze[0]
    ms = [m for m in s['mothers'] if not m['dying'] and not m['dead']
          and m['faction'] != pf]
    return ms[0] if ms else None


def _update_planes(s, dt, w, h):
    rnd = s['rnd']
    gy = s['gy']
    mid = (s['front'][0] + s['front'][1]) / 2.0
    keep = []
    for p in s['planes']:
        p['flash'] = max(0.0, p['flash'] - dt)
        p['age'] += dt
        if p['crash']:
            p['vy'] += 20 * dt
            p['vx'] += math.sin(p['age'] * 4.0 + p['phase']) * 9 * dt
            p['vx'] *= max(0.0, 1 - 0.35 * dt)
            p['x'] += p['vx'] * dt
            p['y'] += p['vy'] * dt
            p['phase'] += dt * 5
            for _ in range(2):
                s['smoke'].append({'x': p['x'] + rnd.uniform(-1, 1), 'y': p['y'],
                                   'vx': rnd.uniform(-1.2, 1.2),
                                   'vy': -rnd.uniform(1, 3),
                                   'age': 0.0, 'life': rnd.uniform(0.6, 1.4)})
            if rnd.random() < 0.5:
                s['debris'].append({'x': p['x'] + rnd.uniform(-2, 2), 'y': p['y'],
                                    'vx': rnd.uniform(-2.5, 2.5),
                                    'vy': rnd.uniform(-1.5, 2),
                                    'age': 0.0, 'life': rnd.uniform(0.4, 1.0),
                                    'hue': 0.07, 'hot': True})
            if p['y'] >= gy:
                _explode(s, p['x'], gy, 3.4, True)
                s['wrecks'].append({'x': p['x'], 'y': gy,
                                    'age': 0.0,
                                    'life': rnd.uniform(4.0, 6.0)})
                if len(s['wrecks']) > 6:
                    s['wrecks'].pop(0)
                continue
            keep.append(p)
            continue
        if p['kind'] == 'transport':
            p['x'] += p['vx'] * dt
            p['y'] = p['base_y'] + math.sin(p['age'] * 1.5 + p['phase']) * 1.2
            p['trail'].append((int(p['x']), int(p['y'])))
            if len(p['trail']) > 20:
                p['trail'].pop(0)
            if not p['retire'] and p['to_drop'] > 0:
                p['drop_t'] -= dt
                if p['drop_t'] <= 0:
                    p['drop_t'] = rnd.uniform(1.2, 1.7)
                    p['to_drop'] -= 1
                    _spawn_chute(s, p)
                if p['to_drop'] > 0 and (p['x'] < mid - w * 1.1
                                         or p['x'] > mid + w * 1.1):
                    p['retire'] = True
            elif p['to_drop'] <= 0:
                p['retire'] = True
            if p['retire']:
                p['vy'] -= 3.0 * dt
                p['y'] += p['vy'] * dt
                p['vx'] *= max(0.0, 1 - 0.4 * dt)
            keep.append(p)
            continue
        if p['kind'] == 'gunship':
            p['x'] += p['vx'] * dt
            p['y'] = p['base_y'] + math.sin(p['age'] * 1.2) * 2.0
            p['trail'].append((int(p['x']), int(p['y'])))
            if len(p['trail']) > 30:
                p['trail'].pop(0)
            if not p['retire']:
                if p['x'] < mid - w * 0.9:
                    p['vx'] = abs(p['vx'])
                elif p['x'] > mid + w * 0.9:
                    p['vx'] = -abs(p['vx'])
                if p['age'] > 30:
                    p['retire'] = True
                    p['vx'] = -abs(p['vx']) * (1 if p['x'] < mid else -1)
            p['gun_t'] -= dt
            if p['gun_t'] <= 0:
                p['gun_t'] = 0.09
                p['flash'] = 0.05
                _strafe_hit(s, p['x'] + rnd.uniform(-w * 0.03, w * 0.03))
            foe, fd = None, 1e9
            for q in s['planes']:
                if q is p or q['crash'] or q['kind'] != 'fighter':
                    continue
                d = math.hypot(q['x'] - p['x'], (q['y'] - p['y']) * 2)
                if d < fd:
                    fd, foe = d, q
            if foe and fd < 26:
                p['aat_t'] -= dt
                if p['aat_t'] <= 0:
                    p['aat_t'] = 0.32
                    _fire_air(s, p, foe)
        else:
            press = None
            if p['hp'] <= 2:
                for q in s['planes']:
                    if (q is not p and q['kind'] == 'fighter'
                            and not q['crash'] and q.get('faction') != p.get('faction')):
                        if math.hypot(q['x'] - p['x'], (q['y'] - p['y']) * 2) < 26:
                            press = q
                            break
            if press is not None:
                ddx = p['x'] - press['x']
                vx = (1 if ddx >= 0 else -1) * 32
                p['vx'] += (vx - p['vx']) * min(1.0, dt * 1.2)
                p['vy'] += math.sin(p['age'] * 6 + p['phase']) * 60 * dt
                p['x'] += p['vx'] * dt
                p['y'] += p['vy'] * dt
                p['trail'].append((int(p['x']), int(p['y'])))
                if len(p['trail']) > 16:
                    p['trail'].pop(0)
            else:
                tg = _fighter_target(s, p)
                if tg is not None:
                    _steer_fighter(s, p, tg, dt, w, h)
                else:
                    p['x'] += p['vx'] * dt
                    p['y'] += p['vy'] * dt
                p['trail'].append((int(p['x']), int(p['y'])))
                if len(p['trail']) > 16:
                    p['trail'].pop(0)
                if tg is not None:
                    d = math.hypot(tg['x'] - p['x'], (tg['y'] - p['y']) * 2)
                    if d < 34:
                        p['gun_t'] -= dt
                        if p['gun_t'] <= 0:
                            p['gun_t'] = 0.15
                            p['flash'] = 0.05
                            _fire_air(s, p, tg)
        if not p['crash'] and p['y'] >= gy - 1:
            p['crash'] = True
            p['vy'] = rnd.uniform(1.0, 3.0)
        if p['x'] < mid - w * 1.6 or p['x'] > mid + w * 1.6 or p['y'] > h + 20 or p['y'] < -8:
            continue
        keep.append(p)
    s['planes'] = keep


def _render_air(hr, a, w, h, cam):
    x, y = int(a['x'] - cam), int(a['y'])
    px, py = int(a['px'] - cam), int(a['py'])
    col = Color(255, 255, 210)
    hr.set_pixel(x, y, '▓', fg=col, z=45)
    if px != x or py != y:
        hr.set_pixel(px, py, '·', fg=col.mul(0.5), z=44)


def _render_plane(hr, p, t, w, h, gy, cam):
    px, py = int(p['x'] - cam), int(p['y'])
    if p['crash']:
        fl = 0.5 + 0.5 * math.sin(t * 30 + p['phase'])
        d = -1 if p['vx'] < 0 else 1
        spin = int(p['phase'] * 0.8) % 4
        if 0 <= px < w and 0 <= py < h:
            nose = px + (d if spin < 2 else -d)
            hr.set_pixel(px, py, '▄' if spin < 2 else '▀',
                         fg=Color(72, 72, 84), z=43)
            hr.set_pixel(nose, py, '█', fg=Color(30, 30, 38), z=43)
            hr.set_pixel(px, py - 1, '▓',
                         fg=Color.from_hsv(0.07, 1, 0.5 + 0.5 * fl), z=44)
            hr.set_pixel(px - d, py, '░',
                         fg=Color.from_hsv(0.07, 0.9, 0.4 + 0.6 * fl), z=43)
        return
    for i, (tx, ty) in enumerate(p['trail'][:-1]):
        sx, sy = int(tx - cam), ty
        f = i / max(1, len(p['trail']))
        if 0 <= sx < w and 0 <= sy < h:
            col = Color.from_hsv(0.0, 0.35, 0.22 + f * 0.3)
            hr.set_pixel(sx, sy, '░' if f > 0.5 else '·', fg=col, z=36)
    if 0 <= px < w and 0 <= py < h:
        if p['kind'] == 'transport':
            d = -1 if p['vx'] < 0 else 1
            hr.set_pixel(px, py, '▄', fg=Color(88, 90, 102), z=43)
            hr.set_pixel(px + d, py, '█', fg=Color(52, 52, 62), z=43)
            hr.set_pixel(px - d, py, '▄', fg=Color(76, 78, 88), z=43)
            hr.set_pixel(px - d, py - 1, '─', fg=Color(66, 68, 78), z=43)
            blink = 0.5 + 0.5 * math.sin(t * 6 + p['phase'])
            hr.set_pixel(px - d, py - 1, '·',
                         fg=Color(255, 90, 60) if blink > 0.6 else Color(255, 255, 255),
                         z=43)
            if p['to_drop'] > 0 and p['drop_t'] < 0.3:
                hr.set_pixel(px, py + 1, '░', fg=Color(255, 210, 120), z=44)
        else:
            body, nose = ((Color(62, 64, 72), Color(34, 34, 40))
                          if p['kind'] == 'gunship'
                          else (Color(168, 170, 184), Color(96, 98, 112)))
            d = -1 if p['vx'] < 0 else 1
            hr.set_pixel(px, py, '▄', fg=body, z=43)
            hr.set_pixel(px + d, py, '█', fg=nose, z=43)
            blink = 0.5 + 0.5 * math.sin(t * 5 + p['phase'])
            hr.set_pixel(px + d, py - 1, '·',
                         fg=Color(255, 90, 60) if blink > 0.7 else Color(255, 255, 255),
                         z=43)
            if p['flash'] > 0:
                hr.set_pixel(px, py, '▓', fg=Color(255, 220, 140), z=44)
                if p['kind'] == 'gunship':
                    for yy in range(py + 2, min(h, gy)):
                        hr.set_pixel(px, yy, '·', fg=Color(255, 200, 120).mul(0.6), z=42)


# ----------------------------------------------------------------------
# tanks, motherships, flak
# ----------------------------------------------------------------------

def _render_tank(hr, tk, w, h, cam):
    if tk['dead']:
        return
    x, y = int(tk['x'] - cam), int(tk['y'])
    hue = FACTION_HUE[tk['faction']]
    fac = tk['facing']
    if tk['flash'] > 0:
        body = Color(255, 255, 255)
        turret = Color(255, 235, 200)
    else:
        body = Color.from_hsv(hue, 0.95, 0.98)
        turret = Color.from_hsv(hue, 0.9, 0.72)
    tr = Color(28, 26, 26)
    if tk['kind'] == 'heavy':
        dark = Color.from_hsv(hue, 0.85, 0.42)
        for dx in range(-5, 6):
            hr.set_pixel(x + dx, y - 1, '▄', fg=tr, z=26)
        for dx in range(-4, 5):
            hr.set_pixel(x + dx, y - 2, '▄', fg=dark, z=27)
        for dx in range(-4, 5):
            hr.set_pixel(x + dx, y - 3, '▄', fg=body, z=27)
        for dx in range(-3, 4):
            hr.set_pixel(x + dx, y - 4, '▄', fg=dark, z=27)
        for dx in range(-2, 3):
            hr.set_pixel(x + dx, y - 5, '▄', fg=turret, z=27)
        hr.set_pixel(x - 1, y - 6, '█', fg=body, z=27)
        hr.set_pixel(x, y - 6, '█', fg=body, z=27)
        hr.set_pixel(x + 1, y - 6, '█', fg=body, z=27)
        for b in (0, 2):
            bx = x + fac * b
            hr.set_pixel(bx, y - 7, '▄', fg=Color(200, 202, 214), z=27)
            hr.set_pixel(bx + fac, y - 7, '▄', fg=Color(150, 152, 166), z=27)
        hr.set_pixel(x, y - 8, '·', fg=Color.from_hsv(hue, 0.6, 0.8), z=26)
        hr.set_pixel(x + fac * 3, y - 5, '░', fg=Color.from_hsv(hue, 0.9, 0.6), z=26)
        if tk['flash'] > 0:
            bx = x + fac * 3
            by = y - 7
            hr.set_pixel(bx, by, '▓', fg=Color(255, 255, 230), z=46)
            hr.set_pixel(bx + fac, by, '▓', fg=Color(255, 220, 140), z=46)
            hr.set_pixel(bx + fac * 2, by, '░', fg=Color(255, 180, 90), z=45)
            hr.set_pixel(bx, by + 1, '░', fg=Color(255, 170, 80), z=45)
        return
    for dx in range(-3, 4):
        hr.set_pixel(x + dx, y - 1, '▄', fg=tr, z=26)
    for dx in range(-2, 3):
        hr.set_pixel(x + dx, y - 2, '▄', fg=Color.from_hsv(hue, 0.85, 0.55), z=27)
        hr.set_pixel(x + dx, y - 3, '▄', fg=body, z=27)
    for dx in range(-1, 2):
        hr.set_pixel(x + dx, y - 4, '▄', fg=turret, z=27)
    hr.set_pixel(x, y - 5, '█', fg=body, z=27)
    hr.set_pixel(x + fac, y - 5, '─', fg=Color(210, 212, 224), z=27)
    hr.set_pixel(x + fac * 2, y - 5, '─', fg=Color(168, 170, 186), z=27)
    hr.set_pixel(x, y - 6, '·', fg=Color.from_hsv(hue, 0.6, 0.8), z=26)
    hr.set_pixel(x - fac * 3, y - 2, '·', fg=Color.from_hsv(0.1, 0.9, 0.75), z=26)
    if tk['flash'] > 0:
        bx = x + fac * 2
        by = y - 5
        hr.set_pixel(bx, by, '▓', fg=Color(255, 255, 230), z=46)
        hr.set_pixel(bx + fac, by, '▓', fg=Color(255, 220, 140), z=46)
        hr.set_pixel(bx + fac * 2, by, '░', fg=Color(255, 180, 90), z=45)


def _render_shell(hr, sh, w, h, cam):
    x, y = int(sh['x'] - cam), int(sh['y'])
    px, py = int(sh['px'] - cam), int(sh['py'])
    hr.set_pixel(x, y, '▓', fg=Color(255, 235, 180), z=46)
    if px != x or py != y:
        hr.set_pixel(px, py, '░', fg=Color(255, 190, 120).mul(0.9), z=45)
        hr.set_pixel(px - (x - px), py - (y - py), '░',
                     fg=Color(255, 160, 90).mul(0.45), z=44)


def _render_wreck(hr, wk, t, w, h, cam):
    x, y = int(wk['x'] - cam), int(wk['y'])
    fade = min(1.0, (wk['life'] - wk['age']) / 1.2)
    if fade <= 0.1:
        return
    col = Color(38, 36, 34).mul(fade)
    for dx in range(-2, 3):
        hr.set_pixel(x + dx, y - 2, '▄', fg=col, z=16)
    hr.set_pixel(x - 1, y - 3, '▄', fg=col, z=16)
    hr.set_pixel(x, y - 3, '▒', fg=Color(52, 42, 36).mul(fade), z=16)
    hr.set_pixel(x + 1, y - 3, '▄', fg=col, z=16)
    hr.set_pixel(x, y - 1, '░', fg=Color(120, 60, 24).mul(fade), z=16)
    fl = 0.5 + 0.5 * math.sin(t * 7 + wk['age'] * 0.3)
    if fl > 0.8:
        hr.set_pixel(x, y - 1, '▓', fg=Color(200, 110, 30).mul(fade), z=17)


def _render_mother(hr, ms, t, w, h, cam):
    x, y = int(ms['x'] - cam), int(ms['y'])
    if 0 <= x < w and 0 <= y < h:
        hull = Color(120, 120, 132)
        hull_d = Color(74, 74, 84)
        for dx in range(-3, 4):
            hr.set_pixel(x + dx, y, '▄', fg=hull, z=43)
            hr.set_pixel(x + dx, y + 1, '▄', fg=hull_d, z=43)
        hr.set_pixel(x, y - 1, '█', fg=hull_d, z=43)
        eng = 0.6 + 0.4 * math.sin(t * 6 + ms['phase'])
        hr.set_pixel(x, y + 2, '░', fg=Color.from_hsv(0.1, 0.9, eng), z=42)
        for dx in (-3, 3):
            blink = 0.5 + 0.5 * math.sin(t * 4 + ms['phase'] + dx)
            hr.set_pixel(x + dx, y, '·',
                         fg=Color(255, 255, 255) if blink > 0.6 else Color(255, 80, 60), z=44)
        if ms['hp'] < 30 or ms.get('crash'):
            fl = 0.5 + 0.5 * math.sin(t * 20 + ms['phase'])
            for dx in (0, 2, -2):
                if fl > 0.4:
                    hr.set_pixel(x + dx, y, '▓', fg=Color.from_hsv(0.07, 1, 0.6 + 0.4 * fl), z=44)


def _render_beam(hr, bm, w, h, cam):
    bx = int(bm['x'] - cam)
    p = 1.0 - bm['age'] / bm['life']
    b0 = int(bm['y0']), int(bm['y1'])
    col = Color(255, 250, 220)
    for yy in range(b0[0], b0[1]):
        if 0 <= bx < w and 0 <= yy < h:
            hr.set_pixel(bx, yy, '│' if yy % 2 else '┃',
                         fg=col.mul(p * 0.9), z=47)
    for dy in range(-2, 3):
        hr.set_pixel(bx + dy, b0[1] - 1, '░', fg=col.mul(p), z=48)


def _shell_blast(s, x, y):
    rnd = s['rnd']
    s['explosions'].append({'x': x, 'y': y, 'age': 0.0,
                            'life': 0.55, 'radius_max': 7.5})
    s['shockwaves'].append({'x': x, 'y': y, 'age': 0.0, 'life': 0.5,
                            'radius_max': 9.0})
    for _ in range(5):
        a = rnd.uniform(0, 6.283)
        sp = rnd.uniform(2, 9)
        s['debris'].append({'x': x, 'y': y, 'vx': math.cos(a) * sp,
                            'vy': math.sin(a) * sp - 4,
                            'age': 0.0, 'life': rnd.uniform(0.4, 0.9),
                            'hue': 0.07, 'hot': False})
    for _ in range(2):
        s['smoke'].append({'x': x + rnd.uniform(-1, 1), 'y': y,
                           'vx': rnd.uniform(-0.6, 0.6), 'vy': -rnd.uniform(1, 3),
                           'age': 0.0, 'life': rnd.uniform(0.8, 1.6)})
    _blast_soldiers(s, x, y, 7.5)
    for tk in s['tanks']:
        if tk['dead']:
            continue
        d = math.hypot(tk['x'] - x, (tk['y'] - y) * 2.0)
        if d < 9.0:
            tk['hp'] -= 2 if d < 6.0 else 1
            if tk['hp'] <= 0:
                _destroy_tank(s, tk)
    for me in s['mechs']:
        if me['dead']:
            continue
        d = math.hypot(me['x'] - x, (me['y'] - y) * 2.0)
        if d < 12.0:
            me['hp'] -= 2 if d < 8.0 else 1
            me['flash'] = 0.15
            if me['hp'] <= 0:
                _destroy_mech(s, me)


def _destroy_tank(s, tk):
    rnd = s['rnd']
    tk['dead'] = True
    tk['dead_t'] = 0.0
    s['wrecks'].append({'x': tk['x'], 'y': tk['y'],
                        'faction': tk['faction'], 'age': 0.0,
                        'life': rnd.uniform(3, 5)})
    if len(s['wrecks']) > 6:
        s['wrecks'].pop(0)
    s['explosions'].append({'x': tk['x'], 'y': tk['y'] - 3, 'age': 0.0,
                            'life': 0.7, 'radius_max': 9.0})
    s['shockwaves'].append({'x': tk['x'], 'y': tk['y'], 'age': 0.0,
                            'life': 0.6, 'radius_max': 11.0})
    s['craters'].append({'x': tk['x'], 'y': tk['y'] + 1, 'r': 3})
    for _ in range(8):
        a = rnd.uniform(0, 6.283)
        sp = rnd.uniform(2, 12)
        s['debris'].append({'x': tk['x'], 'y': tk['y'] - 2,
                            'vx': math.cos(a) * sp, 'vy': math.sin(a) * sp - 6,
                            'age': 0.0, 'life': rnd.uniform(0.5, 1.2),
                            'hue': 0.07, 'hot': rnd.random() < 0.5})
    for _ in range(4):
        s['smoke'].append({'x': tk['x'] + rnd.uniform(-2, 2), 'y': tk['y'] - 3,
                           'vx': rnd.uniform(-0.5, 0.5), 'vy': -rnd.uniform(1.5, 3.5),
                           'age': 0.0, 'life': rnd.uniform(1.2, 2.2)})
    _ragdoll_burst(s, tk['x'], tk['y'] - 3, 4, FACTION_HUE[tk['faction']],
                   spread=13.0, rise=12.0)


def _fire_shell(s, tk):
    rnd = s['rnd']
    mx = tk['x'] + tk['facing'] * 2
    my = tk['y'] - (5 if tk['kind'] == 'heavy' else 4)
    target = None
    for sol in s['soldiers']:
        if sol['dead'] or sol['faction'] == tk['faction']:
            continue
        if abs(sol['x'] - tk['x']) < 38:
            target = sol
            break
    if target is None:
        for o in s['tanks']:
            if o['dead'] or o['faction'] == tk['faction']:
                continue
            if abs(o['x'] - tk['x']) < 38:
                target = o
                break
    if target is None:
        for me in s['mechs']:
            if me['faction'] == tk['faction']:
                continue
            if abs(me['x'] - tk['x']) < 42:
                target = me
                break
    if target is None:
        return
    tt = rnd.uniform(0.45, 0.7)
    g = 16.0
    ty = target['y'] - (6 if target.get('kind') == 'mech' else 2)
    tx = target['x']
    s['shells'].append({
        'x': mx, 'y': my, 'px': mx, 'py': my,
        'vx': (tx - mx) / tt,
        'vy': (ty - my) / tt - 0.5 * g * tt,
        'g': g, 'faction': tk['faction'],
        'dmg': 2 if tk['kind'] == 'heavy' else 1,
    })
    tk['flash'] = 0.12
    _sfx('shot', mx, 1.2)
    for _ in range(2):
        s['smoke'].append({'x': mx + rnd.uniform(-0.5, 0.5), 'y': my,
                           'vx': rnd.uniform(-0.8, 0.8), 'vy': -rnd.uniform(0.5, 1.5),
                           'age': 0.0, 'life': rnd.uniform(0.25, 0.5)})


def _update_tanks(s, dt, w):
    rnd = s['rnd']
    W = s['gw']
    keep = []
    for tk in s['tanks']:
        if tk['dead']:
            tk['dead_t'] += dt
            if tk['dead_t'] > 7.0:
                continue
            keep.append(tk)
            continue
        tk['flash'] = max(0.0, tk['flash'] - dt)
        fac = tk['faction']
        dirv = 1 if fac == 0 else -1
        if tk['state'] == 'advance':
            tx = s['front'][fac]
            if abs(tk['x'] - tx) < 2.0:
                tk['state'] = 'hold'
                tk['target_x'] = tk['x']
            else:
                sp = 2.5 if tk['kind'] == 'heavy' else 5.0
                tk['x'] += dirv * sp * dt
        tk['x'] = max(4.0, min(W - 4.0, tk['x']))
        if tk['state'] == 'hold':
            tk['fire_t'] -= dt
            if tk['fire_t'] <= 0:
                _fire_shell(s, tk)
                if tk['kind'] == 'heavy':
                    tk['fire_t'] = rnd.uniform(3.2, 4.6)
                else:
                    tk['fire_t'] = rnd.uniform(2.2, 3.6)
        keep.append(tk)
    s['tanks'] = keep


def _update_shells(s, dt, w, h):
    rnd = s['rnd']
    gy = s['gy']
    keep = []
    for sh in s['shells']:
        sh['px'], sh['py'] = sh['x'], sh['y']
        sh['vy'] += sh['g'] * dt
        sh['x'] += sh['vx'] * dt
        sh['y'] += sh['vy'] * dt
        hit = False
        for sol in s['soldiers']:
            if sol['dead'] or sol['faction'] == sh['faction']:
                continue
            if abs(sol['x'] - sh['x']) < 1.5 and sh['y'] > sol['y'] - 5:
                _kill(s, sol, sh['vx'] * 0.1, -3, killer=sh['faction'])
                hit = True
                break
        if hit:
            _shell_blast(s, sh['x'], sh['y'])
            continue
        for tk in s['tanks']:
            if tk['dead'] or tk['faction'] == sh['faction']:
                continue
            if abs(tk['x'] - sh['x']) < 2.5 and sh['y'] > tk['y'] - 7:
                tk['hp'] -= sh.get('dmg', 1)
                tk['flash'] = 0.15
                if tk['hp'] <= 0:
                    _destroy_tank(s, tk)
                hit = True
                break
        if hit:
            _shell_blast(s, sh['x'], sh['y'])
            continue
        for me in s['mechs']:
            if me['faction'] == sh['faction']:
                continue
            if abs(me['x'] - sh['x']) < 3.0 and sh['y'] > me['y'] - 18:
                me['hp'] -= sh.get('dmg', 1)
                me['flash'] = 0.15
                if me['hp'] <= 0:
                    _destroy_mech(s, me)
                hit = True
                break
        if hit:
            _shell_blast(s, sh['x'], sh['y'])
            continue
        if sh['y'] >= gy - 1 or sh['x'] < -4 or sh['x'] > s['gw'] + 4 or sh['y'] > h + 10:
            if sh['y'] >= gy - 1:
                _shell_blast(s, sh['x'], min(sh['y'], gy - 1))
            continue
        keep.append(sh)
    s['shells'] = keep


def _spawn_mech(s, faction):
    rnd = s['rnd']
    bu = s['bunkers'][faction]
    s['mechs'].append({
        'faction': faction, 'kind': 'mech',
        'x': float(bu['x']) + (3 if faction == 0 else -3),
        'y': float(s['gy'] - 1),
        'hp': 16, 'state': 'advance', 'target_x': float(s['front'][faction]),
        'fire_t': rnd.uniform(1.5, 3.0),
        'facing': 1 if faction == 0 else -1,
        'flash': 0.0, 'step': rnd.uniform(0, 6.28),
        'dead': False, 'dead_t': 0.0,
    })


def _fire_mech_shell(s, me):
    rnd = s['rnd']
    mx = me['x'] + me['facing'] * 4
    my = me['y'] - 10
    target = None
    for sol in s['soldiers']:
        if sol['dead'] or sol['faction'] == me['faction']:
            continue
        if abs(sol['x'] - me['x']) < 55:
            target = sol
            break
    if target is None:
        for tk in s['tanks']:
            if tk['dead'] or tk['faction'] == me['faction']:
                continue
            if abs(tk['x'] - me['x']) < 55:
                target = tk
                break
    if target is None:
        for o in s['mechs']:
            if o is me or o['faction'] == me['faction']:
                continue
            if abs(o['x'] - me['x']) < 55:
                target = o
                break
    if target is None:
        return
    tt = rnd.uniform(0.5, 0.75)
    g = 18.0
    ty = target['y'] - (6 if target.get('kind') == 'mech' else 2)
    s['shells'].append({
        'x': mx, 'y': my, 'px': mx, 'py': my,
        'vx': (target['x'] - mx) / tt,
        'vy': (ty - my) / tt - 0.5 * g * tt,
        'g': g, 'faction': me['faction'], 'dmg': 3,
    })
    me['flash'] = 0.16
    _sfx('shot', mx, 1.3)
    for _ in range(3):
        s['smoke'].append({'x': mx + rnd.uniform(-0.8, 0.8), 'y': my,
                           'vx': rnd.uniform(-1.0, 1.0), 'vy': -rnd.uniform(0.5, 1.5),
                           'age': 0.0, 'life': rnd.uniform(0.3, 0.6)})


def _destroy_mech(s, me):
    rnd = s['rnd']
    me['dead'] = True
    me['dead_t'] = 0.0
    s['wrecks'].append({'x': me['x'], 'y': me['y'],
                        'faction': me['faction'], 'age': 0.0,
                        'life': rnd.uniform(5, 7)})
    if len(s['wrecks']) > 6:
        s['wrecks'].pop(0)
    s['explosions'].append({'x': me['x'], 'y': me['y'] - 8, 'age': 0.0,
                            'life': 1.0, 'radius_max': 13.0})
    s['shockwaves'].append({'x': me['x'], 'y': me['y'] - 4, 'age': 0.0,
                            'life': 0.9, 'radius_max': 16.0})
    _add_crater(s, me['x'], me['y'] + 2, 4)
    for _ in range(14):
        a = rnd.uniform(0, 6.283)
        sp = rnd.uniform(2, 14)
        s['debris'].append({'x': me['x'], 'y': me['y'] - 8,
                            'vx': math.cos(a) * sp, 'vy': math.sin(a) * sp - 8,
                            'age': 0.0, 'life': rnd.uniform(0.5, 1.4),
                            'hue': 0.07, 'hot': rnd.random() < 0.5})
    for _ in range(6):
        s['smoke'].append({'x': me['x'] + rnd.uniform(-4, 4), 'y': me['y'] - 8,
                           'vx': rnd.uniform(-0.6, 0.6), 'vy': -rnd.uniform(1.5, 4.5),
                           'age': 0.0, 'life': rnd.uniform(1.4, 2.6)})
    _blast_soldiers(s, me['x'], me['y'] - 4, 9.0)
    _ragdoll_burst(s, me['x'], me['y'] - 6, 7, FACTION_HUE[me['faction']],
                   spread=18.0, rise=16.0)


def _update_mechs(s, dt):
    rnd = s['rnd']
    W = s['gw']
    keep = []
    for me in s['mechs']:
        if me['dead']:
            me['dead_t'] += dt
            if me['dead_t'] > 7.0:
                continue
            keep.append(me)
            continue
        me['flash'] = max(0.0, me['flash'] - dt)
        me['step'] += dt * 6
        fac = me['faction']
        dirv = 1 if fac == 0 else -1
        for sol in s['soldiers']:
            if sol['dead'] or sol['faction'] == fac:
                continue
            if abs(sol['x'] - me['x']) < 2.2:
                _kill(s, sol, dirv * rnd.uniform(2, 4), -4)
                break
        if me['state'] == 'advance':
            tx = s['front'][fac]
            if abs(me['x'] - tx) < 2.0:
                me['state'] = 'hold'
                me['target_x'] = me['x']
            else:
                me['x'] += dirv * 2.0 * dt
        me['x'] = max(6.0, min(W - 6.0, me['x']))
        if me['state'] == 'hold':
            me['fire_t'] -= dt
            if me['fire_t'] <= 0:
                _fire_mech_shell(s, me)
                me['fire_t'] = rnd.uniform(2.6, 4.2)
        keep.append(me)
    s['mechs'] = keep


def _render_mech(hr, me, t, w, h, cam):
    if me['dead']:
        return
    x, y = int(me['x'] - cam), int(me['y'])
    hue = FACTION_HUE[me['faction']]
    fac = me['facing']
    if me['flash'] > 0:
        body = Color(255, 255, 255)
        panel = Color(255, 235, 200)
    else:
        body = Color.from_hsv(hue, 0.7, 0.5)
        panel = Color.from_hsv(hue, 0.55, 0.34)
    dark = Color(22, 22, 26)
    steel = Color(140, 142, 156)
    stride = 1 if int(me['step'] * 1.5) % 2 else 0
    fx = x - 3 + stride
    bx = x + 3 - stride
    for dx in range(-1, 2):
        hr.set_pixel(fx + dx, y - 1, '▄', fg=dark, z=28)
        hr.set_pixel(bx + dx, y - 1, '▄', fg=dark, z=28)
    for yy in range(2, 5):
        hr.set_pixel(fx, y - yy, '║', fg=steel, z=28)
        hr.set_pixel(bx, y - yy, '║', fg=steel, z=28)
    for dx in range(-4, 5):
        hr.set_pixel(x + dx, y - 5, '▄', fg=panel, z=28)
    for yy in range(6, 10):
        for dx in range(-3, 4):
            hr.set_pixel(x + dx, y - yy, '▄', fg=body, z=28)
    eng = 0.6 + 0.4 * math.sin(t * 5 + me['step'])
    hr.set_pixel(x, y - 7, '█', fg=Color.from_hsv(0.55, 0.9, eng), z=29)
    hr.set_pixel(x - 4, y - 10, '▄', fg=panel, z=28)
    hr.set_pixel(x + 4, y - 10, '▄', fg=panel, z=28)
    hr.set_pixel(x - 5, y - 10, '▄', fg=body, z=28)
    hr.set_pixel(x + 5, y - 10, '▄', fg=body, z=28)
    hr.set_pixel(x, y - 10, '█', fg=steel, z=28)
    hr.set_pixel(x, y - 11, '·', fg=Color(255, 90, 60), z=27)
    for b in (-4, 4):
        hr.set_pixel(x + b + fac, y - 9, '▄', fg=steel, z=29)
        hr.set_pixel(x + b + fac * 2, y - 9, '▄', fg=Color(105, 107, 120), z=29)
    for k in range(1, 4):
        hr.set_pixel(x + fac * (2 + k), y - 8, '▄',
                     fg=Color(190 + k * 8, 192 + k * 8, 204 + k * 8), z=29)
    if me['flash'] > 0:
        bx = x + fac * 6
        by = y - 8
        hr.set_pixel(bx, by, '▓', fg=Color(255, 255, 230), z=46)
        hr.set_pixel(bx + fac, by, '▓', fg=Color(255, 220, 140), z=46)
        hr.set_pixel(bx + fac * 2, by, '░', fg=Color(255, 180, 90), z=45)
        hr.set_pixel(bx, by - 1, '░', fg=Color(255, 170, 80), z=45)


def _fire_beam(s, ms):
    rnd = s['rnd']
    gy = s['gy']
    cands = [sol for sol in s['soldiers'] if not sol['dead'] and sol['faction'] != ms['faction']]
    if cands:
        tgt = rnd.choice(cands)
        bx = tgt['x'] + rnd.uniform(-2, 2)
    else:
        bx = rnd.uniform(20, s['gw'] - 20)
    s['beams'].append({'x': bx, 'y0': ms['y'], 'y1': gy, 'age': 0.0,
                       'life': 0.16})
    for sol in s['soldiers']:
        if sol['dead'] or sol['faction'] == ms['faction']:
            continue
        if abs(sol['x'] - bx) < 2.0 and sol['y'] >= ms['y']:
            _kill(s, sol, rnd.uniform(-3, 3), -2, killer=ms['faction'])
    for tk in s['tanks']:
        if not tk['dead'] and tk['faction'] != ms['faction'] and abs(tk['x'] - bx) < 3.0:
            tk['hp'] -= 1
            if tk['hp'] <= 0:
                _destroy_tank(s, tk)
    for me in s['mechs']:
        if not me['dead'] and me['faction'] != ms['faction'] and abs(me['x'] - bx) < 3.0:
            me['hp'] -= 2
            me['flash'] = 0.15
            if me['hp'] <= 0:
                _destroy_mech(s, me)
    s['explosions'].append({'x': bx, 'y': gy - 1, 'age': 0.0,
                            'life': 0.4, 'radius_max': 7.0})
    s['shockwaves'].append({'x': bx, 'y': gy - 1, 'age': 0.0,
                            'life': 0.5, 'radius_max': 9.0})
    s['craters'].append({'x': bx, 'y': gy, 'r': 3})
    for _ in range(4):
        s['debris'].append({'x': bx, 'y': gy - 2,
                            'vx': rnd.uniform(-3, 3), 'vy': -rnd.uniform(2, 6),
                            'age': 0.0, 'life': rnd.uniform(0.4, 0.9),
                            'hue': 0.07, 'hot': rnd.random() < 0.6})


def _update_beams(s, dt):
    for bm in s['beams']:
        bm['age'] += dt
    s['beams'] = [bm for bm in s['beams'] if bm['age'] < bm['life']]


def _destroy_mother(s, ms):
    rnd = s['rnd']
    ms['crash'] = True
    ms['crash_v'] = 0.6
    ms['bail_t'] = 0.0
    s['explosions'].append({'x': ms['x'], 'y': ms['y'], 'age': 0.0,
                            'life': 1.4, 'radius_max': 18.0})
    s['shockwaves'].append({'x': ms['x'], 'y': ms['y'], 'age': 0.0,
                            'life': 1.0, 'radius_max': 26.0})
    for _ in range(14):
        a = rnd.uniform(0, 6.283)
        sp = rnd.uniform(4, 18)
        s['debris'].append({'x': ms['x'], 'y': ms['y'],
                            'vx': math.cos(a) * sp, 'vy': math.sin(a) * sp - 6,
                            'age': 0.0, 'life': rnd.uniform(0.8, 2.0),
                            'hue': 0.07, 'hot': rnd.random() < 0.6})
    for _ in range(10):
        s['smoke'].append({'x': ms['x'] + rnd.uniform(-6, 6), 'y': ms['y'] + rnd.uniform(-2, 4),
                           'vx': rnd.uniform(-0.8, 0.8), 'vy': -rnd.uniform(1, 4),
                           'age': 0.0, 'life': rnd.uniform(1.5, 3.0)})


def _update_mothers(s, dt, w, h):
    rnd = s['rnd']
    gy = s['gy']
    mid = (s['front'][0] + s['front'][1]) / 2.0
    keep = []
    for ms in s['mothers']:
        ms['age'] += dt
        if ms.get('crash'):
            # burning wreck falls out of the sky; crew bails out on the way down
            ms['crash_v'] += 17 * dt
            ms['y'] += ms['crash_v'] * dt
            ms['x'] += ms['vx'] * 0.3 * dt
            ms['bail_t'] -= dt
            if ms['y'] < gy - 14 and ms['bail_t'] <= 0:
                ms['bail_t'] = 0.9
                _spawn_chute(s, {'faction': ms['faction'],
                                 'x': ms['x'] + rnd.uniform(-5, 5),
                                 'y': ms['y'] + 2})
            for _ in range(2):
                s['smoke'].append({'x': ms['x'] + rnd.uniform(-6, 6), 'y': ms['y'],
                                   'vx': rnd.uniform(-1.5, 1.5),
                                   'vy': -rnd.uniform(1, 3.5),
                                   'age': 0.0, 'life': rnd.uniform(0.8, 1.8)})
            if rnd.random() < 0.5:
                s['debris'].append({'x': ms['x'] + rnd.uniform(-5, 5), 'y': ms['y'],
                                    'vx': rnd.uniform(-4, 4),
                                    'vy': rnd.uniform(-2, 3),
                                    'age': 0.0, 'life': rnd.uniform(0.5, 1.2),
                                    'hue': 0.07, 'hot': True})
            if ms['y'] >= gy - 2:
                _explode(s, ms['x'], gy - 1, 7.0, True)
                _add_crater(s, ms['x'], gy, 5)
                _ragdoll_burst(s, ms['x'], gy - 3, 12, FACTION_HUE[ms['faction']],
                               spread=26.0, rise=20.0)
                _blast_soldiers(s, ms['x'], gy - 1, 24.0)
                ms['dead'] = True
                continue
            keep.append(ms)
            continue
        if ms['age'] > 5 and ms['hp'] < 260:
            ms['hp'] = min(260.0, ms['hp'] + 1.0 * dt)
        ms['x'] += ms['vx'] * dt
        ms['y'] = h * 0.07 + math.sin(ms['age'] * 0.4) * 1.5
        if not ms['retire']:
            if ms['x'] < mid - w * 0.85:
                ms['vx'] = abs(ms['vx'])
            elif ms['x'] > mid + w * 0.85:
                ms['vx'] = -abs(ms['vx'])
            if ms['age'] > 26:
                ms['retire'] = True
                ms['vx'] = (1 if ms['x'] < mid else -1) * 22.0
        ms['beam_t'] -= dt
        if ms['beam_t'] <= 0 and not ms['retire']:
            ms['beam_t'] = rnd.uniform(2.5, 4.5)
            _fire_beam(s, ms)
        foe, fd = None, 1e9
        for p in s['planes']:
            if p['crash'] or p['kind'] != 'fighter':
                continue
            d = math.hypot(p['x'] - ms['x'], (p['y'] - ms['y']) * 2)
            if d < fd:
                fd, foe = d, p
        if foe and fd < 30:
            ms['aat_t'] -= dt
            if ms['aat_t'] <= 0:
                ms['aat_t'] = 0.45
                _fire_air(s, ms, foe)
        if ms['hp'] <= 0 and not ms['dead']:
            _destroy_mother(s, ms)
            keep.append(ms)
            continue
        if ms['x'] < mid - w * 2 or ms['x'] > mid + w * 2:
            continue
        keep.append(ms)
    s['mothers'] = keep


def _spawn_zeppelin(s, w, h):
    rnd = s['rnd']
    faction = rnd.randint(0, 1)
    fac = 1 if faction == 0 else -1
    s['zeppelins'].append({
        'kind': 'zeppelin', 'faction': faction,
        'x': s['gw'] * 0.5 + fac * rnd.uniform(w * 0.25, w * 0.35),
        'y': h * 0.10 + rnd.uniform(-h * 0.03, h * 0.03),
        'vx': fac * rnd.uniform(1.2, 1.8),
        'hp': 130, 'drop_t': rnd.uniform(1.2, 2.4),
        'aat_t': 0.0, 'flash': 0.0, 'age': 0.0,
        'retire': False, 'dead': False,
    })


def _zepp_drop(s, z, w):
    rnd = s['rnd']
    target = None
    for sol in s['soldiers']:
        if sol['dead'] or sol['faction'] == z['faction']:
            continue
        if abs(sol['x'] - z['x']) < w * 0.4:
            target = sol
            break
    if target is None:
        for tk in s['tanks']:
            if tk['dead'] or tk['faction'] == z['faction']:
                continue
            if abs(tk['x'] - z['x']) < w * 0.4:
                target = tk
                break
    if target is None:
        for me in s['mechs']:
            if me['faction'] == z['faction']:
                continue
            if abs(me['x'] - z['x']) < w * 0.4:
                target = me
                break
    bx = z['x'] + (target['x'] - z['x']) * 0.4 if target else z['x']
    s['bombs'].append({
        'x': bx, 'y': z['y'] + 2, 'vx': rnd.uniform(-1.5, 1.5),
        'vy': 0.0, 'flame': rnd.uniform(0, 6.28),
    })


def _destroy_zeppelin(s, z):
    rnd = s['rnd']
    z['crash'] = True
    z['crash_v'] = 0.8
    z['bail_t'] = 0.0
    s['explosions'].append({'x': z['x'], 'y': z['y'], 'age': 0.0,
                            'life': 1.6, 'radius_max': 22.0})
    s['shockwaves'].append({'x': z['x'], 'y': z['y'], 'age': 0.0,
                            'life': 1.1, 'radius_max': 30.0})
    for _ in range(20):
        a = rnd.uniform(0, 6.283)
        sp = rnd.uniform(4, 20)
        s['debris'].append({'x': z['x'], 'y': z['y'],
                            'vx': math.cos(a) * sp, 'vy': math.sin(a) * sp - 8,
                            'age': 0.0, 'life': rnd.uniform(0.9, 2.2),
                            'hue': 0.07, 'hot': rnd.random() < 0.6})
    for _ in range(14):
        s['smoke'].append({'x': z['x'] + rnd.uniform(-10, 10), 'y': z['y'] + rnd.uniform(-3, 3),
                           'vx': rnd.uniform(-1.5, 1.5), 'vy': -rnd.uniform(1, 4.5),
                           'age': 0.0, 'life': rnd.uniform(1.5, 3.5)})


def _update_zeppelins(s, dt, w, h):
    rnd = s['rnd']
    mid = (s['front'][0] + s['front'][1]) / 2.0
    keep = []
    for z in s['zeppelins']:
        if z['dead']:
            z['age'] += dt
            if z['age'] > 1.0:
                continue
            keep.append(z)
            continue
        if z.get('crash'):
            # burning airship sinks out of the sky; crew bails out on the way
            z['crash_v'] += 15 * dt
            z['y'] += z['crash_v'] * dt
            z['x'] += z['vx'] * 0.25 * dt
            z['bail_t'] -= dt
            if z['y'] < s['gy'] - 12 and z['bail_t'] <= 0:
                z['bail_t'] = 0.6
                _spawn_chute(s, {'faction': z['faction'],
                                 'x': z['x'] + rnd.uniform(-6, 6),
                                 'y': z['y'] + 2})
            for _ in range(2):
                s['smoke'].append({'x': z['x'] + rnd.uniform(-8, 8), 'y': z['y'],
                                   'vx': rnd.uniform(-1.5, 1.5),
                                   'vy': -rnd.uniform(1, 3.5),
                                   'age': 0.0, 'life': rnd.uniform(0.8, 1.8)})
            if rnd.random() < 0.5:
                s['debris'].append({'x': z['x'] + rnd.uniform(-6, 6), 'y': z['y'],
                                    'vx': rnd.uniform(-4, 4),
                                    'vy': rnd.uniform(-2, 3),
                                    'age': 0.0, 'life': rnd.uniform(0.5, 1.2),
                                    'hue': 0.07, 'hot': True})
            if z['y'] >= s['gy'] - 2:
                _explode(s, z['x'], s['gy'] - 1, 7.5, True)
                _add_crater(s, z['x'], s['gy'], 5)
                _ragdoll_burst(s, z['x'], s['gy'] - 3, 14, FACTION_HUE[z['faction']],
                               spread=30.0, rise=22.0)
                _blast_soldiers(s, z['x'], s['gy'] - 1, 24.0)
                z['dead'] = True
                continue
            keep.append(z)
            continue
        z['flash'] = max(0.0, z['flash'] - dt)
        z['age'] += dt
        if z['age'] > 5 and z['hp'] < 130:
            z['hp'] = min(130.0, z['hp'] + 0.8 * dt)
        z['x'] += z['vx'] * dt
        z['y'] = h * 0.10 + math.sin(z['age'] * 0.6) * 1.2
        if not z['retire']:
            if z['x'] < mid - w * 0.7:
                z['vx'] = abs(z['vx'])
            elif z['x'] > mid + w * 0.7:
                z['vx'] = -abs(z['vx'])
            if z['age'] > 55:
                if z['hp'] <= 5:
                    _destroy_zeppelin(s, z)
                else:
                    z['retire'] = True
                    z['vx'] = (1 if z['x'] < mid else -1) * 16.0
        z['drop_t'] -= dt
        if z['drop_t'] <= 0 and not z['retire']:
            z['drop_t'] = rnd.uniform(3.0, 5.0)
            _zepp_drop(s, z, w)
        foe, fd = None, 1e9
        for p in s['planes']:
            if p['crash'] or p['kind'] != 'fighter':
                continue
            d = math.hypot(p['x'] - z['x'], (p['y'] - z['y']) * 2)
            if d < fd:
                fd, foe = d, p
        if foe and fd < 26:
            z['aat_t'] -= dt
            if z['aat_t'] <= 0:
                z['aat_t'] = 0.5
                _fire_air(s, z, foe)
        if z['hp'] <= 0 and not z['dead']:
            _destroy_zeppelin(s, z)
            keep.append(z)
            continue
        if z['x'] < mid - w * 2 or z['x'] > mid + w * 2:
            continue
        keep.append(z)
    s['zeppelins'] = keep


def _render_zeppelin(hr, z, t, w, h, cam):
    if z['dead']:
        return
    x, y = int(z['x'] - cam), int(z['y'])
    hue = FACTION_HUE[z['faction']]
    yy = int(round(math.sin(t * 1.3 + z['age'] * 1.3) * 0.6))
    if z['flash'] > 0:
        hull = Color(255, 255, 255)
    else:
        hull = Color.from_hsv(hue, 0.55, 0.5)
    dark = Color.from_hsv(hue, 0.6, 0.28)
    steel = Color(92, 94, 106)
    spot = 0.5 + 0.5 * math.sin(t * 2 + z['age'])
    for dx in range(-2, 3):
        hr.set_pixel(x + dx, y - 8 + yy, '▄', fg=dark, z=38)
    for dx in range(-5, 6):
        hr.set_pixel(x + dx, y - 7 + yy, '▄', fg=hull, z=38)
    for dx in range(-8, 9):
        hr.set_pixel(x + dx, y - 6 + yy, '▄', fg=hull, z=38)
    for dx in range(-10, 11):
        hr.set_pixel(x + dx, y - 5 + yy, '▄', fg=hull, z=38)
        hr.set_pixel(x + dx, y - 4 + yy, '▄', fg=hull, z=38)
    hr.set_pixel(x - 11, y - 4 + yy, '▄', fg=dark, z=38)
    hr.set_pixel(x + 10, y - 4 + yy, '▄', fg=dark, z=38)
    for dx in range(-9, 10):
        hr.set_pixel(x + dx, y - 3 + yy, '▄', fg=dark, z=38)
    for px in (-7, -3, 1, 5):
        hr.set_pixel(x + px, y - 5 + yy, '░', fg=dark, z=39)
    hr.set_pixel(x, y - 6 + yy, '·',
                 fg=Color.from_hsv(0.14, 0.9, 0.5 + 0.5 * spot), z=40)
    for dx in range(-5, 6):
        hr.set_pixel(x + dx, y - 2 + yy, '▄', fg=steel, z=39)
    d = -1 if z['vx'] < 0 else 1
    for k in (0, 1):
        hr.set_pixel(x - d * (9 + k), y - 4 + yy + (1 if k else 0), '▄', fg=steel, z=38)
        hr.set_pixel(x - d * (9 + k), y - 5 + yy - (1 if k else 0), '▄', fg=steel, z=38)
    for b in (-8, 8):
        hr.set_pixel(x + b, y - 1 + yy, '▓',
                     fg=Color.from_hsv(0.07, 1, 0.45 + 0.55 * spot), z=40)


def _ragdoll_burst(s, x, y, n, hue, spread=16.0, rise=10.0):
    """Blow a unit apart: heavy tumbling chunks that fly, spin and bounce."""
    rnd = s['rnd']
    gy = s['gy']
    for _ in range(n):
        a = rnd.uniform(0, 6.283)
        sp = rnd.uniform(3, spread)
        s['ragdolls'].append({
            'x': x, 'y': y,
            'vx': math.cos(a) * sp,
            'vy': math.sin(a) * sp - rise,
            'rot': rnd.uniform(0, 6.283),
            'vrot': rnd.uniform(-9, 9),
            'glyph': rnd.choice(['▄', '█', '░', '▒', '▓', '▀']),
            'fg': Color.from_hsv(hue, 0.75, 0.62).mul(rnd.uniform(0.75, 1.0))
                 if hue is not None else Color(70, 70, 82),
            'life': rnd.uniform(1.4, 2.8),
            'age': 0.0,
        })
        if len(s['ragdolls']) > 90:
            s['ragdolls'].pop(0)


def _update_ragdolls(s, dt):
    rnd = s['rnd']
    gy = s['gy']
    keep = []
    for rp in s['ragdolls']:
        rp['age'] += dt
        rp['vy'] += 46 * dt
        rp['vrot'] *= max(0.0, 1 - 0.8 * dt)
        rp['x'] += rp['vx'] * dt
        rp['y'] += rp['vy'] * dt
        rp['rot'] += rp['vrot'] * dt
        if rp['y'] >= gy - 1:
            rp['y'] = gy - 1
            if rp['vy'] > 4:
                rp['vy'] = -abs(rp['vy']) * 0.38
                rp['vx'] *= 0.55
                for _ in range(1):
                    s['smoke'].append({'x': rp['x'], 'y': rp['y'],
                                       'vx': rnd.uniform(-0.5, 0.5),
                                       'vy': -rnd.uniform(0.5, 1.4),
                                       'age': 0.0, 'life': rnd.uniform(0.4, 0.9)})
            else:
                rp['vy'] = 0.0
                rp['vx'] *= max(0.0, 1 - 2.0 * dt)
        if rp['age'] >= rp['life']:
            continue
        keep.append(rp)
    s['ragdolls'] = keep


def _render_ragdoll(hr, rp, t, w, h, cam):
    x, y = int(rp['x'] - cam), int(rp['y'])
    if 0 <= x < w and 0 <= y < h:
        k = int(rp['rot'] * 3.0) % 6
        ch = ['▄', '█', '░', '▒', '▓', '▀'][k]
        fade = max(0.25, 1.0 - rp['age'] / rp['life'])
        hr.set_pixel(x, y, ch, fg=rp['fg'].mul(fade), z=20)


def _update_wrecks(s, dt):
    for wk in s['wrecks']:
        wk['age'] += dt
    s['wrecks'] = [wk for wk in s['wrecks'] if wk['age'] < wk['life']]


def _update_flak(s, dt):
    for f in s['flak']:
        f['age'] += dt
    s['flak'] = [f for f in s['flak'] if f['age'] < f['life']]


def _update_far_falls(s, dt):
    """Very-background skyscrapers occasionally fall (not destroyed)."""
    rnd = s['rnd']
    for b in s['buildings']:
        if b['kind'] != 'far' or b['gone'] or b['falling'] is None:
            continue
        b['falling'] = min(1.0, b['falling'] + dt / b['fall_dur'])
        rows = b['h'] * (1.0 - b['falling'])
        front = b['base'] - rows
        if rows > 0.5:
            for _ in range(2):
                s['smoke'].append({'x': b['x'] + rnd.uniform(0, b['w']),
                                   'y': front * 2 + rnd.uniform(-1, 2),
                                   'vx': rnd.uniform(-1.0, 1.0),
                                   'vy': rnd.uniform(-0.8, 0.8),
                                   'age': 0.0, 'life': rnd.uniform(0.8, 1.8),
                                   'dust': True})
        if b['falling'] >= 1.0:
            b['gone'] = True
            b['falling'] = None
            for _ in range(6):
                s['smoke'].append({'x': b['x'] + rnd.uniform(-1, b['w'] + 1),
                                   'y': (b['base'] - 1) * 2 + rnd.uniform(-2, 2),
                                   'vx': rnd.uniform(-2.5, 2.5),
                                   'vy': -rnd.uniform(0.5, 2.5),
                                   'age': 0.0, 'life': rnd.uniform(1.2, 2.6),
                                   'dust': True})
    if s['fall_t'] > 1e8:
        return
    s['fall_t'] -= dt
    if s['fall_t'] > 0:
        return
    far = [b for b in s['buildings'] if b['kind'] == 'far'
           and not b['gone'] and b['falling'] is None]
    if not far:
        s['fall_t'] = 1e8
        return
    weight = [b['h'] for b in far]
    b = rnd.choices(far, weights=weight)[0]
    b['falling'] = 0.0
    b['fall_dur'] = rnd.uniform(1.8, 3.0)
    s['fall_t'] = rnd.uniform(25, 45)
    # foreshadow: a faint crack of dust at the top
    ax = b['x'] + b['w'] // 2
    for _ in range(2):
        s['smoke'].append({'x': ax + rnd.uniform(-2, 2),
                           'y': (b['base'] - b['h']) * 2 + rnd.uniform(-2, 2),
                           'vx': rnd.uniform(-1.5, 1.5), 'vy': -rnd.uniform(0.5, 1.5),
                           'age': 0.0, 'life': rnd.uniform(1.0, 1.6),
                           'dust': True})


def _start_tip(s, b):
    """A heavily damaged skyline topples sideways onto the battlefield."""
    if b.get('tip', 0) or b.get('collapsed'):
        return
    rnd = s['rnd']
    b['tip_dir'] = 1 if (b['x'] + b['w'] * 0.5) < s['mid'] else -1
    b['tip_v'] = rnd.uniform(0.25, 0.45)
    b['tip'] = 0.002
    b['crushed'] = False


def _update_collapses(s, dt):
    """Animate toppling buildings - messy dust, debris and crushed soldiers."""
    rnd = s['rnd']
    gy = s['gy']
    for b in s['buildings']:
        if b.get('collapsed') or not b.get('tip'):
            continue
        b['tip'] = min(1.0, b['tip'] + b['tip_v'] * dt)
        b['tip_v'] += 2.4 * dt
        a = b['tip'] * math.pi / 2.0
        piv = b['x'] if b['tip_dir'] > 0 else b['x'] + b['w']
        if rnd.random() < dt * 14:
            s['smoke'].append({'x': piv + rnd.uniform(-2, 2),
                               'y': (b['base'] - 1) * 2 + rnd.uniform(-2, 2),
                               'vx': rnd.uniform(-2.0, 2.0),
                               'vy': -rnd.uniform(0.5, 2.5),
                               'age': 0.0, 'life': rnd.uniform(0.8, 1.8),
                               'dust': True})
            s['debris'].append({'x': piv + rnd.uniform(-2, 2),
                                'y': (b['base'] - 1) * 2,
                                'vx': rnd.uniform(-3.5, 3.5),
                                'vy': -rnd.uniform(1, 4),
                                'age': 0.0, 'life': rnd.uniform(0.4, 1.0),
                                'hue': 0.08, 'hot': False})
        if b['tip'] > 0.15 and not b['crushed']:
            ext = abs(math.cos(a)) * b['w'] + abs(math.sin(a)) * b['h']
            if b['tip_dir'] > 0:
                lo, hi = b['x'] - 1.0, b['x'] + ext + 1.0
            else:
                lo, hi = b['x'] + b['w'] - ext - 1.0, b['x'] + b['w'] + 1.0
            for sol in s['soldiers']:
                if not sol['dead'] and lo <= sol['x'] <= hi and sol['y'] >= gy - 8:
                    _kill(s, sol, rnd.uniform(-2, 2) * b['tip_dir'],
                          rnd.uniform(-6, -2))
                    _impact(s, sol['x'], sol['y'], sol['faction'])
            b['crushed'] = True
        if b['tip'] >= 1.0:
            b['collapsed'] = True
            b['damage'] = 1.0
            for _ in range(6):
                s['smoke'].append({'x': b['x'] + rnd.uniform(-1, b['w'] + 1),
                                   'y': (b['base'] - 1) * 2 + rnd.uniform(-2, 2),
                                   'vx': rnd.uniform(-2.5, 2.5),
                                   'vy': -rnd.uniform(0.5, 2.5),
                                   'age': 0.0, 'life': rnd.uniform(1.2, 2.6),
                                   'dust': True})


def _damage_structures(s, x, y, strength):
    rnd = s['rnd']
    for b in s['buildings']:
        if b['kind'] == 'far' or b.get('collapsed') or b.get('tip', 0):
            continue
        cy = y / 2.0
        if abs(x - (b['x'] + b['w'] / 2.0)) < 5 + strength * 1.2 and cy > b['base'] - b['h'] - 2:
            b['damage'] = min(1.0, b['damage'] + strength * 0.0039)
            if b['kind'] == 'skyline':
                if not b['fire'] and b['damage'] >= 0.5:
                    b['fire'] = True
                if b['damage'] >= 1.0 and rnd.random() < 0.75:
                    _start_tip(s, b)
    for bu in s['bunkers']:
        if abs(x - bu['x']) < 5 + strength * 1.2 and y > bu['base'] - 4:
            bu['damage'] = min(1.0, bu['damage'] + strength * 0.04)


def _add_crater(s, x, y, r):
    s['craters'].append({'x': x, 'y': min(s['gy'], y), 'r': r,
                         'a': s['rnd'].uniform(0, 6.283)})
    if len(s['craters']) > 90:
        s['craters'].pop(0)


def _explode(s, x, y, strength, ground=True):
    rnd = s['rnd']
    pt = s.get('pt')
    if pt is not None:
        pt.emit(x, y, 6 + int(strength * 8), PALETTES['fire'])
        pt.emit(x, y - 2, int(strength * 2),
                [Color(190, 192, 200), Color(140, 142, 150), Color(90, 92, 100)])
    if strength >= 1.5:
        s['shake_t'] = 1.1
        s['shake_p'] = min(3.5, 0.4 + strength * 0.8)
    if strength >= 2.6:
        s['flash_t'] = max(s['flash_t'], min(0.9, strength * 0.22))
    _sfx('boom', x, 1.0, strength)
    s['explosions'].append({'x': x, 'y': y, 'age': 0.0,
                            'life': 0.4 + strength * 0.24,
                            'radius_max': 2.0 + strength * 3.2})
    s['shockwaves'].append({'x': x, 'y': y, 'age': 0.0, 'life': 0.7,
                            'radius_max': 4.0 + strength * 5.0})
    for _ in range(int(strength * 8)):
        a = rnd.uniform(0, 6.283)
        sp = rnd.uniform(2, 10)
        s['debris'].append({'x': x, 'y': y, 'vx': math.cos(a) * sp,
                            'vy': math.sin(a) * sp - 5,
                            'age': 0.0, 'life': rnd.uniform(0.4, 1.1),
                            'hue': 0.07, 'hot': False})
    for _ in range(int(strength * 3)):
        a = rnd.uniform(0, 6.283)
        sp = rnd.uniform(1, 4)
        s['smoke'].append({'x': x + rnd.uniform(-2, 2), 'y': y + rnd.uniform(-3, 1),
                           'vx': math.cos(a) * sp, 'vy': -rnd.uniform(1.5, 5),
                           'age': 0.0, 'life': rnd.uniform(1.2, 2.8)})
    if ground:
        _add_crater(s, x, y + 2, 2 + strength)
    _blast_soldiers(s, x, y, 2.0 + strength * 3.2)
    for tk in s['tanks']:
        if tk['dead']:
            continue
        d = math.hypot(tk['x'] - x, (tk['y'] - y) * 2.0)
        if d < (2.0 + strength * 3.2) * 1.2:
            tk['hp'] -= 2 if d < 8.0 else 1
            if tk['hp'] <= 0:
                _destroy_tank(s, tk)
    for me in s['mechs']:
        if me['dead']:
            continue
        d = math.hypot(me['x'] - x, (me['y'] - y) * 2.0)
        if d < (2.0 + strength * 3.2) * 1.4:
            me['hp'] -= 2 if d < 10.0 else 1
            me['flash'] = 0.15
            if me['hp'] <= 0:
                _destroy_mech(s, me)
    for bd in s['builders']:
        if bd['dead']:
            continue
        d = math.hypot(bd['x'] - x, (bd['y'] - y) * 2.0)
        if d < (2.0 + strength * 3.2) * 1.3:
            bd['hp'] -= 2 if d < 8.0 else 1
            bd['flash'] = 0.15
            if bd['hp'] <= 0:
                _destroy_builder(s, bd)
    for sn in s['snipers']:
        if sn['dead']:
            continue
        d = math.hypot(sn['x'] - x, (sn['y'] - y) * 2.0)
        if d < (2.0 + strength * 3.2) * 1.4:
            sn['hp'] -= 3
            sn['flash'] = 0.18
            if sn['hp'] <= 0:
                _destroy_sniper(s, sn)
    _damage_structures(s, x, y, strength)


# ----------------------------------------------------------------------
# rendering
# ----------------------------------------------------------------------

def _render_missile(hr, m, w, h, cam):
    px, py = int(m['x'] - cam), int(m['y'])
    for i, (tx, ty) in enumerate(m['trail'][:-1]):
        sx, sy = int(tx - cam), ty
        f = i / max(1, len(m['trail']))
        if 0 <= sx < w and 0 <= sy < h:
            ch = '·' if f < 0.35 else '░'
            col = Color.from_hsv(m['hue'], m['sat'], 0.15 + f * 0.55)
            hr.set_pixel(sx, sy, ch, fg=col, z=38)
    if 0 <= px < w and 0 <= py < h:
        hr.set_pixel(px, py, '●', fg=Color(255, 255, 255), z=42)
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            col = Color.from_hsv(m['hue'], m['sat'], 0.45)
            hr.set_pixel(px + dx, py + dy, '·', fg=col, z=41)


def _render_soldier(hr, sol, w, h, cam):
    if sol['dead']:
        return
    x, y = int(sol['x'] - cam), int(sol['y'])
    hue = FACTION_HUE[sol['faction']]
    role = sol['role']
    fac = sol['facing']
    # no vertical bounce while marching: the old hard on/off toggle read as a
    # jittery "dip" (sprites dropping a line and snapping back), so sprites now
    # stand solidly on the ground line.
    bob = 0
    hy = int(round(sol.get('hop_y', 0.0)))
    y -= hy

    if sol['flash'] > 0:
        body = Color(255, 255, 255)
        head = Color(255, 255, 255)
    else:
        body = Color.from_hsv(hue, 0.85, 0.92)
        head = Color.from_hsv(hue, 0.55, 1.0)

    # tipping sprite forward slightly while a parkour runner is airborne
    airborne = (sol['jump'] and hy > 0)
    l_tilt = -1 if (airborne and int(sol['step'] * 4) % 2) else 0
    z = 20

    if role == 'gunner':
        # heavy support gun with a long barrel and ammo belt
        if sol['flash'] > 0:
            hr.set_pixel(x + fac * 3, y - 2 - bob, '●', fg=Color(255, 240, 160), z=46)
            hr.set_pixel(x + fac * 2, y - 2 - bob, '─', fg=Color(255, 240, 160), z=46)
        cells = [
            (0, -4, '█', head),
            (-2, -3, '▄', body), (0, -3, '▄', body), (2, -3, '▄', body),
            (-1, -3, '█', Color.from_hsv(hue, 0.7, 0.6)),
            (1, -3, '▄', Color.from_hsv(hue, 0.7, 0.6)),
            (fac * 2, -3, '─', Color.from_hsv(hue, 0.8, 0.7)),
            (fac * 3, -3, '─', Color.from_hsv(hue, 0.8, 0.7)),
            (-1, -2, '║', body), (0, -2, '▄', body), (1, -2, '║', body),
            (0, -1, '▄', body), (1, -1, '║', Color.from_hsv(hue, 0.6, 0.6)),
        ]
        for dx, dy, ch, col in cells:
            hr.set_pixel(x + dx, y + dy - bob, ch, fg=col, z=z)
        return

    if role == 'flame':
        # armoured firefighter with a bulky hose pipe on the shoulder
        pack = Color.from_hsv(0.05, 0.85, 0.5 + 0.4 * (0.5 + 0.5 * math.sin(sol['step'] * 2)))
        if sol['flash'] > 0:
            hr.set_pixel(x + fac * 2, y - 3 - bob, '●', fg=Color(255, 240, 160), z=46)
            hr.set_pixel(x + fac * 1, y - 3 - bob, '─', fg=Color(255, 240, 160), z=46)
        cells = [
            (0, -4, '█', head),
            (-2, -3, '▄', body), (0, -3, '▄', body), (2, -3, '▄', body),
            (-1, -3, '█', Color.from_hsv(hue, 0.7, 0.55)),
            (1, -3, '█', Color.from_hsv(hue, 0.7, 0.55)),
            (-2, -2, '║', body), (0, -2, '█', body), (2, -2, '║', body),
            (fac * 2, -2, '╮', pack), (fac * 3, -2, '─' if fac > 0 else '╯', pack),
            (0, -1, '▄', body),
        ]
        for dx, dy, ch, col in cells:
            hr.set_pixel(x + dx, y + dy - bob, ch, fg=col, z=z)
        return

    if role == 'laser':
        # sleek robot with a raised emitter eye
        metal = Color.from_hsv(hue, 0.5, 0.8)
        if sol['flash'] > 0:
            hr.set_pixel(x + fac * 2, y - 3 - bob, '°', fg=Color(255, 255, 255), z=46)
            hr.set_pixel(x + fac * 1, y - 3 - bob, '▮', fg=Color(255, 255, 255), z=46)
        cells = [
            (0, -4, '●', Color(190, 200, 210)),
            (-1, -3, '▄', metal), (0, -3, '▄', metal), (1, -3, '▄', metal),
            (0, -3, '°', Color.from_hsv(hue, 0.9, 1.0)),
            (-1, -2, '│', metal), (0, -2, '│', metal), (1, -2, '│', metal),
            (0, -1, '▄', Color.from_hsv(hue, 0.6, 0.55)),
        ]
        for dx, dy, ch, col in cells:
            hr.set_pixel(x + dx, y + dy - bob, ch, fg=col, z=z)
        return

    if role == 'cyborg':
        # elite special-ops cyborg: armoured, antenna, twin blurred cores
        core = 0.5 + 0.5 * math.sin(sol['step'] * 4)
        armour = Color.from_hsv(hue, 0.6, 0.75)
        if sol['flash'] > 0:
            hr.set_pixel(x + fac * 2, y - 3 - bob, '●', fg=Color(255, 255, 255), z=46)
            hr.set_pixel(x + fac * 1, y - 3 - bob, '·', fg=Color(255, 255, 255), z=46)
        hr.set_pixel(x, y - 5, '§' if core > 0.5 else '·',
                     fg=Color.from_hsv(0.12, 0.8, 0.5 + 0.5 * core), z=z)
        cells = [
            (0, -4, '▣', head),
            (-1, -3, '▄', armour), (0, -3, '▄', armour), (1, -3, '▄', armour),
            (0, -3, '◎', Color.from_hsv(0.12, 0.9, 0.9)),
            (-1, -2, '║', armour), (0, -2, '│', armour), (1, -2, '║', armour),
            (0, -1, '▄', Color(60, 60, 70)),
        ]
        for dx, dy, ch, col in cells:
            hr.set_pixel(x + dx, y + dy - bob, ch, fg=col, z=z)
        if sol['flash'] > 0:
            hr.set_pixel(x, y - 3 - bob, '◎', fg=Color(255, 255, 255), z=46)
        return

    if role == 'parkour':
        # lean, sprinting runner - low and fast, arms tucked
        if sol['flash'] > 0:
            hr.set_pixel(x + fac * 2, y - 2 - bob, '·', fg=Color(255, 240, 160), z=46)
        cells = [
            (0, -3 + l_tilt, '●', head),
            (fac * -1, -2 + l_tilt, '/', body), (0, -2 + l_tilt, '│', body),
            (fac, -1 + l_tilt, '╲' if fac > 0 else '╱', body),
            (fac * -1, -1 + l_tilt, '╱' if fac > 0 else '╲', body),
        ]
        for dx, dy, ch, col in cells:
            hr.set_pixel(x + dx, y + dy - bob, ch, fg=col, z=z)
        return

    if role == 'droid':
        # cheap chrome droid - flat angular frame with a single crimson slit
        metal = Color(190, 200, 205) if sol['flash'] == 0 else Color(255, 255, 255)
        slit = Color.from_hsv(hue, 0.9, 1.0)
        cells = [
            (0, -3, '▓', metal),
            (-1, -2, '▄', metal), (0, -2, '░', slit), (1, -2, '▄', metal),
            (0, -1, '▄', Color.from_hsv(hue, 0.6, 0.5)),
        ]
        for dx, dy, ch, col in cells:
            hr.set_pixel(x + dx, y + dy - bob, ch, fg=col, z=z)
        return

    # ---- classic attacker / defender silhouette -----------------------
    if sol['flash'] > 0:
        hr.set_pixel(x + fac * 2, y - 2 - bob, '●', fg=Color(255, 240, 160), z=46)
        hr.set_pixel(x + fac * 1, y - 2 - bob, '─', fg=Color(255, 240, 160), z=46)
    # both standing and crouched poses span the SAME rows (top at -3) so the
    # crouch toggle never makes the sprite sink a row toward the ground - a
    # discrete height change read as a glitchy "teleport down".
    if sol['crouch']:
        cells = [
            (0, -3, '●', head),
            (-1, -2, '/', body), (0, -2, '╲', body), (1, -2, '╱', body),
            (0, -1, '▄', body),
        ]
    else:
        cells = [
            (0, -3, '●', head),
            (-1, -2, '/', body), (0, -2, '│', body), (1, -2, '\\', body),
            (0, -1, '│', body),
        ]
    for dx, dy, ch, col in cells:
        hr.set_pixel(x + dx, y + dy - bob, ch, fg=col, z=z)


def _render_bunker(hr, bu, cam):
    x, base = int(bu['x'] - cam), int(bu['base'])
    dmg = min(1.0, bu['damage'])
    built = bu.get('built')
    for cell in bu['cells']:
        if cell['r'] < dmg * 0.9:
            continue
        dx, dy = cell['dx'], cell['dy']
        if cell['slit']:
            ch, col = '░', Color(15, 12, 9)
        elif built and (dx + dy) % 2 == 0:
            ch, col = '▓', Color.from_hsv(FACTION_HUE[bu['faction']], 0.55, 0.5)
        elif (dx + dy) % 2 == 0:
            ch, col = '▓', Color(96, 74, 44)
        elif built:
            ch, col = '▒', Color.from_hsv(FACTION_HUE[bu['faction']], 0.4, 0.36)
        else:
            ch, col = '▒', Color(70, 55, 33)
        hr.set_pixel(x + dx, base + dy, ch, fg=col, z=25)


def _render_chute(hr, ch, w, h, cam):
    x, y = int(ch['x'] - cam), int(ch['y'])
    hue = FACTION_HUE[ch['faction']]
    sw = int(math.sin(ch['sway']) * 1.2)
    hr.set_pixel(x - 1, y - 3, '▀', fg=Color.from_hsv(hue, 0.5, 0.7), z=38)
    hr.set_pixel(x, y - 3, '▀', fg=Color.from_hsv(hue, 0.6, 0.85), z=38)
    hr.set_pixel(x + 1, y - 3, '▀', fg=Color.from_hsv(hue, 0.5, 0.7), z=38)
    hr.set_pixel(x, y - 2, '·', fg=Color(210, 210, 210), z=37)
    hr.set_pixel(x, y - 1, '·', fg=Color(190, 190, 190), z=37)
    hr.set_pixel(x + sw, y, '▓', fg=Color.from_hsv(hue, 0.85, 0.92), z=37)


def _render_drone(hr, dr, t, w, h, cam):
    x, y = int(dr['x'] - cam), int(dr['y'])
    if dr.get('tiny'):
        if dr['hack']:
            gl = 0.5 + 0.5 * math.sin(t * 30)
            hr.set_pixel(x, y, '!' if gl > 0.6 else '▓',
                         fg=Color(255, 255, 120), z=31)
            return
        hue = FACTION_HUE[dr['faction']]
        bob = 0.5 + 0.5 * math.sin(t * 9 + dr['phase'])
        body = Color.from_hsv(hue, 0.85, 0.55 + 0.4 * bob)
        hr.set_pixel(x, y, '·', fg=body, z=29)
        fx = x + (-1 if bob < 0.5 else 1)
        hr.set_pixel(fx, y, '·', fg=Color(120, 120, 132), z=28)
        if dr['state'] == 'dive':
            gl = 0.5 + 0.5 * math.sin(t * 34)
            hr.set_pixel(x, y, '!' if gl > 0.5 else '·',
                         fg=Color(255, 140, 60), z=31)
        if dr['flash'] > 0:
            hr.set_pixel(x, y, '·', fg=Color(255, 255, 255), z=31)
        return
    if dr['hack']:
        gl = 0.5 + 0.5 * math.sin(t * 26)
        ch = '▓' if gl > 0.6 else '░'
        col = Color(200, 255, 200) if gl > 0.5 else Color(130, 130, 150)
        hr.set_pixel(x, y, ch, fg=col, z=31)
        hr.set_pixel(x, y - 1, '!', fg=Color(255, 255, 120), z=31)
        hr.set_pixel(x, y + 1, '▄', fg=col.mul(0.6), z=30)
        hr.set_pixel(x - 1, y, '·', fg=col.mul(0.5), z=29)
        hr.set_pixel(x + 1, y, '·', fg=col.mul(0.5), z=29)
        return
    hue = FACTION_HUE[dr['faction']]
    body = Color.from_hsv(hue, 0.85, 0.9)
    blink = 0.5 + 0.5 * math.sin(t * 7 + dr['phase'])
    rcol = Color(205, 205, 215) if blink > 0.5 else Color(95, 95, 105)
    hr.set_pixel(x - 1, y, '·', fg=rcol, z=29)
    hr.set_pixel(x + 1, y, '·', fg=rcol, z=29)
    hr.set_pixel(x, y - 1, '▀', fg=body, z=30)
    hr.set_pixel(x, y, '▓', fg=body, z=30)
    hr.set_pixel(x, y + 1, '▄', fg=Color.from_hsv(hue, 0.7, 0.5), z=30)
    if dr['flash'] > 0:
        hr.set_pixel(x, y, '▓', fg=Color(255, 255, 255), z=31)


def _render_hacker(hr, hk, t, w, h, cam):
    x, y = int(hk['x'] - cam), int(hk['y'])
    hue = FACTION_HUE[hk['faction']]
    locking = hk['lock'] is not None and hk['cd'] <= 0
    blink = 0.5 + 0.5 * math.sin(t * (16 if locking else 4) + hk['phase'] * 8)
    head = Color.from_hsv(hue, 0.55, 0.75)
    body = Color.from_hsv(hue, 0.35, 0.45)
    hr.set_pixel(x, y - 5, '·' if blink > 0.4 else ' ',
                 fg=Color(120, 255, 170) if locking else Color(150, 150, 160), z=23)
    hr.set_pixel(x, y - 4, '│', fg=Color(140, 140, 150), z=23)
    hr.set_pixel(x, y - 3, '●', fg=head, z=23)
    hr.set_pixel(x - 1, y - 2, '/', fg=body, z=23)
    hr.set_pixel(x, y - 2, '│', fg=body, z=23)
    hr.set_pixel(x + 1, y - 2, '\\', fg=body, z=23)
    hr.set_pixel(x, y - 1, '▄', fg=Color.from_hsv(hue, 0.6, 0.35), z=22)
    if hk['flash'] > 0:
        hr.set_pixel(x, y - 3, '●', fg=Color(255, 255, 255), z=24)


def _render_builder(hr, bd, t, w, h, cam):
    x, y = int(bd['x'] - cam), int(bd['y'])
    hue = FACTION_HUE[bd['faction']]
    if bd['flash'] > 0:
        body = Color(255, 255, 255)
    else:
        body = Color.from_hsv(hue, 0.5, 0.6)
    dark = Color.from_hsv(hue, 0.8, 0.4)
    hr.set_pixel(x, y - 4, '·', fg=Color(120, 255, 160) if bd['state'] == 'build'
                 else Color(95, 95, 105), z=21)
    hr.set_pixel(x, y - 3, '│', fg=Color(120, 120, 132), z=21)
    hr.set_pixel(x, y - 2, '▀', fg=body, z=21)
    hr.set_pixel(x - 1, y - 1, '▄', fg=body, z=21)
    hr.set_pixel(x, y - 1, '▄', fg=dark, z=21)
    hr.set_pixel(x + 1, y - 1, '▄', fg=body, z=21)
    if bd['state'] == 'build':
        a = bd['progress']
        pile = min(3, int(a * 3))
        for dy in range(pile):
            for dx in range(-2, 3):
                hr.set_pixel(x + dx, y - 1 - dy, '▒',
                             fg=Color.from_hsv(hue, 0.4, 0.4 + 0.15 * a), z=22)
        spark = 0.5 + 0.5 * math.sin(t * 24 + bd['phase'])
        hr.set_pixel(x + 2, y - 2, '·' if spark > 0.5 else '▓',
                     fg=Color(255, 240, 140), z=46)
        hr.set_pixel(x + 2, y - 1, '·', fg=Color(255, 180, 90), z=45)


def _render_pulse(hr, pl, w, h, cam):
    x1, y1 = int(pl['x1'] - cam), int(pl['y1'])
    x2, y2 = int(pl['x2'] - cam), int(pl['y2'])
    p = 1.0 - pl['age'] / pl['life']
    glitch = pl.get('hack')
    col = Color(150, 255, 170) if pl.get('lock') else Color(255, 225, 130)
    n = max(2, int(math.hypot(x2 - x1, y2 - y1) * 0.4))
    for i in range(n):
        f = i / n
        gx = int(x1 + (x2 - x1) * f + (math.sin(pl['age'] * 42 + i * 2.4) * 1.3 if glitch else 0))
        gy = int(y1 + (y2 - y1) * f)
        if 0 <= gx < w and 0 <= gy < h:
            hr.set_pixel(gx, gy, '┃' if (i + n // 2) % 2 else '·',
                         fg=col.mul(p * 0.85), z=48)
    if glitch and 0 <= x2 < w and 0 <= y2 < h:
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                hr.set_pixel(x2 + dx, y2 + dy, '▓' if p > 0.6 else '░',
                             fg=Color(210, 255, 210).mul(p), z=49)


def _render_corpse(hr, cp, w, h, cam):
    x, y = int(cp['x'] - cam), int(cp['y'])
    hue = FACTION_HUE[cp['faction']]
    if cp['state'] in ('fly', 'slide'):
        col = Color.from_hsv(hue, 0.7, 0.85)
        spin = int(cp['rot'] * 1.3) % 4
        ch = ['▓', '▄', '░', '▀'][spin]
        hr.set_pixel(x, y, ch, fg=col, z=15)
        lx = x + int(math.cos(cp['rot'] * 2.0) * 1.8)
        ly = y + int(math.sin(cp['rot'] * 1.6) * 1.1)
        hr.set_pixel(lx, ly, '·', fg=col.mul(0.55), z=14)
        hr.set_pixel(x - int(cp['vx'] * 0.1), y - int(cp['vy'] * 0.1),
                     '·', fg=col.mul(0.45), z=14)
    else:
        fade = min(1.0, (cp['life'] - cp['age']) / 1.4)
        if fade <= 0.1:
            return
        col = Color.from_hsv(hue, 0.6, 0.7 * fade)
        hr.set_pixel(x - 1, y, '─', fg=col, z=12)
        hr.set_pixel(x, y, '─', fg=col, z=12)
        hr.set_pixel(x + 1, y, '●', fg=col, z=12)


def _render_bullet(hr, b, w, h, cam):
    x, y = int(b['x'] - cam), int(b['y'])
    px, py = int(b['px'] - cam), int(b['py'])
    wtype = b.get('weapon', 'ball')
    col = Color(255, 235, 170) if b['faction'] == 0 else Color(255, 190, 120)
    if b.get('sniper'):
        hr.set_pixel(x, y, '█', fg=Color(255, 255, 255), z=46)
        if px != x or py != y:
            mx, my = (x + px) // 2, (y + py) // 2
            hr.set_pixel(mx, my, '▓', fg=Color(255, 250, 230), z=45)
            hr.set_pixel(px, py, '░', fg=Color(220, 215, 200), z=44)
        return
    if wtype == 'laser':
        lc = Color(140, 255, 255) if b['faction'] == 0 else Color(255, 90, 120)
        hr.set_pixel(x, y, '▮', fg=lc, z=46)
        if px != x or py != y:
            hr.set_pixel(px, py, '°', fg=Color(255, 255, 255), z=45)
        return
    if wtype == 'flame':
        fl = 0.5 + 0.5 * math.sin(px * 3.1 + py * 1.7)
        hot = _FIRE_G.at(0.2 + 0.8 * fl)
        hr.set_pixel(x, y, '°' if fl > 0.4 else '·', fg=hot, z=46)
        return
    hr.set_pixel(x, y, '─', fg=col, z=45)
    if px != x or py != y:
        mx, my = (x + px) // 2, (y + py) // 2
        hr.set_pixel(mx, my, '·', fg=col.mul(0.65), z=44)
        hr.set_pixel(px, py, '·', fg=col.mul(0.4), z=44)


def _render_buildings(c, s, c_h, c_w, t, cam, cy=0):
    for b in s['buildings']:
        bx0 = b['x'] - cam
        bx1 = bx0 + b['w']
        if bx1 < 0 or bx0 >= c_w:
            continue
        dmg = min(1.0, b['damage'])
        tear = int(dmg * b['h'] * 0.55)
        kind = b['kind']
        base = b['base']
        if kind == 'far':
            col = Color(74, 54, 40).mul(b.get('tint', 1.0))
            if b['gone']:
                rows = 1.5
            elif b['falling'] is not None:
                rows = b['h'] * (1.0 - b['falling'])
            else:
                rows = b['h']
            if rows < 0.5:
                continue
            top = base - int(rows)
        elif kind == 'ruin':
            col = Color(46, 38, 30).lerp(Color(16, 14, 14), dmg).mul(b.get('tint', 1.0))
            top = base - b['h'] + tear
        else:
            col = Color(36, 30, 32).lerp(Color(20, 18, 20), dmg).mul(b.get('tint', 1.0))
            top = base - b['h'] + tear
        if b.get('tip', 0) > 0 or b.get('collapsed'):
            a = min(1.0, b['tip']) * math.pi / 2.0
            ca, sa = math.cos(a), math.sin(a)
            if b['tip_dir'] > 0:
                piv = b['x']
                for xx, yy, hrnd in b['cells']:
                    dx = xx - piv
                    dy = base - yy
                    sx = int(round(piv + dx * ca + dy * sa - cam))
                    ry = int(round(base + dx * sa - dy * ca)) - cy
                    if 0 <= sx < c_w and 0 <= ry < c_h:
                        c.set_pixel(sx, ry, ' ', bg=col, z=2)
            else:
                piv = b['x'] + b['w']
                for xx, yy, hrnd in b['cells']:
                    rx = piv - xx
                    dy = base - yy
                    sx = int(round(piv - (rx * ca + dy * sa) - cam))
                    ry = int(round(base + rx * sa - dy * ca)) - cy
                    if 0 <= sx < c_w and 0 <= ry < c_h:
                        c.set_pixel(sx, ry, ' ', bg=col, z=2)
            continue
        for xx, yy, hrnd in b['cells']:
            if yy < top:
                continue
            if dmg > 0.4 and hrnd < (dmg - 0.25) * 0.55:
                continue
            if kind != 'far' and yy == top and b['teeth'][xx - b['x']] and dmg < 0.3:
                continue
            sx = xx - cam
            yy = yy - cy
            if yy < c_h and 0 <= sx < c_w:
                c.set_pixel(sx, yy, ' ', bg=col, z=2)
        if kind == 'far' or kind == 'skyline':
            if b['antenna']:
                ax = b['x'] + b['w'] // 2 - cam
                for ay in range(top - 3, top):
                    ay = ay - cy
                    if ay >= 0 and 0 <= ax < c_w:
                        c.set_pixel(ax, ay, ' ', bg=col, z=2)
            if b['roofbox']:
                rx0 = b['x'] + int((b['w'] - 2) * (0.5 + 0.5 * math.sin(b['seed'] * 3))) - cam
                for ryy in range(top - 1, top):
                    for rxx in range(rx0, min(c_w, rx0 + 2)):
                        if rxx >= 0 and ryy - cy >= 0:
                            c.set_pixel(rxx, ryy - cy, ' ', bg=col.mul(1.15), z=2)
        if kind == 'skyline' and b['fire'] and dmg < 0.85:
            fl = 0.5 + 0.5 * math.sin(t * 1.8 + b['seed'] * 2)
            if fl > 0.72:
                fxc = b['x'] + b['w'] // 2 + int(math.sin(t * 0.9 + b['seed'] * 7)) - cam
                if 0 <= fxc < c_w and top - 1 - cy >= 0:
                    c.set_pixel(fxc, top - 1 - cy, '▄',
                                fg=Color(160, 76, 28).mul(0.4 + 0.6 * fl), z=2)
        if dmg > 0.15:
            n = int(dmg * b['w'] * 2.2)
            for i in range(n):
                rx = b['x'] + (i % b['w']) - cam
                ry = base + (i // b['w']) - cy
                if ry < c_h and 0 <= rx < c_w:
                    c.set_pixel(rx, ry, ' ', bg=Color(52, 38, 24), z=2)


def _composite_filled(hr, c, z, cy=0):
    """Composite the hires buffer, writing only cells with actual content.

    `cy` is a vertical pan (in canvas rows): cy > 0 shifts the view up so the
    aerial fight can be followed as planes climb into the sky.
    """
    for y in range(min(c.h, hr.h // 2)):
        yy = y - cy
        if yy < 0 or yy >= hr.h // 2:
            continue
        rt, rb = hr.buffer[yy * 2], hr.buffer[yy * 2 + 1]
        for x in range(min(c.w, hr.w)):
            t, b = rt[x], rb[x]
            tf = t.fg is not None
            bf = b.fg is not None
            if tf and bf:
                c.set_pixel(x, y, '▀', t.fg, b.fg, z)
            elif tf:
                c.set_pixel(x, y, '▀', t.fg, z=z)
            elif bf:
                c.set_pixel(x, y, '▄', b.fg, z=z)


def _hashn(sx, sy):
    v = math.sin(sx * 12.9898 + sy * 78.233) * 43758.5453
    return v - math.floor(v)


def _crater_cells(s, grid, cr):
    cx0 = int(cr['x'])
    cy = int(cr['y']) // 2
    R = cr['r']
    rx = max(2, int(round(R * 1.2)))
    ry = max(1, int(round(R * 0.42)))
    gyi = max(0, min(len(grid) - 1, cy))
    gxi = max(0, min(len(grid[0]) - 1, cx0))
    base = grid[gyi][gxi]
    a0 = cr.get('a', _hashn(cx0, int(cr['y'])) * 6.283)
    # lit lip, earth wall, deep shadowed pit
    rim = base.lerp(Color(142, 116, 74), 0.42)
    wall = base.lerp(Color(40, 29, 22), 0.55)
    pit = base.lerp(Color(10, 7, 7), 0.88)
    cells = []
    for dy in range(-ry, ry + 1):
        sy = cy + dy
        for dx in range(-rx, rx + 1):
            wx = cx0 + dx
            nx = dx / rx
            ny = dy / ry
            theta = math.atan2(ny, nx)
            j = (0.08 * math.sin(theta * 3 + a0)
                 + 0.06 * math.sin(theta * 7 - a0 * 2.3))
            d = math.hypot(nx, ny)
            depth = (1.0 + j) - d
            if depth <= 0:
                # faint scorch / kicked-up dirt just outside the lip
                if depth > -0.22 and _hashn(wx * 3, sy * 5) < 0.08:
                    col = base.lerp(Color(52, 38, 26), 0.42)
                    cells.append((dx, sy, col.mul(0.75), col, '·'))
                continue
            g = min(1.0, depth * 2.2 + (_hashn(wx * 7 + 3, sy * 13) - 0.5) * 0.4)
            top = max(0.0, -ny)
            # smooth rim->pit falloff, lit far edge, shadowed near wall
            col = rim.lerp(pit, g)
            lit = 0.28 + 0.4 * top * (1.0 - g)
            if ny > 0.35:
                lit -= 0.25 * ((ny - 0.35) / 0.65) * (1.0 - g)
            col = col.mul(0.75 + 0.5 * lit)
            if g > 0.55 and _hashn(wx + 11, sy + 3) < 0.3:
                cells.append((dx, sy, col.mul(0.6), col, '░'))
            else:
                cells.append((dx, sy, None, col, ' '))
    return cells


def _render_craters(c, s, c_h, c_w, cam, cy=0):
    for cr in s['craters']:
        cells = cr.get('_cells')
        if cells is None:
            cells = _crater_cells(s, s['bg_grid'], cr)
            cr['_cells'] = cells
        cx0 = int(cr['x'])
        for dx, sy, fg, bg, ch in cells:
            sx = cx0 + dx - cam
            sy = sy - cy
            if 0 <= sx < c_w and 0 <= sy < c_h:
                c.set_pixel(sx, sy, ch, fg=fg, bg=bg, z=3)


def _advance(s, w, fac):
    """One faction meets its kill quota - push the front into the enemy district."""
    rnd = s['rnd']
    s['adv_msg'] = {'fac': fac, 'age': 0.0, 'life': 2.8}
    mid = (s['front'][0] + s['front'][1]) * 0.5
    _sfx('horn', mid, 0.9)
    # the pushing faction bellows its war cry as it rolls forward
    for _ in range(3):
        _war_cry(s, fac)
    for _ in range(3):
        _explode(s, mid + rnd.uniform(-w * 0.3, w * 0.3),
                 s['gy'] - 1, rnd.uniform(0.9, 1.4), True)
    for _ in range(5):
        s['smoke'].append({'x': mid + rnd.uniform(-w * 0.45, w * 0.45),
                           'y': s['gy'] - 2,
                           'vx': rnd.uniform(-1.2, 1.2),
                           'vy': -rnd.uniform(1.5, 3.5),
                           'age': 0.0, 'life': rnd.uniform(1.4, 2.6)})
    for b in s['buildings']:
        if b['kind'] == 'far' or b.get('collapsed') or b.get('tip', 0):
            continue
        if abs((b['x'] + b['w'] / 2.0) - mid) < w * 0.55:
            b['damage'] = min(1.0, b['damage'] + 0.002)
            if b['kind'] == 'skyline' and b['damage'] >= 1.0 and rnd.random() < 0.75:
                _start_tip(s, b)

