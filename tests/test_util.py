"""Math / ramp utilities."""

import math

from spore_engine import (
    clamp, lerp, ir, ramp, phase, wave, osc, in_bounds,
    approach, move_toward, bounce, dist, lerp_color, smoothstep,
    ramp_color, Color,
)


def test_clamp_lerp_ir():
    assert clamp(5, 0, 3) == 3
    assert clamp(-2, 0, 3) == 0
    assert clamp(1.5, 0, 3) == 1.5
    assert lerp(0, 10, 0.5) == 5.0
    assert ir(2.6) == 3 and ir(2.4) == 2 and ir(2.5) == 2  # banker's? python round


def test_ramp_endoints():
    assert ramp(0.0) == ' '
    assert ramp(1.0) == '@'
    assert ramp(0.5) in ' .:-=+*#%@'


def test_wave_osc_phase_bounce():
    assert abs(wave(0.0) - 0.5) < 1e-9
    assert abs(wave(math.pi / 2, 1.0) - 1.0) < 1e-9
    assert abs(osc(0, 1) - 0.5) < 1e-9
    assert abs(osc(0.25, 1) - 1.0) < 1e-9
    assert 0 <= phase(0.0) < 1
    assert abs(phase(0.0) - phase(1.0)) < 1e-9
    assert abs(bounce(0.0) - 0.0) < 1e-9
    assert abs(bounce(0.25, 1.0) - 0.5) < 1e-9
    assert abs(bounce(0.5, 1.0) - 1.0) < 1e-9


def test_bounds_and_approach():
    assert in_bounds(0, 0, 10, 10)
    assert in_bounds(9, 9, 10, 10)
    assert not in_bounds(10, 0, 10, 10)
    assert not in_bounds(-1, 0, 10, 10)
    assert approach(0, 10, 3) == 3
    assert approach(10, 0, 3) == 7
    assert move_toward(10, 0, 3) == 7


def test_dist_and_colors():
    assert math.isclose(dist(0, 0, 3, 4), 5.0)
    a, b = Color(0, 0, 0), Color(200, 100, 0)
    mid = lerp_color(a, b, 0.5)
    assert mid == Color(100, 50, 0)
    assert smoothstep(0.5) == 0.5
    assert ramp_color(0.0, Color(1, 1, 1), Color(2, 2, 2)) == Color(1, 1, 1)
    assert ramp_color(1.0, Color(1, 1, 1), Color(2, 2, 2)) == Color(2, 2, 2)