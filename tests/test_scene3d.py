"""Tests for the retained 3-D scene: the common currency between backends."""

import json
import math
import os
import tempfile

import pytest

from spore_engine import (Camera3D, Canvas, Color, DrawCall, Entity3D, FuncRenderer,
                          HiResCanvas, Light3D, Material, Mat4, Mesh3D, MeshRenderer,
                          Renderer, Scene3D, Vec3)
from spore_engine.render3d.scene3d import _color, _fill, _reject_material, _vec


def scene_with_orb() -> Scene3D:
    scene = Scene3D('room', ambient=Color(20, 24, 40), background=Color(6, 8, 18))
    scene.camera = Camera3D.look_at((0, 3, 10), (0, 0, 0), fov=55)
    scene.add(Light3D.directional((0.4, -1, 0.3), intensity=1.0))
    scene.add(Entity3D.box('floor', (0, -1, 0), (12, 0.4, 12),
                           Material(Color(70, 80, 100))))
    scene.add(Entity3D.sphere('orb', (0, 1.4, 0), 1.6,
                              material=Material(Color(80, 200, 255), specular=0.9)))
    return scene


def unlit_scene() -> Scene3D:
    scene = Scene3D('bare')
    scene.add(Entity3D.box('b', (0, 0, 0), material=Material(Color(1, 2, 3))))
    return scene


# ---------------------------------------------------------------------------
# exports
# ---------------------------------------------------------------------------

def test_public_names_are_exported():
    import spore_engine
    for name in ('Scene3D', 'Entity3D', 'Material', 'Light3D', 'DrawCall',
                 'Renderer', 'MeshRenderer', 'FuncRenderer'):
        assert getattr(spore_engine, name, None) is not None, name
        assert getattr(spore_engine.render3d, name) is getattr(spore_engine, name)


# ---------------------------------------------------------------------------
# Material
# ---------------------------------------------------------------------------

class TestMaterial:
    def test_defaults(self):
        m = Material()
        assert m.color == Color(200, 200, 200)
        assert m.ambient == pytest.approx(0.15)
        assert m.specular == 0.0
        assert m.emissive == 0.0

    def test_color_accepts_tuple_and_color(self):
        assert Material(Color(1, 2, 3)).color == Color(1, 2, 3)
        assert Material((1, 2, 3)).color == Color(1, 2, 3)

    def test_ambient_keeps_colour_visible(self):
        lit = Material(Color(100, 100, 100), ambient=1.0).shade(
            Vec3(0, 0, 1), Vec3(0, 0, -1), [])
        assert lit.r >= 100

    def test_an_unlit_surface_is_the_ambient_term_alone(self):
        dark = Material(Color(100, 100, 100), ambient=0.0).shade(
            Vec3(0, 0, 1), Vec3(0, 0, -1), [])
        assert dark.r < 20

    def test_a_light_raises_the_channel(self):
        m = Material(Color(200, 200, 200), ambient=0.0, specular=0.0)
        lights = [Light3D.directional((0, 0, -1), color=Color(255, 255, 255),
                                      intensity=0.5)]
        assert m.shade(Vec3(0, 0, 1), Vec3(0, 0, -1), []).r == 0
        assert m.shade(Vec3(0, 0, 1), Vec3(0, 0, -1), lights).r == 100

    def test_channels_are_clamped(self):
        m = Material(Color(200, 200, 200), ambient=0.0, specular=4.0)
        lit = m.shade(Vec3(0, 0, 1), Vec3(0, 0, -1),
                      [Light3D.directional((0, 0, -1), intensity=50.0)])
        assert all(0 <= v <= 255 for v in (lit.r, lit.g, lit.b))

    def test_emissive_ignores_lighting(self):
        args = (Vec3(0, 0, 1), Vec3(0, 0, -1), [])
        on = Material(Color(10, 10, 10), ambient=0.0, emissive=1.0).shade(*args)
        off = Material(Color(10, 10, 10), ambient=0.0, emissive=0.0).shade(*args)
        assert on.r > off.r

    def test_specular_needs_a_view_in_the_reflection(self):
        m = Material(Color(0, 0, 0), ambient=0.0, specular=1.0, shininess=64.0)
        facing = m.shade(Vec3(0, 0, 1), Vec3(0, 0, -1),
                         [Light3D.directional((0, 0, -1), intensity=1.0)])
        behind = m.shade(Vec3(0, 0, 1), Vec3(0, 0, -1),
                         [Light3D.directional((0, 0, 1), intensity=1.0)])
        assert facing.r > behind.r

    def test_a_point_light_attenuates_by_the_shaded_point(self):
        m = Material(Color(255, 255, 255), ambient=0.0, specular=0.0)
        light = Light3D.point((0, 0, 10), intensity=1.0, radius=20.0)
        close = m.shade(Vec3(0, 0, 1), Vec3(0, 0, -1), [light], Vec3(0, 0, 9))
        distant = m.shade(Vec3(0, 0, 1), Vec3(0, 0, -1), [light], Vec3(0, 0, 1))
        assert close.r > distant.r > 0

    def test_round_trip(self):
        m = Material(Color(3, 5, 7), ambient=0.3, specular=0.5, shininess=8.0,
                     emissive=0.2)
        assert Material.from_dict(m.to_dict()).to_dict() == m.to_dict()


# ---------------------------------------------------------------------------
# Light3D
# ---------------------------------------------------------------------------

class TestLight3D:
    def test_directional_is_the_default(self):
        light = Light3D()
        assert light.kind == 'directional'
        assert light.direction == Vec3(0, -1, 0)
        assert light.name == 'light'

    def test_a_light_can_be_named(self):
        assert Light3D.directional((0, -1, 0), name='sun').name == 'sun'

    def test_point_light_carries_a_position(self):
        light = Light3D.point((1, 2, 3), radius=4.0)
        assert light.kind == 'point'
        assert light.position == Vec3(1, 2, 3)
        assert light.radius == 4.0

    def test_negative_intensity_is_rejected(self):
        with pytest.raises(ValueError, match='intensity'):
            Light3D(intensity=-1.0)

    def test_the_default_sun_lights_an_up_facing_surface(self):
        # (0, -1, 0) travels downwards, so it must light a normal of (0, 1, 0)
        _, _, strength = Light3D.directional((0, -1, 0)).contribution(Vec3(0, 1, 0))
        assert strength == pytest.approx(1.0)

    def test_contribution_reports_the_way_back_to_the_light(self):
        towards, _, _ = Light3D.directional((0, -4, 0)).contribution(Vec3(0, 1, 0))
        assert (towards.x, towards.y, towards.z) == pytest.approx((0, 1, 0), abs=1e-9)

    def test_the_reported_direction_is_normalised(self):
        towards, color, strength = Light3D.directional(
            (0, -4, 0), color=Color(255, 0, 0), intensity=1.0).contribution(
                Vec3(0, 1, 0))
        assert towards.length() == pytest.approx(1.0)
        assert color == Color(255, 0, 0)
        assert strength == pytest.approx(1.0)

    def test_a_back_facing_normal_gets_nothing(self):
        _, _, strength = Light3D.directional((0, -1, 0)).contribution(Vec3(0, -1, 0))
        assert strength == 0.0

    def test_a_zero_direction_does_not_divide_by_zero(self):
        _, _, strength = Light3D.directional((0, 0, 0)).contribution(Vec3(0, 1, 0))
        assert strength == 0.0

    def test_a_point_light_aims_at_the_shaded_point(self):
        light = Light3D.point((0, 5, 0))
        towards, _, _ = light.contribution(Vec3(0, 0, 1), at=Vec3(0, 0, 0))
        assert towards.y == pytest.approx(1.0)

    def test_a_point_light_falls_off_within_its_radius(self):
        light = Light3D.point((0, 5, 0), radius=2.0)
        near = light.contribution(Vec3(0, 1, 0), at=Vec3(0, 4, 0))[2]
        far = light.contribution(Vec3(0, 1, 0), at=Vec3(0, 1, 0))[2]
        assert near > far >= 0.0

    def test_a_point_light_beyond_its_radius_is_dark(self):
        light = Light3D.point((0, 5, 0), radius=1.0)
        assert light.contribution(Vec3(0, 0, 1), at=Vec3(0, 0, 0))[2] == 0.0

    def test_a_light_sitting_on_the_surface_is_dark_not_a_crash(self):
        light = Light3D.point((0, 0, 0))
        assert light.contribution(Vec3(0, 0, 1), at=Vec3(0, 0, 0))[2] == 0.0

    def test_intensity_scales_the_result(self):
        normal = Vec3(0, 1, 0)
        weak = Light3D.directional((0, -1, 0), intensity=0.25).contribution(normal)[2]
        strong = Light3D.directional((0, -1, 0), intensity=2.0).contribution(normal)[2]
        assert strong == pytest.approx(weak * 8.0)

    @pytest.mark.parametrize('light', [
        Light3D.directional((0, -1, 0), color=Color(1, 2, 3), intensity=0.8),
        Light3D.point((1, 2, 3), color=Color(4, 5, 6), intensity=0.9, radius=5.0),
    ])
    def test_round_trip(self, light):
        assert Light3D.from_dict(light.to_dict()).to_dict() == light.to_dict()

    def test_a_name_survives_a_round_trip(self):
        light = Light3D.directional((0, -1, 0), name='key')
        assert Light3D.from_dict(light.to_dict()).name == 'key'

    def test_repr_mentions_where(self):
        assert 'directional' in repr(Light3D.directional((0, -1, 0)))
        assert 'point' in repr(Light3D.point((0, 1, 0)))


# ---------------------------------------------------------------------------
# Entity3D
# ---------------------------------------------------------------------------

class TestEntity3D:
    def test_defaults(self):
        e = Entity3D('e', Mesh3D.cube(1.0))
        assert e.name == 'e'
        assert e.visible is True
        assert e.tags == set()
        assert e.parent is None
        assert e.transform == Mat4()
        assert e.material == Material()

    def test_position_is_the_translation_column(self):
        e = Entity3D('e', Mesh3D.cube(1.0), Mat4.translate(1, 2, 3))
        assert e.position() == Vec3(1, 2, 3)

    def test_translate_composes_without_a_decomposition(self):
        e = Entity3D('e', Mesh3D.cube(1.0), Mat4.translate(1, 0, 0))
        e.translate(0, 2, 0)
        assert e.position() == Vec3(1, 2, 0)

    def test_translate_works_in_the_parent_frame(self):
        e = Entity3D('e', Mesh3D.cube(1.0), Mat4.scale(2, 2, 2))
        e.translate(1, 0, 0)
        # pre-multiplying means the offset is not itself scaled
        assert e.position() == Vec3(1, 0, 0)
        assert e.transform[0, 0] == pytest.approx(2.0)

    def test_move_to_keeps_the_linear_part(self):
        e = Entity3D('e', Mesh3D.cube(1.0),
                     Mat4.translate(5, 5, 5) * Mat4.scale(3, 3, 3))
        e.move_to(0, 0, 0)
        assert e.position() == Vec3(0, 0, 0)
        assert e.transform[0, 0] == pytest.approx(3.0)

    def test_parenting_composes_world_space(self):
        child = Entity3D('child', Mesh3D.cube(1.0), Mat4.translate(1, 0, 0))
        child.parent = Entity3D('parent', Mesh3D.cube(1.0), Mat4.translate(0, 10, 0))
        assert child.world_transform()[1, 3] == pytest.approx(10.0)

    def test_parenting_nests(self):
        a = Entity3D('a', Mesh3D.cube(1.0), Mat4.translate(1, 0, 0))
        b = Entity3D('b', Mesh3D.cube(1.0), Mat4.translate(0, 1, 0))
        c = Entity3D('c', Mesh3D.cube(1.0), Mat4.translate(0, 0, 1))
        a.parent, b.parent = b, c
        world = a.world_transform()
        assert [world[0, 3], world[1, 3], world[2, 3]] == pytest.approx([1, 1, 1])

    def test_normal_matrix_ignores_translation(self):
        e = Entity3D('e', Mesh3D.cube(1.0), Mat4.translate(9, 9, 9))
        assert e.normal_matrix()[0, 3] == 0.0

    def test_normal_matrix_of_uniform_scale(self):
        e = Entity3D('e', Mesh3D.cube(1.0), Mat4.scale(2, 2, 2))
        assert e.normal_matrix()[0, 0] == pytest.approx(0.5)

    def test_tuple_verts_are_normalised_to_vec3(self):
        mesh = Mesh3D()
        mesh.verts = [(0.0, 0.0, 0.0), (1, 0, 0), (0, 1, 0)]
        mesh.faces = [(0, 1, 2)]
        Entity3D.from_mesh('m', mesh)
        assert all(isinstance(v, Vec3) for v in mesh.verts)

    def test_bounds_are_in_world_space(self):
        e = Entity3D('e', Mesh3D.cube(1.0),
                     Mat4.translate(0, 10, 0) * Mat4.scale(2, 2, 2))
        lo, hi = e.bounds()
        assert (lo.y, hi.y) == pytest.approx((9.0, 11.0))
        assert (lo.x, hi.x) == pytest.approx((-1.0, 1.0))

    def test_bounds_follow_the_mesh_not_a_unit_cube(self):
        lo, hi = Entity3D.sphere('s', (0, 5, 0), 2.0).bounds()
        assert (lo.x, hi.x) == pytest.approx((-2.0, 2.0), abs=0.05)
        assert (lo.y, hi.y) == pytest.approx((3.0, 7.0), abs=0.05)

    def test_torus_dimensions_are_not_double_scaled(self):
        lo, hi = Entity3D.torus('t', (0, 0, 0), major=2.0, minor=0.5).bounds()
        assert (lo.x, hi.x) == pytest.approx((-2.5, 2.5), abs=0.05)
        assert (lo.y, hi.y) == pytest.approx((-0.5, 0.5), abs=0.05)

    def test_bounds_of_an_empty_mesh(self):
        empty = Entity3D('e', Mesh3D())
        assert empty.bounds() == (Vec3(), Vec3())
        assert empty.radius() == 0.0

    def test_radius_is_the_farthest_vertex(self):
        assert Entity3D('e', Mesh3D.cube(1.0)).radius() == pytest.approx(
            math.sqrt(3) / 2)

    def test_bounds_are_cached_and_invalidated_by_a_new_mesh(self):
        e = Entity3D('e', Mesh3D.cube(1.0))
        assert e.bounds() == e.bounds()
        e.mesh = Mesh3D.sphere(1.0, 4, 6)
        e._bounds = None
        assert e.bounds()[1].x == pytest.approx(1.0, abs=0.05)

    def test_repr_mentions_name_and_visibility(self):
        e = Entity3D('thing', Mesh3D.cube(1.0))
        assert 'thing' in repr(e)
        e.visible = False
        assert 'False' in repr(e)

    def test_a_material_may_not_be_positional_after_tessellation(self):
        with pytest.raises(TypeError, match='material'):
            _reject_material('rings', Material())
        with pytest.raises(TypeError, match='material'):
            Entity3D.sphere('s', (0, 0, 0), 1.0, Material())

    @pytest.mark.parametrize('make,kind', [
        (lambda: Entity3D.box('b', (0, 0, 0), (2, 2, 2)), 'cube'),
        (lambda: Entity3D.sphere('s', (0, 0, 0), 2.0), 'sphere'),
        (lambda: Entity3D.torus('t', (0, 0, 0)), 'torus'),
        (lambda: Entity3D.icosphere('i', (0, 0, 0)), 'icosphere'),
        (lambda: Entity3D.pyramid('p', (0, 0, 0)), 'pyramid'),
    ])
    def test_every_primitive_is_recognised(self, make, kind):
        assert make().describe_geometry()['kind'] == kind

    def test_primitive_parameters_survive(self):
        d = Entity3D.sphere('s', (0, 0, 0), radius=2.0, rings=4, sectors=6
                            ).describe_geometry()
        assert (d['rings'], d['sectors']) == (4, 6)

    def test_scale_lives_in_the_transform_not_the_geometry(self):
        e = Entity3D.box('b', (1, 2, 3), (4, 5, 6))
        assert e.position() == Vec3(1, 2, 3)
        assert (e.transform[0, 0], e.transform[1, 1], e.transform[2, 2]) == \
            pytest.approx((4, 5, 6))

    def test_a_raw_mesh_falls_back_to_vertices(self):
        mesh = Mesh3D()
        mesh.verts = [(0.0, 0.0, 0.0), (1, 0, 0), (0, 1, 0), (0, 0, 1)]
        mesh.faces = [(0, 1, 2), (0, 2, 3), (0, 3, 1), (1, 3, 2)]
        d = Entity3D.from_mesh('m', mesh).describe_geometry()
        assert d['kind'] == 'mesh'
        assert d['verts'] == [[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]]
        assert d['faces'] == [[0, 1, 2], [0, 2, 3], [0, 3, 1], [1, 3, 2]]

    def test_a_raw_mesh_serialises_as_numbers(self):
        mesh = Mesh3D()
        mesh.verts = [(0.0, 0.0, 0.0), (1, 0, 0), (0, 1, 0)]
        mesh.faces = [(0, 1, 2)]
        json.dumps(Entity3D.from_mesh('m', mesh).to_dict())  # would raise on a Vec3

    def test_tags_are_a_set(self):
        e = Entity3D('e', Mesh3D.cube(1.0), tags=['a', 'b', 'a'])
        assert e.tags == {'a', 'b'}


# ---------------------------------------------------------------------------
# DrawCall and renderers
# ---------------------------------------------------------------------------

class TestDrawCall:
    def test_holds_a_fully_specified_call(self):
        surface = HiResCanvas(40, 20)
        call = scene_with_orb().render(surface)[0]
        assert isinstance(call, DrawCall)
        assert call.surface is surface
        assert isinstance(call.view, Mat4)
        assert isinstance(call.projection, Mat4)
        assert len(call.lights) == 1

    def test_shade_uses_the_material_and_lights(self):
        call = scene_with_orb().render(HiResCanvas(40, 20))[1]
        assert isinstance(call.shade(0, Vec3(0, 0, 1), Vec3(0, 0, -1)), Color)

    def test_shade_passes_the_shaded_point_through(self):
        scene = Scene3D('s')
        scene.add(Light3D.point((0, 0, 10), intensity=1.0, radius=20.0))
        scene.add(Entity3D.box('b', material=Material(Color(255, 255, 255),
                                                      ambient=0.0)))
        call = scene.render(HiResCanvas(20, 10))[0]
        close = call.shade(0, Vec3(0, 0, 1), Vec3(0, 0, -1), Vec3(0, 0, 9))
        distant = call.shade(0, Vec3(0, 0, 1), Vec3(0, 0, -1), Vec3(0, 0, 1))
        assert close.r > distant.r > 0

    def test_repr_is_short(self):
        assert 'floor' in repr(scene_with_orb().render(HiResCanvas(40, 20))[0])

    def test_the_base_renderer_refuses_to_draw(self):
        with pytest.raises(NotImplementedError):
            Renderer().draw(None)

    def test_the_mesh_renderer_draws_into_the_surface(self):
        surface = HiResCanvas(40, 20)
        calls = scene_with_orb().render(surface)
        MeshRenderer().draw(calls[1])
        assert any(surface.buffer[y][x].fg is not None
                   for y in range(surface.h) for x in range(surface.w))

    def test_a_func_renderer_runs_the_callback(self):
        seen = []
        renderer = FuncRenderer(lambda call: seen.append(call.entity.name), 'spy')
        for call in scene_with_orb().render(HiResCanvas(20, 10)):
            renderer.draw(call)
        assert seen == ['floor', 'orb']

    def test_a_func_renderer_may_draw_its_own_pixel(self):
        surface = HiResCanvas(10, 5)
        calls = unlit_scene().render(surface)
        FuncRenderer(
            lambda c: c.surface.set_pixel(0, 0, '#', Color(1, 2, 3))).draw(calls[0])
        assert surface.buffer[0][0].fg == Color(1, 2, 3)

    def test_a_func_renderer_name_defaults(self):
        assert FuncRenderer(lambda c: None).name == 'func'
        assert FuncRenderer(lambda c: None, 'mine').name == 'mine'


# ---------------------------------------------------------------------------
# Scene3D
# ---------------------------------------------------------------------------

class TestScene3D:
    def test_defaults(self):
        scene = Scene3D()
        assert scene.name == 'scene'
        assert scene.entities == []
        assert scene.lights == []
        assert isinstance(scene.camera, Camera3D)
        assert scene.background is None
        assert scene.ambient == Color(24, 28, 44)
        assert scene.z == 0.0
        assert len(scene.renderers) == 1

    def test_a_fresh_scene_already_renders(self):
        assert Scene3D('s').render(HiResCanvas(8, 4)) == []

    def test_add_returns_self_for_chaining(self):
        scene = Scene3D('s')
        assert scene.add(Light3D.directional((0, -1, 0))) is scene

    def test_add_routes_lights_and_entities(self):
        scene = Scene3D('s')
        scene.add(Light3D.directional((0, -1, 0))).add(Entity3D.box('b'))
        assert len(scene.lights) == 1
        assert len(scene.entities) == 1

    def test_add_rejects_other_things(self):
        with pytest.raises(TypeError, match='Entity3D or a Light3D'):
            Scene3D('s').add('not an entity')

    def test_get_finds_an_entity_by_name(self):
        assert scene_with_orb().get('orb').name == 'orb'
        assert scene_with_orb().get('nope') is None

    def test_get_finds_a_light_by_name(self):
        scene = Scene3D('s')
        scene.add(Light3D.directional((0, -1, 0), name='sun'))
        assert scene.get('sun').name == 'sun'

    def test_require_raises_for_a_missing_name(self):
        with pytest.raises(KeyError, match='nope'):
            Scene3D('s').require('nope')

    def test_remove_reports_whether_it_removed_anything(self):
        scene = scene_with_orb()
        assert scene.remove(scene.require('orb')) is True
        assert scene.get('orb') is None
        assert scene.remove(Entity3D.box('stranger')) is False

    def test_len_and_iteration_cover_the_entities(self):
        scene = scene_with_orb()
        assert len(scene) == 2
        assert [e.name for e in scene] == ['floor', 'orb']
        assert scene.require('orb') in scene
        assert scene.lights[0] in scene

    def test_visible_entities_skip_hidden_ones(self):
        scene = scene_with_orb()
        scene.require('orb').visible = False
        assert [e.name for e in scene.visible_entities()] == ['floor']

    def test_with_tag_filters_on_its_own_tags(self):
        scene = Scene3D('s')
        scene.add(Entity3D.box('a', tags=['wall']))
        scene.add(Entity3D.box('b', tags=['floor']))
        assert [e.name for e in scene.with_tag('wall')] == ['a']

    def test_tags_are_inherited_from_parents(self):
        scene = Scene3D('s')
        parent = Entity3D('p', Mesh3D.cube(1.0), tags=['group'])
        child = Entity3D('c', Mesh3D.cube(1.0))
        child.parent = parent
        scene.add(parent).add(child)
        assert [e.name for e in scene.with_tag('group')] == ['p', 'c']
        assert scene.all_tags(child) == {'group'}

    def test_a_hidden_parent_takes_its_children_with_it(self):
        scene = Scene3D('s')
        parent = Entity3D('p', Mesh3D.cube(1.0))
        child = Entity3D('c', Mesh3D.cube(1.0))
        child.parent = parent
        scene.add(parent).add(child)
        parent.visible = False
        assert scene.visible_entities() == []
        assert scene.render(HiResCanvas(10, 10)) == []

    def test_a_hidden_ancestor_also_counts(self):
        scene = Scene3D('s')
        grandparent = Entity3D('g', Mesh3D.cube(1.0))
        parent = Entity3D('p', Mesh3D.cube(1.0))
        child = Entity3D('c', Mesh3D.cube(1.0))
        parent.parent = grandparent
        child.parent = parent
        scene.add(grandparent).add(parent).add(child)
        grandparent.visible = False
        assert scene.visible_entities() == []

    def test_render_paints_the_background(self):
        surface = HiResCanvas(12, 6)
        Scene3D('s', background=Color(10, 20, 30)).render(surface)
        assert surface.buffer[0][0].fg == Color(10, 20, 30)
        assert surface.buffer[5][11].fg == Color(10, 20, 30)

    def test_a_background_on_a_low_res_canvas_lands_in_bg(self):
        surface = Canvas(8, 4)
        Scene3D('s', background=Color(1, 2, 3)).render(surface)
        cell = surface.buffer[0][0]
        assert cell.bg == Color(1, 2, 3)
        assert cell.fg is None

    def test_the_background_is_behind_everything(self):
        scene = scene_with_orb()
        surface = HiResCanvas(20, 10)
        scene.render(surface)
        assert surface.buffer[0][0].z < scene.z

    def test_rendering_twice_is_stable(self):
        scene = scene_with_orb()
        surface = HiResCanvas(20, 10)
        scene.render(surface)
        first = [c.fg for row in surface.buffer for c in row]
        scene.render(surface)
        assert [c.fg for row in surface.buffer for c in row] == first

    def test_render_works_on_a_low_res_canvas(self):
        assert [c.entity.name for c in scene_with_orb().render(Canvas(30, 15))] == \
            ['floor', 'orb']

    def test_the_projection_matches_the_surface_it_is_drawn_on(self):
        scene = scene_with_orb()
        wide = scene.render(HiResCanvas(80, 20))[0].projection
        tall = scene.render(HiResCanvas(20, 80))[0].projection
        assert wide != tall

    def test_an_orthographic_camera_is_passed_through(self):
        camera = Camera3D((0, 0, 5), (0, 0, 0), ortho=True, ortho_height=4.0)
        scene = Scene3D('s', camera=camera)
        scene.add(Entity3D.box('b'))
        assert scene.render(HiResCanvas(20, 10))[0].projection is not None

    def test_a_scene_with_no_camera_says_so(self):
        scene = Scene3D('s')
        scene.camera = None
        with pytest.raises(ValueError, match='no camera'):
            scene.render(HiResCanvas(8, 4))

    def test_every_draw_call_sees_every_light(self):
        scene = Scene3D('s')
        scene.add(Light3D.directional((0, -1, 0)))
        scene.add(Light3D.point((1, 1, 1)))
        scene.add(Entity3D.box('b'))
        assert len(scene.render(HiResCanvas(10, 10))[0].lights) == 2

    def test_several_renderers_all_run(self):
        seen = []
        scene = Scene3D('s')
        scene.renderers = [FuncRenderer(lambda c: seen.append(c.entity.name), 'a'),
                           FuncRenderer(lambda c: seen.append(c.entity.name), 'b')]
        scene.add(Entity3D.box('b'))
        scene.render(HiResCanvas(10, 10))
        assert seen == ['b', 'b']

    def test_repr_counts_what_is_in_it(self):
        text = repr(scene_with_orb())
        assert '2 entities' in text
        assert '1 lights' in text


class TestSceneSerialisation:
    def test_round_trip_keeps_everything(self):
        scene = scene_with_orb()
        back = Scene3D.from_dict(scene.to_dict())
        assert back.name == scene.name
        assert [e.name for e in back.entities] == [e.name for e in scene.entities]
        assert len(back.lights) == len(scene.lights)
        assert back.camera.fov == scene.camera.fov

    def test_round_trip_keeps_materials_and_visibility(self):
        scene = scene_with_orb()
        scene.require('orb').visible = False
        back = Scene3D.from_dict(scene.to_dict())
        assert back.require('orb').visible is False
        assert back.require('orb').material.specular == pytest.approx(0.9)
        assert back.require('orb').material.color == Color(80, 200, 255)

    def test_round_trip_keeps_the_transform(self):
        back = Scene3D.from_dict(scene_with_orb().to_dict())
        assert back.require('orb').position() == Vec3(0, 1.4, 0)

    def test_round_trip_keeps_tags(self):
        scene = Scene3D('s')
        scene.add(Entity3D.box('a', tags=['x', 'y']))
        assert Scene3D.from_dict(scene.to_dict()).require('a').tags == {'x', 'y'}

    def test_round_trip_keeps_the_layer(self):
        scene = Scene3D('s')
        scene.z = 42.0
        assert Scene3D.from_dict(scene.to_dict()).z == pytest.approx(42.0)

    def test_round_trip_keeps_the_background_and_ambient(self):
        scene = Scene3D('s', ambient=Color(9, 8, 7), background=Color(1, 2, 3))
        back = Scene3D.from_dict(scene.to_dict())
        assert back.ambient == Color(9, 8, 7)
        assert back.background == Color(1, 2, 3)

    def test_a_reloaded_scene_paints_the_same_picture(self):
        scene = scene_with_orb()
        before, after = HiResCanvas(40, 20), HiResCanvas(40, 20)
        scene.render(before)
        Scene3D.from_dict(scene.to_dict()).render(after)
        assert [c.fg for row in before.buffer for c in row] == \
               [c.fg for row in after.buffer for c in row]

    def test_primitives_do_not_bloat_the_file(self):
        scene = Scene3D('s')
        scene.add(Entity3D.sphere('s', (0, 0, 0), 1.0, material=Material()))
        payload = json.dumps(scene.to_dict())
        # 408 vertices would be kilobytes of floats if the mesh were inlined
        assert len(payload) < 1000, len(payload)

    def test_a_raw_mesh_is_still_saved(self):
        mesh = Mesh3D()
        mesh.verts = [(0.0, 0.0, 0.0), (1, 0, 0), (0, 1, 0)]
        mesh.faces = [(0, 1, 2)]
        scene = Scene3D('s')
        scene.add(Entity3D.from_mesh('m', mesh))
        assert len(Scene3D.from_dict(scene.to_dict()).require('m').mesh.verts) == 3

    def test_a_missing_camera_gets_the_default(self):
        scene = Scene3D('s')
        scene.add(Entity3D.box('b'))
        payload = scene.to_dict()
        payload['camera'] = None
        assert isinstance(Scene3D.from_dict(payload).camera, Camera3D)

    def test_a_hand_edited_ortho_scene_still_loads(self):
        payload = Scene3D('s').to_dict()
        payload['camera']['ortho'] = True
        payload['camera'].pop('ortho_height', None)
        camera = Scene3D.from_dict(payload).camera
        assert camera.ortho is True
        assert camera.projection is not None

    def test_to_dict_is_json_safe(self):
        json.dumps(scene_with_orb().to_dict())

    def test_save_and_load(self):
        scene = scene_with_orb()
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, 'scene.json')
            assert scene.save(path) == path
            back = Scene3D.load(path)
        assert [e.name for e in back.entities] == ['floor', 'orb']

    def test_save_creates_missing_directories(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, 'nested', 'deeper', 'scene.json')
            scene_with_orb().save(path)
            assert os.path.exists(path)

    def test_load_raises_for_a_missing_file(self):
        with pytest.raises(FileNotFoundError):
            Scene3D.load('/nonexistent/scene.json')

    def test_the_file_is_human_readable(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, 'scene.json')
            scene_with_orb().save(path)
            with open(path) as fh:
                text = fh.read()
        assert '"material"' in text
        assert '\n' in text.strip()


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

class TestHelpers:
    def test_vec_returns_a_vector_unchanged(self):
        v = Vec3(1, 2, 3)
        assert _vec(v) is v

    @pytest.mark.parametrize('value', [(1, 2, 3), [1, 2, 3]])
    def test_vec_accepts_sequences(self, value):
        assert _vec(value) == Vec3(1, 2, 3)

    def test_vec_rejects_anything_else(self):
        with pytest.raises(TypeError, match='3-sequence'):
            _vec('nope')

    def test_color_accepts_both_forms(self):
        c = Color(1, 2, 3)
        assert _color(c) is c
        assert _color((1, 2, 3)) == c

    def test_fill_covers_every_cell(self):
        surface = HiResCanvas(5, 3)
        _fill(surface, Color(1, 2, 3), 0.5)
        assert all(c.fg == Color(1, 2, 3) for row in surface.buffer for c in row)
        assert all(c.z == 0.5 for row in surface.buffer for c in row)

    def test_fill_on_a_low_res_canvas_uses_bg(self):
        surface = Canvas(4, 2)
        _fill(surface, Color(1, 2, 3), 0.0)
        assert all(c.bg == Color(1, 2, 3) for row in surface.buffer for c in row)


# ---------------------------------------------------------------------------
# the whole point: several backends, one scene
# ---------------------------------------------------------------------------

class TestBackendIndependence:
    @pytest.mark.parametrize('size', [(40, 20), (80, 40), (20, 10)])
    def test_a_scene_draws_at_any_size(self, size):
        surface = HiResCanvas(*size)
        assert len(scene_with_orb().render(surface)) == 2
        lit = sum(1 for y in range(surface.h) for x in range(surface.w)
                  if surface.buffer[y][x].fg is not None)
        assert lit > 0

    def test_two_renders_produce_identical_calls(self):
        scene = scene_with_orb()
        a = scene.render(HiResCanvas(40, 20))
        b = scene.render(HiResCanvas(40, 20))
        assert [(c.entity.name, len(c.lights)) for c in a] == \
               [(c.entity.name, len(c.lights)) for c in b]
        assert a[0].projection == b[0].projection

    def test_a_custom_renderer_learns_nothing_but_the_call(self):
        sizes = [(c.surface.w, c.surface.h, c.entity.name)
                 for c in scene_with_orb().render(HiResCanvas(30, 15))]
        assert sizes == [(30, 15, 'floor'), (30, 15, 'orb')]

    def test_lighting_varies_across_the_scene(self):
        surface = HiResCanvas(40, 20)
        scene_with_orb().render(surface)
        lit = [c.fg.r for row in surface.buffer for c in row if c.fg is not None]
        assert max(lit) > min(lit)
