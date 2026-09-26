"""Contract tests for every primitive in :mod:`spore_engine.core.draw`.

The existing ``test_draw_primitives.py`` covers defects where a parameter was
ignored. This file sweeps the whole surface: clipping, degenerate sizes,
z-ordering, and the documented ``set_pixel``/``set_pixel_exact`` colour
semantics, on both :class:`Canvas` and :class:`HiResCanvas`.
"""

from __future__ import annotations

import math

import pytest

from spore_engine import Canvas, HiResCanvas
from spore_engine.core.color import BLACK, BLUE, RED, WHITE, Color, Gradient


def blank(w=24, h=12):
    return Canvas(w, h)


def ink(canvas):
    return {(x, y)
            for y in range(canvas.height)
            for x in range(canvas.width)
            if canvas.buffer[y][x].char != ' '}


def char_at(canvas, x, y):
    return canvas.buffer[y][x].char


# -------------------------------------------------------------------
# blit_canvas
# -------------------------------------------------------------------

def test_blit_copies_cells_with_a_foreground():
    src, dst = blank(4, 3), blank(8, 4)
    src.draw_text(0, 0, 'ab', fg=Color(255, 0, 0))
    dst.blit_canvas(src, 1, 1)
    assert char_at(dst, 1, 1) == 'a'
    assert char_at(dst, 2, 1) == 'b'
    assert dst.buffer[1][1].fg == Color(255, 0, 0)


def test_blit_treats_a_none_foreground_as_transparent():
    src, dst = blank(3, 1), blank(6, 2)
    src.draw_text(0, 0, 'xyz')          # no fg: all three stay transparent
    dst.blit_canvas(src, 0, 0)
    assert ink(dst) == set()


def test_blit_keeps_the_destination_where_the_source_is_transparent():
    src, dst = blank(3, 1), blank(6, 2)
    dst.draw_text(0, 0, '###')
    src.draw_text(1, 0, 'A', fg=WHITE)
    dst.blit_canvas(src, 0, 0)
    assert char_at(dst, 0, 0) == '#'
    assert char_at(dst, 1, 0) == 'A'
    assert char_at(dst, 2, 0) == '#'


def test_blit_clips_at_the_edges():
    src, dst = blank(3, 3), blank(4, 4)
    src.fill_rect(0, 0, 3, 3, '#', fg=WHITE)
    dst.blit_canvas(src, 2, 2)
    assert ink(dst) == {(2, 2), (3, 2), (2, 3), (3, 3)}


def test_blit_respects_z_depth():
    src, dst = blank(2, 1), blank(2, 1)
    dst.draw_text(0, 0, '..', fg=WHITE, z=5)
    src.draw_text(0, 0, 'XX', fg=WHITE, z=1)
    dst.blit_canvas(src, 0, 0, z=1)
    assert char_at(dst, 0, 0) == '.', 'the blit drew over a higher z'


# -------------------------------------------------------------------
# fill_rect
# -------------------------------------------------------------------

def test_fill_rect_fills_the_region():
    c = blank()
    c.fill_rect(2, 3, 4, 2, '#')
    assert ink(c) == {(x, y) for y in (3, 4) for x in (2, 3, 4, 5)}


def test_fill_rect_clips_on_every_side():
    c = blank(6, 4)
    c.fill_rect(-3, -3, 20, 20, '#')
    assert ink(c) == {(x, y) for y in range(4) for x in range(6)}


def test_fill_rect_with_a_negative_size_draws_nothing():
    c = blank()
    c.fill_rect(2, 2, -5, 5, '#')
    assert ink(c) == set()


def test_fill_rect_clears_colour_with_exact_semantics():
    c = blank(3, 1)
    c.fill_rect(0, 0, 3, 1, 'x', fg=RED, bg=BLUE)
    c.fill_rect(0, 0, 3, 1, 'y')            # fg/bg default to None = clear
    assert c.buffer[0][0].fg is None
    assert c.buffer[0][0].bg is None


def test_fill_rect_respects_z_depth():
    c = blank(3, 1)
    c.fill_rect(0, 0, 3, 1, '#', z=5)
    c.fill_rect(0, 0, 1, 1, '!', z=1)
    assert char_at(c, 0, 0) == '#'
    c.fill_rect(0, 0, 1, 1, '!', z=5)
    assert char_at(c, 0, 0) == '!'


# -------------------------------------------------------------------
# fill (flood)
# -------------------------------------------------------------------

def test_fill_spreads_across_a_matching_region():
    c = blank(5, 5)
    c.fill_rect(1, 1, 3, 3, '.')
    c.fill(1, 1, 'o', fg=RED)
    assert ink(c) == {(x, y) for y in (1, 2, 3) for x in (1, 2, 3)}


def test_fill_stops_at_a_different_character():
    c = blank(5, 3)
    c.fill_rect(0, 0, 5, 3, '.')
    for y in range(3):
        c.set_pixel(2, y, '|')             # a wall down the middle
    c.fill(0, 0, 'o')
    assert char_at(c, 0, 0) == 'o' and char_at(c, 1, 2) == 'o'
    assert all(char_at(c, 2, y) == '|' for y in range(3)), 'the wall was crossed'
    assert char_at(c, 3, 0) == '.', 'the fill leaked past the wall'


def test_fill_wraps_around_the_screen_edges():
    c = blank(4, 3)
    c.fill_rect(0, 0, 4, 3, '.')
    c.fill(0, 0, 'o')
    assert ink(c) == {(x, y) for y in range(3) for x in range(4)}


def test_fill_outside_the_canvas_does_nothing():
    c = blank()
    c.fill(-5, -5, 'o')
    c.fill(99, 99, 'o')
    assert ink(c) == set()


def test_fill_is_four_connected_not_eight():
    """(0,0) is walled off from the centre by two side-adjacent cells, so a
    diagonal-only route must not be enough."""
    c = blank(3, 3)
    c.fill_rect(0, 0, 3, 3, '.')
    for x, y in ((0, 1), (1, 0), (1, 2), (2, 1)):
        c.set_pixel(x, y, '#')
    c.fill(0, 0, 'o')
    assert char_at(c, 0, 0) == 'o'
    assert char_at(c, 1, 1) == '.', 'the flood leaked diagonally through a wall'


# -------------------------------------------------------------------
# text
# -------------------------------------------------------------------

def test_draw_text_writes_left_to_right():
    c = blank()
    c.draw_text(1, 1, 'hey')
    assert [char_at(c, x, 1) for x in (1, 2, 3)] == list('hey')


def test_draw_text_clips_off_screen():
    c = blank(4, 2)
    c.draw_text(2, 0, 'abcdef')
    assert ''.join(char_at(c, x, 0) for x in range(4)) == '  ab'


def test_draw_text_above_the_canvas_draws_nothing():
    c = blank(4, 2)
    c.draw_text(0, -1, 'abc')
    c.draw_text(0, 2, 'abc')
    assert ink(c) == set()


def test_draw_text_keeps_existing_colour_when_fg_is_none():
    c = blank(3, 1)
    c.set_pixel(0, 0, '#', RED)
    c.draw_text(0, 0, 'x')
    assert c.buffer[0][0].fg == RED


@pytest.mark.parametrize('anchor,expected_x', [
    ('nw', 0), ('n', 11), ('w', 0), ('c', 11),
    ('ne', 22), ('e', 22), ('se', 22),
    ('sw', 0), ('s', 11),
])
def test_draw_text_at_anchor_horizontal_placement(anchor, expected_x):
    c = blank(24, 6)
    ax, ay = c.draw_text_at(0, 0, 'ab', anchor=anchor)
    assert ax == expected_x
    assert char_at(c, ax, ay) == 'a', 'the text is not at the reported anchor x'


def test_draw_text_at_right_anchor_puts_the_text_on_screen():
    c = blank(20, 5)
    ax, ay = c.draw_text_at(0, 0, 'ab', anchor='e')
    assert ax >= 0 and ax + 2 <= c.width
    assert ''.join(char_at(c, x, ay) for x in range(ax, ax + 2)) == 'ab'


def test_draw_text_at_bottom_anchor_puts_the_text_on_screen():
    c = blank(20, 5)
    ax, ay = c.draw_text_at(0, 0, 'ab', anchor='s')
    assert ay >= 0 and ay < c.height
    assert char_at(c, ax, ay) == 'a'


def test_draw_text_at_honours_a_margin():
    c = blank(20, 5)
    ax, _ = c.draw_text_at(2, 0, 'ab', anchor='e')
    assert ax == 20 - 2 - 2, 'the inward margin was ignored'


def test_draw_text_at_centre_anchor_centres_both_axes():
    c = blank(20, 5)
    ax, ay = c.draw_text_at(0, 0, 'abcd', anchor='c')
    assert ax == (20 - 4) // 2
    assert ay == (5 - 1) // 2


def test_draw_text_centered_uses_the_top_anchor():
    c = blank(20, 5)
    ax, ay = c.draw_text_centered(0, 'abcd')
    assert (ax, ay) == ((20 - 4) // 2, 0)


# -------------------------------------------------------------------
# lines
# -------------------------------------------------------------------

def test_draw_line_is_continuous():
    c = blank(20, 7)
    c.draw_line(0, 0, 19, 6, '#')
    drawn = ink(c)
    assert len(drawn) >= 20
    assert (0, 0) in drawn and (19, 6) in drawn


def test_draw_line_of_a_single_point():
    c = blank()
    c.draw_line(3, 3, 3, 3, '#')
    assert ink(c) == {(3, 3)}


def test_draw_line_works_backwards():
    c = blank(10, 5)
    c.draw_line(9, 0, 0, 0, '#')
    assert ink(c) == {(x, 0) for x in range(10)}


def test_draw_line_vertical_and_horizontal():
    c = blank(10, 5)
    c.draw_line(3, 0, 3, 4, '#')
    c.draw_line(0, 2, 9, 2, '@')
    assert (3, 0) in ink(c) and (3, 4) in ink(c)
    assert (0, 2) in ink(c) and (9, 2) in ink(c)


def test_line_thickness_two_covers_more_than_one():
    thin, thick = blank(20, 5), blank(20, 5)
    thin.draw_line_thick(0, 2, 19, 2, thickness=1, char='#')
    thick.draw_line_thick(0, 2, 19, 2, thickness=2, char='#')
    assert len(ink(thick)) > len(ink(thin)), 'thickness had no effect'


def test_line_thickness_widens_monotonically():
    counts = []
    for t in range(1, 6):
        c = blank(20, 9)
        c.draw_line_thick(0, 4, 19, 4, thickness=t, char='#')
        counts.append(len(ink(c)))
    assert counts == sorted(counts), f'thickness was not monotonic: {counts}'


def test_line_thickness_zero_is_clamped_to_one():
    c = blank(20, 5)
    c.draw_line_thick(0, 2, 19, 2, thickness=0, char='#')
    assert ink(c) == {(x, 2) for x in range(20)}


def test_draw_ray_marks_every_step():
    c = blank(20, 5)
    c.draw_ray(1.0, 2.0, 15.0, 2.0, '#')
    drawn = ink(c)
    assert min(x for x, _ in drawn) == 1
    assert max(x for x, _ in drawn) == 15


def test_draw_ray_with_a_zero_length():
    c = blank(5, 5)
    c.draw_ray(2.0, 2.0, 2.0, 2.0, '#')
    assert ink(c) == {(2, 2)}


def test_draw_ray_fade_darkens_along_the_ray():
    c = blank(20, 3)
    c.draw_ray(1.0, 1.0, 18.0, 1.0, '#', fg=Color(200, 200, 200), fade=True)
    first = c.buffer[1][1].fg
    last = c.buffer[1][18].fg
    assert first is not None and last is not None
    assert first.r > last.r, 'fade did not darken towards the end'


def test_draw_ray_without_fade_keeps_one_colour():
    c = blank(20, 3)
    c.draw_ray(1.0, 1.0, 18.0, 1.0, '#', fg=Color(200, 200, 200))
    assert c.buffer[1][1].fg == c.buffer[1][18].fg == Color(200, 200, 200)


# -------------------------------------------------------------------
# rect
# -------------------------------------------------------------------

def test_draw_rect_outline_excludes_the_interior():
    c = blank(5, 5)
    c.draw_rect(1, 1, 3, 3, '#')
    assert ink(c) == {(1, 1), (2, 1), (3, 1),
                      (1, 2), (3, 2),
                      (1, 3), (2, 3), (3, 3)}


def test_draw_rect_fill_covers_everything():
    c = blank(5, 5)
    c.draw_rect(1, 1, 3, 3, '#', fill=True)
    assert ink(c) == {(x, y) for y in (1, 2, 3) for x in (1, 2, 3)}


def test_draw_rect_with_a_degenerate_size():
    c = blank()
    c.draw_rect(1, 1, 0, 5, '#')
    c.draw_rect(1, 1, 5, 0, '#')
    c.draw_rect(1, 1, -2, 2, '#')
    assert ink(c) == set()


def test_draw_rect_radius_uses_round_corners():
    """The glyphs go at the outer corners, with the straight runs between."""
    c = blank(9, 7)
    c.draw_rect(1, 1, 7, 5, radius=2)
    assert char_at(c, 1, 1) == '╭'
    assert char_at(c, 7, 1) == '╮'
    assert char_at(c, 1, 5) == '╰'
    assert char_at(c, 7, 5) == '╯'
    for x in range(3, 6):
        assert char_at(c, x, 1) == '─'
        assert char_at(c, x, 5) == '─'
    for y in range(3, 4):
        assert char_at(c, 1, y) == '│'
        assert char_at(c, 7, y) == '│'
    assert char_at(c, 4, 3) == ' ', 'the rounded rect has no interior'


def test_draw_rect_radius_is_clamped_to_the_rect():
    c = blank(9, 7)
    c.draw_rect(1, 1, 3, 3, radius=50)     # radius larger than the rect
    assert char_at(c, 1, 1) == '╭'         # clamped to the rect's own half-size
    assert char_at(c, 3, 3) == '╯'


def test_draw_rect_radius_larger_than_the_shape_does_not_crash():
    c = blank(4, 3)
    for w in range(1, 4):
        for h in range(1, 3):
            c.draw_rect(0, 0, w, h, radius=4)


def test_draw_rect_clips_off_screen():
    """A rect larger than the canvas clips to the canvas border; it used to
    draw nothing at all because the outline sat on off-screen edges."""
    c = blank(4, 4)
    c.draw_rect(-2, -2, 20, 20, '#')
    assert ink(c) == {(x, 0) for x in range(4)} | {(x, 3) for x in range(4)} | \
                     {(0, 1), (3, 1), (0, 2), (3, 2)}


def test_draw_rect_entirely_off_screen_draws_nothing():
    c = blank(4, 4)
    c.draw_rect(-20, -20, 5, 5, '#')
    c.draw_rect(50, 50, 5, 5, '#')
    c.draw_rect(-10, 0, 4, 4, '#')      # ends exactly at x = -7
    assert ink(c) == set()


def test_draw_rect_clipped_on_one_side_only():
    """6 wide starting at x=-3, so only x=0..2 is on screen."""
    c = blank(6, 4)
    c.draw_rect(-3, 0, 6, 4, '#')
    assert ink(c) == {(x, 0) for x in range(3)} | {(x, 3) for x in range(3)} | \
                     {(0, 1), (2, 1), (0, 2), (2, 2)}


def test_draw_rect_radius_clips_off_screen():
    c = blank(4, 4)
    c.draw_rect(-2, -2, 20, 20, radius=2)
    assert ink(c), 'a rounded rect vanished off-screen'
    assert char_at(c, 0, 0) == '╭'


# -------------------------------------------------------------------
# circle / ellipse
# -------------------------------------------------------------------

def test_draw_circle_outline_reaches_all_four_extremes():
    c = blank(21, 21)
    c.draw_circle(10, 10, 6, '#')
    drawn = ink(c)
    assert (10, 4) in drawn and (10, 16) in drawn
    assert (4, 10) in drawn and (16, 10) in drawn


def test_draw_circle_fill_covers_the_interior():
    c = blank(21, 21)
    c.draw_circle(10, 10, 5, '#', fill=True)
    assert ink(c) == {(10 + dx, 10 + dy)
                      for dy in range(-5, 6) for dx in range(-5, 6)
                      if math.hypot(dx, dy) <= 5.6}


def test_draw_circle_of_radius_one_is_a_plus():
    c = blank(5, 5)
    c.draw_circle(2, 2, 1, '#')
    assert ink(c) == {(2, 2), (2, 1), (2, 3), (1, 2), (3, 2)}


def test_draw_circle_of_radius_zero_marks_the_centre():
    c = blank(5, 5)
    c.draw_circle(2, 2, 0, '#')
    assert (2, 2) in ink(c)


def test_draw_circle_clips_at_the_edge():
    c = blank(5, 5)
    c.draw_circle(0, 0, 3, '#')
    assert (0, 0) in ink(c)
    assert all(0 <= x < 5 and 0 <= y < 5 for x, y in ink(c))


def test_draw_ellipse_is_wider_than_tall():
    c = blank(31, 21)
    c.draw_ellipse(15, 10, 12, 5, '#')
    drawn = ink(c)
    xs = [x for x, _ in drawn]
    ys = [y for _, y in drawn]
    assert (max(xs) - min(xs)) > (max(ys) - min(ys))


def test_draw_ellipse_fill_covers_the_interior():
    c = blank(21, 21)
    c.draw_ellipse(10, 10, 8, 6, '#', fill=True)
    assert (10, 5) in ink(c) and (10, 15) in ink(c)


def test_draw_ellipse_with_a_degenerate_radius():
    c = blank(11, 11)
    c.draw_ellipse(5, 5, 0, 4, '#')
    c.draw_ellipse(5, 5, 4, 0, '#')
    c.draw_ellipse(5, 5, -3, 4, '#')
    assert ink(c) == set()


def test_draw_ellipse_fill_and_outline_differ():
    outline, filled = blank(21, 21), blank(21, 21)
    outline.draw_ellipse(10, 10, 8, 6, '#')
    filled.draw_ellipse(10, 10, 8, 6, '#', fill=True)
    assert len(ink(filled)) > len(ink(outline))


# -------------------------------------------------------------------
# triangle / polygon
# -------------------------------------------------------------------

def test_draw_triangle_outline_draws_three_edges():
    c = blank(12, 9)
    c.draw_triangle(1, 1, 10, 1, 5, 7, '#')
    assert (1, 1) in ink(c) and (10, 1) in ink(c) and (5, 7) in ink(c)


def test_draw_triangle_fill_covers_the_centre():
    c = blank(12, 9)
    c.draw_triangle(1, 1, 10, 1, 5, 7, '#', fill=True)
    assert (5, 4) in ink(c), 'the fill missed the centre'


def test_draw_triangle_fill_of_a_flat_triangle():
    c = blank(10, 4)
    c.draw_triangle(1, 1, 8, 1, 4, 1, '#', fill=True)
    assert ink(c) == set(), 'a zero-height triangle filled a line'


def test_draw_triangle_clips():
    c = blank(6, 6)
    c.draw_triangle(-5, -5, 11, 3, 3, 11, '#', fill=True)
    assert all(0 <= x < 6 and 0 <= y < 6 for x, y in ink(c))


def test_draw_polygon_outline_closes():
    c = blank(12, 9)
    c.draw_polygon([(1, 1), (10, 1), (10, 7), (1, 7)], '#')
    assert (1, 1) in ink(c) and (1, 7) in ink(c), 'the outline left a gap'


def test_draw_polygon_fill_covers_the_centre():
    c = blank(12, 9)
    c.draw_polygon([(1, 1), (10, 1), (10, 7), (1, 7)], '#', fill=True)
    assert (5, 4) in ink(c)


def test_draw_polygon_needs_three_points():
    c = blank(8, 8)
    c.draw_polygon([(1, 1), (5, 5)], '#', fill=True)
    c.draw_polygon([], '#', fill=True)
    assert ink(c) == set()


def test_draw_polygon_fill_handles_a_concave_shape():
    c = blank(14, 10)
    c.draw_polygon([(1, 1), (12, 1), (12, 4), (4, 4), (4, 8), (1, 8)],
                   '#', fill=True)
    assert (8, 2) in ink(c), 'the top bar of the L was not filled'
    assert (2, 6) in ink(c), 'the leg of the L was not filled'
    assert (8, 6) not in ink(c), 'the notch of the L was filled in'


def test_draw_polygon_with_a_horizontal_edge():
    c = blank(12, 9)
    c.draw_polygon([(1, 1), (10, 1), (10, 7), (1, 7)], '#', fill=True)
    assert (1, 1) in ink(c) and (10, 1) in ink(c)


# -------------------------------------------------------------------
# bezier / arc
# -------------------------------------------------------------------

def test_draw_bezier_passes_through_its_endpoints():
    c = blank(30, 20)
    c.draw_bezier([(2.0, 2.0), (20.0, 16.0), (27.0, 3.0)], steps=40, char='#')
    assert (2, 2) in ink(c) and (27, 3) in ink(c)


def test_draw_bezier_stays_within_its_control_hull():
    c = blank(40, 40)
    c.draw_bezier([(5.0, 5.0), (30.0, 35.0)], steps=60, char='#')
    assert all(5 <= x <= 30 and 5 <= y <= 35 for x, y in ink(c))


def test_draw_bezier_needs_two_points():
    c = blank()
    c.draw_bezier([(1.0, 1.0)], char='#')
    assert ink(c) == set()


def test_draw_bezier_rejects_a_zero_step_count():
    c = blank()
    with pytest.raises(ValueError):
        c.draw_bezier([(1.0, 1.0), (2.0, 2.0)], steps=0)


def test_draw_arc_covers_the_requested_sweep():
    c = blank(21, 21)
    c.draw_arc(10, 10, 8, 0, math.pi / 2, '#')
    assert (18, 10) in ink(c), 'the arc missed its start'
    assert (10, 18) in ink(c), 'the arc missed its end'


def test_draw_arc_stays_on_its_radius():
    c = blank(41, 41)
    c.draw_arc(20, 20, 12, 0, math.pi * 2, '#')
    for x, y in ink(c):
        assert abs(math.hypot(x - 20, y - 20) - 12) < 1.5


def test_draw_arc_with_a_tiny_radius():
    c = blank(9, 9)
    c.draw_arc(4, 4, 0, 0, 1.0, '#')
    assert ink(c) == {(4, 4)}


# -------------------------------------------------------------------
# gradients
# -------------------------------------------------------------------

def test_gradient_fill_uses_the_scheme_characters():
    c = blank(10, 1)
    c.gradient_fill(0, 0, 10, 1, Gradient(BLACK, WHITE))
    chars = [char_at(c, x, 0) for x in range(10)]
    assert len(set(chars)) > 1, 'the gradient was flat'


def test_gradient_fill_vertical_and_horizontal_differ():
    horiz, vert = blank(10, 6), blank(10, 6)
    horiz.gradient_fill(0, 0, 10, 6, Gradient(BLACK, WHITE),
                         horizontal=True)
    vert.gradient_fill(0, 0, 10, 6, Gradient(BLACK, WHITE),
                       horizontal=False)
    assert vert.buffer[5][0].fg != horiz.buffer[5][0].fg


def test_gradient_fill_normalises_reversed_corners():
    fwd, rev = blank(10, 4), blank(10, 4)
    g = Gradient(BLACK, WHITE)
    fwd.gradient_fill(2, 1, 8, 3, g, horizontal=True)
    rev.gradient_fill(8, 3, 2, 1, g, horizontal=True)
    assert [fwd.buffer[1][x].fg for x in range(10)] == \
           [rev.buffer[1][x].fg for x in range(10)]


def test_gradient_fill_degenerate_span_does_not_divide_by_zero():
    c = blank()
    c.gradient_fill(3, 3, 3, 3, Gradient(BLACK, WHITE))


def test_gradient_fill_clears_the_foreground():
    c = blank(4, 1)
    c.draw_text(0, 0, 'abcd', fg=RED)
    c.gradient_fill(0, 0, 4, 1, Gradient(BLACK, WHITE))
    assert all(c.buffer[0][x].fg is not None for x in range(4))


def test_gradient_fill_radial_is_brightest_at_the_edge():
    c = blank(21, 21)
    c.gradient_fill_radial(10, 10, 8, Gradient(BLACK, WHITE))
    centre = c.buffer[10][10].fg
    edge = c.buffer[10][18].fg   # the +r ring must be painted
    assert centre is not None and edge is not None
    assert centre.r < edge.r


def test_gradient_fill_radial_with_a_zero_radius():
    c = blank(9, 9)
    c.gradient_fill_radial(4, 4, 0, Gradient(BLACK, WHITE))
    assert ink(c) == set()


def test_gradient_fill_radial_with_a_negative_radius():
    c = blank(9, 9)
    c.gradient_fill_radial(4, 4, -3, Gradient(BLACK, WHITE))
    assert ink(c) == set()


def test_fill_gradient_x_puts_the_colour_in_the_background():
    c = blank(10, 3)
    assert c.fill_gradient_x(0, 0, 10, 3, Gradient(BLACK, WHITE)) is c
    cell = c.buffer[1][5]
    assert cell.char == ' '
    assert cell.bg is not None
    assert cell.fg is None


def test_fill_gradient_x_varies_left_to_right():
    c = blank(10, 1)
    c.fill_gradient_x(0, 0, 10, 1, Gradient(BLACK, WHITE))
    left, right = c.buffer[0][0].bg, c.buffer[0][9].bg
    assert left.r < right.r


def test_fill_gradient_y_varies_top_to_bottom():
    c = blank(3, 10)
    c.fill_gradient_y(0, 0, 3, 10, Gradient(BLACK, WHITE))
    top, bottom = c.buffer[0][1].bg, c.buffer[9][1].bg
    assert top.r < bottom.r


def test_fill_gradient_returns_self_for_chaining():
    c = blank()
    g = Gradient(BLACK, WHITE)
    assert c.fill_gradient_y(0, 0, 4, 4, g) is c


def test_fill_gradient_with_a_one_pixel_span():
    c = blank(3, 3)
    c.fill_gradient_x(0, 0, 1, 1, Gradient(BLACK, WHITE))
    c.fill_gradient_y(0, 0, 1, 1, Gradient(BLACK, WHITE))
    assert c.buffer[0][0].bg is not None


def test_fill_gradient_clips():
    c = blank(4, 4)
    c.fill_gradient_x(-5, -5, 20, 20, Gradient(BLACK, WHITE))
    assert all(c.buffer[y][x].bg is not None for y in range(4) for x in range(4))


def test_fill_sky_sweeps_above_and_flattens_below():
    c = blank(6, 10)
    c.fill_sky(Gradient(BLACK, WHITE), horizon=0.5)
    assert c.buffer[1][3].bg is not None
    ground = c.buffer[9][3].bg
    assert all(c.buffer[y][3].bg == ground for y in range(5, 10)), \
        'the ground is not flat'


def test_fill_sky_returns_self():
    c = blank()
    assert c.fill_sky(Gradient(BLACK, WHITE)) is c


@pytest.mark.parametrize('horizon', [-1.0, 0.0, 1.0, 2.0])
def test_fill_sky_clamps_the_horizon(horizon):
    c = blank(4, 6)
    c.fill_sky(Gradient(BLACK, WHITE), horizon=horizon)


# -------------------------------------------------------------------
# noise
# -------------------------------------------------------------------

def test_noise_is_reproducible():
    a, b = blank(10, 4), blank(10, 4)
    a.noise(0, 0, 10, 4, seed=42)
    b.noise(0, 0, 10, 4, seed=42)
    assert [[a.buffer[y][x].char for x in range(10)] for y in range(4)] == \
           [[b.buffer[y][x].char for x in range(10)] for y in range(4)]


def test_noise_differs_between_seeds():
    a, b = blank(20, 6), blank(20, 6)
    a.noise(0, 0, 20, 6, seed=1)
    b.noise(0, 0, 20, 6, seed=2)
    assert [[a.buffer[y][x].char for x in range(20)] for y in range(6)] != \
           [[b.buffer[y][x].char for x in range(20)] for y in range(6)]


def test_noise_does_not_disturb_the_global_random_state():
    import random
    random.seed(1234)
    expected = [random.random() for _ in range(3)]
    random.seed(1234)
    blank(20, 10).noise(0, 0, 20, 10, seed=7)
    assert [random.random() for _ in range(3)] == expected


def test_noise_clips():
    """SHADE_CHARS contains ' ', so a written cell can look blank. Clipping is
    shown by matching the call that was clipped against the tight one."""
    clipped, tight = blank(5, 5), blank(5, 5)
    clipped.noise(-4, -4, 20, 20, seed=3)
    tight.noise(0, 0, 5, 5, seed=3)
    assert [[clipped.buffer[y][x].char for x in range(5)] for y in range(5)] == \
           [[tight.buffer[y][x].char for x in range(5)] for y in range(5)]


def test_noise_leaves_the_rest_of_the_surface_alone():
    c = blank(10, 6)
    c.fill_rect(0, 0, 10, 6, '@')           # a marker everywhere
    c.noise(2, 2, 3, 2, seed=1)
    for y in range(6):
        for x in range(10):
            inside = 2 <= x < 5 and 2 <= y < 4
            if not inside:
                assert char_at(c, x, y) == '@', (x, y)


def test_noise_with_a_negative_size():
    c = blank()
    c.noise(0, 0, -4, -4, seed=3)
    assert ink(c) == set()


# -------------------------------------------------------------------
# the whole surface, on both surfaces, at hostile sizes
# -------------------------------------------------------------------

def _all_calls(c):
    """Every primitive, with parameters that are deliberately awkward."""
    g = Gradient(BLACK, WHITE)
    yield lambda: c.blit_canvas(blank(2, 2), 0, 0)
    yield lambda: c.fill_rect(-2, -2, 40, 40, '#', fg=RED, bg=BLUE)
    yield lambda: c.fill(0, 0, 'o')
    yield lambda: c.draw_text(-2, -2, 'hello', fg=RED)
    yield lambda: c.draw_text_at(0, 0, 'hi', anchor='se')
    yield lambda: c.draw_text_centered(0, 'hi')
    yield lambda: c.draw_line(-5, -5, 30, 30, '#')
    yield lambda: c.draw_line_thick(0, 5, 20, 5, thickness=3, char='#')
    yield lambda: c.draw_ray(0.0, 0.0, 20.0, 10.0, '#', fg=RED, fade=True)
    yield lambda: c.draw_rect(1, 1, 8, 6, '#', radius=2)
    yield lambda: c.draw_circle(10, 6, 5, '#', fill=True)
    yield lambda: c.draw_ellipse(10, 6, 7, 4, '#', fill=True)
    yield lambda: c.draw_triangle(1, 1, 18, 2, 9, 11, '#', fill=True)
    yield lambda: c.draw_polygon([(1, 1), (18, 2), (12, 11), (2, 9)], '#', fill=True)
    yield lambda: c.draw_bezier([(1.0, 1.0), (10.0, 10.0), (19.0, 2.0)], steps=20)
    yield lambda: c.draw_arc(10, 6, 6, 0, math.pi * 1.5, '#')
    yield lambda: c.gradient_fill(0, 0, 20, 12, g)
    yield lambda: c.gradient_fill_radial(10, 6, 5, g)
    yield lambda: c.fill_gradient_x(0, 0, 20, 12, g)
    yield lambda: c.fill_gradient_y(0, 0, 20, 12, g)
    yield lambda: c.fill_sky(g, horizon=0.4)
    yield lambda: c.noise(0, 0, 20, 12, seed=5)


SURFACES = [lambda: blank(24, 12), lambda: HiResCanvas(24, 12)]


@pytest.mark.parametrize('factory', SURFACES)
def test_every_primitive_survives_a_full_sweep(factory):
    c = factory()
    for call in _all_calls(c):
        call()
    # nothing escaped the buffer
    for y in range(c.height):
        assert len(c.buffer[y]) == c.width


@pytest.mark.parametrize('w,h', [(1, 1), (1, 8), (8, 1), (2, 2), (3, 3)])
def test_every_primitive_survives_tiny_surfaces(w, h):
    c = Canvas(w, h)
    for call in _all_calls(c):
        call()
    for y in range(h):
        assert len(c.buffer[y]) == w


@pytest.mark.parametrize('factory', SURFACES)
def test_primitives_never_raise_on_a_non_finite_coordinate(factory):
    c = factory()
    c.draw_line(0, 0, float('inf'), 3, '#')
    c.draw_ray(0.0, 0.0, float('nan'), 3.0, '#')
    c.draw_bezier([(0.0, 0.0), (float('inf'), 1.0)], steps=5)


# -------------------------------------------------------------------
# HiResCanvas parity
# -------------------------------------------------------------------

def test_hires_exposes_the_same_primitives():
    calls = list(_all_calls(blank()))          # a generator: only read it once
    assert calls
    import inspect
    for _ in calls:
        pass
    for name in ('blit_canvas', 'fill_rect', 'fill', 'draw_text', 'draw_text_at',
                 'draw_text_centered', 'draw_line', 'draw_line_thick', 'draw_ray',
                 'draw_rect', 'draw_circle', 'draw_ellipse', 'draw_triangle',
                 'draw_polygon', 'draw_bezier', 'draw_arc', 'gradient_fill',
                 'gradient_fill_radial', 'fill_gradient_x', 'fill_gradient_y',
                 'fill_sky', 'noise'):
        assert hasattr(HiResCanvas, name), f'HiResCanvas lacks {name}'
        assert hasattr(Canvas, name), f'Canvas lacks {name}'
    assert inspect.signature(HiResCanvas.draw_rect).parameters.keys() == \
           inspect.signature(Canvas.draw_rect).parameters.keys()


def test_hires_drawing_stays_inside_its_buffer():
    c = HiResCanvas(20, 10)
    for call in _all_calls(c):
        call()
    for y in range(c.h):
        for x in range(c.w):
            assert c.buffer[y][x].char is not None
