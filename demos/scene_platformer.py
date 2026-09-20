"""Moon platformer -- the first demo built on easy.App.

Shows the full App pipeline in a real TTY: camera follow, gradient sky,
low-res player + platforms, hires coins, ScreenFX shake/flash, held arrow
keys (raw-mode terminal repeat), and an auto-pilot for the headless runner.

Run standalone:
    python3 -m demos.scene_platformer
"""

import random
from spore_engine import *
from spore_engine.easy.app import App

_APP = None
_AUTOPILOT = False

WORLD_W, WORLD_H = 160, 60
GRAV = 9.8

PLATFORMS = [
    (0, 52, 160, 2),
    (20, 44, 14, 1), (44, 40, 10, 1), (62, 46, 12, 1),
    (84, 38, 12, 1), (106, 42, 10, 1), (128, 36, 8, 1),
    (70, 30, 10, 1), (96, 26, 8, 1), (118, 24, 8, 1),
    (36, 22, 8, 1), (60, 16, 6, 1), (86, 12, 6, 1),
]
COINS = [(24, 40), (48, 36), (66, 42), (90, 34), (112, 38),
         (132, 32), (76, 26), (102, 22), (42, 18)]


class Coin:
    def __init__(self, x, y):
        self.x = float(x)
        self.y = float(y)
        self.tag = 'coin'
        self.z = self._z = 12
        self.hires = True
        self._visible = True
        self._opacity = 1.0
        self._cells = [('●', 0, 0)]
        self._fg = Color.from_hsv(random.random() * 0.12, 0.9, 0.95)
        self._bg = None
        self._scale_x = self._scale_y = 1.0
        self._rotation = 0.0
        self._width = 1
        self._height = 1

    def update(self, dt):
        pass


def _remaining_coins(app):
    return [s for s in app._sprites if getattr(s, 'tag', None) == 'coin']


def _build_app(w, h):
    app = App(width=w, height=h, title="spore | moon platformer", fps=30)
    app.bg_gradient(Color(8, 10, 28), Color(60, 34, 96))
    app.camera = Camera(w, h, x=0, y=0, world_w=WORLD_W, world_h=WORLD_H)
    app.state = {'x': 2.0, 'y': WORLD_H - 9.0, 'vx': 0.0, 'vy': 0.0,
                 'grounded': False, 'score': 0}
    app.ctx = {'was_grounded': False}

    for _ in range(40):
        app.sprite('·', random.randint(0, WORLD_W - 1), random.randint(0, 30),
                   fg=Color.from_hsv(0.6, 0.4, 0.5), z=0)

    for x, y, ww, hh in PLATFORMS:
        app.rect(ww, hh, x=x, y=y, char='#',
                 fg=Color.from_hsv(0.62, 0.4, 0.55),
                 bg=Color.from_hsv(0.62, 0.5, 0.32), z=3)

    player = app.sprite('█', 0, 0, fg=Color(255, 235, 120), z=10)
    player.x = app.state['x']
    player.y = app.state['y']
    app.player = player

    for cx, cy in COINS:
        app.add(Coin(cx, cy))

    app.text('◄ ► move    SPACE jump    Q quit', 2, 1, fg=DIM, z=99)
    app.hud = app.text('score 0', 2, 2, fg=Color(180, 220, 255), z=99)

    def physics(a, dt):
        st = a.state
        if _AUTOPILOT:
            coins = _remaining_coins(a)
            if not coins:
                st['vx'], st['vy'] = -6.0, 0.0
            else:
                tx, ty = coins[0].x, coins[0].y
                dx = tx - st['x']
                if abs(dx) > 0.9:
                    st['vx'] = 7.0 if dx > 0 else -7.0
                else:
                    st['vx'] = 0.0
                    if st['y'] > ty + 0.5 and st['grounded']:
                        st['vy'] = -13.0
        st['vy'] = min(st['vy'] + GRAV * dt, 14)
        st['x'] += st['vx'] * dt
        st['y'] += st['vy'] * dt
        if st['x'] < 0:
            st['x'] = 0
        if st['x'] > WORLD_W - 1:
            st['x'] = WORLD_W - 1
        if st['y'] < 0:
            st['y'], st['vy'] = 0.0, 0.0
        stood = False
        feet = st['y'] + 1.0
        if st['vy'] >= 0:
            for px, py, pw, ph in PLATFORMS:
                if px <= st['x'] <= px + pw - 0.25 and py - 1 <= feet <= py + 0.5:
                    st['y'] = py - 1
                    stood = True
                    break
        was = a.ctx['was_grounded']
        if stood and not was:
            a.add_flash(0.10, 0.15)
        if not stood and was:
            a.add_shake(0.9, 0.25)
        a.ctx['was_grounded'] = stood
        st['grounded'] = stood
        player.x = st['x']
        player.y = st['y']
        a.camera.follow(st['x'], st['y'] - 4, dt=dt)
        a.camera.clamp()
        for s in _remaining_coins(a):
            if abs(s.x - st['x']) < 0.8 and abs(s.y - st['y']) < 0.8:
                a.remove(s)
                st['score'] += 1
                a.add_shake(0.6, 0.2)
                a.add_flash(0.18, 0.14)
        if a.hud._cells or True:
            a.hud.draw_text(0, 0, f"score {st['score']}", Color(180, 220, 255))

    def _jump(a):
        if a.state['grounded']:
            a.state['vy'] = -13.0
            a.state['grounded'] = False
            a.add_shake(0.4, 0.15)

    app.on_key('left', lambda a: a.state.update(vx=-9.0))
    app.on_key('right', lambda a: a.state.update(vx=9.0))
    app.on_key(' ', _jump)
    app.on_key('up', _jump)
    app.on_tick(physics)
    return app


def main():
    global _AUTOPILOT
    _AUTOPILOT = False
    _build_app(100, 30).run()


def scene_platformer(c, hr, t, pt, dt):
    global _APP, _AUTOPILOT
    _AUTOPILOT = True
    if _APP is None:
        _APP = _build_app(c.w, c.h)
    a = _APP
    a._is_tty = False
    a.canvas = c
    a.hr = hr
    a._t += dt
    a._dt = dt
    a.screen_fx.tick(dt)
    a._update(dt)
    a._render_frame()


if __name__ == '__main__':
    main()