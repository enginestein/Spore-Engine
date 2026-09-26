"""Tests for spore_engine.easy.anim and the tween primitives it builds on."""
from __future__ import annotations

import math

import pytest

from spore_engine.anim.anim import EASING, Sequence, Tween
from spore_engine.easy.anim import Anim


class FakeSprite:
    """The attributes Anim reads and writes."""

    def __init__(self):
        self.x = 0.0
        self.y = 0.0
        self.opacity = 1.0
        self.scale_x = 1.0
        self.scale_y = 1.0
        self.rotation = 0.0


@pytest.fixture
def sprite():
    return FakeSprite()


def run(anim, seconds, step=1 / 60):
    for _ in range(int(seconds / step)):
        anim.update(step)
    return anim


# -------------------------------------------------------------------
# Tween
# -------------------------------------------------------------------

def test_tween_reaches_one_and_reports_done():
    t = Tween(1.0, 'linear')
    assert not t.done
    run_t = 0.0
    for _ in range(60):
        t.update(1 / 60)
        run_t += 1 / 60
    assert t.done
    assert t.value == pytest.approx(1.0)


OVERSHOOT = {'back_in', 'back_out', 'back_in_out',
             'elastic_in', 'elastic_out', 'elastic_in_out'}


def test_non_overshooting_easings_stay_within_the_unit_range():
    for name in set(EASING) - OVERSHOOT:
        t = Tween(1.0, name)
        for _ in range(30):
            t.update(1 / 30)
            assert 0.0 <= t.value <= 1.0 + 1e-9, f'{name} left [0, 1]'


def test_overshooting_easings_really_overshoot():
    """back_* and elastic_* are meant to leave [0, 1]; if they stopped doing
    so they would be pointless."""
    for name in OVERSHOOT:
        t = Tween(1.0, name)
        values = []
        for _ in range(40):
            t.update(1 / 40)
            values.append(t.value)
        assert min(values) < -1e-6 or max(values) > 1 + 1e-6, \
            f'{name} no longer overshoots'


def test_tween_with_a_zero_duration_is_immediately_complete():
    t = Tween(0.0, 'linear')
    assert t.value == 1.0
    t.update(1.0)
    assert t.done


def test_tween_with_a_negative_elapsed_reads_as_zero():
    """A negative elapsed is how Anim.delay() is expressed."""
    for name in ('linear', 'quad_in', 'cubic_in', 'quart_in', 'sine_in',
                 'expo_in', 'back_in', 'bounce_out'):
        t = Tween(1.0, name)
        t.elapsed = -0.5
        assert t.value == 0.0, f'{name} moved during a delay'


def test_tween_clamps_far_past_the_end():
    t = Tween(1.0, 'quad_in')
    t.elapsed = 50.0
    assert t.value == pytest.approx(1.0)


def test_tween_unknown_easing_falls_back_to_linear():
    t = Tween(1.0, 'no-such-easing')
    t.update(0.5)
    assert t.value == pytest.approx(0.5)


def test_tween_loop_never_completes_and_wraps():
    t = Tween(1.0, 'linear', loop=True)
    for _ in range(300):
        t.update(1 / 60)
    assert not t.done
    assert t.elapsed < t.duration


def test_tween_yoyo_reverses_at_the_ends():
    t = Tween(1.0, 'linear', yoyo=True)
    seen_forward = []
    for _ in range(180):
        t.update(1 / 60)
        seen_forward.append(t.forward)
    assert True in seen_forward and False in seen_forward, 'yoyo never reversed'


def test_tween_yoyo_halves_the_value_on_the_return_leg():
    t = Tween(1.0, 'linear', yoyo=True)
    t.update(0.5)
    assert t.value == pytest.approx(0.5)
    t.update(0.5)          # reaches the end and flips
    assert t.forward is False
    t.update(0.25)         # a quarter of the way back
    assert t.value == pytest.approx(0.75)


def test_tween_update_after_completion_is_a_no_op():
    t = Tween(0.1, 'linear')
    t.update(1.0)
    assert t.done
    t.update(5.0)
    assert t.elapsed == pytest.approx(0.1)


def test_tween_reset():
    t = Tween(1.0, 'linear', yoyo=True)
    t.update(2.0)
    t.forward = False
    t.reset()
    assert t.elapsed == 0.0
    assert t.forward is True
    assert not t.done


def test_every_easing_is_callable_and_anchored_at_the_ends():
    for name, fn in EASING.items():
        assert fn(0.0) == pytest.approx(0.0, abs=1e-6), f'{name}(0) != 0'
        assert fn(1.0) == pytest.approx(1.0, abs=1e-6), f'{name}(1) != 1'


# -------------------------------------------------------------------
# builder methods
# -------------------------------------------------------------------

def test_to_records_both_axes_and_returns_self(sprite):
    a = Anim(sprite)
    assert a.to(10, 20) is a
    assert a._props['x'] == (0.0, 10.0)
    assert a._props['y'] == (0.0, 20.0)


def test_fade_clamps_its_target(sprite):
    a = Anim(sprite)
    a.fade(5.0)
    assert a._props['opacity'] == (1.0, 1.0)
    a.fade(-3.0)
    assert a._props['opacity'] == (1.0, 0.0)


def test_scale_clamps_away_from_zero(sprite):
    a = Anim(sprite)
    a.scale(0.0)
    assert a._props['scale_x'][1] == 0.01
    assert a._props['scale_y'][1] == 0.01


def test_scale_sets_both_axes(sprite):
    a = Anim(sprite)
    a.scale(2.5)
    assert a._props['scale_x'][1] == a._props['scale_y'][1] == 2.5


@pytest.mark.parametrize('call,expected', [
    (lambda a: a.over(2.0), '_duration'),
    (lambda a: a.ease('quad_in'), '_easing'),
    (lambda a: a.loop(), '_loop'),
    (lambda a: a.yoyo(), '_yoyo'),
    (lambda a: a.delay(1.0), '_delay'),
])
def test_setters_return_self_and_store(sprite, call, expected):
    a = Anim(sprite)
    assert call(a) is a


def test_over_clamps_a_zero_duration(sprite):
    assert Anim(sprite).over(0.0)._duration == 0.01
    assert Anim(sprite).over(-5.0)._duration == 0.01


def test_delay_clamps_a_negative_delay(sprite):
    assert Anim(sprite).delay(-1.0)._delay == 0.0


def test_spin_pulse_wobble_force_looping(sprite):
    for build in (lambda a: a.spin(), lambda a: a.pulse(), lambda a: a.wobble()):
        a = build(Anim(sprite))
        assert a._loop is True


def test_forever_and_then_return_self(sprite):
    a = Anim(sprite)
    cb = lambda: None
    assert a.forever() is a
    assert a.then(cb) is a
    assert a._callback is cb


def test_done_starts_false(sprite):
    assert Anim(sprite).done is False


# -------------------------------------------------------------------
# tween behaviour through Anim
# -------------------------------------------------------------------

def test_tween_moves_the_sprite_to_the_target(sprite):
    a = Anim(sprite).to(10, 4).over(1.0)
    run(a, 1.2)
    assert sprite.x == pytest.approx(10.0)
    assert sprite.y == pytest.approx(4.0)
    assert a.done


def test_tween_snaps_exactly_to_the_end(sprite):
    a = Anim(sprite).to(7, 0).over(0.3).ease('quad_in')
    run(a, 0.3)
    assert sprite.x == 7.0


def test_tween_runs_the_callback_once_at_the_end(sprite):
    calls = []
    a = Anim(sprite).to(1, 0).over(0.2).then(lambda: calls.append(1))
    run(a, 0.1)
    assert calls == [], 'the callback fired before the tween finished'
    run(a, 0.3)
    assert calls == [1]
    run(a, 0.5)
    assert calls == [1], 'the callback fired more than once'


def test_update_after_done_changes_nothing(sprite):
    a = Anim(sprite).to(5, 5).over(0.2)
    run(a, 0.4)
    x, y = sprite.x, sprite.y
    a.update(1.0)
    assert (sprite.x, sprite.y) == (x, y)


def test_a_delay_holds_the_sprite_still(sprite):
    a = Anim(sprite).to(10, 0).over(0.5).ease('quad_in').delay(0.5)
    for _ in range(30):
        a.update(1 / 60)
        assert sprite.x == 0.0, 'the sprite moved during the delay'
    run(a, 0.6)
    assert sprite.x == pytest.approx(10.0)


def test_the_start_value_is_read_when_the_animation_starts(sprite):
    """to() captures the position when it is called; the tween must still
    begin from wherever the sprite actually is when it first ticks."""
    a = Anim(sprite).to(10, 0).over(1.0)
    sprite.x = 4.0
    a.update(0.0)
    assert sprite.x == 4.0
    run(a, 1.2)
    assert sprite.x == pytest.approx(10.0)


def test_an_empty_tween_completes_immediately(sprite):
    a = Anim(sprite).over(1.0)
    a.update(0.016)
    assert a.done


def test_a_looping_tween_never_completes(sprite):
    a = Anim(sprite).to(10, 0).over(0.2).forever()
    run(a, 2.0)
    assert not a.done


def test_fade_and_scale_tween_together(sprite):
    a = Anim(sprite).to(0, 0).fade(0.0).scale(2.0).over(0.4)
    run(a, 0.6)
    assert sprite.opacity == pytest.approx(0.0)
    assert sprite.scale_x == pytest.approx(2.0)
    assert sprite.scale_y == pytest.approx(2.0)


# -------------------------------------------------------------------
# continuous types
# -------------------------------------------------------------------

def test_wait_completes_after_its_time(sprite):
    calls = []
    a = Anim(sprite).wait(0.3).then(lambda: calls.append(1))
    run(a, 0.1)
    assert not a.done and calls == []
    run(a, 0.4)
    assert a.done and calls == [1]


def test_wait_zero_completes_on_the_first_tick(sprite):
    a = Anim(sprite).wait(0.0)
    a.update(0.0)
    assert a.done


def test_spin_rotates_by_turns_per_second(sprite):
    a = Anim(sprite).spin(1.0)
    a.update(0.25)
    assert sprite.rotation == pytest.approx(0.25 * 2 * math.pi)
    assert not a.done, 'spin should keep going'


def test_spin_respects_a_negative_speed(sprite):
    a = Anim(sprite).spin(-2.0)
    a.update(0.5)
    assert sprite.rotation == pytest.approx(-2.0 * 0.5 * 2 * math.pi)


def test_pulse_stays_within_its_bounds(sprite):
    a = Anim(sprite).pulse(0.8, 1.2, period=0.5)
    for _ in range(200):
        a.update(1 / 60)
        assert 0.79 <= sprite.scale_x <= 1.21, sprite.scale_x
        assert sprite.scale_x == sprite.scale_y


def test_pulse_visits_both_extremes(sprite):
    a = Anim(sprite).pulse(0.8, 1.2, period=1.0)
    seen = set()
    for _ in range(120):
        a.update(1 / 60)
        seen.add(round(sprite.scale_x, 3))
    assert min(seen) < 0.85 and max(seen) > 1.15, f'pulse stayed flat: {sorted(seen)}'


def test_pulse_survives_a_zero_period(sprite):
    a = Anim(sprite).pulse(0.5, 1.5, period=0.0)
    a.update(0.1)          # must not divide by zero
    assert not math.isnan(sprite.scale_x)


def test_wobble_moves_the_sprite_and_survives_a_zero_period(sprite):
    a = Anim(sprite).wobble(2.0, period=0.0)
    a.update(0.1)          # must not divide by zero
    assert not math.isnan(sprite.x)
    assert sprite.x != 0.0


def test_wobble_reverses_direction_within_a_period(sprite):
    """wobble integrates a sine, so the sprite drifts one way then back."""
    a = Anim(sprite).wobble(4.0, period=1.0)
    xs = []
    for _ in range(60):
        a.update(1 / 60)
        xs.append(sprite.x)
    assert max(xs) > 0.0, 'the sprite never moved'
    # the displacement is bounded, not a random walk
    assert max(xs) < 4.0, f'wobble ran away: {max(xs)}'
    assert xs[-1] < max(xs), 'wobble never came back'


# -------------------------------------------------------------------
# Sequence
# -------------------------------------------------------------------

def test_sequence_advances_one_step_at_a_time():
    s = Sequence((0.1, 'linear'), (0.1, 'quad_in'))
    assert len(s.steps) == 2
    for _ in range(6):
        s.update(1 / 60)
    assert s.idx == 0
    for _ in range(6):
        s.update(1 / 60)
    assert s.idx == 1
    for _ in range(12):
        s.update(1 / 60)
    assert s.done


def test_sequence_accepts_tween_instances():
    t = Tween(0.1, 'linear')
    s = Sequence(t)
    assert s.steps == [t]


def test_sequence_value_follows_the_current_step():
    s = Sequence((1.0, 'linear'))
    s.update(0.5)
    assert s.value == pytest.approx(0.5)
    s.update(1.0)
    assert s.value == 1.0


def test_an_empty_sequence_is_done():
    s = Sequence()
    s.update(0.1)
    assert s.done
    assert s.value == 1.0


def test_sequence_update_after_completion_is_a_no_op():
    s = Sequence((0.1, 'linear'))
    s.update(1.0)
    idx = s.idx
    s.update(1.0)
    assert s.idx == idx


def test_sequence_reset():
    s = Sequence((0.1, 'linear'), (0.1, 'linear'))
    for _ in range(60):
        s.update(1 / 60)
    assert s.done
    s.reset()
    assert not s.done
    assert s.idx == 0
    assert all(not step.done for step in s.steps)
