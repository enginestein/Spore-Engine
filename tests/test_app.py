"""easy.App full-pipeline rendering (headless)."""

from spore_engine import App, Camera, Color


def _app():
    app = App(width=40, height=20, title='TEST')
    app.canvas.render_to = lambda *a, **k: None
    return app


def test_bg_and_lowres_sprite():
    app = _app()
    app.bg_gradient(Color(5, 5, 30), Color(120, 60, 200))
    app.sprite('AB', 2, 3, fg=Color(255, 255, 255), z=1)
    app._render()
    assert app.canvas.get_pixel(2, 3).char == 'A'
    assert app.canvas.get_pixel(1, 1).bg is not None


def test_hires_sprite_renders_to_hr():
    app = _app()
    app.bg(Color(20, 20, 40))
    app.rect(2, 1, x=0, y=0, fg=Color(0, 255, 0), hires=True, z=2)
    app._render()
    # hires position doubled onto hr
    assert app.hr.get_pixel(0, 0).fg is not None or app.hr.get_pixel(1, 0).fg is not None
    assert app.hr.get_pixel(0, 1).fg is not None


def test_camera_transforms_sprites():
    app = _app()
    app.camera = Camera(40, 20, x=10, y=10, world_w=80, world_h=40)
    app.sprite('A', 20, 10, fg=Color(255, 255, 255), z=1)
    app._render()
    sx, sy = app.camera.to_screen(20, 10)
    assert app.canvas.get_pixel(sx, sy).char == 'A'


def test_handlers_fire():
    app = _app()
    seen = {}
    app.on_key('left', lambda a: seen.update(left=True))
    app.sprite(' ', 0, 0)
    app._key_handlers['left'](app)
    assert seen.get('left')


def test_add_flash_runs_full_pipeline():
    app = _app()
    app.sprite('X', 0, 0, fg=Color(255, 255, 255))
    app.add_flash(1.0)
    app._render()
    cell = app.canvas.get_pixel(0, 0)
    assert cell.fg is not None