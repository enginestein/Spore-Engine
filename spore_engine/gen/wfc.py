from __future__ import annotations
import math, random
from typing import Optional
from ..core.canvas import Canvas
from ..core.color import Color, DIM


SHADE = ' .:-=+*#%@'


class WFCTile:
    def __init__(self, char: str, fg: Optional[Color] = None, bg: Optional[Color] = None, name: str = ''):
        self.char = char
        self.fg = fg
        self.bg = bg
        self.name = name or char
        self.edges: dict[str, str] = {}  # direction -> edge pattern string
        self.probability = 1.0

    def copy(self) -> WFCTile:
        t = WFCTile(self.char, self.fg, self.bg, self.name)
        t.edges = self.edges.copy()
        t.probability = self.probability
        return t


class WFC:
    def __init__(self, width: int, height: int):
        self.w = width
        self.h = height
        self.tiles: list[WFCTile] = []
        self.tile_map: dict[str, int] = {}
        self.grid: list[list[list[int]]] = []  # superposition per cell
        self.collapsed: list[list[bool]] = []
        self.output: list[list[Optional[WFCTile]]] = []
        self._rng = random.Random()

    def add_tile(self, tile: WFCTile) -> int:
        idx = len(self.tiles)
        self.tiles.append(tile)
        self.tile_map[tile.name] = idx
        return idx

    def add_tile_from_sample(self, char: str, fg: Optional[Color] = None,
                              bg: Optional[Color] = None, name: str = '',
                              north: str = '', east: str = '', south: str = '',
                              west: str = '') -> int:
        t = WFCTile(char, fg, bg, name or char)
        if north: t.edges['n'] = north
        if east: t.edges['e'] = east
        if south: t.edges['s'] = south
        if west: t.edges['w'] = west
        return self.add_tile(t)

    def _valid_neighbor(self, tile_idx: int, direction: str, other_idx: int) -> bool:
        t = self.tiles[tile_idx]
        o = self.tiles[other_idx]
        edge_a = t.edges.get(direction, '')
        opp = {'n': 's', 's': 'n', 'e': 'w', 'w': 'e'}
        edge_b = o.edges.get(opp.get(direction, ''), '')
        if not edge_a or not edge_b:
            return True
        return edge_a == edge_b

    def reset(self, seed: int = 0):
        self._rng = random.Random(seed)
        self.grid = [[list(range(len(self.tiles))) for _ in range(self.w)] for _ in range(self.h)]
        self.collapsed = [[False] * self.w for _ in range(self.h)]
        self.output = [[None] * self.w for _ in range(self.h)]

    def _entropy(self, x: int, y: int) -> float:
        opts = self.grid[y][x]
        total = sum(self.tiles[i].probability for i in opts)
        if total <= 0:
            return 1e9
        e = -sum((self.tiles[i].probability / total) *
                 math.log(self.tiles[i].probability / total + 1e-10)
                 for i in opts)
        noise = self._rng.random() * 1e-6
        return e + noise

    def _lowest_entropy(self) -> tuple[int, int]:
        best = 1e9
        best_pos = (-1, -1)
        for y in range(self.h):
            for x in range(self.w):
                if not self.collapsed[y][x]:
                    e = self._entropy(x, y)
                    if e < best:
                        best = e
                        best_pos = (x, y)
        return best_pos

    def _observe(self, x: int, y: int):
        opts = self.grid[y][x]
        if not opts:
            return
        weights = [self.tiles[i].probability for i in opts]
        total = sum(weights)
        if total <= 0:
            chosen = self._rng.choice(opts)
        else:
            r = self._rng.random() * total
            cumulative = 0
            chosen = opts[0]
            for i, w in zip(opts, weights):
                cumulative += w
                if r <= cumulative:
                    chosen = i
                    break
        self.grid[y][x] = [chosen]
        self.collapsed[y][x] = True
        self.output[y][x] = self.tiles[chosen]

    def _propagate(self):
        stack = [(x, y) for y in range(self.h) for x in range(self.w) if self.collapsed[y][x]]
        while stack:
            x, y = stack.pop()
            opts = self.grid[y][x]
            if not opts:
                continue
            for dx, dy, direction in [(0, -1, 'n'), (1, 0, 'e'), (0, 1, 's'), (-1, 0, 'w')]:
                nx, ny = x + dx, y + dy
                if nx < 0 or nx >= self.w or ny < 0 or ny >= self.h:
                    continue
                if self.collapsed[ny][nx]:
                    continue
                valid = [i for i in self.grid[ny][nx]
                         if any(self._valid_neighbor(ti, direction, i) for ti in opts)]
                if len(valid) < len(self.grid[ny][nx]):
                    self.grid[ny][nx] = valid
                    if len(valid) == 1:
                        self.collapsed[ny][nx] = True
                        self.output[ny][nx] = self.tiles[valid[0]]
                    stack.append((nx, ny))

    def generate(self, seed: int = 0, max_retries: int = 10) -> bool:
        for attempt in range(max_retries):
            self.reset(seed + attempt * 1000)
            if self._generate_step():
                return True
        return False

    def _generate_step(self) -> bool:
        for _ in range(self.w * self.h * 4):
            x, y = self._lowest_entropy()
            if x < 0:
                return True
            self._observe(x, y)
            self._propagate()
            for yy in range(self.h):
                for xx in range(self.w):
                    if not self.grid[yy][xx]:
                        return False
        return all(self.collapsed[y][x] for y in range(self.h) for x in range(self.w))

    def render(self, canvas: Canvas, ox: int = 0, oy: int = 0):
        for y in range(self.h):
            for x in range(self.w):
                t = self.output[y][x]
                if t:
                    cx, cy = x + ox, y + oy
                    if 0 <= cx < canvas.w and 0 <= cy < canvas.h:
                        canvas.set_pixel(cx, cy, t.char, t.fg or DIM)

    @staticmethod
    def simple_path_tiles() -> WFC:
        wfc = WFC(10, 10)
        wfc.add_tile_from_sample(' ', DIM, name='empty',
                                  north=' ', east=' ', south=' ', west=' ')
        wfc.add_tile_from_sample('#', Color(100, 150, 255), name='wall',
                                  north='#', east='#', south='#', west='#')
        wfc.add_tile_from_sample('+', Color(255, 255, 100), name='path_h',
                                  north=' ', east='+', south=' ', west='+')
        wfc.add_tile_from_sample('+', Color(255, 255, 100), name='path_v',
                                  north='+', east=' ', south='+', west=' ')
        wfc.add_tile_from_sample('+', Color(255, 255, 100), name='turn_ne',
                                  north='+', east='+', south=' ', west=' ')
        wfc.add_tile_from_sample('+', Color(255, 255, 100), name='turn_nw',
                                  north='+', east=' ', south=' ', west='+')
        wfc.add_tile_from_sample('+', Color(255, 255, 100), name='turn_se',
                                  north=' ', east='+', south='+', west=' ')
        wfc.add_tile_from_sample('+', Color(255, 255, 100), name='turn_sw',
                                  north=' ', east=' ', south='+', west='+')
        wfc.add_tile_from_sample('+', Color(255, 255, 100), name='cross',
                                  north='+', east='+', south='+', west='+')
        return wfc

    @staticmethod
    def simple_platformer_tiles() -> WFC:
        wfc = WFC(16, 12)
        wfc.add_tile_from_sample(' ', DIM, name='air',
                                  north=' ', east=' ', south=' ', west=' ')
        wfc.add_tile_from_sample('#', Color(139, 90, 43), name='ground',
                                  north='#', east='#', south='#', west='#')
        wfc.add_tile_from_sample('[', Color(34, 139, 34), name='grass_top',
                                  north=' ', east='[', south='#', west='[')
        wfc.add_tile_from_sample('.', Color(100, 100, 100), name='stone',
                                  north='.', east='.', south='.', west='.')
        return wfc
