from ..core.color import Color
from ..core.util import clamp, smoothstep, lerp_color

def map_range(value, in_min, in_max, out_min, out_max):
    if in_min == in_max:
        return out_min
    return out_min + (out_max - out_min) * (value - in_min) / (in_max - in_min)

def random_color(brightness=1.0):
    import random
    return Color(
        int(random.random() * 255 * brightness),
        int(random.random() * 255 * brightness),
        int(random.random() * 255 * brightness),
    )
