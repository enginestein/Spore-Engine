from __future__ import annotations
from typing import Any


class SceneState:
    """Attribute-access scratch state for a scene.

    Replaces the hand-rolled ``_XX = None`` module singleton pattern used by
    most demos::

        st = scene_state('fireflies')
        st.flies = st.get('flies') or _make_flies(w, h)
    """

    def __init__(self, name: str = ''):
        object.__setattr__(self, '_name', name)
        object.__setattr__(self, '_d', {})
        object.__setattr__(self, '_time', 0.0)

    @property
    def name(self) -> str:
        return self._name

    @property
    def t(self) -> float:
        """Scene-local time, advanced by ``tick``."""
        return self._time

    def tick(self, dt: float) -> float:
        self._time += dt
        return self._time

    def __getattr__(self, key: str) -> Any:
        if key.startswith('_'):
            raise AttributeError(key)
        try:
            return self._d[key]
        except KeyError:
            raise AttributeError(key) from None

    def __setattr__(self, key: str, value: Any) -> None:
        if key.startswith('_'):
            object.__setattr__(self, key, value)
        else:
            self._d[key] = value

    def __delattr__(self, key: str) -> None:
        if key.startswith('_'):
            object.__delattr__(self, key)
        else:
            self._d.pop(key, None)

    def get(self, key: str, default: Any = None, factory=None) -> Any:
        """fetch with a default; ``factory`` lazily builds the default once."""
        if key in self._d:
            return self._d[key]
        if factory is not None:
            self._d[key] = factory()
            return self._d[key]
        return default

    def __getitem__(self, key: str) -> Any:
        return self._d[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self._d[key] = value

    def setdefault(self, key: str, default: Any = None) -> Any:
        return self._d.setdefault(key, default)

    def update(self, other: dict) -> None:
        self._d.update(other)

    def __contains__(self, key: str) -> bool:
        return key in self._d

    def keys(self):
        return self._d.keys()

    def items(self):
        return self._d.items()

    def clear(self) -> None:
        self._d.clear()

    def __len__(self) -> int:
        return len(self._d)

    def __repr__(self) -> str:
        return f'SceneState({self._name!r}, {len(self._d)} keys)'


_states: dict[str, SceneState] = {}


def scene_state(name: str = '') -> SceneState:
    """Return the stable SceneState for a scene name (auto-created)."""
    st = _states.get(name)
    if st is None:
        st = SceneState(name)
        _states[name] = st
    return st


def clear_scene_states() -> None:
    """Drop all registered scene state (e.g. between scene switches)."""
    _states.clear()


def list_scene_states() -> list[str]:
    return list(_states.keys())