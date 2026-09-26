"""One camera, and the projection conventions the 3-D paths disagreed about.

Every 3-D renderer in this engine used to take a camera in its own dialect.
``engine3d`` took a ``Mat4`` view and projection. ``raytracer`` took two bare
3-tuples and a field of view in *degrees*. ``sdf`` took two ``Vec3`` and a
field of view in degrees. ``voxel`` took eight scalars - yaw, a "height" value
that was not a pitch, a step budget, a horizontal fov in *radians*. ``isometric``
took nothing at all and read mutable state off ``self.camera``.

The result was that no two of them could be driven by the same view, and the
degrees/radians split was a live bug source: ``Mat4.perspective`` documents
radians, and a caller passing degrees gets a silently wrong image rather than
an error. :class:`Camera3D` is the thing that ends that. It is a plain value
object - no drawing, no state - which produces a view and a projection that
every backend can consume, and it can be decomposed back to a position and
target for the backends that want those.

::

    cam = Camera3D.look_at((0, 2, 8), (0, 0, 0), fov=60, surface=hr)
    render_mesh_solid(hr, mesh, cam.view, cam.projection, light)
    sdf_scene.render(c, *cam.eye_and_target(), fov=cam.fov_degrees)

``fov`` is degrees everywhere, because that is what a person means by "a 60
degree lens". The conversion to the radians :class:`~spore_engine.Mat4`
wants happens once, here.
"""

from __future__ import annotations

import math

from ..core.geom import Mat4, Vec3

__all__ = ['Camera3D']


class Camera3D:
    """A perspective or orthographic camera described by where it is and what
    it is aimed at.

    Immutable in practice: :attr:`view` and :attr:`projection` are computed
    once in the constructor, and moving the camera means building a new one.
    That is deliberate - it is a value, not a scene node, so it can be shared,
    stored on an entity, and serialised.
    """

    __slots__ = ('_eye', '_projection', '_target', '_up', 'far', 'fov',
                 'near', 'ortho', 'view')

    def __init__(self, eye, target, up=(0, 1, 0), fov: float = 60.0,
                 surface=None, near: float = 0.1, far: float = 100.0,
                 ortho: bool = False, ortho_height: float | None = None):
        """Build a camera.

        :param eye: camera position, a :class:`~spore_engine.Vec3` or a 3-tuple.
        :param target: what it looks at, same accepted forms.
        :param up: roll reference. A camera looking straight up or down needs
            this to be non-parallel or :meth:`Mat4.look_at` returns identity.
        :param fov: vertical field of view in **degrees**, in ``(0, 180)``.
        :param surface: the surface this camera will render to. Its aspect
            decides the projection's x scale; without it, aspect is 1.
        :param near: near plane, must be positive.
        :param far: far plane, must be beyond ``near``.
        :param ortho: use a parallel projection instead of perspective.
        :param ortho_height: world units spanned vertically. Required for an
            orthographic camera - there is no fov to infer it from.
        """
        eye_v = Vec3(*eye) if isinstance(eye, (tuple, list)) else Vec3(eye.x, eye.y, eye.z)
        target_v = (Vec3(*target) if isinstance(target, (tuple, list))
                    else Vec3(target.x, target.y, target.z))
        up_v = Vec3(*up) if isinstance(up, (tuple, list)) else Vec3(up.x, up.y, up.z)
        if not 0.0 < fov < 180.0:
            raise ValueError(f'Camera3D fov must be in (0, 180) degrees, got {fov}')
        if near <= 0 or far <= near:
            raise ValueError(
                f'Camera3D needs 0 < near < far, got near={near}, far={far}')
        if ortho and ortho_height is None:
            raise ValueError('an orthographic Camera3D needs ortho_height')
        if ortho_height is not None and ortho_height <= 0:
            raise ValueError(
                f'ortho_height must be positive, got {ortho_height}')

        width = height = None
        if surface is not None:
            width = getattr(surface, 'w', None) or surface.width
            height = getattr(surface, 'h', None) or surface.height
        aspect = (width / height) if width and height else 1.0

        self._eye = eye_v
        self._target = target_v
        self._up = up_v
        self.fov = float(fov)
        self.near = float(near)
        self.far = float(far)
        self.ortho = bool(ortho)
        self.view = Mat4.look_at(eye_v, target_v, up_v)
        if ortho:
            half_h = ortho_height / 2.0
            half_w = half_h * aspect
            self._projection = Mat4.orthographic(-half_w, half_w, half_h, -half_h,
                                                 near, far)
        else:
            self._projection = Mat4.perspective(math.radians(fov), aspect, near, far)

    # -- convenience constructors -----------------------------------------

    @classmethod
    def look_at(cls, eye, target, **kwargs) -> Camera3D:
        return cls(eye, target, **kwargs)

    @classmethod
    def orbiting(cls, target, distance: float = 8.0, angle: float = 0.0,
                 elevation: float = 30.0, **kwargs) -> Camera3D:
        """A camera on a circular orbit, the Lissajous every 3-D demo reinvents.

        ``angle`` is degrees around the vertical axis and ``elevation`` degrees
        above the horizon, so a slow sweep is
        ``Camera3D.orbiting((0,0,0), 8, t*12, 25)``.
        """
        a = math.radians(angle)
        e = math.radians(elevation)
        return cls((target[0] + distance * math.cos(e) * math.sin(a),
                    target[1] + distance * math.sin(e),
                    target[2] + distance * math.cos(e) * math.cos(a)),
                   target, **kwargs)

    @classmethod
    def from_matrices(cls, view: Mat4, projection: Mat4, fov: float = 60.0) -> Camera3D:
        """Recover a camera from a matrix pair, for a backend that only speaks
        matrices and a backend that only speaks a position.

        The inverse of a ``look_at`` view is its own transpose when built that
        way, so the eye is the translation column and the target is one unit
        along the view's forward axis. Exact for the affine case; an
        approximate ``fov`` is *not* recovered, so pass the real one.
        """
        inv = view.inverse()
        eye = Vec3(inv[0, 3], inv[1, 3], inv[2, 3])
        forward = Vec3(-view[2, 0], -view[2, 1], -view[2, 2])
        cam = cls.__new__(cls)
        cam._eye = eye
        cam._target = Vec3(eye.x + forward.x, eye.y + forward.y, eye.z + forward.z)
        cam._up = Vec3(0, 1, 0)
        cam.fov = float(fov)
        cam.near = 0.1
        cam.far = 100.0
        cam.ortho = False
        cam.view = view
        cam._projection = projection
        return cam

    # -- accessors ---------------------------------------------------------

    @property
    def eye(self) -> Vec3:
        return self._eye

    @property
    def target(self) -> Vec3:
        return self._target

    @property
    def projection(self) -> Mat4:
        """The projection matrix, named ``projection`` rather than ``proj`` so
        it cannot be confused with the projection *operation* the renderers
        perform."""
        return self._projection

    @property
    def fov_radians(self) -> float:
        """What :meth:`Mat4.perspective` wants."""
        return math.radians(self.fov)

    def fov_degrees(self) -> float:
        """What :class:`~spore_engine.render3d.sdf.SDFScene` and
        :class:`~spore_engine.render3d.raytracer.RayScene` want."""
        return self.fov

    def eye_and_target(self) -> tuple[tuple[float, float, float],
                                      tuple[float, float, float]]:
        """The positional form the raytracer and SDF paths take, as plain
        tuples because that is literally their parameter type."""
        e = self._eye
        t = self._target
        return ((e.x, e.y, e.z), (t.x, t.y, t.z))

    def basis(self) -> tuple[Vec3, Vec3, Vec3]:
        """Orthonormal ``(right, up, forward)`` for the target.

        The raytracer and the SDF path each build this by hand from two
        positions; deriving it from the view matrix keeps the three of them
        agreeing, including under roll.
        """
        forward = self.view_forward()
        right = self._up.cross(forward).norm()
        up = forward.cross(right).norm()
        return right, up, forward

    def view_forward(self) -> Vec3:
        """The direction the camera looks, unit length.

        Falls back to ``(0, 0, -1)`` when the eye and target coincide, where
        the direction is undefined.
        """
        d = self._target - self._eye
        return d.norm() if d.length() else Vec3(0, 0, -1)

    def to_dict(self) -> dict:
        """A JSON-safe form, for :class:`Scene3D` round-trips."""
        return {'eye': [self._eye.x, self._eye.y, self._eye.z],
                'target': [self._target.x, self._target.y, self._target.z],
                'up': [self._up.x, self._up.y, self._up.z],
                'fov': self.fov, 'near': self.near, 'far': self.far,
                'ortho': self.ortho}

    @classmethod
    def from_dict(cls, d: dict) -> Camera3D:
        """Rebuild from :meth:`to_dict`.

        A file that says ``ortho`` but omits the height is a hand edit away
        from being unloadable, so derive one that frames the target rather than
        refusing to open it.
        """
        eye = Vec3(*d['eye']) if isinstance(d['eye'], (tuple, list)) else d['eye']
        target = (Vec3(*d['target']) if isinstance(d['target'], (tuple, list))
                  else d['target'])
        height = d.get('ortho_height')
        if d.get('ortho') and height is None:
            height = max(1e-3, (eye - target).length())
        return cls(d['eye'], d['target'], up=d.get('up', (0, 1, 0)),
                   fov=d.get('fov', 60.0), near=d.get('near', 0.1),
                   far=d.get('far', 100.0), ortho=d.get('ortho', False),
                   ortho_height=height)

    def aspect_for(self, surface) -> float:
        """Width over height of ``surface``, which is what a projection needs."""
        width = getattr(surface, 'w', None) or surface.width
        height = getattr(surface, 'h', None) or surface.height
        return width / height

    def __eq__(self, other) -> bool:
        if not isinstance(other, Camera3D):
            return NotImplemented
        return (self._eye == other._eye and self._target == other._target
                and self.fov == other.fov and self.view == other.view
                and self._projection == other._projection)

    def __repr__(self) -> str:
        kind = 'ortho' if self.ortho else 'perspective'
        return (f'Camera3D(eye=({self._eye.x:.1f}, {self._eye.y:.1f}, '
                f'{self._eye.z:.1f}), fov={self.fov:g}°, {kind})')
