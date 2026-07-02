from __future__ import annotations
import math, random
from typing import Optional
from ..core.canvas import Canvas
from ..core.color import Color, DIM
from ..sim.noise import PerlinNoise


SHADE = ' .:-=+*#%@'


# ═══════════════════════════════════════════════════════════════════
# DUNGEON GENERATION — BSP rooms + corridors
# ═══════════════════════════════════════════════════════════════════

class Room:
    def __init__(self, x: int, y: int, w: int, h: int):
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.connected = False
        self.type = 'normal'
        self.tags: list[str] = []

    @property
    def cx(self) -> int:
        return self.x + self.w // 2

    @property
    def cy(self) -> int:
        return self.y + self.h // 2

    @property
    def area(self) -> int:
        return self.w * self.h

    def intersects(self, other: Room, pad: int = 1) -> bool:
        return not (self.x + self.w + pad <= other.x or
                    other.x + other.w + pad <= self.x or
                    self.y + self.h + pad <= other.y or
                    other.y + other.h + pad <= self.y)

    def center_dist(self, other: Room) -> float:
        return math.hypot(self.cx - other.cx, self.cy - other.cy)

    def random_point(self, rng: random.Random) -> tuple[int, int]:
        return (rng.randint(self.x + 1, self.x + self.w - 2),
                rng.randint(self.y + 1, self.y + self.h - 2))

    def __repr__(self):
        return f'Room({self.x},{self.y} {self.w}x{self.h})'


class DungeonGen:
    def __init__(self, width: int, height: int, seed: int = 42):
        self.w = width
        self.h = height
        self.seed = seed
        self._rng = random.Random(seed)
        self.grid: list[list[str]] = [['#'] * width for _ in range(height)]
        self.rooms: list[Room] = []
        self.corridors: list[tuple[tuple[int, int], tuple[int, int]]] = []

    def generate(self, min_room_size: int = 4, max_room_size: int = 12,
                 max_rooms: int = 15, bsp_depth: int = 4):
        self.grid = [['#'] * self.w for _ in range(self.h)]
        self.rooms = []
        self.corridors = []

        leaves = self._bsp(0, 0, self.w, self.h, bsp_depth)
        for leaf in leaves:
            max_rw = min(max_room_size, leaf[2] - 2)
            max_rh = min(max_room_size, leaf[3] - 2)
            if max_rw < min_room_size or max_rh < min_room_size:
                rw = max(3, leaf[2] - 4)
                rh = max(3, leaf[3] - 4)
                rx = leaf[0] + 1
                ry = leaf[1] + 1
            else:
                rw = self._rng.randint(min_room_size, max_rw)
                rh = self._rng.randint(min_room_size, max_rh)
                rx = leaf[0] + self._rng.randint(1, leaf[2] - rw - 1)
                ry = leaf[1] + self._rng.randint(1, leaf[3] - rh - 1)
            room = Room(rx, ry, rw, rh)
            ok = all(not room.intersects(ex, pad=1) for ex in self.rooms)
            if ok:
                self.rooms.append(room)

        if len(self.rooms) < 2:
            for y in range(2, self.h - 2, 3):
                for x in range(2, self.w - 2, 3):
                    if len(self.rooms) >= max_rooms:
                        break
                    room = Room(x, y, 3, 3)
                    if all(not room.intersects(ex, pad=1) for ex in self.rooms):
                        self.rooms.append(room)

        if len(self.rooms) > 1:
            self._tag_rooms()
            sorted_rooms = sorted(self.rooms, key=lambda r: r.cx)
            for i in range(len(sorted_rooms) - 1):
                self._carve_corridor(sorted_rooms[i], sorted_rooms[i + 1])

        for room in self.rooms:
            self._carve_room(room)

        return self.rooms

    def _bsp(self, x: int, y: int, w: int, h: int, depth: int) -> list[tuple[int, int, int, int]]:
        if depth <= 0 or w < 8 or h < 8:
            return [(x, y, w, h)]
        if self._rng.random() < 0.5:
            if w < 10:
                return [(x, y, w, h)]
            split = self._rng.randint(w // 3, w * 2 // 3)
            return (self._bsp(x, y, split, h, depth - 1) +
                    self._bsp(x + split, y, w - split, h, depth - 1))
        else:
            if h < 10:
                return [(x, y, w, h)]
            split = self._rng.randint(h // 3, h * 2 // 3)
            return (self._bsp(x, y, w, split, depth - 1) +
                    self._bsp(x, y + split, w, h - split, depth - 1))

    def _tag_rooms(self):
        if not self.rooms:
            return
        self.rooms[0].type = 'entrance'
        self.rooms[0].tags.append('entrance')
        if len(self.rooms) > 1:
            self.rooms[-1].type = 'treasure'
            self.rooms[-1].tags.append('treasure')
        for i in range(1, len(self.rooms) - 1):
            if self._rng.random() < 0.2:
                self.rooms[i].type = 'shop'
                self.rooms[i].tags.append('shop')
            elif self._rng.random() < 0.15:
                self.rooms[i].type = 'boss'
                self.rooms[i].tags.append('boss')

    def _carve_room(self, room: Room):
        for y in range(room.y, room.y + room.h):
            for x in range(room.x, room.x + room.w):
                if 0 <= x < self.w and 0 <= y < self.h:
                    self.grid[y][x] = '.'
                    if y == room.y or y == room.y + room.h - 1:
                        self.grid[y][x] = '-'
                    if x == room.x or x == room.x + room.w - 1:
                        self.grid[y][x] = '|'

        if room.type == 'entrance':
            self.grid[room.cy][room.cx] = '>'
        elif room.type == 'treasure':
            self.grid[room.cy][room.cx] = '$'
        elif room.type == 'shop':
            self.grid[room.cy][room.cx] = 'M'
        elif room.type == 'boss':
            self.grid[room.cy][room.cx] = 'B'
        else:
            if self._rng.random() < 0.1:
                self.grid[room.cy][room.cx] = '!'

    def _carve_corridor(self, a: Room, b: Room):
        x, y = a.cx, a.cy
        tx, ty = b.cx, b.cy
        self.corridors.append(((x, y), (tx, ty)))
        while x != tx or y != ty:
            if self._rng.random() < 0.5:
                if x < tx:
                    x += 1
                elif x > tx:
                    x -= 1
                elif y < ty:
                    y += 1
                elif y > ty:
                    y -= 1
            else:
                if y < ty:
                    y += 1
                elif y > ty:
                    y -= 1
                elif x < tx:
                    x += 1
                elif x > tx:
                    x -= 1
            if 0 <= x < self.w and 0 <= y < self.h and self.grid[y][x] == '#':
                self.grid[y][x] = '.'

    def render(self, canvas: Canvas, ox: int = 0, oy: int = 0, z: float = 5):
        for y in range(min(self.h, canvas.h - oy)):
            for x in range(min(self.w, canvas.width - ox)):
                ch = self.grid[y][x]
                if ch == '#':
                    canvas.set_pixel(x + ox, y + oy, '█',
                                     Color(80, 80, 110), z=z)
                elif ch == '.':
                    canvas.set_pixel(x + ox, y + oy, '·',
                                     Color(160, 160, 180), z=z)
                elif ch == '-':
                    canvas.set_pixel(x + ox, y + oy, '─',
                                     Color(120, 100, 80), z=z)
                elif ch == '|':
                    canvas.set_pixel(x + ox, y + oy, '│',
                                     Color(120, 100, 80), z=z)
                elif ch == '>':
                    canvas.set_pixel(x + ox, y + oy, '▶',
                                     Color(100, 255, 100), z=z)
                elif ch == '$':
                    canvas.set_pixel(x + ox, y + oy, '♦',
                                     Color(255, 220, 50), z=z)
                elif ch == 'M':
                    canvas.set_pixel(x + ox, y + oy, '⚔',
                                     Color(100, 200, 255), z=z)
                elif ch == 'B':
                    canvas.set_pixel(x + ox, y + oy, '☠',
                                     Color(255, 80, 80), z=z)
                elif ch == '!':
                    canvas.set_pixel(x + ox, y + oy, '!',
                                     Color(255, 255, 100), z=z)


# ═══════════════════════════════════════════════════════════════════
# RIVER GENERATION
# ═══════════════════════════════════════════════════════════════════

class RiverGen:
    def __init__(self, width: int, height: int, seed: int = 42):
        self.w = width
        self.h = height
        self.seed = seed
        self._rng = random.Random(seed)
        self.noise = PerlinNoise(seed)
        self.paths: list[list[tuple[int, int]]] = []

    def generate_rivers(self, heightmap: list[list[float]],
                        num_rivers: int = 3, meander: float = 0.5,
                        max_length: int = 200) -> list[list[tuple[int, int]]]:
        self.paths = []
        sources: list[tuple[int, int]] = []

        for _ in range(num_rivers * 2):
            sx = self._rng.randint(1, self.w - 2)
            sy = self._rng.randint(1, self.h - 2)
            if heightmap[sy][sx] > 0.6:
                sources.append((sx, sy))
                if len(sources) >= num_rivers:
                    break

        if not sources:
            for _ in range(num_rivers):
                sources.append((self._rng.randint(1, self.w - 2),
                                self._rng.randint(1, self.h - 2)))

        for sx, sy in sources[:num_rivers]:
            path = self._trace_river(sx, sy, heightmap, meander, max_length)
            if len(path) > 5:
                self.paths.append(path)

        return self.paths

    def _trace_river(self, sx: int, sy: int, heightmap: list[list[float]],
                     meander: float, max_length: int) -> list[tuple[int, int]]:
        path = [(sx, sy)]
        x, y = float(sx), float(sy)
        step = 0
        visited = {(sx, sy)}

        while step < max_length:
            gx = heightmap[int(y)][min(int(x) + 1, self.w - 1)] - \
                 heightmap[int(y)][max(int(x) - 1, 0)]
            gy = heightmap[min(int(y) + 1, self.h - 1)][int(x)] - \
                 heightmap[max(int(y) - 1, 0)][int(x)]

            noise_angle = self.noise.noise2(x * 0.05, y * 0.05) * meander * 2
            dx = -gx + math.cos(noise_angle) * meander
            dy = -gy + math.sin(noise_angle) * meander
            d_len = math.hypot(dx, dy)
            if d_len < 0.001:
                break
            dx /= d_len
            dy /= d_len
            x += dx
            y += dy
            ix, iy = int(round(x)), int(round(y))
            if ix < 0 or ix >= self.w or iy < 0 or iy >= self.h:
                break
            if heightmap[iy][ix] < 0.05:
                break
            if (ix, iy) in visited:
                step += 1
                continue
            visited.add((ix, iy))
            path.append((ix, iy))
            step += 1

            if heightmap[iy][ix] < 0.1:
                break

        return path

    def apply_to(self, heightmap: list[list[float]], depth: float = 0.3,
                 width: int = 2):
        for path in self.paths:
            for i, (px, py) in enumerate(path):
                r = width
                if i < 3 or i >= len(path) - 3:
                    r = max(1, width - 1)
                for dy in range(-r, r + 1):
                    for dx in range(-r, r + 1):
                        if dx * dx + dy * dy <= r * r:
                            nx, ny = px + dx, py + dy
                            if 0 <= nx < self.w and 0 <= ny < self.h:
                                heightmap[ny][nx] = max(0, heightmap[ny][nx] - depth)

    def render(self, canvas: Canvas, z: float = 5):
        for path in self.paths:
            for i, (px, py) in enumerate(path):
                t = i / max(1, len(path))
                col = Color.from_hsv(0.55, 0.6, 0.3 + t * 0.5)
                canvas.set_pixel(px, py, '~', col, z=z)


# ═══════════════════════════════════════════════════════════════════
# WORLD GENERATION — terrain + biomes + rivers + features
# ═══════════════════════════════════════════════════════════════════

class WorldGen:
    def __init__(self, width: int, height: int, seed: int = 42):
        self.w = width
        self.h = height
        self.seed = seed
        self._rng = random.Random(seed)
        self.noise = PerlinNoise(seed)
        self.heightmap: list[list[float]] = [[0.0] * width for _ in range(height)]
        self.moisture: list[list[float]] = [[0.0] * width for _ in range(height)]
        self.biome_map: list[list[str]] = [[''] * width for _ in range(height)]
        self.rivers: list[list[tuple[int, int]]] = []
        self.settlements: list[tuple[int, int, str]] = []
        self.features: list[tuple[int, int, str]] = []

    def generate(self, scale: float = 0.04, octaves: int = 6,
                 rivers: int = 4, river_meander: float = 0.6,
                 settlements: int = 5):
        for y in range(self.h):
            for x in range(self.w):
                e = self.noise.fbm2(x * scale, y * scale, octaves=octaves)
                self.heightmap[y][x] = max(0, min(1, e * 0.5 + 0.5))

        for y in range(self.h):
            for x in range(self.w):
                m = self.noise.noise2(x * scale * 1.5 + 50, y * scale * 1.5 + 50)
                self.moisture[y][x] = max(0, min(1, m * 0.5 + 0.5))

        river_gen = RiverGen(self.w, self.h, self.seed + 1)
        self.rivers = river_gen.generate_rivers(
            self.heightmap, num_rivers=rivers, meander=river_meander)
        river_gen.apply_to(self.heightmap, depth=0.4, width=2)

        self._assign_biomes()

        for _ in range(settlements):
            for _ in range(20):
                sx = self._rng.randint(1, self.w - 2)
                sy = self._rng.randint(1, self.h - 2)
                e = self.heightmap[sy][sx]
                b = self.biome_map[sy][sx]
                if 0.15 < e < 0.7 and b not in ('ocean', 'beach', 'tundra', 'snow', 'mountain'):
                    too_close = any(
                        math.hypot(sx - ox, sy - oy) < 5
                        for ox, oy, _ in self.settlements
                    )
                    if not too_close:
                        name = self._rng.choice(['Village', 'Town', 'Keep', 'Outpost', 'Farm'])
                        self.settlements.append((sx, sy, name))
                        break

        for _ in range(self._rng.randint(3, 8)):
            for _ in range(10):
                fx = self._rng.randint(1, self.w - 2)
                fy = self._rng.randint(1, self.h - 2)
                e = self.heightmap[fy][fx]
                b = self.biome_map[fy][fx]
                if b not in ('ocean', 'snow', 'mountain'):
                    feat = self._rng.choice(['ruins', 'tower', 'shrine', 'grove', 'mine'])
                    self.features.append((fx, fy, feat))
                    break

    def _assign_biomes(self):
        for y in range(self.h):
            for x in range(self.w):
                e = self.heightmap[y][x]
                m = self.moisture[y][x]

                is_river = any(
                    abs(px - x) <= 2 and abs(py - y) <= 2
                    for path in self.rivers for px, py in path
                )
                if is_river and e > 0.05:
                    self.biome_map[y][x] = 'river'
                    continue
                if e < 0.05:
                    self.biome_map[y][x] = 'ocean'
                elif e < 0.12:
                    self.biome_map[y][x] = 'beach'
                elif e > 0.75:
                    self.biome_map[y][x] = 'mountain'
                elif e > 0.65 and m < 0.4:
                    self.biome_map[y][x] = 'tundra'
                elif m < 0.2:
                    self.biome_map[y][x] = 'desert'
                elif m < 0.4:
                    if e < 0.3:
                        self.biome_map[y][x] = 'grassland'
                    else:
                        self.biome_map[y][x] = 'forest'
                elif m < 0.6:
                    if e < 0.25:
                        self.biome_map[y][x] = 'grassland'
                    else:
                        self.biome_map[y][x] = 'forest'
                elif e < 0.3:
                    self.biome_map[y][x] = 'swamp'
                elif e < 0.5:
                    self.biome_map[y][x] = 'rainforest'
                else:
                    self.biome_map[y][x] = 'taiga'

    BIOME_COLORS = {
        'ocean': Color(20, 40, 100),
        'beach': Color(180, 170, 120),
        'desert': Color(200, 180, 100),
        'grassland': Color(60, 160, 60),
        'forest': Color(30, 120, 40),
        'rainforest': Color(20, 100, 30),
        'tundra': Color(140, 150, 160),
        'taiga': Color(40, 80, 60),
        'mountain': Color(120, 100, 80),
        'swamp': Color(50, 90, 50),
        'snow': Color(220, 220, 230),
        'river': Color(30, 80, 180),
    }

    BIOME_CHARS = {
        'ocean': ' ',
        'beach': ':',
        'desert': '.',
        'grassland': '"',
        'forest': '%',
        'rainforest': '%',
        'tundra': ':',
        'taiga': '^',
        'mountain': '^',
        'swamp': '~',
        'snow': ' ',
        'river': '~',
    }

    def render(self, canvas: Canvas, z: float = 5,
               show_biomes: bool = True, show_features: bool = True):
        for y in range(min(self.h, canvas.h)):
            for x in range(min(self.w, canvas.width)):
                b = self.biome_map[y][x]
                if not b:
                    continue
                e = self.heightmap[y][x]
                col = self.BIOME_COLORS.get(b, Color(100, 100, 100))
                if not show_biomes:
                    v = e
                    col = Color.from_hsv(0.2 + v * 0.2, 0.6, 0.1 + v * 0.7)
                    ci = int(v * (len(SHADE) - 1))
                    canvas.set_pixel(x, y, SHADE[ci], col, z=z)
                else:
                    ch = self.BIOME_CHARS.get(b, ' ')
                    if b == 'mountain':
                        ci = int(e * (len(SHADE) - 1)) if e > 0.75 else 7
                        ch = SHADE[min(ci, len(SHADE) - 1)]
                    elif b == 'ocean':
                        ch = ' '
                    elif b == 'snow':
                        ch = ' '
                    canvas.set_pixel(x, y, ch, col, z=z)

        if show_features:
            for sx, sy, name in self.settlements:
                if 0 <= sx < canvas.w and 0 <= sy < canvas.h:
                    canvas.set_pixel(sx, sy, '♦', Color(255, 200, 60), z=z + 1)
                    for i, ch in enumerate(name[:8]):
                        px = sx - len(name[:8]) // 2 + i
                        if 0 <= px < canvas.w and sy + 1 < canvas.h:
                            canvas.set_pixel(px, sy + 1, ch,
                                             Color(255, 255, 200), z=z + 1)
            for fx, fy, feat in self.features:
                if 0 <= fx < canvas.w and 0 <= fy < canvas.h:
                    icons = {'ruins': '▒', 'tower': '▲', 'shrine': '❖',
                             'grove': '♣', 'mine': '⚒'}
                    canvas.set_pixel(fx, fy, icons.get(feat, '?'),
                                     Color(200, 200, 100), z=z + 1)
