import math, random
from spore_engine import *
from spore_engine.core.color import *
from spore_engine.sim.cellular import GameOfLife, Automata1D, WireWorld, LangtonsAnt, PATTERNS

_gol = None
def scene_game_of_life(c, hr, t, pt, dt):
    global _gol
    if _gol is None:
        _gol = GameOfLife(c.w, c.h)
        _gol.randomize(0.35)
        _gol.set_pattern(c.w//2-5, c.h//2-5, PATTERNS['glider_gun'])
    for _ in range(3):
        _gol.step()
    for y in range(c.h):
        for x in range(c.w):
            n = (math.sin(x*0.02+t*0.3)+math.cos(y*0.02+t*0.2))*0.5+0.5
            c.set_pixel(x, y, ' ', bg=Color(int(2+n*6), int(1+n*3), int(3+n*8)), z=-100)
    _gol.render(c)
    c.draw_text(2, 0, "Conway's Game of Life", Color(100,255,100), z=100)

_ca = None
def scene_automata_1d(c, hr, t, pt, dt):
    global _ca
    rules = [30, 90, 110, 150, 182, 73]
    rule = rules[int(t/6)%len(rules)]
    if _ca is None or t < 0.1:
        _ca = Automata1D(c.w, rule)
    _ca.render(c, 0, 0, min(c.h-2, 200), t=t)
    c.draw_text(2, c.h-2, f"1D Cellular — Rule {rule}", Color(100,200,255), z=100)

_ww = None
def scene_wireworld(c, hr, t, pt, dt):
    global _ww
    if _ww is None:
        _ww = WireWorld(c.w, c.h)
        for y in range(c.h):
            for x in range(c.w):
                if y==0 or y==c.h-1 or x==0 or x==c.w-1:
                    _ww.set(x, y, 3)
        for x in range(10, 30):
            _ww.set(x, c.h//2, 3)
        for x in range(15, 25):
            _ww.set(x, c.h//2+1, 3)
        _ww.set(5, c.h//2, 1)
        _ww.set(5, c.h//2-1, 3)
        for x in range(5, 15):
            _ww.set(x, c.h//2-2, 3)
    for _ in range(2):
        _ww.step()
    for y in range(c.h):
        for x in range(c.w):
            n = (math.sin(x*0.04+t*0.1)+math.cos(y*0.03))*0.5+0.5
            c.set_pixel(x, y, ' ', bg=Color(int(3+n*5), int(1+n*3), int(5+n*10)), z=-100)
    _ww.render(c)
    c.draw_text(2, 0, "WireWorld", Color(255,200,0), z=100)

_la = None
def scene_langton(c, hr, t, pt, dt):
    global _la
    if _la is None:
        _la = LangtonsAnt(c.w, c.h)
    for _ in range(20):
        _la.step()
    _la.render(c, t=t)
    c.draw_text(2, 0, "Langton's Ant", Color(255,255,100), z=100)
