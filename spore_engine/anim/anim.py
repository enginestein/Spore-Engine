from __future__ import annotations
import math

# -- EASING FUNCTIONS ---------------------------------------------

def linear(t: float) -> float:
    return max(0, min(1, t))

def quad_in(t: float) -> float:
    return t * t

def quad_out(t: float) -> float:
    return -t * (t - 2)

def quad_in_out(t: float) -> float:
    return 2 * t * t if t < 0.5 else -2 * t * t + 4 * t - 1

def cubic_in(t: float) -> float:
    return t * t * t

def cubic_out(t: float) -> float:
    return (t - 1) ** 3 + 1

def cubic_in_out(t: float) -> float:
    return 4 * t ** 3 if t < 0.5 else (2 * t - 2) ** 3 / 2 + 1

def quart_in(t: float) -> float:
    return t ** 4

def quart_out(t: float) -> float:
    return -((t - 1) ** 4 - 1)

def quart_in_out(t: float) -> float:
    return 8 * t ** 4 if t < 0.5 else -8 * (t - 1) ** 4 + 1

def quint_in(t: float) -> float:
    return t ** 5

def quint_out(t: float) -> float:
    return (t - 1) ** 5 + 1

def quint_in_out(t: float) -> float:
    return 16 * t ** 5 if t < 0.5 else (16 * (t - 1) ** 5 + 1) / 2 + 0.5

def sine_in(t: float) -> float:
    return 1 - math.cos(t * math.pi / 2)

def sine_out(t: float) -> float:
    return math.sin(t * math.pi / 2)

def sine_in_out(t: float) -> float:
    return -(math.cos(math.pi * t) - 1) / 2

def expo_in(t: float) -> float:
    return 0 if t == 0 else 2 ** (10 * (t - 1))

def expo_out(t: float) -> float:
    return 1 if t == 1 else 1 - 2 ** (-10 * t)

def expo_in_out(t: float) -> float:
    if t == 0 or t == 1: return t
    return 2 ** (20 * t - 10) / 2 if t < 0.5 else (2 - 2 ** (-20 * t + 10)) / 2

def circ_in(t: float) -> float:
    return 1 - math.sqrt(1 - t * t)

def circ_out(t: float) -> float:
    return math.sqrt(1 - (t - 1) ** 2)

def circ_in_out(t: float) -> float:
    return (1 - math.sqrt(1 - 4 * t * t)) / 2 if t < 0.5 else (math.sqrt(1 - (2 * t - 2) ** 2) + 1) / 2

def bounce_out(t: float) -> float:
    if t < 1 / 2.75: return 7.5625 * t * t
    if t < 2 / 2.75: return 7.5625 * (t - 1.5 / 2.75) ** 2 + 0.75
    if t < 2.5 / 2.75: return 7.5625 * (t - 2.25 / 2.75) ** 2 + 0.9375
    return 7.5625 * (t - 2.625 / 2.75) ** 2 + 0.984375

def bounce_in(t: float) -> float:
    return 1 - bounce_out(1 - t)

def bounce_in_out(t: float) -> float:
    return bounce_in(t * 2) / 2 if t < 0.5 else bounce_out(t * 2 - 1) / 2 + 0.5

def elastic_out(t: float) -> float:
    if t == 0 or t == 1: return t
    return 2 ** (-10 * t) * math.sin((t - 0.075) * 2 * math.pi / 0.3) + 1

def elastic_in(t: float) -> float:
    if t == 0 or t == 1: return t
    return -(2 ** (10 * (t - 1)) * math.sin((t - 1.075) * 2 * math.pi / 0.3))

def elastic_in_out(t: float) -> float:
    if t == 0 or t == 1: return t
    t2 = t * 2
    if t2 < 1:
        return -0.5 * (2 ** (10 * (t2 - 1)) * math.sin((t2 - 1.075) * 2 * math.pi / 0.3))
    return 0.5 * (2 ** (-10 * (t2 - 1)) * math.sin((t2 - 1.075) * 2 * math.pi / 0.3)) + 1

def back_in(t: float) -> float:
    return t * t * t - t * math.sin(t * math.pi)

def back_out(t: float) -> float:
    t2 = 1 - t
    return 1 - (t2 * t2 * t2 - t2 * math.sin(t2 * math.pi))

def back_in_out(t: float) -> float:
    if t < 0.5:
        t2 = 2 * t
        return 0.5 * (t2 * t2 * t2 - t2 * math.sin(t2 * math.pi))
    t2 = 1 - (2 * t - 1)
    return 0.5 * (1 - (t2 * t2 * t2 - t2 * math.sin(t2 * math.pi))) + 0.5

EASING = {
    'linear': linear,
    'quad_in': quad_in, 'quad_out': quad_out, 'quad_in_out': quad_in_out,
    'cubic_in': cubic_in, 'cubic_out': cubic_out, 'cubic_in_out': cubic_in_out,
    'quart_in': quart_in, 'quart_out': quart_out, 'quart_in_out': quart_in_out,
    'quint_in': quint_in, 'quint_out': quint_out, 'quint_in_out': quint_in_out,
    'sine_in': sine_in, 'sine_out': sine_out, 'sine_in_out': sine_in_out,
    'expo_in': expo_in, 'expo_out': expo_out, 'expo_in_out': expo_in_out,
    'circ_in': circ_in, 'circ_out': circ_out, 'circ_in_out': circ_in_out,
    'bounce_in': bounce_in, 'bounce_out': bounce_out, 'bounce_in_out': bounce_in_out,
    'elastic_in': elastic_in, 'elastic_out': elastic_out, 'elastic_in_out': elastic_in_out,
    'back_in': back_in, 'back_out': back_out, 'back_in_out': back_in_out,
}


# -- TWEEN ---------------------------------------------------------

class Tween:
    def __init__(self, duration: float = 1.0, easing: str = 'linear',
                 loop: bool = False, yoyo: bool = False):
        self.duration = duration
        self.easing = EASING.get(easing, linear)
        self.loop = loop
        self.yoyo = yoyo
        self.elapsed = 0.0
        self.forward = True
        self._done = False

    def update(self, dt: float):
        if self._done:
            return
        self.elapsed += dt
        if self.elapsed >= self.duration:
            if self.loop:
                self.elapsed = self.elapsed % self.duration
                if self.yoyo:
                    self.forward = not self.forward
            elif self.yoyo:
                self.forward = not self.forward
                self.elapsed = 0.0
            else:
                self.elapsed = self.duration
                self._done = True

    @property
    def value(self) -> float:
        t = min(1, self.elapsed / self.duration) if self.duration > 0 else 1
        v = self.easing(t)
        return v if self.forward else (1 - v)

    @property
    def done(self) -> bool:
        return self._done

    def reset(self):
        self.elapsed = 0.0
        self.forward = True
        self._done = False


# -- SEQUENCE ------------------------------------------------------

class Sequence:
    def __init__(self, *steps: tuple[float, str] | Tween):
        self.steps: list[Tween] = []
        for s in steps:
            if isinstance(s, Tween):
                self.steps.append(s)
            else:
                self.steps.append(Tween(duration=s[0], easing=s[1]))
        self.idx = 0
        self._done = False

    def update(self, dt: float):
        if self._done or self.idx >= len(self.steps):
            self._done = True
            return
        self.steps[self.idx].update(dt)
        if self.steps[self.idx].done:
            self.idx += 1
            if self.idx >= len(self.steps):
                self._done = True

    @property
    def value(self) -> float:
        if self._done or self.idx >= len(self.steps):
            return 1.0
        return self.steps[self.idx].value

    @property
    def done(self) -> bool:
        return self._done

    def reset(self):
        self.idx = 0
        self._done = False
        for s in self.steps:
            s.reset()


# -- OSCILLATOR ----------------------------------------------------

class Oscillator:
    def __init__(self, period: float = 1.0, min_val: float = 0.0,
                 max_val: float = 1.0, offset: float = 0.0):
        self.period = period
        self.min = min_val
        self.max = max_val
        self.offset = offset

    def value(self, t: float) -> float:
        phase = (t + self.offset) / self.period * 2 * math.pi
        return self.min + (self.max - self.min) * (0.5 + 0.5 * math.sin(phase))


# -- TIMER / TICKER ------------------------------------------------

class Ticker:
    def __init__(self, interval: float = 1.0, repeat: bool = True):
        self.interval = interval
        self.repeat = repeat
        self.elapsed = 0.0
        self._done = False

    def update(self, dt: float) -> bool:
        if self._done:
            return False
        self.elapsed += dt
        if self.elapsed >= self.interval:
            self.elapsed = 0.0
            if not self.repeat:
                self._done = True
            return True
        return False

    def reset(self):
        self.elapsed = 0.0
        self._done = False


# -- ENTITY ---------------------------------------------------------

class Entity:
    def __init__(self, x: float = 0, y: float = 0):
        self.x = x
        self.y = y
        self.scale_x = 1.0
        self.scale_y = 1.0
        self.rotation = 0.0
        self.opacity = 1.0
        self.visible = True
        self.data: dict = {}

    def set_pos(self, x: float, y: float):
        self.x = x
        self.y = y

    def move(self, dx: float, dy: float):
        self.x += dx
        self.y += dy


# -- ANIMATOR -------------------------------------------------------

class Animator:
    def __init__(self, target: Entity, duration: float = 1.0,
                 easing: str = 'linear', loop: bool = False, yoyo: bool = False):
        self.target = target
        self.tweens: dict[str, Tween] = {}
        self.start_vals: dict[str, float] = {}
        self.end_vals: dict[str, float] = {}
        self.active = False

    def animate(self, prop: str, end_val: float, duration: float = 1.0,
                easing: str = 'linear', loop: bool = False, yoyo: bool = False):
        start = getattr(self.target, prop, 0.0)
        self.start_vals[prop] = start
        self.end_vals[prop] = end_val
        self.tweens[prop] = Tween(duration, easing, loop, yoyo)
        self.active = True
        return self

    def update(self, dt: float):
        if not self.active:
            return
        done = True
        for prop, tween in self.tweens.items():
            tween.update(dt)
            if not tween.done:
                done = False
            v = tween.value
            cur = self.start_vals[prop]
            end = self.end_vals[prop]
            setattr(self.target, prop, cur + (end - cur) * v)
        if done:
            self.active = False

    @property
    def done(self) -> bool:
        return not self.active or all(t.done for t in self.tweens.values())

    def reset(self):
        for t in self.tweens.values():
            t.reset()
        self.active = True


# -- PATH -----------------------------------------------------------

class Path:
    def __init__(self, *points: tuple[float, float]):
        self.points = list(points)

    def add_point(self, x: float, y: float):
        self.points.append((x, y))

    @property
    def length(self) -> float:
        return sum(
            math.hypot(self.points[i + 1][0] - self.points[i][0],
                       self.points[i + 1][1] - self.points[i][1])
            for i in range(len(self.points) - 1)
        )

    def point_at(self, t: float) -> tuple[float, float]:
        if not self.points:
            return (0, 0)
        if len(self.points) == 1:
            return self.points[0]
        t = max(0, min(1, t))
        total_len = self.length
        target_dist = t * total_len
        accumulated = 0.0
        for i in range(len(self.points) - 1):
            seg_len = math.hypot(self.points[i + 1][0] - self.points[i][0],
                                 self.points[i + 1][1] - self.points[i][1])
            if accumulated + seg_len >= target_dist:
                seg_t = (target_dist - accumulated) / seg_len if seg_len > 0 else 0
                x = self.points[i][0] + (self.points[i + 1][0] - self.points[i][0]) * seg_t
                y = self.points[i][1] + (self.points[i + 1][1] - self.points[i][1]) * seg_t
                return (x, y)
            accumulated += seg_len
        return self.points[-1]

    def render(self, canvas, char='.', fg=None, z=0):
        for i in range(len(self.points) - 1):
            canvas.draw_line(round(self.points[i][0]), round(self.points[i][1]),
                             round(self.points[i + 1][0]), round(self.points[i + 1][1]),
                             char, fg, z=z)


class PathFollower:
    def __init__(self, path: Path, duration: float = 3.0, loop: bool = True,
                 easing: str = 'linear'):
        self.path = path
        self.tween = Tween(duration, easing, loop=loop)
        self.progress = 0.0

    def update(self, dt: float):
        self.tween.update(dt)
        self.progress = self.tween.value

    def get_position(self) -> tuple[float, float]:
        return self.path.point_at(self.progress)

    @property
    def done(self) -> bool:
        return self.tween.done


# -- INTERPOLATORS -------------------------------------------------

# Single canonical versions live in core.util (clamp/smoothstep/lerp/
# lerp_color); anim re-exports those same objects so the names never
# drift between subpackages. lerp_tuple keeps a private clamped helper
# so out-of-range t values interpolate safely.
from ..core.util import lerp, lerp_color

def _lerp_capped(a, b, t):
    return a + (b - a) * max(0, min(1, t))


def lerp_tuple(a: tuple, b: tuple, t: float) -> tuple:
    return tuple(_lerp_capped(a[i], b[i], t) for i in range(len(a)))
