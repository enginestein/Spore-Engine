from __future__ import annotations
import math
from typing import Optional
import numpy as np
from scipy.ndimage import uniform_filter, maximum_filter, sobel
from ..core.canvas import Canvas
from ..core.color import Color, WHITE, DIM


SHADE = ' .:-=+*#%@'


def _extract_fg(canvas: Canvas) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    w, h = canvas.width, canvas.height
    r = np.zeros((h, w), dtype=np.int32)
    g = np.zeros((h, w), dtype=np.int32)
    b = np.zeros((h, w), dtype=np.int32)
    mask = np.zeros((h, w), dtype=np.bool_)
    buf = canvas.buffer
    for y in range(h):
        row = buf[y]
        for x in range(w):
            fg = row[x].fg
            if fg is not None:
                r[y, x] = fg.r
                g[y, x] = fg.g
                b[y, x] = fg.b
                mask[y, x] = True
    return r, g, b, mask


def _apply_fg(canvas: Canvas, r: np.ndarray, g: np.ndarray, b: np.ndarray, mask: np.ndarray):
    buf = canvas.buffer
    for y in range(canvas.height):
        row = buf[y]
        for x in range(canvas.width):
            if mask[y, x]:
                row[x].fg = Color(int(r[y, x]), int(g[y, x]), int(b[y, x]))


def _clamp(arr: np.ndarray) -> np.ndarray:
    return np.clip(np.round(arr), 0, 255).astype(np.int32)


def box_blur(canvas: Canvas, radius: int = 1):
    w, h = canvas.width, canvas.height
    if radius < 1:
        return
    r, g, b, mask = _extract_fg(canvas)
    size = 2 * radius + 1
    r_blur = uniform_filter(r.astype(np.float64), size=size, mode='constant', cval=0)
    g_blur = uniform_filter(g.astype(np.float64), size=size, mode='constant', cval=0)
    b_blur = uniform_filter(b.astype(np.float64), size=size, mode='constant', cval=0)
    r_out = np.where(mask, r_blur, r).astype(np.int32)
    g_out = np.where(mask, g_blur, g).astype(np.int32)
    b_out = np.where(mask, b_blur, b).astype(np.int32)
    _apply_fg(canvas, r_out, g_out, b_out, mask)


def glow(canvas: Canvas, threshold: float = 0.6, radius: int = 2, intensity: float = 0.5):
    w, h = canvas.width, canvas.height
    r, g, b, mask = _extract_fg(canvas)
    lum = (0.299 * r + 0.587 * g + 0.114 * b) / 255.0
    bright_mask = (lum > threshold) & mask
    if not bright_mask.any():
        return
    v = np.where(bright_mask, (lum - threshold) / (1 - threshold), 0.0)
    glow_map = maximum_filter(v, size=2 * radius + 1, mode='constant', cval=0)
    glow_map = np.clip(glow_map * intensity, 0, 1)
    for y in range(h):
        for x in range(w):
            val = glow_map[y, x]
            if val > 0:
                cell = canvas.buffer[y][x]
                if cell.fg:
                    cell.fg = cell.fg.blend(WHITE, min(1, val))
                else:
                    canvas.set_pixel(x, y, SHADE[int(val * 9)], WHITE.mul(val))


def edge_detect(canvas: Canvas, fg: Optional[Color] = None, threshold: float = 0.15):
    w, h = canvas.width, canvas.height
    edge_color = fg or Color(0, 255, 255)
    _, _, _, mask = _extract_fg(canvas)
    lum = np.zeros((h, w), dtype=np.float64)
    buf = canvas.buffer
    for y in range(h):
        row = buf[y]
        for x in range(w):
            fg_c = row[x].fg
            if fg_c:
                lum[y, x] = fg_c.luminance
    sx = sobel(lum, axis=1, mode='constant') / 8.0
    sy = sobel(lum, axis=0, mode='constant') / 8.0
    mag = np.sqrt(sx ** 2 + sy ** 2) / 128.0
    edges = mag > threshold
    for y in range(1, h - 1):
        for x in range(1, w - 1):
            if edges[y, x]:
                canvas.set_pixel(x, y, '@', edge_color,
                                 z=(canvas.get_pixel(x, y).z + 1 if canvas.get_pixel(x, y) else 0))


def dither(canvas: Canvas, palette: Optional[list[Color]] = None):
    pal = palette or [Color(0, 0, 0), Color(255, 255, 255), Color(255, 0, 0),
                      Color(0, 255, 0), Color(0, 0, 255), Color(255, 255, 0)]
    pal_np = np.array([[c.r, c.g, c.b] for c in pal], dtype=np.int32)
    w, h = canvas.width, canvas.height
    buf = canvas.buffer
    for y in range(h):
        for x in range(w):
            cell = buf[y][x]
            if not cell.fg:
                continue
            old = np.array([cell.fg.r, cell.fg.g, cell.fg.b], dtype=np.int32)
            dist = np.sum((pal_np - old) ** 2, axis=1)
            best = pal_np[dist.argmin()]
            cell.fg = Color(int(best[0]), int(best[1]), int(best[2]))
            err = old - best
            for dx, dy, wgt in [(1, 0, 7 / 16), (-1, 1, 3 / 16), (0, 1, 5 / 16), (1, 1, 1 / 16)]:
                nx, ny = x + dx, y + dy
                if 0 <= nx < w and 0 <= ny < h:
                    c = buf[ny][nx]
                    if c.fg:
                        c.fg = Color(
                            max(0, min(255, c.fg.r + int(err[0] * wgt))),
                            max(0, min(255, c.fg.g + int(err[1] * wgt))),
                            max(0, min(255, c.fg.b + int(err[2] * wgt))),
                        )


def scanlines(canvas: Canvas, intensity: float = 0.3):
    factor = 1 - intensity
    buf = canvas.buffer
    for y in range(0, canvas.height, 2):
        row = buf[y]
        for x in range(canvas.width):
            if row[x].fg:
                row[x].fg = row[x].fg.mul(factor)


def vignette(canvas: Canvas, intensity: float = 0.5):
    w, h = canvas.width, canvas.height
    cy, cx = h / 2.0, w / 2.0
    max_dist = math.sqrt(cx * cx + cy * cy)
    Y, X = np.ogrid[:h, :w]
    dist = np.sqrt((X - cx) ** 2 + (Y - cy) ** 2) / max_dist
    dark = np.maximum(0, 1 - dist * intensity)
    buf = canvas.buffer
    for y in range(h):
        d = dark[y, 0]
        row = buf[y]
        for x in range(w):
            cell = row[x]
            if cell.fg:
                cell.fg = cell.fg.mul(d)
            if cell.bg:
                cell.bg = cell.bg.mul(d)


def chromatic_aberration(canvas: Canvas, offset: int = 1):
    w, h = canvas.width, canvas.height
    r, g, b, mask = _extract_fg(canvas)
    r_shift = np.zeros_like(r)
    b_shift = np.zeros_like(b)
    r_shift[:, max(0, offset):w] = r[:, :w - offset] if offset > 0 else r[:, -offset:]
    if offset > 0:
        r_shift[:, :offset] = r[:, :offset]
    b_shift[:, :w - offset] = b[:, offset:] if offset > 0 else b[:, :w + offset]
    if offset > 0:
        b_shift[:, w - offset:] = b[:, w - offset:]
    r_out = np.where(mask, r_shift, r)
    b_out = np.where(mask, b_shift, b)
    _apply_fg(canvas, r_out, g, b_out, mask)


def pixelate(canvas: Canvas, block_size: int = 3):
    w, h = canvas.width, canvas.height
    r = np.zeros((h, w), dtype=np.float64)
    g = np.zeros((h, w), dtype=np.float64)
    b = np.zeros((h, w), dtype=np.float64)
    count = np.zeros((h, w), dtype=np.float64)
    buf = canvas.buffer
    for y in range(h):
        row = buf[y]
        for x in range(w):
            fg = row[x].fg
            if fg:
                r[y, x] = fg.r
                g[y, x] = fg.g
                b[y, x] = fg.b
                count[y, x] = 1
    for by in range(0, h, block_size):
        for bx in range(0, w, block_size):
            y1, y2 = by, min(by + block_size, h)
            x1, x2 = bx, min(bx + block_size, w)
            sub_count = count[y1:y2, x1:x2].sum()
            if sub_count > 0:
                avg_r = int(round(r[y1:y2, x1:x2].sum() / sub_count))
                avg_g = int(round(g[y1:y2, x1:x2].sum() / sub_count))
                avg_b = int(round(b[y1:y2, x1:x2].sum() / sub_count))
                for y in range(y1, y2):
                    for x in range(x1, x2):
                        if buf[y][x].fg:
                            buf[y][x].fg = Color(avg_r, avg_g, avg_b)


def palette_remap(canvas: Canvas, grad, intensity: float = 1.0):
    for y in range(canvas.height):
        for x in range(canvas.width):
            cell = canvas.buffer[y][x]
            if cell.fg:
                lum = cell.fg.luminance / 255
                cell.fg = grad.at(lum)
