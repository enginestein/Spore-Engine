"""Tests for the media layer.

Pillow and ffmpeg are optional extras, so everything here is skipped when
they are missing -- but on a machine that has them the media package was
almost entirely untested (glyphart at 6%, img3d at 7%, ffmpeg at 15%), which
is a poor place for untested code that shells out to another process and
parses untyped pixel data.

The emphasis is on the boundaries: image files the caller supplies, video
probing, and the process-cleanup paths in FFmpegPipe, which are the places
where a failure turns into a hung terminal rather than an exception.
"""

from __future__ import annotations

import io
import os
import subprocess
import sys

import pytest

from spore_engine import Canvas, Color, Gradient, Video
from spore_engine.media import (ansi_io, converter, ffmpeg, glyphart, imaging,
                                video)

pytest.importorskip('PIL', reason='Pillow is in the "media" extra')
from PIL import Image, UnidentifiedImageError

requires_ffmpeg = pytest.mark.skipif(not ffmpeg.have_ffmpeg(),
                                     reason='ffmpeg is not installed')
requires_ffprobe = pytest.mark.skipif(not ffmpeg.have_ffprobe(),
                                      reason='ffprobe is not installed')


# --- fixtures ------------------------------------------------------------

@pytest.fixture
def rgb_image(tmp_path):
    """A small image with a known, non-uniform colour layout."""
    img = Image.new('RGB', (32, 16), (10, 10, 40))
    for x in range(16):
        for y in range(16):
            img.putpixel((x, y), (10 + x * 15, 40, 255 - y * 15))
    path = tmp_path / 'ramp.png'
    img.save(path)
    return str(path)


@pytest.fixture
def gray_image(tmp_path):
    img = Image.new('L', (32, 16))
    for x in range(32):
        for y in range(16):
            img.putpixel((x, y), (x * 8) % 256)
    path = tmp_path / 'gray.png'
    img.save(path)
    return str(path)


@pytest.fixture
def gif_image(tmp_path):
    frames = []
    for i in range(3):
        f = Image.new('RGB', (8, 8), (i * 80, 255 - i * 80, 128))
        frames.append(f.convert('P', palette=Image.ADAPTIVE))
    path = tmp_path / 'anim.gif'
    frames[0].save(path, save_all=True, append_images=frames[1:],
                   duration=100, loop=0)
    return str(path)


@pytest.fixture
def test_video_file(tmp_path):
    """A short real video, encoded by ffmpeg itself."""
    if not (ffmpeg.have_ffmpeg() and ffmpeg.have_ffprobe()):
        pytest.skip('ffmpeg/ffprobe not installed')
    path = tmp_path / 'clip.mp4'
    r = subprocess.run(
        ['ffmpeg', '-y', '-loglevel', 'error', '-f', 'lavfi', '-i',
         'testsrc=duration=1:size=64x48:rate=10', '-pix_fmt', 'yuv420p',
         str(path)],
        capture_output=True, text=True)
    if r.returncode != 0:
        pytest.skip(f'ffmpeg could not build a fixture: {r.stderr[:200]}')
    return str(path)


# --- glyphart -----------------------------------------------------------

def test_image_to_glyph_returns_the_requested_size(gray_image):
    out = glyphart.image_to_glyph(gray_image, width=20)
    lines = out.splitlines()
    assert len(lines[0]) == 20
    assert len(lines) >= 1
    # Only glyphs, no ANSI escapes: this is the plain-text entry point.
    assert '\x1b' not in out


def test_image_to_glyph_uses_only_the_given_ramp(gray_image):
    out = glyphart.image_to_glyph(gray_image, width=16, shade=' .oO@')
    assert set(out.replace('\n', '')) <= set(' .oO@')


def test_image_to_glyph_invert_flips_the_ramp(gray_image):
    normal = glyphart.image_to_glyph(gray_image, width=16, shade=' .oO@')
    inverted = glyphart.image_to_glyph(gray_image, width=16, shade=' .oO@',
                                       invert=True)
    assert normal != inverted
    ramp = ' .oO@'
    for a, b in zip(normal.replace('\n', ''), inverted.replace('\n', ''), strict=False):
        if a in ramp and b in ramp:
            assert ramp.index(a) + ramp.index(b) == len(ramp) - 1


def test_image_to_glyph_colored_pairs_glyphs_with_rgb(rgb_image):
    text, colors = glyphart.image_to_glyph_colored(rgb_image, width=16)
    lines = text.splitlines()
    assert len(colors) == len(lines)
    for row, line in zip(colors, lines, strict=False):
        assert len(row) == len(line)
        for r, g, b in row:
            assert 0 <= r <= 255 and 0 <= g <= 255 and 0 <= b <= 255


def test_image_to_glyph_colored_reports_the_real_pixel_colour(tmp_path):
    """The colour must come from the source pixel, not from the ramp index.

    If the colour were derived from the glyph index, a flat-coloured image
    would come back with every cell the same colour instead of the source RGB.
    """
    # Two solid halves, so the downscale to 4x4 keeps both regions intact.
    img = Image.new('RGB', (16, 16), (10, 40, 200))
    for y in range(16):
        for x in range(8):
            img.putpixel((x, y), (200, 20, 10))
    path = tmp_path / 'halves.png'
    img.save(path)
    text, colors = glyphart.image_to_glyph_colored(str(path), width=4, height=4)
    assert len(text.splitlines()) == 4
    for row in colors:
        assert len(row) == 4
    # Column 0 comes from the red half, column 3 from the blue half.
    for row in colors:
        r0, g0, b0 = row[0]
        r3, g3, b3 = row[3]
        assert r0 > 150 and g0 < 60, f'expected the red half, got {(r0, g0, b0)}'
        assert b3 > 150 and r3 < 60, f'expected the blue half, got {(r3, g3, b3)}'


def test_image_to_glyph_explicit_height_is_respected(gray_image):
    out = glyphart.image_to_glyph(gray_image, width=20, height=7)
    assert len(out.splitlines()) == 7


def test_image_to_glyph_rejects_a_non_image(gray_image, tmp_path):
    bogus = tmp_path / 'not.png'
    bogus.write_text('this is not a png')
    # Pillow raises UnidentifiedImageError; ffmpeg raises FFmpegError.
    with pytest.raises((UnidentifiedImageError, OSError, RuntimeError)):
        glyphart.image_to_glyph(str(bogus), width=8)


def test_image_to_glyph_reports_a_missing_file(tmp_path):
    with pytest.raises((FileNotFoundError, OSError)):
        glyphart.image_to_glyph(str(tmp_path / 'nope.png'), width=8)


def test_is_animated_is_false_for_a_still(gray_image):
    assert glyphart.is_animated(gray_image) is False


def test_is_animated_is_true_for_a_gif(gif_image):
    assert glyphart.is_animated(gif_image) is True


def test_is_animated_is_false_for_a_missing_file(tmp_path):
    assert glyphart.is_animated(str(tmp_path / 'nope.png')) is False


# --- video frames via glyphart ------------------------------------------

@requires_ffmpeg
@requires_ffprobe
def test_video_to_glyph_frames(test_video_file):
    frames = glyphart.video_to_glyph_frames(test_video_file, width=16, max_frames=3)
    assert 1 <= len(frames) <= 3
    for f in frames:
        assert '\x1b' not in f
        assert len(f.splitlines()[0]) == 16


@requires_ffmpeg
@requires_ffprobe
def test_video_to_glyph_colored_frames(test_video_file):
    frames = glyphart.video_to_glyph_colored_frames(test_video_file, width=12,
                                                    max_frames=2)
    assert 1 <= len(frames) <= 2
    for text, colors in frames:
        assert len(text.splitlines()) == len(colors)


@requires_ffmpeg
@requires_ffprobe
def test_video_frame_count_honours_max_frames(test_video_file):
    few = glyphart.video_to_glyph_frames(test_video_file, width=8, max_frames=1)
    more = glyphart.video_to_glyph_frames(test_video_file, width=8, max_frames=4)
    assert len(few) <= len(more)


# --- converter -----------------------------------------------------------

def test_image_to_canvas_produces_the_requested_size(rgb_image):
    c = converter.image_to_canvas(rgb_image, width=24, color=True)
    assert c.width == 24
    assert c.height > 0


def test_image_to_canvas_without_color_is_monochrome(rgb_image):
    """color=False encodes brightness in the glyph and flattens the ink.

    Every cell still gets a foreground so the result is legible on a terminal
    with a light background; what changes is that all of them are the same
    dim grey and the shading has moved into the character.
    """
    c = converter.image_to_canvas(rgb_image, width=12, color=False)
    inks = {cell.fg for row in c.buffer for cell in row if cell.fg}
    assert inks == {Color(180, 180, 180)}
    assert len({cell.char for row in c.buffer for cell in row}) > 1


def test_image_to_canvas_with_color_sets_foreground(rgb_image):
    c = converter.image_to_canvas(rgb_image, width=12, color=True)
    assert any(cell.fg is not None for row in c.buffer for cell in row)


def test_image_to_canvas_invert_differs(rgb_image):
    normal = converter.image_to_canvas(rgb_image, width=12, invert=False)
    inverted = converter.image_to_canvas(rgb_image, width=12, invert=True)
    assert [[c.fg for c in row] for row in normal.buffer] != \
           [[c.fg for c in row] for row in inverted.buffer]


@requires_ffmpeg
@requires_ffprobe
def test_video_to_ascii_returns_a_video(test_video_file):
    seen = []
    v = converter.video_to_ascii(test_video_file, width=12, max_frames=2,
                                 on_progress=lambda *a: seen.append(a))
    assert isinstance(v, Video)
    assert v.width == 12
    assert len(v.frames) >= 1
    assert seen, 'on_progress was never called'


@requires_ffmpeg
@requires_ffprobe
def test_video_to_player_returns_a_frame_player(test_video_file):
    from spore_engine import FramePlayer
    p = converter.video_to_player(test_video_file, width=10, max_frames=2)
    assert isinstance(p, FramePlayer)
    assert p.frame_count >= 1
    assert not p.done


# --- imaging -------------------------------------------------------------

def test_canvas_from_text_round_trips_dimensions():
    c = imaging.canvas_from_text('ab\ncde')
    assert c.width == 3
    assert c.height == 2
    assert c.buffer[0][0].char == 'a'
    assert c.buffer[1][2].char == 'e'


def test_canvas_from_text_rejects_empty_input():
    """Canvas forbids a zero dimension, so empty text needs a clear error."""
    with pytest.raises(ValueError, match='at least one visible character'):
        imaging.canvas_from_text('')


def test_canvas_to_ascii_rescales_for_terminal_aspect():
    """canvas_to_ascii halves the height for the character aspect ratio.

    It is a renderer, not a serializer -- export_ansi/parse_ansi is the
    lossless pair -- so a 3x2 canvas asked for width 3 comes back one row
    tall, and every row is exactly `width` characters.
    """
    c = Canvas(3, 2)
    for y, line in enumerate(('abc', 'def')):
        for x, ch in enumerate(line):
            c.set_pixel(x, y, ch)
    out = imaging.canvas_to_ascii(c, width=3, use_color=False)
    rows = out.splitlines()
    assert all(len(r) == 3 for r in rows)
    assert len(rows) == max(1, int(3 * (2 / 3) * 0.5))


def test_canvas_to_ascii_with_color_emits_escapes():
    c = Canvas(4, 2)
    for y in range(2):
        for x in range(4):
            c.set_pixel(x, y, '#', Color(255, 0, 0))
    out = imaging.canvas_to_ascii(c, width=4, use_color=True)
    assert '\x1b[' in out


def test_gradient_canvas_horizontal_is_constant_along_a_column():
    grad = Gradient(Color(0, 0, 0), Color(255, 255, 255))
    c = imaging.gradient_canvas(8, 4, grad, horizontal=True)
    for x in range(8):
        colours = {c.buffer[y][x].fg for y in range(4)}
        assert len(colours) == 1


def test_gradient_canvas_vertical_is_constant_along_a_row():
    grad = Gradient(Color(0, 0, 0), Color(255, 255, 255))
    c = imaging.gradient_canvas(8, 4, grad, horizontal=False)
    for y in range(4):
        colours = {c.buffer[y][x].fg for x in range(8)}
        assert len(colours) == 1


def test_scale_canvas_changes_size():
    src = Canvas(8, 4)
    for y in range(4):
        for x in range(8):
            src.set_pixel(x, y, '#', Color(x * 30, y * 60, 0))
    out = imaging.scale_canvas(src, 16, 8)
    assert out.width == 16
    assert out.height == 8


# --- video synthesis -----------------------------------------------------

def test_make_test_video_shape():
    v = video.make_test_video(w=16, h=8, num_frames=3, fps=5)
    assert isinstance(v, Video)
    assert v.width == 16 and v.height == 8
    assert v.frame_count == 3
    assert v.fps == 5


def test_make_color_bars_shape_and_variety():
    v = video.make_color_bars(w=16, h=8, num_frames=4, fps=5)
    assert v.frame_count == 4
    flat = {c for row in v.frames[0] for c in row if c is not None}
    assert len(flat) > 3, 'colour bars should not be a single colour'


def test_make_spinning_donut_changes_over_time():
    v = video.make_spinning_donut_video(w=24, h=12, num_frames=3, fps=5)
    assert v.frame_count == 3
    first = [list(row) for row in v.frames[0]]
    last = [list(row) for row in v.frames[-1]]
    assert first != last, 'a spinning donut must animate'


def test_video_frames_are_colour_grids():
    """Video stores one colour grid per frame, not a Canvas per frame."""
    v = video.make_test_video(w=8, h=4, num_frames=2)
    assert v.frame_count == 2
    for frame in v.frames:
        assert len(frame) == 4
        for row in frame:
            assert len(row) == 8
            for cell in row:
                assert cell is None or isinstance(cell, Color)


# --- ansi_io -------------------------------------------------------------

def test_export_and_parse_ansi_round_trip():
    c = Canvas(5, 2)
    for y in range(2):
        for x in range(5):
            c.set_pixel(x, y, '@' if x % 2 else '#', Color(10, 200, 30))
    text = ansi_io.export_ansi(c)
    assert '\x1b[' in text
    back = ansi_io.parse_ansi(text)
    assert back.width == 5 and back.height == 2
    assert back.buffer[0][0].char == '#'
    assert back.buffer[0][0].fg == Color(10, 200, 30)


def test_export_plain_text_has_no_escapes():
    c = Canvas(4, 2)
    for y in range(2):
        for x in range(4):
            c.set_pixel(x, y, '=', Color(255, 0, 0))
    text = ansi_io.export_plain_text(c)
    assert '\x1b' not in text
    assert len(text.splitlines()) == 2


def test_save_and_load_ansi_file(tmp_path):
    c = Canvas(6, 3)
    for y in range(3):
        for x in range(6):
            c.set_pixel(x, y, '*', Color(1, 2, 3))
    path = tmp_path / 'out.ans'
    ansi_io.save_ansi_file(str(path), c)
    assert path.exists()
    back = ansi_io.load_ansi_file(str(path))
    assert back is not None
    assert back.width == 6
    assert back.buffer[2][5].char == '*'


def test_load_ansi_file_returns_none_when_absent(tmp_path):
    assert ansi_io.load_ansi_file(str(tmp_path / 'missing.ans')) is None


def test_canvas_to_block_art_packs_two_rows_per_line():
    """Block art uses upper-half blocks, so 4 rows become 2 output lines."""
    c = Canvas(4, 4)
    for y in range(4):
        for x in range(4):
            c.set_pixel(x, y, ' ', fg=Color(y * 40, 0, 0))
    out = ansi_io.canvas_to_block_art(c)
    rows = out.splitlines()
    assert len(rows) == 2, 'each output line covers two canvas rows'
    # Every cell carries its own truecolor SGR, so measure visible width only.
    for row in rows:
        visible = ansi_io.re.sub(r'\033\[[0-9;]*m', '', row)
        assert len(visible) == 4
    assert '\u2580' in out


# --- ffmpeg probing ------------------------------------------------------

@requires_ffprobe
def test_probe_duration_and_fps_and_size(test_video_file):
    assert ffmpeg.probe_duration(test_video_file) > 0
    assert ffmpeg.probe_fps(test_video_file) > 0
    w, h = ffmpeg.probe_size(test_video_file)
    assert (w, h) == (64, 48)


@requires_ffprobe
def test_probe_duration_returns_zero_for_an_unreadable_file(tmp_path):
    """Duration is only used for a progress bar, so failure is not fatal."""
    bogus = tmp_path / 'nope.mp4'
    bogus.write_text('not a video')
    assert ffmpeg.probe_duration(str(bogus)) == 0.0


def test_have_ffmpeg_matches_the_path():
    from shutil import which
    assert ffmpeg.have_ffmpeg() == (which('ffmpeg') is not None)


def test_require_ffmpeg_raises_a_clear_error_when_absent(monkeypatch):
    monkeypatch.setattr(ffmpeg, 'have_ffmpeg', lambda: False)
    with pytest.raises(RuntimeError) as exc:
        ffmpeg.require_ffmpeg()
    message = str(exc.value).lower()
    assert 'ffmpeg' in message
    assert 'install' in message or 'path' in message


# --- FFmpegPipe process handling ----------------------------------------

def test_ffmpeg_pipe_takes_arguments_without_the_binary():
    """The binary is prepended, so callers must not include it themselves.

    Passing a full command ran `ffmpeg ffmpeg -i ...`, which exits 1 having
    written nothing, and the caller saw an empty stream rather than an error.
    """
    from spore_engine.media.ffmpeg import FFmpegPipe
    assert FFmpegPipe(['-i', 'x']).args == ['-i', 'x']
    with pytest.raises(ValueError, match='added automatically'):
        FFmpegPipe(['ffmpeg', '-i', 'x'])


def test_ffmpeg_pipe_surface():
    from spore_engine.media.ffmpeg import FFmpegPipe
    for attr in ('read', 'read_all', 'terminate', '__enter__', '__exit__'):
        assert hasattr(FFmpegPipe, attr), f'FFmpegPipe is missing {attr}'


def test_ffmpeg_pipe_closes_its_process_on_error(tmp_path, monkeypatch):
    """A crash mid-stream must not leave an ffmpeg process running."""
    from spore_engine.media import ffmpeg as ff

    class FakeProc:
        def __init__(self):
            self.stdin = io.BytesIO()
            self.stdout = io.BytesIO()
            self.stderr = io.BytesIO()
            self.returncode = None
            self.terminated = False

        def poll(self):
            return self.returncode

        def wait(self, timeout=None):
            return self.returncode or 0

        def terminate(self):
            self.terminated = True
            self.returncode = -15

        def kill(self):
            self.terminated = True
            self.returncode = -9

    created = []

    def fake_popen(cmd, **kwargs):
        proc = FakeProc()
        created.append(proc)
        return proc

    monkeypatch.setattr(ff.subprocess, 'Popen', fake_popen)
    pipe = ff.FFmpegPipe(['-i', 'x'])
    with pytest.raises(RuntimeError, match='boom'):
        with pipe:
            raise RuntimeError('boom')
    assert created, 'the fake ffmpeg was never started'
    assert created[0].terminated or created[0].returncode is not None, \
        'the ffmpeg child was left running after an exception in the body'


def test_ffmpeg_pipe_detects_a_missing_binary(monkeypatch):
    from spore_engine.media import ffmpeg as ff

    def boom(*a, **k):
        raise FileNotFoundError('ffmpeg')

    monkeypatch.setattr(ff.subprocess, 'Popen', boom)
    pipe = ff.FFmpegPipe(['-i', 'x'])
    from spore_engine.media.ffmpeg import FFmpegUnavailable
    with pytest.raises(FFmpegUnavailable):
        with pipe:
            pass


# --- img3d ---------------------------------------------------------------

def test_heightfield_cube_builds_a_mesh():
    from spore_engine.media.img3d import heightfield_cube
    grid = [[0.0, 0.5, 1.0], [0.2, 0.8, 0.4]]
    colors = [[Color(255, 0, 0)] * 3 for _ in range(2)]
    mesh = heightfield_cube(grid, colors)
    assert mesh.verts
    assert mesh.faces
    assert len(mesh.face_colors) == len(mesh.faces)


def test_image_to_heightfield_from_a_real_image(rgb_image):
    from spore_engine.media.img3d import image_to_heightfield
    mesh = image_to_heightfield(rgb_image, grid_w=8, grid_h=6)
    assert mesh.verts
    assert mesh.faces


def test_make_test_pattern_writes_a_readable_image():
    from spore_engine.media.img3d import make_test_pattern
    path = make_test_pattern()
    try:
        assert os.path.exists(path)
        with Image.open(path) as img:
            assert img.width > 0 and img.height > 0
    finally:
        if os.path.exists(path):
            os.unlink(path)


def test_render_mesh_onscreen_draws_something():
    from spore_engine import HiResCanvas
    from spore_engine.media.img3d import (heightfield_cube,
                                          render_mesh_onscreen)
    grid = [[0.0, 0.6], [0.3, 0.9]]
    colors = [[Color(200, 50, 50)] * 2 for _ in range(2)]
    mesh = heightfield_cube(grid, colors)
    c = Canvas(24, 10)
    hr = HiResCanvas(24, 20)
    render_mesh_onscreen(c, hr, mesh, t=0.5)
    assert any(cell.char != ' ' for row in c.buffer for cell in row)


# --- module-level laziness ----------------------------------------------

def test_media_modules_import_without_pillow():
    """Importing must not need Pillow even though calling it does."""
    script = (
        'import sys\n'
        "sys.modules['PIL'] = None\n"
        f'sys.path.insert(0, {os.path.dirname(os.path.dirname(os.path.abspath(__file__)))!r})\n'
        'import spore_engine.media.glyphart, spore_engine.media.converter\n'
        'import spore_engine.media.img3d, spore_engine.media.video\n'
        'import spore_engine.render3d.raytracer\n'
        'print("IMPORT_OK")\n'
    )
    r = subprocess.run([sys.executable, '-c', script], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert 'IMPORT_OK' in r.stdout


def test_missing_pillow_error_names_the_extra():
    script = (
        'import sys\n'
        "sys.modules['PIL'] = None\n"
        f'sys.path.insert(0, {os.path.dirname(os.path.dirname(os.path.abspath(__file__)))!r})\n'
        'from spore_engine.media.img3d import image_to_heightfield\n'
        'try:\n'
        "    image_to_heightfield('x.png')\n"
        'except RuntimeError as e:\n'
        "    print('ERR', e)\n"
    )
    r = subprocess.run([sys.executable, '-c', script], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert 'ERR' in r.stdout
    assert 'media' in r.stdout
