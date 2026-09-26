from __future__ import annotations
import math
import json
from collections.abc import Callable
from ..core.canvas import Canvas
from ..core.glyphs import SHADE_CHARS
from ..core.color import Color


#: Re-exported from core.glyphs so the ramp is defined once.
SHADE = SHADE_CHARS


class VideoFrame:
    def __init__(self, canvas: Canvas, duration: float = 1.0 / 30):
        self.canvas = canvas
        self.duration = duration


class FramePlayer:
    def __init__(self, fps: float = 30.0, loop: bool = True):
        self.frames: list[VideoFrame] = []
        self.fps = fps
        self.loop = loop
        self._idx = 0
        self._timer = 0.0
        self._playing = False
        self._done = False
        self._on_frame: Callable | None = None

    def load_frames(self, frames: list[VideoFrame]):
        self.frames = frames
        self._idx = 0
        self._timer = 0.0
        self._done = False

    def add_frame(self, frame: VideoFrame):
        self.frames.append(frame)

    @property
    def current_frame(self) -> VideoFrame | None:
        if 0 <= self._idx < len(self.frames):
            return self.frames[self._idx]
        return None

    @property
    def frame_count(self) -> int:
        return len(self.frames)

    @property
    def playing(self) -> bool:
        return self._playing

    @property
    def done(self) -> bool:
        return self._done

    def play(self):
        self._playing = True

    def pause(self):
        self._playing = False

    def stop(self):
        self._playing = False
        self._idx = 0
        self._timer = 0.0
        self._done = False

    def seek(self, frame_idx: int):
        self._idx = max(0, min(frame_idx, len(self.frames) - 1))
        self._timer = 0.0
        self._done = False

    def update(self, dt: float):
        if not self._playing or self._done or not self.frames:
            return
        self._timer += dt
        frame_dur = self.frames[self._idx].duration
        while self._timer >= frame_dur and not self._done:
            self._timer -= frame_dur
            self._idx += 1
            if self._idx >= len(self.frames):
                if self.loop:
                    self._idx = 0
                else:
                    self._idx = len(self.frames) - 1
                    self._done = True
                    self._playing = False
                    return

    @property
    def progress(self) -> float:
        return self._idx / max(1, len(self.frames))

    def render(self, canvas: Canvas, ox: int = 0, oy: int = 0,
               scale: float = 1.0, z: float = 5):
        frame = self.current_frame
        if frame is None:
            return
        src = frame.canvas
        if scale == 1.0 and ox == 0 and oy == 0:
            for y in range(min(src.h, canvas.h)):
                for x in range(min(src.w, canvas.w)):
                    cell = src.buffer[y][x]
                    if cell.char != ' ' or cell.fg:
                        canvas.set_pixel(x, y, cell.char, cell.fg, cell.bg, z)
        else:
            for y in range(canvas.h):
                for x in range(canvas.w):
                    sx = int((x - ox) / scale)
                    sy = int((y - oy) / scale)
                    if 0 <= sx < src.w and 0 <= sy < src.h:
                        cell = src.buffer[sy][sx]
                        if cell.char != ' ' or cell.fg:
                            canvas.set_pixel(x, y, cell.char, cell.fg, cell.bg, z)


class Video:
    def __init__(self, width: int = 0, height: int = 0, fps: float = 30.0):
        self.width = width
        self.height = height
        self.fps = fps
        self.frames: list[list[list[Color | None]]] = []

    @property
    def duration(self) -> float:
        return len(self.frames) / self.fps

    @property
    def frame_count(self) -> int:
        return len(self.frames)

    def to_player(self, loop: bool = True, shade: str = SHADE) -> FramePlayer:
        player = FramePlayer(self.fps, loop)
        for pixel_data in self.frames:
            c = Canvas(self.width, self.height)
            for y in range(min(len(pixel_data), self.height)):
                for x in range(min(len(pixel_data[y]), self.width)):
                    col = pixel_data[y][x]
                    if col:
                        lum = col.luminance / 255
                        ci = int(lum * (len(shade) - 1))
                        c.set_pixel(x, y, shade[ci], col)
            player.add_frame(VideoFrame(c))
        return player

    def add_frame_data(self, data: list[list[Color | None]]):
        self.frames.append(data)

    def from_canvas_sequence(self, canvases: list[Canvas]):
        for c in canvases:
            if self.width == 0:
                self.width = c.width
                self.height = c.height
            data: list[list[Color | None]] = []
            for y in range(c.height):
                row: list[Color | None] = []
                for x in range(c.width):
                    row.append(c.buffer[y][x].fg)
                data.append(row)
            self.frames.append(data)

    def save(self, path: str):
        data = {
            'w': self.width, 'h': self.height,
            'fps': self.fps,
            'frames': [],
        }
        for frame in self.frames:
            fdata = []
            for row in frame:
                rdata = []
                for col in row:
                    if col:
                        rdata.append([col.r, col.g, col.b])
                    else:
                        rdata.append(None)
                fdata.append(rdata)
            data['frames'].append(fdata)
        with open(path, 'w') as f:
            json.dump(data, f)

    @classmethod
    def load(cls, path: str) -> Video:
        with open(path) as f:
            data = json.load(f)
        v = cls(data['w'], data['h'], data['fps'])
        for fdata in data['frames']:
            frame = []
            for row in fdata:
                rdata = []
                for col in row:
                    if col:
                        rdata.append(Color(col[0], col[1], col[2]))
                    else:
                        rdata.append(None)
                frame.append(rdata)
            v.frames.append(frame)
        return v


def make_test_video(w: int, h: int, num_frames: int = 60, fps: float = 15) -> Video:
    v = Video(w, h, fps)
    for fi in range(num_frames):
        t = fi / fps
        frame: list[list[Color | None]] = []
        for y in range(h):
            row: list[Color | None] = []
            for x in range(w):
                nx, ny = x / w, y / h
                v1 = math.sin(nx * 6 + t * 2) * math.cos(ny * 4 + t * 1.5)
                v2 = math.sin((nx + ny) * 5 + t * 3) * 0.5
                val = v1 * 0.7 + v2 * 0.3
                val = max(-1, min(1, val))
                hue = (nx * 0.5 + ny * 0.3 + t * 0.1) % 1.0
                bright = 0.1 + (val * 0.5 + 0.5) * 0.8
                col = Color.from_hsv(hue, 0.75, bright)
                row.append(col)
            frame.append(row)
        v.frames.append(frame)
    return v


def make_color_bars(w: int, h: int, num_frames: int = 30, fps: float = 10) -> Video:
    v = Video(w, h, fps)
    bars = [
        Color(255, 0, 0), Color(255, 255, 0), Color(0, 255, 0),
        Color(0, 255, 255), Color(0, 0, 255), Color(255, 0, 255),
        Color(255, 255, 255), Color(0, 0, 0),
    ]
    for fi in range(num_frames):
        t = fi / fps
        frame: list[list[Color | None]] = []
        for y in range(h):
            row: list[Color | None] = []
            offset = int(t * 2 * w / len(bars)) % w
            for x in range(w):
                bi = ((x + offset) * len(bars)) // w
                col = bars[bi % len(bars)]
                row.append(col.mul(1 - 0.3 * (y / h)))
            frame.append(row)
        v.frames.append(frame)
    return v


def make_spinning_donut_video(w: int, h: int, num_frames: int = 60, fps: float = 15) -> Video:
    v = Video(w, h, fps)
    A, B = 0.0, 0.0
    for fi in range(num_frames):
        t = fi / fps
        A = t * 1.5
        B = t * 0.8
        frame: list[list[Color | None]] = []
        zb = [[0.0] * w for _ in range(h)]
        for _iy in range(h):
            row: list[Color | None] = [None] * w
            frame.append(row)
        theta = 0.0
        while theta < 2 * math.pi:
            theta += 0.07
            phi = 0.0
            while phi < 2 * math.pi:
                phi += 0.02
                costheta, sintheta = math.cos(theta), math.sin(theta)
                cosphi, sinphi = math.cos(phi), math.sin(phi)
                h1 = 1 + 0.5 * cosphi
                x = h1 * costheta
                y = h1 * sintheta
                z = 0.5 * sinphi
                d = z * math.cos(B) + x * math.sin(B)
                x2 = x * math.cos(B) - z * math.sin(B)
                z2 = d
                d = y * math.cos(A) - z2 * math.sin(A)
                y2 = y * math.sin(A) + z2 * math.cos(A)
                z3 = d
                ooz = 1 / (z3 + 5)
                xp = int(w / 2 + x2 * ooz * w * 0.4)
                yp = int(h / 2 - y2 * ooz * h * 0.3)
                if 0 <= xp < w and 0 <= yp < h:
                    if ooz > zb[yp][xp]:
                        zb[yp][xp] = ooz
                        lum = max(0, min(1, (x2 * y2 * z3) * 0.5 + 0.5))
                        vv = int(lum * 200) + 55
                        frame[yp][xp] = Color(vv, vv, vv)
        v.frames.append(frame)
    return v
