import math
from spore_engine import *
from spore_engine.core.color import *
from spore_engine.media.video import make_test_video, make_color_bars, make_spinning_donut_video, FramePlayer, Video, VideoFrame

_VD = None

def _generate_bouncing_ball_video(w, h):
    v = Video(w, h, 20)
    for fi in range(90):
        t = fi / 20
        frame = []
        bx = int(w / 2 + (w / 2 - 3) * math.sin(t * 1.3))
        by = int(h / 2 + (h / 2 - 3) * math.sin(t * 1.8))
        for y in range(h):
            row = []
            for x in range(w):
                d = math.hypot(x - bx, y - by)
                if d < 2:
                    row.append(Color(255, 200, 80))
                elif d < 3:
                    row.append(Color(200, 100, 30))
                else:
                    lum = int(20 + 10 * math.sin(x * 0.3 + y * 0.2 + t))
                    row.append(Color(lum, lum, lum + 10))
            frame.append(row)
        v.frames.append(frame)
    return v

def scene_video_player(c, hr, t, pt, dt):
    global _VD
    w, h = c.w, c.h

    if _VD is None:
        test_vid = make_test_video(w, h, 60, 15)
        bars_vid = make_color_bars(w, h, 30, 10)
        donut_vid = make_spinning_donut_video(w, h, 90, 20)
        bounce_vid = _generate_bouncing_ball_video(w, h)

        test_player = test_vid.to_player(loop=True)
        bars_player = bars_vid.to_player(loop=True)
        donut_player = donut_vid.to_player(loop=True)
        bounce_player = bounce_vid.to_player(loop=True)

        for p in [test_player, bars_player, donut_player, bounce_player]:
            p.play()

        _VD = {
            'players': [test_player, bars_player, donut_player, bounce_player],
            'current': 0,
            'last_switch': 0,
        }

    s = _VD
    vid_idx = int(t / 10) % 4

    if vid_idx != s['current']:
        s['players'][s['current']].stop()
        s['current'] = vid_idx
        s['players'][vid_idx].play()

    player = s['players'][vid_idx]
    player.update(dt)

    for y in range(h):
        for x in range(w):
            c.set_pixel(x, y, ' ', bg=Color(5, 3, 8), z=-100)

    player.render(c, 0, 0, 1.0, 5)

    names = ['Plasma Wave', 'Color Bars', 'Spinning Donut', 'Bouncing Ball']
    name = names[vid_idx]
    frame_dur = player.current_frame.duration if player.current_frame else 0
    info = f"Frame {min(player._idx + 1, player.frame_count)}/{player.frame_count} | {1.0/frame_dur:.0f}fps" if frame_dur else f"Frame {player._idx + 1}/{player.frame_count}"
    c.draw_text(2, 0, f"Video: {name}", WHITE, z=100)
    c.draw_text(2, h - 1, info, DIM, z=100)
