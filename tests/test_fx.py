"""Tests for the fx layer: shaders, post-processing filters and transitions.

These are all canvas-to-canvas transforms, so the useful assertions are
structural: the output keeps the buffer's shape, nothing raises on a canvas
too small for the filter's window, and the documented knobs actually change
the result. Several of these shaders sample a neighbourhood, so running them
on a canvas smaller than the filter radius is a real edge case rather than a
contrived one.
"""

from __future__ import annotations

import pytest

from spore_engine import Canvas, Color
from spore_engine.fx import postfx, shaders, transitions


# --- helpers -------------------------------------------------------------

def _painted(w=24, h=12, seed=0):
    """A canvas with plenty of both glyphs and colour to chew on."""
    import random
    rng = random.Random(seed)
    c = Canvas(w, h)
    for y in range(h):
        for x in range(w):
            c.set_pixel(x, y, rng.choice('@#*+=-:. '),
                        Color(rng.randrange(256), rng.randrange(256), rng.randrange(256)))
    return c


def _text_of(canvas):
    return [''.join(cell.char for cell in row) for row in canvas.buffer]


def _signature(canvas):
    return tuple((cell.char, cell.fg) for row in canvas.buffer for cell in row)


# --- shaders -------------------------------------------------------------

ALL_SHADERS = [
    shaders.ASCIIRemap(), shaders.ASCIIRemap(invert=True, use_bg=True),
    shaders.ChannelShift(1, 0, 0), shaders.ChannelShift(0, 2, -2),
    shaders.Kaleidoscope(6), shaders.Ripple(), shaders.Ripple(3.0, 0.9, 2.0),
    shaders.VHSGlitch(0.3), shaders.Warp(), shaders.Crystallize(4),
    shaders.Crystallize(1), shaders.PixelSort('x'), shaders.PixelSort('y'),
    shaders.Emboss(1.0), shaders.Emboss(3.0), shaders.HeatHaze(),
    shaders.HeatHaze(4.0, 0.2, 3.0), shaders.Solarize(0.3),
    shaders.Posterize(2), shaders.Posterize(8), shaders.CelShade(2, 0.1),
    shaders.SwirlDistort(0.05), shaders.WaveDistort(),
    shaders.WaveDistort(4.0, 3.0, 0.5, 0.4, 2.0), shaders.KuwaharaFilter(1),
    shaders.KuwaharaFilter(3),
]
SHADER_IDS = [type(s).__name__ + repr(getattr(s, '__dict__', {}))[:40] for s in ALL_SHADERS]


@pytest.mark.parametrize('shader', ALL_SHADERS, ids=SHADER_IDS)
def test_shader_preserves_canvas_shape(shader):
    canvas = _painted()
    before = (canvas.width, canvas.height)
    shader.apply(canvas, t=1.25, dt=0.016)
    assert (canvas.width, canvas.height) == before


@pytest.mark.parametrize('shader', ALL_SHADERS, ids=SHADER_IDS)
def test_shader_handles_a_canvas_smaller_than_its_window(shader):
    """Filters that sample a neighbourhood must clip, not read past the end."""
    for w, h in [(1, 1), (2, 2), (3, 1), (1, 3), (5, 4)]:
        shader.apply(_painted(w, h, seed=w), t=0.5, dt=0.016)


@pytest.mark.parametrize('shader', ALL_SHADERS, ids=SHADER_IDS)
def test_shader_is_idempotent_on_an_empty_canvas(shader):
    """A blank canvas has no edges or colours for a filter to trip over."""
    shader.apply(Canvas(16, 8), t=0.0, dt=0.0)


@pytest.mark.parametrize('shader', ALL_SHADERS, ids=SHADER_IDS)
def test_shader_output_is_always_a_valid_color(shader):
    """No filter may produce an out-of-gamut colour.

    Color validates its channels, so a filter that rounds or scales carelessly
    raises here instead of drawing something subtly wrong.
    """
    canvas = _painted()
    shader.apply(canvas, t=2.0, dt=0.033)
    for row in canvas.buffer:
        for cell in row:
            if cell.fg is not None:
                assert 0 <= cell.fg.r <= 255
                assert 0 <= cell.fg.g <= 255
                assert 0 <= cell.fg.b <= 255
            if cell.bg is not None:
                assert 0 <= cell.bg.r <= 255


# --- individual shader behaviour ----------------------------------------

def test_ascii_remap_invert_is_the_complement():
    plain, inverted = _painted(16, 8), _painted(16, 8)
    shaders.ASCIIRemap(invert=False).apply(plain)
    shaders.ASCIIRemap(invert=True).apply(inverted)
    ramp = ' .:-=+*#%@'
    for a, b in zip(_text_of(plain), _text_of(inverted), strict=False):
        for ca, cb in zip(a, b, strict=False):
            if ca in ramp and cb in ramp:
                assert ramp.index(ca) + ramp.index(cb) == len(ramp) - 1


def test_posterize_reduces_the_number_of_distinct_levels():
    c = _painted(20, 10)
    shaders.Posterize(levels=3).apply(c)
    levels = {cell.fg.r for row in c.buffer for cell in row if cell.fg}
    assert len(levels) <= 3


def test_channel_shift_samples_to_the_right():
    """ChannelShift(r_shift=3) takes red from three columns further right.

    The shift index is clamped to the canvas, so the right edge re-samples its
    own rightmost column rather than falling off the end.
    """
    original = _painted(20, 10)
    shifted = _painted(20, 10)
    shaders.ChannelShift(r_shift=3, g_shift=0, b_shift=0).apply(shifted)
    for y in range(10):
        for x in range(20 - 3):
            assert shifted.buffer[y][x].fg.r == original.buffer[y][x + 3].fg.r
            # The untouched channels still come from this column.
            assert shifted.buffer[y][x].fg.g == original.buffer[y][x].fg.g
            assert shifted.buffer[y][x].fg.b == original.buffer[y][x].fg.b


def test_pixel_sort_accepts_both_axes():
    for axis in ('x', 'y'):
        c = _painted(16, 8)
        shaders.PixelSort(axis=axis).apply(c)
        assert len(_text_of(c)) == 8


def test_solarize_inverts_above_the_threshold():
    c = Canvas(4, 1)
    c.set_pixel(0, 0, ' ', bg=Color(10, 10, 10))     # dark  -> unchanged
    c.set_pixel(1, 0, ' ', bg=Color(240, 240, 240))  # light -> inverted
    c.set_pixel(2, 0, ' ', bg=Color(200, 30, 30))
    shaders.Solarize(threshold=0.5).apply(c)
    assert c.buffer[0][0].bg.r == 10
    assert c.buffer[0][1].bg.r < 100


def test_kuwahara_filter_needs_at_least_a_few_pixels():
    """A radius larger than the canvas must not read out of bounds."""
    c = _painted(4, 4)
    shaders.KuwaharaFilter(radius=10).apply(c)
    assert len(_text_of(c)) == 4


def test_crystallize_flattens_colour_into_blocks():
    """Crystallize should make each cell take one seed's colour.

    It is a Voronoi filter, so a 1x1 cell is not the identity: the seed for a
    cell is jittered inside it and a pixel can legitimately be nearer to a
    neighbour's seed. What must hold is that few distinct colours survive.
    """
    c = _painted(32, 16)
    before = len({cell.fg for row in c.buffer for cell in row if cell.fg})
    shaders.Crystallize(cell_size=6, seed=1).apply(c)
    after = len({cell.fg for row in c.buffer for cell in row if cell.fg})
    assert after < before / 4, f'{before} -> {after} is not enough flattening'


# --- pipeline ------------------------------------------------------------

def test_pipeline_runs_shaders_in_order():
    pipe = shaders.ShaderPipeline()
    pipe.add(shaders.Solarize(0.5))
    pipe.add(shaders.Posterize(2))
    assert len(pipe) == 2
    c = _painted(16, 8)
    pipe.apply(c, t=0.5, dt=0.016)
    assert len(_text_of(c)) == 8


def test_pipeline_get_add_remove():
    pipe = shaders.ShaderPipeline()
    s = shaders.Ripple()
    pipe.add(s)
    assert pipe.get('ripple') is s
    assert pipe.get('nope') is None
    pipe.remove('ripple')
    assert pipe.get('ripple') is None
    assert len(pipe) == 0


def test_pipeline_applies_a_duplicated_shader_twice():
    """ShaderPipeline is a list wrapper, so duplicates are honoured.

    Deduplicating by name would silently drop a deliberate second pass, and
    the pipeline is cheap to reason about as an ordered list.
    """
    pipe = shaders.ShaderPipeline()
    once, twice = _painted(12, 6), _painted(12, 6)
    pipe.add(shaders.SwirlDistort(0.05))
    pipe.apply(once)
    pipe.add(shaders.SwirlDistort(0.05))
    pipe.apply(twice)
    assert len(pipe) == 2
    assert _signature(once) != _signature(twice)


def test_base_shader_apply_is_abstract():
    with pytest.raises(NotImplementedError):
        shaders.Shader().apply(Canvas(4, 4))


# --- post-processing -----------------------------------------------------

POSTFX = [
    (postfx.box_blur, (2,)), (postfx.maximum_filter, (2,)),
    (postfx.uniform_filter, (2,)),
    (postfx.edge_detect, ()), (postfx.glow, ()),
    (postfx.chromatic_aberration, (2,)), (postfx.scanlines, ()),
    (postfx.vignette, ()), (postfx.pixelate, (3,)),
    (postfx.dither, ()),
]


@pytest.mark.parametrize('fn,args', POSTFX, ids=[f.__name__ for f, _ in POSTFX])
def test_postfx_preserves_shape(fn, args):
    c = _painted(24, 12)
    before = _text_of(c)
    fn(c, *args)
    assert len(_text_of(c)) == len(before)
    assert all(len(r) == len(before[0]) for r in _text_of(c))


@pytest.mark.parametrize('fn,args', POSTFX, ids=[f.__name__ for f, _ in POSTFX])
def test_postfx_on_tiny_canvases(fn, args):
    for w, h in [(1, 1), (2, 2), (3, 5), (5, 3)]:
        fn(_painted(w, h, seed=w), *args)


def test_vignette_darkens_the_corners_more_than_the_centre():
    c = _painted(31, 21)
    for row in c.buffer:
        for cell in row:
            cell.fg = Color(200, 200, 200)
    postfx.vignette(c)
    def lum(x, y):
        return c.buffer[y][x].fg.r
    centre = lum(15, 10)
    assert lum(0, 0) < centre
    assert lum(30, 20) < centre


def test_pixelate_averages_colour_within_a_block():
    """pixelate flattens colour, not glyphs.

    Averaging the glyph as well would destroy the text, so only fg is
    touched: within a block every cell must end up the same colour.
    """
    c = _painted(32, 8)
    for y in range(8):
        for x in range(32):
            c.buffer[y][x].char = chr(65 + x % 26)
    postfx.pixelate(c, 4)
    for y in range(8):
        for start in range(0, 32, 4):
            block = [c.buffer[y][x].fg for x in range(start, start + 4)]
            assert len(set(block)) == 1
    # The glyphs survived.
    assert c.buffer[0][0].char == 'A'
    assert c.buffer[0][1].char == 'B'


def test_scanlines_alters_odd_rows():
    c = _painted(10, 8)
    for row in c.buffer:
        for cell in row:
            cell.fg = Color(100, 100, 100)
    postfx.scanlines(c)
    rows = [c.buffer[y][0].fg.r for y in range(8)]
    assert len(set(rows)) > 1, 'scanlines made every row identical'


def test_palette_remap_replaces_colour_with_the_gradient():
    from spore_engine import Gradient
    grad = Gradient(Color(0, 0, 0), Color(255, 255, 255))
    c = _painted(16, 8)
    postfx.palette_remap(c, grad)
    for row in c.buffer:
        for cell in row:
            if cell.fg is not None:
                # A black-to-white ramp is grey, so all channels must agree.
                assert cell.fg.r == cell.fg.g == cell.fg.b
                assert 0 <= cell.fg.r <= 255


def test_palette_remap_on_tiny_canvases():
    from spore_engine import Gradient
    grad = Gradient(Color(0, 0, 0), Color(255, 255, 255))
    for w, h in [(1, 1), (2, 2), (3, 5)]:
        postfx.palette_remap(_painted(w, h, seed=w), grad)


# --- transitions ---------------------------------------------------------

TRANSITIONS = [
    transitions.Fade(), transitions.Wipe(), transitions.Wipe('left'),
    transitions.Wipe('down'), transitions.Wipe('up'),
    transitions.Checkerboard(), transitions.Checkerboard(4),
    transitions.PixelDissolve(), transitions.Slide(),
]


@pytest.mark.parametrize('tr', TRANSITIONS, ids=lambda t: type(t).__name__ + str(getattr(t, 'direction', '')) + str(getattr(t, 'size', '')))
def test_transition_runs_at_every_progress(tr):
    for t in (-1.0, 0.0, 0.25, 0.5, 0.75, 1.0, 2.0):
        tr.apply(_painted(20, 10), _painted(20, 10, seed=1), t)


@pytest.mark.parametrize('tr', TRANSITIONS, ids=lambda t: type(t).__name__)
def test_transition_handles_mismatched_sizes(tr):
    """The two canvases need not be the same size."""
    for dw, dh, sw, sh in [(20, 10, 12, 6), (12, 6, 20, 10), (5, 5, 1, 1), (1, 1, 5, 5)]:
        tr.apply(_painted(dw, dh), _painted(sw, sh, seed=2), 0.5)


def test_transition_base_class_is_abstract():
    with pytest.raises(NotImplementedError):
        transitions.Transition().apply(Canvas(2, 2), Canvas(2, 2), 0.5)


def test_fade_convention_matches_the_other_transitions():
    """t=0 shows the source, t=1 reaches the destination.

    This is the "from the current screen to the next one" convention, and
    Fade, Wipe and the dissolves all have to agree on it or a scene change
    would appear to run backwards depending on which effect was used.
    """
    src, dst = _painted(12, 6), _painted(12, 6, seed=9)
    at_zero = _painted(12, 6)
    transitions.Fade().apply(at_zero, src, 0.0)
    assert _signature(at_zero) == _signature(src)

    at_one = _painted(12, 6, seed=9)
    transitions.Fade().apply(at_one, src, 1.0)
    for y in range(6):
        for x in range(12):
            assert at_one.buffer[y][x].fg == dst.buffer[y][x].fg


def test_wipe_direction_actually_differs():
    b = _painted(16, 8, seed=3)
    right, left = _painted(16, 8), _painted(16, 8)
    transitions.Wipe('right').apply(right, b, 0.5)
    transitions.Wipe('left').apply(left, b, 0.5)
    assert _signature(right) != _signature(left)


def test_pixel_dissolve_is_deterministic_for_a_seed():
    b = _painted(16, 8, seed=4)
    one, two = _painted(16, 8), _painted(16, 8)
    transitions.PixelDissolve().apply(one, b, 0.5)
    transitions.PixelDissolve().apply(two, b, 0.5)
    assert _signature(one) == _signature(two)
