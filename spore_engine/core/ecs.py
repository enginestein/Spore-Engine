"""A small entity-component system that renders through Scene/Layer.

Entities are bags of components addressed by a world-unique id.  Systems
run in priority order each ``world.update(dt)``.  ``SpriteRenderSystem`` is
the Scene/Layer integration point: every entity holding a ``Transform`` and
a ``SpriteComponent`` is blitted onto a ``Scene`` canvas (or one of its
overlay layers) every tick, so games can keep game state in ECS terms while
presenting through the existing ``Scene.present`` compositor.

    world = World()
    hero = world.create()
    hero.add(Transform(5, 3))
    hero.add(SpriteComponent(sprite))           # a core Sprite from an asset
    scene = Scene(40, 20)
    world.add_system(SpriteRenderSystem(scene))
    world.update(0.016)
    scene.present(sys.stdout)

The ECS entity type is ``EcsEntity`` so it never collides with the animation
``Entity``; component types are plain classes, so ``world.query`` keys on the
running component class.
"""

from __future__ import annotations
from collections.abc import Iterator

from .canvas import Canvas
from .scene import Scene
from .sprite import Sprite


class Component:
    """Base class for all components (a plain data holder)."""

    def __init__(self, label: str = ''):
        self.label = label

    def __repr__(self):
        return f'{type(self).__name__}({self.label!r})'


class EcsEntity:
    """One game object: an id plus its components, keyed by component type."""

    __slots__ = ('components', 'id', 'world')

    def __init__(self, world: World, eid: int):
        self.world = world
        self.id = eid
        self.components: dict[type, Component] = {}

    def add(self, comp: Component) -> EcsEntity:
        self.components[type(comp)] = comp
        return self

    def get(self, comp_type: type):
        return self.components.get(comp_type)

    def has(self, comp_type: type) -> bool:
        return comp_type in self.components

    def remove(self, comp_type: type):
        return self.components.pop(comp_type, None)

    def __repr__(self):
        parts = ', '.join(c.__class__.__name__ for c in self.components.values())
        return f'EcsEntity({self.id}: {parts})'


class World:
    """Owns entities and systems; systems run in priority order on tick."""

    def __init__(self):
        self._entities: dict[int, EcsEntity] = {}
        self._next_id = 1
        self.systems: list[System] = []

    def create(self) -> EcsEntity:
        e = EcsEntity(self, self._next_id)
        self._entities[e.id] = e
        self._next_id += 1
        return e

    def add(self, entity: EcsEntity) -> EcsEntity:
        self._entities[entity.id] = entity
        if entity.id >= self._next_id:
            self._next_id = entity.id + 1
        entity.world = self
        return entity

    def e(self, eid: int) -> EcsEntity | None:
        return self._entities.get(eid)

    def has(self, eid: int) -> bool:
        return eid in self._entities

    def delete(self, target) -> bool:
        eid = target.id if isinstance(target, EcsEntity) else int(target)
        return self._entities.pop(eid, None) is not None

    def query(self, *types: type) -> Iterator[EcsEntity]:
        """Yield entities carrying every one of ``types``, in creation order."""
        for e in self._entities.values():
            if all(t in e.components for t in types):
                yield e

    def add_system(self, system: System) -> System:
        self.systems.append(system)
        self.systems.sort(key=lambda s: s.priority)
        return system

    def update(self, dt: float):
        for system in self.systems:
            system.update(self, dt)

    def __len__(self):
        return len(self._entities)

    def __repr__(self):
        return f'World({len(self)} entities, {len(self.systems)} systems)'


class System:
    """Base class: override ``update``; ``priority`` orders systems likely first."""

    def __init__(self, priority: int = 0):
        self.priority = priority

    def update(self, world: World, dt: float):
        pass

    def __repr__(self):
        return f'{type(self).__name__}(priority={self.priority})'


class Transform(Component):
    """Position/scale of an entity inside a Scene (integer cell grid)."""

    def __init__(self, x: float = 0, y: float = 0, z: float = 0,
                 scale: int = 1):
        super().__init__('transform')
        self.x = x
        self.y = y
        self.z = z
        self.scale = max(1, int(scale))


class SpriteComponent(Component):
    """Drawable: a core Sprite plus optional colour overrides for this entity."""

    def __init__(self, sprite: Sprite, fg=None, bg=None,
                 transparent: str | None = ' ', z: float | None = None):
        super().__init__('sprite')
        self.sprite = sprite
        self.fg = fg
        self.bg = bg
        self.transparent = transparent
        self.z = z


class SpriteRenderSystem(System):
    """Blit every ``Transform + SpriteComponent`` entity onto a Scene/Layer.

    With ``layer`` set, entities draw onto that overlay layer's canvas
    (``scene.layer(name)``); otherwise onto the main ``scene.canvas``.
    ``z`` here is the fallback depth when an entity leaves ``SpriteComponent.z``
    unset; ``transform.z`` then takes precedence through the component default.
    """

    def __init__(self, scene: Scene | None = None,
                 layer: str | None = None, priority: int = 0,
                 z: float = 0):
        super().__init__(priority)
        self.scene = scene
        self.layer = layer
        self.z = z

    def target(self) -> Canvas | None:
        if self.scene is None:
            return None
        if self.layer is not None:
            return self.scene.layer(self.layer).canvas
        return self.scene.canvas

    def update(self, world: World, dt: float):
        canvas = self.target()
        if canvas is None:
            return
        for entity in world.query(Transform, SpriteComponent):
            t = entity.get(Transform)
            comp = entity.get(SpriteComponent)
            depth = comp.z
            if depth is None:
                depth = t.z if t.z else self.z
            comp.sprite.blit_to(canvas, int(t.x), int(t.y),
                                comp.fg, comp.bg, depth,
                                comp.transparent, int(t.scale))