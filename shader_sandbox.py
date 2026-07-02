#!/usr/bin/env python3
"""
Shader Sandbox — Interactive ASCII Shader Playground
====================================================
A TUI sandbox for the Spore Engine's modular shader pipeline.
Browse source effects, build shader chains, tweak params live.

Controls:
  Tab/Shift+Tab   Cycle sections: Source / Shaders / Params / Legend
  Up/Down         Navigate items within current section
  Left/Right      Adjust slider values / toggle shaders
  Enter/Space     Toggle shader on/off
  + / -           Add / remove shader
  q / Esc         Quit
"""

import sys, os, time, math, random, select, tty, termios
from typing import Optional, Callable

from spore_engine import Canvas, Color, DIM
from spore_engine.core.color import Gradient
from spore_engine.fx.shaders import (
    ShaderPipeline, Shader,
    WaveDistort, SwirlDistort, KuwaharaFilter,
    Posterize, Solarize, CelShade, HeatHaze, Emboss,
    PixelSort, Crystallize, ASCIIRemap, ChannelShift,
    Kaleidoscope, Warp, VHSGlitch, Ripple,
)
from spore_engine.fx.effects import plasma, fire, starfield
from spore_engine.sim.noise import PerlinNoise
from spore_engine.sim.cellular import ReactionDiffusion
from spore_engine.gen.fractals import Mandelbrot, BurningShip
from spore_engine.gen.fractals import NewtonFractal, BarnsleyFern

# ═══════════════════════════════════════════════════════════════════
# SHADER REGISTRY — metadata for auto-generated controls
# ═══════════════════════════════════════════════════════════════════

class ParamDef:
    def __init__(self, name: str, key: str, vmin: float, vmax: float,
                 default: float, step: float = 0.05, integer: bool = False):
        self.name = name
        self.key = key
        self.min = vmin
        self.max = vmax
        self.default = default
        self.step = step
        self.integer = integer

    def to_slider(self, value: float) -> float:
        """Map param value -> slider 0-1."""
        return (value - self.min) / (self.max - self.min)

    def from_slider(self, slider: float) -> float:
        """Map slider 0-1 -> param value."""
        v = self.min + slider * (self.max - self.min)
        if self.integer:
            return int(round(v / self.step)) * self.step
        return round(v / self.step) * self.step


class ShaderDef:
    def __init__(self, name: str, cls: type, params: list[ParamDef]):
        self.name = name
        self.cls = cls
        self.params = params

    def create_instance(self) -> Shader:
        kwargs = {p.key: p.default for p in self.params}
        return self.cls(**kwargs)

    def apply_slider(self, instance: Shader, param_key: str, slider_val: float):
        for p in self.params:
            if p.key == param_key:
                setattr(instance, param_key, p.from_slider(slider_val))
                return


SHADER_REGISTRY: list[ShaderDef] = [
    ShaderDef("Wave Distort", WaveDistort, [
        ParamDef("Amp X", "amp_x", 0, 10, 2.0, 0.1),
        ParamDef("Amp Y", "amp_y", 0, 10, 1.0, 0.1),
        ParamDef("Freq X", "freq_x", 0.01, 0.5, 0.1, 0.01),
        ParamDef("Freq Y", "freq_y", 0.01, 0.5, 0.08, 0.01),
        ParamDef("Speed", "speed", 0, 5, 1.0, 0.1),
    ]),
    ShaderDef("Swirl", SwirlDistort, [
        ParamDef("Strength", "strength", 0, 0.1, 0.02, 0.002),
    ]),
    ShaderDef("Kuwahara", KuwaharaFilter, [
        ParamDef("Radius", "radius", 1, 5, 2, 1, integer=True),
    ]),
    ShaderDef("Posterize", Posterize, [
        ParamDef("Levels", "levels", 2, 16, 4, 1, integer=True),
    ]),
    ShaderDef("Solarize", Solarize, [
        ParamDef("Threshold", "threshold", 0, 1, 0.5, 0.02),
    ]),
    ShaderDef("Cel Shade", CelShade, [
        ParamDef("Levels", "levels", 2, 8, 3, 1, integer=True),
        ParamDef("Edge Thresh", "edge_threshold", 0, 1, 0.2, 0.02),
    ]),
    ShaderDef("Heat Haze", HeatHaze, [
        ParamDef("Amplitude", "amplitude", 0, 5, 2.0, 0.1),
        ParamDef("Frequency", "frequency", 0.01, 0.2, 0.04, 0.005),
        ParamDef("Speed", "speed", 0, 5, 1.5, 0.1),
    ]),
    ShaderDef("Emboss", Emboss, [
        ParamDef("Intensity", "intensity", 0, 3, 1.0, 0.05),
    ]),
    ShaderDef("Pixel Sort", PixelSort, []),  # axis is a choice, not slider
    ShaderDef("Crystallize", Crystallize, [
        ParamDef("Cell Size", "cell_size", 2, 20, 8, 1, integer=True),
        ParamDef("Seed", "seed", 0, 999, 42, 1, integer=True),
    ]),
    ShaderDef("ASCII Remap", ASCIIRemap, []),  # bool params
    ShaderDef("Channel Shift", ChannelShift, [
        ParamDef("R Shift", "r_shift", -5, 5, 0, 1, integer=True),
        ParamDef("G Shift", "g_shift", -5, 5, 0, 1, integer=True),
        ParamDef("B Shift", "b_shift", -5, 5, 0, 1, integer=True),
    ]),
    ShaderDef("Kaleidoscope", Kaleidoscope, [
        ParamDef("Segments", "segments", 2, 24, 8, 1, integer=True),
    ]),
    ShaderDef("Warp", Warp, [
        ParamDef("Time Scale", "time_scale", 0, 3, 0.5, 0.05),
    ]),
    ShaderDef("VHS Glitch", VHSGlitch, [
        ParamDef("Intensity", "intensity", 0, 1, 0.1, 0.01),
    ]),
    ShaderDef("Ripple", Ripple, [
        ParamDef("Amplitude", "amplitude", 0, 5, 1.5, 0.1),
        ParamDef("Frequency", "frequency", 0.1, 2, 0.5, 0.05),
        ParamDef("Speed", "speed", 0, 5, 1.0, 0.1),
    ]),
]

# ═══════════════════════════════════════════════════════════════════
# SOURCE EFFECTS — draw the base content that shaders transform
# ═══════════════════════════════════════════════════════════════════

class SourceState:
    """Per-source persistent state."""
    def __init__(self):
        self.fire_buffer: Optional[list[list[float]]] = None
        self.stars: list[list[float]] = []
        self.noise: Optional[PerlinNoise] = None
        self.rd: Optional[ReactionDiffusion] = None
        self.mandel: Optional[Mandelbrot] = None
        self.burning: Optional[BurningShip] = None
        self.newton: Optional[NewtonFractal] = None
        self.fern: Optional[BarnsleyFern] = None


def src_plasma(c: Canvas, t: float, dt: float, ss: SourceState):
    plasma(c, t, speed=0.8)


def src_fire(c: Canvas, t: float, dt: float, ss: SourceState):
    w, h = c.w, c.h
    if ss.fire_buffer is None or len(ss.fire_buffer) != h or (len(ss.fire_buffer) and len(ss.fire_buffer[0]) != w):
        ss.fire_buffer = [[0.0] * w for _ in range(h)]
    fire(c, t, ss.fire_buffer)


def src_starfield(c: Canvas, t: float, dt: float, ss: SourceState):
    if not ss.stars:
        for _ in range(120):
            ss.stars.append([random.uniform(-30, 30), random.uniform(-15, 15), random.uniform(0.5, 2.0)])
    starfield(c, t, ss.stars)


def src_noise(c: Canvas, t: float, dt: float, ss: SourceState):
    if ss.noise is None:
        ss.noise = PerlinNoise(seed=42)
    w, h = c.w, c.h
    grad = Gradient.from_palette('neon')
    for y in range(h):
        for x in range(w):
            nx = x * 0.04 + t * 0.01
            ny = y * 0.04 + t * 0.008
            v = ss.noise.noise2(nx, ny) * 0.5 + 0.5
            v = max(0, min(1, v))
            ci = int(v * 9)
            c.set_pixel(x, y, ' .:-=+*#%@'[ci], grad.at(v))


def src_rainbow_waves(c: Canvas, t: float, dt: float, ss: SourceState):
    w, h = c.w, c.h
    for y in range(h):
        for x in range(w):
            v = math.sin(x * 0.05 + t * 0.5) * 0.5 + 0.5
            v2 = math.sin(y * 0.05 + t * 0.3) * 0.5 + 0.5
            hue = (v * 0.5 + v2 * 0.3 + t * 0.02) % 1.0
            col = Color.from_hsv(hue, 0.8, 0.7 + 0.3 * math.sin(x * 0.03 + t))
            ci = int((v * 0.5 + v2 * 0.5) * 9)
            c.set_pixel(x, y, ' .:-=+*#%@'[ci], col)


def src_mandelbrot(c: Canvas, t: float, dt: float, ss: SourceState):
    need_init = ss.mandel is None or ss.mandel.w != c.w or ss.mandel.h != c.h
    if need_init:
        ss.mandel = Mandelbrot(c.w, c.h, max_iter=60)
    zoom = 3.0
    ss.mandel.render(c, center=(-0.5 + t * 0.003, 0), zoom=zoom, t=t)


def src_burning_ship(c: Canvas, t: float, dt: float, ss: SourceState):
    need_init = ss.burning is None or ss.burning.w != c.w or ss.burning.h != c.h
    if need_init:
        ss.burning = BurningShip(c.w, c.h, max_iter=60)
    ss.burning.render(c, center=(-0.5 + t * 0.002, 0), zoom=3.0, t=t)


def src_reaction_diffusion(c: Canvas, t: float, dt: float, ss: SourceState):
    need_init = ss.rd is None or ss.rd.w != c.w or ss.rd.h != c.h
    if need_init:
        ss.rd = ReactionDiffusion(c.w, c.h, feed=0.0545, kill=0.062)
    ss.rd.step()
    ss.rd.render(c, t=t)


def src_test_scene(c: Canvas, t: float, dt: float, ss: SourceState):
    w, h = c.w, c.h
    for y in range(h):
        for x in range(w):
            nx, ny = x / w, y / h
            v = (math.sin(nx * 8 + t * 0.3) * math.cos(ny * 6 + t * 0.2)
                 + 0.5 * math.sin((nx + ny) * 5 + t * 0.4))
            v = v * 0.5 + 0.5
            hue = (nx * 0.3 + ny * 0.5 + t * 0.02) % 1.0
            col = Color.from_hsv(hue, 0.7, 0.15 + v * 0.7)
            ch = ' ' if v < 0.2 else ('░' if v < 0.4 else ('▒' if v < 0.6 else ('▓' if v < 0.8 else '█')))
            c.set_pixel(x, y, ch, col, z=5)

    cx, cy = w // 2, h // 2
    for i in range(6):
        a = i / 6 * math.pi * 2 + t * 0.2
        r = 6 + 3 * math.sin(i * 2.5 + t)
        px = int(cx + r * 8 * math.cos(a))
        py = int(cy + r * 3 * math.sin(a))
        for j in range(8):
            a2 = j / 8 * math.pi * 2 - t * 0.3
            r2 = 2 + math.sin(t + j)
            sx = int(px + r2 * 4 * math.cos(a2))
            sy = int(py + r2 * 2 * math.sin(a2))
            if 0 <= sx < w and 0 <= sy < h:
                col = Color.from_hsv(j / 8 + t * 0.01, 0.8, 0.9)
                c.set_pixel(sx, sy, '♦', col, z=10)


def src_newton(c: Canvas, t: float, dt: float, ss: SourceState):
    need_init = ss.newton is None or ss.newton.w != c.w or ss.newton.h != c.h
    if need_init:
        ss.newton = NewtonFractal(c.w, c.h)
    ss.newton.render(c, zoom=3.0, t=t)


def src_fern(c: Canvas, t: float, dt: float, ss: SourceState):
    need_init = ss.fern is None or ss.fern.w != c.w or ss.fern.h != c.h
    if need_init:
        ss.fern = BarnsleyFern(c.w, c.h)
    ss.fern.step(c, n=200)


SOURCES: list[tuple[str, Callable]] = [
    ("Plasma", src_plasma),
    ("Fire", src_fire),
    ("Starfield", src_starfield),
    ("Perlin Noise", src_noise),
    ("Rainbow Waves", src_rainbow_waves),
    ("Mandelbrot", src_mandelbrot),
    ("Burning Ship", src_burning_ship),
    ("Newton Fractal", src_newton),
    ("Barnsley Fern", src_fern),
    ("Reaction-Diff", src_reaction_diffusion),
    ("Test Scene", src_test_scene),
]

# ═══════════════════════════════════════════════════════════════════
# UI CONSTANTS
# ═══════════════════════════════════════════════════════════════════

COL_BG = Color(10, 10, 22)
COL_PANEL_BG = Color(16, 16, 34)
COL_BORDER = Color(60, 60, 100)
COL_ACCENT = Color(100, 200, 255)
COL_ACCENT2 = Color(255, 200, 80)
COL_HEADING = Color(180, 180, 255)
COL_SLIDER_ON = Color(100, 200, 255)
COL_SLIDER_OFF = Color(60, 60, 80)
COL_TOGGLE_ON = Color(80, 200, 80)
COL_TOGGLE_OFF = Color(200, 80, 80)
COL_DIM = DIM
COL_ENABLED = Color(180, 255, 180)
COL_DISABLED = Color(180, 120, 120)
COL_LABEL = Color(200, 200, 220)
COL_VALUE = Color(180, 180, 200)
COL_SEPARATOR = Color(40, 40, 60)
COL_STATUS_BAR = Color(30, 30, 50)

SECTION_NAMES = ["Source", "Shaders", "Params", "Legend"]
MIN_TERM_W = 90
MIN_TERM_H = 24

# ═══════════════════════════════════════════════════════════════════
# UI DRAWING HELPERS
# ═══════════════════════════════════════════════════════════════════

def draw_slider(c: Canvas, x: int, y: int, width: int, value: float,
                label: str = "", focused: bool = False):
    ox = x
    if label:
        c.draw_text(ox, y, label[:8], COL_ACCENT if focused else COL_LABEL)
        ox += min(len(label), 8) + 1

    bw = max(3, width)
    pos = int(value * (bw - 2))
    pos = max(1, min(bw - 2, pos))

    track = []
    for i in range(bw):
        if i == 0:
            track.append('├')
        elif i == bw - 1:
            track.append('┤')
        elif i == pos:
            track.append('●' if focused else '◆')
        else:
            track.append('─')

    fg = COL_SLIDER_ON if focused else COL_SLIDER_OFF
    c.draw_text(ox, y, ''.join(track), fg)

    pct = f"{int(value * 100)}%"
    c.draw_text(ox + bw + 1, y, pct, COL_VALUE)


def draw_section_header(c: Canvas, x: int, y: int, w: int, text: str):
    c.draw_text(x, y, f" ══ {text} ══", COL_HEADING)
    for i in range(x + len(text) + 7, x + w):
        if i < c.w:
            c.set_pixel(i, y, '═', COL_BORDER)


# ═══════════════════════════════════════════════════════════════════
# SANDBOX STATE
# ═══════════════════════════════════════════════════════════════════

class PipelineEntry:
    def __init__(self, def_idx: int, instance: Shader):
        self.def_idx = def_idx
        self.instance = instance
        self.enabled = True


class ShaderSandbox:
    def __init__(self):
        self.source_idx = 0
        self.pipeline: list[PipelineEntry] = []
        self.source_state = SourceState()
        self.t = 0.0

        # Focus state
        self.section = 0  # 0=Source, 1=Shaders, 2=Params, 3=Legend
        self.focus_idx = 0  # index within current section

        # Running
        self.running = True

        # Terminal
        self.term_w, self.term_h = 100, 30
        self.prev_canvas = None

    def preview_rect(self) -> tuple[int, int, int, int]:
        pw = max(20, self.term_w - self.controls_width() - 2)
        return (0, 0, pw, self.term_h - 1)

    def controls_width(self) -> int:
        if self.term_w < MIN_TERM_W:
            return 0
        cw = self.term_w - self.term_w * 3 // 5 - 2
        return max(30, min(45, cw))

    def get_focused_shader(self) -> Optional[PipelineEntry]:
        if self.section == 1 and self.pipeline and 0 <= self.focus_idx < len(self.pipeline):
            return self.pipeline[self.focus_idx]
        return None

    def get_focused_shader_by_section2(self) -> Optional[PipelineEntry]:
        if self.pipeline and 0 <= self.focus_idx < len(self.pipeline):
            return self.pipeline[self.focus_idx]
        return None

    def add_shader(self, def_idx: int):
        if def_idx < 0 or def_idx >= len(SHADER_REGISTRY):
            return
        sdef = SHADER_REGISTRY[def_idx]
        inst = sdef.create_instance()
        self.pipeline.append(PipelineEntry(def_idx, inst))

    def remove_shader(self, idx: int):
        if 0 <= idx < len(self.pipeline):
            self.pipeline.pop(idx)
            if self.focus_idx >= len(self.pipeline):
                self.focus_idx = max(0, len(self.pipeline) - 1)

    def toggle_shader(self, idx: int):
        if 0 <= idx < len(self.pipeline):
            self.pipeline[idx].enabled = not self.pipeline[idx].enabled

    def update_pipeline(self):
        pipe = ShaderPipeline()
        for entry in self.pipeline:
            if entry.enabled:
                pipe.add(entry.instance)
        return pipe

    def render_frame(self, c: Canvas, t: float, dt: float):
        pw, cw = self.preview_rect()[2], self.controls_width()
        has_controls = cw >= 30 and self.term_w >= MIN_TERM_W

        # ── Background ──────────────────────────────────────────
        for y in range(c.h):
            for x in range(c.w):
                c.set_pixel(x, y, ' ', bg=COL_BG)

        # ── Preview ─────────────────────────────────────────────
        pw = min(pw, c.w - (cw + 2 if has_controls else 0))
        ph = c.h - 1

        # Draw source into a temporary sub-canvas for the preview area
        preview = Canvas(pw, ph)
        source_fn = SOURCES[self.source_idx][1]
        source_fn(preview, t, dt, self.source_state)

        # Apply shader pipeline
        pipeline = self.update_pipeline()
        pipeline.apply(preview, t, dt)

        # Blit preview to main canvas
        for y in range(min(ph, c.h - 1)):
            for x in range(min(pw, c.w)):
                cell = preview.buffer[y][x]
                if cell.fg is not None:
                    c.set_pixel(x, y, cell.char, cell.fg, cell.bg, z=1)

        # Preview border
        if has_controls and pw > 0:
            for y in range(ph):
                px = pw
                if y < c.h:
                    c.set_pixel(px, y, '│', COL_BORDER, z=2)

        # ── Controls Panel ───────────────────────────────────────
        if has_controls:
            self._draw_controls(c, pw + 2, 0, cw, t)

        # ── Status Bar ──────────────────────────────────────────
        self._draw_status_bar(c, t, dt)

    def _draw_controls(self, c: Canvas, ox: int, oy: int, cw: int, t: float):
        y = oy + 1
        max_y = c.h - 2

        # ── Title ───────────────────────────────────────────────
        title = " Shader Sandbox "
        for i, ch in enumerate(title):
            px = ox + 2 + i
            if px < c.w:
                c.set_pixel(px, y, ch, COL_ACCENT2)
        y += 2
        if y >= max_y: return

        # ── Source Section ──────────────────────────────────────
        sec_focused = (self.section == 0)
        draw_section_header(c, ox, y, cw, "SOURCE")
        y += 1
        if y >= max_y: return

        src_name = SOURCES[self.source_idx][0]
        marker = '▸' if sec_focused else ' '
        c.draw_text(ox + 3, y, f"{marker} {src_name}", COL_ACCENT if sec_focused else COL_LABEL)
        y += 2
        if y >= max_y: return

        # ── Shaders Section ─────────────────────────────────────
        sec_focused = (self.section == 1)
        draw_section_header(c, ox, y, cw, "SHADERS")
        y += 1
        if y >= max_y: return

        if not self.pipeline:
            c.draw_text(ox + 3, y, "(empty — press + to add)", COL_DIM)
            y += 2
        else:
            for i, entry in enumerate(self.pipeline):
                if y >= max_y: break
                sdef = SHADER_REGISTRY[entry.def_idx]
                is_focused = sec_focused and i == self.focus_idx
                marker = '▸' if is_focused else ' '
                enabled_ch = '✓' if entry.enabled else ' '
                ch_color = COL_TOGGLE_ON if entry.enabled else COL_DISABLED
                name_color = COL_ENABLED if entry.enabled else COL_DISABLED
                c.draw_text(ox + 3, y, f"{marker}[{enabled_ch}] {sdef.name}", name_color)
                if is_focused:
                    c.draw_text(ox + 1, y, "▸", COL_ACCENT)
                    # Focus highlight
                    for fx in range(ox + 1, ox + cw - 1):
                        if fx < c.w and y < c.h:
                            cell = c.buffer[y][fx]
                            if cell.fg is None:
                                c.set_pixel(fx, y, ' ', bg=Color(25, 25, 50))
                y += 1
            y += 1

        if y >= max_y: return

        # ── Params Section ──────────────────────────────────────
        sec_focused = (self.section == 2)
        focused_entry = None
        if self.section == 2 and self.pipeline:
            focused_entry = self.pipeline[self.focus_idx] if self.focus_idx < len(self.pipeline) else None
        elif self.section == 1:
            focused_entry = self.get_focused_shader()

        draw_section_header(c, ox, y, cw, "PARAMS")
        y += 1
        if y >= max_y: return

        if focused_entry:
            sdef = SHADER_REGISTRY[focused_entry.def_idx]
            if sdef.params:
                for pi, pdef in enumerate(sdef.params):
                    if y >= max_y: break
                    curr_val = getattr(focused_entry.instance, pdef.key, pdef.default)
                    slider_val = pdef.to_slider(curr_val)
                    param_focused = sec_focused and pi == self.focus_idx
                    draw_slider(c, ox + 3, y, cw - 12, slider_val,
                                pdef.name[:10], param_focused)
                    y += 1
            else:
                c.draw_text(ox + 3, y, "(no adjustable params)", COL_DIM)
                y += 1
        else:
            c.draw_text(ox + 3, y, "(select a shader above)", COL_DIM)
            y += 1

        y += 1
        if y >= max_y: return

        # ── Legend / Keys ────────────────────────────────────────
        sec_focused = (self.section == 3)
        draw_section_header(c, ox, y, cw, "KEYS")
        y += 1
        if y >= max_y: return

        keys = [
            "Tab     Section cycle",
            "↑ ↓     Navigate items",
            "← →     Adjust / toggle",
            "Enter   Toggle shader",
            "+       Add shader",
            "-       Remove shader",
            "q/Esc   Quit",
        ]
        for line in keys:
            if y >= max_y: break
            c.draw_text(ox + 3, y, line, COL_DIM)
            y += 1

    def _draw_status_bar(self, c: Canvas, t: float, dt: float):
        y = c.h - 1
        fps = int(1.0 / max(dt, 0.001))
        for x in range(c.w):
            c.set_pixel(x, y, ' ', bg=COL_STATUS_BAR)

        src_name = SOURCES[self.source_idx][0]
        n_shaders = len(self.pipeline)
        n_active = sum(1 for e in self.pipeline if e.enabled)
        info = f"  {src_name}  |  Shaders: {n_active}/{n_shaders}  |  FPS: {fps}"
        c.draw_text(2, y, info, COL_VALUE, z=2)

        section_name = SECTION_NAMES[self.section]
        c.draw_text(c.w - len(section_name) - 4, y, f"[{section_name}]", COL_ACCENT, z=2)

    def handle_key(self, key: str):
        # ── Global keys ──────────────────────────────────────────
        if key in ('q', 'escape'):
            self.running = False
            return

        if key == '+' or key == '=':
            self._prompt_add_shader()
            return

        if key == '-' or key == '_':
            if self.section == 1 and self.pipeline:
                self.remove_shader(self.focus_idx)
                self.focus_idx = min(self.focus_idx, max(0, len(self.pipeline) - 1))
            return

        if key == '\t':
            self.section = (self.section + 1) % 4
            self.focus_idx = 0
            return

        if key == 'tab_back':
            self.section = (self.section - 1) % 4
            self.focus_idx = 0
            return

        # ── Section-specific keys ────────────────────────────────
        if self.section == 0:
            self._handle_source_keys(key)
        elif self.section == 1:
            self._handle_shader_keys(key)
        elif self.section == 2:
            self._handle_param_keys(key)
        elif self.section == 3:
            pass  # no interaction in legend

    def _handle_source_keys(self, key: str):
        n = len(SOURCES)
        if key == 'up':
            self.source_idx = (self.source_idx - 1) % n
            self.source_state = SourceState()
        elif key == 'down':
            self.source_idx = (self.source_idx + 1) % n
            self.source_state = SourceState()
        elif key in ('enter', '\r', ' '):
            self.section = 1
            self.focus_idx = 0

    def _handle_shader_keys(self, key: str):
        if not self.pipeline:
            if key in ('up', 'down'):
                pass
            return

        n = len(self.pipeline)
        if key == 'up':
            self.focus_idx = (self.focus_idx - 1) % n
        elif key == 'down':
            self.focus_idx = (self.focus_idx + 1) % n
        elif key in ('enter', '\r', ' '):
            self.toggle_shader(self.focus_idx)
        elif key == 'right':
            self.toggle_shader(self.focus_idx)
        elif key == 'left':
            self.toggle_shader(self.focus_idx)

    def _handle_param_keys(self, key: str):
        entry = self.get_focused_shader_by_section2()
        if not entry:
            if key in ('up', 'down'):
                self.section = 0
                self.focus_idx = 0
            return

        sdef = SHADER_REGISTRY[entry.def_idx]
        if not sdef.params:
            return

        n = len(sdef.params)
        if key == 'up':
            self.focus_idx = (self.focus_idx - 1) % n
        elif key == 'down':
            self.focus_idx = (self.focus_idx + 1) % n
        elif key == 'left':
            pdef = sdef.params[self.focus_idx]
            curr = getattr(entry.instance, pdef.key, pdef.default)
            new_val = max(pdef.min, curr - pdef.step)
            new_val = round(new_val / pdef.step) * pdef.step
            if pdef.integer:
                new_val = int(new_val)
            setattr(entry.instance, pdef.key, new_val)
        elif key == 'right':
            pdef = sdef.params[self.focus_idx]
            curr = getattr(entry.instance, pdef.key, pdef.default)
            new_val = min(pdef.max, curr + pdef.step)
            new_val = round(new_val / pdef.step) * pdef.step
            if pdef.integer:
                new_val = int(new_val)
            setattr(entry.instance, pdef.key, new_val)

    def _prompt_add_shader(self):
        """Cycle through available shaders and add one not already in pipeline."""
        used_indices = {e.def_idx for e in self.pipeline}
        available = [i for i in range(len(SHADER_REGISTRY)) if i not in used_indices]
        if not available:
            # All shaders already in pipeline — just add first one
            available = list(range(len(SHADER_REGISTRY)))
        if available:
            idx = available[0]
            self.add_shader(idx)
            self.section = 1
            self.focus_idx = len(self.pipeline) - 1


# ═══════════════════════════════════════════════════════════════════
# TERMINAL HELPERS
# ═══════════════════════════════════════════════════════════════════

_KEYS = {
    '\x1b[A': 'up', '\x1b[B': 'down', '\x1b[C': 'right', '\x1b[D': 'left',
    '\x1b[Z': 'tab_back',
    '\x7f': 'backspace', '\x1b': 'escape',
    '\t': '\t', '\r': 'enter',
}


def _read_key(timeout: float = 0.01) -> Optional[str]:
    if not select.select([sys.stdin], [], [], timeout)[0]:
        return None
    ch = os.read(sys.stdin.fileno(), 1).decode('utf-8', errors='replace')
    if ch != '\x1b':
        if ch == '\x7f':
            return 'backspace'
        if ch == '\r':
            return 'enter'
        return ch
    seq = ch
    while select.select([sys.stdin], [], [], 0.03)[0]:
        b = os.read(sys.stdin.fileno(), 1).decode('utf-8', errors='replace')
        if not b:
            break
        seq += b
        if b.isalpha() and b not in '0123456789;':
            break
        if b == '~':
            break
    return _KEYS.get(seq, 'escape')


def _get_term_size():
    try:
        import shutil
        return shutil.get_terminal_size((100, 30))
    except Exception:
        return (100, 30)


# ═══════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════

def main():
    # ── Check terminal size ────────────────────────────────────
    tw, th = _get_term_size()
    if tw < MIN_TERM_W or th < MIN_TERM_H:
        print(f"Terminal too small ({tw}x{th}). Need at least {MIN_TERM_W}x{MIN_TERM_H}.")
        print("Resize your terminal and try again.")
        sys.exit(1)

    sandbox = ShaderSandbox()
    sandbox.term_w, sandbox.term_h = tw, th

    # ── Setup raw terminal ──────────────────────────────────────
    if not sys.stdin.isatty():
        print("Need a real terminal. Run this interactively.")
        sys.exit(1)

    fd = sys.stdin.fileno()
    old_term = termios.tcgetattr(fd)
    try:
        new = termios.tcgetattr(fd)
        new[tty.LFLAG] &= ~(termios.ECHO | termios.ICANON | termios.ISIG)
        new[tty.CC][termios.VMIN] = 0
        new[tty.CC][termios.VTIME] = 1
        termios.tcsetattr(fd, termios.TCSADRAIN, new)

        sys.stdout.write('\033[?25l\033[2J')
        sys.stdout.flush()

        # ── Add initial shaders ─────────────────────────────────
        sandbox.add_shader(0)  # Wave Distort

        # ── Main Loop ───────────────────────────────────────────
        last_frame = time.time()
        render_count = 0
        while sandbox.running:
            now = time.time()
            dt = now - last_frame
            last_frame = now
            if dt > 0.1:
                dt = 0.033
            sandbox.t += dt

            # Handle input
            key = _read_key(timeout=0.005)
            if key:
                sandbox.handle_key(key)

            # Check terminal resize
            render_count += 1
            if render_count % 10 == 0:
                new_tw, new_th = _get_term_size()
                if new_tw != sandbox.term_w or new_th != sandbox.term_h:
                    sandbox.term_w, sandbox.term_h = new_tw, new_th

            # Render
            canvas = Canvas(sandbox.term_w, sandbox.term_h)
            sandbox.render_frame(canvas, sandbox.t, dt)
            canvas.render_to(sys.stdout)

    except KeyboardInterrupt:
        pass
    finally:
        termios.tcsetattr(fd, termios.TCSANOW, old_term)
        sys.stdout.write('\033[?25h\033[0m')
        sys.stdout.flush()
        print("\nShader Sandbox closed. Thanks for playing!")


if __name__ == '__main__':
    main()
