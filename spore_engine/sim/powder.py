from __future__ import annotations
import numpy as np
from ..core.color import Color
from ..core.canvas import Canvas

EMPTY = 0; SAND = 1; WATER = 2; STONE = 3; WOOD = 4; FIRE = 5
SMOKE = 6; OIL = 7; LAVA = 8; ACID = 9; PLANT = 10; SALT = 11; STEAM = 12

LIQUIDS = {WATER, OIL}
GASES = {FIRE, SMOKE, STEAM}
SOLIDS = {SAND, STONE, WOOD, LAVA, ACID, PLANT, SALT}
FLAMMABLE = {WOOD, OIL, PLANT}
#: What lava can melt. STONE is deliberately absent: it let lava convert a
#: stone floor into more lava, which cooled back to stone and melted again, so
#: a lava spill never settled and lava mass grew out of nothing.
MELTABLE = {SAND: LAVA}

#: Materials whose rules never change them, so they do not age.
_INERT = {STONE, WOOD}

MATERIAL_NAMES = {
    EMPTY: 'Empty', SAND: 'Sand', WATER: 'Water', STONE: 'Stone',
    WOOD: 'Wood', FIRE: 'Fire', SMOKE: 'Smoke', OIL: 'Oil',
    LAVA: 'Lava', ACID: 'Acid', PLANT: 'Plant', SALT: 'Salt',
    STEAM: 'Steam',
}

MATERIAL_COLORS = np.array([
    [0, 0, 0],       # EMPTY
    [194, 178, 128], # SAND
    [30, 100, 220],  # WATER
    [120, 120, 120], # STONE
    [110, 70, 30],   # WOOD
    [255, 180, 30],  # FIRE
    [80, 80, 80],    # SMOKE
    [180, 140, 40],  # OIL
    [255, 100, 20],  # LAVA
    [50, 220, 50],   # ACID
    [30, 160, 30],   # PLANT
    [230, 230, 240], # SALT
    [200, 200, 220], # STEAM
], dtype=np.int32)

RENDER_CHARS = np.array([
    ' ', '.', '~', '#', '%', '*', ':', '~', '@', '~', '%', '.', ':'
], dtype='<U1')


class PowderSim:
    def __init__(self, width: int, height: int):
        self.w = width
        self.h = height
        self.size = width * height
        self.type_arr = np.zeros(self.size, dtype=np.int32)
        self.life_arr = np.zeros(self.size, dtype=np.int32)
        self.temp_arr = np.full(self.size, 20, dtype=np.int32)
        self.updated_arr = np.zeros(self.size, dtype=np.bool_)
        self.color_arr = np.zeros((self.size, 3), dtype=np.uint8)
        self.brush_size = 3
        self.current_material = SAND
        self.gravity = 1.0
        self._rng_state = np.random.RandomState(42)
        # Rendering varies sand/water/fire tints for looks. That must not come
        # out of the simulation's stream: sharing one RandomState made the
        # trajectory depend on how many frames had been drawn, so the same
        # inputs simulated differently depending on the render cadence.
        self._rng_render = np.random.RandomState(1337)

    def _idx(self, x: int, y: int) -> int:
        return y * self.w + x

    def _in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.w and 0 <= y < self.h

    def _get_type(self, x: int, y: int) -> int:
        return self.type_arr[self._idx(x, y)] if self._in_bounds(x, y) else -1

    def set_cell(self, x: int, y: int, type_: int):
        if not self._in_bounds(x, y):
            return
        idx = self._idx(x, y)
        self.type_arr[idx] = type_
        self.life_arr[idx] = 0
        self.temp_arr[idx] = 20
        self.color_arr[idx] = 0
        if type_ == FIRE:
            self.life_arr[idx] = self._rng_state.randint(20, 61)
            self.temp_arr[idx] = 400 + self._rng_state.randint(0, 201)
        elif type_ == SMOKE:
            self.life_arr[idx] = self._rng_state.randint(30, 81)
            self.temp_arr[idx] = 100 + self._rng_state.randint(0, 101)
        elif type_ == LAVA:
            self.life_arr[idx] = self._rng_state.randint(100, 301)
            self.temp_arr[idx] = 800 + self._rng_state.randint(0, 201)
        elif type_ == STEAM:
            self.life_arr[idx] = self._rng_state.randint(20, 61)
            self.temp_arr[idx] = 120
        elif type_ == PLANT:
            self.life_arr[idx] = self._rng_state.randint(50, 201)
        elif type_ == SALT:
            self.life_arr[idx] = 1

    def paint(self, x: int, y: int, type_: int | None = None):
        mt = type_ if type_ is not None else self.current_material
        bs = self.brush_size
        for dy in range(-bs, bs + 1):
            for dx in range(-bs, bs + 1):
                if dx * dx + dy * dy <= bs * bs:
                    self.set_cell(x + dx, y + dy, mt)

    def clear(self):
        self.type_arr.fill(0)
        self.life_arr.fill(0)
        self.temp_arr.fill(20)
        self.updated_arr.fill(False)
        self.color_arr.fill(0)

    def _swap(self, x1: int, y1: int, x2: int, y2: int):
        i1, i2 = self._idx(x1, y1), self._idx(x2, y2)
        self.type_arr[i1], self.type_arr[i2] = self.type_arr[i2], self.type_arr[i1]
        self.life_arr[i1], self.life_arr[i2] = self.life_arr[i2], self.life_arr[i1]
        self.temp_arr[i1], self.temp_arr[i2] = self.temp_arr[i2], self.temp_arr[i1]
        self.color_arr[i1], self.color_arr[i2] = self.color_arr[i2], self.color_arr[i1].copy()

    def _try_move(self, x: int, y: int, dx: int, dy: int) -> bool:
        nx, ny = x + dx, y + dy
        if not self._in_bounds(nx, ny):
            return False
        if self.type_arr[self._idx(nx, ny)] != EMPTY:
            return False
        self._swap(x, y, nx, ny)
        return True

    def _is_flammable_adjacent(self, x: int, y: int) -> bool:
        w = self.w
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                nx, ny = x + dx, y + dy
                if self._in_bounds(nx, ny) and self.type_arr[ny * w + nx] == FIRE:
                    return True
        return False

    def update(self):
        w, h = self.w, self.h
        tp = self.type_arr
        lf = self.life_arr
        up = self.updated_arr
        rng = self._rng_state
        size = self.size

        # Every row is visited, including the last. Skipping the bottom row
        # froze whatever settled there: acid, smoke and steam only clear
        # themselves through their update rules, so they piled up on the floor
        # forever. Scanning downwards means a grain that moves down lands in a
        # row already visited this tick, so it is still processed only once.
        for y in range(h - 1, -1, -1):
            row = y * w
            for x in range(w):
                idx = row + x
                if up[idx]:
                    continue
                t = tp[idx]
                if t == EMPTY:
                    continue
                up[idx] = True
                # One tick of ageing for everything that ages. Doing it here
                # rather than in each rule kept the rules from double-decrementing
                # (lava and plant did, so they aged twice as fast), and skipping
                # the inert solids stops their life counting down into negatives.
                if t not in _INERT:
                    lf[idx] -= 1

                if t == SAND:
                    self._update_sand(x, y)
                elif t == WATER:
                    self._update_water(x, y)
                elif t == OIL:
                    self._update_oil(x, y)
                elif t == FIRE:
                    self._update_fire(x, y, rng)
                elif t == SMOKE:
                    self._update_smoke(x, y, rng)
                elif t == STEAM:
                    self._update_steam(x, y, rng)
                elif t == LAVA:
                    self._update_lava(x, y, rng)
                elif t == ACID:
                    self._update_acid(x, y, rng)
                elif t == PLANT:
                    self._update_plant(x, y, rng)
                elif t == SALT:
                    self._update_salt(x, y)

        for i in range(size):
            up[i] = False

    def _update_sand(self, x: int, y: int):
        w = self.w
        r = self._rng_state.random_sample()
        if self._try_move(x, y, 0, 1):
            return
        if r < 0.5:
            if self._try_move(x, y, -1, 1): return
            if self._try_move(x, y, 1, 1): return
        else:
            if self._try_move(x, y, 1, 1): return
            if self._try_move(x, y, -1, 1): return
        if self._is_flammable_adjacent(x, y):
            self.set_cell(x, y, FIRE)
            self.life_arr[y * w + x] = self._rng_state.randint(30, 61)

    def _update_water(self, x: int, y: int):
        w = self.w
        below = self._get_type(x, y + 1)
        if below == OIL:
            self._swap(x, y, x, y + 1)
            return
        if self._try_move(x, y, 0, 1):
            return
        spread = 4
        for dx in (-1, 1):
            for step in range(1, spread + 1):
                tx = x + dx * step
                if not self._in_bounds(tx, y): break
                if self.type_arr[y * w + tx] != EMPTY: break
                if self._in_bounds(tx, y + 1) and self.type_arr[(y + 1) * w + tx] == EMPTY:
                    self._swap(x, y, tx, y)
                    return
        if self._rng_state.random_sample() < 0.3:
            self._try_move(x, y, -1, 0)
        if self._rng_state.random_sample() < 0.3:
            self._try_move(x, y, 1, 0)
        if self.type_arr[y * w + x] == WATER and self._is_flammable_adjacent(x, y):
            self.set_cell(x, y, STEAM)
            self.life_arr[y * w + x] = self._rng_state.randint(20, 61)

    def _update_oil(self, x: int, y: int):
        above = self._get_type(x, y - 1)
        if above == WATER:
            # Rise through the water above, pushing it down.
            self._swap(x, y, x, y - 1)
            return
        if self._get_type(x, y + 1) == WATER:
            # Buoyant. Holding position lets _update_water sink past and leave
            # the oil on top. Swapping downwards here instead contradicted that
            # rule, and swapping upwards as well made the pair oscillate
            # forever, since the two swaps undid each other every tick.
            return
        if self._try_move(x, y, 0, 1): return
        if self._try_move(x, y, -1, 0): return
        if self._try_move(x, y, 1, 0): return
        if self._try_move(x, y, 0, -1) and self._rng_state.random_sample() < 0.3:
            return
        if self._is_flammable_adjacent(x, y) and self._rng_state.random_sample() < 0.3:
            self.set_cell(x, y, FIRE)
            self.life_arr[y * self.w + x] = self._rng_state.randint(40, 81)

    def _update_fire(self, x: int, y: int, rng: np.random.RandomState):
        idx = y * self.w + x
        r, g, b = rng.randint(200, 256), rng.randint(100, 201), rng.randint(0, 51)
        self.color_arr[idx] = [r, g, b]
        if rng.random_sample() < 0.15:
            self.set_cell(x, y + 1, SMOKE)
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dx == 0 and dy == 0: continue
                nx, ny = x + dx, y + dy
                if self._in_bounds(nx, ny):
                    nt = self.type_arr[ny * self.w + nx]
                    if nt in FLAMMABLE and rng.random_sample() < 0.1:
                        self.set_cell(nx, ny, FIRE)
                        self.life_arr[ny * self.w + nx] = rng.randint(20, 61)
        if rng.random_sample() < 0.3:
            self._try_move(x, y, 0, -1)
        if rng.random_sample() < 0.2:
            self._try_move(x, y, -1, 0)
        if rng.random_sample() < 0.2:
            self._try_move(x, y, 1, 0)
        if self.life_arr[idx] <= 0:
            self.type_arr[idx] = SMOKE
            self.life_arr[idx] = rng.randint(30, 81)

    def _update_smoke(self, x: int, y: int, rng: np.random.RandomState):
        if rng.random_sample() < 0.3:
            self._try_move(x, y, 0, -1)
        if rng.random_sample() < 0.2:
            self._try_move(x, y, -1, 0)
        if rng.random_sample() < 0.2:
            self._try_move(x, y, 1, 0)
        idx = y * self.w + x
        if self.life_arr[idx] <= 0 or rng.random_sample() < 0.01:
            self.type_arr[idx] = EMPTY

    def _update_lava(self, x: int, y: int, rng: np.random.RandomState):
        w = self.w
        below = self._get_type(x, y + 1)
        if below == WATER:
            self.set_cell(x, y, STONE)
            self.set_cell(x, y + 1, STEAM)
            return
        if self._try_move(x, y, 0, 1):
            return
        # Return on a successful diagonal move: falling through decremented
        # life_arr at the cell the lava had just left.
        if rng.random_sample() < 0.5:
            if self._try_move(x, y, -1, 1): return
            if self._try_move(x, y, 1, 1): return
        else:
            if self._try_move(x, y, 1, 1): return
            if self._try_move(x, y, -1, 1): return
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dx == 0 and dy == 0: continue
                nx, ny = x + dx, y + dy
                if self._in_bounds(nx, ny):
                    nt = self.type_arr[ny * w + nx]
                    if nt in FLAMMABLE and rng.random_sample() < 0.3:
                        self.set_cell(nx, ny, FIRE)
                    elif nt in MELTABLE and rng.random_sample() < 0.05:
                        # Swap rather than set_cell: converting the neighbour
                        # in place created lava out of nothing.
                        self._swap(x, y, nx, ny)
                        return
        idx = y * w + x
        if self.life_arr[idx] <= 0:
            self.type_arr[idx] = STONE

    def _update_acid(self, x: int, y: int, rng: np.random.RandomState):
        w = self.w
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dx == 0 and dy == 0: continue
                nx, ny = x + dx, y + dy
                if self._in_bounds(nx, ny):
                    nt = self.type_arr[ny * w + nx]
                    if nt != EMPTY and nt != ACID and nt != STONE and rng.random_sample() < 0.3:
                        self.set_cell(nx, ny, EMPTY)
                        self.set_cell(x, y, EMPTY)
                        return
        if self._try_move(x, y, 0, 1): return
        if rng.random_sample() < 0.5:
            if self._try_move(x, y, -1, 1): return
            if self._try_move(x, y, 1, 1): return
        else:
            if self._try_move(x, y, 1, 1): return
            if self._try_move(x, y, -1, 1): return
        idx = y * w + x
        if rng.random_sample() < 0.01:
            self.type_arr[idx] = EMPTY

    def _is_grounded(self, x: int, y: int) -> bool:
        """True if the first solid cell under (x, y) is real ground.

        Scanning past other plants lets a plant on the ground grow a column
        upward, but without this a lone plant floating in mid-air treated its
        own body as support and grew an uncontrolled stack in the air.
        """
        for yy in range(y + 1, self.h):
            t = self._get_type(x, yy)
            if t == EMPTY:
                return False
            if t != PLANT:
                return True
        return False

    def _update_plant(self, x: int, y: int, rng: np.random.RandomState):
        idx = y * self.w + x
        if self.life_arr[idx] <= 0:
            if rng.random_sample() < 0.7:
                self.type_arr[idx] = PLANT
                self.life_arr[idx] = rng.randint(50, 201)
        if rng.random_sample() < 0.05 and self._is_grounded(x, y):
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    if dx == 0 and dy == 0: continue
                    nx, ny = x + dx, y + dy
                    if self._in_bounds(nx, ny) and self.type_arr[ny * self.w + nx] == EMPTY and ny < self.h - 1:
                        below = self.type_arr[(ny + 1) * self.w + nx]
                        if below != EMPTY:
                            self.set_cell(nx, ny, PLANT)
                            self.life_arr[ny * self.w + nx] = rng.randint(50, 201)
                            return

    def _update_steam(self, x: int, y: int, rng: np.random.RandomState):
        if rng.random_sample() < 0.3:
            self._try_move(x, y, 0, -1)
        if rng.random_sample() < 0.2:
            self._try_move(x, y, -1, 0)
        if rng.random_sample() < 0.2:
            self._try_move(x, y, 1, 0)
        idx = y * self.w + x
        if self.life_arr[idx] <= 0 or rng.random_sample() < 0.02:
            self.type_arr[idx] = EMPTY

    def _update_salt(self, x: int, y: int):
        below = self._get_type(x, y + 1)
        if below in (WATER, OIL):
            self.type_arr[y * self.w + x] = EMPTY
            return
        if self._try_move(x, y, 0, 1): return
        r = self._rng_state.random_sample()
        if r < 0.5:
            if self._try_move(x, y, -1, 1): return
            self._try_move(x, y, 1, 1)
        else:
            if self._try_move(x, y, 1, 1): return
            self._try_move(x, y, -1, 1)

    def render(self, canvas: Canvas, z: float = 5):
        w, h = self.w, self.h
        tp = self.type_arr
        clr = self.color_arr
        mc = MATERIAL_COLORS
        chs = RENDER_CHARS
        rng = self._rng_render

        for y in range(h):
            row = y * w
            for x in range(w):
                idx = row + x
                t = tp[idx]
                if t == EMPTY:
                    continue
                has_custom = clr[idx, 0] | clr[idx, 1] | clr[idx, 2]
                if has_custom:
                    col = Color(int(clr[idx, 0]), int(clr[idx, 1]), int(clr[idx, 2]))
                else:
                    base = mc[t]
                    if t == SAND:
                        v = rng.randint(-20, 21)
                        col = Color(int(base[0] + v), int(base[1] + v), int(base[2] + v))
                    elif t == WATER:
                        col = Color(int(base[0]), int(base[1]), int(base[2] + rng.randint(-10, 11)))
                    elif t == FIRE:
                        col = Color(rng.randint(200, 256), rng.randint(80, 181), rng.randint(0, 41))
                    elif t == LAVA:
                        col = Color(rng.randint(200, 256), rng.randint(60, 151), rng.randint(0, 21))
                    elif t == PLANT:
                        col = Color(int(base[0]), int(base[1] + rng.randint(-10, 21)), int(base[2]))
                    elif t == SMOKE:
                        v = rng.randint(60, 101)
                        col = Color(v, v, v)
                    else:
                        col = Color(int(base[0]), int(base[1]), int(base[2]))
                canvas.set_pixel(x, y, str(chs[t]), col, z=z)
