"""Tests for simulation state that has to survive a terminal resize.

A terminal can be resized at any moment, and the engine's simulators cache
grids sized to whatever canvas they were first built for. Every one of them
needs a real resize path - assigning ``sim.w``/``sim.h`` by hand leaves the
underlying arrays at their original size while every accessor trusts the new
numbers, and the failure shows up as an IndexError deep inside a render loop.
"""

from __future__ import annotations

import pytest

from spore_engine import Canvas
from spore_engine.gen.erosion import ErosionSim


# --- ErosionSim ----------------------------------------------------------

def _sim(w, h):
    s = ErosionSim(w, h)
    s.generate_heightmap()
    return s


def test_erosion_resize_updates_every_grid():
    s = _sim(30, 10)
    s.resize(12, 6)
    assert (s.w, s.h) == (12, 6)
    for name in ('heightmap', 'water', 'sediment'):
        grid = getattr(s, name)
        assert len(grid) == 6, f'{name} has {len(grid)} rows'
        assert all(len(row) == 12 for row in grid), f'{name} row width wrong'


def test_erosion_resize_preserves_existing_terrain():
    """A resize should not blank out the ground that is still on screen."""
    s = _sim(30, 10)
    before = [s.get_height(x, 5) for x in range(30)]
    s.resize(30, 10)
    after = [s.get_height(x, 5) for x in range(30)]
    assert before == after, 'a no-op resize changed the heightmap'


@pytest.mark.parametrize('size', [(80, 30), (12, 6), (2, 2), (1, 1)])
def test_erosion_survives_a_resize_to_any_size(size):
    s = _sim(30, 10)
    s.erode(200)
    s.resize(*size)
    # The whole point: the simulation keeps running afterwards.
    s.erode(100)
    s.add_rain(1.0)
    s.evaporate()
    s.render(Canvas(30, 10))


def test_erosion_grids_stay_in_sync_when_only_one_axis_changes():
    s = _sim(30, 10)
    s.resize(30, 24)
    assert len(s.heightmap) == 24
    assert all(len(row) == 30 for row in s.heightmap)
    s.resize(9, 24)
    assert all(len(row) == 9 for row in s.heightmap)


def test_erosion_accessors_are_bounds_safe():
    s = _sim(10, 5)
    for x, y in [(-1, 0), (0, -1), (10, 0), (0, 5), (999, 999), (-5, -5)]:
        assert isinstance(s.get_height(x, y), float)
        assert isinstance(s._total_height(x, y), float)


def test_erosion_erode_runs_on_a_degenerate_grid():
    """`randint(1, w-2)` is an empty range once w drops below 3."""
    for w, h in [(1, 1), (2, 2), (2, 10), (10, 2)]:
        s = ErosionSim(w, h)
        s.generate_heightmap()
        s.erode(20)


def test_erosion_resize_to_the_same_size_is_a_no_op():
    s = _sim(20, 8)
    s.erode(50)
    snap = [row[:] for row in s.heightmap]
    s.resize(20, 8)
    assert s.heightmap == snap
