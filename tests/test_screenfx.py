"""ScreenFX shake/flash/fade state machine."""

from spore_engine import ScreenFX, Canvas, Color


def test_inactive_by_default():
    fx = ScreenFX()
    assert not fx.active
    fx.tick(1.0)


def test_shake_flash_timers():
    fx = ScreenFX()
    fx.add_shake(2.0)
    fx.add_flash(0.5)
    assert fx.active
    assert fx.shake_t > 0 and fx.flash_t > 0
    for _ in range(100):
        fx.tick(0.5)
    assert not fx.active


def test_apply_runs_without_stream():
    fx = ScreenFX()
    fx.add_shake(3.0)
    fx.add_flash(1.0)
    c = Canvas(4, 4)
    c.fill_rect(0, 0, 4, 4, fg=Color(200, 200, 200), z=1)
    fx.apply(c, seed=5)  # must not raise on small canvas


def test_fade_animation():
    fx = ScreenFX()
    fx.add_fade(Color(0, 0, 0), duration=1.0)
    fx.tick(0.5)
    assert 0 < fx.fade_t < 1
    fx.tick(1.0)
    assert fx.fade_t >= 1
    assert not fx.active


def test_max_power_capped():
    fx = ScreenFX()
    fx.add_shake(999)
    fx.add_flash(99)
    assert fx.shake_p <= 3.5
    assert fx.flash_p <= 1.0