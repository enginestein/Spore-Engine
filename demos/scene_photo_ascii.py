import math, os
from spore_engine import *
from spore_engine.core.color import *


_cache = None
_custom_path = os.path.join(os.path.dirname(__file__), 'image.jpg')


def _load_img(path, w, h):
    from PIL import Image, ImageEnhance
    img = Image.open(path).convert('RGB')
    img = ImageEnhance.Contrast(img).enhance(1.1)
    img = ImageEnhance.Color(img).enhance(1.05)
    return img.resize((w, h), Image.LANCZOS)


def scene_photo_ascii(c: Canvas, hr: HiResCanvas, t: float, pt, dt: float):
    global _cache
    path = _custom_path if os.path.isfile(_custom_path) else None

    bg = Gradient(Color(8, 6, 24), Color(22, 14, 38))
    c.gradient_fill(0, 0, c.w, c.h, bg, horizontal=False, z=-100)

    if not path:
        c.draw_text(c.w // 2 - 6, c.h // 2, 'no image', Color(255, 80, 80), z=100)
        return

    if _cache is None:
        _cache = _load_img(path, hr.w, hr.h)

    pixels = list(_cache.getdata())
    hr.clear()
    row_size = hr.w
    for y in range(hr.h):
        base = y * row_size
        for x in range(hr.w):
            r, g, b = pixels[base + x]
            hr.set_pixel(x, y, '@', Color(r, g, b))

    hr.to_canvas(c, z=0)

    c.draw_rect(0, 0, c.w, c.h, fg=Color(140, 120, 110), z=1, radius=1)
    c.draw_text(2, 0, 'Photo ASCII', Color(255, 200, 130), z=2)
    c.draw_text(2, c.h - 1,
                f'{os.path.basename(path)} | {hr.w}x{hr.h} | half-block', DIM, z=2)
