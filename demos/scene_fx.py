import math, random
from spore_engine import *
from spore_engine.core.color import *
from spore_engine.fx.effects import plasma, fire, matrix_rain
from spore_engine.fx.textfx import glitch_text

SHADE = ' .:-=+*#%@'

_fb = None
def scene_fire_plasma(c, hr, t, pt, dt):
    global _fb
    fw, fh = c.w-10, min(20, c.h//4)
    fx, fy = 5, c.h-fh-3
    if _fb is None or len(_fb) != fh or len(_fb[0]) != fw:
        _fb = [[0.0]*fw for _ in range(fh)]
    plasma(c, t, w=c.w, h=c.h//2, palette='neon')
    fire(c, t, _fb, fx, fy, fw, fh)
    for i in range(c.w):
        c.set_pixel(i, c.h//2, '─', Color.from_hsv((t*0.05+i*0.001)%1.0, 0.5, 0.3))
    c.draw_text(2, 0, "Fire + Plasma", Color(255, 150, 50), z=100)

def scene_fireworks(c, hr, t, pt, dt):
    # Dark night sky gradient
    grad = Gradient(Color(0, 0, 10), Color(0, 0, 40), Color(20, 10, 50))
    for y in range(c.h):
        for x in range(c.w):
            c.set_pixel(x, y, ' ', bg=grad.at(y/c.h), z=-100)
            
    # Launch new fireworks randomly
    if random.random() < 0.08:
        cx = random.uniform(c.w*0.1, c.w*0.9)
        cy = random.uniform(c.h*0.1, c.h*0.4)
        palettes = ['fire', 'neon', 'sunset', 'ice', 'forest']
        pal = PALETTES[random.choice(palettes)]
        # Add some variation in burst size
        pt.emit(cx, cy, random.randint(30, 70), pal)
        
    pt.update_and_render(c, dt)
    c.draw_text(2, 0, "Fireworks", Color(255, 200, 100), z=100)

_mr_drops = None
def scene_matrix(c, hr, t, pt, dt):
    global _mr_drops
    if _mr_drops is None:
        _mr_drops = []
        for x in range(c.w):
            if random.random() < 0.4:
                _mr_drops.append({
                    'x': x,
                    'y': random.uniform(-c.h, 0),
                    'speed': random.uniform(0.4, 1.0),
                    'len': random.randint(10, 25),
                })

    # Pure black background for maximum contrast
    for y in range(c.h):
        for x in range(c.w):
            c.set_pixel(x, y, ' ', bg=BLACK, z=-100)

    # Use the overhauled core matrix_rain effect
    matrix_rain(c, t, _mr_drops)

    # Subtle scanline effect
    for y in range(0, c.h, 2):
        for x in range(c.w):
            cell = c.buffer[y][x]
            if cell.fg:
                cell.fg = cell.fg.mul(0.8)

    c.draw_text(2, 0, "Matrix Rain", Color(0, 255, 0), z=100)

_stars = None
def scene_starfield(c, hr, t, pt, dt):
    global _stars
    if _stars is None:
        _stars = [[random.uniform(-1,1)*30,random.uniform(-1,1)*15,random.uniform(0.2,2.0)]
                  for _ in range(200)]
    for y in range(c.h):
        ty = y / c.h
        col = Color.from_hsv(0.65-ty*0.15, 0.4, 0.03+ty*0.08)
        for x in range(c.w):
            c.set_pixel(x, y, ' ', bg=col, z=-100)
    speed = 2 + math.sin(t*0.2)*1.5
    cx2, cy2 = c.w//2, c.h//2
    for s in _stars:
        s[2] -= speed*0.02
        if s[2] < 0.1:
            s[0] = random.uniform(-1,1)*30; s[1]=random.uniform(-1,1)*15; s[2]=2.0
            continue
        px = int(cx2 + s[0]/s[2])
        py = int(cy2 + s[1]/s[2])
        if 0 <= px < c.w and 0 <= py < c.h:
            b = min(1.0, 0.5/(s[2]*s[2]))
            hue = (t*0.02+s[0]*0.01)%1.0
            ch = '·' if b<0.3 else ('✦' if b>0.7 else '★')
            c.set_pixel(px, py, ch, Color.from_hsv(hue,0.9,0.5+b*0.5))
            if b > 0.6:
                for dx,dy in [(-1,0),(1,0),(0,-1),(0,1)]:
                    c.set_pixel(px+dx, py+dy, '·', Color.from_hsv(hue,0.6,b*0.3))
    c.draw_text(2, 0, f"Starfield — {speed:.1f}x", Color(150, 200, 255), z=100)

def scene_audio(c, hr, t, pt, dt):
    for y in range(c.h):
        for x in range(c.w):
            n = (math.sin(x*0.02+t*0.1)*math.cos(y*0.03+t*0.08))*0.5+0.5
            c.set_pixel(x, y, ' ', bg=Color(int(2+n*8),int(1+n*4),int(5+n*15)), z=-100)
    bw = max(2, c.w//30)
    total = bw+1
    nb = c.w//total
    for i in range(nb):
        freq = (i+1)*0.5+math.sin(t*0.3+i*0.2)*0.3
        val = 0.3+0.5*(0.5+0.5*math.sin(t*freq+i*1.5))
        val += 0.2*math.sin(t*2.5+i*3.7)
        val = max(0.05, min(0.95, val))
        bh = int(val*c.h*0.7)
        bx = i*total
        hue = i/nb
        for bj in range(bh):
            y = c.h-2-bj
            t_ = bj/max(1,bh)
            c.set_pixel(bx, y, '█', Color.from_hsv(hue+t*0.02,0.8,0.3+t_*0.7))
        for bj in range(bh-1, -1, -1):
            y = c.h-2-bj
            if bj == bh-1:
                c.set_pixel(bx, y, '▀', Color.from_hsv(hue+t*0.02,0.9,1.0))
    c.draw_text(2, 0, "Audio Viz", Color(100, 255, 200), z=100)
