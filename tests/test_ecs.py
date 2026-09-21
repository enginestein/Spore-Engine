"""Entity-component-system: entities, queries, systems, Scene rendering."""

import io

from spore_engine import (World, System, Component, EcsEntity,
                          Transform, SpriteComponent, SpriteRenderSystem)
from spore_engine import Canvas, Scene, Color, Sprite, load_sprite
import tempfile, os


def test_entity_create_and_query():
    world = World()
    a = world.create()
    b = world.create()
    assert isinstance(a, EcsEntity)
    assert a.id == 1 and b.id == 2
    assert len(world) == 2
    a.add(Transform(1, 2))
    found = list(world.query(Transform))
    assert found == [a]


def test_world_methods():
    world = World()
    e = world.create()
    assert world.has(e.id)
    assert world.e(e.id) is e
    assert world.delete(e.id) is True
    assert not world.has(e.id)
    assert list(world.query(Transform)) == []


def test_add_re_registers_external_entity():
    world = World()
    foreign = EcsEntity.__new__(EcsEntity)          # not owned yet
    foreign.id = 42
    foreign.components = {}
    world.add(foreign)
    assert world.e(42) is foreign
    assert foreign.world is world


def test_component_add_get_remove():
    e = World().create()
    t = Transform(0, 0)
    e.add(t)
    assert e.get(Transform) is t
    assert e.has(Transform)
    assert e.remove(Transform) is t
    assert not e.has(Transform)


def test_system_priority_order():
    calls = []

    class S(System):
        def __init__(self, name, priority=0):
            super().__init__(priority)
            self.name = name

        def update(self, world, dt):
            calls.append(self.name)

    world = World()
    world.add_system(S('late', 10))
    world.add_system(S('early', 0))
    world.update(0.1)
    assert calls == ['early', 'late']


def test_sprite_render_system_into_scene():
    world = World()
    e = world.create()
    e.add(Transform(1, 1))
    e.add(SpriteComponent(Sprite.from_string('.X.\nXXX\n')))
    scene = Scene(10, 5)
    world.add_system(SpriteRenderSystem(scene))
    world.update(0.0)
    assert scene.canvas.get_pixel(1, 1).char == '.'
    assert scene.canvas.get_pixel(2, 1).char == 'X'
    assert scene.canvas.get_pixel(2, 2).char == 'X'


def test_sprite_render_system_layer():
    world = World()
    e = world.create()
    e.add(Transform(0, 0))
    e.add(SpriteComponent(Sprite.from_string('@\n')))
    scene = Scene(10, 5)
    world.add_system(SpriteRenderSystem(scene, layer='hud'))
    world.update(0.0)
    assert scene.layer('hud').canvas.get_pixel(0, 0).char == '@'
    assert scene.canvas.get_pixel(0, 0).char != '@'


def test_sprite_render_system_level_and_z():
    world = World()
    e = world.create()
    e.add(Transform(3, 2, z=7))
    e.add(SpriteComponent(Sprite.from_string('~')))
    scene = Scene(10, 5)
    world.add_system(SpriteRenderSystem(scene))
    world.update(0.0)
    assert scene.canvas.get_pixel(3, 2).char == '~'
    assert scene.canvas.get_pixel(3, 2).z == 7


def test_system_without_scene_is_noop():
    world = World()
    world.create().add(Transform(0, 0)).add(SpriteComponent(Sprite.from_string('x')))
    world.add_system(SpriteRenderSystem())
    world.update(0.0)  # must not raise


def test_end_to_end_with_assets_and_present(tmp_path):
    p = tmp_path / 's.spr'
    p.write_text('>--o\n')
    sprite = load_sprite(str(p))
    world = World()
    world.create().add(Transform(2, 1)).add(SpriteComponent(sprite))
    scene = Scene(12, 4)
    world.add_system(SpriteRenderSystem(scene))
    world.update(0.016)
    buf = io.StringIO()
    scene.present(buf)
    out = buf.getvalue()
    assert '>--o' in out


def test_ecs_entity_repr():
    e = World().create()
    e.add(Transform(0, 0))
    assert 'EcsEntity' in repr(e)
    assert 'Transform' in repr(e)