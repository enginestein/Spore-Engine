import math, random
from spore_engine import *
from spore_engine.core.color import *
from spore_engine.core.geom import Vec3
from spore_engine.sim.noise import PerlinNoise


# --- Cloud generation state ---
_SCENE = None

def _cloud_density(p: Vec3, noise: PerlinNoise, t: float) -> float:
    """Return cloud density at point p, using layered 2D noise over xz plane"""
    # Base cloud layer between y=2 and y=6
    if p.y < 1.5 or p.y > 7.0:
        return 0.0

    # Pseudo-3D: encode z into the x coordinate with different offsets per octave
    fx = p.x * 0.06 + p.z * 0.04 + t * 0.008
    fy = p.y * 0.08
    n1 = noise.noise2(fx, fy)

    fx2 = p.x * 0.12 + p.z * 0.09 + 1.7 - t * 0.005
    fy2 = p.y * 0.15 + 3.2
    n2 = noise.noise2(fx2, fy2)

    fx3 = p.x * 0.03 + p.z * 0.025 + 5.3 + t * 0.006
    fy3 = p.y * 0.04 + 1.1
    n3 = noise.noise2(fx3, fy3)

    # Cloud density from combined noise
    density = (n1 * 0.5 + n2 * 0.3 + n3 * 0.2) * 0.5 + 0.5

    # Steep sigmoid for sharp cloud edges
    density = 1.0 / (1.0 + math.exp(-(density - 0.35) * 8.0))

    # Fade at top and bottom of cloud layer
    fade_in = min(1.0, (p.y - 1.5) / 0.8)
    fade_out = min(1.0, (7.0 - p.y) / 1.0)
    density *= fade_in * fade_out

    # Add detail noise for wispy edges
    fxd = p.x * 0.3 + p.z * 0.25 + 9.7 + t * 0.02
    fyd = p.y * 0.4 + 5.1
    n_detail = noise.noise2(fxd, fyd)
    detail = (n_detail * 0.5 + 0.5) * 0.3
    density = max(0, density - detail)

    return max(0.0, min(1.0, density))

def _raymarch_clouds(
    origin: Vec3, direction: Vec3,
    noise: PerlinNoise, t: float,
    sun_dir: Vec3, max_dist: float = 60.0,
    steps: int = 80, light_steps: int = 16
) -> Color:
    """
    Volumetric ray march through clouds with single-scattering god rays.
    At each sample point, compute cloud density and the amount of sunlight
    scattered toward the viewer (in-scattering). Sunlight is attenuated by
    cloud density along the light ray (shadow term).
    """
    step_size = max_dist / steps

    # Sky color gradient (builds up behind everything)
    sky = Gradient(
        Color(30, 50, 120),   # deep blue at top
        Color(80, 120, 200),  # mid blue
        Color(180, 160, 130), # horizon haze
        Color(220, 190, 140), # near horizon
    )

    # Sun color
    sun_color = Color(255, 220, 150)
    sun_glow_color = Color(255, 180, 80)

    total_r = 0.0
    total_g = 0.0
    total_b = 0.0
    transmittance = 1.0  # how much background is visible

    for i in range(steps):
        p = origin + direction * (i * step_size)

        # Sample cloud density at this point
        dens = _cloud_density(p, noise, t)
        if dens < 0.01:
            continue

        # How much light gets through this sample (absorption)
        sample_trans = math.exp(-dens * 1.5 * step_size)

        # Sun in-scattering (god ray) - march toward sun to compute shadow
        sun_occ = 1.0
        sp = p
        for j in range(light_steps):
            sp = sp + sun_dir * (1.5 + j * 1.2)
            sd = _cloud_density(sp, noise, t)
            if sd > 0.01:
                sun_occ *= math.exp(-sd * 1.5 * 1.2)

        # Henyey-Greenstein phase function (forward scattering)
        cos_angle = direction.dot(sun_dir)
        g = 0.6
        phase = (1.0 - g * g) / (4.0 * math.pi * (1.0 + g * g - 2.0 * g * cos_angle) ** 1.5)

        # In-scattered light reaching the viewer from this sample
        scatter = dens * transmittance * sun_occ * phase * 0.6

        total_r += sun_color.r * scatter * 0.04
        total_g += sun_color.g * scatter * 0.04
        total_b += sun_color.b * scatter * 0.04

        # Update transmittance along view ray
        transmittance *= sample_trans

        # Early termination
        if transmittance < 0.005:
            break

    # Compute sky background with sun glow
    cos_sun = direction.dot(sun_dir)
    sun_disk = max(0, (cos_sun - 0.9995) / 0.0005)

    # Sky color based on view elevation
    sky_t = max(0, min(1, (direction.y * 0.5 + 0.5)))
    bg = sky.at(sky_t)

    # Sun glow on sky
    sun_glow = max(0, cos_sun) ** 40 * 0.8
    bg = Color(
        min(255, bg.r + int(sun_glow_color.r * sun_glow)),
        min(255, bg.g + int(sun_glow_color.g * sun_glow)),
        min(255, bg.b + int(sun_glow_color.b * sun_glow)),
    )

    # Compose: background * transmittance + volumetric light
    result = Color(
        min(255, int(bg.r * transmittance + total_r)),
        min(255, int(bg.g * transmittance + total_g)),
        min(255, int(bg.b * transmittance + total_b)),
    )
    return result


def _render_ground(canvas: Canvas, t: float, noise: PerlinNoise):
    """Render a simple ground plane with color"""
    w, h = canvas.w, canvas.h
    ground_grad = Gradient(
        Color(25, 25, 30),
        Color(35, 40, 35),
        Color(50, 55, 40),
        Color(70, 75, 50),
    )
    for y in range(h // 2 + 2, h):
        ty = (y - h // 2 - 2) / (h - h // 2 - 2)
        for x in range(w):
            n = noise.noise2(x * 0.08, y * 0.08 + t * 0.02) * 0.5 + 0.5
            col = ground_grad.at(ty).mul(0.7 + 0.3 * n)
            canvas.set_pixel(x, y, '\xe2\x96\x88', col, z=5)
    hy = h // 2 + 1
    for x in range(w):
        col = Color(40, 45, 40)
        canvas.set_pixel(x, hy, '\xe2\x96\x80', col, z=6)


def scene_god_rays(c: Canvas, hr: HiResCanvas, t: float, pt, dt: float):
    """God Rays - Realistic volumetric light shafts piercing through cloud layers"""
    global _SCENE
    w, h = c.w, c.h

    if _SCENE is None:
        _SCENE = {
            'noise': PerlinNoise(42),
        }

    noise = _SCENE['noise']

    # Camera orbits around a point, looking at clouds
    cam_dist = 14.0 + 2.0 * math.sin(t * 0.04)
    cam_angle = t * 0.03
    cam_height = 4.0 + 1.5 * math.sin(t * 0.05)

    eye = Vec3(
        cam_dist * math.sin(cam_angle),
        cam_height,
        cam_dist * math.cos(cam_angle),
    )
    target = Vec3(0, 3.5, 0)

    # Sun direction (slowly moves across sky)
    sun_angle = -0.6 + 0.3 * math.sin(t * 0.02)
    sun_elev = 0.4 + 0.2 * math.sin(t * 0.025)
    sun_dir = Vec3(
        math.cos(sun_angle) * math.cos(sun_elev),
        math.sin(sun_elev),
        math.sin(sun_angle) * math.cos(sun_elev),
    ).norm()

    # Camera basis
    aspect = w / h
    forward = (target - eye).norm()
    world_up = Vec3(0, 1, 0)
    right = forward.cross(world_up).norm()
    up = right.cross(forward)
    fov = 65.0
    tan_fov = math.tan(math.radians(fov) / 2)

    # Render with sub-sampling
    lm = int(w * h * 0.08)
    step = max(1, int(math.sqrt(w * h / lm)))

    # Clear
    for y in range(h):
        for x in range(w):
            c.set_pixel(x, y, ' ')

    for y in range(0, h, step):
        for x in range(0, w, step):
            sx = (2 * (x + 0.5) / w - 1) * aspect * tan_fov
            sy = (1 - 2 * (y + 0.5) / h) * tan_fov

            rd = (forward + right * sx + up * sy).norm()
            col = _raymarch_clouds(eye, rd, noise, t, sun_dir)

            for dy in range(min(step, h - y)):
                for dx in range(min(step, w - x)):
                    c.set_pixel(x + dx, y + dy, '\xe2\x96\x88', col, z=10)

    # Fill gaps if subsampling
    if step > 1:
        for y in range(h):
            for x in range(w):
                px = c.get_pixel(x, y)
                if px and (px.fg is None or (px.fg.r == 0 and px.fg.g == 0 and px.fg.b == 0)):
                    neighbors = []
                    for dx, dy in [(-step,0),(step,0),(0,-step),(0,step)]:
                        nx, ny = x + dx, y + dy
                        np_ = c.get_pixel(nx, ny)
                        if np_ and np_.fg:
                            neighbors.append(np_.fg)
                    if neighbors:
                        avg = Color(
                            sum(c2.r for c2 in neighbors) // len(neighbors),
                            sum(c2.g for c2 in neighbors) // len(neighbors),
                            sum(c2.b for c2 in neighbors) // len(neighbors),
                        )
                        c.set_pixel(x, y, '\xe2\x96\x88', avg, z=10)

    # Render ground
    _render_ground(c, t, noise)

    # Brighten bright pixels (god ray enhancement)
    for y in range(h):
        for x in range(w):
            px = c.get_pixel(x, y)
            if px and px.fg:
                lum = px.fg.luminance
                if lum > 80:
                    boost = min(1.0, (lum - 80) / 120.0) * 0.3
                    c.set_pixel(x, y, px.char, Color(
                        min(255, px.fg.r + int(255 * boost)),
                        min(255, px.fg.g + int(220 * boost)),
                        min(255, px.fg.b + int(180 * boost)),
                    ), z=px.z)

    # Title with animated color
    title_hue = (sun_angle * 0.2 + 0.08) % 1.0
    c.draw_text(2, 0, '\xe2\x9c\xa6 God Rays \xe2\x9c\xa6', Color.from_hsv(title_hue, 0.8, 1.0), z=100)
    c.draw_text(2, c.h - 1, 'volumetric clouds | light shafts | atmospheric scattering | crepuscular rays', DIM, z=100)
