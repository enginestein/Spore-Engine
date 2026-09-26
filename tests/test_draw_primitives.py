"""Regression tests for drawing primitives whose parameters were ignored.

Each test here corresponds to a real defect where a documented public
parameter had no observable effect, so a caller's intent was silently
discarded.
"""

from __future__ import annotations

import pytest

from spore_engine import Canvas
from spore_engine.gen.lsystem import LSystem


def _ink(canvas):
    return {(x, y)
            for y in range(canvas.height)
            for x in range(canvas.width)
            if canvas.buffer[y][x].char != ' '}


# --- draw_line_thick -----------------------------------------------------

def test_line_thickness_of_one_is_a_plain_line():
    c = Canvas(20, 5)
    c.draw_line_thick(0, 2, 19, 2, thickness=1, char='#')
    assert _ink(c) == {(x, 2) for x in range(20)}


@pytest.mark.parametrize('thickness', [2, 3, 4, 5, 7, 9])
def test_horizontal_line_thickness_is_exact(thickness):
    """A horizontal line must span exactly `thickness` rows.

    The old implementation always drew three passes (+0, +1, -1) regardless
    of the argument, so thickness=2 and thickness=40 rendered identically.
    It also used half-integer offsets, which round ambiguously on a cell
    grid and collapsed even thicknesses in half.
    """
    c = Canvas(30, 15)
    c.draw_line_thick(2, 7, 27, 7, thickness=thickness, char='#')
    rows = {y for _, y in _ink(c)}
    assert len(rows) == thickness
    assert min(rows) == 7 - thickness // 2
    assert max(rows) == 7 - thickness // 2 + thickness - 1


@pytest.mark.parametrize('thickness', [2, 3, 4, 5, 7])
def test_vertical_line_thickness_is_exact(thickness):
    c = Canvas(15, 15)
    c.draw_line_thick(7, 2, 7, 12, thickness=thickness, char='#')
    cols = {x for x, _ in _ink(c)}
    assert len(cols) == thickness


def test_line_thickness_is_clipped_not_wrapped():
    """A thick line at the canvas edge clips, it does not wrap around."""
    c = Canvas(10, 4)
    c.draw_line_thick(0, 0, 9, 0, thickness=5, char='#')
    assert all(0 <= y < c.height for _, y in _ink(c))
    assert {y for _, y in _ink(c)} == {0, 1, 2}


def test_degenerate_line_thickness_does_not_divide_by_zero():
    """A zero-length segment has no direction; the normal must not blow up."""
    c = Canvas(6, 6)
    c.draw_line_thick(3, 3, 3, 3, thickness=4, char='#')
    assert _ink(c), 'a point with thickness should still mark a small blob'


# --- LSystem thickness ---------------------------------------------------

def test_lsystem_honours_thickness():
    """`thickness` used to be written as `'#' if thickness > 1 else '#'`."""
    counts = {}
    for th in (1, 2, 3, 5):
        c = Canvas(30, 14)
        LSystem('F', {}).render(c, x=5, y=7, length=6, thickness=th)
        counts[th] = len(_ink(c))
    assert counts[1] < counts[2] < counts[3] <= counts[5]


def test_lsystem_thickness_one_matches_a_single_line():
    c = Canvas(30, 14)
    LSystem('F', {}).render(c, x=5, y=7, length=6, thickness=1)
    assert _ink(c) == {(5, y) for y in range(1, 8)}
