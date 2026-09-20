import math
from spore_engine import *
from spore_engine.core.color import *
from .constants import *
from . import ground
from .ground import (
    _init, _spawn_missile, _spawn_soldier, _spawn_gunship,
    _spawn_fighter, _spawn_mother, _spawn_mech, _spawn_zeppelin, _spawn_tank,
    _spawn_transport, _update_chutes, _render_chute,
    _spawn_swarm, _update_drones, _render_drone,
    _spawn_hacker, _update_hackers, _render_hacker, _render_pulse,
    _spawn_sniper, _update_snipers, _render_sniper,
    _spawn_builder, _update_builders, _render_builder,
    _spawn_driller, _update_drillers, _render_driller,
    _advance, _update_soldiers, _update_bullets, _update_corpses,
    _update_planes, _update_air, _update_tanks, _update_shells,
    _update_wrecks, _update_collapses, _update_mothers, _update_mechs,
    _update_zeppelins, _update_beams, _update_flak, _destroy_zeppelin,
    _explode, _render_missile, _update_far_falls, _render_buildings,
    _render_craters, _composite_filled,
    _render_wreck, _render_corpse, _render_soldier, _render_tank,
    _render_mech, _render_bunker, _render_bullet, _render_air,
    _render_plane, _render_mother, _render_zeppelin, _render_beam,
    _render_shell, _update_ragdolls, _render_ragdoll,
    _war_cry, _update_shouts,
)

_ADV_OSC = Oscillator(2 * math.pi / 12, 0.2, 1.0)
_MOTH_OSC = Oscillator(2 * math.pi / 8, 0.0, 1.0)


def reset():
    ground._WB = None


def scene_war_battlefield(c, hr, t, pt, dt):
    """Ground war - soldiers, tanks, mechs, gunships, bombs and destruction."""
    w, h = hr.w, hr.h
    ground._init(w, h)
    s = ground._WB
    s['pt'] = pt
    rnd = s['rnd']
    dt = max(0.0, min(0.1, dt))
    gy = s['gy']
    c_h = min(c.h, s['gh'])
    c_w = min(c.w, s['gw'])
    W = s['gw']

    # ---- spawners -------------------------------------------------
    # artillery barrages - a battery throws 4-5 shells every 40-50s,
    # instead of a constant rain of random bombs
    if s['barrage_n'] > 0:
        s['barrage_gap'] -= dt
        if s['barrage_gap'] <= 0:
            _spawn_missile(s, w, h)
            s['barrage_n'] -= 1
            s['barrage_gap'] = rnd.uniform(0.3, 0.6)
    else:
        s['barrage_t'] -= dt
        if s['barrage_t'] <= 0:
            s['barrage_n'] = rnd.randint(4, 5)
            s['barrage_gap'] = 0.4
            s['barrage_t'] = rnd.uniform(40, 50)

    s['soldier_t'] -= dt
    alive = [0, 0]
    for sol in s['soldiers']:
        if not sol['dead']:
            alive[sol['faction']] += 1
    if s['soldier_t'] <= 0 and sum(alive) < 45:
        _spawn_soldier(s, 0 if alive[0] <= alive[1] else 1)
        s['soldier_t'] = rnd.uniform(0.25, 0.6)

    # war cries - a faction bellows now and then from its front line.  When a
    # side holds a clear advantage it shouts more, selling the aggression.
    s['cry_t'] -= dt
    if s['cry_t'] <= 0:
        heavy = alive[0] > alive[1] + 8
        s['cry_t'] = rnd.uniform(4, 9) if not heavy else rnd.uniform(2, 5)
        for fac in (0, 1):
            if rnd.random() < 0.6:
                _war_cry(s, fac)

    s['plane_t'] -= dt
    if s['plane_t'] <= 0 and sum(1 for p in s['planes'] if not p['crash']) < 3:
        if not any(p['kind'] == 'gunship' and not p['crash'] for p in s['planes']):
            _spawn_gunship(s, w, h)
            s['plane_t'] = rnd.uniform(9, 15)
        else:
            s['plane_t'] = rnd.uniform(1.0, 2.0)

    # paratrooper transports - a cargo plane drops chutes over the battlefield
    s['drop_t'] -= dt
    transports_live = [p for p in s['planes'] if p['kind'] == 'transport' and not p['crash']]
    if s['drop_t'] <= 0 and not transports_live:
        _spawn_transport(s, w, h)
        s['drop_t'] = rnd.uniform(28, 42)

    # tiny strike drones arrive in swarms that harass the front lines
    s['drone_t'] -= dt
    drones_live = [d for d in s['drones'] if not d['dead']]
    if s['drone_t'] <= 0 and len(drones_live) < 14:
        _spawn_swarm(s, w, h)
        s['drone_t'] = rnd.uniform(18, 28)

    # hackers shelter in the safe spot behind the front and hijack enemy drones
    s['hacker_t'] -= dt
    hackers_live = [h for h in s['hackers'] if not h['dead']]
    if s['hacker_t'] <= 0 and len(hackers_live) < 2:
        n0 = sum(1 for h in hackers_live if h['faction'] == 0)
        n1 = sum(1 for h in hackers_live if h['faction'] == 1)
        fac = 0 if n0 <= n1 else 1
        _spawn_hacker(s, fac)
        s['hacker_t'] = rnd.uniform(18, 30)

    # sharpshooters take perches on rooftops and in windows behind the front
    s['sniper_t'] -= dt
    if s['sniper_t'] <= 0:
        s['sniper_t'] = rnd.uniform(14, 26)
        snipers_live = [sn for sn in s['snipers'] if not sn['dead']]
        for fac in (0, 1):
            n = sum(1 for sn in snipers_live if sn['faction'] == fac)
            if n < 2:
                _spawn_sniper(s, fac, w)

    # robot builders walk to the front and raise bunkers for their faction.
    # spawn evenly for both sides: each faction keeps up to 2 builders alive
    # until it has raised 3 bunkers.
    s['builder_t'] -= dt
    if s['builder_t'] <= 0:
        builders_live = [b for b in s['builders'] if not b['dead']]
        for fac in (0, 1):
            mine = sum(1 for b in builders_live if b['faction'] == fac)
            if mine < 2 and s['built_bunkers'][fac] < 3:
                bd = _spawn_builder(s, fac)
                bd['target_x'] = float(
                    s['front'][fac] - (1 if fac == 0 else -1) * rnd.uniform(14, 22))
                ground._sfx('blip', bd['x'], 0.35)
        s['builder_t'] = rnd.uniform(16, 26)

    # interceptors scramble against gunships, motherships and zeppelins
    s['intercept_t'] -= dt
    mother_tgt = [m for m in s['mothers'] if not m['dying'] and not m['dead']]
    zepp_tgt = [z for z in s['zeppelins'] if not z['dead']]
    gunship_tgt = [p for p in s['planes'] if p['kind'] == 'gunship' and not p['crash']]
    fighters_live = [p for p in s['planes'] if p['kind'] == 'fighter' and not p['crash']]
    if mother_tgt:
        air_threat = mother_tgt[0]
        needed = 3
    elif zepp_tgt:
        air_threat = zepp_tgt[0]
        needed = 3
    elif gunship_tgt:
        air_threat = gunship_tgt[0]
        needed = 2
    else:
        air_threat, needed = None, 0
    if air_threat is not None and len(fighters_live) < needed and s['intercept_t'] <= 0:
        _spawn_fighter(s, w, h, air_threat)
        s['intercept_t'] = rnd.uniform(1.5, 3.0)

    # rare mothership deployment by a faction
    s['mother_t'] -= dt
    if s['mother_t'] <= 0 and len(s['mothers']) == 0:
        _spawn_mother(s, w, h)
        s['mother_t'] = rnd.uniform(50, 85)

    # massive walking mechs - rare, one or two at a time
    s['mech_t'] -= dt
    if s['mech_t'] <= 0 and len(s['mechs']) < 2:
        _spawn_mech(s, rnd.randint(0, 1))
        s['mech_t'] = rnd.uniform(32, 50)

    # colossal zeppelins - every ~50-80s
    s['zepp_t'] -= dt
    if s['zepp_t'] <= 0 and len(s['zeppelins']) < 1:
        _spawn_zeppelin(s, w, h)
        s['zepp_t'] = rnd.uniform(50, 80)

    # underground drillers burrow beneath enemy armour and pierce it
    s['driller_t'] -= dt
    if s['driller_t'] <= 0:
        drillers_live = [d for d in s['drillers'] if not d['dead']]
        for fac in (0, 1):
            mine = sum(1 for d in drillers_live if d['faction'] == fac)
            foes = ([m for m in s['mechs'] if not m['dead'] and m['faction'] != fac]
                    + [t for t in s['tanks'] if not t['dead'] and t['faction'] != fac])
            if mine < 2 and foes:
                dr = _spawn_driller(s, fac)
                dr['tgt'] = ground._driller_target(s, dr)
                ground._sfx('swarm', dr['x'], 0.4)
        s['driller_t'] = rnd.uniform(20, 32)

    # tanks roll out to the front
    s['tank_t'] -= dt
    tanks_live = [tk for tk in s['tanks'] if not tk['dead']]
    if s['tank_t'] <= 0 and len(tanks_live) < 4:
        n0 = sum(1 for tk in tanks_live if tk['faction'] == 0)
        n1 = sum(1 for tk in tanks_live if tk['faction'] == 1)
        fac = 0 if n0 <= n1 else 1
        _spawn_tank(s, fac)
        s['tank_t'] = rnd.uniform(9, 16)

    # ---- campaign: kill advantage drives the battle line ----------------
    # a faction that keeps winning kills grinds the front forward for good,
    # so the line never stalls in the middle. KILL_ADV streaks still fire
    # the horn + fireworks celebration.
    bx0, bx1 = s['bunkers'][0]['x'], s['bunkers'][1]['x']
    net = s['deaths'][1] - s['deaths'][0]
    s['push'] = max(-MAX_PUSH * w, min(MAX_PUSH * w, net * w * PUSH_RATE))
    if s['streak'][0] >= KILL_ADV:
        s['streak'][0] = 0
        _advance(s, w, 0)
    if s['streak'][1] >= KILL_ADV:
        s['streak'][1] = 0
        _advance(s, w, 1)

    # front lines drift with momentum, plus district push
    base_f0 = W * 0.5 - w * 0.08
    base_f1 = W * 0.5 + w * 0.08
    for f in (0, 1):
        e = 1 - f
        dir = 1 if f == 0 else -1
        if alive[f] > alive[e] + 2:
            s['drift'][f] += dir * dt * 3
        elif alive[f] < alive[e] - 2:
            s['drift'][f] -= dir * dt * 3
        s['drift'][f] = max(-8.0, min(8.0, s['drift'][f]))
        s['front'][f] = max(bx0 + 8, min(bx1 - 8,
                             (base_f0 if f == 0 else base_f1) + s['push'] + s['drift'][f]))
    s['front'][1] = max(s['front'][1], s['front'][0] + 4)
    s['front'][0] = min(s['front'][0], s['front'][1] - 4)

    # battle centre + side-scrolling camera that pans with the war, plus a
    # manual vertical pan (cam_y) so the aerial fight can be followed
    s['mid'] = (s['front'][0] + s['front'][1]) * 0.5
    target = max(0.0, min(W - w, s['mid'] - w * 0.5 + s['cam_off']))
    dc = target - s['cam']
    if abs(dc) < 1.5:
        s['cam'] = target
    else:
        s['cam'] += max(-1.0, min(1.0, dc))
    s['cam_i'] = int(round(s['cam']))
    cam = s['cam_i']
    cy = s['cam_y']

    if s['adv_msg']:
        s['adv_msg']['age'] += dt
        if s['adv_msg']['age'] >= s['adv_msg']['life']:
            s['adv_msg'] = None

    # ---- update combat --------------------------------------------
    _update_soldiers(s, dt)
    _update_bullets(s, dt)
    _update_corpses(s, dt)
    _update_shouts(s, hr, w, h, cam, dt)
    _update_planes(s, dt, w, h)
    _update_chutes(s, dt, w, h)
    _update_drones(s, dt, w, h)
    _update_hackers(s, dt, w, h)
    _update_snipers(s, dt, w, h)
    _update_builders(s, dt, w)
    _update_air(s, dt, w, h)
    _update_tanks(s, dt, w)
    _update_shells(s, dt, w, h)
    _update_drillers(s, dt, w, h)
    _update_wrecks(s, dt)
    _update_ragdolls(s, dt)
    _update_collapses(s, dt)
    _update_mothers(s, dt, w, h)
    _update_mechs(s, dt)
    _update_zeppelins(s, dt, w, h)
    _update_beams(s, dt)
    _update_flak(s, dt)

    # anti-aircraft flak bursts around live aircraft
    targets = ([p for p in s['planes'] if not p['crash']]
               + [m for m in s['mothers'] if not m['dying'] and not m['dead']]
               + [z for z in s['zeppelins'] if not z['dead']])
    if targets:
        s['flak_t'] -= dt
        if s['flak_t'] <= 0:
            s['flak_t'] = rnd.uniform(1.6, 3.2)
            tg = rnd.choice(targets)
            fx = tg['x'] + rnd.uniform(-8, 8)
            fy = tg['y'] + rnd.uniform(-6, 6)
            s['flak'].append({'x': fx, 'y': fy, 'age': 0.0,
                              'life': 0.7, 'r': 3.4})
            ground._sfx('flak', fx, 0.6)
            s['smoke'].append({'x': fx, 'y': fy,
                               'vx': rnd.uniform(-0.6, 0.6),
                               'vy': rnd.uniform(-0.3, 1.2),
                               'age': 0.0, 'life': rnd.uniform(0.6, 1.2)})
            if rnd.random() < 0.45:
                tg['hp'] -= 1
                if tg['kind'] == 'gunship' and tg['hp'] <= 0 and not tg['crash']:
                    tg['crash'] = True
                    tg['vy'] = rnd.uniform(0.5, 2)
                if tg['kind'] == 'transport' and tg['hp'] <= 0 and not tg['crash']:
                    tg['crash'] = True
                    tg['vy'] = rnd.uniform(0.5, 2)
                if tg['kind'] == 'zeppelin' and tg['hp'] <= 0:
                    _destroy_zeppelin(s, tg)

    # ---- update ordnance -------------------------------------------
    alive = []
    for b in s['bombs']:
        b['vy'] += 30 * dt
        b['x'] += b['vx'] * dt
        b['y'] += b['vy'] * dt
        b['flame'] += dt * 28
        if b['y'] >= gy or b['y'] > h + 20:
            _explode(s, b['x'], gy, 2.3, True)
            continue
        px, py = int(b['x'] - cam), int(b['y'])
        if 0 <= px < w and 0 <= py < h:
            hr.set_pixel(px, py, '●', fg=Color(120, 120, 130), z=30)
            hr.set_pixel(px, max(0, py - 1), '▄', fg=Color(60, 60, 70), z=29)
            fl = 0.6 + 0.4 * math.sin(b['flame'])
            hr.set_pixel(px, max(0, py - 2), '·',
                         fg=Color.from_hsv(0.07, 1, fl), z=32)
        alive.append(b)
    s['bombs'] = alive

    alive = []
    for m in s['missiles']:
        m['age'] += dt
        m['vy'] += m['g'] * dt
        m['x'] += m['vx'] * dt
        m['y'] += m['vy'] * dt
        m['trail'].append((int(m['x']), int(m['y'])))
        if len(m['trail']) > 26:
            m['trail'].pop(0)
        if m['y'] >= gy or m['x'] < -w or m['x'] > W + w or m['y'] > h + 30:
            _explode(s, m['x'], min(m['y'], gy), 3.4, True)
            continue
        if m['y'] > gy * 0.55 and rnd.random() < dt * 0.04:
            _explode(s, m['x'], m['y'], 1.2, False)
            s['smoke'].append({'x': m['x'], 'y': m['y'],
                               'vx': rnd.uniform(-0.8, 0.8),
                               'vy': rnd.uniform(-0.5, 0.5),
                               'age': 0.0, 'life': rnd.uniform(1.0, 1.8)})
            continue
        _render_missile(hr, m, w, h, cam)
        alive.append(m)
    s['missiles'] = alive

    # ---- update particles ------------------------------------------
    for e in s['explosions']:
        e['age'] += dt
    s['explosions'] = [e for e in s['explosions'] if e['age'] < e['life']]
    if len(s['explosions']) > 10:
        s['explosions'] = s['explosions'][-10:]

    for sh in s['shockwaves']:
        sh['age'] += dt
    s['shockwaves'] = [sh for sh in s['shockwaves'] if sh['age'] < sh['life']]

    # burning buildings emit rising smoke plumes
    _update_far_falls(s, dt)
    for pl in s['pulses']:
        pl['age'] += dt
    s['pulses'] = [pl for pl in s['pulses'] if pl['age'] < pl['life']]
    if len(s['pulses']) > 60:
        s['pulses'] = s['pulses'][-60:]
    for b in s['buildings']:
        if (b['kind'] == 'skyline' and b['fire'] and b['damage'] < 0.85
                and not b.get('tip', 0) and not b.get('collapsed')
                and rnd.random() < dt * 0.4):
            top = b['base'] - b['h'] + int(b['damage'] * b['h'] * 0.55)
            s['smoke'].append({'x': b['x'] + rnd.uniform(0, b['w']),
                               'y': top * 2 - 2,
                               'vx': rnd.uniform(-0.4, 0.4),
                               'vy': -rnd.uniform(1.2, 2.8),
                               'age': 0.0, 'life': rnd.uniform(1.6, 3.2)})

    alive = []
    for p in s['smoke']:
        p['age'] += dt
        p['vy'] -= 4 * dt
        p['vx'] *= max(0.0, 1 - 0.5 * dt)
        p['x'] += p['vx'] * dt
        p['y'] += p['vy'] * dt
        a = 1 - p['age'] / p['life']
        if a <= 0 or p['y'] < -5:
            continue
        if p.get('dust'):
            g = int(150 * a)
            hr.set_pixel(int(p['x'] - cam), int(p['y']), '░' if a > 0.5 else '·',
                         fg=Color(g, int(g * 0.78), int(g * 0.6)), z=41)
        else:
            g = int(95 * a)
            hr.set_pixel(int(p['x'] - cam), int(p['y']), '░' if a > 0.65 else '·',
                         fg=Color(g, g, g + 8), z=40)
        alive.append(p)
    if len(alive) > 140:
        alive = alive[-140:]
    s['smoke'] = alive

    alive = []
    for p in s['debris']:
        p['age'] += dt
        p['vy'] += 46 * dt
        p['x'] += p['vx'] * dt
        p['y'] += p['vy'] * dt
        a = 1 - p['age'] / p['life']
        if a <= 0 or p['y'] > gy + 2:
            continue
        if p.get('hot'):
            col = Color(255, 240, 200).mul(a)
            ch = '·'
        else:
            col = Color.from_hsv(p.get('hue', 0.06), 0.85, a * 0.9)
            ch = '·' if a < 0.4 else '░'
        hr.set_pixel(int(p['x'] - cam), int(p['y']), ch, fg=col, z=55)
        alive.append(p)
    s['debris'] = alive

    # ---- background sky + ground -----------------------------------
    for y in range(c_h):
        row = s['bg_grid'][max(0, min(s['gh'] - 1, y - cy))]
        for x in range(c_w):
            c.set_pixel(x, y, ' ', bg=row[cam + x], z=1)

    # ---- buildings (torn, with rubble) ------------------------------
    _render_buildings(c, s, c_h, c_w, t, cam, cy)

    # ---- scorched craters --------------------------------------------
    _render_craters(c, s, c_h, c_w, cam, cy)

    # ---- windows / fire glow -----------------------------------------
    for wi, (wx, wy, seed, b_idx, lit) in enumerate(s['windows_all']):
        sx = wx - cam
        sy = wy - cy
        if sx < 0 or sx >= c_w or sy < 0 or sy >= c_h:
            continue
        b = s['buildings'][b_idx]
        if b.get('collapsed') or b.get('tip', 0):
            continue
        if b['damage'] > 0.85 or wy < b['base'] - b['h'] + int(b['damage'] * b['h'] * 0.55):
            continue
        fl = s['win_osc'][wi].value(t)
        if b['fire']:
            # muted ember in a few windows - slow, dim, no harsh flashing
            if lit > 0.7 and fl > 0.62:
                c.set_pixel(sx, sy, '·', fg=Color(140, 60, 22), z=4)
        else:
            # steady warm light, sparse and soft - gentle slow flicker
            if lit > 0.72 and fl > 0.3:
                c.set_pixel(sx, sy, '·', fg=Color(196, 164, 118), z=4)

    # ---- actors on hires buffer -------------------------------------
    for wk in s['wrecks']:
        _render_wreck(hr, wk, t, w, h, cam)
    for rp in s['ragdolls']:
        _render_ragdoll(hr, rp, t, w, h, cam)
    for cp in s['corpses']:
        _render_corpse(hr, cp, w, h, cam)
    for sol in s['soldiers']:
        _render_soldier(hr, sol, w, h, cam)
    for ch in s['chutes']:
        _render_chute(hr, ch, w, h, cam)
    for tk in s['tanks']:
        _render_tank(hr, tk, w, h, cam)
    for me in s['mechs']:
        _render_mech(hr, me, t, w, h, cam)
    for bu in s['bunkers']:
        _render_bunker(hr, bu, cam)
    for b in s['bullets']:
        _render_bullet(hr, b, w, h, cam)
    for a in s['air']:
        _render_air(hr, a, w, h, cam)
    for p in s['planes']:
        _render_plane(hr, p, t, w, h, gy, cam)
    for dr in s['drones']:
        _render_drone(hr, dr, t, w, h, cam)
    for hk in s['hackers']:
        _render_hacker(hr, hk, t, w, h, cam)
    for sn in s['snipers']:
        _render_sniper(hr, sn, t, w, h, cam)
    for bd in s['builders']:
        _render_builder(hr, bd, t, w, h, cam)
    for dr in s['drillers']:
        _render_driller(hr, dr, t, w, h, gy, cam)
    for pl in s['pulses']:
        _render_pulse(hr, pl, w, h, cam)
    for ms in s['mothers']:
        _render_mother(hr, ms, t, w, h, cam)
    for z in s['zeppelins']:
        _render_zeppelin(hr, z, t, w, h, cam)
    for bm in s['beams']:
        _render_beam(hr, bm, w, h, cam)
    for sh in s['shells']:
        _render_shell(hr, sh, w, h, cam)

    # ---- explosion fireballs -----------------------------------------
    for e in s['explosions']:
        p = e['age'] / e['life']
        r = e['radius_max'] * (0.3 + 0.7 * math.sin(math.pi * min(1.0, p)))
        r *= (1.0 - 0.35 * p)
        if r < 0.8:
            continue
        bmax = 1.0 - p
        ry = r * 0.5
        ex = e['x'] - cam
        x0, x1 = int(ex - r), int(ex + r)
        y0, y1 = int(e['y'] - ry), int(e['y'] + ry)
        for py in range(y0, y1 + 1):
            for px in range(x0, x1 + 1):
                d = math.hypot(px - ex, (py - e['y']) * 2.0) / r
                if d > 1.0:
                    continue
                b = (1.0 - d) ** 1.3 * bmax
                if b < 0.04:
                    continue
                if b > 0.7:
                    ch, col = '█', Color(255, 252, 220)
                elif b > 0.4:
                    ch, col = '█', Color(255, 185, 90)
                elif b > 0.18:
                    ch, col = '▒', Color(220, 105, 35)
                else:
                    ch, col = '░', Color(130, 55, 18)
                hr.set_pixel(px, py, ch, fg=col, z=60)

    # ---- shockwave rings ---------------------------------------------
    for sh in s['shockwaves']:
        p = sh['age'] / sh['life']
        r = sh['radius_max'] * (0.2 + 0.8 * p)
        if r < 1:
            continue
        col = Color.from_hsv(0.07, 0.6, (1 - p) * 0.5)
        ry = r * 0.5
        sx = sh['x'] - cam
        x0, x1 = int(sx - r), int(sx + r)
        y0, y1 = int(sh['y'] - ry), int(sh['y'] + ry)
        for py in range(y0, y1 + 1):
            for px in range(x0, x1 + 1):
                d = math.hypot(px - sx, (py - sh['y']) * 2.0)
                if abs(d - r) < 1.0:
                    hr.set_pixel(px, py, '░', fg=col, z=50)

    # ---- anti-aircraft flak bursts -----------------------------------
    for f in s['flak']:
        p = f['age'] / f['life']
        r = f['r'] * (0.35 + 0.65 * p)
        if r < 1:
            continue
        col = Color.from_hsv(0.09, 0.4, 0.35 + 0.6 * (1 - p))
        fx = f['x'] - cam
        x0, x1 = int(fx - r), int(fx + r)
        y0, y1 = int(f['y'] - r), int(f['y'] + r)
        for py in range(y0, y1 + 1):
            for px in range(x0, x1 + 1):
                d = math.hypot(px - fx, (py - f['y']) * 2.0)
                if abs(d - r) < 1.0:
                    hr.set_pixel(px, py, '░', fg=col, z=58)
        if p < 0.35:
            core = 1 - p / 0.35
            ccol = Color(255, 255, 255).mul(core)
            ccx, ccy = int(fx), int(f['y'])
            for dx in range(-1, 2):
                for dy in range(-1, 2):
                    hr.set_pixel(ccx + dx, ccy + dy,
                                 '▓' if core > 0.6 else '░', fg=ccol, z=59)

    # ---- engine particle system --------------------------------------
    pt.update_and_render(hr, dt, dx=-cam, dy=0, z=58)

    # ---- composite (actors over windows over buildings) --------------
    _composite_filled(hr, c, z=5, cy=cy)

    # ---- HUD ----------------------------------------------------------
    a0 = sum(1 for sol in s['soldiers'] if not sol['dead'] and sol['faction'] == 0)
    a1 = sum(1 for sol in s['soldiers'] if not sol['dead'] and sol['faction'] == 1)
    b0, r0 = s['deaths'][0], s['deaths'][1]
    c.draw_text(2, 0, '☄ WAR BATTLEFIELD ☄', Color.from_hsv(0.05, 0.9, 1.0), z=100)
    sc = '{} - {}'.format(b0, r0)
    hue = 0.62 if b0 < r0 else (0.02 if r0 < b0 else 0.12)
    c.draw_text(c_w - len(sc) - 2, 0, sc, Color.from_hsv(hue, 0.9, 1.0), z=100)
    ntk = len([tk for tk in s['tanks'] if not tk['dead']])
    ndr = len([d for d in s['drones'] if not d['dead']])
    nsn = len([sn for sn in s['snipers'] if not sn['dead']])
    status = ('blue {}  red {}   fallen {}-{}  |  adv {}/{} - {}/{}  |  tanks {}  drones {}  snipers {}'
              .format(a0, a1, b0, r0, s['streak'][0], KILL_ADV,
                      s['streak'][1], KILL_ADV, ntk, ndr, nsn))
    eng = ground.get_sound()
    if eng is not None:
        eng.set_listener(cam + w * 0.5, w)
        eng.ambient('drone', min(1.0, ndr / 6.0))
        eng.ambient('wind', 0.6)
        if eng.muted:
            status += '   [M]'
    c.draw_text(2, c.h - 1, status, DIM, z=100)
    c.draw_text(2, 1, 'q Menu', DIM, z=100)

    if s['push'] > w * 0.2:
        zone = 'RED DISTRICT'
        zcol = Color.from_hsv(0.02, 0.9, 1.0)
    elif s['push'] < -w * 0.2:
        zone = 'BLUE DISTRICT'
        zcol = Color.from_hsv(0.62, 0.9, 1.0)
    else:
        zone = 'MIDDLE GROUND'
        zcol = DIM
    c.draw_text(c_w - len(zone) - 2, c.h - 1, zone, zcol, z=100)

    am = s['adv_msg']
    if am is not None:
        fac = am['fac']
        msg = 'BLUE PUSHES INTO RED DISTRICT' if fac == 0 else 'RED PUSHES INTO BLUE DISTRICT'
        col = Color.from_hsv(FACTION_HUE[fac], 0.95, 0.9)
        pulse = _ADV_OSC.value(t)
        c.draw_text(c_w // 2 - len(msg) // 2, 1, msg, col, z=100)
        sub = '<<< OPPONENT PUSHED BACK >>>'
        c.draw_text(c_w // 2 - len(sub) // 2, 2, sub,
                    Color.from_hsv(0.12, 0.9, 0.4 + 0.6 * pulse), z=100)

    for ms in s['mothers']:
        if not ms['dead'] and ms['y'] < c_h * 2 - 2:
            fl = _MOTH_OSC.value(t)
            hue_m = FACTION_HUE[ms['faction']]
            warn = 'MOTHERSHIP'
            c.draw_text(c_w - len(warn) - 2, 1, warn,
                        Color.from_hsv(hue_m, 0.9, 0.5 + 0.5 * fl), z=100)

    # ---- engine screen shake + flash on heavy impacts -----------------
    if s['flash_t'] > 0:
        flash(c, min(0.8, s['flash_t'] * 2.5), 101)
        s['flash_t'] -= dt
    if s['shake_t'] > 0:
        shake(c, s['shake_p'] * min(1.0, s['shake_t'] / 1.1), seed=int(t * 100))
        s['shake_t'] -= dt
