import math, random
from spore_engine import *
from spore_engine.core.color import *


T = None  # transparent

PALETTE = {
    'hair_brown': Color(110, 70, 35),
    'hair_blonde': Color(235, 200, 60),
    'hair_red': Color(200, 65, 40),
    'hair_black': Color(45, 38, 35),
    'hair_darkb': Color(75, 50, 30),
    'skin1': Color(255, 210, 170),
    'skin2': Color(230, 180, 140),
    'skin3': Color(210, 160, 110),
    'skin4': Color(245, 195, 150),
    'shirt_blue': Color(65, 130, 215),
    'shirt_green': Color(55, 185, 85),
    'shirt_cyan': Color(55, 200, 190),
    'dress_red': Color(210, 50, 55),
    'dress_purple': Color(150, 50, 200),
    'dress_pink': Color(235, 120, 160),
    'pants_dark': Color(50, 60, 95),
    'pants_brown': Color(110, 75, 45),
    'pants_grey': Color(90, 90, 100),
    'boots_brown': Color(65, 42, 38),
    'boots_black': Color(30, 30, 32),
    'boots_grey': Color(70, 70, 75),
}

P = PALETTE
C = lambda name: P[name]

def sprite(*frame_rows):
    """Each frame_rows is a list of 7 strings, each string is 5 chars.
       Chars: letters mapping to palette keys, '.' = transparent.
    """
    frames = []
    for rows in frame_rows:
        frame = []
        for row_str in rows:
            frame.append([(C(ch) if ch != '.' else T) for ch in row_str])
        frames.append(frame)
    return frames

# --- Mappings: each char -> palette key ---
# h=hair_brown, H=hair_blonde, r=hair_red, k=hair_black, d=hair_darkb
# s=skin1, S=skin2, t=skin3, u=skin4
# b=shirt_blue, g=shirt_green, c=shirt_cyan
# R=dress_red, P=dress_purple, p=dress_pink
# n=pants_dark, w=pants_brown, y=pants_grey
# B=boots_brown, K=boots_black, G=boots_grey

# Shortcut: build sprites with a char->name mapping per sprite, then resolve
def build(rows, cmap):
    out = []
    for row_str in rows:
        out.append([(P[cmap[ch]] if ch != '.' else T) for ch in row_str])
    return out

H1 = {'h': 'hair_brown', 's': 'skin1', 'b': 'shirt_blue',
      'n': 'pants_dark', 'B': 'boots_brown'}
H2 = {'h': 'hair_brown', 's': 'skin1', 'b': 'shirt_blue',
      'n': 'pants_dark', 'B': 'boots_brown',
      'e': 'shirt_cyan'}
H3 = {'d': 'hair_darkb', 'S': 'skin2', 'g': 'shirt_green',
      'w': 'pants_brown', 'G': 'boots_grey'}
H4 = {'H': 'hair_blonde', 's': 'skin1', 'R': 'dress_red',
      'K': 'boots_black'}
H5 = {'r': 'hair_red', 't': 'skin3', 'P': 'dress_purple',
      'K': 'boots_black'}
H6 = {'k': 'hair_black', 'S': 'skin2', 'p': 'dress_pink',
      'K': 'boots_black'}
H7 = {'k': 'hair_black', 'u': 'skin4', 'c': 'shirt_cyan',
      'y': 'pants_grey', 'K': 'boots_black'}
H8 = {'H': 'hair_blonde', 'S': 'skin2', 'p': 'dress_pink',
      'K': 'boots_black'}

CHAR_TEMPLATES = []

def add(frames, cmap):
    CHAR_TEMPLATES.append([build(fr, cmap) for fr in frames])

# Male Knight: blue shirt, brown hair
add([
    [  # frame 0: left foot forward
        '.hhh.',
        'hsssh',
        'hsssh',
        '.bbb.',
        'bbbbb',
        'bnn..',
        'bBB..',
    ],
    [  # frame 1: right foot forward
        '.hhh.',
        'hsssh',
        'hsssh',
        '.bbb.',
        'bbbbb',
        '..nnb',
        '..BBb',
    ],
], H1)

# Male Ranger: green shirt, dark hair
add([
    [
        '.ddd.',
        'dSSSd',
        'dSSSd',
        '.ggg.',
        'ggggg',
        'gww..',
        'gGG..',
    ],
    [
        '.ddd.',
        'dSSSd',
        'dSSSd',
        '.ggg.',
        'ggggg',
        '..wwg',
        '..GGg',
    ],
], H3)

# Male Urban: cyan accents, white shirt, black hair
add([
    [
        '.kkk.',
        'kuuuk',
        'kuuuk',
        '.ccc.',
        'ccccc',
        'cyy..',
        'cKK..',
    ],
    [
        '.kkk.',
        'kuuuk',
        'kuuuk',
        '.ccc.',
        'ccccc',
        '..yyc',
        '..KKc',
    ],
], H7)

# Female Queen: red dress, blonde hair
add([
    [
        'HHHHH',
        'HsssH',
        'HsssH',
        '.RRR.',
        'RRRRR',
        'RRRR.',
        'RK.K.',
    ],
    [
        'HHHHH',
        'HsssH',
        'HsssH',
        '.RRR.',
        'RRRRR',
        '.RRRR',
        '.K.RK',
    ],
], H4)

# Female Mage: purple dress, red hair
add([
    [
        'rrrrr',
        'rtttr',
        'rtttr',
        '.PPP.',
        'PPPPP',
        'PPPP.',
        'PK.K.',
    ],
    [
        'rrrrr',
        'rtttr',
        'rtttr',
        '.PPP.',
        'PPPPP',
        '.PPPP',
        '.K.PK',
    ],
], H5)

# Female Dancer: pink dress, black hair
add([
    [
        'kkkkk',
        'kSSSk',
        'kSSSk',
        '.ppp.',
        'ppppp',
        'pppp.',
        'pK.K.',
    ],
    [
        'kkkkk',
        'kSSSk',
        'kSSSk',
        '.ppp.',
        'ppppp',
        '.pppp',
        '.K.pK',
    ],
], H6)

# Female Beach: pink dress, blonde hair
add([
    [
        'HHHHH',
        'HSSSH',
        'HSSSH',
        '.ppp.',
        'ppppp',
        'pppp.',
        'pK.K.',
    ],
    [
        'HHHHH',
        'HSSSH',
        'HSSSH',
        '.ppp.',
        'ppppp',
        '.pppp',
        '.K.pK',
    ],
], H8)


SPRITE_W = 5
SPRITE_H = 7


class Walker:
    def __init__(self, frames, gender, x, y, speed):
        self.frames = frames
        self.nframes = len(frames)
        self.gender = gender
        self.x = x
        self.y = y
        self.speed = speed
        self.anim_t = random.random() * 10
        self.anim_speed = 5 + random.random() * 3

    def update(self, dt):
        self.x += self.speed * dt
        self.anim_t += dt * self.anim_speed
        if self.x > 80 + 2:
            self.x = -SPRITE_W - 2
            self.y = 28 + random.random() * 6
            self.speed = 8 + random.random() * 12
            if random.random() < 0.5:
                self.speed = -self.speed

    def draw(self, c):
        fi = int(self.anim_t) % self.nframes
        frame = self.frames[fi]
        ox = round(self.x)
        oy = round(self.y)
        for j in range(SPRITE_H):
            row = frame[j]
            for i in range(SPRITE_W):
                col = row[i]
                if col is None:
                    continue
                c.set_pixel(ox + i, oy + j, ' ', None, col, z=0)


def scene_walkers(c: Canvas, hr: HiResCanvas, t: float, pt, dt: float):
    if not hasattr(scene_walkers, 'walkers'):
        walkers = []
        genders = ['male', 'female']
        for idx, frames in enumerate(CHAR_TEMPLATES):
            gender = 'female' if 'dress' in str(frames) else 'male'
            # rough heuristic: check the colors used
            x = random.uniform(0, 70)
            y = 29 + random.uniform(-2, 3)
            speed = 6 + random.random() * 14
            if random.random() < 0.5:
                speed = -speed
            w = Walker(frames, gender, x, y, speed)
            w.anim_t = random.random() * 10
            walkers.append(w)
        scene_walkers.walkers = walkers

    bg = Gradient(Color(12, 10, 28), Color(30, 18, 50))
    c.gradient_fill(0, 0, c.w, c.h, bg, horizontal=False, z=-100)

    ground = Gradient(Color(50, 60, 35), Color(30, 38, 20))
    c.gradient_fill(0, 30, c.w, c.h, ground, horizontal=False, z=-99)

    stars_phase = t * 0.3
    for i in range(25):
        sx = int((i * 37 + 13) % 80)
        sy = int((i * 53 + 7) % 28)
        bright = 0.3 + 0.7 * (0.5 + 0.5 * math.sin(stars_phase + i * 2.7))
        b = int(80 * bright)
        star_col = Color(b, b, min(255, b + 20))
        c.set_pixel(sx, sy, '.', star_col, z=-50)

    for w in scene_walkers.walkers:
        w.update(dt)
        w.draw(c)

    c.draw_rect(0, 0, c.w, c.h, fg=Color(160, 130, 120), z=50, radius=1)
    c.draw_text(2, 0, 'Pixel Walkers', Color(255, 200, 120), z=51)
    c.draw_text(2, c.h - 1, f'{len(scene_walkers.walkers)} characters', DIM, z=51)
