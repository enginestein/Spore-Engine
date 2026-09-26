"""Convert images/videos to plain ASCII text (no ANSI escape codes).

Output is pure copyable text - suitable for paste into any text document.
"""
from __future__ import annotations
import time

from ..core.glyphs import SHADE_CHARS
from ..core.term import CHAR_ASPECT
from .ffmpeg import (FFmpegError, FFmpegPipe, probe_fps as _probe_fps,
                     probe_size as _probe_size)

#: The canonical ramp, re-exported so this module has one name for it.
SHADE_DEFAULT = SHADE_CHARS
SHADE_REV = SHADE_CHARS[::-1]
SHADE_RICH = " .'`^\",:;Il!i><~+_-?][}{1)(|\\/tfjrxnuvczXYUJCLQ0OZmwqpdbkhao*#MW&8%B@$"
SHADE_BLOCK = ' .░▒▓█'


def _gif_frame_count(path: str) -> int:
    try:
        from PIL import Image
        with Image.open(path) as img:
            return getattr(img, 'n_frames', 1)
    except Exception:
        return 1


def is_animated(path: str) -> bool:
    ext = path.lower().rsplit('.', 1)[-1]
    if ext == 'gif':
        return _gif_frame_count(path) > 1
    return ext in ('mp4', 'mkv', 'avi', 'webm')


def image_to_glyph(path: str, width: int = 80, height: int | None = None,
                   shade: str = SHADE_DEFAULT, invert: bool = False) -> str:
    """Load an image file, return plain ASCII glyph text (no ANSI codes)."""
    try:
        from PIL import Image
    except ImportError as exc:  # pragma: no cover - depends on the env
        raise RuntimeError(
            'PIL/Pillow is required for image conversion; install the '
            '"media" extra (pip install spore-engine[media])'
        ) from exc

    with Image.open(path) as src:
        img = src.convert('L')
    iw, ih = img.size
    if height is None:
        height = max(1, int(width * (ih / iw) * CHAR_ASPECT))
    img = img.resize((width, height), Image.LANCZOS)

    s = SHADE_REV if invert else shade
    lines: list[str] = []
    for y in range(height):
        line = ''
        for x in range(width):
            lum = img.getpixel((x, y))
            ci = int(lum / 255 * (len(s) - 1))
            line += s[ci]
        lines.append(line.rstrip())
    return '\n'.join(lines)


def image_to_glyph_colored(path: str, width: int = 80,
                           height: int | None = None,
                           shade: str = SHADE_DEFAULT,
                           invert: bool = False
                           ) -> tuple[str, list[list[tuple[int, int, int]]]]:
    """Load image, return (text_string, color_grid).

    - text_string: plain ASCII glyphs (one char per pixel)
    - color_grid[y][x] = (R, G, B) matching the original pixel colour

    ``text_string`` is *not* right-stripped, so ``len(text[y])`` always equals
    ``len(color_grid[y])``. The two are meant to be consumed together with
    ``zip(text[y], color_grid[y])``, and stripping trailing blanks from the
    text while leaving the colour grid full width silently shifted every
    column after the first space.
    """
    from PIL import Image
    with Image.open(path) as src:
        img = src.convert('RGB')
    iw, ih = img.size
    if height is None:
        height = max(1, int(width * (ih / iw) * CHAR_ASPECT))
    img_small = img.resize((width, height), Image.LANCZOS)
    if invert:
        shade = SHADE_REV if shade == SHADE_DEFAULT else shade[::-1]

    lines: list[str] = []
    colors: list[list[tuple[int, int, int]]] = []
    for y in range(height):
        line = ''
        row: list[tuple[int, int, int]] = []
        for x in range(width):
            r, g, b = img_small.getpixel((x, y))
            lum = (0.299 * r + 0.587 * g + 0.114 * b) / 255
            ci = int(lum * (len(shade) - 1))
            line += shade[ci]
            row.append((r, g, b))
        lines.append(line)
        colors.append(row)
    return '\n'.join(lines), colors


def video_to_glyph_frames(path: str, width: int = 80,
                          height: int | None = None,
                          shade: str = SHADE_DEFAULT, invert: bool = False,
                          max_frames: int = 0,
                          fps: float | None = None) -> list[str]:
    """Extract video frames as plain ASCII text strings.

    Uses ffmpeg under the hood.  Each string is a rectangular block of
    text characters separated by newlines.
    """
    ext = path.lower().rsplit('.', 1)[-1]
    if ext == 'gif':
        return _gif_to_text_frames(path, width, height, shade, invert, max_frames)

    iw, ih = _probe_size(path)
    src_fps = _probe_fps(path)
    if height is None:
        height = max(1, int(width * (ih / max(iw, 1)) * CHAR_ASPECT))
    if fps is None:
        fps = src_fps

    s = SHADE_REV if invert else shade
    cmd = ['-v', '0', '-i', path]
    if fps != src_fps:
        cmd += ['-vf', f'fps={fps}']
    cmd += ['-f', 'rawvideo', '-pix_fmt', 'gray', '-']

    frame_size = iw * ih
    frames: list[str] = []
    frame_count = 0

    with FFmpegPipe(cmd) as pipe:
        while True:
            raw = pipe.read(frame_size)
            if not raw or len(raw) < frame_size:
                break

            lines: list[str] = []
            for y in range(height):
                line = ''
                for x in range(width):
                    sx = int(x / width * iw)
                    sy = int(y / height * ih)
                    lum = raw[sy * iw + sx]
                    ci = int(lum / 255 * (len(s) - 1))
                    line += s[ci]
                lines.append(line.rstrip())
            frames.append('\n'.join(lines))
            frame_count += 1

            if max_frames > 0 and frame_count >= max_frames:
                pipe.terminate()
                break

    if not frames:
        raise FFmpegError(f'ffmpeg produced no frames from {path}')
    return frames


def _gif_to_text_frames(path: str, width: int = 80,
                        height: int | None = None,
                        shade: str = SHADE_DEFAULT, invert: bool = False,
                        max_frames: int = 0) -> list[str]:
    """Extract animated GIF frames as plain text."""
    from PIL import Image
    s = SHADE_REV if invert else shade
    frames: list[str] = []
    with Image.open(path) as img:
        n = getattr(img, 'n_frames', 1)
        iw, ih = img.size
        if height is None:
            height = max(1, int(width * (ih / iw) * CHAR_ASPECT))

        for fi in range(n):
            if max_frames > 0 and fi >= max_frames:
                break
            img.seek(fi)
            frame = img.convert('L').resize((width, height), Image.LANCZOS)
            lines: list[str] = []
            for y in range(height):
                line = ''
                for x in range(width):
                    lum = frame.getpixel((x, y))
                    ci = int(lum / 255 * (len(s) - 1))
                    line += s[ci]
                lines.append(line.rstrip())
            frames.append('\n'.join(lines))
    return frames


def video_to_glyph_colored_frames(
    path: str, width: int = 80, height: int | None = None,
    shade: str = SHADE_DEFAULT, invert: bool = False,
    max_frames: int = 0, fps: float | None = None
) -> list[tuple[str, list[list[tuple[int, int, int]]]]]:
    """Extract video frames as (text, color_grid) pairs.

    Works with videos and animated GIFs.
    """
    ext = path.lower().rsplit('.', 1)[-1]
    if ext == 'gif':
        return _gif_colored_frames(path, width, height, shade, invert, max_frames)

    iw, ih = _probe_size(path)
    src_fps = _probe_fps(path)
    if height is None:
        height = max(1, int(width * (ih / max(iw, 1)) * CHAR_ASPECT))
    if fps is None:
        fps = src_fps

    s = SHADE_REV if invert else shade
    cmd = ['-v', '0', '-i', path]
    if fps != src_fps:
        cmd += ['-vf', f'fps={fps}']
    cmd += ['-f', 'rawvideo', '-pix_fmt', 'rgb24', '-']

    frame_size = iw * ih * 3
    frames: list[tuple[str, list[list[tuple[int, int, int]]]]] = []
    frame_count = 0

    with FFmpegPipe(cmd) as pipe:
        while True:
            raw = pipe.read(frame_size)
            if not raw or len(raw) < frame_size:
                break

            lines: list[str] = []
            colors: list[list[tuple[int, int, int]]] = []
            for y in range(height):
                line = ''
                row: list[tuple[int, int, int]] = []
                for x in range(width):
                    sx = int(x / width * iw)
                    sy = int(y / height * ih)
                    idx = (sy * iw + sx) * 3
                    r, g, b = raw[idx], raw[idx + 1], raw[idx + 2]
                    lum = (0.299 * r + 0.587 * g + 0.114 * b) / 255
                    ci = int(lum * (len(s) - 1))
                    line += s[ci]
                    row.append((r, g, b))
                lines.append(line)
                colors.append(row)
            frames.append(('\n'.join(lines), colors))
            frame_count += 1

            if max_frames > 0 and frame_count >= max_frames:
                pipe.terminate()
                break

    if not frames:
        raise FFmpegError(f'ffmpeg produced no frames from {path}')
    return frames


def _gif_colored_frames(
    path: str, width: int = 80, height: int | None = None,
    shade: str = SHADE_DEFAULT, invert: bool = False,
    max_frames: int = 0
) -> list[tuple[str, list[list[tuple[int, int, int]]]]]:
    """Extract animated GIF frames as (text, color_grid) pairs."""
    from PIL import Image
    s = SHADE_REV if invert else shade
    frames: list[tuple[str, list[list[tuple[int, int, int]]]]] = []
    with Image.open(path) as img:
        n = getattr(img, 'n_frames', 1)
        iw, ih = img.size
        if height is None:
            height = max(1, int(width * (ih / iw) * CHAR_ASPECT))

        for fi in range(n):
            if max_frames > 0 and fi >= max_frames:
                break
            img.seek(fi)
            frame_rgb = img.convert('RGB').resize((width, height), Image.LANCZOS)
            frame_l = frame_rgb.convert('L')
            lines: list[str] = []
            colors: list[list[tuple[int, int, int]]] = []
            for y in range(height):
                line = ''
                row: list[tuple[int, int, int]] = []
                for x in range(width):
                    r, g, b = frame_rgb.getpixel((x, y))
                    lum = frame_l.getpixel((x, y))
                    ci = int(lum / 255 * (len(s) - 1))
                    line += s[ci]
                    row.append((r, g, b))
                # Not stripped: the text and the colour grid are zipped
                # together by the caller and must stay column-aligned.
                lines.append(line)
                colors.append(row)
            frames.append(('\n'.join(lines), colors))
    return frames


def play_glyph_video(frames: list[str], fps: float = 15,
                     loop: bool = False, clear_screen: bool = True):
    """Play pre-extracted glyph frames in the terminal as plain text.

    Each frame is printed directly to stdout (no ANSI colour codes).
    Use Ctrl+C to stop.
    """
    try:
        while True:
            for fi, frame in enumerate(frames):
                if clear_screen:
                    print('\033[H', end='', flush=True)
                print(frame, flush=True)
                if fi < len(frames) - 1:
                    time.sleep(1.0 / fps)
                else:
                    if loop:
                        time.sleep(1.0 / fps)
                    else:
                        return
    except KeyboardInterrupt:
        pass



