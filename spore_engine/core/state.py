from __future__ import annotations

from typing import Any

__all__ = [
    'SceneState',
    'SceneStateStore',
    'clear_scene_states',
    'list_scene_states',
    'scene_state',
]

#: Attribute names exposed as read-only properties on SceneState.
_READONLY = frozenset({'name', 't'})


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
        elif key in _READONLY:
            # 'name' and 't' are read-only properties. Without this branch an
            # assignment silently succeeded, landed in _d, and was then
            # unreachable - st.t = 0.0 left st.t unchanged but st.get('t')
            # returning the assigned value.
            raise AttributeError(
                f'{type(self).__name__}.{key} is read-only; '
                f'write to st[{key!r}] or st.setdefault({key!r}, ...) instead')
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


class SceneStateStore:
    """A named collection of :class:`SceneState` objects.

    The module-level :func:`scene_state` helper uses one shared default store,
    which is convenient for single-engine scripts. For anything long-lived -
    two engines in one process, a test suite, a server hosting several scenes -
    create your own store and pass it around instead, so one scene's state can
    never leak into another's.

        store = SceneStateStore()
        st = store.get('fireflies')
    """

    def __init__(self):
        self._states: dict = {}

    def get(self, name: str) -> SceneState:
        """Fetch (or create) the state registered under ``name``."""
        st = self._states.get(name)
        if st is None:
            st = SceneState(name)
            self._states[name] = st
        return st

    def clear(self) -> None:
        """Drop every state in this store."""
        self._states.clear()

    def names(self) -> list:
        """The names currently registered, in insertion order."""
        return list(self._states)

    def __len__(self) -> int:
        return len(self._states)

    def __contains__(self, name: str) -> bool:
        return name in self._states

    def __repr__(self) -> str:
        return f'SceneStateStore({len(self._states)} states)'


#: Shared default store used by the module-level helpers.
default_store = SceneStateStore()


def scene_state(name: str | None = None) -> SceneState:
    """Return the stable :class:`SceneState` for ``name`` (auto-created).

    ``name`` is required on purpose. The old signature defaulted to ``''``,
    which meant *every* caller that forgot the name silently shared one object
    process-wide - two independent engines would then read and write each
    other's state. If you genuinely want one shared unnamed state, say so
    explicitly with ``scene_state('')``.
    """
    if name is None:
        raise TypeError(
            'scene_state() needs a name; pass scene_state("my-scene"). '
            'Omitting it used to alias every caller to one shared global.')
    return default_store.get(name)


def clear_scene_states() -> None:
    """Drop all state in the shared default store (e.g. between scene
    switches). Prefer a private :class:`SceneStateStore` when you need
    isolation."""
    default_store.clear()


def list_scene_states() -> list:
    """Names registered in the shared default store."""
    return default_store.names()
