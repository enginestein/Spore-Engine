from __future__ import annotations
import random
from collections import deque
from typing import Optional
from ..core.canvas import Canvas
from ..core.color import Color, GREEN, BLUE, RED, YELLOW, WHITE, DIM


class Maze:
    def __init__(self, width: int, height: int):
        self.w = width
        self.h = height
        self.grid = [[1] * (width * 2 + 1) for _ in range(height * 2 + 1)]
        self.solution: list[tuple[int, int]] = []
        self.generated = False

    def generate_dfs(self, seed: int = 0):
        rng = random.Random(seed)
        for y in range(self.h):
            for x in range(self.w):
                self.grid[y * 2 + 1][x * 2 + 1] = 0
        stack = [(0, 0)]
        visited = {(0, 0)}
        while stack:
            cx, cy = stack[-1]
            neighbors = []
            for dx, dy in [(2, 0), (-2, 0), (0, 2), (0, -2)]:
                nx, ny = cx + dx, cy + dy
                if 0 <= nx < self.w * 2 + 1 and 0 <= ny < self.h * 2 + 1 and (nx // 2, ny // 2) not in visited:
                    if 0 <= nx // 2 < self.w and 0 <= ny // 2 < self.h:
                        neighbors.append((nx, ny))
            if neighbors:
                nx, ny = rng.choice(neighbors)
                wx, wy = (cx + nx) // 2, (cy + ny) // 2
                self.grid[wy][wx] = 0
                self.grid[ny][nx] = 0
                stack.append((nx, ny))
                visited.add((nx // 2, ny // 2))
            else:
                stack.pop()
        self.generated = True

    def generate_prim(self, seed: int = 0):
        rng = random.Random(seed)
        for y in range(self.h):
            for x in range(self.w):
                self.grid[y * 2 + 1][x * 2 + 1] = 0
        walls = []
        self.grid[1][1] = 0
        for dx, dy in [(2, 0), (-2, 0), (0, 2), (0, -2)]:
            nx, ny = 1 + dx, 1 + dy
            if 0 < nx < self.w * 2 and 0 < ny < self.h * 2:
                walls.append((nx, ny, 1, 1))
        while walls:
            wx, wy, px, py = walls.pop(rng.randint(0, len(walls) - 1))
            cx, cy = (wx + px) // 2, (wy + py) // 2
            if 0 <= wx < self.w * 2 + 1 and 0 <= wy < self.h * 2 + 1 and self.grid[wy][wx] == 1:
                self.grid[cy][cx] = 0
                self.grid[wy][wx] = 0
                for dx, dy in [(2, 0), (-2, 0), (0, 2), (0, -2)]:
                    nx, ny = wx + dx, wy + dy
                    if 0 < nx < self.w * 2 and 0 < ny < self.h * 2 and self.grid[ny][nx] == 1:
                        walls.append((nx, ny, wx, wy))
        self.generated = True

    def solve_bfs(self, start: tuple[int, int] = (1, 1),
                  end: Optional[tuple[int, int]] = None):
        if end is None:
            end = (self.w * 2 - 1, self.h * 2 - 1)
        q = deque([start])
        parent = {start: None}
        while q:
            cx, cy = q.popleft()
            if (cx, cy) == end:
                break
            for dx, dy in [(2, 0), (-2, 0), (0, 2), (0, -2)]:
                nx, ny = cx + dx, cy + dy
                mx, my = (cx + nx) // 2, (cy + ny) // 2
                if 0 <= nx < self.w * 2 + 1 and 0 <= ny < self.h * 2 + 1:
                    if (nx, ny) not in parent and self.grid[my][mx] == 0 and self.grid[ny][nx] == 0:
                        parent[(nx, ny)] = (cx, cy)
                        q.append((nx, ny))
        path = []
        cur = end
        while cur is not None:
            path.append(cur)
            cur = parent.get(cur)
        path.reverse()
        self.solution = path
        return path

    def solve_dfs(self, start: tuple[int, int] = (1, 1),
                  end: Optional[tuple[int, int]] = None):
        if end is None:
            end = (self.w * 2 - 1, self.h * 2 - 1)
        stack = [start]
        parent = {start: None}
        visited = {start}
        found = False
        while stack and not found:
            cx, cy = stack.pop()
            if (cx, cy) == end:
                found = True
                break
            for dx, dy in [(2, 0), (-2, 0), (0, 2), (0, -2)]:
                nx, ny = cx + dx, cy + dy
                mx, my = (cx + nx) // 2, (cy + ny) // 2
                if 0 <= nx < self.w * 2 + 1 and 0 <= ny < self.h * 2 + 1:
                    if (nx, ny) not in visited and self.grid[my][mx] == 0 and self.grid[ny][nx] == 0:
                        visited.add((nx, ny))
                        parent[(nx, ny)] = (cx, cy)
                        stack.append((nx, ny))
        path = []
        cur = end
        while cur is not None:
            path.append(cur)
            cur = parent.get(cur)
        path.reverse()
        self.solution = path
        return path

    def render(self, canvas: Canvas, ox: int = 0, oy: int = 0,
               wall_color: Optional[Color] = None,
               path_color: Optional[Color] = None,
               show_solution: bool = True):
        wc = wall_color or Color(100, 150, 255)
        pc = path_color or YELLOW
        for y in range(min(len(self.grid), canvas.height - oy)):
            for x in range(min(len(self.grid[0]), canvas.width - ox)):
                cell_x, cell_y = x + ox, y + oy
                if self.grid[y][x] == 1:
                    canvas.set_pixel(cell_x, cell_y, '█', wc)
                else:
                    canvas.set_pixel(cell_x, cell_y, '·', DIM)
        if show_solution and self.solution:
            for i, (sx, sy) in enumerate(self.solution):
                if 0 <= sy < len(self.grid) and 0 <= sx < len(self.grid[0]):
                    t = i / len(self.solution)
                    c = pc.lerp(RED, t) if i > 0 else GREEN
                    canvas.set_pixel(sx + ox, sy + oy, '@', c)
            if self.solution:
                ex, ey = self.solution[-1]
                canvas.set_pixel(ex + ox, ey + oy, '★', YELLOW)
                sx, sy = self.solution[0]
                canvas.set_pixel(sx + ox, sy + oy, 'S', GREEN)
