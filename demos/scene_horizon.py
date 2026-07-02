import math, random
from spore_engine import *
from spore_engine.core.color import *

_HZ = None

def _build_mountains(w, h, horizon_y, seed=0):
    rng = random.Random(seed)
    ranges = []
    for layer in range(3):
        detail = 60 + layer * 40
        base = [rng.uniform(0.05, 0.15 + layer * 0.08) for _ in range(detail)]
        peaks = []
        for i in range(detail):
            n = base[i]
            n += math.sin(i * 0.3 + layer * 2) * 0.04
            n += math.sin(i * 0.7 + layer * 5 + 1.3) * 0.025
            n += math.sin(i * 1.1 + layer * 7 + 0.7) * 0.015
            peaks.append(max(0.01, n))
        ranges.append({
            'peaks': peaks,
            'base_h': horizon_y - int((0.08 + layer * 0.04) * h),
            'detail': detail,
            'layer': layer,
        })
    return ranges

def _build_cloud_field(w, h, seed=1):
    rng = random.Random(seed)
    clouds = []
    for _ in range(18):
        cx = rng.uniform(-w * 0.5, w * 1.5)
        cy = rng.uniform(h * 0.02, h * 0.32)
        cw = rng.uniform(10, 35)
        ch = rng.uniform(cw * 0.2, cw * 0.45)
        lobes = rng.randint(3, 7)
        lobe_data = []
        for _ in range(lobes):
            lx = rng.uniform(-cw * 0.35, cw * 0.35)
            ly = rng.uniform(-ch * 0.2, ch * 0.1)
            lr = rng.uniform(cw * 0.08, cw * 0.25)
            lobe_data.append((lx, ly, lr))
        clouds.append({
            'x': cx, 'y': cy, 'w': cw, 'h': ch,
            'speed': rng.uniform(0.08, 0.3),
            'lobes': lobe_data,
            'brightness': rng.uniform(0.3, 1.0),
            'phase': rng.uniform(0, 2 * math.pi),
        })
    return clouds

def _scene_init(w, h):
    global _HZ
    if _HZ is not None:
        return
    horizon_y = int(h * 0.62)
    _HZ = {
        'horizon_y': horizon_y,
        'stars': [(random.uniform(0, w), random.uniform(0, h*0.55),
                   random.uniform(0, 2*math.pi), random.uniform(0.3, 1.0))
                  for _ in range(200)],
        'clouds': _build_cloud_field(w, h),
        'mountains': _build_mountains(w, h, horizon_y),
        'birds': [{'x': random.uniform(0, w), 'y': random.uniform(h*0.12, h*0.22),
                   'vx': random.uniform(0.4, 1.2), 'phase': random.uniform(0, 2*math.pi),
                   'wing_speed': random.uniform(2.0, 4.0), 'depth': random.uniform(0, 1)}
                  for _ in range(6)],
    }

def _atmosphere_scatter(t):
    alt = (math.sin(t * 0.015) * 0.5 + 0.5)
    sun_angle = alt * math.pi * 0.45 + 0.05 * math.pi
    return sun_angle

def _sky_color_at(ty, sun_angle, x_off):
    if sun_angle < 0.2:
        return Color(5, 5, 18)

    rayleigh = 1.0 + 4.0 * (1.0 / max(0.01, math.cos(sun_angle * 0.7 + 0.3)) - 1.0)
    r_bright = min(1.0, 0.15 + 0.85 * math.exp(-ty * 3.5 * rayleigh))
    g_bright = min(1.0, 0.08 + 0.92 * math.exp(-ty * 4.5 * rayleigh))
    b_bright = min(1.0, 0.05 + 0.95 * math.exp(-ty * 6.0 * rayleigh))

    horizon_ty = 1.0 - abs(ty - 0.92) * 6
    horizon_glow = max(0, horizon_ty)

    warm_hue = 0.08 - horizon_glow * 0.06
    warm_sat = 0.6 + horizon_glow * 0.3
    warm_bri = 0.3 + horizon_glow * 0.6

    sun_horiz = max(0, 1 - abs(ty - 0.92) * 3)
    warm_bri += sun_horiz * 0.2
    warm_hue -= sun_horiz * 0.02

    r = r_bright * (1 - warm_bri * 0.6) + warm_bri
    g = g_bright * (1 - warm_bri * 0.5) + warm_bri * 0.7
    b = b_bright * (1 - warm_bri * 0.3) + warm_bri * 0.2

    sky_fade = 0.7 + 0.3 * max(0, 1 - ty)**0.3
    r = min(1.0, r * sky_fade)
    g = min(1.0, g * sky_fade)
    b = min(1.0, b * sky_fade)

    zenith_r = Color.from_hsv(0.63, 0.35, 0.03)
    zenith_b = Color.from_hsv(0.62, 0.4, 0.06)
    zenith_t = ty * 3
    if zenith_t < 1:
        col = zenith_r.lerp(zenith_b, zenith_t)
    else:
        col = zenith_b

    sky_r = int(min(255, r * 255 * 0.4 + col.r * 0.6))
    sky_g = int(min(255, g * 255 * 0.4 + col.g * 0.6))
    sky_b = int(min(255, b * 255 * 0.4 + col.b * 0.6))

    return Color(sky_r, sky_g, sky_b)

def _draw_sky(hr, w, h, horizon_y, sun_x, sun_y, sun_angle):
    for y in range(horizon_y + 2):
        ty = y / max(1, horizon_y)
        col = _sky_color_at(ty, sun_angle, 0)
        for x in range(w):
            col_var = _sky_color_at(ty, sun_angle, x / max(1, w))
            blended = col.lerp(col_var, 0.3)
            hr.set_pixel(x, y, ' ', bg=blended, z=-100)

def _draw_sun(hr, w, h, sun_x, sun_y, horizon_y, t, sun_angle):
    if sun_y >= horizon_y or sun_y < 0:
        return
    r = 9 + int(4 * (0.5 + 0.5 * math.sin(t * 0.08)))
    glow_r = r + 12 + int(4 * (0.5 + 0.5 * math.sin(t * 0.05 + 1.3)))

    crep_count = 24
    for i in range(crep_count):
        angle = (i / crep_count) * 2 * math.pi + t * 0.02
        angle += math.sin(i * 2.3 + t * 0.1) * 0.15
        ray_len = glow_r * (2.0 + 0.5 * math.sin(t * 0.07 + i * 1.7))
        for step in range(1, int(ray_len)):
            d = step
            px = sun_x + int(math.cos(angle) * d)
            py = sun_y + int(math.sin(angle) * d)
            if 0 <= px < w and 0 <= py < horizon_y - 1:
                fade = 1 - d / ray_len
                fade = fade * fade * 0.07
                if fade > 0.01:
                    r_c = int(255 * fade)
                    g_c = int(220 * fade)
                    b_c = int(180 * fade)
                    hr.set_pixel(px, py, '·', fg=Color(r_c, g_c, b_c), z=45)

    for dy in range(-glow_r, glow_r + 1):
        for dx in range(-glow_r, glow_r + 1):
            d = math.hypot(dx, dy)
            px, py = sun_x + dx, sun_y + dy
            if 0 <= px < w and 0 <= py < horizon_y - 1:
                if d < r:
                    bri = 1 - d / r
                    fade = 1 - bri * 0.3
                    r_col = int(min(255, 255 * fade))
                    g_col = int(min(255, 230 * fade))
                    b_col = int(min(255, 180 * fade))
                    ch = '█' if bri > 0.7 else ('▓' if bri > 0.45 else ('▒' if bri > 0.25 else '░'))
                    hr.set_pixel(px, py, ch, fg=Color(r_col, g_col, b_col), z=60)
                elif d < glow_r:
                    glow = 1 - (d - r) / (glow_r - r)
                    glow_bri = glow * glow * 0.4
                    r_g = int(255 * glow_bri)
                    g_g = int(200 * glow_bri)
                    b_g = int(140 * glow_bri)
                    if r_g > 15:
                        ch = '·' if glow < 0.3 else '░'
                        hr.set_pixel(px, py, ch, fg=Color(r_g, g_g, b_g), z=50)

def _draw_stars(hr, w, h, horizon_y, sun_angle, t):
    night = max(0, min(1, (0.5 - sun_angle) * 3))
    if night < 0.05:
        return
    for cx, cy, phase, bright in _HZ['stars']:
        px = int(cx)
        py = int(cy)
        if py >= horizon_y - 8:
            continue
        twinkle = 0.5 + 0.5 * math.sin(t * 2.0 + phase * 5 + cx * 2.3)
        visible = twinkle * bright * night
        if visible < 0.15:
            continue
        b = int(min(255, visible * 255))
        ch = '·' if visible < 0.5 else '✦'
        hr.set_pixel(px, py, ch, fg=Color(b, b, min(255, int(b * 1.15))), z=70)

def _draw_clouds(hr, w, h, horizon_y, sun_x, sun_y, t, dt):
    for cl in _HZ['clouds']:
        cl['x'] += cl['speed'] * dt * 6
        if cl['x'] > w + cl['w'] * 2:
            cl['x'] = -cl['w'] * 2
            cl['y'] = random.uniform(h * 0.02, h * 0.32)

        cx_f, cy_f = cl['x'], cl['y']

        for lx, ly, lr in cl['lobes']:
            lcx = cx_f + lx
            lcy = cy_f + ly
            for dy in range(-int(lr), int(lr) + 1):
                for dx in range(-int(lr), int(lr) + 1):
                    d = math.hypot(dx, dy)
                    if d >= lr:
                        continue
                    px, py = int(lcx + dx), int(lcy + dy)
                    if px < 0 or px >= w or py < 0 or py >= horizon_y - 2:
                        continue
                    norm_d = d / lr
                    density = 1 - norm_d * norm_d
                    density *= density
                    if density < 0.1:
                        continue
                    alpha = density * 0.55

                    dist_to_sun = math.hypot(px - sun_x, py - sun_y)
                    sun_dist_norm = dist_to_sun / max(w, h)
                    sun_facing = max(0, 1 - sun_dist_norm * 2)

                    warmth = sun_facing * 0.3
                    bri = 0.3 + density * 0.5 + warmth * 0.2

                    rim_dx = (px - sun_x) / max(1, lr * 2)
                    rim_dy = (py - sun_y) / max(1, lr * 2)
                    rim_dist = math.hypot(rim_dx, rim_dy)
                    rim = max(0, 1 - abs(rim_dist - 0.7) * 5) * 0.3
                    bri += rim
                    bri = min(1, bri)

                    hue = 0.08 + warmth * 0.04
                    col = Color.from_hsv(hue % 1.0, 0.05 + warmth * 0.2, bri)
                    col = col.mul(0.5 + alpha * 0.5)

                    hr.set_pixel(px, py, ' ', bg=col, z=30)

def _draw_mountains(hr, w, h, horizon_y, sun_x, sun_y, t):
    ranges = _HZ['mountains']
    for r_range in ranges:
        peaks, base_h, detail, layer = r_range['peaks'], r_range['base_h'], r_range['detail'], r_range['layer']
        fog_factor = 0.15 + layer * 0.25

        for x in range(w):
            fi = x * detail / max(1, w)
            i0 = int(fi)
            i1 = min(i0 + 1, detail - 1)
            frac = fi - i0
            h_val = peaks[i0] * (1 - frac) + peaks[i1] * frac
            h_val += math.sin(x * 0.05 + layer * 3.7 + t * 0.01) * 0.01

            mtop = base_h - int(h_val * horizon_y * (0.5 - layer * 0.1))
            if mtop <= 0:
                mtop = 1

            for y in range(mtop, max(mtop, base_h)):
                if y <= 0 or y >= horizon_y:
                    continue
                ty = (y - mtop) / max(1, base_h - mtop)

                shade = 0.5 + 0.5 * math.cos((x - sun_x) * 0.02)
                shade = max(0.2, min(1, shade))

                if h_val > 0.18 and y < mtop + 2 + layer:
                    snow_bri = min(1, 0.5 + 0.5 * (h_val - 0.18) / 0.1)
                    sr = int((180 + 50 * snow_bri) * (1 - fog_factor) + 80 * fog_factor)
                    sg = int((190 + 40 * snow_bri) * (1 - fog_factor) + 85 * fog_factor)
                    sb = int((220 + 30 * snow_bri) * (1 - fog_factor) + 95 * fog_factor)
                    col = Color(min(255, sr), min(255, sg), min(255, sb))
                else:
                    base_r = 25 + int(30 * (1 - layer * 0.3))
                    base_g = 18 + int(25 * (1 - layer * 0.3))
                    base_b = 22 + int(35 * (1 - layer * 0.3))
                    base = Color(base_r, base_g, base_b)
                    lit = base.mul(shade * (0.6 + 0.4 * (1 - ty)))
                    fog_col = Color(120 + layer * 30, 100 + layer * 25, 130 + layer * 40)
                    col = lit.lerp(fog_col, fog_factor * (0.5 + ty * 0.5))

                hr.set_pixel(x, y, ' ', bg=col, z=10 + layer * 2)

def _draw_ocean(hr, w, h, horizon_y, sun_x, t):
    if horizon_y >= h:
        return

    wave_offsets = [0.3, 1.7, 2.9, 0.8]

    for y in range(horizon_y, h):
        ty = (y - horizon_y) / max(1, h - horizon_y)
        for x in range(w):
            wave1 = math.sin(x * 0.06 + t * 1.5 + wave_offsets[0]) * 2
            wave2 = math.sin(x * 0.11 + t * 2.3 + wave_offsets[1]) * 1.2
            wave3 = math.sin(x * 0.023 + t * 0.9 + wave_offsets[2]) * 3
            wave4 = math.sin(x * 0.18 + t * 3.7 + wave_offsets[3]) * 0.6
            wave = wave1 + wave2 + wave3 + wave4

            depth = ty * 2 + (wave * 0.02)
            depth = max(0, min(1, depth))

            horiz_dist = 1 - ty
            fresnel = horiz_dist * horiz_dist * 0.6 + 0.05

            dx = x - sun_x
            dist_to_sun_ray = abs(dx) / max(1, w * 0.35)
            if dist_to_sun_ray < 1:
                ray_brightness = (1 - dist_to_sun_ray) * (1 - dist_to_sun_ray) * fresnel
            else:
                ray_brightness = 0

            glitter = 0
            if abs(dx) < w * 0.15 and y > horizon_y + 2:
                glitter_time = math.sin(t * 2.5 + x * 0.3 + y * 0.5 + wave_offsets[3])
                if glitter_time > 0.7:
                    glitter = (glitter_time - 0.7) * 3 * (1 - abs(dx) / (w * 0.15))

            bri = 0.08 + depth * 0.15 + ray_brightness * 0.5 + glitter * 0.6
            bri = min(1, bri)

            warm = max(0, 1 - dist_to_sun_ray * 1.5) * 0.3
            hue = 0.10 - warm * 0.06 - depth * 0.04
            hue = hue % 1.0
            sat = 0.35 + warm * 0.3 - depth * 0.15
            sat = max(0.1, min(0.7, sat))

            col = Color.from_hsv(hue, sat, max(0.02, bri))

            ch_idx = (y + int(wave)) % 4
            ch = '█'
            if ch_idx == 0: ch = '░'
            elif ch_idx == 1: ch = '▒'
            elif ch_idx == 2: ch = '▓'

            if glitter > 0.3:
                ch = '█'
                col = Color(255, 240, 200)

            hr.set_pixel(x, y, ch, fg=col, z=5)

    ref_x = sun_x
    for y in range(horizon_y, min(horizon_y + int(h * 0.40), h)):
        ty = (y - horizon_y) / max(1, h - horizon_y)
        spread = max(1, int(2 + ty * 14))
        for dx in range(-spread, spread + 1):
            px = ref_x + dx
            if px < 0 or px >= w:
                continue
            d = abs(dx) / max(1, spread)
            if d >= 1:
                continue
            shimmer = 0.5 + 0.5 * math.sin(t * 3.5 + px * 2.1 + y * 2.7)
            bri = (1 - d * d) * (1 - ty * 0.8) * shimmer * 0.6
            if bri < 0.08:
                continue
            col = Color.from_hsv(0.09, 0.4 + d * 0.3, bri)
            hr.set_pixel(px, y, '█' if bri > 0.3 else '▓', fg=col, z=55)

def _draw_birds(c, w, t, dt):
    ch = c.h
    for b in _HZ['birds']:
        b['x'] += b['vx'] * dt * 8
        b['y'] += math.sin(t * b['wing_speed'] + b['phase']) * dt * 0.3
        if b['x'] > w + 8:
            b['x'] = -8
            b['y'] = random.uniform(0, ch * 0.25)
        px, py = int(b['x']), int(b['y'])
        wing = math.sin(t * b['wing_speed'] + b['phase'])
        depth_bri = 0.3 + b['depth'] * 0.4
        col = Color(int(25 * depth_bri), int(20 * depth_bri), int(30 * depth_bri))
        if 0 <= px < w and 0 <= py < ch - 2:
            c.set_pixel(px, py, '>' if wing > 0 else '<', col, z=80)
            if wing > 0.3 and px - 1 >= 0:
                c.set_pixel(px - 1, py, '~' if wing > 0.6 else '-', col, z=80)
            elif wing < -0.3 and px + 1 < w:
                c.set_pixel(px + 1, py, '~' if wing < -0.6 else '-', col, z=80)


def scene_horizon(c, hr, t, pt, dt):
    global _HZ
    w, h = hr.w, hr.h
    _scene_init(w, h)

    s = _HZ
    horizon_y = s['horizon_y']

    sun_angle = _atmosphere_scatter(t)
    sun_x = int(w * 0.45 + math.sin(t * 0.025) * w * 0.2)
    sun_y = int(horizon_y - 2 - math.sin(sun_angle) * horizon_y * 0.35)

    _draw_sky(hr, w, h, horizon_y, sun_x, sun_y, sun_angle)
    _draw_stars(hr, w, h, horizon_y, sun_angle, t)
    _draw_clouds(hr, w, h, horizon_y, sun_x, sun_y, t, dt)
    _draw_mountains(hr, w, h, horizon_y, sun_x, sun_y, t)
    _draw_ocean(hr, w, h, horizon_y, sun_x, t)
    _draw_sun(hr, w, h, sun_x, sun_y, horizon_y, t, sun_angle)
    hr.to_canvas(c)
    _draw_birds(c, w, t, dt)
