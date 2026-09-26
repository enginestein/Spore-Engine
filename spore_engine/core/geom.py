from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Union

__all__ = ['Mat4', 'Vec2', 'Vec3']

Scalar = Union[int, float]  # noqa: UP007  (runtime alias, must stay Union)


@dataclass
class Vec2:
    """A mutable 2D vector with value equality.

    Mutable because the physics and steering integrators update positions and
    velocities in place; equal by value because scene code compares points.
    Hashable by value, so a vector can key a dict - but because it is mutable
    you must not change ``x``/``y`` while it sits inside a set or dict.

    This is the engine's *only* 2D vector. ``sim.physics`` used to carry a
    second, subtly different one (hashable, with ``__truediv__`` and
    ``length_sq``), so a value satisfied one module's type hints and not the
    other's. This implementation is a superset of both.
    """

    x: float = 0
    y: float = 0

    def __add__(self, o: Vec2) -> Vec2: return Vec2(self.x + o.x, self.y + o.y)
    def __sub__(self, o: Vec2) -> Vec2: return Vec2(self.x - o.x, self.y - o.y)
    def __mul__(self, s: Scalar) -> Vec2: return Vec2(self.x * s, self.y * s)
    def __rmul__(self, s: Scalar) -> Vec2: return Vec2(self.x * s, self.y * s)
    def __neg__(self) -> Vec2: return Vec2(-self.x, -self.y)

    def __truediv__(self, s: Scalar) -> Vec2:
        if s == 0:
            raise ZeroDivisionError('Vec2 division by zero')
        return Vec2(self.x / s, self.y / s)

    def __hash__(self) -> int:
        return hash((self.x, self.y))

    def dot(self, o: Vec2) -> float: return self.x * o.x + self.y * o.y
    def length(self) -> float: return math.hypot(self.x, self.y)
    def length_sq(self) -> float: return self.x * self.x + self.y * self.y
    def norm(self) -> Vec2:
        l = self.length()
        return Vec2(self.x / l, self.y / l) if l else Vec2()
    def cross(self, o: Vec2) -> float: return self.x * o.y - self.y * o.x
    def dist(self, o: Vec2) -> float: return (self - o).length()
    def copy(self) -> Vec2: return Vec2(self.x, self.y)


@dataclass
class Vec3:
    """A mutable 3D vector with value equality."""

    x: float = 0
    y: float = 0
    z: float = 0

    def __add__(self, o: Vec3) -> Vec3: return Vec3(self.x + o.x, self.y + o.y, self.z + o.z)
    def __sub__(self, o: Vec3) -> Vec3: return Vec3(self.x - o.x, self.y - o.y, self.z - o.z)
    def __mul__(self, s: Scalar) -> Vec3: return Vec3(self.x * s, self.y * s, self.z * s)
    def __rmul__(self, s: Scalar) -> Vec3: return Vec3(self.x * s, self.y * s, self.z * s)
    def __neg__(self) -> Vec3: return Vec3(-self.x, -self.y, -self.z)
    def __hash__(self) -> int: return hash((self.x, self.y, self.z))
    def dot(self, o: Vec3) -> float: return self.x * o.x + self.y * o.y + self.z * o.z
    def cross(self, o: Vec3) -> Vec3:
        return Vec3(self.y * o.z - self.z * o.y,
                    self.z * o.x - self.x * o.z,
                    self.x * o.y - self.y * o.x)
    def length(self) -> float: return math.sqrt(self.x * self.x + self.y * self.y + self.z * self.z)
    def length_sq(self) -> float: return self.x * self.x + self.y * self.y + self.z * self.z
    def norm(self) -> Vec3:
        l = self.length()
        return Vec3(self.x / l, self.y / l, self.z / l) if l else Vec3()
    def dist(self, o: Vec3) -> float: return (self - o).length()
    def copy(self) -> Vec3: return Vec3(self.x, self.y, self.z)


class Mat4:
    """A 4x4 matrix stored as a flat 16-element row-major list.

    Index with ``m[i, j]``. Most scenes only need the static constructors and
    :meth:`transform`.
    """

    def __init__(self, data: list | None = None):
        if data is None:
            data = [1, 0, 0, 0,
                    0, 1, 0, 0,
                    0, 0, 1, 0,
                    0, 0, 0, 1]
        elif len(data) != 16:
            # An empty list used to silently produce the identity matrix via
            # `data or [...]`, hiding the caller's mistake.
            raise ValueError(f'Mat4 needs exactly 16 elements, got {len(data)}')
        self.m = list(data)

    def __getitem__(self, ij):
        i, j = ij
        return self.m[i * 4 + j]

    def __setitem__(self, ij, v):
        i, j = ij
        self.m[i * 4 + j] = v

    def __eq__(self, other) -> bool:
        if not isinstance(other, Mat4):
            return NotImplemented
        return self.m == other.m

    def __repr__(self) -> str:
        rows = [', '.join(f'{v:g}' for v in self.m[i * 4:(i + 1) * 4])
                for i in range(4)]
        return 'Mat4([' + '; '.join(rows) + '])'

    def __mul__(self, other: Mat4) -> Mat4:
        r = Mat4()
        for i in range(4):
            for j in range(4):
                r[i, j] = sum(self[i, k] * other[k, j] for k in range(4))
        return r

    def transform(self, v: Vec3) -> Vec3:
        """Apply this matrix to a point, dividing through by w.

        The w is discarded, which is right for a screen position but loses
        information a renderer needs. Use :meth:`transform4` when you need
        perspective-correct interpolation, or :meth:`transform_vector` for a
        direction.
        """
        x, y, z, w = self.transform4(v)
        if w != 0:
            x, y, z = x / w, y / w, z / w
        return Vec3(x, y, z)

    def transform4(self, v: Vec3) -> tuple[float, float, float, float]:
        """Apply this matrix to a point and return ``(x, y, z, w)`` undivided.

        Two things need the w that :meth:`transform` throws away. A raytracer
        generating primary rays from a projection has to divide by the
        per-vertex w itself, because each pixel is a different point on the
        image plane. And a rasterizer interpolating depth across a triangle is
        only correct under perspective if it interpolates ``z/w`` and ``1/w``
        separately - the rasterizer in :mod:`spore_engine.render3d.engine3d` is
        handed post-divide z per vertex and cannot recover the w it needs.
        """
        return (self[0, 0] * v.x + self[0, 1] * v.y + self[0, 2] * v.z + self[0, 3],
                self[1, 0] * v.x + self[1, 1] * v.y + self[1, 2] * v.z + self[1, 3],
                self[2, 0] * v.x + self[2, 1] * v.y + self[2, 2] * v.z + self[2, 3],
                self[3, 0] * v.x + self[3, 1] * v.y + self[3, 2] * v.z + self[3, 3])

    def transform_vector(self, v: Vec3) -> Vec3:
        """Apply the rotation/scale part only, ignoring translation.

        This is how a direction moves - a light vector, a camera basis axis -
        as opposed to a position. Feeding a *point* to this quietly drops its
        offset, which is the bug that made ``engine3d`` hand-extract its view
        direction out of ``view_mat[2, 0..2]`` instead.
        """
        return Vec3(self[0, 0] * v.x + self[0, 1] * v.y + self[0, 2] * v.z,
                    self[1, 0] * v.x + self[1, 1] * v.y + self[1, 2] * v.z,
                    self[2, 0] * v.x + self[2, 1] * v.y + self[2, 2] * v.z)

    def normal_matrix(self) -> Mat4:
        """The inverse-transpose of the upper 3x3, for transforming normals.

        Under a non-uniform scale a surface normal does not transform like a
        direction, so shading with ``transform_vector`` gives the wrong result.
        Returns the identity when the matrix is singular, matching
        :meth:`inverse`.
        """
        a = [[self[i, j] for j in range(3)] for i in range(3)]
        det = (a[0][0] * (a[1][1] * a[2][2] - a[1][2] * a[2][1])
               - a[0][1] * (a[1][0] * a[2][2] - a[1][2] * a[2][0])
               + a[0][2] * (a[1][0] * a[2][1] - a[1][1] * a[2][0]))
        if det == 0:
            return Mat4()
        inv = [[0.0] * 3 for _ in range(3)]
        for i in range(3):
            for j in range(3):
                r0, r1 = (i + 1) % 3, (i + 2) % 3
                c0, c1 = (j + 1) % 3, (j + 2) % 3
                inv[j][i] = (a[r0][c0] * a[r1][c1] - a[r0][c1] * a[r1][c0]) / det
        out = Mat4()
        for i in range(3):
            for j in range(3):
                out[i, j] = inv[j][i]      # transpose: for a rotation this
        return out                        # recovers the rotation, not R^T

    @staticmethod
    def identity() -> Mat4:
        """The identity matrix."""
        return Mat4()

    @staticmethod
    def translate(x: float, y: float, z: float) -> Mat4:
        return Mat4([1, 0, 0, x, 0, 1, 0, y, 0, 0, 1, z, 0, 0, 0, 1])

    @staticmethod
    def scale(x: float, y: float, z: float) -> Mat4:
        return Mat4([x, 0, 0, 0, 0, y, 0, 0, 0, 0, z, 0, 0, 0, 0, 1])

    @staticmethod
    def rotate_x(a: float) -> Mat4:
        c = math.cos(a); s = math.sin(a)
        return Mat4([1, 0, 0, 0, 0, c, -s, 0, 0, s, c, 0, 0, 0, 0, 1])

    @staticmethod
    def rotate_y(a: float) -> Mat4:
        c = math.cos(a); s = math.sin(a)
        return Mat4([c, 0, s, 0, 0, 1, 0, 0, -s, 0, c, 0, 0, 0, 0, 1])

    @staticmethod
    def rotate_z(a: float) -> Mat4:
        c = math.cos(a); s = math.sin(a)
        return Mat4([c, -s, 0, 0, s, c, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1])

    @staticmethod
    def orthographic(left: float, right: float, top: float, bottom: float,
                     near: float, far: float) -> Mat4:
        """A parallel projection.

        The engine's five 3-D paths had no orthographic option at all, so an
        isometric or technical view had to fake one by picking a very narrow
        perspective fov. Distances map linearly to depth here, which is also
        what makes an axis-aligned sprite grid read correctly under it.
        """
        if right == left or top == bottom:
            raise ValueError(
                f'orthographic needs a non-degenerate box, got '
                f'left={left} right={right} top={top} bottom={bottom}')
        if near == far:
            raise ValueError(f'orthographic needs near != far, got {near}')
        return Mat4([2 / (right - left), 0, 0, -(right + left) / (right - left),
                     0, 2 / (top - bottom), 0, -(top + bottom) / (top - bottom),
                     0, 0, -2 / (far - near), -(far + near) / (far - near),
                     0, 0, 0, 1])

    @staticmethod
    def perspective(fov: float, aspect: float, near: float, far: float) -> Mat4:
        """A perspective projection.

        ``fov`` is the vertical field of view in radians and must be in
        ``(0, pi)``; ``aspect`` must be positive; ``near``/``far`` must satisfy
        ``0 < near < far``. Violating these used to raise ``ZeroDivisionError``
        from inside the trigonometry.
        """
        if not 0 < fov < math.pi:
            raise ValueError(f'perspective fov must be in (0, pi), got {fov}')
        if aspect <= 0:
            raise ValueError(
                f'perspective aspect must be positive, got {aspect}')
        if not 0 < near < far:
            raise ValueError(
                f'perspective needs 0 < near < far, got near={near}, far={far}')
        f = 1 / math.tan(fov / 2)
        return Mat4([f / aspect, 0, 0, 0,
                     0, f, 0, 0,
                     0, 0, (far + near) / (near - far), 2 * far * near / (near - far),
                     0, 0, -1, 0])

    @staticmethod
    def look_at(eye: Vec3, target: Vec3, up: Vec3 | None = None) -> Mat4:
        """A view matrix looking from ``eye`` towards ``target``."""
        if up is None:
            up = Vec3(0, 1, 0)
        f = (target - eye).norm()
        if f.length() < 1e-8:
            return Mat4.identity()
        s = f.cross(up).norm()
        if s.length() < 1e-8:
            up = Vec3(0, 0, 1) if abs(up.y - 1) < 1e-8 else Vec3(0, 1, 0)
            s = f.cross(up).norm()
        u = s.cross(f)
        return Mat4([s.x, s.y, s.z, -s.dot(eye),
                     u.x, u.y, u.z, -u.dot(eye),
                     -f.x, -f.y, -f.z, f.dot(eye),
                     0, 0, 0, 1])

    def transpose(self) -> Mat4:
        """The transpose."""
        return Mat4([
            self.m[0], self.m[4], self.m[8], self.m[12],
            self.m[1], self.m[5], self.m[9], self.m[13],
            self.m[2], self.m[6], self.m[10], self.m[14],
            self.m[3], self.m[7], self.m[11], self.m[15],
        ])

    def __matmul__(self, other: Mat4) -> Mat4:
        return self.__mul__(other)

    def inverse(self) -> Mat4:
        """The inverse, or the identity if this matrix is singular.

        A singular matrix is not an error - it is the normal result for a
        degenerate transform, and identity is the safe fallback.

        Implemented as Gauss-Jordan elimination with partial pivoting rather
        than the cofactor expansion, because the storage is row-major and the
        cofactor form has to transpose its output. Getting that index wrong
        returns a plausible-looking matrix that is not an inverse at all, which
        is invisible until a projected point lands in the wrong place.
        """
        a = [list(self.m[r * 4:(r + 1) * 4]) + [1.0 if i == r else 0.0
                                                 for i in range(4)]
             for r in range(4)]
        for col in range(4):
            # Partial pivoting: find the largest magnitude pivot in this column.
            pivot = max(range(col, 4), key=lambda r: abs(a[r][col]))
            if abs(a[pivot][col]) < 1e-12:
                return Mat4.identity()   # singular
            a[col], a[pivot] = a[pivot], a[col]
            p = a[col][col]
            a[col] = [v / p for v in a[col]]
            for r in range(4):
                if r == col:
                    continue
                f = a[r][col]
                if f:
                    a[r] = [v - f * w for v, w in zip(a[r], a[col], strict=False)]
        return Mat4([a[r][4 + c] for r in range(4) for c in range(4)])

