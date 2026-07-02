from __future__ import annotations
import math
from dataclasses import dataclass


@dataclass
class Vec2:
    x: float = 0
    y: float = 0

    def __add__(self, o: Vec2) -> Vec2: return Vec2(self.x + o.x, self.y + o.y)
    def __sub__(self, o: Vec2) -> Vec2: return Vec2(self.x - o.x, self.y - o.y)
    def __mul__(self, s: float) -> Vec2: return Vec2(self.x * s, self.y * s)
    def __rmul__(self, s: float) -> Vec2: return Vec2(self.x * s, self.y * s)
    def __neg__(self) -> Vec2: return Vec2(-self.x, -self.y)
    def dot(self, o: Vec2) -> float: return self.x * o.x + self.y * o.y
    def length(self) -> float: return math.hypot(self.x, self.y)
    def norm(self) -> Vec2:
        l = self.length()
        return Vec2(self.x / l, self.y / l) if l else Vec2()
    def cross(self, o: Vec2) -> float: return self.x * o.y - self.y * o.x
    def dist(self, o: Vec2) -> float: return (self - o).length()


@dataclass
class Vec3:
    x: float = 0
    y: float = 0
    z: float = 0

    def __add__(self, o: Vec3) -> Vec3: return Vec3(self.x + o.x, self.y + o.y, self.z + o.z)
    def __sub__(self, o: Vec3) -> Vec3: return Vec3(self.x - o.x, self.y - o.y, self.z - o.z)
    def __mul__(self, s: float) -> Vec3: return Vec3(self.x * s, self.y * s, self.z * s)
    def __rmul__(self, s: float) -> Vec3: return Vec3(self.x * s, self.y * s, self.z * s)
    def __neg__(self) -> Vec3: return Vec3(-self.x, -self.y, -self.z)
    def dot(self, o: Vec3) -> float: return self.x * o.x + self.y * o.y + self.z * o.z
    def cross(self, o: Vec3) -> Vec3:
        return Vec3(self.y * o.z - self.z * o.y,
                    self.z * o.x - self.x * o.z,
                    self.x * o.y - self.y * o.x)
    def length(self) -> float: return math.sqrt(self.x * self.x + self.y * self.y + self.z * self.z)
    def norm(self) -> Vec3:
        l = self.length()
        return Vec3(self.x / l, self.y / l, self.z / l) if l else Vec3()
    def dist(self, o: Vec3) -> float: return (self - o).length()


class Mat4:
    def __init__(self, data=None):
        self.m = data or [1, 0, 0, 0,
                          0, 1, 0, 0,
                          0, 0, 1, 0,
                          0, 0, 0, 1]

    def __getitem__(self, ij):
        i, j = ij
        return self.m[i * 4 + j]

    def __setitem__(self, ij, v):
        i, j = ij
        self.m[i * 4 + j] = v

    def __mul__(self, other: Mat4) -> Mat4:
        r = Mat4()
        for i in range(4):
            for j in range(4):
                r[i, j] = sum(self[i, k] * other[k, j] for k in range(4))
        return r

    def transform(self, v: Vec3) -> Vec3:
        x = self[0, 0] * v.x + self[0, 1] * v.y + self[0, 2] * v.z + self[0, 3]
        y = self[1, 0] * v.x + self[1, 1] * v.y + self[1, 2] * v.z + self[1, 3]
        z = self[2, 0] * v.x + self[2, 1] * v.y + self[2, 2] * v.z + self[2, 3]
        w = self[3, 0] * v.x + self[3, 1] * v.y + self[3, 2] * v.z + self[3, 3]
        if w != 0:
            x, y, z = x / w, y / w, z / w
        return Vec3(x, y, z)

    @staticmethod
    def identity() -> Mat4: return Mat4()

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
    def perspective(fov: float, aspect: float, near: float, far: float) -> Mat4:
        f = 1 / math.tan(fov / 2)
        return Mat4([f / aspect, 0, 0, 0,
                     0, f, 0, 0,
                     0, 0, (far + near) / (near - far), 2 * far * near / (near - far),
                     0, 0, -1, 0])

    @staticmethod
    def look_at(eye: Vec3, target: Vec3, up: Vec3 = Vec3(0, 1, 0)):
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
        return Mat4([
            self.m[0], self.m[4], self.m[8], self.m[12],
            self.m[1], self.m[5], self.m[9], self.m[13],
            self.m[2], self.m[6], self.m[10], self.m[14],
            self.m[3], self.m[7], self.m[11], self.m[15],
        ])

    def __matmul__(self, other: Mat4) -> Mat4:
        return self.__mul__(other)

    def inverse(self) -> Mat4:
        m = self.m
        a = m[0]*m[5]*m[10]*m[15] + m[0]*m[6]*m[11]*m[13] + m[0]*m[7]*m[9]*m[14] \
          + m[1]*m[4]*m[11]*m[14] + m[1]*m[6]*m[8]*m[15] + m[1]*m[7]*m[10]*m[12] \
          + m[2]*m[4]*m[9]*m[15] + m[2]*m[5]*m[11]*m[12] + m[2]*m[7]*m[8]*m[13] \
          + m[3]*m[4]*m[10]*m[13] + m[3]*m[5]*m[8]*m[14] + m[3]*m[6]*m[9]*m[12] \
          - m[0]*m[5]*m[11]*m[14] - m[0]*m[6]*m[9]*m[15] - m[0]*m[7]*m[10]*m[13] \
          - m[1]*m[4]*m[10]*m[15] - m[1]*m[6]*m[11]*m[12] - m[1]*m[7]*m[8]*m[14] \
          - m[2]*m[4]*m[11]*m[13] - m[2]*m[5]*m[8]*m[15] - m[2]*m[7]*m[9]*m[12] \
          - m[3]*m[4]*m[9]*m[14] - m[3]*m[5]*m[10]*m[12] - m[3]*m[6]*m[8]*m[13]
        if abs(a) < 1e-12:
            return Mat4.identity()
        inv = [0] * 16
        for i in range(4):
            for j in range(4):
                sub = [
                    m[(i+1)%4 + ((j+1)%4)*4], m[(i+1)%4 + ((j+2)%4)*4], m[(i+1)%4 + ((j+3)%4)*4],
                    m[(i+2)%4 + ((j+1)%4)*4], m[(i+2)%4 + ((j+2)%4)*4], m[(i+2)%4 + ((j+3)%4)*4],
                    m[(i+3)%4 + ((j+1)%4)*4], m[(i+3)%4 + ((j+2)%4)*4], m[(i+3)%4 + ((j+3)%4)*4],
                ]
                det = sub[0]*(sub[4]*sub[8]-sub[5]*sub[7]) \
                    - sub[1]*(sub[3]*sub[8]-sub[5]*sub[6]) \
                    + sub[2]*(sub[3]*sub[7]-sub[4]*sub[6])
                inv[i + j*4] = det / a
        return Mat4(inv)
