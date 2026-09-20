from __future__ import annotations
import math, os, subprocess, tempfile, shutil, json
from typing import Optional
from ..core.canvas import Canvas
from ..core.color import Color
from .video import Video, VideoFrame, FramePlayer


SHADE = ' .:-=+*#%@'
SHADE_REV = '@%#*+=-:. '


# -------------------------------------------------------------------
# IMAGE -> ASCII
# -------------------------------------------------------------------

def image_to_canvas(path: str, width: int = 80, height: Optional[int] = None,
                    invert: bool = False, color: bool = True) -> Canvas:
    """Load an image file and convert to an ASCII Canvas via ffmpeg/PIL."""
    try:
        from PIL import Image
    except ImportError:
        return _image_to_canvas_ffmpeg(path, width, height, invert, color)

    img = Image.open(path).convert('RGB')
    iw, ih = img.size
    if height is None:
        height = max(1, int(width * (ih / iw) * 0.45))
    img = img.resize((width, height), Image.LANCZOS)

    c = Canvas(width, height)
    shade = SHADE_REV if invert else SHADE

    for y in range(height):
        for x in range(width):
            r, g, b = img.getpixel((x, y))
            col = Color(r, g, b)
            if color:
                c.set_pixel(x, y, '@', col)
            else:
                lum = col.luminance / 255
                ci = int(lum * (len(shade) - 1))
                c.set_pixel(x, y, shade[ci], Color(180, 180, 180))
    return c


def _image_to_canvas_ffmpeg(path: str, width: int = 80, height: Optional[int] = None,
                             invert: bool = False, color: bool = True) -> Canvas:
    """Fallback: use ffmpeg to decode a single image to raw RGB."""
    try:
        pipe = subprocess.Popen(
            ['ffmpeg', '-v', '0', '-i', path,
             '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        data = pipe.stdout.read()
        pipe.wait()
    except FileNotFoundError:
        raise RuntimeError('Neither PIL nor ffmpeg is available')

    if not data:
        raise ValueError(f'Could not decode image: {path}')

    iw, ih = _probe_size(path)
    if height is None:
        height = max(1, int(width * (ih / iw) * 0.45))

    c = Canvas(width, height)
    shade = SHADE_REV if invert else SHADE

    for y in range(height):
        for x in range(width):
            sx = int(x / width * iw)
            sy = int(y / height * ih)
            idx = (sy * iw + sx) * 3
            if idx + 2 < len(data):
                r, g, b = data[idx], data[idx + 1], data[idx + 2]
                col = Color(r, g, b)
                if color:
                    c.set_pixel(x, y, '@', col)
                else:
                    lum = col.luminance / 255
                    ci = int(lum * (len(shade) - 1))
                    c.set_pixel(x, y, shade[ci], Color(180, 180, 180))
    return c


# -------------------------------------------------------------------
# VIDEO -> ASCII
# -------------------------------------------------------------------

def _probe_size(path: str) -> tuple[int, int]:
    try:
        out = subprocess.check_output(
            ['ffprobe', '-v', '0', '-select_streams', 'v:0',
             '-show_entries', 'stream=width,height',
             '-of', 'csv=p=0', path])
        parts = out.decode().strip().split(',')
        return int(parts[0]), int(parts[1])
    except Exception:
        return (0, 0)


def _probe_fps(path: str) -> float:
    try:
        out = subprocess.check_output(
            ['ffprobe', '-v', '0', '-select_streams', 'v:0',
             '-show_entries', 'stream=r_frame_rate',
             '-of', 'csv=p=0', path])
        parts = out.decode().strip().split('/')
        return float(parts[0]) / float(parts[1]) if len(parts) == 2 else 30.0
    except Exception:
        return 30.0


def video_to_ascii(path: str, width: int = 80, height: Optional[int] = None,
                   fps: Optional[float] = None, max_frames: int = 0,
                   invert: bool = False, color: bool = True,
                   on_progress: Optional[callable] = None) -> Video:
    """Convert a video file to an ASCII Video using ffmpeg.

    Args:
        path: Path to video file (mp4, mkv, avi, gif, etc.)
        width: Output ASCII width in characters
        height: Output ASCII height (auto if None)
        fps: Output framerate (auto from source if None)
        max_frames: Max frames to extract (0 = all)
        invert: Invert luminance->character mapping
        color: Preserve color (True) or grayscale (False)
        on_progress: Callback(progress_float) during conversion

    Returns:
        Video object ready for .to_player()
    """
    iw, ih = _probe_size(path)
    src_fps = _probe_fps(path)
    if height is None:
        height = max(1, int(width * (ih / iw) * 0.45))
    if fps is None:
        fps = src_fps

    shade = SHADE_REV if invert else SHADE
    v = Video(width, height, fps)

    fps_filter = f'fps={fps}' if fps != src_fps else ''

    cmd = ['ffmpeg', '-v', '0', '-i', path]
    if fps_filter:
        cmd += ['-vf', fps_filter]
    cmd += ['-f', 'rawvideo', '-pix_fmt', 'rgb24', '-']

    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                stderr=subprocess.DEVNULL)
    except FileNotFoundError:
        raise RuntimeError('ffmpeg is required for video conversion')

    frame_size = iw * ih * 3
    frame_count = 0
    total_frames_expected = 0

    try:
        dur_out = subprocess.check_output(
            ['ffprobe', '-v', '0', '-show_entries', 'format=duration',
             '-of', 'csv=p=0', path])
        duration = float(dur_out.decode().strip())
        total_frames_expected = int(duration * fps)
        if max_frames > 0:
            total_frames_expected = min(total_frames_expected, max_frames)
    except Exception:
        total_frames_expected = 0

    while True:
        raw = proc.stdout.read(frame_size)
        if not raw or len(raw) < frame_size:
            break

        frame_data: list[list[Optional[Color]]] = []
        for y in range(ih):
            row: list[Optional[Color]] = []
            for x in range(iw):
                idx = (y * iw + x) * 3
                row.append(Color(raw[idx], raw[idx + 1], raw[idx + 2]))
            frame_data.append(row)

        ascii_row_cache: dict[tuple[int, int], list[Optional[Color]]] = {}
        out_frame: list[list[Optional[Color]]] = []
        for y in range(height):
            row: list[Optional[Color]] = []
            for x in range(width):
                sx = int(x / width * iw)
                sy = int(y / height * ih)
                col = frame_data[sy][sx]
                if color:
                    row.append(col)
                else:
                    lum = col.luminance
                    row.append(Color(lum, lum, lum))
            out_frame.append(row)

        v.frames.append(out_frame)
        frame_count += 1

        if on_progress and total_frames_expected > 0:
            on_progress(frame_count / total_frames_expected)

        if max_frames > 0 and frame_count >= max_frames:
            proc.terminate()
            break

    proc.wait()
    return v


def video_to_player(path: str, width: int = 80, height: Optional[int] = None,
                    fps: Optional[float] = None, max_frames: int = 0,
                    loop: bool = True, invert: bool = False,
                    color: bool = True,
                    on_progress: Optional[callable] = None) -> FramePlayer:
    """Convert a video file directly to a FramePlayer (ready to play)."""
    v = video_to_ascii(path, width, height, fps, max_frames,
                       invert, color, on_progress)
    return v.to_player(loop=loop)


# -------------------------------------------------------------------
# SCREEN CAPTURE (bonus: record terminal as ASCII video)
# -------------------------------------------------------------------

class ScreenRecorder:
    """Records Canvas frames into a Video for later playback/save."""

    def __init__(self, width: int, height: int, fps: float = 15):
        self.video = Video(width, height, fps)
        self.count = 0

    def record_frame(self, canvas: Canvas):
        data: list[list[Optional[Color]]] = []
        for y in range(canvas.h):
            row: list[Optional[Color]] = []
            for x in range(canvas.w):
                cell = canvas.buffer[y][x]
                row.append(cell.fg or Color(0, 0, 0))
            data.append(row)
        self.video.frames.append(data)
        self.count += 1

    def save(self, path: str):
        self.video.save(path)

    def to_player(self, loop: bool = True) -> FramePlayer:
        return self.video.to_player(loop=loop)
