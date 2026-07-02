import math
import random
from spore_engine.core.color import Color, Gradient, WHITE, BLACK, DIM
from spore_engine.sim.noise import PerlinNoise
from spore_engine.gen.scenery import DayNightCycle

_LS = None

def scene_landscape(c, hr, t, pt, dt):
    global _LS
    if _LS is None:
        _LS = {
            'n': PerlinNoise(42),
            'n2': PerlinNoise(99),
            'cycle': DayNightCycle(cycle_duration=30.0), # 30s day/night
            'stars': [(random.random(), random.random()) for _ in range(50)]
        }
    
    W, H2 = hr.w, hr.h
    cycle = _LS['cycle']
    cycle.update(dt)
    
    phase = cycle.phase
    sky_base = cycle.sky_color
    amb = cycle.ambient_brightness
    
    for y in range(H2 // 2 + 4):
        ty = y / (H2 // 2)
        if 0.2 < phase < 0.8:
            c_top = sky_base
            hue_shift = 0.5 + 0.3*math.sin(t*0.2)
            c_bot = sky_base.lerp(Color(255, 200, 150), 0.5) if phase > 0.6 else sky_base.lerp(Color(200, 230, 255), 0.5)
        else:
            c_top = Color(2, 2, 10)
            c_bot = sky_base
        col = c_top.lerp(c_bot, ty)
        for x in range(W):
            hr.set_pixel_z(x, y, col, -100)

    # 2. Celestial Bodies
    sun_x = int(W * phase * 1.2 - W * 0.1)
    sun_y = int(H2 * 0.45 - math.sin(phase * math.pi) * H2 * 0.35)
    
    if cycle.is_day or (0.1 < phase < 0.9):
        # Draw Sun/Moon
        is_sun = 0.2 < phase < 0.75
        body_col = Color(255, 255, 200) if is_sun else Color(200, 200, 255)
        r = 8 if is_sun else 5
        for dy in range(-r, r+1):
            for dx in range(-r, r+1):
                d = math.hypot(dx, dy)
                px, py = sun_x + dx, sun_y + dy
                if 0 <= px < W and 0 <= py < H2:
                    if d < r:
                        hr.set_pixel_z(px, py, body_col, 80)
                    elif d < r + 2:
                        hr.set_pixel_z(px, py, body_col.mul(0.3), 70)

    # Stars at night
    if amb < 0.5:
        for sx, sy in _LS['stars']:
            px, py = int(sx * W), int(sy * H2 * 0.4)
            twinkle = 0.5 + 0.5 * math.sin(t * 3 + sx * 100)
            if twinkle > 0.8:
                hr.set_pixel_z(px, py, WHITE.mul(1.0 - amb), 10)

    # 3. Mountains with Dynamic Shading
    mb = int(H2 * 0.65)
    n2 = _LS['n2']
    for x in range(W):
        # Height function
        h_val = 0.2 + 0.15 * math.sin(x * 0.02) + 0.05 * math.sin(x * 0.05)
        h_val += n2.noise1(x * 0.03) * 0.1
        top = mb - int(h_val * H2)
        
        for y in range(top, mb):
            # Shading depends on sun position
            dx_sun = (x - sun_x) / W
            shade = 0.5 + dx_sun * 0.5 # Basic directional shading
            shade = max(0.2, min(1.0, shade)) * amb
            
            # Base mountain color (Blueish-Grey)
            base_col = Color(40, 50, 80).lerp(Color(20, 20, 40), (y - top) / (mb - top))
            col = base_col.mul(shade)
            
            # Snow caps
            if y < top + 3 and h_val > 0.25:
                col = Color(200, 210, 255).mul(amb + 0.2)
                
            hr.set_pixel_z(x, y, col, 20)

    water_y = mb
    for y in range(water_y, H2):
        ty = (y - water_y) / (H2 - water_y)
        for x in range(W):
            distortion = int(math.sin(x * 0.2 + t * 4) * 2)
            ref_col = sky_base.mul(0.5).lerp(Color(20, 40, 80), ty)
            ripple = math.sin(x * 0.4 + t * 2) * math.sin(y * 0.2 + t * 1.5) * 0.15
            hr.set_pixel_z(x, y, ref_col.mul(1.0 + ripple + 0.1*math.sin(x*0.1+t*3)), 10)

    hr.to_canvas(c)
    c.draw_text(2, 0, f"Landscape — {cycle.phase*24:02.0f}:00", Color(100, 200, 255), z=100)
