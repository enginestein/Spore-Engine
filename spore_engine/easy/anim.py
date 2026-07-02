from __future__ import annotations
import math
from ..anim.anim import Tween


class Anim:
    def __init__(self, sprite):
        self.sprite = sprite
        self._props = {}
        self._duration = 1.0
        self._easing = 'linear'
        self._loop = False
        self._yoyo = False
        self._delay = 0.0
        self._tween = None
        self._done = False
        self._started = False
        self._callback = None
        self._type = 'tween'
        self._spin_speed = 0
        self._pulse_min = 1.0
        self._pulse_max = 1.0
        self._pulse_period = 1.0
        self._wobble_amount = 0.0
        self._wobble_period = 1.0
        self._wait_time = 0.0
        self._accum = 0.0

    def to(self, x, y):
        self._props['x'] = (self.sprite.x, float(x))
        self._props['y'] = (self.sprite.y, float(y))
        return self

    def fade(self, opacity):
        self._props['opacity'] = (self.sprite.opacity, max(0, min(1, opacity)))
        return self

    def scale(self, s):
        self._props['scale_x'] = (self.sprite.scale_x, max(0.01, s))
        self._props['scale_y'] = (self.sprite.scale_y, max(0.01, s))
        return self

    def spin(self, speed=1.0):
        self._type = 'spin'
        self._spin_speed = speed
        self._loop = True
        return self

    def pulse(self, min_scale=0.8, max_scale=1.2, period=1.0):
        self._type = 'pulse'
        self._pulse_min = min_scale
        self._pulse_max = max_scale
        self._pulse_period = period
        self._loop = True
        return self

    def wobble(self, amount=2.0, period=1.0):
        self._type = 'wobble'
        self._wobble_amount = amount
        self._wobble_period = period
        self._loop = True
        return self

    def wait(self, seconds):
        self._type = 'wait'
        self._wait_time = seconds
        return self

    def over(self, duration):
        self._duration = max(0.01, duration)
        return self

    def ease(self, name):
        self._easing = name
        return self

    def loop(self, enabled=True):
        self._loop = enabled
        return self

    def yoyo(self, enabled=True):
        self._yoyo = enabled
        return self

    def delay(self, seconds):
        self._delay = max(0, seconds)
        return self

    def then(self, callback):
        self._callback = callback
        return self

    def forever(self):
        self._loop = True
        return self

    @property
    def done(self):
        return self._done

    def _start(self):
        if self._started:
            return
        self._started = True
        if self._type == 'wait':
            self._accum = 0.0
        elif self._type in ('spin', 'pulse', 'wobble'):
            self._accum = 0.0
        elif self._type == 'tween' and self._props:
            for name in self._props:
                start, end = self._props[name]
                self._props[name] = (start, end)
            self._tween = Tween(self._duration, self._easing, self._loop, self._yoyo)
            if self._delay > 0:
                self._tween.elapsed = -self._delay

    def update(self, dt):
        if self._done:
            return
        if not self._started:
            self._start()
        if self._type == 'wait':
            self._accum += dt
            if self._accum >= self._wait_time:
                self._done = True
                if self._callback:
                    self._callback()
            return
        if self._type == 'spin':
            self._accum += dt
            self.sprite.rotation += self._spin_speed * dt * math.pi * 2
            return
        if self._type == 'pulse':
            self._accum += dt
            t = (self._accum % self._pulse_period) / self._pulse_period
            mid = (self._pulse_min + self._pulse_max) / 2
            amp = (self._pulse_max - self._pulse_min) / 2
            s = mid + amp * math.sin(t * math.pi * 2)
            self.sprite.scale_x = s
            self.sprite.scale_y = s
            return
        if self._type == 'wobble':
            self._accum += dt
            t = (self._accum % self._wobble_period) / self._wobble_period
            self.sprite.x += math.sin(t * math.pi * 2) * self._wobble_amount * dt
            return
        if self._tween is None:
            self._done = True
            return
        self._tween.update(dt)
        v = self._tween.value
        for name, (start, end) in self._props.items():
            setattr(self.sprite, name, start + (end - start) * v)
        if self._tween.done:
            for name, (start, end) in self._props.items():
                setattr(self.sprite, name, end)
            self._done = True
            if self._callback:
                self._callback()
