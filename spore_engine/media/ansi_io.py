from __future__ import annotations
import re
from typing import Optional
from ..core.canvas import Canvas
from ..core.color import Color


ANSI_FG_PATTERN = re.compile(r'\033\[(?:0;)?(?:38;5;(\d+)|38;2;(\d+);(\d+);(\d+))m')
ANSI_BG_PATTERN = re.compile(r'\033\[(?:0;)?(?:48;5;(\d+)|48;2;(\d+);(\d+);(\d+))m')
ANSI_RESET = re.compile(r'\033\[0m')
ANSI_CLEAR = re.compile(r'\033\[[0-9;]*[HJK]')
ANSI_SGR = re.compile(r'\033\[[0-9;]*m')


ANSI_256_COLORS: list[Color] = []
for i in range(16):
    ANSI_256_COLORS.append(Color.from_hex(
        ['000000','800000','008000','808000','000080','800080','008080','c0c0c0',
         '808080','ff0000','00ff00','ffff00','0000ff','ff00ff','00ffff','ffffff'][i]))
for r in range(6):
    for g in range(6):
        for b in range(6):
            ANSI_256_COLORS.append(Color(r * 51 or 0, g * 51 or 0, b * 51 or 0))
for i in range(24):
    v = 8 + i * 10
    ANSI_256_COLORS.append(Color(v, v, v))


def _nearest_ansi256(c: Color) -> int:
    best = 0
    best_d = float('inf')
    for i, ac in enumerate(ANSI_256_COLORS):
        d = (c.r - ac.r) ** 2 + (c.g - ac.g) ** 2 + (c.b - ac.b) ** 2
        if d < best_d:
            best_d = d
            best = i
    return best


def parse_ansi(text: str) -> Canvas:
    lines = text.split('\n')
    h = len(lines)
    w = max(len(re.sub(r'\033\[[0-9;]*[mHKJ]', '', l)) for l in lines) if lines else 80
    c = Canvas(max(w, 1), max(h, 1))
    current_fg: Optional[Color] = None
    current_bg: Optional[Color] = None

    for y, line in enumerate(lines):
        x = 0
        i = 0
        while i < len(line):
            if line[i] == '\033':
                m = ANSI_FG_PATTERN.match(line[i:])
                if m:
                    if m.group(1):
                        idx = int(m.group(1))
                        if idx < len(ANSI_256_COLORS):
                            current_fg = ANSI_256_COLORS[idx]
                    else:
                        current_fg = Color(int(m.group(2)), int(m.group(3)), int(m.group(4)))
                    i += m.end()
                    continue
                m = ANSI_BG_PATTERN.match(line[i:])
                if m:
                    if m.group(1):
                        idx = int(m.group(1))
                        if idx < len(ANSI_256_COLORS):
                            current_bg = ANSI_256_COLORS[idx]
                    else:
                        current_bg = Color(int(m.group(2)), int(m.group(3)), int(m.group(4)))
                    i += m.end()
                    continue
                m = ANSI_RESET.match(line[i:])
                if m:
                    current_fg = None
                    current_bg = None
                    i += m.end()
                    continue
                m = ANSI_SGR.match(line[i:])
                if m:
                    i += m.end()
                    continue
                m = ANSI_CLEAR.match(line[i:])
                if m:
                    i += m.end()
                    continue
                i += 1
                continue
            if line[i] != '\r' and x < c.w and y < c.h:
                c.set_pixel(x, y, line[i], current_fg, current_bg)
                x += 1
            i += 1
    return c


def export_ansi(canvas: Canvas) -> str:
    lines = []
    for y in range(canvas.h):
        line = ''
        last_fg: Optional[Color] = None
        last_bg: Optional[Color] = None
        for x in range(canvas.w):
            cell = canvas.buffer[y][x]
            if cell.fg != last_fg or cell.bg != last_bg:
                if not cell.fg and not cell.bg:
                    line += '\033[0m'
                else:
                    parts = ['\033[0;']
                    if cell.fg:
                        idx = _nearest_ansi256(cell.fg)
                        parts.append(f'38;5;{idx}')
                    if cell.bg:
                        idx = _nearest_ansi256(cell.bg)
                        parts.append(f'48;5;{idx}')
                    line += ';'.join(parts) + 'm'
                last_fg = cell.fg
                last_bg = cell.bg
            line += cell.char or ' '
        lines.append(line + '\033[0m')
    return '\n'.join(lines) + '\n'


def load_ansi_file(filepath: str) -> Optional[Canvas]:
    try:
        with open(filepath, 'rb') as f:
            raw = f.read()
        text = raw.decode('utf-8', errors='replace')
        return parse_ansi(text)
    except OSError:
        return None


def save_ansi_file(filepath: str, canvas: Canvas):
    text = export_ansi(canvas)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(text)


def export_plain_text(canvas: Canvas) -> str:
    lines = []
    for y in range(canvas.h):
        line = ''.join(cell.char if cell.char != ' ' else ' ' for cell in canvas.buffer[y])
        lines.append(line.rstrip())
    return '\n'.join(lines)


def canvas_to_block_art(canvas: Canvas, fg_only: bool = False) -> str:
    sb = []
    for y in range(0, canvas.h, 2):
        for x in range(canvas.w):
            t = canvas.get_pixel(x, y)
            b = canvas.get_pixel(x, y + 1) if y + 1 < canvas.h else None
            if t and t.fg and b and b.fg:
                sb.append('\033[0;38;2;{};{};{};48;2;{};{};{}m\u2580'.format(
                    t.fg.r, t.fg.g, t.fg.b, b.fg.r, b.fg.g, b.fg.b))
            elif t and t.fg:
                sb.append('\033[0;38;2;{};{};{}m\u2580'.format(t.fg.r, t.fg.g, t.fg.b))
            elif b and b.fg:
                sb.append('\033[0;38;2;{};{};{}m\u2584'.format(b.fg.r, b.fg.g, b.fg.b))
            else:
                sb.append(' ')
        sb.append('\033[0m\n')
    return ''.join(sb)
