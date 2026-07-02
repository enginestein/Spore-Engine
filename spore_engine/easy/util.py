from ..core.color import Color, PALETTES
from ..anim.anim import EASING

def map_range(value, in_min, in_max, out_min, out_max):
    if in_min == in_max:
        return out_min
    return out_min + (out_max - out_min) * (value - in_min) / (in_max - in_min)

def clamp(value, lo, hi):
    return max(lo, min(hi, value))

def smoothstep(t):
    return t * t * (3 - 2 * t)

def lerp_color(c1, c2, t):
    if c1 is None:
        return c2
    if c2 is None:
        return c1
    return Color(
        int(c1.r + (c2.r - c1.r) * t),
        int(c1.g + (c2.g - c1.g) * t),
        int(c1.b + (c2.b - c1.b) * t),
    )

def random_color(brightness=1.0):
    import random
    return Color(
        int(random.random() * 255 * brightness),
        int(random.random() * 255 * brightness),
        int(random.random() * 255 * brightness),
    )
