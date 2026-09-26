import math, os, glob
from spore_engine import *
from spore_engine.core.color import *
from spore_engine.media.video import FramePlayer
from spore_engine.media.converter import image_to_canvas, video_to_player

_ACS = None


def _find_media():
    media = []
    for ext in ('*.png', '*.jpg', '*.jpeg', '*.gif', '*.mp4', '*.mkv', '*.avi'):
        media.extend(glob.glob(os.path.expanduser('~/Pictures/') + ext))
        media.extend(glob.glob(os.path.expanduser('~/Videos/') + ext))
        media.extend(glob.glob(os.path.expanduser('~/Desktop/') + ext))
        media.extend(glob.glob(os.path.expanduser('~/Downloads/') + ext))
    return media[:5]


def scene_media_player(c: Canvas, hr: HiResCanvas, t: float, pt, dt: float):
    global _ACS
    w, h = c.w, c.h

    if _ACS is None:
        _ACS = {'mode': 'title', 'player': None, 'frames': [],
                'img_canvas': None, 'img_name': '', 'msg': 'Scanning...'}

    s = _ACS
    phase = int(t / 8) % 4

    for y in range(h):
        for x in range(w):
            c.set_pixel(x, y, ' ', bg=Color(5, 3, 8), z=-100)

    if phase == 0:
        files = _find_media()
        if not files:
            c.draw_text(2, 5, 'No media found in ~/Pictures, ~/Videos,', Color(180, 180, 200), z=10)
            c.draw_text(2, 6, '~/Desktop, or ~/Downloads', Color(180, 180, 200), z=10)
            c.draw_text(2, 8, 'Place a PNG/JPG/MP4/MKV file in one', Color(120, 120, 150), z=10)
            c.draw_text(2, 9, 'of those directories and restart.', Color(120, 120, 150), z=10)
        else:
            idx = int(t / 3) % len(files)
            fp = files[idx]
            name = os.path.basename(fp)
            ext = name.lower().rsplit('.', 1)[-1]
            if ext in ('mp4', 'mkv', 'avi', 'gif'):
                if s['player'] is None or s.get('last_file') != fp:
                    s['msg'] = f'Loading {name}...'
                    for y2 in range(h):
                        for x2 in range(w):
                            c.set_pixel(x2, y2, ' ', bg=Color(5, 3, 8), z=0)
                    c.draw_text(2, h // 2, s['msg'], Color(255, 200, 100), z=10)
                    for x2 in range(w):
                        for y2 in range(h):
                            px = c.get_pixel(x2, y2)
                            if px and px.fg:
                                hr.set_pixel(x2 * 2, y2, px.char, px.fg, px.z)
                                hr.set_pixel(x2 * 2 + 1, y2, px.char, px.fg, px.z)
                    try:
                        player = video_to_player(fp, w, h, max_frames=300, color=True)
                        player.play()
                        s['player'] = player
                        s['last_file'] = fp
                        s['img_name'] = name
                    except Exception as e:
                        s['msg'] = f'Error: {e}'
                        s['player'] = None
                if s['player']:
                    s['player'].update(dt * 1.5)
                    s['player'].render(c, 0, 0, 1.0, 5)
                    info = f'{s["img_name"][:20]} | {s["player"]._idx + 1}/{s["player"].frame_count}'
                    c.draw_text(2, h - 1, info, Color(100, 100, 130), z=10)
            else:
                # Rebuild on a resize too: the decoded canvas is sized to the
                # terminal at decode time, so a resize left it the old shape
                # and the blit below ran off the end of it.
                if (s['img_canvas'] is None or s.get('last_file') != fp
                        or s['img_canvas'].w != w or s['img_canvas'].h != h):
                    s['msg'] = f'Loading {name}...'
                    try:
                        s['img_canvas'] = image_to_canvas(fp, w, h, color=True)
                        s['last_file'] = fp
                        s['img_name'] = name
                        s['msg'] = ''
                    except Exception as e:
                        s['msg'] = f'Error: {e}'
                        s['img_canvas'] = None
                if s['img_canvas']:
                    img = s['img_canvas']
                    for y2 in range(min(h, img.h)):
                        for x2 in range(min(w, img.w)):
                            cc = img.buffer[y2][x2]
                            if cc.char != ' ' or cc.fg:
                                c.set_pixel(x2, y2, cc.char, cc.fg, cc.bg, cc.z)
                    c.draw_text(2, h - 1, s['img_name'][:30], Color(100, 100, 130), z=10)
                if s['msg']:
                    c.draw_text(2, h // 2, s['msg'], Color(255, 200, 100), z=10)
    elif phase == 1:
        c.draw_text(w // 2 - 12, h // 2 - 2, ' IMAGE → ASCII ', Color(100, 200, 255), z=10)
        c.draw_text(w // 2 - 14, h // 2, 'Loads PNG/JPG/JPEG', Color(180, 180, 200), z=10)
        c.draw_text(w // 2 - 16, h // 2 + 1, 'Converts to luminance ASCII', Color(180, 180, 200), z=10)
        c.draw_text(w // 2 - 14, h // 2 + 2, 'Preserves truecolor output', Color(180, 180, 200), z=10)
    elif phase == 2:
        c.draw_text(w // 2 - 12, h // 2 - 2, ' VIDEO → ASCII ', Color(255, 200, 100), z=10)
        c.draw_text(w // 2 - 16, h // 2, 'Loads MP4/MKV/AVI/GIF', Color(180, 180, 200), z=10)
        c.draw_text(w // 2 - 18, h // 2 + 1, 'Extracts frames via ffmpeg', Color(180, 180, 200), z=10)
        c.draw_text(w // 2 - 16, h // 2 + 2, 'Plays back as ASCII video', Color(180, 180, 200), z=10)
    else:
        c.draw_text(w // 2 - 12, h // 2 - 2, ' ASCII MEDIA PLAYER ', Color(150, 200, 150), z=10)
        c.draw_text(w // 2 - 18, h // 2, 'Drop images/videos in ~/Pictures', Color(180, 180, 200), z=10)
        c.draw_text(w // 2 - 14, h // 2 + 1, 'to see them here automatically', Color(180, 180, 200), z=10)

    for x in range(w):
        for y in range(h):
            px = c.get_pixel(x, y)
            if px and px.fg:
                hr.set_pixel(x * 2, y, px.char, px.fg, px.z)
                hr.set_pixel(x * 2 + 1, y, px.char, px.fg, px.z)
