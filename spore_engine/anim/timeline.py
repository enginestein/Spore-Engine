from __future__ import annotations
from typing import Any
from collections.abc import Callable
from ..core.color import Color
from .anim import EASING, lerp, lerp_color, lerp_tuple


class Keyframe:
    def __init__(self, time: float, value: Any, easing: str = 'linear'):
        self.time = time
        self.value = value
        self.easing = easing

    def __repr__(self):
        return f'Keyframe({self.time}: {self.value}, {self.easing})'


class Track:
    def __init__(self, name: str = '', default: Any = 0.0):
        self.name = name
        self.keyframes: list[Keyframe] = []
        self.default = default
        self._lerp_mode = 'float'

    def add_keyframe(self, time: float, value: Any, easing: str = 'linear'):
        self.keyframes.append(Keyframe(time, value, easing))
        self.keyframes.sort(key=lambda k: k.time)
        return self

    def remove_keyframe(self, time: float):
        self.keyframes = [k for k in self.keyframes if k.time != time]

    def get_value(self, time: float) -> Any:
        if not self.keyframes:
            return self.default
        if len(self.keyframes) == 1:
            return self.keyframes[0].value
        if time <= self.keyframes[0].time:
            return self.keyframes[0].value
        if time >= self.keyframes[-1].time:
            return self.keyframes[-1].value
        for i in range(len(self.keyframes) - 1):
            a, b = self.keyframes[i], self.keyframes[i + 1]
            if a.time <= time <= b.time:
                t = (time - a.time) / (b.time - a.time) if b.time > a.time else 0
                ease_fn = EASING.get(b.easing, EASING['linear'])
                t = ease_fn(t)
                return self._interpolate(a.value, b.value, t)
        return self.default

    def _interpolate(self, a: Any, b: Any, t: float) -> Any:
        if isinstance(a, (int, float)) and isinstance(b, (int, float)):
            return lerp(a, b, t)
        if isinstance(a, Color) and isinstance(b, Color):
            return lerp_color(a, b, t)
        if isinstance(a, tuple) and isinstance(b, tuple) and len(a) == len(b):
            return lerp_tuple(a, b, t)
        return a if t < 0.5 else b

    @property
    def duration(self) -> float:
        if not self.keyframes:
            return 0
        return self.keyframes[-1].time

    @property
    def key_count(self) -> int:
        return len(self.keyframes)

    def __repr__(self):
        return f'Track({self.name!r}, {self.key_count} keys)'


class Timeline:
    def __init__(self, duration: float = 5.0, loop: bool = False,
                 yoyo: bool = False, autoplay: bool = True):
        self.duration = duration
        self.loop = loop
        self.yoyo = yoyo
        self.tracks: dict[str, Track] = {}
        self.time = 0.0
        self._playing = autoplay
        self._forward = True
        self._done = False
        self._speed = 1.0
        self._callbacks: dict[str, list[tuple[float, Callable]]] = {}

    def add_track(self, name: str, default: Any = 0.0) -> Track:
        if name not in self.tracks:
            self.tracks[name] = Track(name, default)
        return self.tracks[name]

    def get_track(self, name: str) -> Track | None:
        return self.tracks.get(name)

    def add_keyframe(self, track_name: str, time: float,
                     value: Any, easing: str = 'linear'):
        t = self.add_track(track_name)
        t.add_keyframe(time, value, easing)
        if time > self.duration:
            self.duration = time
        return self

    def on(self, event: str, callback: Callable):
        if event == 'complete':
            self._callbacks.setdefault('complete', []).append(callback)
        return self

    @property
    def playing(self) -> bool:
        return self._playing

    @playing.setter
    def playing(self, val: bool):
        self._playing = val

    def play(self):
        self._playing = True

    def pause(self):
        self._playing = False

    def stop(self):
        self._playing = False
        self.time = 0.0
        self._forward = True
        self._done = False

    def seek(self, time: float):
        self.time = max(0, min(self.duration, time))
        self._done = False

    def update(self, dt: float):
        if not self._playing or self._done:
            return
        dt *= self._speed
        if self._forward:
            self.time += dt
            if self.time >= self.duration:
                if self.yoyo:
                    self._forward = False
                    self.time = self.duration - (self.time - self.duration)
                elif self.loop:
                    self.time = self.time % self.duration
                else:
                    self.time = self.duration
                    self._playing = False
                    self._done = True
                    for cb in self._callbacks.get('complete', []):
                        cb()
        else:
            self.time -= dt
            if self.time <= 0:
                if self.loop or self.yoyo:
                    self._forward = True
                    self.time = 0
                else:
                    self.time = 0
                    self._playing = False
                    self._done = True
                    for cb in self._callbacks.get('complete', []):
                        cb()

    def get_value(self, track_name: str) -> Any:
        track = self.tracks.get(track_name)
        if track is None:
            return None
        return track.get_value(self.time)

    def apply_to(self, obj, attr_map: dict[str, str]):
        for track_name, obj_attr in attr_map.items():
            val = self.get_value(track_name)
            if val is not None:
                setattr(obj, obj_attr, val)

    @property
    def progress(self) -> float:
        return self.time / self.duration if self.duration > 0 else 0

    @property
    def done(self) -> bool:
        return self._done

    def all_values(self) -> dict[str, Any]:
        return {name: track.get_value(self.time)
                for name, track in self.tracks.items()}

    def __repr__(self):
        return (f'Timeline({self.time:.1f}/{self.duration:.1f}s, '
                f'{"playing" if self._playing else "paused"}, '
                f'{len(self.tracks)} tracks)')
