"""Structural integrity checks for the package surface.

These guard against a specific failure mode that bit us during the lint
cleanup: a module imports names purely to re-export them from its
subpackage ``__init__``, and an "unused import" autofix silently deletes
one. The module still imports fine on its own, the subpackage ``__init__``
still references the name, and the package becomes unimportable.

The tests are intentionally exhaustive rather than clever -- they exist to
turn a confusing ``ImportError`` at ``import spore_engine`` time into a
named, isolated failure.
"""

from __future__ import annotations

import importlib
import pkgutil

import pytest

import spore_engine


def _iter_modules():
    """Every importable module in the package, including private ones."""
    for info in pkgutil.walk_packages(spore_engine.__path__, "spore_engine."):
        yield info.name


def _iter_packages():
    for info in pkgutil.walk_packages(spore_engine.__path__, "spore_engine."):
        if info.ispkg:
            yield info.name


def test_every_module_imports():
    """No module may fail to import.

    Covers both missing third-party extras (imported lazily, so they must not
    raise here) and names deleted by an over-eager linter.
    """
    failures = []
    for name in _iter_modules():
        try:
            importlib.import_module(name)
        except Exception as exc:
            failures.append(f"{name}: {type(exc).__name__}: {exc}")
    assert not failures, "modules failed to import:\n" + "\n".join(failures)


def test_every_all_entry_resolves():
    """Every name in every ``__all__`` must actually exist.

    An ``__all__`` that advertises a missing name only fails at the moment
    someone writes ``from spore_engine.fx import *``, which is exactly the
    kind of bug that ships.
    """
    failures = []
    for name in [*_iter_modules(), "spore_engine"]:
        module = importlib.import_module(name)
        for exported in getattr(module, "__all__", ()):
            if not hasattr(module, exported):
                failures.append(f"{name}.__all__ names missing {exported!r}")
    assert not failures, "\n".join(failures)


def test_all_entries_are_strings():
    """``__all__`` holding a non-string breaks ``import *`` confusingly."""
    for name in [*_iter_modules(), "spore_engine"]:
        module = importlib.import_module(name)
        for exported in getattr(module, "__all__", ()):
            assert isinstance(exported, str), f"{name}.__all__ has non-str {exported!r}"


@pytest.mark.parametrize("package", list(_iter_packages()))
def test_subpackage_init_is_importable(package):
    """Subpackage ``__init__`` files are the documented public API.

    They re-export from sibling modules, so they break the moment one of
    those modules stops providing a name.
    """
    assert importlib.import_module(package) is not None


def test_top_level_exports_are_deduplicated():
    """``__all__`` must not list the same name twice.

    Duplicates are harmless at runtime but usually mean a merge mistake, and
    ``from x import *`` silently keeps the last one.
    """
    seen = set()
    duplicates = []
    for exported in getattr(spore_engine, "__all__", ()):
        if exported in seen:
            duplicates.append(exported)
        seen.add(exported)
    assert not duplicates, f"duplicate __all__ entries: {sorted(set(duplicates))}"
