import math
import random
from spore_engine import Canvas, HiResCanvas, Color, Gradient, DIM, WHITE
from spore_engine.ui.font import Font


class Menu:
    """TUI title + options screen for the standalone war game."""

    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.font = Font.default_5x7()
        self.items = ['START BATTLE', 'CONTROLS', 'QUIT']
        self.actions = ['start', 'controls', 'quit']
        self.index = 0
        self.screen = 'main'
        self.chosen = None
        self.t = 0.0
        rnd = random.Random(1337)
        self.embers = [(rnd.uniform(0, width), rnd.uniform(0, height),
                        rnd.uniform(6, 14), rnd.uniform(0, 6.28))
                       for _ in range(46)]
        self.skyline = self._make_skyline(rnd)

    def _make_skyline(self, rnd):
        blocks = []
        x = 0
        while x < self.width:
            w = rnd.randint(4, 10)
            h = rnd.randint(4, 12)
            blocks.append((x, w, h))
            x += w + rnd.randint(1, 3)
        return blocks

    def handle_key(self, key):
        if self.screen == 'controls':
            if key in ('enter', 'escape', 'q', 'b'):
                self.screen = 'main'
                return True
            return False
        if key == 'up':
            self.index = (self.index - 1) % len(self.items)
            return True
        if key == 'down':
            self.index = (self.index + 1) % len(self.items)
            return True
        if key == 'enter':
            action = self.actions[self.index]
            if action == 'controls':
                self.screen = 'controls'
            elif action == 'quit':
                self.chosen = 'quit'
            else:
                self.chosen = 'start'
            return True
        if key == 'q' or key == 'escape':
            self.chosen = 'quit'
            return True
        return False

    def selected_action(self):
        return self.chosen

    def pop_action(self):
        action = self.chosen
        self.chosen = None
        return action

    def update(self, dt):
        self.t += dt

    def _draw_background(self, c, t):
        for y in range(self.height):
            p = y / max(1, self.height - 1)
            top = Color(6, 8, 16)
            bot = Color(26, 12, 6)
            bg = top.lerp(bot, p)
            for x in range(self.width):
                c.set_pixel(x, y, ' ', bg=bg, z=1)

        horizon = int(self.height * 0.68)
        for bx, bw, bh in self.skyline:
            sil = Color.from_hsv(0.02, 0.6, 0.10)
            for dx in range(bw):
                for dy in range(bh):
                    c.set_pixel(bx + dx, horizon - dy, ' ', bg=sil, z=2)
            for dx in range(bw):
                flick = math.sin(t * 3 + bx * 1.3 + dx)
                if flick > 0.75 and self.t > 0.5:
                    c.set_pixel(bx + dx, horizon - rnd_dy(self.t, bx, bh),
                                '░', fg=Color(255, 180, 60), z=3)

        for ex, ey, spd, ph in self.embers:
            yy = (ey - (t * spd * 0.15)) % self.height
            a = max(0.0, 1.0 - yy / self.height)
            if a > 0.05:
                c.set_pixel(int(ex) % self.width, int(yy), '·',
                            fg=Color.from_hsv(0.06, 0.9, 0.2 + 0.7 * a), z=4)

    def render(self, c, hr, t):
        c.clear()
        hr.clear()
        self._draw_background(c, t)
        w, h = self.width, self.height

        if self.screen == 'controls':
            self._draw_controls(c, hr, t)
            return

        title = 'WAR BATTLEFIELD'
        tw = len(title) * (self.font.width + 1)
        tx = max(0, (w - tw) // 2)
        ty = 3
        grad = Gradient(Color(120, 16, 4), Color(255, 150, 30),
                        Color(255, 240, 190))
        self._font_title(c, title, tx, ty, grad, z=10)
        for x in range(tw):
            col = grad.at(x / max(1, tw - 1))
            c.set_pixel(tx + x, ty + self.font.height,
                        '─' if x % 3 else '▒', fg=col.mul(0.5), z=10)

        sub = '— GROUND WARFARE —'
        sx = (w - len(sub)) // 2
        self._sine(c, sx, ty + self.font.height + 3, sub, t)

        start_y = ty + self.font.height + 7
        for i, item in enumerate(self.items):
            row = start_y + i * 2
            sel = i == self.index
            if sel:
                label = '  {0}  '.format(item)
                x0 = (w - len(label)) // 2
                for k, ch in enumerate(label):
                    if 0 < k < len(label) - 1:
                        c.set_pixel(x0 + k, row, ch,
                                    fg=Color.from_hsv(0.07, 1.0, 1.0),
                                    bg=Color.from_hsv(0.02, 0.8, 0.22), z=20)
                glow = 0.5 + 0.5 * math.sin(t * 5)
                c.set_pixel(x0, row, '►', fg=Color.from_hsv(0.07, 1, glow), z=20)
                c.set_pixel(x0 + len(label) - 1, row, '◄',
                            fg=Color.from_hsv(0.07, 1, glow), z=20)
            else:
                label = '  {0}  '.format(item)
                x0 = (w - len(label)) // 2
                c.draw_text(x0, row, '  {0}  '.format(item), DIM, z=20)

        hint = '↑/↓ move   Enter select   q quit'
        c.draw_text((w - len(hint)) // 2, h - 1, hint, DIM, z=50)

    def _draw_controls(self, c, hr, t):
        w, h = self.width, self.height
        title = 'CONTROLS'
        self._font_title(c, title, (w - len(title) * 6) // 2, 2,
                         Gradient(Color(60, 90, 160), Color(160, 210, 255)),
                         z=10)
        rows = [
            '↑ / ↓ ............ move selection / scroll',
            'Enter ........... confirm / start battle',
            'q ................ return to menu / quit',
            'Esc ............. back to menu',
        ]
        y = 12
        for line in rows:
            c.draw_text(max(0, (w - len(line)) // 2), y, line,
                        Color(200, 210, 230), z=20)
            y += 2
        c.draw_text(max(0, (w - 40) // 2), h - 2,
                    'In battle: blue (left) vs red (right) soldiers',
                    DIM, z=50)

    def _font_title(self, c, text, x, y, gradient, z):
        fw, fh = self.font.width, self.font.height
        cursor_x = x
        for i, char in enumerate(text):
            if char in self.font.data:
                bitmap = self.font.data[char]
                char_t = i / max(1, len(text) - 1)
                col = gradient.at(char_t)
                for col_i in range(fw):
                    col_data = bitmap[col_i]
                    for row in range(fh):
                        if (col_data >> row) & 1:
                            c.set_pixel(cursor_x + col_i, y + row,
                                        '█', col, None, z)
            cursor_x += fw + 1

    def _sine(self, c, x, y, text, t):
        for i, ch in enumerate(text):
            yy = y + round(math.sin(t * 2 + i * 0.5))
            hue = (i / len(text) + t * 0.08) % 1.0
            c.set_pixel(x + i, yy, ch, Color.from_hsv(hue, 0.6, 0.7), z=15)


def rnd_dy(t, seed, bh):
    return int(abs(math.sin(t * 4 + seed)) * bh)
