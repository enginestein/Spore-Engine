"""A retained 3-D scene: entities you build once, keep, and save.

Everything else in :mod:`spore_engine.render3d` is immediate mode. A demo
function computes a picture, throws it away and recomputes it next frame; there
is no object that outlives a frame, so there is nothing to move, name, hide,
group, or save. This module is the missing half - the part that makes the engine
an authoring surface rather than a gallery of renderers.

The shape::

    scene = Scene3D('demo')
    scene.camera = Camera3D.look_at((0, 3, 9), (0, 0, 0), fov=55)
    scene.ambient = Color(20, 24, 40)
    scene.add(Light3D.directional((0.4, -1, 0.3), color=Color(255, 240, 200),
                                 intensity=1.0))
    scene.add(Entity3D.box('plinth', (0, -1, 0), (4, 0.5, 4),
                           Material(Color(120, 130, 150))))
    scene.add(Entity3D.sphere('orb', (0, 1.2, 0), 1.4,
                              Material(Color(90, 200, 255), specular=0.9)))
    scene.render(hr)                 # draws every entity, z-buffered
    scene.save('scene.json')         # and it round-trips

Three pieces make that work.

:class:`DrawCall` is the common currency. The five 3-D backends disagreed about
everything - surface type, camera form, field-of-view units, how depth was
stored - so the scene resolves all of that once per frame and hands each
renderer a fully specified call. The backends keep their existing entry points;
a :class:`Renderer` adapts one of them.

:class:`Entity3D` is the retained thing: a geometry, a transform, a material, a
name, a visibility flag. It is data, so it can be stored, serialised, and
diffed.

:class:`Material` and :class:`Light3D` are declarative shading, which the
engine previously hard-coded per renderer - a 0.2 ambient floor here, a Phong
term with a white specular there, altitude bands in the voxel path, and nothing
at all in the isometric one.

``to_dict``/``from_dict`` are JSON-clean, so a scene is a file. That is the part
that makes this an authoring tool rather than a toy: build it in code once, then
open the file and change a number.
"""

from __future__ import annotations

import json
import os

from ..core.color import Color
from ..core.canvas import HiResCanvas
from ..core.geom import Mat4, Vec3
from .camera3d import Camera3D
from .engine3d import Mesh3D, render_mesh_solid

__all__ = [
    'DrawCall',
    'Entity3D',
    'FuncRenderer',
    'Light3D',
    'Material',
    'MeshRenderer',
    'Renderer',
    'Scene3D',
]

#: How a geometry is rebuilt from its serialised description. Keys are the
#: ``kind`` in JSON; values build a fresh :class:`Mesh3D` from parameters.
PRIMITIVES = {
    'cube': lambda **p: Mesh3D.cube(p.get('size', 1.0)),
    'sphere': lambda **p: Mesh3D.sphere(p.get('radius', 1.0), p.get('rings', 12),
                                        p.get('sectors', 16)),
    'torus': lambda **p: Mesh3D.torus(p.get('major_radius', 1.5),
                                      p.get('minor_radius', 0.5),
                                      p.get('major_segments', 24),
                                      p.get('minor_segments', 12)),
    'icosphere': lambda **p: Mesh3D.icosphere(p.get('radius', 1.0),
                                              p.get('subdivisions', 2)),
    'pyramid': lambda **p: Mesh3D.pyramid(p.get('size', 1.0)),
}


def _vec(v) -> Vec3:
    if isinstance(v, Vec3):
        return v
    if isinstance(v, (tuple, list)):
        return Vec3(*v)
    raise TypeError(f'expected a Vec3 or a 3-sequence, got {type(v).__name__}')


def _color(c) -> Color:
    return c if isinstance(c, Color) else Color(*c)


# ---------------------------------------------------------------------------
# Shading, declaratively
# ---------------------------------------------------------------------------

class Material:
    """How a surface responds to light.

    Replaces shading that used to be hard-coded inside each renderer: a Lambert
    term with a 0.2 floor in the mesh rasterizer, a Phong term with a white
    specular in the raytracer, altitude bands in the voxel path, and nothing at
    all in the isometric one. ``shade`` here is the single implementation, and
    every backend can be handed it.
    """

    __slots__ = ('ambient', 'color', 'emissive', 'shininess', 'specular')

    def __init__(self, color=(200, 200, 200), ambient: float = 0.15,
                 specular: float = 0.0, shininess: float = 24.0,
                 emissive: float = 0.0):
        self.color = _color(color)
        self.ambient = float(ambient)
        self.specular = float(specular)
        self.shininess = float(shininess)
        self.emissive = float(emissive)

    def shade(self, normal: Vec3, view_dir: Vec3, lights,
              at: Vec3 | None = None) -> Color:
        """A Blinn-Phong term: ambient floor, then diffuse and specular per light.

        ``lights`` is a list of :class:`Light3D`; one with no effect on this
        normal contributes nothing, so an unlit face is the ambient floor
        rather than black. Pass ``at``, the shaded point in world space, so a
        point light attenuates by its real distance rather than by the origin.
        """
        out = self.color.mul(self.ambient)
        for light in lights or ():
            direction, colour, strength = light.contribution(normal, at)
            if strength <= 0.0:
                continue
            lit = self.color.mul(min(1.0, strength))
            out = Color(min(255, out.r + lit.r),
                        min(255, out.g + lit.g),
                        min(255, out.b + lit.b))
            if self.specular > 0.0:
                half = (direction - view_dir)
                if half.length() > 0:
                    spec = max(0.0, half.norm().dot(normal)) ** self.shininess
                    add = int(255 * min(1.0, spec * self.specular * strength))
                    out = Color(min(255, out.r + add), min(255, out.g + add),
                                min(255, out.b + add))
        if self.emissive:
            e = int(255 * min(1.0, self.emissive))
            out = Color(min(255, out.r + e), min(255, out.g + e),
                        min(255, out.b + e))
        return out

    def to_dict(self) -> dict:
        return {'color': [self.color.r, self.color.g, self.color.b],
                'ambient': self.ambient, 'specular': self.specular,
                'shininess': self.shininess, 'emissive': self.emissive}

    @classmethod
    def from_dict(cls, d: dict) -> Material:
        return cls(d.get('color', (200, 200, 200)), d.get('ambient', 0.15),
                   d.get('specular', 0.0), d.get('shininess', 24.0),
                   d.get('emissive', 0.0))

    def __eq__(self, other) -> bool:
        if not isinstance(other, Material):
            return NotImplemented
        return self.to_dict() == other.to_dict()

    def __repr__(self) -> str:
        return (f'Material(color={self.color.hex}, ambient={self.ambient}, '
                f'specular={self.specular})')


class Light3D:
    """A directional or point light.

    :attr:`direction` is the direction light *travels*, so the default
    ``(0, -1, 0)`` is a sun shining down onto up-facing surfaces.
    :meth:`contribution` reports the opposite - pointing back at the light -
    because that is the vector the Lambert and Blinn-Phong terms want.

    A point light needs the point being shaded to attenuate and to aim
    correctly, so pass ``at``; the default of the origin is only a fallback.
    """

    __slots__ = ('color', 'direction', 'intensity', 'kind', 'name', 'position',
                 'radius')

    def __init__(self, direction=(0, -1, 0), color=(255, 255, 255),
                 intensity: float = 1.0, position=None, radius: float = 0.0,
                 name: str = 'light'):
        if intensity < 0:
            raise ValueError(f'Light3D intensity must be >= 0, got {intensity}')
        self.name = name
        self.direction = _vec(direction)
        self.color = _color(color)
        self.intensity = float(intensity)
        self.position = _vec(position) if position is not None else None
        self.radius = float(radius)
        self.kind = 'point' if position is not None else 'directional'

    @classmethod
    def directional(cls, direction=(0, -1, 0), **kwargs) -> Light3D:
        return cls(direction=direction, **kwargs)

    @classmethod
    def point(cls, position=(0, 5, 5), **kwargs) -> Light3D:
        return cls(position=position, **kwargs)

    def contribution(self, normal: Vec3, at: Vec3 | None = None):
        """``(direction_towards_light, colour, strength)`` for a surface normal.

        ``at`` is the point being shaded. A point light uses it for its
        direction and its falloff; a directional light ignores it. Returns a
        zero strength when the light is behind the surface, so a back face is
        lit only by the ambient term.
        """
        if self.position is not None:
            origin = at if at is not None else Vec3()
            to_light = self.position - origin
            distance = to_light.length()
            if distance == 0:
                return Vec3(0, 1, 0), self.color, 0.0
            falloff = 1.0
            if self.radius > 0:
                falloff = max(0.0, 1.0 - (distance / self.radius) ** 2)
            strength = self.intensity * falloff
            lambert = max(0.0, to_light.norm().dot(normal))
            return to_light.norm(), self.color, strength * lambert
        towards = -self.direction.norm()
        lambert = max(0.0, towards.dot(normal))
        return towards, self.color, self.intensity * lambert

    def to_dict(self) -> dict:
        d = {'kind': self.kind, 'name': self.name,
             'color': [self.color.r, self.color.g, self.color.b],
             'intensity': self.intensity}
        if self.kind == 'point':
            d['position'] = [self.position.x, self.position.y, self.position.z]
            d['radius'] = self.radius
        else:
            d['direction'] = [self.direction.x, self.direction.y, self.direction.z]
        return d

    @classmethod
    def from_dict(cls, d: dict) -> Light3D:
        name = d.get('name', 'light')
        if d.get('kind') == 'point':
            return cls(position=d.get('position', (0, 5, 5)),
                       color=d.get('color', (255, 255, 255)),
                       intensity=d.get('intensity', 1.0),
                       radius=d.get('radius', 0.0), name=name)
        return cls(direction=d.get('direction', (0, -1, 0)),
                   color=d.get('color', (255, 255, 255)),
                   intensity=d.get('intensity', 1.0), name=name)

    def __repr__(self) -> str:
        where = (f'position=({self.position.x:.1f},{self.position.y:.1f},'
                 f'{self.position.z:.1f})' if self.kind == 'point'
                 else f'direction=({self.direction.x:.1f},{self.direction.y:.1f},'
                      f'{self.direction.z:.1f})')
        return f'Light3D({self.kind}, {where}, intensity={self.intensity})'


# ---------------------------------------------------------------------------
# The retained object
# ---------------------------------------------------------------------------

def _reject_material(what: str, value) -> None:
    """Catch ``sphere('x', (0,0,0), 1.0, material)``.

    The tessellation arguments sit between ``radius`` and ``material``, so a
    material passed positionally lands in one of them and fails much later
    inside the mesh builder with a confusing message.
    """
    if isinstance(value, Material):
        raise TypeError(f'{what} received a Material; pass material=... by keyword')


class Entity3D:
    """One thing in the scene: geometry, transform, material, name, visibility.

    Deliberately plain data. The transform is a full :class:`Mat4`, so
    translation, rotation and non-uniform scale compose the way they do
    everywhere else, and :meth:`normal_matrix` is derived rather than stored so
    it cannot go stale.
    """

    __slots__ = ('_bounds', '_geometry', 'material', 'mesh', 'name', 'parent',
                 'tags', 'transform', 'visible')

    def __init__(self, name: str, mesh: Mesh3D, transform: Mat4 | None = None,
                 material: Material | None = None, visible: bool = True,
                 tags=()):
        self.name = name
        self.mesh = mesh
        self.transform = transform if transform is not None else Mat4()
        self.material = material if material is not None else Material()
        self.visible = bool(visible)
        self.tags = set(tags)
        self.parent = None
        self._bounds = None
        self._geometry: dict | None = None
        if mesh is not None and any(not isinstance(v, Vec3) for v in mesh.verts):
            # a hand-built mesh is full of plain tuples; everything below reads
            # .x/.y/.z, so normalise once here rather than at every use
            mesh.verts = [v if isinstance(v, Vec3) else Vec3(*v) for v in mesh.verts]
            self._bounds = None

    # -- constructors for the primitives ------------------------------------

    @classmethod
    def box(cls, name, position=(0, 0, 0), size=(1, 1, 1), material=None, **kw) -> Entity3D:
        return cls._prim(name, 'cube', {'size': 1.0}, Mesh3D.cube(1.0),
                         Mat4.translate(*position) * Mat4.scale(*size), material, **kw)

    @classmethod
    def sphere(cls, name, position=(0, 0, 0), radius=1.0, rings=16, sectors=24,
               material=None, **kw) -> Entity3D:
        _reject_material('rings', rings)
        _reject_material('sectors', sectors)
        # the mesh is a unit sphere and the radius lives in the transform, so
        # the recorded description carries the tessellation only
        return cls._prim(name, 'sphere', {'rings': rings, 'sectors': sectors},
                         Mesh3D.sphere(1.0, rings, sectors),
                         Mat4.translate(*position) * Mat4.scale(radius, radius, radius),
                         material, **kw)

    @classmethod
    def torus(cls, name, position=(0, 0, 0), major=1.5, minor=0.5,
              major_segments=24, minor_segments=12, material=None, **kw) -> Entity3D:
        return cls._prim(name, 'torus',
                         {'major_radius': major, 'minor_radius': minor,
                          'major_segments': major_segments,
                          'minor_segments': minor_segments},
                         Mesh3D.torus(major, minor, major_segments, minor_segments),
                         Mat4.translate(*position), material, **kw)

    @classmethod
    def icosphere(cls, name, position=(0, 0, 0), radius=1.0, subdivisions=2,
                  material=None, **kw) -> Entity3D:
        return cls._prim(name, 'icosphere', {'subdivisions': subdivisions},
                         Mesh3D.icosphere(1.0, subdivisions),
                         Mat4.translate(*position) * Mat4.scale(radius, radius, radius),
                         material, **kw)

    @classmethod
    def pyramid(cls, name, position=(0, 0, 0), size=1.0, material=None, **kw) -> Entity3D:
        return cls._prim(name, 'pyramid', {'size': 1.0}, Mesh3D.pyramid(1.0),
                         Mat4.translate(*position) * Mat4.scale(size, size, size),
                         material, **kw)

    @classmethod
    def _prim(cls, name, kind, params, mesh, transform, material=None, **kw) -> Entity3D:
        """Build from a primitive and remember how, so a scene file stays small
        and readable instead of embedding a few thousand vertex triples."""
        entity = cls(name, mesh, transform, material, **kw)
        entity._geometry = {'kind': kind, **params}
        return entity

    @classmethod
    def from_mesh(cls, name, mesh: Mesh3D, transform=None, material=None,
                  **kw) -> Entity3D:
        return cls(name, mesh, transform, material, **kw)

    # -- transforms -------------------------------------------------------

    def world_transform(self) -> Mat4:
        """The transform including any parent chain."""
        m = self.transform
        node = self.parent
        while node is not None:
            m = node.transform * m
            node = node.parent
        return m

    def normal_matrix(self) -> Mat4:
        """The world transform's normal matrix - see :meth:`Mat4.normal_matrix`
        for why a scaled model needs this rather than the transform itself."""
        return self.world_transform().normal_matrix()

    def translate(self, dx, dy, dz) -> Entity3D:
        """Move by a delta, preserving whatever rotation and scale is there.

        Pre-multiplying a translation is exact for any matrix, so this is the
        safe way to animate a position.
        """
        self.transform = Mat4.translate(dx, dy, dz) * self.transform
        return self

    def move_to(self, x, y, z) -> Entity3D:
        """Place at an absolute position, keeping the linear part.

        Takes the 3x3 block of the *world* transform and rebuilds the
        translation, so a parented entity lands where it was told to. For
        anything more involved than position, set :attr:`transform` directly -
        a general matrix cannot be decomposed back into TRS.
        """
        world = self.world_transform()
        linear = Mat4()
        for i in range(3):
            for j in range(3):
                linear[i, j] = world[i, j]
        self.transform = Mat4.translate(x, y, z) * linear
        return self

    def bounds(self) -> tuple:
        """The world-space axis-aligned bounds, as two corners.

        Cheap enough to call per frame for a handful of entities, which is what
        frustum culling wants; the local half-extents are cached because they
        only change when the mesh does.
        """
        if self._bounds is None:
            mesh = self.mesh
            if not mesh.verts:
                self._bounds = (Vec3(), Vec3())
            else:
                xs = [v.x for v in mesh.verts]
                ys = [v.y for v in mesh.verts]
                zs = [v.z for v in mesh.verts]
                self._bounds = (Vec3(min(xs), min(ys), min(zs)),
                                 Vec3(max(xs), max(ys), max(zs)))
        world = self.world_transform()
        lo, hi = self._bounds
        corners = [world.transform(Vec3(x, y, z))
                   for x in (lo.x, hi.x) for y in (lo.y, hi.y) for z in (lo.z, hi.z)]
        xs = [c.x for c in corners]
        ys = [c.y for c in corners]
        zs = [c.z for c in corners]
        return Vec3(min(xs), min(ys), min(zs)), Vec3(max(xs), max(ys), max(zs))

    def radius(self) -> float:
        """The world-space distance from the entity's origin to its farthest
        vertex - the cheapest conservative bound for culling and for sizing a
        point light's falloff."""
        if not self.mesh.verts:
            return 0.0
        world = self.world_transform()
        return max(world.transform(v).length() for v in self.mesh.verts)

    def position(self) -> Vec3:
        """The world-space translation of this entity."""
        world = self.world_transform()
        return Vec3(world[0, 3], world[1, 3], world[2, 3])

    # -- geometry description (for serialisation) --------------------------

    def describe_geometry(self) -> dict:
        """A JSON-safe description of the mesh.

        Recognises the built-in primitives by comparing against a freshly built
        copy, and falls back to raw verts/faces for anything loaded or
        hand-built. That keeps a scene of primitives small and readable while
        still round-tripping a mesh that came from an OBJ file.
        """
        if self._geometry is not None:
            return dict(self._geometry)
        params = {'cube': ('size',), 'sphere': ('radius', 'rings', 'sectors'),
                  'torus': ('major_radius', 'minor_radius', 'major_segments',
                            'minor_segments'),
                  'icosphere': ('radius', 'subdivisions'), 'pyramid': ('size',)}
        for kind, build in PRIMITIVES.items():
            candidate = build()
            if len(candidate.verts) != len(self.mesh.verts):
                continue
            if all(abs(a - b) < 1e-6 for va, vb in zip(candidate.verts, self.mesh.verts, strict=False)
                   for a, b in ((va.x, vb.x), (va.y, vb.y), (va.z, vb.z))) \
                    and candidate.faces == self.mesh.faces:
                d = {'kind': kind}
                for key in params[kind]:
                    d[key] = getattr(self.mesh, key, None) or 1.0
                return d
        return {'kind': 'mesh',
                'verts': [[v.x, v.y, v.z] for v in self.mesh.verts],
                'faces': [list(f) for f in self.mesh.faces]}

    @staticmethod
    def build_geometry(d: dict) -> Mesh3D:
        kind = d.get('kind', 'cube')
        if kind in PRIMITIVES:
            return PRIMITIVES[kind](**{k: v for k, v in d.items() if k != 'kind'})
        mesh = Mesh3D()
        mesh.verts = [Vec3(*v) for v in d.get('verts', [])]
        mesh.faces = [list(f) for f in d.get('faces', [])]
        return mesh

    # -- serialisation ----------------------------------------------------

    def to_dict(self) -> dict:
        t = self.transform
        return {'name': self.name, 'visible': self.visible,
                'tags': sorted(self.tags),
                'transform': [t[i, j] for i in range(4) for j in range(4)],
                'material': self.material.to_dict(),
                'geometry': self.describe_geometry()}

    @classmethod
    def from_dict(cls, d: dict) -> Entity3D:
        flat = d.get('transform') or [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]
        transform = Mat4(list(flat))
        geometry = d.get('geometry', {})
        entity = cls(d.get('name', 'entity'),
                     cls.build_geometry(geometry),
                     transform,
                     Material.from_dict(d.get('material', {})),
                     d.get('visible', True),
                     d.get('tags', ()))
        entity._geometry = dict(geometry)
        return entity

    def __repr__(self) -> str:
        return (f"Entity3D({self.name!r}, verts={len(self.mesh.verts)}, "
                f"faces={len(self.mesh.faces)}, visible={self.visible})")


# ---------------------------------------------------------------------------
# Draw calls and renderers
# ---------------------------------------------------------------------------

class DrawCall:
    """One resolved thing to draw: the common currency between a scene and a backend.

    The five 3-D backends disagreed about surface type, camera form, fov units
    and where depth lived. :class:`Scene3D` settles all of that once per frame
    and hands each backend a fully specified call, so a backend never has to ask
    what aspect it is drawing for or whether a light list is a list.
    """

    __slots__ = ('entity', 'lights', 'material', 'projection', 'surface', 'view')

    def __init__(self, entity: Entity3D, surface, view: Mat4, projection: Mat4,
                 lights, material: Material):
        self.entity = entity
        self.surface = surface
        self.view = view
        self.projection = projection
        self.lights = list(lights)
        self.material = material

    def shade(self, face_index, normal, view_dir, at: Vec3 | None = None) -> Color:
        """The material's shading for one face, with lights applied."""
        return self.material.shade(normal, view_dir, self.lights, at)

    def __repr__(self) -> str:
        return f'DrawCall({self.entity.name!r}, lights={len(self.lights)})'


class Renderer:
    """Base class for a backend. Subclasses implement :meth:`draw`.

    Kept as a real class rather than a ``Protocol`` so a scene can hold
    several renderers, swap one for another, and be serialised - which is the
    point of having a scene at all.
    """

    name = 'renderer'

    def draw(self, call: DrawCall) -> None:
        raise NotImplementedError

    def __repr__(self) -> str:
        return f'{type(self).__name__}()'


class MeshRenderer(Renderer):
    """Feeds the engine's z-buffered mesh rasterizer.

    Applies the entity's world transform to the mesh, then hands
    :func:`~spore_engine.render3d.engine3d.render_mesh_solid` a shading callback
    so the material and light list are honoured instead of the built-in
    Lambert term.

    That rasteriser shades a whole face one colour, so there is no per-pixel
    position to hand a point light; its falloff is measured from the origin. A
    renderer that wants exact point lights should shade per vertex and pass
    ``at`` to :meth:`Material.shade`.
    """

    name = 'mesh'

    def draw(self, call: DrawCall) -> None:
        entity = call.entity
        world = entity.world_transform()
        mesh = entity.mesh if world == Mat4() else entity.mesh.transform(world)
        lights = call.lights
        material = call.material
        surface = call.surface
        # the rasterizer keeps a z per sub-cell, which only a hi-res buffer
        # has, so a low-res surface is drawn through a temporary one and folded
        # back down. The fold leaves empty sub-cells alone, so a background
        # painted earlier still shows through.
        # two sub-cells per cell row, which is the usual hi-res convention
        target = surface if isinstance(surface, HiResCanvas) else \
            HiResCanvas(surface.width, surface.height * 2)
        render_mesh_solid(
            target, mesh, call.view, call.projection,
            shade=lambda fi, n, vd, _lights: material.shade(n, vd, lights, None))
        if target is not surface:
            target.to_canvas(surface)


class FuncRenderer(Renderer):
    """Wraps any plain ``fn(call)`` so a custom backend needs no subclass.

    The escape hatch for the backends this module does not adapt - the raytracer,
    the SDF marcher, the isometric blitter - and for a one-off experiment.
    """

    def __init__(self, fn, name: str = 'func') -> None:
        self.fn = fn
        self.name = name

    def draw(self, call: DrawCall) -> None:
        self.fn(call)

    def __repr__(self) -> str:
        return f'FuncRenderer({self.name!r})'


# ---------------------------------------------------------------------------
# The scene
# ---------------------------------------------------------------------------

class Scene3D:
    """A retained collection of entities, a camera and lights.

    ::

        scene = Scene3D('room')
        scene.camera = Camera3D.look_at((0, 2, 8), (0, 0, 0), fov=55)
        scene.add(Entity3D.box('floor', (0, -1, 0), (10, 0.4, 10)))
        scene.render(hr)
        scene.save('room.json')

    ``render`` resolves the camera against the surface it was handed, builds one
    :class:`DrawCall` per visible entity, and runs them through the renderers
    in order. Because the scene is data, ``to_dict`` makes it a file and
    ``load`` brings it back.
    """

    def __init__(self, name: str = 'scene', ambient: Color | None = None,
                 camera: Camera3D | None = None,
                 background: Color | None = None):
        self.name = name
        self.entities: list[Entity3D] = []
        self.lights: list[Light3D] = []
        self.renderers: list[Renderer] = [MeshRenderer()]
        # a default camera, so a fresh scene renders instead of raising; the
        # projection gets rebuilt per surface anyway
        self.camera = camera if camera is not None else Camera3D.look_at(
            (0, 2, 8), (0, 0, 0), fov=60.0)
        self.ambient = _color(ambient) if ambient is not None else Color(24, 28, 44)
        self.background = _color(background) if background is not None else None
        self.z = 0.0

    # -- collection behaviour ---------------------------------------------

    def add(self, item) -> Scene3D:
        """Add an :class:`Entity3D` or a :class:`Light3D`; returns self."""
        if isinstance(item, Light3D):
            self.lights.append(item)
        elif isinstance(item, Entity3D):
            self.entities.append(item)
        else:
            raise TypeError(
                f'expected an Entity3D or a Light3D, got {type(item).__name__}')
        return self

    def remove(self, item) -> bool:
        for collection in (self.entities, self.lights):
            if item in collection:
                collection.remove(item)
                return True
        return False

    def get(self, name: str):
        """The first entity or light called ``name``, or ``None``."""
        for collection in (self.entities, self.lights):
            for item in collection:
                if item.name == name:
                    return item
        return None

    def require(self, name: str):
        """Like :meth:`get` but raises - a typo should not read as "not there,
        leave it out" and quietly produce an empty scene."""
        found = self.get(name)
        if found is None:
            raise KeyError(f'no entity or light named {name!r} in {self.name!r}')
        return found

    def __len__(self) -> int:
        return len(self.entities)

    def __iter__(self):
        return iter(self.entities)

    def __contains__(self, item) -> bool:
        return item in self.entities or item in self.lights

    def _shown(self, entity: Entity3D) -> bool:
        """Visible, and not under a hidden ancestor.

        A hidden parent should take its children with it; otherwise turning one
        group off means hunting for every child that belonged to it.
        """
        node = entity
        while node is not None:
            if not node.visible:
                return False
            node = node.parent
        return True

    def visible_entities(self) -> list[Entity3D]:
        return [e for e in self.entities if self._shown(e)]

    def all_tags(self, entity: Entity3D) -> set:
        """``entity``'s own tags plus those it inherits from its parents."""
        tags: set = set()
        node = entity
        while node is not None:
            tags |= node.tags
            node = node.parent
        return tags

    def with_tag(self, tag: str) -> list[Entity3D]:
        """Every entity carrying ``tag``, whether its own or inherited."""
        return [e for e in self.entities if tag in self.all_tags(e)]

    # -- rendering ---------------------------------------------------------

    def render(self, surface) -> list[DrawCall]:
        """Draw every visible entity into ``surface``; returns the draw calls.

        The camera's projection is rebuilt against ``surface`` so the aspect is
        always right, whichever surface type it is handed - a terminal cell grid
        and a hi-res sub-cell grid need different ones.
        """
        if self.camera is None:
            raise ValueError(f'scene {self.name!r} has no camera')
        if self.background is not None:
            _fill(surface, self.background, self.z - 100)
        camera = self._camera_for(surface)
        calls = []
        lights = list(self.lights)
        for entity in self.visible_entities():
            call = DrawCall(entity, surface, camera.view, camera.projection,
                            lights, entity.material)
            calls.append(call)
            for renderer in self.renderers:
                renderer.draw(call)
        return calls

    def _camera_for(self, surface) -> Camera3D:
        """The scene camera with its projection rebuilt for ``surface``.

        A terminal cell grid and a hi-res sub-cell grid have different aspects,
        so a camera built for one is wrong for the other. Rebuilding here means
        a scene does not have to know which surface it is about to be drawn on.
        """
        cam = self.camera
        if cam.ortho:
            return cam
        return Camera3D(cam.eye, cam.target, up=(0, 1, 0), fov=cam.fov,
                        surface=surface, near=cam.near, far=cam.far)

    # -- serialisation -----------------------------------------------------

    def to_dict(self) -> dict:
        return {'name': self.name,
                'ambient': [self.ambient.r, self.ambient.g, self.ambient.b],
                'background': ([self.background.r, self.background.g,
                                self.background.b] if self.background else None),
                'z': self.z,
                'camera': (self.camera.to_dict() if self.camera else None),
                'lights': [light.to_dict() for light in self.lights],
                'entities': [entity.to_dict() for entity in self.entities]}

    @classmethod
    def from_dict(cls, d: dict) -> Scene3D:
        scene = cls(d.get('name', 'scene'),
                    d.get('ambient', (24, 28, 44)))
        bg = d.get('background')
        scene.background = _color(bg) if bg else None
        scene.z = d.get('z', 0.0)
        cam = d.get('camera')
        if cam:
            scene.camera = Camera3D.from_dict(cam)
        for light in d.get('lights', []):
            scene.lights.append(Light3D.from_dict(light))
        for entity in d.get('entities', []):
            scene.entities.append(Entity3D.from_dict(entity))
        return scene

    def save(self, path: str) -> str:
        """Write the scene to ``path`` as JSON; returns the path."""
        directory = os.path.dirname(os.path.abspath(path))
        if directory:
            os.makedirs(directory, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as fh:
            json.dump(self.to_dict(), fh, indent=1, sort_keys=True)
        return path

    @classmethod
    def load(cls, path: str) -> Scene3D:
        """Read a scene back from ``path``."""
        with open(path, encoding='utf-8') as fh:
            return cls.from_dict(json.load(fh))

    def __repr__(self) -> str:
        return (f'Scene3D({self.name!r}, {len(self.entities)} entities, '
                f'{len(self.lights)} lights)')


def _fill(surface, color: Color, z: float) -> None:
    """Paint a flat background across a whole surface.

    A hi-res sub-cell is a foreground, because the fold pairs it with the
    sub-cell below; a low-res cell needs the colour in its background to show
    as a solid fill.
    """
    w = getattr(surface, 'w', None) or surface.width
    h = getattr(surface, 'h', None) or surface.height
    sub_is_fg = isinstance(surface, HiResCanvas)
    for y in range(h):
        for x in range(w):
            cell = surface.buffer[y][x]
            cell.char = ' '
            cell.fg = color if sub_is_fg else None
            cell.bg = None if sub_is_fg else color
            cell.z = z

