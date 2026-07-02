from spore_engine import *
from spore_engine.core.color import *
from spore_engine.gen.dungeon import DungeonGen, WorldGen


def scene_dungeon(c: Canvas, hr: HiResCanvas, t: float, pt, dt: float):
    h = c.h
    w = c.w

    phase = t % 12
    if phase < 5:
        dungeon = DungeonGen(40, 22, seed=int(t * 10))
        dungeon.generate(min_room_size=3, max_room_size=7, max_rooms=10, bsp_depth=3)
        dungeon.render(c, ox=0, oy=0)
        c.draw_rect(0, 0, w - 1, h - 1, '#', Color(200, 200, 200), z=0)
        c.draw_text(w // 2 - 8, 0, ' DUNGEON GEN ', Color(255, 220, 100), z=10)
        c.draw_text(w // 2 - 8, h - 1, ' rooms:' + str(len(dungeon.rooms)),
                     Color(180, 180, 200), z=10)
        for i, r in enumerate(dungeon.rooms):
            if r.type != 'normal':
                c.draw_text(r.x, r.y - 1, r.type[:5], Color(255, 255, 150), z=5)
    elif phase < 10:
        wg = WorldGen(40, 22, seed=int(t * 7))
        wg.generate(scale=0.06, octaves=5, rivers=3, settlements=4)
        wg.render(c, show_biomes=True, show_features=True)
        c.draw_rect(0, 0, w - 1, h - 1, '#', Color(200, 200, 200), z=0)
        c.draw_text(w // 2 - 8, 0, '  WORLD GEN  ', Color(100, 255, 150), z=10)
        c.draw_text(w // 2 - 8, h - 1,
                     'settlements:' + str(len(wg.settlements)) +
                     ' features:' + str(len(wg.features)),
                     Color(180, 180, 200), z=10)
    else:
        wg = WorldGen(40, 22, seed=int(t * 7))
        wg.generate(scale=0.06, octaves=5, rivers=3, settlements=4)
        wg.render(c, show_biomes=False, show_features=False)
        c.draw_rect(0, 0, w - 1, h - 1, '#', Color(200, 200, 200), z=0)
        c.draw_text(w // 2 - 8, 0, ' HEIGHTMAP  ', Color(255, 180, 100), z=10)

    for x in range(w):
        for y in range(h):
            px = c.get_pixel(x, y)
            if px and px.fg:
                hr.set_pixel(x * 2, y, px.char, px.fg, px.z)
                hr.set_pixel(x * 2 + 1, y, px.char, px.fg, px.z)
