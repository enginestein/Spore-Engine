from __future__ import annotations
import math
import random
from ..core.canvas import Canvas

from ..core.color import Color, BLACK  # noqa: F401  (re-exported for the subpackage API)
class Transition:
    def apply(self, dst: Canvas, src: Canvas, t: float):
        raise NotImplementedError

class Fade(Transition):
    def apply(self, dst: Canvas, src: Canvas, t: float):
        t = max(0, min(1, t))
        for y in range(min(dst.h, src.h)):
            for x in range(min(dst.w, src.w)):
                dc = dst.buffer[y][x]
                sc = src.buffer[y][x]
                if sc.fg:
                    if dc.fg:
                        dc.fg = sc.fg.blend(dc.fg, t)
                    else:
                        dc.fg = sc.fg
                if sc.bg:
                    if dc.bg:
                        dc.bg = sc.bg.blend(dc.bg, t)
                    else:
                        dc.bg = sc.bg
                if t <= 0.5:
                    dc.char = sc.char

class Wipe(Transition):
    def __init__(self, direction: str = 'right'):
        self.direction = direction

    def apply(self, dst: Canvas, src: Canvas, t: float):
        t = max(0, min(1, t))
        w, h = min(dst.w, src.w), min(dst.h, src.h)
        
        if self.direction == 'right':
            split = int(t * w)
            for y in range(h):
                for x in range(split, w):
                    # Copy from src to dst for the non-wiped part
                    dst.set_pixel(x, y, src.buffer[y][x].char, 
                                 src.buffer[y][x].fg, src.buffer[y][x].bg)
        elif self.direction == 'left':
            split = int((1 - t) * w)
            for y in range(h):
                for x in range(split):
                    dst.set_pixel(x, y, src.buffer[y][x].char, 
                                 src.buffer[y][x].fg, src.buffer[y][x].bg)
        elif self.direction == 'down':
            split = int(t * h)
            for x in range(w):
                for y in range(split, h):
                    dst.set_pixel(x, y, src.buffer[y][x].char, 
                                 src.buffer[y][x].fg, src.buffer[y][x].bg)
        elif self.direction == 'up':
            split = int((1 - t) * h)
            for x in range(w):
                for y in range(split):
                    dst.set_pixel(x, y, src.buffer[y][x].char, 
                                 src.buffer[y][x].fg, src.buffer[y][x].bg)

class Checkerboard(Transition):
    def __init__(self, size: int = 4):
        self.size = size

    def apply(self, dst: Canvas, src: Canvas, t: float):
        t = max(0, min(1, t))
        w, h = min(dst.w, src.w), min(dst.h, src.h)
        
        # Determine number of blocks to reveal
        total_blocks_x = math.ceil(w / self.size)
        total_blocks_y = math.ceil(h / self.size)
        total_blocks = total_blocks_x * total_blocks_y
        
        num_to_show = int(t * total_blocks)
        
        # For simplicity, just use a deterministic pattern based on t
        for by in range(total_blocks_y):
            for bx in range(total_blocks_x):
                # A simple way to "randomly" pick blocks to show
                # using a hash-like function
                block_id = (bx * 17 + by * 31) % total_blocks
                if block_id >= num_to_show:
                    for y in range(by * self.size, min((by + 1) * self.size, h)):
                        for x in range(bx * self.size, min((bx + 1) * self.size, w)):
                            dst.set_pixel(x, y, src.buffer[y][x].char, 
                                         src.buffer[y][x].fg, src.buffer[y][x].bg)

class PixelDissolve(Transition):
    def __init__(self, seed: int = 42):
        self.seed = seed

    def apply(self, dst: Canvas, src: Canvas, t: float):
        t = max(0, min(1, t))
        w, h = min(dst.w, src.w), min(dst.h, src.h)
        
        random.Random(self.seed)
        # This is expensive if we re-generate every time.
        # In a real engine we might pre-calculate the order.
        
        threshold = t
        for y in range(h):
            for x in range(w):
                # Use a stable "random" value for each pixel
                val = (x * 12345 + y * 67890 + self.seed) % 1000 / 1000.0
                if val >= threshold:
                    dst.set_pixel(x, y, src.buffer[y][x].char, 
                                 src.buffer[y][x].fg, src.buffer[y][x].bg)

class Slide(Transition):
    def __init__(self, direction: str = 'right'):
        self.direction = direction

    def apply(self, dst: Canvas, src: Canvas, t: float):
        t = max(0, min(1, t))
        w, h = min(dst.w, src.w), min(dst.h, src.h)
        
        offset_x, offset_y = 0, 0
        if self.direction == 'right':
            offset_x = int(t * w)
        elif self.direction == 'left':
            offset_x = -int(t * w)
        elif self.direction == 'down':
            offset_y = int(t * h)
        elif self.direction == 'up':
            offset_y = -int(t * h)
            
        # Draw next scene (dst) sliding in, and prev scene (src) sliding out
        # Since dst already contains the "next" scene, we need to shift it
        # and then draw src shifted.
        
        # 1. Backup dst
        backup = dst.copy()
        dst.clear()
        
        # 2. Draw src shifted
        for y in range(h):
            for x in range(w):
                sx, sy = x + offset_x, y + offset_y
                if 0 <= sx < w and 0 <= sy < h:
                    dst.set_pixel(sx, sy, src.buffer[y][x].char, 
                                 src.buffer[y][x].fg, src.buffer[y][x].bg)
        
        # 3. Draw dst (next scene) shifted in
        dx_start, dy_start = 0, 0
        if self.direction == 'right': dx_start = -w + offset_x
        elif self.direction == 'left': dx_start = w + offset_x
        elif self.direction == 'down': dy_start = -h + offset_y
        elif self.direction == 'up': dy_start = h + offset_y
        
        for y in range(h):
            for x in range(w):
                dx, dy = x + dx_start, y + dy_start
                if 0 <= dx < w and 0 <= dy < h:
                    dst.set_pixel(dx, dy, backup.buffer[y][x].char, 
                                 backup.buffer[y][x].fg, backup.buffer[y][x].bg)
