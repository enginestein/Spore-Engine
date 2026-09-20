"""Convert images/videos to plain ASCII text (no ANSI escape codes).

Output is pure copyable text - suitable for paste into any text document.
"""
from __future__ import annotations
import math, os, time, subprocess
from typing import Optional

SHADE_DEFAULT = ' .:-=+*#%@'
SHADE_REV = '@%#*+=-:. '
SHADE_RICH = " .'`^\",:;Il!i><~+_-?][}{1)(|\\/tfjrxnuvczXYUJCLQ0OZmwqpdbkhao*#MW&8%B@$"
SHADE_BLOCK = ' .░▒▓█'


def _load_image_pil(path: str):
    from PIL import Image
    return Image.open(path)


def _gif_frame_count(path: str) -> int:
    try:
        from PIL import Image
        img = Image.open(path)
        return getattr(img, 'n_frames', 1)
    except Exception:
        return 1


def is_animated(path: str) -> bool:
    ext = path.lower().rsplit('.', 1)[-1]
    if ext == 'gif':
        return _gif_frame_count(path) > 1
    return ext in ('mp4', 'mkv', 'avi', 'webm')


def image_to_glyph(path: str, width: int = 80, height: Optional[int] = None,
                   shade: str = SHADE_DEFAULT, invert: bool = False) -> str:
    """Load an image file, return plain ASCII glyph text (no ANSI codes)."""
    try:
        from PIL import Image
    except ImportError:
        raise RuntimeError('PIL/Pillow is required for image conversion')

    img = Image.open(path).convert('L')
    iw, ih = img.size
    if height is None:
        height = max(1, int(width * (ih / iw) * 0.45))
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
                           height: Optional[int] = None,
                           shade: str = SHADE_DEFAULT,
                           invert: bool = False
                           ) -> tuple[str, list[list[tuple[int, int, int]]]]:
    """Load image, return (text_string, color_grid).

    - text_string: plain ASCII glyphs (one char per pixel)
    - color_grid[y][x] = (R, G, B) matching the original pixel colour
    """
    from PIL import Image
    img = Image.open(path).convert('RGB')
    iw, ih = img.size
    if height is None:
        height = max(1, int(width * (ih / iw) * 0.45))
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
        lines.append(line.rstrip())
        colors.append(row)
    return '\n'.join(lines), colors


def _gif_frames_pil(path: str) -> list[tuple[str, list[list[tuple[int, int, int]]]]]:
    """Extract each frame of an animated GIF as coloured glyph data."""
    from PIL import Image
    img = Image.open(path)
    frames: list[tuple[str, list[list[tuple[int, int, int]]]]] = []
    try:
        while True:
            rgb = img.convert('RGB')
            frames.append(('', []))
            img.seek(img.tell() + 1)
    except EOFError:
        pass
    return frames


def video_to_glyph_frames(path: str, width: int = 80,
                          height: Optional[int] = None,
                          shade: str = SHADE_DEFAULT, invert: bool = False,
                          max_frames: int = 0,
                          fps: Optional[float] = None) -> list[str]:
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
        height = max(1, int(width * (ih / max(iw, 1)) * 0.45))
    if fps is None:
        fps = src_fps

    s = SHADE_REV if invert else shade
    cmd = ['ffmpeg', '-v', '0', '-i', path]
    if fps != src_fps:
        cmd += ['-vf', f'fps={fps}']
    cmd += ['-f', 'rawvideo', '-pix_fmt', 'gray', '-']

    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                stderr=subprocess.DEVNULL)
    except FileNotFoundError:
        raise RuntimeError('ffmpeg is required for video conversion')

    frame_size = iw * ih
    frames: list[str] = []
    frame_count = 0

    while True:
        raw = proc.stdout.read(frame_size)
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
            proc.terminate()
            break

    proc.wait()
    return frames


def _gif_to_text_frames(path: str, width: int = 80,
                        height: Optional[int] = None,
                        shade: str = SHADE_DEFAULT, invert: bool = False,
                        max_frames: int = 0) -> list[str]:
    """Extract animated GIF frames as plain text."""
    from PIL import Image
    s = SHADE_REV if invert else shade
    frames: list[str] = []
    img = Image.open(path)
    n = getattr(img, 'n_frames', 1)
    iw, ih = img.size
    if height is None:
        height = max(1, int(width * (ih / iw) * 0.45))

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
    path: str, width: int = 80, height: Optional[int] = None,
    shade: str = SHADE_DEFAULT, invert: bool = False,
    max_frames: int = 0, fps: Optional[float] = None
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
        height = max(1, int(width * (ih / max(iw, 1)) * 0.45))
    if fps is None:
        fps = src_fps

    s = SHADE_REV if invert else shade
    cmd = ['ffmpeg', '-v', '0', '-i', path]
    if fps != src_fps:
        cmd += ['-vf', f'fps={fps}']
    cmd += ['-f', 'rawvideo', '-pix_fmt', 'rgb24', '-']

    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                stderr=subprocess.DEVNULL)
    except FileNotFoundError:
        raise RuntimeError('ffmpeg is required for video conversion')

    frame_size = iw * ih * 3
    frames: list[tuple[str, list[list[tuple[int, int, int]]]]] = []
    frame_count = 0

    while True:
        raw = proc.stdout.read(frame_size)
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
            lines.append(line.rstrip())
            colors.append(row)
        frames.append(('\n'.join(lines), colors))
        frame_count += 1

        if max_frames > 0 and frame_count >= max_frames:
            proc.terminate()
            break

    proc.wait()
    return frames


def _gif_colored_frames(
    path: str, width: int = 80, height: Optional[int] = None,
    shade: str = SHADE_DEFAULT, invert: bool = False,
    max_frames: int = 0
) -> list[tuple[str, list[list[tuple[int, int, int]]]]]:
    """Extract animated GIF frames as (text, color_grid) pairs."""
    from PIL import Image
    s = SHADE_REV if invert else shade
    frames: list[tuple[str, list[list[tuple[int, int, int]]]]] = []
    img = Image.open(path)
    n = getattr(img, 'n_frames', 1)
    iw, ih = img.size
    if height is None:
        height = max(1, int(width * (ih / iw) * 0.45))

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
            lines.append(line.rstrip())
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
