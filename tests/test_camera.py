"""Camera viewport math."""

from spore_engine import Canvas, Camera, Color


def test_world_to_screen_roundtrip():
    cam = Camera(40, 20, x=100, y=50)
    sx, sy = cam.to_screen(100, 50)
    assert (sx, sy) == (20, 10)  # dead centre
    wx, wy = cam.to_world(sx, sy)
    assert abs(wx - 100) < 1e-9
    assert abs(wy - 50) < 1e-9


def test_zoom_shrinks_screen_distance():
    cam = Camera(40, 20, x=0, y=0, zoom=2.0)
    sx, sy = cam.to_screen(2, 0)
    assert (sx, sy) == (24, 10)


def test_in_view():
    cam = Camera(40, 20, x=100, y=100)
    assert cam.in_view(100, 100)
    assert not cam.in_view(200, 100)


def test_follow_and_snap():
    cam = Camera(40, 20)
    cam.follow(10, 5)  # no dt -> snap
    assert (cam.x, cam.y) == (10, 5)
    cam.follow(50, 20, dt=0.1)  # dt present -> lerp toward target
    assert 10 < cam.x < 50


def test_clamp_world_bounds():
    cam = Camera(10, 10, x=0, y=0, world_w=100, world_h=50)
    cam.follow(99, 0)  # force past right edge
    assert cam.x <= 100 - 5
    cam.follow(0, 49)
    assert cam.y <= 50 - 5


def test_draw_uses_world_coords():
    cam = Camera(10, 10, x=0, y=0)
    c = Canvas(10, 10)
    cam.draw(c, 0, 0, '@', fg=Color(255, 255, 255), z=1)
    assert c.get_pixel(5, 5).char == '@'