from __future__ import annotations
import math
import random
from typing import Optional
from ..core.canvas import Canvas
from ..core.color import Color


SHADE = ' .:-=+*#%@'


class GameOfLife:
    def __init__(self, width: int, height: int):
        self.w = width
        self.h = height
        self.grid = [[0] * width for _ in range(height)]
        self.buffer = [[0] * width for _ in range(height)]

    def randomize(self, density: float = 0.3):
        for y in range(self.h):
            for x in range(self.w):
                self.grid[y][x] = 1 if random.random() < density else 0

    def set_pattern(self, x: int, y: int, pattern: list[str]):
        for py, row in enumerate(pattern):
            for px, ch in enumerate(row):
                gy, gx = y + py, x + px
                if 0 <= gy < self.h and 0 <= gx < self.w:
                    self.grid[gy][gx] = 1 if ch in '@#' else 0

    def step(self):
        for y in range(self.h):
            for x in range(self.w):
                neighbors = 0
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        if dx == 0 and dy == 0:
                            continue
                        ny, nx = (y + dy) % self.h, (x + dx) % self.w
                        neighbors += self.grid[ny][nx]
                cell = self.grid[y][x]
                if cell and (neighbors < 2 or neighbors > 3):
                    self.buffer[y][x] = 0
                elif not cell and neighbors == 3:
                    self.buffer[y][x] = 1
                else:
                    self.buffer[y][x] = cell
        self.grid, self.buffer = self.buffer, self.grid

    def render(self, canvas: Canvas, ox: int = 0, oy: int = 0,
               fg_alive: Optional[Color] = None, fg_dead: Optional[Color] = None):
        alive = fg_alive or Color(100, 255, 100)
        dead = fg_dead or Color(20, 40, 20)
        for y in range(min(self.h, canvas.height - oy)):
            for x in range(min(self.w, canvas.width - ox)):
                if self.grid[y][x]:
                    canvas.set_pixel(x + ox, y + oy, '@', alive)
                elif dead:
                    canvas.set_pixel(x + ox, y + oy, '·', dead)


PATTERNS = {
    'glider': ["@#", "#@", " @@"],
    'blinker': ["@@@"],
    'toad': [" @@@", "@@@ "],
    'beacon': ["@@", "@@", " @@", " @@",],
    'pulsar': [
        "  ###   ###  ",
        "            ",
        "#  #  #  #",
        "#  #  #  #",
        "#  #  #  #",
        "  ###   ###  ",
        "            ",
        "  ###   ###  ",
        "#  #  #  #",
        "#  #  #  #",
        "#  #  #  #",
        "            ",
        "  ###   ###  ",
    ],
    'glider_gun': [
        "                        #            ",
        "                      # #            ",
        "            ##      ##            ## ",
        "           #   #    ##            ## ",
        "##        #     #   ##               ",
        "##        #   # ##    # #            ",
        "          #     #       #            ",
        "           #   #                     ",
        "            ##                       ",
    ],
    'spaceship': [
        " #@",
        "#  ",
        "#  ",
        " ##",
    ],
    'r_pentomino': [" @@", "@@ ", " @ "],
}


class Automata1D:
    def __init__(self, width: int, rule: int = 30):
        self.w = width
        self.rule = rule
        self.rule_bits = [(rule >> i) & 1 for i in range(8)]
        self.row = [0] * width
        self.row[width // 2] = 1
        self.current_row = 0

    def step(self) -> list[int]:
        new_row = [0] * self.w
        for i in range(self.w):
            left = self.row[i - 1] if i > 0 else self.row[self.w - 1]
            center = self.row[i]
            right = self.row[(i + 1) % self.w]
            idx = (left << 2) | (center << 1) | right
            new_row[i] = self.rule_bits[idx]
        self.row = new_row
        self.current_row += 1
        return self.row

    def render(self, canvas: Canvas, ox: int = 0, oy: int = 0,
               rows: int = 0, fg: Optional[Color] = None, t: float = 0):
        c = fg or Color(100, 200, 255)
        for r in range(rows):
            row_data = self.row if r == 0 else (self.step() if self.current_row > 0 else self.row)
            for x in range(min(self.w, canvas.width - ox)):
                if row_data[x]:
                    hue = (x * 0.01 + r * 0.02 + t * 0.05) % 1.0
                    canvas.set_pixel(x + ox, r + oy, '@', Color.from_hsv(hue, 0.8, 1.0))


class WireWorld:
    def __init__(self, width: int, height: int):
        self.w = width
        self.h = height
        self.grid = [[0] * width for _ in range(height)]
        self.buffer = [[0] * width for _ in range(height)]

    def set(self, x: int, y: int, val: int):
        if 0 <= x < self.w and 0 <= y < self.h:
            self.grid[y][x] = val

    def step(self):
        for y in range(self.h):
            for x in range(self.w):
                cell = self.grid[y][x]
                if cell == 1:
                    self.buffer[y][x] = 2
                elif cell == 2:
                    self.buffer[y][x] = 3
                elif cell == 3:
                    self.buffer[y][x] = 0
                elif cell == 0:
                    heads = 0
                    for dy in (-1, 0, 1):
                        for dx in (-1, 0, 1):
                            if dx == 0 and dy == 0:
                                continue
                            ny, nx = (y + dy) % self.h, (x + dx) % self.w
                            if self.grid[ny][nx] == 1:
                                heads += 1
                    self.buffer[y][x] = 1 if (heads == 1 or heads == 2) else 0
        self.grid, self.buffer = self.buffer, self.grid

    def render(self, canvas: Canvas, ox: int = 0, oy: int = 0):
        colors = [Color(20, 20, 20), Color(0, 0, 255), Color(255, 200, 0), Color(200, 100, 0)]
        chars = [' ', '█', '▓', '▒']
        for y in range(min(self.h, canvas.height - oy)):
            for x in range(min(self.w, canvas.width - ox)):
                v = self.grid[y][x]
                canvas.set_pixel(x + ox, y + oy, chars[v], colors[v])


class LangtonsAnt:
    def __init__(self, width: int, height: int):
        self.w = width
        self.h = height
        self.grid = [[0] * width for _ in range(height)]
        self.ax, self.ay = width // 2, height // 2
        self.dir = 0
        self.dirs = [(0, -1), (1, 0), (0, 1), (-1, 0)]

    def step(self):
        cell = self.grid[self.ay][self.ax]
        self.grid[self.ay][self.ax] = 1 - cell
        self.dir = (self.dir + (1 if cell == 0 else -1)) % 4
        dx, dy = self.dirs[self.dir]
        self.ax = (self.ax + dx) % self.w
        self.ay = (self.ay + dy) % self.h

    def render(self, canvas: Canvas, ox: int = 0, oy: int = 0, t: float = 0):
        for y in range(min(self.h, canvas.height - oy)):
            for x in range(min(self.w, canvas.width - ox)):
                v = self.grid[y][x]
                if v:
                    h = (x * 0.01 + y * 0.01 + t * 0.02) % 1.0
                    canvas.set_pixel(x + ox, y + oy, '#', Color.from_hsv(h, 0.8, 0.8))
                else:
                    canvas.set_pixel(x + ox, y + oy, '·', Color(40, 40, 40))
        canvas.set_pixel(self.ax + ox, self.ay + oy, '@', Color(255, 255, 100))


class ReactionDiffusion:
    def __init__(self, width: int, height: int,
                 feed: float = 0.055, kill: float = 0.062,
                 diff_u: float = 0.16, diff_v: float = 0.08):
        self.w = width
        self.h = height
        self.feed = feed
        self.kill = kill
        self.diff_u = diff_u
        self.diff_v = diff_v
        self.dt = 0.5
        self.U = [[1.0] * width for _ in range(height)]
        self.V = [[0.0] * width for _ in range(height)]
        self._seed()

    def _seed(self):
        cx, cy = self.w // 2, self.h // 2
        r = min(self.w, self.h) // 10
        for y in range(cy - r, cy + r):
            for x in range(cx - r, cx + r):
                if (x - cx) ** 2 + (y - cy) ** 2 < r * r:
                    if 0 <= x < self.w and 0 <= y < self.h:
                        self.V[y][x] = 0.8

    def _seed_random(self, density: float = 0.05):
        for y in range(self.h):
            for x in range(self.w):
                if random.random() < density:
                    self.V[y][x] = 1.0

    def set_params(self, feed: float, kill: float):
        self.feed = feed
        self.kill = kill

    def step(self):
        U, V = self.U, self.V
        w, h = self.w, self.h
        du, dv = self.diff_u, self.diff_v
        feed, kill = self.feed, self.kill
        for y in range(1, h - 1):
            for x in range(1, w - 1):
                u = U[y][x]
                v = V[y][x]
                lap_u = (U[y - 1][x] + U[y + 1][x] + U[y][x - 1] + U[y][x + 1] - 4 * u) * 0.2
                lap_v = (V[y - 1][x] + V[y + 1][x] + V[y][x - 1] + V[y][x + 1] - 4 * v) * 0.2
                uvv = u * v * v
                U[y][x] += (du * lap_u - uvv + feed * (1 - u)) * self.dt
                V[y][x] += (dv * lap_v + uvv - (feed + kill) * v) * self.dt

    def render(self, canvas: Canvas, ox: int = 0, oy: int = 0, t: float = 0):
        for y in range(min(self.h, canvas.height - oy)):
            for x in range(min(self.w, canvas.width - ox)):
                v = self.V[y][x]
                v = max(0, min(1, v))
                hue = (v * 0.6 + t * 0.02) % 1.0
                sat = 0.5 + v * 0.5
                val = 0.3 + v * 0.7
                color = Color.from_hsv(hue, sat, val)
                ci = int(v * 9)
                canvas.set_pixel(x + ox, y + oy, SHADE[ci], color)


GRAY_SCOTT_PARAMS = {
    'coral': (0.0545, 0.062),
    'spots': (0.030, 0.062),
    'stripes': (0.035, 0.065),
    'mitosis': (0.036, 0.064),
    'spirals': (0.020, 0.055),
    'worms': (0.078, 0.061),
    'maze': (0.029, 0.057),
    'waves': (0.014, 0.055),
}
