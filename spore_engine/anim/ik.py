from __future__ import annotations
import math
from typing import Optional
from ..core.canvas import Canvas
from ..core.color import Color
from ..core.geom import Vec2


class Bone:
    __slots__ = ('length', 'angle', 'pos', 'color', 'children')
    def __init__(self, length: float, angle: float = 0, pos: Vec2 = Vec2(),
                 color: Optional[Color] = None):
        self.length = length
        self.angle = angle
        self.pos = pos
        self.color = color or Color(220, 180, 120)
        self.children: list[Bone] = []

    @property
    def end_pos(self) -> Vec2:
        return Vec2(
            self.pos.x + math.cos(self.angle) * self.length,
            self.pos.y + math.sin(self.angle) * self.length,
        )

    def add_child(self, child: Bone):
        self.children.append(child)

    def world_pos(self, parent_pos: Vec2 = Vec2(), parent_angle: float = 0) -> Vec2:
        return Vec2(
            parent_pos.x + math.cos(parent_angle + self.angle) * self.length,
            parent_pos.y + math.sin(parent_angle + self.angle) * self.length,
        )

    def world_angle(self, parent_angle: float = 0) -> float:
        return parent_angle + self.angle


class Skeleton:
    def __init__(self, root: Optional[Bone] = None):
        self.root = root or Bone(0)
        self._solve_positions: list[Vec2] = []

    def _get_chain(self, bone: Bone, chain: list[Bone], parent_angle: float = 0):
        chain.append(bone)
        for child in bone.children:
            self._get_chain(child, chain, bone.world_angle(parent_angle))

    def solve_fabrik(self, target: Vec2, tolerance: float = 0.5,
                     max_iterations: int = 20):
        chain: list[Bone] = []
        self._get_chain(self.root, chain)
        if not chain:
            return

        lengths = [b.length for b in chain]
        total_len = sum(lengths)
        if target.length() > total_len:
            for i, b in enumerate(chain):
                b.angle = math.atan2(target.y - b.pos.y, target.x - b.pos.x)
                if i < len(chain) - 1:
                    b.pos = b.end_pos
            return

        positions = [b.pos for b in chain]
        root_pos = positions[0]

        for _ in range(max_iterations):
            positions[-1] = target
            for i in range(len(positions) - 2, -1, -1):
                d = positions[i].dist(positions[i + 1])
                if d < 0.001:
                    d = 1
                ratio = lengths[i] / d
                positions[i] = Vec2(
                    positions[i + 1].x + (positions[i].x - positions[i + 1].x) * ratio,
                    positions[i + 1].y + (positions[i].y - positions[i + 1].y) * ratio,
                )

            positions[0] = root_pos
            for i in range(1, len(positions)):
                d = positions[i - 1].dist(positions[i])
                if d < 0.001:
                    d = 1
                ratio = lengths[i - 1] / d
                positions[i] = Vec2(
                    positions[i - 1].x + (positions[i].x - positions[i - 1].x) * ratio,
                    positions[i - 1].y + (positions[i].y - positions[i - 1].y) * ratio,
                )

            if positions[-1].dist(target) < tolerance:
                break

        for i, b in enumerate(chain):
            b.pos = positions[i]
            if i < len(chain) - 1:
                b.angle = math.atan2(
                    positions[i + 1].y - positions[i].y,
                    positions[i + 1].x - positions[i].x,
                )
            else:
                b.angle = chain[i - 1].angle if i > 0 else 0

        self._solve_positions = positions

    def solve_ccd(self, target: Vec2, max_iterations: int = 30):
        chain: list[Bone] = []
        self._get_chain(self.root, chain)
        if not chain:
            return

        end_effector = chain[-1].end_pos if len(chain) > 1 else chain[0].end_pos
        root_angle = chain[0].angle

        for _ in range(max_iterations):
            end_effector = chain[-1].end_pos
            if end_effector.dist(target) < 0.5:
                break
            for i in range(len(chain) - 2, -1, -1):
                to_end = end_effector - chain[i].pos
                to_target = target - chain[i].pos
                a1 = math.atan2(to_end.y, to_end.x)
                a2 = math.atan2(to_target.y, to_target.x)
                diff = a2 - a1
                if abs(diff) > math.pi:
                    diff -= 2 * math.pi * (1 if diff > 0 else -1)
                chain[i].angle += diff * 0.5

                pos = chain[0].pos
                for j in range(1, len(chain)):
                    chain[j].pos = chain[j - 1].end_pos

                end_effector = chain[-1].end_pos
                if end_effector.dist(target) < 0.5:
                    return

        self._solve_positions = [b.pos for b in chain]

    def render(self, canvas: Canvas, ox: int = 0, oy: int = 0,
               joint_char: str = '●', bone_char: str = '#',
               show_angles: bool = False):
        def _render(bone: Bone, parent_pos: Vec2, parent_angle: float):
            wpos = parent_pos
            if bone.length > 0:
                wpos = bone.world_pos(parent_pos, parent_angle)
                wangle = bone.world_angle(parent_angle)
                end_x = int(wpos.x) + ox
                end_y = int(wpos.y) + oy
                start_x = int(parent_pos.x) + ox
                start_y = int(parent_pos.y) + oy
                canvas.draw_line(start_x, start_y, end_x, end_y, bone_char, bone.color, z=1)
                canvas.set_pixel(end_x, end_y, joint_char, bone.color, z=2)
                if show_angles and bone.length > 1:
                    arc_x = int(parent_pos.x + math.cos(wangle) * bone.length * 0.5) + ox
                    arc_y = int(parent_pos.y + math.sin(wangle) * bone.length * 0.5) + oy
                    canvas.set_pixel(arc_x, arc_y, '·', Color(255, 100, 100), z=3)
            for child in bone.children:
                _render(child, wpos, parent_angle + bone.angle if bone.length > 0 else parent_angle)

        if self.root:
            _render(self.root, self.root.pos, 0)
            canvas.set_pixel(int(self.root.pos.x) + ox, int(self.root.pos.y) + oy, '◉',
                             Color(255, 100, 100), z=3)


def create_arm(base_x: float, base_y: float, segments: int = 3,
               segment_length: float = 3, color: Optional[Color] = None) -> Skeleton:
    col = color or Color(220, 180, 120)
    root = Bone(0, 0, Vec2(base_x, base_y), col)
    prev = root
    for i in range(segments):
        bone = Bone(segment_length, math.radians(-90 + i * 10), prev.end_pos, col)
        prev.add_child(bone)
        prev = bone
    return Skeleton(root)


def create_leg(base_x: float, base_y: float, segments: int = 2,
               segment_length: float = 2.5, color: Optional[Color] = None) -> Skeleton:
    col = color or Color(200, 160, 100)
    root = Bone(0, 0, Vec2(base_x, base_y), col)
    prev = root
    for i in range(segments):
        bone = Bone(segment_length, math.radians(90 + i * 5), prev.end_pos, col)
        prev.add_child(bone)
        prev = bone
    return Skeleton(root)


def create_tentacle(base_x: float, base_y: float, segments: int = 8,
                    segment_length: float = 1.5, color: Optional[Color] = None) -> Skeleton:
    col = color or Color(100, 200, 180)
    root = Bone(0, 0, Vec2(base_x, base_y), col)
    prev = root
    for i in range(segments):
        w = i / segments
        bone = Bone(segment_length * (1 - w * 0.5), math.radians(10 + i * 5), prev.end_pos,
                    col.lerp(Color(180, 255, 200), w))
        prev.add_child(bone)
        prev = bone
    return Skeleton(root)
