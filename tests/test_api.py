"""One namespace, one true version of each public name.

The whole package must not expose the same identifier from two subpackages
with different meanings (the historical Input/Camera/Scene clashes, plus the
pasted-over ``easy`` re-exports). This test makes that invariant explicit so
it cannot silently regress.
"""

import importlib
import inspect

import spore_engine

_SUBPACKAGES = ('core', 'fx', 'gen', 'render3d', 'sim', 'ui', 'anim',
                'easy', 'media')


def _publics(module):
    out = {}
    for name in dir(module):
        if name.startswith('_'):
            continue
        try:
            obj = getattr(module, name)
        except Exception:
            continue
        if inspect.ismodule(obj):
            continue
        out[name] = obj
    return out


def _submodules():
    return {s: importlib.import_module('spore_engine.' + s)
            for s in _SUBPACKAGES}


def test_no_cross_subpackage_name_collisions():
    seen = {}
    for sub, module in _submodules().items():
        for name, obj in _publics(module).items():
            prev = seen.get(name)
            if prev is not None and prev[1] is not obj:
                raise AssertionError(
                    f"'{name}' is exported by both {prev[0]} and {sub} with "
                    f"different objects ({prev[1]!r} vs {obj!r}); a name must "
                    f"mean the same thing package-wide")
            seen.setdefault(name, (sub, obj))


def test_top_level_matches_every_subpackage_object():
    for name, obj in _publics(spore_engine).items():
        for sub, module in _submodules().items():
            if hasattr(module, name) and getattr(module, name) is not obj:
                raise AssertionError(
                    f"top-level '{name}' is not the same object as "
                    f"spore_engine.{sub}.{name}")