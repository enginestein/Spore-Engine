import math, random
from spore_engine import *
from spore_engine.core.color import *
from spore_engine.sim.physics import PhysicsWorld, Body
from spore_engine.sim.fluid import FluidSim, WaveSim
from spore_engine.gen.terrain import Terrain

SHADE = ' .:-=+*#%@'

_fl = None
def scene_fluid(c, hr, t, pt, dt):
    global _fl
    if _fl is None:
        _fl = FluidSim(c.w, c.h, 0.0001, 0.0001)
    mx, my = c.w//2, c.h//2
    _fl.add_velocity(mx+int(math.sin(t)*5), my+int(math.cos(t*0.7)*3),
                     0.5+math.sin(t*2)*0.3, 0.3+math.cos(t*1.3)*0.2, 4)
    _fl.add_dye(mx+int(math.sin(t)*5), my+int(math.cos(t*0.7)*3), 1.5, 4)
    _fl.step()
    _fl.render(c, t=t, mode='dye')
    c.draw_text(2, 0, "Fluid Simulation", Color(100, 200, 255), z=100)

_pw = None
def scene_physics(c, hr, t, pt, dt):
    global _pw
    if _pw is None:
        _pw = PhysicsWorld(gravity=15, bounds_x=c.w, bounds_y=c.h)
        for i in range(15):
            b = Body(random.uniform(3,c.w-3), random.uniform(1,5),
                     random.uniform(0.8,2.0), random.uniform(0.5,2),
                     Color.from_hsv(random.random(),0.8,0.9))
            b.restitution = random.uniform(0.4,0.8)
            b.vel.x = random.uniform(-10,10)
            _pw.add_body(b)
        PhysicsWorld.chain(_pw, c.w//2, 3, 10, 2.2, 0.6, Color(180,200,255))
        PhysicsWorld.cloth(_pw, c.w//2-6, 3, 8, 5, 1.8, 0.3, Color(150,200,255))
    _pw.step(dt, 4)
    for y in range(c.h):
        ty = y / c.h
        for x in range(c.w):
            n = (math.sin(x*0.03+t*0.2)+math.cos(y*0.05+t*0.1))*0.5+0.5
            c.set_pixel(x, y, ' ', bg=Color(int(3+n*8), int(2+n*5), int(8+n*20)), z=-100)
    _pw.render(c, show_trails=True)
    c.draw_text(2, 0, "Physics Engine", Color(150, 200, 255), z=100)

_tr = None
def scene_terrain(c, hr, t, pt, dt):
    global _tr
    if _tr is None:
        _tr = Terrain(c.w, c.h, 42)
    _tr.generate(0.05, 6, 0.5)
    _tr.render_topdown(c, grad=Gradient(Color(0,40,80),Color(50,120,50),Color(100,180,50),
                                        Color(160,140,40),Color(180,120,60),Color(200,200,200)))
    c.draw_text(2, 0, "Perlin Terrain", Color(100, 220, 100), z=100)

_wv = None
def scene_waves(c, hr, t, pt, dt):
    global _wv
    if _wv is None:
        _wv = WaveSim(c.w, c.h, 0.985)
    _wv.splash(random.randint(0,c.w-1), random.randint(0,c.h-1), 0.5+random.random(), 2)
    for _ in range(2):
        _wv.step()
    _wv.render(c, t=t)
    c.draw_text(2, 0, "Wave Simulation", Color(100, 180, 255), z=100)
