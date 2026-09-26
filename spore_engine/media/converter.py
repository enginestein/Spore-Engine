from __future__ import annotations
import os
from ..core.canvas import Canvas
from ..core.glyphs import SHADE_CHARS
from ..core.color import Color
from ..core.term import CHAR_ASPECT
from .ffmpeg import (FFmpegError, FFmpegPipe, probe_duration, probe_fps, probe_size)
from .video import Video, FramePlayer

#: Re-exported from core.glyphs so the ramp is defined once.
SHADE = SHADE_CHARS
SHADE_REV = SHADE_CHARS[::-1]


def _aspect_height(width: int, src_w: int, src_h: int) -> int:
    """Rows for a target width that keeps the source's aspect undistorted.

    A terminal cell is taller than it is wide, so a naively square mapping
    stretches the image vertically. The correction factor comes from
    :data:`~spore_engine.core.term.CHAR_ASPECT` rather than a literal 0.45
    repeated at each call site.
    """
    return max(1, int(width * (src_h / src_w) * CHAR_ASPECT))



# -------------------------------------------------------------------
# IMAGE -> ASCII
# -------------------------------------------------------------------

def image_to_canvas(path: str, width: int = 80, height: int | None = None,
                    invert: bool = False, color: bool = True) -> Canvas:
    """Load an image file and convert to an ASCII Canvas.

    Uses pillow when installed and falls back to ffmpeg otherwise, so neither
    is a hard dependency. Raises a typed error if neither can decode the file
    rather than returning a blank canvas.

    ``invert`` means different things in the two modes, because there is
    nothing to invert in one of them:

    - ``color=True`` (the default) writes the source RGB as the foreground, so
      ``invert`` inverts those channels. It previously did nothing at all in
      this mode, because the glyph was a constant ``'@'`` and there was no
      ramp to reverse.
    - ``color=False`` packs brightness into the glyph, so ``invert`` reverses
      the shade ramp instead.
    """
    try:
        from PIL import Image
    except ImportError:
        return _image_to_canvas_ffmpeg(path, width, height, invert, color)

    if not os.path.isfile(path):
        raise FileNotFoundError(f'image file not found: {path}')
    with Image.open(path) as src:
        img = src.convert('RGB')
    iw, ih = img.size
    if height is None:
        height = _aspect_height(width, iw, ih)
    img = img.resize((width, height), Image.LANCZOS)

    c = Canvas(width, height)
    shade = SHADE_REV if invert else SHADE

    for y in range(height):
        for x in range(width):
            r, g, b = img.getpixel((x, y))
            col = Color(r, g, b)
            if color:
                if invert:
                    col = Color(255 - r, 255 - g, 255 - b)
                c.set_pixel(x, y, '@', col)
            else:
                lum = col.luminance / 255
                ci = int(lum * (len(shade) - 1))
                c.set_pixel(x, y, shade[ci], Color(180, 180, 180))
    return c


def _image_to_canvas_ffmpeg(path: str, width: int = 80, height: int | None = None,
                             invert: bool = False, color: bool = True) -> Canvas:
    """Fallback: use ffmpeg to decode a single image to raw RGB."""
    iw, ih = probe_size(path)
    with FFmpegPipe(['-v', '0', '-i', path,
                     '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-']) as pipe:
        data = pipe.read_all()

    if not data:
        raise FFmpegError(f'ffmpeg decoded no pixels from {path}')

    if height is None:
        height = _aspect_height(width, iw, ih)

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
                    if invert:
                        col = Color(255 - r, 255 - g, 255 - b)
                    c.set_pixel(x, y, '@', col)
                else:
                    lum = col.luminance / 255
                    ci = int(lum * (len(shade) - 1))
                    c.set_pixel(x, y, shade[ci], Color(180, 180, 180))
    return c


# -------------------------------------------------------------------
# VIDEO -> ASCII
# -------------------------------------------------------------------

# Kept as module-level aliases so the old private names still resolve.
_probe_size = probe_size
_probe_fps = probe_fps


def video_to_ascii(path: str, width: int = 80, height: int | None = None,
                   fps: float | None = None, max_frames: int = 0,
                   invert: bool = False, color: bool = True,
                   on_progress: callable | None = None) -> Video:
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

    Raises:
        FFmpegUnavailable: ffmpeg/ffprobe is not installed.
        FFmpegError: the file has no decodable video stream, or ffmpeg
            produced no frames. A zero-frame result used to be returned as an
            empty Video, which then divided by zero in FramePlayer.

    The ffmpeg process is always killed and reaped, including when
    ``on_progress`` raises or ``max_frames`` cuts the read short.
    """
    iw, ih = probe_size(path)
    src_fps = probe_fps(path)
    if height is None:
        height = _aspect_height(width, iw, ih)
    if fps is None:
        fps = src_fps
    if fps <= 0:
        raise ValueError(f'fps must be positive, got {fps}')

    v = Video(width, height, fps)

    fps_filter = f'fps={fps}' if fps != src_fps else ''

    cmd = ['-v', '0', '-i', path]
    if fps_filter:
        cmd += ['-vf', fps_filter]
    cmd += ['-f', 'rawvideo', '-pix_fmt', 'rgb24', '-']

    duration = probe_duration(path)
    total_frames_expected = 0
    if duration > 0:
        total_frames_expected = int(duration * fps)
        if max_frames > 0:
            total_frames_expected = min(total_frames_expected, max_frames)

    frame_size = iw * ih * 3
    frame_count = 0

    with FFmpegPipe(cmd) as pipe:
        while True:
            raw = pipe.read(frame_size)
            if not raw or len(raw) < frame_size:
                break

            frame_data: list[list[Color | None]] = []
            for y in range(ih):
                row: list[Color | None] = []
                for x in range(iw):
                    idx = (y * iw + x) * 3
                    row.append(Color(raw[idx], raw[idx + 1], raw[idx + 2]))
                frame_data.append(row)

            out_frame: list[list[Color | None]] = []
            for y in range(height):
                row: list[Color | None] = []
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
                on_progress(min(1.0, frame_count / total_frames_expected))

            if max_frames > 0 and frame_count >= max_frames:
                pipe.terminate()
                break

    if frame_count == 0:
        raise FFmpegError(
            f'ffmpeg produced no frames from {path} (it may be audio-only, '
            'empty, or corrupt)')
    return v


def video_to_player(path: str, width: int = 80, height: int | None = None,
                    fps: float | None = None, max_frames: int = 0,
                    loop: bool = True, invert: bool = False,
                    color: bool = True,
                    on_progress: callable | None = None) -> FramePlayer:
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
        data: list[list[Color | None]] = []
        for y in range(canvas.h):
            row: list[Color | None] = []
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
