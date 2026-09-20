"""Canvas / HiResCanvas core drawing primitives and compositing."""

import io

import pytest

from spore_engine import (Canvas, HiResCanvas, Color, Gradient, DIM)


PRIMITIVES = [
    'fill_rect', 'fill', 'blit_canvas',
    'draw_text', 'draw_text_at', 'draw_text_centered',
    'draw_line', 'draw_line_thick', 'draw_ray',
    'draw_rect', 'draw_circle', 'draw_ellipse',
    'draw_triangle', 'draw_polygon', 'draw_bezier', 'draw_arc',
    'gradient_fill', 'gradient_fill_radial',
    'fill_gradient_x', 'fill_gradient_y', 'fill_sky',
    'noise',
]


@pytest.mark.parametrize('cls', [Canvas, HiResCanvas])
@pytest.mark.parametrize('m', PRIMITIVES)
def test_primitive_api_on_both_surfaces(cls, m):
    assert hasattr(cls(10, 10), m)


def test_canvas_resets_to_deep_empty():
    c = Canvas(5, 5)
    assert c.get_pixel(0, 0).z == -float('inf')
    c.clear()
    assert c.get_pixel(0, 0).z == -float('inf')
    # negative-z backgrounds stick after clear
    c.set_pixel(2, 2, ' ', bg=Color(1, 2, 3), z=-100)
    assert c.get_pixel(2, 2).bg == Color(1, 2, 3)


def test_z_order():
    c = Canvas(3, 3)
    c.set_pixel(1, 1, 'a', fg=Color(255, 0, 0), z=5)
    c.set_pixel(1, 1, 'b', fg=Color(0, 255, 0), z=10)
    assert c.get_pixel(1, 1).char == 'b'
    c.set_pixel(1, 1, 'c', fg=Color(0, 0, 255), z=4)  # lower: ignored
    assert c.get_pixel(1, 1).char == 'b'


def test_fill_rect_bounds_and_guard():
    c = Canvas(10, 10)
    c.fill_rect(-5, 3, 20, 2, 'X', fg=Color(255, 255, 255), z=1)
    assert c.get_pixel(0, 3).char == 'X'
    assert c.get_pixel(9, 3).char == 'X'
    assert c.get_pixel(5, 4).char == 'X'
    assert c.get_pixel(9, 5).char != 'X'


def test_draw_text_and_anchors():
    c = Canvas(20, 10)
    c.draw_text(1, 1, 'abc', fg=Color(1, 2, 3), z=1)
    assert c.get_pixel(1, 1).char == 'a'
    assert c.get_pixel(3, 1).char == 'c'
    ax, _ = c.draw_text_centered(0, '1234', fg=Color(1, 2, 3), z=1)
    assert ax == (20 - 4) // 2
    x, y = c.draw_text_at(0, 5, 'OOO', anchor='e')
    assert x == 20 - 3
    x, y = c.draw_text_at(0, 0, 'OO', anchor='c')
    assert x == (20 - 2) // 2 and y == (10 - 1) // 2


def test_fill_sky_gradient_background_only():
    c = Canvas(20, 10)
    c.fill_sky(Gradient(Color(5, 5, 30), Color(120, 60, 200)), horizon=0.5, z=-100)
    top = c.get_pixel(0, 0)
    assert top.char == ' ' and top.fg is None and top.bg is not None
    mid = c.get_pixel(0, 5)
    assert mid.fg is None and mid.bg is not None


def test_fill_gradient_x_y():
    c = Canvas(6, 4)
    c.fill_gradient_x(0, 0, 6, 2, Gradient(Color(0, 0, 0), Color(100, 0, 0)))
    assert c.get_pixel(0, 0).bg.r < c.get_pixel(5, 0).bg.r
    c.fill_gradient_y(0, 2, 6, 2, Gradient(Color(0, 0, 0), Color(0, 100, 0)))
    assert c.get_pixel(0, 2).bg.g < c.get_pixel(0, 3).bg.g


def test_outline_and_filled_shapes():
    c = Canvas(12, 12)
    c.draw_rect(2, 2, 4, 4, fg=Color(255, 255, 255), z=1)
    assert c.get_pixel(2, 2).char != ' '
    assert c.get_pixel(3, 3).char == ' '  # hollow interior
    c.fill_rect(0, 0, 3, 3, fg=Color(255, 0, 0), z=2)
    assert c.get_pixel(1, 1).fg == Color(255, 0, 0)
    c.draw_circle(6, 6, 3, fill=True, fg=Color(0, 255, 0), z=3)
    assert c.get_pixel(6, 6).fg == Color(0, 255, 0)
    c.draw_line(0, 0, 3, 0, fg=Color(0, 0, 255), z=4)
    assert c.get_pixel(2, 0).fg == Color(0, 0, 255)


def test_blit_canvas_skips_empty():
    src = Canvas(5, 5)
    src.set_pixel(1, 1, 'A', fg=Color(255, 255, 255), z=1)
    dst = Canvas(5, 5)
    dst.set_pixel(1, 1, ' ', bg=Color(9, 9, 9), z=0)
    dst.blit_canvas(src)
    assert dst.get_pixel(1, 1).char == 'A'
    assert dst.get_pixel(0, 0).bg is None  # untouched


def test_hires_to_canvas_preserves_background():
    c = Canvas(6, 4)
    c.set_pixel(1, 1, ' ', bg=Color(10, 20, 30), z=0)
    hr = HiResCanvas(6, 8)
    hr.set_pixel(4, 2, '@', fg=Color(255, 255, 255), z=5)  # maps to c(4,1)
    hr.to_canvas(c)  # default: skip empty -> sky survives
    assert c.get_pixel(1, 1).bg == Color(10, 20, 30)
    assert c.get_pixel(1, 1).fg is None
    assert c.get_pixel(4, 1).fg == Color(255, 255, 255)
    # blank=True erases empties
    c2 = Canvas(6, 4)
    c2.set_pixel(1, 1, ' ', bg=Color(10, 20, 30), z=0)
    hr.to_canvas(c2, blank=True)
    assert c2.get_pixel(1, 1).bg is None


def test_hires_half_block_blend():
    c = Canvas(4, 4)
    hr = HiResCanvas(4, 8)
    hr.set_pixel(0, 0, fg=Color(255, 0, 0))           # top half
    hr.set_pixel(0, 1, fg=Color(0, 0, 255))           # bottom half
    hr.to_canvas(c)
    cell = c.get_pixel(0, 0)
    assert cell.char == '▀'
    assert cell.fg == Color(255, 0, 0)
    assert cell.bg == Color(0, 0, 255)


def test_render_to_string():
    c = Canvas(4, 2)
    c.draw_text(1, 0, 'hi', fg=Color(255, 255, 255), z=1)
    buf = io.StringIO()
    c.render_to(buf, clear_first=True)
    out = buf.getvalue()
    assert '\x1b[' in out
    assert 'hi' in out


def test_copy_roundtrip():
    c = Canvas(4, 3)
    c.set_pixel(1, 1, 'x', fg=Color(1, 2, 3), z=7)
    cc = c.copy()
    assert cc.get_pixel(1, 1).char == 'x'
    assert cc.get_pixel(1, 1).z == 7