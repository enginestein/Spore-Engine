import math
import random
from spore_engine import *
from spore_engine.core.color import *

_font = None
def scene_title(c, hr, t, pt, dt):
    global _font
    if _font is None:
        _font = Font.default_5x7()
    
    # Background plasma
    plasma(c, t, speed=0.5)
    
    # Animated title
    title = "SPORE ENGINE"
    y_off = int(math.sin(t * 2) * 2)
    _font.render_text_gradient(c, title, (c.w - len(title)*6)//2, c.h//2 - 5 + y_off, 
                              scale=1, gradient=Gradient.from_palette('neon'))
    
    # Subtitle
    c.draw_text((c.w - 20)//2, c.h//2 + 4, "A NEW DIMENSION OF TEXT", WHITE)
    
    # Floating particles
    for i in range(10):
        px = int((t * 5 + i * 20) % c.w)
        py = int(c.h/2 + 8 + math.sin(t + i) * 3)
        c.set_pixel(px, py, '*', Color.from_hsv((t*0.1 + i*0.1)%1.0, 0.8, 1.0))

_voxel = None
_hm = None
def scene_voxel_landscape(c, hr, t, pt, dt):
    global _voxel, _hm
    if _voxel is None:
        from spore_engine.gen.terrain import Terrain
        ter = Terrain(80, 80, seed=42)
        ter.generate_island(scale=0.04)
        _hm = ter.heightmap
        _voxel = VoxelScene(80, 80, _hm)
        
    c.clear()
    
    lx = t * 0.4
    amb = 0.4 + 0.3 * math.sin(t * 0.2)
    
    sky_hue = (0.6 + 0.1 * math.sin(t * 0.1)) % 1.0
    for y in range(c.h // 2 + 2):
        ty = y / (c.h/2)
        col = Color.from_hsv(sky_hue, 0.6 - ty * 0.3, 0.3 + ty * 0.5)
        for x in range(c.w):
            c.set_pixel(x, y, ' ', bg=col)
            
    sx = int(c.w * 0.7 + math.cos(lx) * 20)
    sy = int(c.h * 0.2 + math.sin(lx) * 10)
    if 0 <= sx < c.w and 0 <= sy < c.h:
        c.set_pixel(sx, sy, '☼', Color(255, 255, 200), z=50)
        for dx in range(-2, 3):
            for dy in range(-2, 3):
                d = math.hypot(dx, dy)
                if d <= 2.5 and (dx!=0 or dy!=0):
                    c.set_pixel(sx+dx, sy+dy, '·', Color(255, 200, 100).mul(0.3-0.1*d), z=49)

    _voxel.render(c, angle=t * 0.2, elevation=0.6, distance=100, 
                  light_angle=lx, amb=amb)
    
    c.draw_text(2, 0, "Cinematic Voxel Landscape", Color(180, 200, 255), z=100)

_bs = None
def scene_burning_ship(c, hr, t, pt, dt):
    global _bs
    if _bs is None:
        _bs = BurningShip(c.w, c.h, max_iter=64)
    
    zoom = 2.0 * math.exp(-t * 0.1) + 0.05
    # Center on one of the interesting areas
    _bs.render(c, center=(-1.75, -0.03), zoom=zoom, t=t)
    c.draw_text(2, 0, f"Burning Ship — zoom {zoom:.2f}", Color(255, 150, 50), z=100)

_nf = None
def scene_newton(c, hr, t, pt, dt):
    global _nf
    if _nf is None:
        _nf = NewtonFractal(c.w, c.h)
    
    _nf.render(c, zoom=2.0 + math.sin(t*0.5), t=t)
    c.draw_text(2, 0, "Newton Fractal", Color(150, 200, 255), z=100)

_fern = None
def scene_barnsley_fern(c, hr, t, pt, dt):
    global _fern
    if _fern is None:
        _fern = BarnsleyFern(c.w, c.h)
    
    # We don't clear the canvas to let it grow, but the demo loop might clear it.
    # So we draw many steps per frame.
    _fern.step(c, n=500, color=Color(0, 255, 0))
    c.draw_text(2, 0, "Barnsley Fern", Color(100, 255, 100), z=100)
