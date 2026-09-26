"""The array-level image pipeline: fields, images, and the cell sink.

Two things here are load-bearing and easy to regress, so they get real tests
rather than smoke coverage:

* the half-block contract. ``to_cells`` is the only place a picture becomes
  cells, and it has to put colour in ``fg`` on a ``HiResCanvas`` and in ``bg``
  on a ``Canvas`` - the eight ``fg``-only ``postfx`` filters got that wrong, and
  a picture that loses half its sub-cells still looks plausible enough to ship.
* :class:`CellCache`. It only pays off if an unchanged sub-cell keeps the
  ``Color`` object it already had, so the test asserts object *identity*, not
  just equality.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from spore_engine import (Canvas, Color, Gradient, HiResCanvas, PerlinNoise)
from spore_engine.fx.imgops import (CellCache, Field, Image, StarField,
                                   _gradient_lut, to_cells)

H, W = 8, 12
SKY = Gradient(Color(10, 20, 30), Color(200, 220, 255))


# ---------------------------------------------------------------------------
# Field
# ---------------------------------------------------------------------------

class TestFieldBasics:
    def test_holds_float32(self):
        assert Field([[1, 2], [3, 4]]).a.dtype == np.float32

    def test_arithmetic_with_numbers_and_fields(self):
        a = Field([[1.0, 2.0]])
        b = Field([[10.0, 20.0]])
        assert (a + b).a.tolist() == [[11.0, 22.0]]
        assert (a * 3).a.tolist() == [[3.0, 6.0]]
        assert (b - a).a.tolist() == [[9.0, 18.0]]
        assert (b / 2).a.tolist() == [[5.0, 10.0]]
        assert (2 + a).a.tolist() == [[3.0, 4.0]]
        assert (10 - a).a.tolist() == [[9.0, 8.0]]
        assert (-a).a.tolist() == [[-1.0, -2.0]]

    def test_arithmetic_does_not_mutate_operands(self):
        a = Field([[1.0]])
        b = Field([[2.0]])
        _ = a + b
        assert a.a.tolist() == [[1.0]] and b.a.tolist() == [[2.0]]

    def test_shape_mismatch_names_both_shapes(self):
        with pytest.raises(ValueError, match=r'shape mismatch \(1, 2\) vs \(1, 3\)'):
            Field([[1, 2]]) + Field([[1, 2, 3]])

    def test_shape_and_repr(self):
        f = Field.zeros((3, 4))
        assert f.shape == (3, 4)
        assert 'Field' in repr(f)


class TestFieldShaping:
    def test_threshold_linear_ramp(self):
        f = Field([[0.0, 0.5, 1.0]])
        assert f.threshold(0.25, 0.75).a.tolist() == [[0.0, 0.5, 1.0]]

    def test_threshold_without_high_is_a_step(self):
        f = Field([[0.0, 0.5, 1.0]])
        assert f.threshold(0.4).a.tolist() == [[0.0, 1.0, 1.0]]

    def test_smoothstep_is_flat_at_both_ends(self):
        f = Field([[-1.0, 0.0, 0.5, 1.0, 2.0]])
        out = f.smoothstep().a.tolist()[0]
        assert out[0] == 0.0 and out[-1] == 1.0
        assert 0.0 < out[2] < 1.0

    def test_smoothstep_survives_a_degenerate_range(self):
        assert Field([[0.5]]).smoothstep(1.0, 1.0).a.tolist() == [[0.0]]

    def test_clip_abs_sqrt_pow(self):
        assert Field([[-1.0, 0.25, 4.0]]).clip(0, 1).a.tolist() == [[0.0, 0.25, 1.0]]
        assert Field([[-3.0]]).abs().a.tolist() == [[3.0]]
        assert Field([[-1.0, 4.0]]).sqrt().a.tolist() == [[0.0, 2.0]]
        assert Field([[2.0]]).__pow__(2).a.tolist() == [[4.0]]

    def test_shifted_translates_and_zero_fills(self):
        out = Field([[1.0, 2.0]]).shifted(1)
        assert out.a.tolist() == [[0.0, 1.0]]

    def test_shift_off_the_edge_is_all_zero_not_a_crash(self):
        assert Field([[1.0]]).shifted(50).a.tolist() == [[0.0]]
        assert Field([[1.0]]).shifted(-50).a.tolist() == [[0.0]]

    def test_resized_is_a_no_op_at_the_same_size(self):
        f = Field([[1.0, 2.0]])
        assert f.resized(1, 2).a.tolist() == [[1.0, 2.0]]

    def test_resized_grows_and_shrinks(self):
        f = Field([[1.0, 2.0]])
        assert f.resized(2, 4).shape == (2, 4)
        assert f.resized(1, 1).shape == (1, 1)

    def test_row_requires_a_1d_field(self):
        assert Field([1.0, 2.0]).row(slice(None)).tolist() == [1.0, 2.0]
        with pytest.raises(ValueError, match='needs a 1-D field'):
            Field([[1.0]]).row(slice(None))


class TestFieldMorphology:
    def test_dilate_max_grows_and_min_shrinks(self):
        f = Field([[0.0, 1.0, 0.0]])
        assert f.dilate(1, 'max').a[0, 1] == 1.0
        assert f.dilate(1, 'min').a.tolist() == [[0.0, 0.0, 0.0]]

    def test_dilate_rejects_an_unknown_op(self):
        with pytest.raises(ValueError, match="'max' or 'min'"):
            Field.zeros((2, 2)).dilate(1, 'average')

    def test_dilate_below_one_returns_a_copy(self):
        f = Field([[1.0]])
        assert f.dilate(0).a.tolist() == [[1.0]]

    def test_blurred_preserves_the_mean(self):
        f = Field([[0.0, 1.0], [0.0, 1.0]])
        assert pytest.approx(float(f.blurred(1).a.mean()), abs=1e-5) == 0.5

    def test_blurred_below_one_returns_a_copy(self):
        assert float(Field([[0.3]]).blurred(0).a[0, 0]) == pytest.approx(0.3)


class TestFieldGenerators:
    def test_fbm_line_shape_and_range(self):
        f = Field.fbm_line(PerlinNoise(1), 16, 0.1)
        assert f.shape == (16,)
        assert float(f.a.min()) > -0.2 and float(f.a.max()) < 1.2

    def test_fbm_line_zero_frequency_is_flat_mid(self):
        assert Field.fbm_line(PerlinNoise(1), 4, 0.0).a.tolist() == [0.5] * 4

    def test_fbm_2d_shape(self):
        assert Field.fbm(PerlinNoise(1), 4, 6).shape == (4, 6)

    def test_plasma_is_normalised_and_moves_with_time(self):
        a = Field.plasma(H, W, t=0.0)
        b = Field.plasma(H, W, t=2.0)
        assert a.shape == (H, W)
        assert float(a.a.min()) >= 0.0 and float(a.a.max()) <= 1.0
        assert not np.array_equal(a.a, b.a)

    def test_plasma_with_no_terms_is_zero(self):
        assert Field.plasma(2, 2, terms=()).a.tolist() == [[0.0, 0.0], [0.0, 0.0]]

    def test_radial_peaks_at_the_centre(self):
        f = Field.radial(H, W, 5, 4, 3)
        assert float(f.a[4, 5]) == pytest.approx(1.0, abs=1e-5)
        assert float(f.a[0, 0]) == pytest.approx(0.0, abs=1e-5)

    def test_radial_rejects_a_zero_radius(self):
        with pytest.raises(ValueError, match='non-zero radius'):
            Field.radial(2, 2, 0, 0, 0)

    def test_gauss_peak_and_tail(self):
        f = Field.gauss(H, W, 5, 4, 2.0)
        assert float(f.a[4, 5]) == pytest.approx(1.0, abs=1e-5)
        assert float(f.a[0, 0]) < 0.1

    def test_waves_shape_and_range(self):
        f = Field.waves(H, W, t=1.0)
        assert f.shape == (H, W)
        assert float(f.a.min()) >= 0.0 and float(f.a.max()) <= 1.0

    def test_waves_direction_picks_a_different_phase(self):
        assert not np.array_equal(Field.waves(H, W, direction='x').a,
                                  Field.waves(H, W, direction='y').a)


class TestFieldToColour:
    def test_tinted_scales_by_gain(self):
        img = Field.full((2, 2), 0.5).tinted(Color(200, 100, 50))
        assert img.a[0, 0].tolist() == [100.0, 50.0, 25.0]

    def test_palette_maps_field_onto_a_gradient(self):
        f = Field([[0.0, 1.0]])
        img = f.palette(Gradient(Color(0, 0, 0), Color(255, 255, 255)))
        assert img.a[0, 0].tolist() == [0.0, 0.0, 0.0]
        assert img.a[0, 1].tolist() == [255.0, 255.0, 255.0]

    def test_palette_accepts_a_plain_list_of_colours(self):
        img = Field([[0.0, 1.0]]).palette([Color(0, 0, 0), Color(10, 20, 30)])
        assert img.a[0, 1].tolist() == [10.0, 20.0, 30.0]

    def test_palette_clamps_out_of_range_values(self):
        img = Field([[-5.0, 5.0]]).palette(Gradient(Color(0, 0, 0), Color(255, 255, 255)))
        assert img.a[0, 0].tolist() == [0.0, 0.0, 0.0]
        assert img.a[0, 1].tolist() == [255.0, 255.0, 255.0]


# ---------------------------------------------------------------------------
# Image
# ---------------------------------------------------------------------------

class TestImageBasics:
    def test_rejects_a_non_rgb_shape(self):
        with pytest.raises(ValueError, match=r'needs shape \(h, w, 3\)'):
            Image(np.zeros((2, 2)))

    def test_zeros_and_full(self):
        assert Image.zeros((2, 3)).shape == (2, 3)
        assert Image.full((2, 3), (10, 20, 30)).a[0, 0].tolist() == [10.0, 20.0, 30.0]

    def test_gradient_keeps_all_three_channels(self):
        img = Image.gradient('y', SKY, H, W)
        assert img.shape == (H, W)
        assert img.a[0, 0].tolist() == [10.0, 20.0, 30.0]
        assert img.a[H - 1, W - 1].tolist() == [200.0, 220.0, 255.0]

    def test_gradient_is_constant_across_the_other_axis(self):
        img = Image.gradient('y', SKY, H, W)
        assert all(np.array_equal(img.a[y, 0], img.a[y, W - 1]) for y in range(H))
        imgx = Image.gradient('x', SKY, H, W)
        assert all(np.array_equal(imgx.a[0, x], imgx.a[H - 1, x]) for x in range(W))

    def test_gradient_rejects_a_bad_axis(self):
        with pytest.raises(ValueError, match="axis must be 'x' or 'y'"):
            Image.gradient('z', SKY, 2, 2)

    def test_gradient_rejects_a_zero_length(self):
        with pytest.raises(ValueError, match='at least one sample'):
            Image.gradient('y', SKY, 0, 4)

    def test_operations_return_new_images(self):
        img = Image.zeros((2, 2))
        assert img.scaled(2) is not img
        assert img.a.sum() == 0.0

    def test_multiplication_scales(self):
        assert Image.full((1, 1), (10, 20, 30)).__mul__(2).a[0, 0].tolist() == [20.0, 40.0, 60.0]
        assert (2 * Image.full((1, 1), (10, 20, 30))).a[0, 0].tolist() == [20.0, 40.0, 60.0]
        assert Image.full((1, 1), (10, 20, 30)).__truediv__(2).a[0, 0].tolist() == [5.0, 10.0, 15.0]


class TestImageCombination:
    def test_add_is_additive_light(self):
        a = Image.full((1, 1), (10, 20, 30))
        b = Image.full((1, 1), (5, 5, 5))
        assert a.add(b).a[0, 0].tolist() == [15.0, 25.0, 35.0]

    def test_add_accepts_a_field_and_a_colour(self):
        img = Image.zeros((1, 1)).add(Field([[0.5]]), Color(100, 200, 0))
        assert img.a[0, 0].tolist() == [50.0, 100.0, 0.0]

    def test_over_is_alpha_compositing(self):
        a = Image.full((1, 1), (0, 0, 0))
        b = Image.full((1, 1), (100, 100, 100))
        assert a.over(b, 0.25).a[0, 0].tolist() == [25.0, 25.0, 25.0]
        assert a.over(b, 1.0).a[0, 0].tolist() == [100.0, 100.0, 100.0]
        assert a.over(b, 0.0).a[0, 0].tolist() == [0.0, 0.0, 0.0]

    def test_over_accepts_a_per_pixel_alpha_field(self):
        a = Image.zeros((1, 2))
        b = Image.full((1, 2), (100, 100, 100))
        out = a.over(b, Field([[0.0, 1.0]]))
        assert out.a[0, 0].tolist() == [0.0, 0.0, 0.0]
        assert out.a[0, 1].tolist() == [100.0, 100.0, 100.0]

    def test_mix_and_absorb(self):
        a = Image.full((1, 1), (0, 0, 0))
        b = Image.full((1, 1), (100, 200, 40))
        assert a.mix(b, 0.5).a[0, 0].tolist() == [50.0, 100.0, 20.0]
        assert a.absorb(Color(10, 20, 30), 0.5).a[0, 0].tolist() == [5.0, 10.0, 15.0]

    def test_scaled_by_a_field(self):
        out = Image.full((1, 2), (10, 10, 10)).scaled(Field([[1.0, 0.5]]))
        assert out.a[0, 0].tolist() == [10.0, 10.0, 10.0]
        assert out.a[0, 1].tolist() == [5.0, 5.0, 5.0]

    def test_luma_is_rec709(self):
        img = Image.full((1, 1), (0, 255, 0))
        assert float(img.luma().a[0, 0]) == pytest.approx(0.7152 * 255, abs=0.01)

    def test_palette_remaps_by_luminance(self):
        img = Image.full((1, 1), (255, 255, 255))
        out = img.palette(Gradient(Color(0, 0, 0), Color(255, 0, 0)))
        assert out.a[0, 0].tolist() == [255.0, 0.0, 0.0]

    def test_posterized_needs_two_levels(self):
        with pytest.raises(ValueError, match='levels >= 2'):
            Image.zeros((1, 1)).posterized(1)

    def test_posterized_snaps_channels(self):
        img = Image.full((1, 1), (100, 100, 100))
        assert img.posterized(2).a[0, 0].tolist() == [0.0, 0.0, 0.0]


class TestImageResampling:
    def test_sample_rows_gathers_per_column(self):
        img = Image.gradient('y', SKY, H, W)
        out = img.sample_rows(np.array([H - 1] * W, dtype=np.int32))
        assert np.array_equal(out.a, img.a[:, [H - 1] * W, :])

    def test_sample_rows_handles_a_reversed_index(self):
        img = Image.gradient('y', SKY, H, W)
        out = img.sample_rows(np.arange(W, dtype=np.int32)[::-1])
        assert np.array_equal(out.a[:, 0, :], img.a[:, W - 1, :])

    def test_sample_rows_accepts_a_2d_index_field(self):
        img = Image.gradient('y', SKY, H, W)
        out = img.sample_rows(np.full((H, W), 3, dtype=np.int32))
        assert np.array_equal(out.a[5, 5], img.a[3, 5])

    def test_sample_rows_rejects_a_wrong_length(self):
        with pytest.raises(ValueError, match='rows for 12 columns'):
            Image.zeros((H, W)).sample_rows(np.zeros(3, dtype=np.int32))

    def test_sample_rows_clamps_out_of_range_indices(self):
        img = Image.gradient('y', SKY, H, W)
        out = img.sample_rows(np.array([999] * W, dtype=np.int32))
        assert np.array_equal(out.a[:, 0, :], img.a[:, H - 1, :])

    def test_displaced_with_a_zero_offset_is_the_identity(self):
        img = Image.gradient('y', SKY, H, W)
        zero = np.zeros((H, W), dtype=np.float32)
        assert np.array_equal(img.displaced(zero).a, img.a)

    def test_displaced_rejects_a_bad_mode(self):
        with pytest.raises(ValueError, match="'clamp' or 'wrap'"):
            Image.zeros((2, 2)).displaced(np.zeros((2, 2)), mode='mirror')

    def test_displaced_wrap_brings_the_far_edge_around(self):
        img = Image.gradient('x', SKY, 2, 4)
        out = img.displaced(np.full((2, 4), -3.0, dtype=np.float32), mode='wrap')
        assert out.a[0, 0].tolist() == pytest.approx(img.a[0, 1].tolist())


class TestImageGrading:
    def test_tonemapped_leaves_the_toe_alone(self):
        img = Image.full((1, 1), (100, 50, 25))
        assert img.tonemapped(knee=172.0).a[0, 0].tolist() == [100.0, 50.0, 25.0]

    def test_tonemapped_rolls_off_the_shoulder(self):
        img = Image.full((1, 1), (1000, 1000, 1000))
        out = img.tonemapped(knee=172.0).a[0, 0]
        assert 172.0 < out[0] < 255.0

    def test_bloom_only_touches_what_is_above_the_threshold(self):
        dark = Image.full((4, 4), (10, 10, 10)).bloomed(threshold=205.0)
        assert dark.a.max() == pytest.approx(10.0, abs=0.01)
        bright = Image.full((4, 4), (250, 250, 250)).bloomed(threshold=205.0)
        assert bright.a.max() > 250.0

    def test_bloom_spreads_outward_from_a_hot_spot(self):
        img = Image.zeros((9, 9))
        img = img.placed(Image.full((1, 1), (255, 255, 255)), 4, 4)
        out = img.bloomed(threshold=205.0, radius=2, intensity=0.5)
        assert out.a[4, 6, 0] > 0.0 and out.a[4, 4, 0] > out.a[4, 6, 0]

    def test_vignetted_darkens_the_corner_not_the_centre(self):
        img = Image.full((9, 9), (200, 200, 200)).vignetted(intensity=0.5)
        assert img.a[4, 4, 0] == pytest.approx(200.0, abs=0.01)
        assert img.a[0, 0, 0] < 200.0


class TestImageComposition:
    def test_stacked_requires_matching_widths(self):
        with pytest.raises(ValueError, match='width mismatch'):
            Image.zeros((2, 3)).stacked(Image.zeros((2, 4)))

    def test_stacked_concatenates_rows(self):
        out = Image.zeros((2, 3)).stacked(Image.zeros((3, 3)))
        assert out.shape == (5, 3)

    def test_placed_composites_at_an_offset(self):
        bg = Image.zeros((4, 4))
        fg = Image.full((1, 1), (100, 100, 100))
        assert bg.placed(fg, 1, 2).a[1, 2].tolist() == [100.0, 100.0, 100.0]
        assert bg.placed(fg, 1, 2).a[0, 0].tolist() == [0.0, 0.0, 0.0]

    def test_placed_clips_at_the_edges(self):
        bg = Image.zeros((2, 2))
        assert bg.placed(Image.full((5, 5), (9, 9, 9)), 1, 1).a[1, 1].tolist() == [9.0] * 3

    def test_rows_and_resized(self):
        img = Image.zeros((6, 4))
        assert img.rows(1, 3).shape == (2, 4)
        assert img.resized(3, 2).shape == (3, 2)

    def test_scattered_accumulates_duplicate_points(self):
        out = Image.zeros((1, 1)).scattered([(0, 0, 10, 0, 0), (0, 0, 5, 0, 0)])
        assert out.a[0, 0].tolist() == [15.0, 0.0, 0.0]

    def test_scattered_ignores_an_empty_list(self):
        assert Image.zeros((2, 2)).scattered([]).a.sum() == 0.0


class TestImagePost:
    """The cell-level fx that had no array equivalent."""

    def test_blurred_preserves_a_flat_image(self):
        assert float(Image.full((6, 6), (40, 80, 120)).blurred(2).a.mean()) == pytest.approx(80.0)

    def test_blurred_reduces_noise(self):
        img = Image.full((12, 12), (100, 100, 100)).add(
            Field.waves(12, 12, t=1.0).tinted(Color(90, 90, 90)))
        assert float(img.luma().a.std()) > float(img.blurred(2).luma().a.std())

    def test_blurred_below_one_is_a_copy(self):
        img = Image.full((3, 3), (10, 20, 30))
        assert img.blurred(0).a.tolist() == img.a.tolist()

    def test_kuwahara_leaves_a_flat_image_exactly_alone(self):
        for shape in [(1, 1), (1, 8), (8, 1), (2, 2), (8, 12)]:
            assert float(Image.full(shape, (100, 100, 100)).kuwahara(2).a.mean()) == \
                pytest.approx(100.0), f'flat image broke at {shape}'

    def test_kuwahara_flattens_noise_without_collapsing_the_mean(self):
        img = Image.gradient('y', SKY, 24, 40).add(
            Field.waves(24, 40, t=1.0).tinted(Color(90, 120, 200), 0.6))
        out = img.kuwahara(2)
        assert float(out.luma().a.std()) < float(img.luma().a.std()), 'must smooth'
        assert float(out.a.mean()) == pytest.approx(float(img.a.mean()), rel=0.2)

    def test_kuwahara_keeps_the_channels_independent(self):
        img = Image.gradient('y', SKY, 16, 16)
        means = img.kuwahara(2).a.mean(axis=(0, 1))
        assert means[2] - means[0] > 20, 'a blue sky must not come out grey'

    def test_kuwahara_below_one_is_a_copy(self):
        img = Image.full((4, 4), (10, 20, 30))
        assert img.kuwahara(0).a.tolist() == img.a.tolist()

    def test_scanlined_darkens_alternate_rows(self):
        img = Image.full((4, 4), (100, 100, 100))
        out = img.scanlined(0.5)
        assert float(out.a[0].mean()) == pytest.approx(100.0)
        assert float(out.a[1].mean()) == pytest.approx(50.0)
        assert float(out.a[3].mean()) == pytest.approx(50.0)

    def test_pixelated_averages_blocks(self):
        img = Image.zeros((4, 4))
        img.a[0, 0] = (100, 0, 0)
        out = img.pixelated(2)
        assert out.a[0, 0].tolist() == [25.0, 0.0, 0.0], 'one lit cell in a 2x2 block'
        assert out.a[3, 3].tolist() == [0.0, 0.0, 0.0]

    def test_pixelated_needs_a_positive_block(self):
        with pytest.raises(ValueError, match='block >= 1'):
            Image.zeros((2, 2)).pixelated(0)

    def test_pixelated_one_is_a_copy(self):
        img = Image.full((2, 2), (1, 2, 3))
        assert img.pixelated(1).a.tolist() == img.a.tolist()

    def test_chromatic_zero_is_a_copy(self):
        img = Image.gradient('x', SKY, 2, 4)
        assert img.chromatic(0).a.tolist() == img.a.tolist()

    def test_chromatic_shifts_red_and_blue_apart(self):
        img = Image.gradient('x', SKY, 1, 8)
        out = img.chromatic(2)
        assert not np.array_equal(out.a[0, 0], img.a[0, 0])

    def test_edged_darkens_a_hard_boundary(self):
        flat = Image.full((8, 8), (200, 200, 200))
        assert float(flat.edged(0.8).a.mean()) == pytest.approx(200.0, abs=0.01)
        split = Image.gradient('x', Gradient(Color(0, 0, 0), Color(255, 255, 255)), 8, 8)
        assert float(split.edged(0.8).a.mean()) < float(split.a.mean())

    def test_edged_zero_is_a_copy(self):
        img = Image.full((3, 3), (1, 2, 3))
        assert img.edged(0).a.tolist() == img.a.tolist()

    @pytest.mark.parametrize('shape', [(1, 1), (1, 8), (8, 1), (2, 2), (8, 12)])
    def test_every_post_op_survives_a_degenerate_shape(self, shape):
        img = Image.full(shape, (100, 100, 100))
        for out in (img.blurred(1), img.kuwahara(1), img.edged(0.4),
                    img.pixelated(2), img.chromatic(1), img.scanlined(0.2)):
            assert out.shape == shape


class TestFromSurface:
    def test_round_trips_a_hi_res_surface_losslessly(self):
        src = Image.gradient('y', SKY, 8, 6)
        hr = HiResCanvas(6, 8)
        src.to_cells(hr)
        back = Image.from_surface(hr)
        assert np.abs(back.a - np.round(src.a)).max() <= 1.0

    def test_reads_a_low_res_surface_from_its_background(self):
        c = Canvas(4, 3)
        Image.full((3, 4), (11, 22, 33)).to_cells(c)
        assert Image.from_surface(c).a[0, 0].tolist() == [11.0, 22.0, 33.0]

    def test_empty_cells_read_as_black(self):
        assert float(Image.from_surface(Canvas(3, 2)).a.sum()) == 0.0

    def test_survives_the_mesh_round_trip(self):
        """A 3-D pass draws into cells; the grade then sees what it drew."""
        from spore_engine.core.geom import Mat4, Vec3
        from spore_engine.render3d.engine3d import Mesh3D, render_mesh_solid
        hr = HiResCanvas(20, 16)
        Image.full((16, 20), (0, 0, 0)).to_cells(hr, z=-100)
        render_mesh_solid(hr, Mesh3D.cube(1.0), Mat4.look_at(Vec3(0, 0, 4), Vec3(0, 0, 0)),
                          Mat4.perspective(1.0, hr.w / hr.h, 0.1, 10),
                          Vec3(0, 0, 1))
        back = Image.from_surface(hr)
        assert back.a.max() > 100.0, 'the mesh must be visible in the read-back'
        assert float(back.a.mean()) > 0.0, 'the background must be there too'


# ---------------------------------------------------------------------------
# The sink
# ---------------------------------------------------------------------------

class TestToCells:
    def test_low_res_writes_the_background_with_a_blank_glyph(self):
        c = Canvas(W, H)
        Image.full((H, W), (10, 20, 30)).to_cells(c)
        cell = c.get_pixel(3, 3)
        assert cell.char == ' '
        assert cell.bg == Color(10, 20, 30)
        assert cell.fg is None

    def test_hires_writes_the_foreground_for_the_fold(self):
        hr = HiResCanvas(W, H * 2)
        Image.full((H * 2, W), (10, 20, 30)).to_cells(hr)
        cell = hr.get_pixel(3, 3)
        assert cell.fg == Color(10, 20, 30)
        assert cell.bg is None

    def test_both_sub_cells_survive_the_fold(self):
        c = Canvas(W, H)
        hr = HiResCanvas(W, H * 2)
        top = Image.gradient('y', Gradient(Color(255, 0, 0), Color(0, 0, 0)),
                             H * 2, W)
        top.to_cells(hr)
        hr.to_canvas(c)
        cell = c.get_pixel(W // 2, H // 2)
        assert cell.char == '\u2580'
        assert cell.fg.r > cell.bg.r, 'the top sub-cell must be the warmer one'

    def test_rejects_a_size_mismatch(self):
        # the message has to say the image must match exactly, not merely "fit":
        # a smaller image would leave the rest of the surface on the last frame
        with pytest.raises(ValueError, match='needs an exact match'):
            Image.zeros((2, 2)).to_cells(Canvas(3, 3))

    @pytest.mark.parametrize('shape', [(2, 3), (3, 2), (4, 3)])
    def test_neither_a_smaller_nor_a_larger_image_is_accepted(self, shape):
        with pytest.raises(ValueError, match='exact match'):
            Image.zeros(shape).to_cells(Canvas(3, 3))

    def test_the_message_names_both_sizes_height_first(self):
        with pytest.raises(ValueError, match=r'image is 2x5 .* surface is 4x7'):
            Image.zeros((2, 5)).to_cells(Canvas(7, 4))

    def test_ignores_a_degenerate_image(self):
        Image.zeros((0, 0)).to_cells(Canvas(4, 4))       # must not raise

    def test_module_level_alias_matches_the_method(self):
        c1, c2 = Canvas(W, H), Canvas(W, H)
        img = Image.full((H, W), (1, 2, 3))
        img.to_cells(c1)
        to_cells(img, c2)
        assert c1.get_pixel(0, 0).bg == c2.get_pixel(0, 0).bg

    def test_field_to_cells_greyscales(self):
        c = Canvas(W, H)
        Field.full((H, W), 0.5).to_cells(c)
        assert c.get_pixel(0, 0).bg == Color(127, 127, 127)


class TestCellCache:
    def test_matches_only_at_its_own_size(self):
        assert CellCache(4, 5).matches(4, 5)
        assert not CellCache(4, 5).matches(5, 4)
        assert not CellCache(4, 5).matches(4, 6)

    def test_rejects_a_degenerate_size(self):
        with pytest.raises(ValueError, match='positive size'):
            CellCache(0, 4)

    def test_reuses_the_colour_object_for_an_unchanged_pixel(self):
        cache = CellCache(H, W)
        c = Canvas(W, H)
        img = Image.full((H, W), (10, 20, 30))
        img.to_cells(c, cache=cache)
        first = c.get_pixel(2, 2).bg
        img.to_cells(c, cache=cache)
        assert c.get_pixel(2, 2).bg is first, 'unchanged sub-cell must keep its Color'

    def test_rebuilds_the_colour_object_when_the_pixel_moves(self):
        cache = CellCache(H, W)
        c = Canvas(W, H)
        Image.full((H, W), (10, 20, 30)).to_cells(c, cache=cache)
        first = c.get_pixel(2, 2).bg
        Image.full((H, W), (90, 20, 30)).to_cells(c, cache=cache)
        second = c.get_pixel(2, 2).bg
        assert second is not first
        assert second == Color(90, 20, 30)

    def test_never_builds_more_colours_than_the_surface_has(self):
        cache = CellCache(H, W)
        c = Canvas(W, H)
        Image.full((H, W), (1, 2, 3)).to_cells(c, cache=cache)
        assert len(cache) == H * W

    def test_a_changed_frame_rebuilds_only_what_moved(self):
        cache = CellCache(2, 2)
        c = Canvas(2, 2)
        Image.full((2, 2), (1, 1, 1)).to_cells(c, cache=cache)
        img = Image.full((2, 2), (1, 1, 1))
        img.a[0, 0] = (9, 9, 9)
        img.to_cells(c, cache=cache)
        assert c.get_pixel(0, 0).bg == Color(9, 9, 9)
        assert c.get_pixel(1, 1).bg == Color(1, 1, 1)

    def test_painting_at_the_wrong_size_is_rejected(self):
        with pytest.raises(ValueError, match='cache is 2x2'):
            CellCache(2, 2).paint(np.zeros((3, 3, 3), np.float32), Canvas(3, 3))

    def test_a_stale_cache_falls_back_to_a_plain_paint(self):
        c = Canvas(W, H)
        Image.full((H, W), (7, 8, 9)).to_cells(c, cache=CellCache(2, 2))
        assert c.get_pixel(0, 0).bg == Color(7, 8, 9)

    def test_clear_and_repr(self):
        cache = CellCache(2, 2)
        Image.full((2, 2), (1, 1, 1)).to_cells(Canvas(2, 2), cache=cache)
        assert 'CellCache' in repr(cache)
        cache.clear()
        assert len(cache) == 0


# ---------------------------------------------------------------------------
# StarField
# ---------------------------------------------------------------------------

class TestStarField:
    def test_count_and_length(self):
        assert len(StarField(count=25)) == 25
        assert len(StarField(count=0)) == 0

    def test_rejects_a_negative_count(self):
        with pytest.raises(ValueError, match='count must be >= 0'):
            StarField(count=-1)

    def test_sample_is_deterministic_for_a_seed(self):
        a = StarField(count=40, seed=7).sample(1.0, W, H)
        b = StarField(count=40, seed=7).sample(1.0, W, H)
        assert a == b

    def test_sample_stays_inside_the_surface(self):
        for x, y, *_ in StarField(count=200).sample(3.0, W, H):
            assert 0 <= x < W and 0 <= y < H

    def test_sample_scales_with_the_surface_not_a_cached_size(self):
        stars = StarField(count=200)
        for w, h in ((10, 5), (200, 100)):
            for x, y, *_ in stars.sample(1.0, w, h):
                assert 0 <= x < w and 0 <= y < h

    def test_sample_is_empty_on_a_degenerate_surface(self):
        assert StarField(count=10).sample(1.0, 0, 5) == []

    def test_twinkle_changes_over_time(self):
        stars = StarField(count=200)
        assert stars.sample(0.0, 80, 40) != stars.sample(0.7, 80, 40)

    def test_draw_adds_light_to_an_image(self):
        img = Image.zeros((H, W))
        out = StarField(count=60).draw(img, 1.0, threshold=0.0)
        assert out.a.max() > 0.0

    def test_draw_cells_writes_glyphs(self):
        c = Canvas(W, H)
        StarField(count=40).draw_cells(c, 1.0, threshold=0.0)
        assert any(c.buffer[y][x].char == '\u00b7'
                   for y in range(H) for x in range(W))

    def test_draw_cells_works_on_a_hires_surface(self):
        hr = HiResCanvas(W, H * 2)
        StarField(count=40).draw_cells(hr, 1.0, threshold=0.0)
        assert any(hr.buffer[y][x].fg is not None
                   for y in range(H * 2) for x in range(W))

    def test_repr(self):
        assert 'StarField' in repr(StarField(count=3))


# ---------------------------------------------------------------------------
# fast_color
# ---------------------------------------------------------------------------

class TestFastColor:
    def test_equals_the_validating_constructor(self):
        from spore_engine import fast_color
        assert fast_color(1, 2, 3) == Color(1, 2, 3)

    def test_is_hashable_and_usable_as_a_key(self):
        from spore_engine import fast_color
        assert {fast_color(1, 2, 3): 'x'}[Color(1, 2, 3)] == 'x'


# ---------------------------------------------------------------------------
# The pipeline the module exists for
# ---------------------------------------------------------------------------

def test_an_aurora_shaped_frame_builds_end_to_end():
    """The shape the module was added for: generate, combine, grade, sink."""
    hz = 10
    sky = Image.gradient('y', SKY, hz, W)
    sky = sky.add(Field.radial(hz, W, 8, 3, 4, power=1.4).tinted(Color(90, 255, 160)))
    sky = sky.add(StarField(count=40).draw(Image.zeros((hz, W)), 2.0, threshold=0.0))
    mirror = np.clip(hz - 1 - np.arange(W) * 0.35, 0, hz - 1).astype(np.int32)
    water = sky.sample_rows(mirror).absorb(Color(4, 12, 24), 0.35)
    frame = sky.stacked(water).tonemapped().bloomed().vignetted()
    assert frame.shape == (hz * 2, W)
    assert math.isfinite(float(frame.a.max()))

    hr = HiResCanvas(W, hz * 2)
    frame.to_cells(hr, cache=CellCache(hz * 2, W))
    c = Canvas(W, hz)
    hr.to_canvas(c)
    filled = sum(1 for y in range(c.h) for x in range(c.w)
                 if c.buffer[y][x].bg is not None or c.buffer[y][x].fg is not None)
    assert filled == W * hz, 'every cell must carry a colour'


# ---------------------------------------------------------------------------
# gains and masks: broadcast before resize
# ---------------------------------------------------------------------------

class TestBroadcastGains:
    """A per-row or per-column field is a broadcast, not something to stretch.

    Resizing an ``(h, 1)`` gain field used to interpolate that one column into a
    gradient across the width, which is never what a caller means and produced a
    wrong frame with no error. The aurora hit this on its water absorption.
    """

    H, W = 6, 10

    def base(self):
        return Image.full((self.H, self.W), (255, 255, 255))

    def test_scaled_broadcasts_a_per_row_field(self):
        col = np.array([[v] for v in (0, .25, .5, .75, 1, .5)], np.float32)
        out = self.base().scaled(col)
        assert out.a[2, :, 0] == pytest.approx(np.full(self.W, 127.5), abs=0.01)

    def test_scaled_broadcasts_a_per_column_field(self):
        row = np.linspace(0, 1, self.W, dtype=np.float32)[None, :]
        out = self.base().scaled(row)
        assert out.a[0, :, 0] == pytest.approx(np.linspace(0, 255, self.W), abs=0.01)

    def test_scaled_still_resizes_a_genuinely_different_shape(self):
        out = self.base().scaled(np.array([[0., 1.], [1., 0.]], np.float32))
        assert out.a[0, 0, 0] == pytest.approx(0.0, abs=0.01)
        assert out.a[0, self.W - 1, 0] == pytest.approx(255.0, abs=0.01)

    def test_mix_broadcasts_a_per_row_field(self):
        col = np.array([[v] for v in (0, .25, .5, .75, 1, .5)], np.float32)
        out = self.base().mix(Color(0, 0, 0), col)
        assert out.a[2, :, 0] == pytest.approx(np.full(self.W, 127.5), abs=0.01)

    def test_over_broadcasts_a_per_row_field(self):
        col = np.array([[v] for v in (0, .25, .5, .75, 1, .5)], np.float32)
        out = self.base().over(Color(0, 0, 0), col)
        assert out.a[2, :, 0] == pytest.approx(np.full(self.W, 127.5), abs=0.01)

    def test_add_broadcasts_a_per_row_field(self):
        col = np.array([[v] for v in (0, 1, 2, 3, 4, 5)], np.float32)
        out = Image.zeros((self.H, self.W)).add(col, gain=Color(10, 20, 30))
        assert out.a[2, :, 0] == pytest.approx(np.full(self.W, 20.0), abs=0.01)
        assert out.a[2, :, 2] == pytest.approx(np.full(self.W, 60.0), abs=0.01)

    def test_add_accepts_a_float_triple_as_the_tint(self):
        # a Color is 0-255; a bare triple is an absolute multiplier, the same
        # convention Field.tinted and Image.bloomed already use
        out = Image.zeros((self.H, self.W)).add(np.ones((self.H, self.W), np.float32),
                                                gain=(0.5, 0.25, 1.0))
        assert out.a[0, 0].tolist() == pytest.approx([0.5, 0.25, 1.0])

    def test_add_with_a_colour_gain_is_the_0_255_form(self):
        out = Image.zeros((self.H, self.W)).add(np.ones((self.H, self.W), np.float32),
                                                gain=Color(0, 64, 255))
        assert out.a[0, 0].tolist() == pytest.approx([0.0, 64.0, 255.0], abs=0.01)

    def test_a_colour_operand_needs_no_full_frame_temporary(self):
        # correctness, not timing: absorbing towards a colour must not change
        # the arithmetic now that it no longer builds a constant-colour frame
        lit = np.full((self.H, self.W), 0.25, np.float32)
        out = self.base().absorb(Color(0, 0, 0), lit)
        assert out.a[0, 0, 0] == pytest.approx(191.25, abs=0.01)


# ---------------------------------------------------------------------------
# the ramp LUT is cached, not rebuilt per call
# ---------------------------------------------------------------------------

class TestGradientLutCache:
    def test_the_same_gradient_returns_the_same_table(self):
        a = _gradient_lut(SKY, 256)
        b = _gradient_lut(SKY, 256)
        assert a is b

    def test_a_different_ramp_gets_its_own_table(self):
        other = Gradient(Color(1, 2, 3), Color(4, 5, 6))
        assert not np.array_equal(_gradient_lut(other, 256), _gradient_lut(SKY, 256))

    def test_a_different_length_rebuilds(self):
        assert _gradient_lut(SKY, 64).shape == (64, 3)
        assert _gradient_lut(SKY, 256).shape == (256, 3)

    def test_a_list_of_colours_is_accepted(self):
        lut = _gradient_lut([Color(0, 0, 0), Color(255, 255, 255)], 8)
        assert lut.shape == (8, 3)
        assert lut[0].tolist() == pytest.approx([0, 0, 0])
        assert lut[-1].tolist() == pytest.approx([255, 255, 255])

    def test_zero_samples_is_an_error(self):
        with pytest.raises(ValueError, match='at least one sample'):
            _gradient_lut(SKY, 0)

    def test_palette_through_a_field_uses_the_cache(self):
        f = Field(np.linspace(0, 1, 12, dtype=np.float32).reshape(3, 4))
        assert np.array_equal(f.palette(SKY).a, f.palette(SKY).a)


class TestAddDispatch:
    """``add`` dispatches on the type of ``other``, which is never ambiguous.

    It used to branch on ``gain`` instead, so ``add(field)`` - the most natural
    call there is - treated the field as a colour and raised.
    """

    def base(self):
        return Image.zeros((4, 6))

    def test_a_field_is_grey_light(self):
        f = Field(np.full((4, 6), 0.5, np.float32))
        assert self.base().add(f).a[0, 0].tolist() == pytest.approx([0.5] * 3)

    def test_a_field_with_a_scalar_gain(self):
        f = Field(np.full((4, 6), 0.5, np.float32))
        assert self.base().add(f, 2).a[0, 0].tolist() == pytest.approx([1.0] * 3)

    def test_a_field_tinted_by_a_color(self):
        f = Field(np.full((4, 6), 0.5, np.float32))
        out = self.base().add(f, gain=Color(10, 20, 30)).a[0, 0]
        assert out.tolist() == pytest.approx([5.0, 10.0, 15.0])

    def test_a_field_tinted_by_a_float_triple(self):
        f = Field(np.full((4, 6), 0.5, np.float32))
        out = self.base().add(f, gain=(1.0, 2.0, 4.0)).a[0, 0]
        assert out.tolist() == pytest.approx([0.5, 1.0, 2.0])

    def test_a_bare_ndarray_is_a_field(self):
        f = np.full((4, 6), 0.5, np.float32)
        assert self.base().add(f).a[0, 0].tolist() == pytest.approx([0.5] * 3)

    def test_a_colour_is_broadcast(self):
        assert self.base().add(Color(5, 6, 7)).a[0, 0].tolist() == pytest.approx([5, 6, 7])

    def test_a_colour_with_a_scalar_gain(self):
        out = self.base().add(Color(5, 6, 7), 2).a[0, 0]
        assert out.tolist() == pytest.approx([10, 12, 14])

    def test_an_image_is_scaled_by_gain(self):
        other = Image.full((4, 6), (1, 2, 3))
        assert self.base().add(other, 2).a[0, 0].tolist() == pytest.approx([2, 4, 6])

    def test_a_one_d_array_is_one_value_per_column(self):
        out = self.base().add(np.full(6, 0.25, np.float32),
                              gain=Color(4, 0, 0)).a
        assert out[:, 0, 0].tolist() == pytest.approx([1.0] * 4)

    def test_add_is_additive_not_overwriting(self):
        a = Image.full((4, 6), (10, 10, 10))
        assert a.add(Color(1, 2, 3)).a[0, 0].tolist() == pytest.approx([11, 12, 13])

    def test_add_does_not_mutate_either_operand(self):
        a = Image.full((4, 6), (10, 10, 10))
        b = Image.full((4, 6), (1, 1, 1))
        a.add(b)
        assert a.a[0, 0].tolist() == [10, 10, 10]
        assert b.a[0, 0].tolist() == [1, 1, 1]

    def test_every_form_agrees_with_hand_arithmetic(self):
        f = np.full((4, 6), 0.5, np.float32)
        assert self.base().add(f, gain=Color(2, 4, 6)).a[0, 0].tolist() == \
            pytest.approx((0.5 * 2, 0.5 * 4, 0.5 * 6))
