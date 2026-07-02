import math, os, time
from spore_engine import *
from spore_engine.core.color import *
from spore_engine.media.glyphart import (
    image_to_glyph_colored, video_to_glyph_colored_frames, is_animated,
    SHADE_DEFAULT, SHADE_REV, SHADE_RICH, SHADE_BLOCK,
)

GLYPH_PATH = os.environ.get('GLYPH_IMG', os.path.expanduser('~/Desktop/ASCII/image.gif'))

_GS = None
_SAVE_PATH = '/tmp/glyph_art.txt'

SHADE_NAMES = {
    SHADE_DEFAULT: 'Standard',
    SHADE_REV: 'Inverted',
    SHADE_RICH: 'Rich',
    SHADE_BLOCK: 'Blocks',
}
SHADES = [SHADE_DEFAULT, SHADE_REV, SHADE_RICH, SHADE_BLOCK]


def _save_plain_text(text: str):
    try:
        with open(_SAVE_PATH, 'w') as f:
            f.write(text)
        return True
    except Exception:
        return False


def scene_glyph_art(c: Canvas, hr: HiResCanvas, t: float, pt, dt: float):
    global _GS
    w, h = c.w, c.h

    if _GS is None or _GS.get('path') != GLYPH_PATH:
        _GS = {
            'path': GLYPH_PATH,
            'name': '',
            'err': '',
            'text': '',
            'colors': [],
            'frames': [],
            'fps': 10,
            'player_idx': 0,
            'last_shade': -1,
            'saved': False,
        }

    s = _GS

    for y in range(h):
        for x in range(w):
            c.set_pixel(x, y, ' ', bg=Color(5, 3, 8), z=-100)

    if not GLYPH_PATH or not os.path.isfile(GLYPH_PATH):
        msg = f'Set GLYPH_IMG env var or edit GLYPH_PATH in demos/scene_glyph_art.py'
        c.draw_text(2, h // 2 - 2, 'No image file found.', Color(255, 200, 100), z=10)
        c.draw_text(2, h // 2, msg[:w-4], Color(180, 180, 200), z=10)
        c.draw_text(2, h // 2 + 1, f'Looked for: {GLYPH_PATH}'[:w-4], Color(120, 120, 150), z=10)
        return

    fp = GLYPH_PATH
    name = os.path.basename(fp)

    shade_idx = int(t / 4) % len(SHADES)
    shade = SHADES[shade_idx]
    shade_name = SHADE_NAMES.get(shade, 'Custom')

    gw = min(w - 4, 120)
    gh = min(h - 4, 60)

    if is_animated(fp) and not fp.lower().endswith('.gif'):
        pass
    else:
        pass

    reload = (s['name'] != name or shade_idx != s.get('last_shade'))
    ext = name.lower().rsplit('.', 1)[-1]
    is_video = ext in ('mp4', 'mkv', 'avi', 'webm') or (ext == 'gif' and is_animated(fp))

    if is_video:
        if reload or not s['frames']:
            try:
                result = video_to_glyph_colored_frames(
                    fp, gw, gh, shade=shade, max_frames=120, fps=10)
                s['frames'] = result
                s['name'] = name
                s['err'] = ''
                s['last_shade'] = shade_idx
            except Exception as e:
                s['err'] = str(e)
                s['frames'] = []

        if s['err']:
            c.draw_text(2, h // 2, f'Error: {s["err"]}', Color(255, 100, 100), z=10)
        elif s['frames']:
            s['player_idx'] = (s['player_idx'] + 1) % len(s['frames'])
            text, colors = s['frames'][s['player_idx']]
            lines = text.split('\n')
            ox = (w - max(len(l) for l in lines)) // 2 if lines else 0
            oy = (h - len(lines)) // 2 - 1
            for li, line in enumerate(lines):
                for ci, ch in enumerate(line):
                    cx, cy = ox + ci, oy + li
                    if 0 <= cx < w and 0 <= cy < h and ch != ' ':
                        r, g, b = colors[li][ci] if li < len(colors) and ci < len(colors[li]) else (180, 180, 200)
                        c.set_pixel(cx, cy, ch, Color(int(r), int(g), int(b)), z=5)

            saved_msg = ''
            if shade_idx != s.get('last_shade_saved'):
                if _save_plain_text(text):
                    saved_msg = f'  [saved to {_SAVE_PATH}]'
                    s['last_shade_saved'] = shade_idx
            info = f'{name[:20]:20s} | {shade_name} | Frame {s["player_idx"] + 1}/{len(s["frames"])}{saved_msg}'
            c.draw_text(2, h - 2, info[:w-4], Color(100, 100, 130), z=10)
            c.draw_text(2, 0, ' GLYPH VIDEO ', Color(200, 180, 100), z=10)
    else:
        if reload or not s['text']:
            try:
                text, colors = image_to_glyph_colored(fp, gw, gh, shade=shade)
                s['text'] = text
                s['colors'] = colors
                s['name'] = name
                s['err'] = ''
                s['last_shade'] = shade_idx
            except Exception as e:
                s['err'] = str(e)

        if s['err']:
            c.draw_text(2, h // 2, f'Error: {s["err"]}', Color(255, 100, 100), z=10)
        else:
            lines = s['text'].split('\n')
            ox = (w - max(len(l) for l in lines)) // 2 if lines else 0
            oy = (h - len(lines)) // 2 - 1
            for li, line in enumerate(lines):
                for ci, ch in enumerate(line):
                    cx, cy = ox + ci, oy + li
                    if 0 <= cx < w and 0 <= cy < h and ch != ' ':
                        r, g, b = s['colors'][li][ci] if li < len(s['colors']) and ci < len(s['colors'][li]) else (180, 180, 200)
                        c.set_pixel(cx, cy, ch, Color(int(r), int(g), int(b)), z=5)

            saved_msg = ''
            if shade_idx != s.get('last_shade_saved'):
                if _save_plain_text(s['text']):
                    saved_msg = f'  [saved to {_SAVE_PATH}]'
                    s['last_shade_saved'] = shade_idx
            info = f'{name[:20]:20s} | {shade_name} | {len(lines)}x{max(len(l) for l in lines) if lines else 0}{saved_msg}'
            c.draw_text(2, h - 2, info[:w-4], Color(100, 100, 130), z=10)
            c.draw_text(2, 0, ' GLYPH ART — colored, copyable! ', Color(150, 200, 150), z=10)

    for x in range(w):
        for y in range(h):
            px = c.get_pixel(x, y)
            if px and px.fg:
                hr.set_pixel(x * 2, y, px.char, px.fg, px.z)
                hr.set_pixel(x * 2 + 1, y, px.char, px.fg, px.z)
