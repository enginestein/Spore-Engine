from __future__ import annotations
import math
import random
from typing import Optional
from ..core.canvas import Canvas
from ..core.color import Color


class LSystem:
    def __init__(self, axiom: str, rules: dict[str, str], angle: float = 25,
                 iterations: int = 4, start_angle: float = -90):
        self.axiom = axiom
        self.rules = rules
        self.angle = math.radians(angle)
        self.iterations = iterations
        self.start_angle = math.radians(start_angle)
        self.sentence = axiom

    def generate(self, iterations: Optional[int] = None) -> str:
        n = iterations if iterations is not None else self.iterations
        s = self.axiom
        for _ in range(n):
            s = ''.join(self.rules.get(c, c) for c in s)
        self.sentence = s
        return s

    def render(self, canvas: Canvas, x: float = 0, y: float = 0,
               length: float = 3, t: float = 0,
               color: Optional[Color] = None,
               thickness: int = 1, leaf_char: str = '*',
               stochastic: bool = False):
        col = color or Color(100, 200, 100)
        stack: list[tuple[float, float, float]] = []
        cx, cy = x, y
        angle = self.start_angle
        saved_sentence = self.sentence

        if stochastic:
            saved_sentence = ''.join(self.rules.get(c, c) if random.random() < 0.9 else c for c in saved_sentence)

        i = 0
        while i < len(saved_sentence):
            c = saved_sentence[i]
            if c == 'F' or c == 'G':
                ex = cx + math.cos(angle) * length
                ey = cy + math.sin(angle) * length
                leaf = (c == 'G' or (c == 'F' and random.random() < 0.02))
                if leaf:
                    lc = Color.from_hsv((t * 0.1 + i * 0.001) % 1.0, 0.8, 0.9)
                    canvas.set_pixel(round(ex), round(ey), leaf_char, lc)
                else:
                    depth = max(0, 1 - abs(ex - x) * 0.01 - abs(ey - y) * 0.01)
                    branch_color = col.lerp(Color(140, 100, 60), depth * 0.3)
                    canvas.draw_line(round(cx), round(cy), round(ex), round(ey),
                                     '#' if thickness > 1 else '#',
                                     branch_color)
                cx, cy = ex, ey
            elif c == '+':
                angle += self.angle
            elif c == '-':
                angle -= self.angle
            elif c == '[':
                stack.append((cx, cy, angle))
            elif c == ']':
                if stack:
                    cx, cy, angle = stack.pop()
            elif c == '|':
                angle += math.pi
            i += 1


LSYSTEMS = {
    'tree1': LSystem('F', {'F': 'FF+[+F-F-F]-[-F+F+F]'}, 22.5, 4, -90),
    'tree2': LSystem('F', {'F': 'F[+F]F[-F]F'}, 25.7, 5, -90),
    'tree3': LSystem('F', {'F': 'F[+F]F[-F][F]'}, 20, 5, -90),
    'plant': LSystem('X', {'X': 'F[+X]F[-X]+X', 'F': 'FF'}, 20, 6, -90),
    'sierpinski': LSystem('F-G-G', {'F': 'F-G+F+G-F', 'G': 'GG'}, 120, 4, 0),
    'dragon': LSystem('FX', {'X': 'X+YF+', 'Y': '-FX-Y'}, 90, 10, 0),
    'koch': LSystem('F', {'F': 'F+F-F-F+F'}, 90, 4, 0),
    'hilbert': LSystem('A', {'A': '-BF+AFA+FB-', 'B': '+AF-BFB-FA+'}, 90, 4, 0),
    'bush': LSystem('F', {'F': '-F+F-F+F+F-F-F+F'}, 90, 3, 0),
    'weed': LSystem('X', {'X': 'F[-X][X]F[+X]', 'F': 'FF'}, 25, 5, -90),
}
