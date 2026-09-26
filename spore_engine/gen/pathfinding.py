from __future__ import annotations
import math
import heapq
from ..core.canvas import Canvas
from ..core.color import Color, GREEN, RED, DIM


class AStar:
    def __init__(self, width: int, height: int):
        self.w = width
        self.h = height
        self.grid: list[list[float]] = [[1.0] * width for _ in range(height)]
        self.walkable: list[list[bool]] = [[True] * width for _ in range(height)]
        self.path: list[tuple[int, int]] = []
        self.visited: list[tuple[int, int]] = []

    def set_walkable(self, x: int, y: int, walkable: bool, cost: float = 1.0):
        if 0 <= x < self.w and 0 <= y < self.h:
            self.walkable[y][x] = walkable
            self.grid[y][x] = cost

    def set_obstacle(self, x: int, y: int):
        self.set_walkable(x, y, False)

    def from_tile_grid(self, tile_grid: list[list[int]],
                       walkable_values: set[int],
                       costs: dict[int, float] | None = None):
        for y in range(min(len(tile_grid), self.h)):
            for x in range(min(len(tile_grid[0]), self.w)):
                v = tile_grid[y][x]
                self.walkable[y][x] = v in walkable_values
                if costs and v in costs:
                    self.grid[y][x] = costs[v]
                else:
                    self.grid[y][x] = 1.0

    def heuristic(self, a: tuple[int, int], b: tuple[int, int]) -> float:
        return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2)

    def neighbors(self, pos: tuple[int, int], diagonals: bool = False) -> list[tuple[int, int, float]]:
        x, y = pos
        result = []
        dirs = [(0, -1, 1), (0, 1, 1), (-1, 0, 1), (1, 0, 1)]
        if diagonals:
            dirs += [(-1, -1, 1.414), (1, -1, 1.414), (-1, 1, 1.414), (1, 1, 1.414)]
        for dx, dy, base_cost in dirs:
            nx, ny = x + dx, y + dy
            if 0 <= nx < self.w and 0 <= ny < self.h and self.walkable[ny][nx]:
                cost = self.grid[ny][nx] * base_cost
                result.append((nx, ny, cost))
        return result

    def find_path(self, start: tuple[int, int], end: tuple[int, int],
                  diagonals: bool = False, max_steps: int = 5000) -> list[tuple[int, int]]:
        if not (0 <= start[0] < self.w and 0 <= start[1] < self.h):
            return []
        if not (0 <= end[0] < self.w and 0 <= end[1] < self.h):
            return []
        if not self.walkable[start[1]][start[0]]:
            return []
        if not self.walkable[end[1]][end[0]]:
            return []

        open_set = [(0, start)]
        came_from: dict[tuple[int, int], tuple[int, int] | None] = {start: None}
        g_score: dict[tuple[int, int], float] = {start: 0}
        f_score: dict[tuple[int, int], float] = {start: self.heuristic(start, end)}
        visited_order: list[tuple[int, int]] = []
        steps = 0

        while open_set and steps < max_steps:
            steps += 1
            _, current = heapq.heappop(open_set)
            if current in visited_order:
                continue
            visited_order.append(current)

            if current == end:
                self.visited = visited_order
                self.path = self._reconstruct(came_from, current)
                return self.path

            for nx, ny, move_cost in self.neighbors(current, diagonals):
                neighbor = (nx, ny)
                tentative_g = g_score.get(current, float('inf')) + move_cost
                if tentative_g < g_score.get(neighbor, float('inf')):
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g
                    f = tentative_g + self.heuristic(neighbor, end)
                    f_score[neighbor] = f
                    heapq.heappush(open_set, (f, neighbor))

        self.visited = visited_order
        self.path = []
        return []

    def _reconstruct(self, came_from: dict, current: tuple[int, int]) -> list[tuple[int, int]]:
        path = [current]
        while current in came_from and came_from[current] is not None:
            current = came_from[current]
            path.append(current)
        path.reverse()
        return path

    def render(self, canvas: Canvas, ox: int = 0, oy: int = 0,
               show_visited: bool = True, show_path: bool = True):
        for y in range(self.h):
            for x in range(self.w):
                cx, cy = x + ox, y + oy
                if cx < 0 or cx >= canvas.w or cy < 0 or cy >= canvas.h:
                    continue
                if not self.walkable[y][x]:
                    canvas.set_pixel(cx, cy, '#', Color(80, 80, 100), z=1)
                else:
                    canvas.set_pixel(cx, cy, '·', DIM, z=0)

        if show_visited and self.visited:
            for i, (vx, vy) in enumerate(self.visited):
                cx, cy = vx + ox, vy + oy
                t = i / max(1, len(self.visited))
                c = Color(50, int(100 + 100 * (1 - t)), 50)
                px = canvas.get_pixel(cx, cy)
                if px and px.z <= 1:
                    canvas.set_pixel(cx, cy, '·', c, z=1)

        if show_path and self.path:
            for i, (px, py) in enumerate(self.path):
                cx, cy = px + ox, py + oy
                t = i / max(1, len(self.path))
                c = GREEN.lerp(RED, t)
                canvas.set_pixel(cx, cy, '@' if i > 0 and i < len(self.path) - 1 else 'S' if i == 0 else 'E', c, z=2)

    @staticmethod
    def from_maze_walls(width: int, height: int,
                        wall_grid: list[list[int]]) -> AStar:
        astar = AStar(width, height)
        for y in range(min(height, len(wall_grid))):
            for x in range(min(width, len(wall_grid[0]))):
                astar.set_walkable(x, y, wall_grid[y][x] == 0)
        return astar
