import math, random
from spore_engine import *
from spore_engine.core.color import *
from spore_engine.fx.field import FieldSource, FieldSystem

_FD = None

def scene_field_demo(c, hr, t, pt, dt):
    global _FD
    w, h = c.w, c.h
    if _FD is None:
        fs = FieldSystem(150, w, h)
        fs.field.add(FieldSource(w * 0.35, h * 0.5, 4.0, 'vortex', min(w, h) * 0.35))
        fs.field.add(FieldSource(w * 0.65, h * 0.5, 3.0, 'vortex', min(w, h) * 0.3))
        _FD = {'fs': fs}

    s = _FD
    fs = s['fs']

    for y in range(h):
        for x in range(w):
            col = Color(int(x / w * 4), int(y / h * 3), int(6 + y / h * 8))
            c.set_pixel(x, y, ' ', bg=col, z=-100)

    num_sources = 2 + int(t * 0.08) % 3
    if num_sources == 2 and len(fs.field.sources) != 2:
        fs.field.sources = [
            FieldSource(w * 0.35, h * 0.5, 4.0, 'vortex', min(w, h) * 0.35),
            FieldSource(w * 0.65, h * 0.5, 3.0, 'vortex', min(w, h) * 0.3),
        ]
    elif num_sources == 3 and len(fs.field.sources) != 3:
        fs.field.sources = [
            FieldSource(w * 0.3, h * 0.4, 3.0, 'sink', min(w, h) * 0.3),
            FieldSource(w * 0.7, h * 0.4, 2.5, 'source', min(w, h) * 0.3),
            FieldSource(w * 0.5, h * 0.7, 2.0, 'vortex', min(w, h) * 0.25),
        ]
    elif num_sources == 4 and len(fs.field.sources) != 4:
        fs.field.sources = [
            FieldSource(w * 0.5, h * 0.5, 3.0, 'swirl', min(w, h) * 0.4),
            FieldSource(w * 0.3, h * 0.3, 2.0, 'source', min(w, h) * 0.2),
            FieldSource(w * 0.7, h * 0.3, 2.0, 'source', min(w, h) * 0.2),
            FieldSource(w * 0.5, h * 0.7, 2.0, 'sink', min(w, h) * 0.2),
        ]

    fs.width = w
    fs.height = h
    fs.update(dt)
    fs.render(c, t)

    for src in fs.field.sources:
        px, py = int(src.x), int(src.y)
        if 0 <= px < w and 0 <= py < h:
            hue = {'vortex': 0.6, 'sink': 0.0, 'source': 0.3, 'swirl': 0.8}.get(src.kind, 0.5)
            col = Color.from_hsv(hue, 0.9, 0.9)
            c.set_pixel(px, py, '♦', col, z=15)

    mode_names = ['Binary Vortex', 'Sink+Source+Vortex', 'Swirl Field']
    c.draw_text(2, 0, f"Field: {mode_names[num_sources-2]}", WHITE, z=100)
    c.draw_text(2, h - 1, "Modes cycle automatically", DIM, z=100)
