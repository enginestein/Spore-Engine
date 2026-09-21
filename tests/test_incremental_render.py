"""Incremental/dirty-cell rendering: unchanged cells must not be re-emitted."""

import io

from spore_engine import Canvas, Color


def _render(c, clear_first=True, force_full=False):
    buf = io.StringIO()
    c.render_to(buf, clear_first=clear_first, force_full=force_full)
    return buf.getvalue()


def _signed_bytes(out):
    return out.encode('utf-8', 'surrogateescape')


def test_first_render_is_full_then_next_is_empty():
    c = Canvas(20, 5)
    c.draw_text(1, 1, 'hello', fg=Color(255, 255, 255), z=1)
    first = _render(c)
    stats_first = c.render_stats
    second = _render(c)
    stats_second = c.render_stats
    assert 'hello' in first
    assert stats_first['full'] is True
    # nothing changed -> no cell is re-emitted (only the optional home seq)
    assert stats_second['cells'] == 0
    assert stats_second['rows'] == 0
    assert stats_second['full'] is False
    assert 'hello' not in second


def test_single_cell_change_is_batched_and_minimal():
    c = Canvas(20, 5)
    c.draw_text(1, 1, 'hello', fg=Color(255, 255, 255), z=1)
    _render(c)
    # move exactly one char
    c.set_pixel(4, 1, 'X', fg=Color(255, 255, 255), z=1)
    out = _render(c)
    stats = c.render_stats
    assert 'X' in out
    assert 'hello' not in out
    assert stats['cells'] < 10  # far fewer than the full 100-cell buffer
    assert stats['rows'] == 1
    # regenerating the full frame from scratch is strictly larger
    fresh = Canvas(20, 5)
    fresh.draw_text(1, 1, 'hhhhhhhhhhhhhhhhhhh', fg=Color(255, 255, 255), z=1)
    full_out = _render(fresh)
    assert len(_signed_bytes(out)) < len(_signed_bytes(full_out))


def test_bg_change_is_detected():
    c = Canvas(10, 3)
    c.set_pixel(2, 1, ' ', bg=Color(10, 20, 30), z=0)
    _render(c)
    # same char, same fg, only the background colour flips
    c.set_pixel(2, 1, ' ', bg=Color(200, 0, 0), z=0)
    out = _render(c)
    assert Color(200, 0, 0).ansi_bg() in out
    assert c.render_stats['cells'] == 1


def test_clear_then_repaint_is_incremental():
    c = Canvas(20, 5)
    c.fill_rect(0, 0, 20, 5, ' ', bg=Color(1, 2, 3), z=0)
    _render(c)
    # the classic App/demo pattern: clear whole buffer, repaint it identically
    c.clear()
    c.fill_rect(0, 0, 20, 5, ' ', bg=Color(1, 2, 3), z=0)
    out = _render(c)
    stats = c.render_stats
    assert stats['cells'] == 0, 'identical frame must not re-emit background'
    assert stats['full'] is False
    # clear + repaint with just a small delta stays minimal
    c.clear()
    c.fill_rect(0, 0, 20, 5, ' ', bg=Color(1, 2, 3), z=0)
    c.set_pixel(3, 1, '!', fg=Color(255, 255, 255), z=5)
    changed = _render(c)
    assert '!' in changed
    assert c.render_stats['cells'] <= 4
    full = Canvas(20, 5)
    full.fill_rect(0, 0, 20, 5, ' ', bg=Color(1, 2, 3), z=0)
    assert len(_signed_bytes(changed)) < len(_signed_bytes(_render(full)))


def test_force_full_redraw():
    c = Canvas(10, 4)
    c.set_pixel(1, 1, 'a', fg=Color(255, 255, 255), z=1)
    _render(c)
    out = _render(c, force_full=True)
    assert 'a' in out
    assert c.render_stats['full'] is True


def test_full_redraw_helper_invalidates():
    c = Canvas(10, 4)
    c.set_pixel(1, 1, 'a', fg=Color(255, 255, 255), z=1)
    _render(c)
    c.full_redraw()
    out = _render(c)
    assert out != ''
    assert c.render_stats['full'] is True


def test_stats_property_on_fresh_canvas():
    c = Canvas(4, 4)
    assert c.render_stats is None
    _render(c)
    assert c.render_stats['cells'] == 16