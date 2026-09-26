"""``Mesh3D`` primitives and the rasterizer that consumes them.

These exist because of a bug they would have caught immediately:
``Mesh3D.cube`` listed its last two faces with vertices from both z planes,
which made them duplicates of the y faces, and wound both x faces inside-out.
The box therefore had no +-z normal at all, so ``render_mesh_solid`` - which
culls on ``normal . view_dir >= 0`` - drew *nothing* when the cube faced the
camera. ``scene_3d`` rotates the cube every frame, so some face always passed
the cull and the demo looked fine.

The invariant worth locking down is "every face normal points away from the
centroid", which is what both the cull and the lighting depend on.
"""

from __future__ import annotations


import pytest

from spore_engine import Color, HiResCanvas, Mat4, Vec3
from spore_engine.render3d.engine3d import Mesh3D, render_mesh_solid


def _centroid(verts) -> Vec3:
    n = len(verts)
    return Vec3(sum(v.x for v in verts) / n, sum(v.y for v in verts) / n,
                sum(v.z for v in verts) / n)


def _outward_faces(mesh: Mesh3D) -> list[bool]:
    """Per face: does its normal point away from the mesh centroid?"""
    centre = _centroid(mesh.verts)
    return [mesh.face_normal(fi).dot(_centroid([mesh.verts[i] for i in f]) - centre) > 0
            for fi, f in enumerate(mesh.faces)]


class TestCube:
    def test_has_eight_verts_and_six_quad_faces(self):
        cube = Mesh3D.cube(1.0)
        assert len(cube.verts) == 8
        assert len(cube.faces) == 6
        assert all(len(f) == 4 for f in cube.faces)

    def test_every_face_is_a_distinct_plane(self):
        cube = Mesh3D.cube(1.0)
        assert len({tuple(sorted(f)) for f in cube.faces}) == 6

    def test_every_face_has_an_outward_normal(self):
        cube = Mesh3D.cube(1.0)
        assert all(_outward_faces(cube)), \
            'a face wound inside-out is culled when it should be drawn'

    def test_normals_cover_all_six_axis_directions(self):
        cube = Mesh3D.cube(1.0)
        seen = {tuple(round(c) for c in (n.x, n.y, n.z))
                for n in (cube.face_normal(i) for i in range(6))}
        assert seen == {(1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0),
                        (0, 0, 1), (0, 0, -1)}

    def test_size_scales_the_verts(self):
        assert max(abs(v.x) for v in Mesh3D.cube(4.0).verts) == pytest.approx(2.0)
        assert max(abs(v.x) for v in Mesh3D.cube(1.0).verts) == pytest.approx(0.5)

    def test_edges_reference_real_verts(self):
        cube = Mesh3D.cube(1.0)
        assert all(0 <= a < 8 and 0 <= b < 8 for a, b in cube.edges)

    def test_has_a_colour_per_face(self):
        assert len(Mesh3D.cube(1.0).face_colors) == 6

    def test_face_normal_survives_a_degenerate_face(self):
        cube = Mesh3D.cube(1.0)
        cube.faces.append([0, 1])
        assert cube.face_normal(len(cube.faces) - 1) == Vec3(0, 1, 0)


class TestOtherPrimitives:
    @pytest.mark.parametrize('make', [
        lambda: Mesh3D.cube(1.0),
        lambda: Mesh3D.sphere(1.0, 6, 8),
        lambda: Mesh3D.torus(1.5, 0.5, 8, 6),
        lambda: Mesh3D.icosphere(1.0, 1),
        lambda: Mesh3D.pyramid(1.0),
    ])
    def test_primitives_produce_usable_meshes(self, make):
        mesh = make()
        assert mesh.verts and mesh.faces
        assert all(len(f) >= 3 for f in mesh.faces)
        assert all(0 <= i < len(mesh.verts) for f in mesh.faces for i in f)

    def test_sphere_verts_sit_on_the_radius(self):
        for v in Mesh3D.sphere(2.0, 6, 8).verts:
            assert v.length() == pytest.approx(2.0, abs=1e-6)

    def test_icosphere_verts_sit_on_the_radius(self):
        for v in Mesh3D.icosphere(3.0, 1).verts:
            assert v.length() == pytest.approx(3.0, abs=1e-6)

    def test_norm_normalises_rather_than_measuring(self):
        """``Vec3.norm()`` divides; ``length()`` measures. Easy to confuse."""
        assert Vec3(3, 0, 4).norm().length() == pytest.approx(1.0)
        assert Vec3(3, 0, 4).length() == pytest.approx(5.0)

    def test_transform_returns_a_new_mesh(self):
        mesh = Mesh3D.cube(1.0)
        moved = mesh.transform(Mat4.translate(10, 0, 0))
        assert moved is not mesh
        assert max(v.x for v in moved.verts) == pytest.approx(10.5)


class TestRenderMeshSolid:
    @staticmethod
    def _lit(eye: Vec3) -> int:
        hr = HiResCanvas(20, 16)
        render_mesh_solid(hr, Mesh3D.cube(1.0), Mat4.look_at(eye, Vec3(0, 0, 0)),
                          Mat4.perspective(1.0, hr.w / hr.h, 0.1, 10), Vec3(0, 0, -1))
        return sum(1 for y in range(hr.h) for x in range(hr.w)
                   if hr.buffer[y][x].fg is not None)

    @pytest.mark.parametrize('eye,label', [
        (Vec3(0, 0, 4), 'down -z'), (Vec3(4, 0, 0), 'down -x'), (Vec3(0, 4, 0), 'down -y'),
    ])
    def test_a_face_on_cube_renders_from_every_axis(self, eye, label):
        """The regression: a cube with no +-z normal drew nothing here."""
        assert self._lit(eye) > 0, f'cube rendered empty viewed {label}'

    def test_respects_an_existing_background_depth(self):
        hr = HiResCanvas(20, 16)
        for y in range(hr.h):
            for x in range(hr.w):
                hr.buffer[y][x].fg = Color(9, 9, 9)
                hr.buffer[y][x].z = -100
        render_mesh_solid(hr, Mesh3D.cube(1.0), Mat4.look_at(Vec3(0, 0, 4), Vec3(0, 0, 0)),
                          Mat4.perspective(1.0, hr.w / hr.h, 0.1, 10), Vec3(0, 0, -1))
        assert any(hr.buffer[y][x].z >= 0
                   for y in range(hr.h) for x in range(hr.w)), \
            'the mesh must draw above a background layer'

    def test_light_direction_changes_the_shading(self):
        shades = []
        for light in (Vec3(0, 0, 1), Vec3(0, -1, 0)):
            hr = HiResCanvas(20, 16)
            render_mesh_solid(hr, Mesh3D.cube(1.0),
                              Mat4.look_at(Vec3(0, 0, 4), Vec3(0, 0, 0)),
                              Mat4.perspective(1.0, hr.w / hr.h, 0.1, 10), light)
            lit = [hr.buffer[y][x].fg for y in range(hr.h) for x in range(hr.w)
                   if hr.buffer[y][x].fg is not None]
            shades.append(sum(c.luminance for c in lit) / len(lit))
        assert shades[0] != shades[1]

    def test_geometry_aimed_off_screen_draws_less_than_geometry_aimed_at_it(self):
        """Off-screen geometry is clipped to the surface, not wrapped onto it.

        Aiming at a target far off to the side projects the cube past the edge,
        so the rasterizer clamps the span and paints only what is left - fewer
        cells than the same cube aimed at the centre.
        """
        def lit(target) -> int:
            hr = HiResCanvas(20, 16)
            render_mesh_solid(hr, Mesh3D.cube(1.0),
                              Mat4.look_at(Vec3(0, 0, 4), target),
                              Mat4.perspective(1.0, hr.w / hr.h, 0.1, 10), Vec3(0, 0, 1))
            return sum(1 for y in range(hr.h) for x in range(hr.w)
                       if hr.buffer[y][x].fg is not None)

        assert lit(Vec3(3, 0, 0)) < lit(Vec3(0, 0, 0))

    def test_a_mesh_partly_off_screen_draws_the_visible_part(self):
        hr = HiResCanvas(20, 16)
        render_mesh_solid(hr, Mesh3D.cube(1.0),
                          Mat4.look_at(Vec3(0, 0, 3), Vec3(1.2, 0, 0)),
                          Mat4.perspective(1.0, hr.w / hr.h, 0.1, 10), Vec3(0, 0, -1))
        assert any(hr.buffer[y][x].fg is not None
                   for y in range(hr.h) for x in range(hr.w))

    def test_a_mesh_behind_the_camera_does_not_hang(self):
        hr = HiResCanvas(20, 16)
        render_mesh_solid(hr, Mesh3D.cube(1.0), Mat4.look_at(Vec3(0, 0, 4), Vec3(0, 0, 0)),
                          Mat4.perspective(1.0, hr.w / hr.h, 0.1, 10), Vec3(0, 0, -1))
        before = sum(1 for y in range(hr.h) for x in range(hr.w)
                     if hr.buffer[y][x].fg is not None)
        render_mesh_solid(hr, Mesh3D.cube(1.0).transform(Mat4.translate(0, 0, -100)),
                          Mat4.look_at(Vec3(0, 0, 4), Vec3(0, 0, 0)),
                          Mat4.perspective(1.0, hr.w / hr.h, 0.1, 10), Vec3(0, 0, -1))
        after = sum(1 for y in range(hr.h) for x in range(hr.w)
                    if hr.buffer[y][x].fg is not None)
        assert after == before, 'a behind-camera mesh must not paint over anything'
