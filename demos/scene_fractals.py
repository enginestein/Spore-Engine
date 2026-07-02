import math, random
from spore_engine import *
from spore_engine.core.color import *
from spore_engine.sim.cellular import ReactionDiffusion
from spore_engine.gen.lsystem import LSYSTEMS

SHADE = ' .:-=+*#%@'

def scene_mandelbrot(c, hr, t, pt, dt):
    zoom = 3.0*math.exp(-t*0.12)+0.3
    cx2, cy2 = -0.5+math.sin(t*0.05)*0.1, math.sin(t*0.07)*0.1
    mi = min(200, int(50+t*2))
    for py in range(c.h):
        for px in range(c.w):
            x0 = (px/c.w-0.5)*zoom+cx2
            y0 = (py/c.h-0.5)*zoom+cy2
            x, y = 0.0, 0.0
            it = 0
            while x*x+y*y < 4 and it < mi:
                xt = x*x - y*y + x0
                y = 2*x*y + y0
                x = xt
                it += 1
            if it == mi:
                c.set_pixel(px, py, ' ', bg=Color(0,0,5))
            else:
                n = it/mi
                hue = (n*2.5+t*0.02)%1.0
                c.set_pixel(px, py, '█', Color.from_hsv(hue,0.7,0.3+n*0.7))
    c.draw_text(2, 0, f"Mandelbrot — zoom {zoom:.1f}", Color(100, 200, 255), z=100)

_rd = None
def scene_reaction_diffusion(c, hr, t, pt, dt):
    global _rd
    if _rd is None:
        _rd = ReactionDiffusion(c.w, c.h, 0.045, 0.062)
    for _ in range(5):
        _rd.step()
    _rd.render(c, 0, 0, t)
    c.draw_text(2, 0, "Reaction-Diffusion", Color(200, 100, 255), z=100)

def scene_lsystem(c, hr, t, pt, dt):
    grad = Gradient.from_palette('sunset')
    for y in range(c.h):
        for x in range(c.w):
            c.set_pixel(x, y, '█', grad.at(y/c.h), z=-100)
    key = int(t/8) % len(LSYSTEMS)
    name = list(LSYSTEMS.keys())[key]
    ls = LSYSTEMS[name]
    ls.generate()
    ls.render(c, c.w//2, c.h-3, 2.8, t, Color(100,180+int(math.sin(t)*30),80))
    c.draw_text(2, 0, f"L-System — {name}", Color(100, 255, 150), z=100)

def scene_julia(c, hr, t, pt, dt):
    cx2, cy2 = -0.7*math.sin(t*0.1), 0.27015*math.cos(t*0.12)
    zoom = 3.0
    mi = 72
    for py in range(c.h):
        for px in range(c.w):
            zx = (px/c.w-0.5)*zoom
            zy = (py/c.h-0.5)*zoom
            it = 0
            while zx*zx+zy*zy < 4 and it < mi:
                xt = zx*zx - zy*zy + cx2
                zy = 2*zx*zy + cy2
                zx = xt
                it += 1
            if it == mi:
                c.set_pixel(px, py, ' ', bg=Color(2,1,6))
            else:
                n = it/mi
                hue = (n*4+t*0.03)%1.0
                c.set_pixel(px, py, '█', Color.from_hsv(hue,0.8,n**0.6))
    c.draw_text(2, 0, "Julia Sets", Color(255, 150, 200), z=100)
