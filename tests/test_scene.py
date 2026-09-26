"""Scene/Layer compositing."""

import io

from spore_engine import Scene, Color


def test_scene_forwards_draw_to_canvas():
    s = Scene(20, 10)
    s.fill_rect(0, 0, 4, 4, fg=Color(255, 255, 255), z=1)
    assert s.canvas.get_pixel(1, 1).fg == Color(255, 255, 255)
    assert s.hr is not None and s.hr.h == 20


def test_layer_creation_and_forwarding():
    s = Scene(10, 8)
    hud = s.layer('hud', z=50)
    hud.draw_text(1, 1, 'HI', fg=Color(0, 255, 0), z=50)
    assert hud.canvas.get_pixel(1, 1).char == 'H'
    same = s.layer('hud', z=60)
    assert same is hud
    assert hud.z == 60


def test_compose_stacks_hires_over_bg():
    s = Scene(10, 8)
    s.canvas.set_pixel(4, 1, ' ', bg=Color(9, 9, 9), z=0)
    s.hr.set_pixel(4, 2, '@', fg=Color(255, 255, 255), z=5)  # -> c(4,1) top half
    s.compose()
    cell = s.canvas.get_pixel(4, 1)
    assert cell.char == '▀' and cell.fg == Color(255, 255, 255)
    assert s.canvas.get_pixel(0, 0).bg is None  # empty hr cells skip


def test_present_writes_frame():
    s = Scene(6, 4)
    s.draw_text(1, 1, 'go', fg=Color(255, 255, 255), z=1)
    buf = io.StringIO()
    s.present(buf)
    assert 'go' in buf.getvalue()


def test_scene_dict_repr():
    s = Scene(4, 4)
    assert repr(s) == 'Scene(4x4, 0 layers)'