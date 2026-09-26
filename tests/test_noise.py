"""Tests for the noise generators in ``spore_engine.sim.noise``.

These cover two classes of defect that were found by smoke-testing every
public callable:

1. A function that raised on every call (``ValueNoise.noise2`` indexed its
   lookup table with a float).
2. A function that returned a plausible but useless result
   (``noise2d_array`` sampled gradient noise at integer lattice points,
   where it is identically zero, so the default produced a flat field).
"""

from __future__ import annotations

import math

import pytest

from spore_engine.sim.noise import (OpenSimplexNoise, PerlinNoise, ValueNoise,
                                    WorleyNoise)

ALL_2D = [PerlinNoise, ValueNoise, WorleyNoise, OpenSimplexNoise]
IDS = [c.__name__ for c in ALL_2D]


def _flat(grid):
    return [v for row in grid for v in row]


# --- the shared surface --------------------------------------------------

@pytest.mark.parametrize('cls', ALL_2D, ids=IDS)
def test_every_noise_class_exposes_the_same_2d_api(cls):
    """All four generators answer to the same names.

    ValueNoise used to expose only ``noise2`` while the others also had
    ``fbm2`` and the array samplers, so code that swapped noise types broke
    depending on which one it picked.
    """
    for name in ('noise2', 'fbm2', 'ridge2', 'noise2d_array', 'fbm2d_array'):
        assert callable(getattr(cls, name, None)), f'{cls.__name__} lacks {name}'


@pytest.mark.parametrize('cls', ALL_2D, ids=IDS)
def test_noise2_is_finite_and_bounded(cls):
    n = cls(seed=1)
    for x, y in [(0.0, 0.0), (1.3, 2.7), (-4.5, 9.25), (1e3, -1e3)]:
        v = n.noise2(x, y)
        assert isinstance(v, float) and math.isfinite(v)
        assert abs(v) < 1e4, f'{cls.__name__}.noise2 blew up at {(x, y)}: {v}'


@pytest.mark.parametrize('cls', ALL_2D, ids=IDS)
def test_noise2d_array_default_is_not_flat(cls):
    """The default grid scale must not land on the zero lattice.

    Gradient noise is exactly 0 at every integer coordinate, so a scale of
    1.0 over integer pixel indices returns an all-zero field - which reads
    as "noise generation is broken" rather than "bad default".
    """
    grid = _flat(cls(seed=3).noise2d_array(16, 12))
    assert len(grid) == 16 * 12
    assert all(math.isfinite(v) for v in grid)
    assert max(grid) - min(grid) > 1e-6, f'{cls.__name__} array is constant'


@pytest.mark.parametrize('cls', ALL_2D, ids=IDS)
def test_noise2d_array_shape_and_offset(cls):
    n = cls(seed=5)
    assert len(n.noise2d_array(7, 3)) == 3
    assert all(len(row) == 7 for row in n.noise2d_array(7, 3))
    shifted = _flat(n.noise2d_array(8, 8, ox=0.5, oy=0.5))
    plain = _flat(n.noise2d_array(8, 8))
    assert shifted != plain, 'ox/oy offsets had no effect'


@pytest.mark.parametrize('cls', ALL_2D, ids=IDS)
def test_fbm2d_array_is_finite_and_varied(cls):
    grid = _flat(cls(seed=9).fbm2d_array(16, 16, octaves=3))
    assert all(math.isfinite(v) for v in grid)
    assert max(grid) - min(grid) > 1e-6


@pytest.mark.parametrize('cls', ALL_2D, ids=IDS)
def test_same_seed_is_deterministic(cls):
    a, b = cls(seed=42), cls(seed=42)
    assert a.noise2(1.7, -2.3) == b.noise2(1.7, -2.3)
    assert _flat(a.noise2d_array(6, 6)) == _flat(b.noise2d_array(6, 6))


@pytest.mark.parametrize('cls', ALL_2D, ids=IDS)
def test_different_seeds_differ(cls):
    a, b = cls(seed=1), cls(seed=2)
    assert a.noise2(1.7, -2.3) != b.noise2(1.7, -2.3)


# --- continuity ----------------------------------------------------------

def test_value_noise_is_continuous_across_a_lattice_point():
    """Value noise must not jump at integer boundaries.

    Its old implementation summed a table *value* into the index, so it
    raised instead of blending - this is the cheap guard against a repeat.
    """
    n = ValueNoise(seed=3)
    for gx, gy in [(2, 1), (0, 0), (-3, 5)]:
        eps = 1e-7
        at = n.noise2(gx, gy)
        assert abs(n.noise2(gx + eps, gy) - at) < 1e-5
        assert abs(n.noise2(gx, gy + eps) - at) < 1e-5


def test_value_noise_lattice_indices_wrap_instead_of_overflowing():
    """Sampling far outside the 512-entry table must not raise."""
    n = ValueNoise(seed=3)
    for x, y in [(1e5, 1e5), (-1e5, -1e5), (512, 512), (-513, 7)]:
        assert math.isfinite(n.noise2(x, y))


def test_perlin_noise_is_zero_on_the_lattice():
    """Documents the property that made scale=1.0 a bad grid default."""
    n = PerlinNoise(seed=1)
    for gx, gy in [(0, 0), (1, 1), (3, -2), (10, 10)]:
        assert abs(n.noise2(gx, gy)) < 1e-12


def test_perlin_noise_tiles_periodically():
    """Perlin noise repeats every 256 units by construction."""
    n = PerlinNoise(seed=1)
    for x, y in [(3.25, 4.5), (-11.75, 8.0)]:
        assert abs(n.noise2(x, y) - n.noise2(x + 256, y + 256)) < 1e-9


# --- 1D ------------------------------------------------------------------

def test_perlin_noise1_runs():
    n = PerlinNoise(seed=1)
    values = [n.noise1(i * 0.13) for i in range(50)]
    assert all(math.isfinite(v) for v in values)
    assert max(values) - min(values) > 1e-6
    assert math.isfinite(n.fbm1(1.3))


# --- acceleration --------------------------------------------------------

def test_fbm2d_grid_matches_the_pure_python_sampler():
    """The numba grid path must agree with the Python one.

    They are separate implementations of the same function, so only a
    cross-check ties them together.
    """
    n = PerlinNoise(seed=4)
    grid = n.fbm2d_grid(8, 6, scale=0.1, octaves=3)
    ref = n.fbm2d_array(8, 6, scale=0.1, octaves=3)
    for y in range(6):
        for x in range(8):
            assert grid[y][x] == pytest.approx(ref[y][x], abs=1e-6)
