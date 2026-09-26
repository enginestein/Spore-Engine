"""The additions that let one camera drive every 3-D backend.

Three gaps, all found by trying to make two renderers share a view:

* ``Mat4.transform`` divided by w and threw it away. A rasterizer cannot
  interpolate depth correctly across a triangle without the per-vertex w, and a
  raytracer cannot generate a ray from a projection at all.
* There was no ``transform_vector``, so ``engine3d`` hand-extracted its view
  direction out of ``view_mat[2, 0..2]`` and lighting a rotated model had no
  way to move a normal.
* There was no orthographic projection, so isometric and technical views had
  to fake one with a very narrow fov.

``Camera3D`` then replaces four different camera conventions - matrices, bare
tuples in degrees, ``Vec3`` in degrees, and eight scalars in radians - with
one value object.
"""

from __future__ import annotations

import math

import pytest

from spore_engine import Canvas, Camera3D, Color, HiResCanvas, Mat4, Mesh3D, Vec3
from spore_engine.render3d.engine3d import render_mesh_solid

SURFACE_W, SURFACE_H = 40, 30


class TestTransform4:
    def test_returns_the_undivided_components(self):
        m = Mat4.perspective(1.0, 1.0, 0.1, 100)
        x, y, z, w = m.transform4(Vec3(0, 0, -5))
        assert w == pytest.approx(5.0)
        assert z == pytest.approx(4.8098, abs=1e-3), 'clip-space z, not view z'
        assert z != pytest.approx(m.transform(Vec3(0, 0, -5)).z), \
            'the point of transform4 is that z is still undivided'

    def test_agrees_with_transform_once_divided(self):
        m = Mat4.look_at(Vec3(0, 2, 6), Vec3(0, 0, 0))
        for v in (Vec3(0, 0, 0), Vec3(1, -1, 0.5), Vec3(-3, 2, 1)):
            x, y, z, w = m.transform4(v)
            assert (x / w, y / w, z / w) == pytest.approx(
                (m.transform(v).x, m.transform(v).y, m.transform(v).z))

    def test_identity_keeps_w_at_one(self):
        assert Mat4().transform4(Vec3(1, 2, 3)) == (1.0, 2.0, 3.0, 1.0)

    def test_w_grows_with_distance_under_a_projection(self):
        """A look_at view is affine - w stays 1. The perspective w is in
        proj * view, which is the matrix a raytracer or rasterizer holds."""
        assert Mat4.look_at(Vec3(0, 0, 4), Vec3(0, 0, 0)).transform4(Vec3(0, 0, 0))[3] == 1.0
        m = (Mat4.perspective(1.0, 1.0, 0.1, 100)
             * Mat4.look_at(Vec3(0, 0, 4), Vec3(0, 0, 0)))
        near, far = m.transform4(Vec3(0, 0, 0)), m.transform4(Vec3(0, 0, -3))
        assert far[3] > near[3], 'a point further away has a larger w'


class TestTransformVector:
    def test_ignores_translation(self):
        assert Mat4.translate(10, 20, 30).transform_vector(Vec3(1, 0, 0)) == Vec3(1, 0, 0)

    def test_applies_rotation(self):
        m = Mat4.rotate_z(math.pi / 2)
        got = m.transform_vector(Vec3(1, 0, 0))
        assert got.x == pytest.approx(0.0, abs=1e-9)
        assert got.y == pytest.approx(1.0)

    def test_applies_scale(self):
        assert Mat4.scale(2, 3, 4).transform_vector(Vec3(1, 1, 1)) == Vec3(2, 3, 4)

    def test_a_position_and_a_direction_differ_by_translation(self):
        m = Mat4.translate(5, 0, 0) * Mat4.rotate_y(math.pi / 2)
        p = m.transform(Vec3(1, 0, 0))
        d = m.transform_vector(Vec3(1, 0, 0))
        assert p.length() != pytest.approx(d.length())


class TestNormalMatrix:
    def test_is_the_identity_for_a_rigid_transform(self):
        m = Mat4.translate(3, 4, 5) * Mat4.rotate_y(0.7)
        for ch in range(9):
            i, j = divmod(ch, 3)          # the 3x3 block, not a flat Mat4 index
            assert m.normal_matrix()[i, j] == pytest.approx(m[i, j])

    def test_corrects_a_non_uniform_scale(self):
        """A normal under a non-uniform scale is not the scaled direction."""
        sy = 3.0
        n = Vec3(0, 1, 0)
        plain = Mat4.scale(1, sy, 1).transform_vector(n)
        proper = Mat4.scale(1, sy, 1).normal_matrix().transform_vector(n)
        assert plain.length() == pytest.approx(sy), 'a direction just gets scaled'
        p = proper.norm()
        assert (p.x, p.y, p.z) == pytest.approx((0, 1, 0), abs=1e-9), \
            'the normal matrix keeps a plane normal perpendicular to the plane'

    def test_singular_input_falls_back_to_identity(self):
        assert Mat4.scale(0, 0, 0).normal_matrix() == Mat4()

    def test_stays_perpendicular_to_the_surface(self):
        """A tilted plane's normal must stay perpendicular after transforming."""
        m = Mat4.rotate_x(0.6) * Mat4.rotate_y(0.3) * Mat4.scale(1, 4, 2)
        plane_n = Vec3(0, 0, 1)
        plane_t = Vec3(1, 0, 0)
        n = m.normal_matrix().transform_vector(plane_n).norm()
        t = m.transform_vector(plane_t).norm()
        assert n.dot(t) == pytest.approx(0.0, abs=1e-9)


class TestOrthographic:
    def test_maps_the_box_onto_the_unit_cube(self):
        m = Mat4.orthographic(-2, 2, 1, -1, 1, 11)   # top above bottom
        for x, y in ((-2, -1), (2, 1), (0, 0)):
            p = m.transform(Vec3(x, y, -1))
            assert (p.x, p.y) == pytest.approx((x / 2, y))

    def test_depth_is_linear_in_distance(self):
        m = Mat4.orthographic(-1, 1, -1, 1, 1, 11)
        near = m.transform(Vec3(0, 0, -1)).z
        far = m.transform(Vec3(0, 0, -11)).z
        assert (near, far) == pytest.approx((-1.0, 1.0)), 'near->-1, far->+1'
        mid = m.transform(Vec3(0, 0, -6)).z   # midway between near=1 and far=11
        assert mid == pytest.approx(0.0, abs=1e-9), 'and halfway is halfway'

    def test_rejects_a_degenerate_box(self):
        with pytest.raises(ValueError, match='non-degenerate box'):
            Mat4.orthographic(1, 1, 0, 1, 1, 2)

    def test_rejects_equal_planes(self):
        with pytest.raises(ValueError, match='near != far'):
            Mat4.orthographic(-1, 1, -1, 1, 5, 5)


class TestCellDepth:
    """Perspective depth, kept out of the painter's-order ``z``."""

    def test_starts_unset(self):
        assert Canvas(3, 2).get_pixel(0, 0).depth == float('inf')

    def test_nearer_wins_regardless_of_z(self):
        c = Canvas(4, 3)
        c.set_pixel_depth(1, 1, 0.8, '#', Color(255, 0, 0), z=5)
        c.set_pixel_depth(1, 1, 0.2, '@', Color(0, 255, 0), z=99)
        cell = c.get_pixel(1, 1)
        assert cell.char == '@' and cell.fg == Color(0, 255, 0)
        assert cell.depth == pytest.approx(0.2)
        assert cell.z == 99, 'z is recorded, not used as the depth test'

    def test_farther_is_rejected(self):
        c = Canvas(4, 3)
        c.set_pixel_depth(1, 1, 0.2, '@')
        c.set_pixel_depth(1, 1, 0.9, 'X')
        assert c.get_pixel(1, 1).char == '@'

    def test_equal_depth_overwrites(self):
        c = Canvas(4, 3)
        c.set_pixel_depth(1, 1, 0.5, 'a')
        c.set_pixel_depth(1, 1, 0.5, 'b')
        assert c.get_pixel(1, 1).char == 'b'

    def test_out_of_bounds_is_a_noop(self):
        c = Canvas(4, 3)
        c.set_pixel_depth(-1, 0, 0.1)
        c.set_pixel_depth(0, 99, 0.1)
        assert c.get_pixel(0, 0).depth == float('inf')

    def test_hires_surface_has_the_same_rule(self):
        hr = HiResCanvas(4, 3)
        hr.set_pixel_depth(1, 1, 0.8, '@', Color(1, 2, 3), z=5)
        hr.set_pixel_depth(1, 1, 0.2, '.', Color(4, 5, 6), z=99)
        assert hr.buffer[1][1].char == '.'
        assert hr.buffer[1][1].depth == pytest.approx(0.2)

    def test_clear_resets_depth(self):
        c = Canvas(3, 2)
        c.set_pixel_depth(0, 0, 0.1)
        c.clear()
        assert c.get_pixel(0, 0).depth == float('inf')

    def test_copy_and_resize_carry_depth(self):
        c = Canvas(4, 3)
        c.set_pixel_depth(1, 1, 0.3)
        assert c.copy().get_pixel(1, 1).depth == pytest.approx(0.3)
        hr = HiResCanvas(4, 3)
        hr.set_pixel_depth(1, 1, 0.3)
        assert hr.copy().buffer[1][1].depth == pytest.approx(0.3)
        c.resize(6, 4)
        assert c.get_pixel(1, 1).depth == pytest.approx(0.3)

    def test_depth_is_not_part_of_equality(self):
        """The incremental diff keys on glyph and colour; depth must not make
        two visually identical cells compare unequal."""
        a, b = Canvas(3, 2), Canvas(3, 2)
        a.set_pixel_depth(0, 0, 0.1)
        b.set_pixel_depth(0, 0, 0.9)
        assert a.get_pixel(0, 0) == b.get_pixel(0, 0)

    def test_set_pixel_z_still_orders_by_z(self):
        c = Canvas(4, 3)
        c.set_pixel(1, 1, 'a', z=5)
        c.set_pixel(1, 1, 'b', z=1)
        assert c.get_pixel(1, 1).char == 'a'


class TestCamera3D:
    def test_view_matches_look_at(self):
        cam = Camera3D.look_at((0, 2, 6), (0, 0, 0), fov=60)
        assert cam.view == Mat4.look_at(Vec3(0, 2, 6), Vec3(0, 0, 0))

    def test_projection_uses_the_surface_aspect(self):
        hr = HiResCanvas(SURFACE_W, SURFACE_H * 2)
        cam = Camera3D.look_at((0, 0, 5), (0, 0, 0), fov=60, surface=hr)
        assert cam.projection == Mat4.perspective(
            math.radians(60), SURFACE_W / (SURFACE_H * 2), 0.1, 100.0)

    def test_without_a_surface_the_aspect_is_one(self):
        cam = Camera3D.look_at((0, 0, 5), (0, 0, 0), fov=60)
        assert cam.projection == Mat4.perspective(math.radians(60), 1.0, 0.1, 100.0)

    def test_fov_is_degrees_and_converts_once(self):
        cam = Camera3D.look_at((0, 0, 5), (0, 0, 0), fov=90)
        assert cam.fov == 90.0
        assert cam.fov_radians == pytest.approx(math.pi / 2)
        assert cam.fov_degrees() == 90.0

    def test_accepts_tuples_and_vec3_alike(self):
        a = Camera3D.look_at((1, 2, 3), (0, 0, 0), fov=60)
        b = Camera3D.look_at(Vec3(1, 2, 3), Vec3(0, 0, 0), fov=60)
        assert a == b

    def test_eye_and_target_are_plain_tuples(self):
        eye, target = Camera3D.look_at((1, 2, 3), (0, 0, 0)).eye_and_target()
        assert eye == (1.0, 2.0, 3.0) and target == (0.0, 0.0, 0.0)

    def test_basis_is_orthonormal_and_unit(self):
        right, up, forward = Camera3D.look_at((4, 3, 6), (0, 0, 0)).basis()
        for v in (right, up, forward):
            assert v.length() == pytest.approx(1.0)
        assert right.dot(up) == pytest.approx(0.0, abs=1e-9)
        assert right.dot(forward) == pytest.approx(0.0, abs=1e-9)
        assert up.dot(forward) == pytest.approx(0.0, abs=1e-9)

    def test_forward_points_at_the_target(self):
        f = Camera3D.look_at((0, 0, 5), (0, 0, -5)).view_forward()
        assert (f.x, f.y, f.z) == pytest.approx((0, 0, -1))

    def test_forward_survives_a_roll(self):
        cam = Camera3D.look_at((0, 0, 5), (0, 0, 0), up=(1, 0, 0))
        assert cam.view_forward().length() == pytest.approx(1.0)

    def test_forward_falls_back_when_eye_equals_target(self):
        cam = Camera3D.look_at((1, 1, 1), (1, 1, 1))
        assert cam.view_forward() == Vec3(0, 0, -1)

    def test_orbiting_keeps_its_distance(self):
        cam = Camera3D.orbiting((0, 0, 0), 8, 30, 25)
        assert (cam.eye - cam.target).length() == pytest.approx(8.0)

    def test_orbiting_moves_as_the_angle_changes(self):
        a = Camera3D.orbiting((0, 0, 0), 8, 0)
        b = Camera3D.orbiting((0, 0, 0), 8, 90)
        assert a.eye != b.eye

    def test_orthographic_uses_the_given_height(self):
        hr = HiResCanvas(SURFACE_W, SURFACE_H)
        cam = Camera3D.look_at((0, 5, 5), (0, 0, 0), surface=hr, ortho=True,
                              ortho_height=6)
        assert cam.ortho
        assert cam.projection == Mat4.orthographic(-4, 4, 3, -3, 0.1, 100.0)

    def test_from_matrices_round_trips_the_eye(self):
        cam = Camera3D.look_at((1, 2, 6), (0, 0, 0), fov=45)
        back = Camera3D.from_matrices(cam.view, cam.projection, 45)
        assert (back.eye.x, back.eye.y, back.eye.z) == pytest.approx((1, 2, 6), abs=1e-9)
        assert back.view == cam.view and back.projection == cam.projection

    def test_drives_the_mesh_rasterizer(self):
        hr = HiResCanvas(SURFACE_W, SURFACE_H * 2)
        cam = Camera3D.look_at((0, 1.5, 6), (0, 0, 0), fov=60, surface=hr)
        render_mesh_solid(hr, Mesh3D.cube(1.2), cam.view, cam.projection, Vec3(0, 0, -1))
        assert any(hr.buffer[y][x].fg is not None
                   for y in range(hr.h) for x in range(hr.w))

    def test_aspect_for_reads_either_surface_type(self):
        cam = Camera3D.look_at((0, 0, 1), (0, 0, 0))
        assert cam.aspect_for(Canvas(80, 20)) == 4.0
        assert cam.aspect_for(HiResCanvas(80, 40)) == 2.0, 'sub-cells, not cells'

    def test_rejects_a_bad_fov(self):
        with pytest.raises(ValueError, match=r'fov must be in \(0, 180\)'):
            Camera3D.look_at((0, 0, 1), (0, 0, 0), fov=200)

    def test_rejects_bad_planes(self):
        with pytest.raises(ValueError, match=r'0 < near < far'):
            Camera3D.look_at((0, 0, 1), (0, 0, 0), near=5, far=1)

    def test_rejects_an_orthographic_camera_with_no_height(self):
        with pytest.raises(ValueError, match='needs ortho_height'):
            Camera3D.look_at((0, 0, 1), (0, 0, 0), ortho=True)

    def test_rejects_a_non_positive_ortho_height(self):
        with pytest.raises(ValueError, match='ortho_height must be positive'):
            Camera3D.look_at((0, 0, 1), (0, 0, 0), ortho=True, ortho_height=0)

    def test_equality_and_repr(self):
        cam = Camera3D.look_at((0, 0, 5), (0, 0, 0), fov=60)
        assert cam == Camera3D.look_at((0, 0, 5), (0, 0, 0), fov=60)
        assert cam != Camera3D.look_at((0, 0, 6), (0, 0, 0), fov=60)
        assert (cam != 'not a camera') is True
        assert 'Camera3D' in repr(cam) and '60' in repr(cam)
