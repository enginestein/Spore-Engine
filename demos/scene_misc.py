import math, random
from spore_engine import *
from spore_engine.core.color import *
from spore_engine.fx.textfx import *
from spore_engine.fx.postfx import *
from spore_engine.gen.maze import Maze

SHADE = ' .:-=+*#%@'

def scene_textfx(c, hr, t, pt, dt):
    for y in range(c.h):
        for x in range(c.w):
            n = (math.sin(x*0.1+t*0.5)*math.cos(y*0.1+t*0.3))*0.5+0.5
            c.set_pixel(x, y, SHADE[int(n*9)], Color.from_hsv(n*0.3+t*0.02,0.5,0.15))
    ty = 2
    wave_text(c, 2, ty, "WAVE TEXT", t, 3, WHITE); ty += 3
    rainbow_text(c, 2, ty, "RAINBOW TEXT — EVERY CHAR A HUE", t); ty += 3
    sine_text(c, 2, ty, "SINE WAVE BOUNCE", t, 2, 2, Color(100,200,255)); ty += 3
    glitch_text(c, 2, ty, "GLITCH TEXT — R@NDOM C0RRUPTI0N", t, Color(0,255,100)); ty += 3
    fire_text(c, 2, ty, "FIRE TEXT — BURNING CHARACTERS", t); ty += 3
    gradient_text(c, 2, ty, "GRADIENT TEXT", t, Gradient(RED, YELLOW, CYAN, MAGENTA)); ty += 3
    bounce_text(c, 2, ty, "BOUNCE TEXT UP AND DOWN", t, Color(255,200,100))
    c.draw_text(2, c.h-1, "Text Effects", Color(200, 150, 255), z=100)

_mz = None
def scene_maze(c, hr, t, pt, dt):
    global _mz
    mw = min(20, c.w//2-2)
    mh = min(10, c.h//2-2)
    if _mz is None:
        _mz = Maze(mw, mh)
        _mz.generate_dfs(42)
        _mz.solve_bfs()
    for y in range(c.h):
        for x in range(c.w):
            n = (math.sin(x*0.05+t*0.1)*math.cos(y*0.05))*0.5+0.5
            c.set_pixel(x, y, ' ', bg=Color(int(5+n*10),int(3+n*8),int(10+n*15)))
    ox, oy = (c.w-len(_mz.grid[0]))//2, (c.h-len(_mz.grid))//2
    _mz.render(c, ox, oy, Color(100,150,255), YELLOW)
    c.draw_text(2, 0, "Maze — S=Start ★=Goal", GREEN, z=100)

_wd, _wt = [], 0
def scene_weather(c, hr, t, pt, dt):
    global _wd, _wt
    wt = int(t/10)%3
    if len(_wd)==0 or wt!=_wt:
        _wt=wt; _wd=[]
    if _wt==0:
        while len(_wd)<c.w*2:
            _wd.append([random.randint(0,c.w-1),random.uniform(-5,0),random.uniform(0.5,1.5)])
        for y in range(c.h):
            for x in range(c.w):
                n=(math.sin(x*0.05+t*0.3)+math.cos(y*0.04+t*0.2))*0.5+0.5
                c.set_pixel(x,y,' ',bg=Color(int(5+n*12),int(3+n*8),int(15+n*30)),z=-100)
        for d in _wd:
            x,y,spd=d; y+=spd
            if y>=c.h: y=-random.uniform(0,3); x=random.randint(0,c.w-1)
            d[1]=y
            if 0<=y<c.h:
                c.set_pixel(x,int(y),'│',Color.from_hsv(0.6,0.5,0.4+spd*0.4))
                c.set_pixel(x-1,int(y),'·',Color.from_hsv(0.6,0.3,0.15+spd*0.15),z=0)
        c.draw_text(2,0,"Weather — Rain",Color(150,150,255),z=100)
    elif _wt==1:
        while len(_wd)<80:
            _wd.append([random.randint(0,c.w-1),random.uniform(-5,c.h+5),random.uniform(0.2,0.6)])
        for y in range(c.h):
            for x in range(c.w):
                n=(math.sin(x*0.04+t*0.15)+math.cos(y*0.05+t*0.1))*0.5+0.5
                c.set_pixel(x,y,' ',bg=Color(int(10+n*15),int(10+n*12),int(20+n*30)),z=-100)
        for d in _wd:
            x,y,spd=d; y+=spd
            if y>=c.h: y=-random.uniform(0,5); x=random.randint(0,c.w-1)
            d[1]=y
            if 0<=y<c.h:
                b=0.5+spd*0.5
                c.set_pixel(x,int(y),'❄' if b>0.7 else '*',Color(200,200,255).mul(b))
        c.draw_text(2,0,"Weather — Snow",Color(200,220,255),z=100)
    else:
        for y in range(c.h):
            for x in range(c.w):
                n=(math.sin(x*0.08+t*0.2)+math.cos(y*0.06+t*0.15))*0.25+0.5
                c.set_pixel(x,y,' ',bg=Color(int(15+45*n),int(12+28*n),int(20+55*n)),z=-100)
        for _ in range(int(10+math.sin(t)*5)):
            x,y=random.randint(0,c.w-1),random.randint(0,c.h-1)
            c.set_pixel(x,y,'▒',Color(200,200,220).mul(0.5+random.random()*0.5))
        c.draw_text(2,0,"Weather — Fog",Color(180,190,200),z=100)

_pfx_t=0
def scene_postfx(c, hr, t, pt, dt):
    global _pfx_t
    _pfx_t+=dt
    for y in range(c.h):
        for x in range(c.w):
            d=math.hypot(x-c.w/2,y-c.h/2)/math.hypot(c.w/2,c.h/2)
            v=(math.sin(x*0.05+_pfx_t)*math.cos(y*0.05+_pfx_t*0.7))*0.5+0.5
            h=(d*0.5+_pfx_t*0.03)%1.0
            c.set_pixel(x,y,SHADE[int(v*9)],Color.from_hsv(h,0.6,0.3+v*0.7))
    fi=int(_pfx_t/4)%6
    names=['Chromatic Aberration','Box Blur','Edge Detect','Glow','Scanlines','Pixel+Vignette']
    if fi==1: box_blur(c,2)
    elif fi==2: edge_detect(c, Color(0,255,255), Color(0,0,0))
    elif fi==3: glow(c,0.5,3,0.4)
    elif fi==4: scanlines(c,0.3)
    elif fi==5: pixelate(c,4); vignette(c,0.4)
    else: chromatic_aberration(c,1)
    c.draw_text(2, 0, f"PostFX — {names[fi]}", Color(200, 180, 255), z=100)
