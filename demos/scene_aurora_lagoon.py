import math
import random

import numpy as np

from spore_engine import (Canvas, Color, Field, Gradient, HiResCanvas, Image,
                          PerlinNoise, clamp, fast_color, monotonic, scene_state)
from spore_engine.fx.imgops import CellCache, StarField

TAU = math.tau

# ---------------------------------------------------------------------------
# Palettes. The aurora ramp follows the real emission lines: N2+ violet along
# the lower fringe, 557.7nm atomic-oxygen green through the body of the
# curtain, thinning yellow-green, then 630nm oxygen red at the crown.
# ---------------------------------------------------------------------------

_SKY = Gradient(
    Color(2, 3, 11),
    Color(4, 6, 21),
    Color(7, 12, 35),
    Color(11, 19, 47),
    Color(19, 32, 58),
)

_AURORA = Gradient(
    Color(134, 116, 255),
    Color(80, 235, 240),
    Color(80, 255, 150),
    Color(140, 250, 120),
    Color(255, 150, 130),
    Color(255, 172, 112),
)

_WATER = Color(5, 14, 25)
_CREST = Color(104, 152, 196)
_MOON = Color(255, 246, 228)
_MOON_PATH = Color(255, 232, 186)
_MIST = Color(120, 178, 202)
_AIRGLOW = Color(34, 104, 102)
_RIM_COOL = Color(88, 178, 162)
_RIM_MOON = Color(178, 206, 230)
_HULL = Color(11, 16, 30)
_GUNWALE = Color(122, 176, 182)
_LANTERN = Color(255, 186, 100)
_MOTES = (Color(255, 202, 124), Color(146, 222, 255))

#: lower edge, span, gain, drift, ray frequency, hue shift, envelope freq/phase
_LAYERS = (
    (0.34, 0.46, 2.30, 0.050, 0.90, 0.00, 0.045, 0.0),
    (0.16, 0.28, 1.35, 0.082, 1.45, -0.11, 0.075, 19.0),
    (0.52, 0.62, 0.85, 0.028, 0.55, 0.07, 0.030, 37.0),
)

#: A low layered shore, not a mountain range, and translucent as well as
#: feathered: at one sub-cell of vertical resolution a tall opaque silhouette
#: resolves into a staircase of blocks, while a thin receding shoreline reads
#: as distance and leaves the frame to the aurora.
#: colour, height fraction, fBm frequency, fBm phase, rim strength, opacity
_RIDGES = (
    (Color(26, 34, 58), 0.070, 0.090, 11.3, 1.00, 0.72),
    (Color(14, 20, 36), 0.028, 0.140, 27.1, 0.70, 0.54),
    (Color(6, 9, 20), 0.012, 0.200, 41.5, 0.00, 0.36),
)

#: The frame's grade. The knee matches the palette's top stop so a deliberately
#: bright sky is left alone; the bloom threshold sits just under the moon so
#: only the moon and the brightest aurora crowns glare.
_KNEE = 172.0
_BLOOM_AT = 205.0
_BLOOM_RADIUS = 3
_BLOOM = 52.0 / 255.0
_VIGNETTE = 0.52


def _rgb(c: Color) -> np.ndarray:
    """A colour as three floats, for the few places that write a row in place."""
    return np.array([c.r, c.g, c.b], dtype=np.float32)


def _fbm(pn, w, freq, drift=0.0, offset=0.0, octaves=3, gain=1.0):
    """A per-column fBm trace as a plain array.

    :meth:`Field.fbm_line` is the shared implementation - the grid kernel is
    JIT-compiled when numba is present, which is a 14x saving on a quarter of
    this frame's budget. This drops the wrapper because every curtain and
    shoreline below is numpy broadcasting, not a field pipeline.
    """
    return Field.fbm_line(pn, w, freq, drift, offset, octaves, gain).a


def _sky_field(w, hz, t, pn, st):
    """Composite the whole sky as linear RGB; return it with the moon."""
    f32 = np.float32
    yy = np.arange(hz, dtype=f32)[:, None]
    xx = np.arange(w, dtype=f32)[None, :]
    hgt = (hz - 1) - yy                                   # height above the horizon

    sky = Image.gradient('y', _SKY, hz, w)

    mr = max(1.2, hz * 0.150)
    mx = w * 0.68 + 1.4 * math.sin(t * 0.043)
    my = hz * 0.40 + 0.9 * math.sin(t * 0.031 + 1.2)

    # -- galactic band ------------------------------------------------------
    band_c = hz * 0.30 + hz * 0.22 * np.sin(xx * 0.05 + 1.1)
    band = np.exp(-(((yy - band_c) / (hz * 0.11)) ** 2))
    grain = 0.5 + 0.5 * np.sin(xx * 2.4 + 1.7 * np.sin(xx * 0.9)) * np.sin(
        yy * 3.2 + xx * 0.5 + 2.0)
    sky = sky.add(band * grain * 15.0, gain=(0.55, 0.62, 1.0))

    # -- stars --------------------------------------------------------------
    stars = st.get('stars', None,
                   lambda: StarField(300, 0x5EED, warm=0.12, twinkle=1.5))
    sky = stars.draw(sky, t, gain=130.0, threshold=0.42)

    # -- aurora curtains ----------------------------------------------------
    phase = _fbm(pn, w, 0.11, 0.0, 40.0, 2, 5.0)
    for base_f, span_f, gain, speed, freq, hue_ofs, env_f, env_o in _LAYERS:
        jag = _fbm(pn, w, 0.019, t * speed, env_o, 3) - 0.5
        base = hz * (base_f + 0.15 * jag)
        # a contrasty per-column envelope is what turns a wash into curtains
        env = np.clip(_fbm(pn, w, env_f, t * 0.025, env_o + 5.0, 3, 1.35), 0, 1.35) ** 1.70
        p = (hgt - base[None, :]) / max(2.0, hz * span_f)
        pc = np.clip(p, 0.0, 1.0)
        win = np.clip(p / 0.12, 0.0, 1.0) * np.clip((1.0 - p) / 0.15, 0.0, 1.0)
        prof = (1.0 - pc) ** 1.7
        fringe = 0.60 * np.exp(-(((hgt - base[None, :]) / 2.4) ** 2))
        stri = (0.5 + 0.5 * np.sin(xx * freq + phase[None, :] + t * 0.45 + pc * 3.0)) ** 2.0
        stri = 0.20 + 0.80 * stri
        stri *= 0.60 + 0.40 * np.sin(phase[None, :] * 1.7 + pc * 6.5 - t * 0.28)
        # a second harmonic groups the rays irregularly instead of leaving one
        # evenly spaced comb
        stri *= 0.52 + 0.48 * (0.5 + 0.5 * np.sin(
            xx * freq * 2.7 + phase[None, :] * 3.1 + t * 0.31 + pc * 1.7))
        # the ramp is sampled per pixel by curtain height, then scaled by the
        # curtain's own intensity - so one pass through the palette replaces
        # the old baked LUT and its index arithmetic
        curtain = Field((prof + fringe) * win * gain * stri * env)
        sky = sky.add(Field(pc + hue_ofs).palette(_AURORA).scaled(curtain))

    # -- moon, limb-darkened, with a two-lobe corona -----------------------
    d = np.hypot(xx - mx, yy - my)
    limb = 1.0 - 0.24 * np.clip(d / mr, 0, 1) ** 3
    disc = np.clip((mr - d) / 1.8, 0, 1) * limb
    halo = 0.30 * np.exp(-d / (mr * 2.2)) + 0.085 * np.exp(-d / (mr * 6.5))
    sky = sky.add(disc + halo, gain=_MOON)

    # -- airglow pooling along the horizon ---------------------------------
    sky = sky.add(np.exp(-(((yy - (hz - 1) + hz * 0.13) / (hz * 0.13)) ** 2)) * 0.24,
                  gain=_AIRGLOW)

    # -- ridge silhouettes, far to near -------------------------------------
    # The rim on each crest is driven by the aurora luminance immediately
    # above it, so the edge glows exactly where a curtain passes behind the
    # ridge and stays dark where the sky is empty.
    luma = sky.luma().a
    xidx = np.arange(w, dtype=np.int32)
    for col, hf, freq, off, rim_gain, opacity in _RIDGES:
        # two octaves: a broad range plus fine crests. A single low-frequency
        # trace is nearly flat across a terminal and reads as one black bar.
        swell = _fbm(pn, w, freq, t * 0.06, off, 4, 1.0)
        crest = _fbm(pn, w, freq * 3.7, t * 0.09, off + 13.0, 2, 1.0)
        relief = np.clip(swell * 1.30 + crest * 0.38 - 0.30, 0.0, 1.45)
        top = hz - 1.0 - hz * hf * relief
        tint = np.clip(1.0 - (hz - 1.0 - top[None, :]) / (hz * 0.22), 0, 1)
        # Feather the crest over ~2.5 sub-cells. A hard one-cell staircase is
        # what makes a low-res silhouette read as pixel-art blocks.
        soft = np.clip((yy - top[None, :]) / 2.4 + 0.5, 0, 1)
        lit = soft * opacity * (0.88 + 0.12 * tint)
        sky = sky.absorb(col, lit)
        if rim_gain <= 0.0:
            continue
        behind = luma[np.clip(top, 0, hz - 1).astype(np.int32), xidx]
        rmoon = np.exp(-(((xx - mx) / (w * 0.34 + 1.0)) ** 2))
        peak = 0.45 + 0.55 * np.clip(
            _fbm(pn, w, freq * 2.4, t * 0.09, off + 60.0, 2, 1.0), 0, 1)[None, :]
        rimw = np.clip((behind[None, :] - 34.0) / 130.0, 0, 1)
        rimw = rimw * (0.30 + 0.70 * rmoon) * peak * rim_gain
        # rimw is already a single row, so indexing it again with [None] would
        # make this mask three-dimensional - which the old per-channel
        # assignment only survived because numpy squeezed the stray axis away
        rim = (soft > 0.02) & (yy < top[None, :] + 1.2) & (rimw > 0.05)
        # purely additive: blending toward a colour darkened the sky to a black
        # block wherever the rim weight was small
        lit_rim = np.where(rim, rimw, 0.0)
        sky = sky.add(lit_rim * 0.85, gain=_RIM_COOL)
        sky = sky.add(lit_rim * 0.45 * rmoon, gain=_RIM_MOON)

    # -- ground mist drifting across the far shore -------------------------
    mfog = np.clip(_fbm(pn, w, 0.035, t * 0.09, 61.0, 3, 1.0), 0, 1) ** 1.4
    wob = 0.55 + 0.45 * np.sin(xx * 0.11 + t * 0.5 + yy * 0.35)
    band = np.clip(1.0 - hgt / max(1.0, hz * 0.15), 0, 1) ** 1.5
    sky = sky.add(band * mfog[None, :] * wob * 0.55, gain=_MIST)

    return sky, (mx, my, mr)


def _water_field(w, hz, max_d, sky, moon, t, pn, st):
    """Mirror the sky about the horizon and turn it into water."""
    f32 = np.float32
    mx, my, mr = moon
    d = np.arange(1, max_d + 1, dtype=f32)[:, None]
    xx = np.arange(w, dtype=f32)[None, :]
    dn = d / max_d

    ph1 = xx * 0.33 + d * 0.29 + t * 1.85
    wave = (1.05 * np.sin(ph1)
            + 0.58 * np.sin(xx * 0.112 - d * 0.10 + t * 1.03)
            + 0.33 * np.sin(xx * 0.71 + d * 0.55 - t * 2.55)
            + 0.19 * np.sin(xx * 1.31 + d * 0.97 + t * 3.65))
    amp = 0.22 + 0.78 * dn
    src = hz - (d * 0.78 + 0.011 * d * d) + wave * amp
    syi = np.clip(src, 0, hz - 1).astype(np.int32)
    # the mirror: water row d samples sky row syi[d]. This is a per-*row*
    # gather, the transpose of Image.sample_rows, so it stays an index.
    body = Image(sky.a[syi, np.arange(w, dtype=np.int32)[None, :]])

    body = body.absorb(_WATER, 0.48 * (0.22 + 0.72 * dn))

    # Only the very top of the dominant wave lights a crest; thresholding the
    # raw sum saturated most of the surface and turned the lake into a bar code.
    crest = np.clip((np.sin(ph1) * amp - 0.72) / 0.28, 0, 1) ** 1.3
    body = body.add(crest * (0.22 - 0.12 * dn), gain=_CREST)

    # the moon lays a glitter path that widens as it comes toward the viewer
    d0 = my * 0.78 + 0.011 * my * my
    along = np.exp(-(((d - d0) / (max_d * 0.30 + 1.0)) ** 2))
    across = np.exp(-(((xx - mx) / (mr * 0.9 + d * 0.50)) ** 2))
    spk = (0.5 + 0.5 * np.sin(xx * 1.9 + d * 1.25
                              + 2.4 * np.sin(d * 0.35 - t * 0.9) - t * 3.3)) ** 5
    mod = 0.45 + 0.55 * (0.5 + 0.5 * np.sin(d * 0.8 + xx * 0.06 + t * 1.1))
    body = body.add(along * across * spk * mod * 1.5, gain=_MOON_PATH)

    mfog = np.clip(_fbm(pn, w, 0.035, t * 0.09, 61.0, 3, 1.0), 0, 1) ** 1.4
    body = body.add(np.clip(1.0 - d / 4.5, 0, 1) ** 1.4 * mfog[None, :] * 0.45,
                    gain=_MIST)

    _moored_boat(body, w, hz, max_d, t)
    return body


def _moored_boat(body, w, hz, max_d, t):
    """A small moored boat, lantern lit, trailing a broken reflection.

    Writes straight into ``body``'s buffer rather than returning a new image:
    it is a few dozen slice assignments, and a copy of a full water buffer per
    frame would cost more than the boat is worth.

    Deliberately horizontal, and only one of them: a narrow vertical silhouette
    is a dark smudge at sub-cell resolution, and two hulls read as clutter
    rather than depth. The lantern is the only warm light in a cold frame, so it
    carries the focal point and its streak anchors the composition.
    """
    f32 = np.float32
    a = body.a
    rows = a.shape[0]
    xf = np.arange(w, dtype=f32)
    hull_v = _rgb(_HULL)
    gunw_v = _rgb(_GUNWALE)
    flame_v = _rgb(_LANTERN)

    persp = 0.70
    u = 0.32 + 0.010 * math.sin(t * 0.05)
    by = int(2.0 + persp * (max_d - 6.0))
    if not 0.08 <= u < 0.92 or by >= rows - 3 or by < 5:
        return
    cx = int(u * (w - 1))
    bw = 2.4 + persp * 3.4
    rock = 0.35 * math.sin(t * 0.5)

    # A three-row trapezoid alone reads as a bar; the mast is what makes the
    # silhouette resolve as a boat.
    for k in range(3):
        row = by - k
        hw = bw * (0.50 + 0.34 * k)
        a0 = max(0, int(cx - hw + rock * k))
        a1 = min(w, int(cx + hw + rock * k) + 1)
        if a0 >= a1:
            continue
        a[row, a0:a1] = hull_v * (0.85 + 0.25 * k)
        if k == 2:                                       # gunwale catches light
            g0, g1 = a0 + 1, a1 - 1
            if g0 < g1:
                a[row, g0:g1] = gunw_v * 0.72

    for k in (1, 2):
        row = by - 2 - k
        if 0 <= row < rows:
            a[row, cx] = hull_v * (1.0 + 0.2 * k)

    ly = by - 5
    a[ly, cx] = flame_v
    a[ly, max(0, cx - 1):cx + 2] += flame_v * 0.42
    a[ly, max(0, cx - 2):cx + 3] += flame_v * 0.15
    if ly - 1 >= 0:
        a[ly - 1, cx] = flame_v * 0.45
    for gy in range(1, 4):                               # warm pool on the water
        gyy = by - gy
        if 0 <= gyy < rows:
            g0, g1 = max(0, cx - gy - 1), min(w, cx + gy + 2)
            if g0 < g1:
                a[gyy, g0:g1] += flame_v * (0.20 / (gy + 1))

    length = int(6.0 + persp * 14.0)
    for dy in range(1, length + 1):
        y = by + dy
        if y >= rows:
            break
        fade = 1.0 - dy / (length + 1.0)
        wob = math.sin(dy * 0.8 + t * 1.9) * (0.6 + 1.3 * dy / (length + 1.0))
        amt = fade * fade * (0.22 + 0.78 * (0.5 + 0.5 * np.sin(
            xf * 1.6 + dy * 2.3 - t * 2.7)))
        ox = int(wob + (0.5 if wob >= 0 else -0.5))
        half = max(1, int(bw * (0.5 + 0.5 * dy / length)))
        s0, s1 = max(0, cx - half + ox), min(w, cx + half + ox + 1)
        if s0 < s1:
            a[y, s0:s1] += flame_v * (amt[s0:s1] * 0.75)[..., None]


def _add_light(hr, x, y, r, g, b, z):
    """Additively brighten one sub-cell, creating it if it is still empty."""
    if x < 0 or x >= hr.w or y < 0 or y >= hr.h:
        return
    cell = hr.buffer[y][x]
    cur = cell.fg
    cr, cg, cb = (0, 0, 0) if cur is None else (cur.r, cur.g, cur.b)
    cell.char = ' '
    # a full frame allocates one Color per sub-cell and the validating
    # constructor costs about a microsecond each, which is the largest single
    # line item here; the caller clips with numpy first
    cell.fg = fast_color(min(255, max(0, int(cr + r))),
                         min(255, max(0, int(cg + g))),
                         min(255, max(0, int(cb + b))))
    cell.bg = None
    cell.z = z


def _motes(hr, w, hz, t, st):
    """Drifting lights over the lagoon, each with a wobbling reflection."""
    now = monotonic()
    last = st.get('mote_clock')
    st.mote_clock = now
    fps = st.get('fps')
    if last is not None and 0.0 < now - last < 0.5:
        inst = 1.0 / (now - last)
        st.fps = inst if fps is None else fps * 0.88 + inst * 0.12

    def build():
        rnd = random.Random(0xF1A3)
        return [(rnd.random(), rnd.random() ** 1.6, rnd.random() * TAU,
                 rnd.uniform(0.004, 0.015), rnd.random() < 0.34) for _ in range(64)]

    for u, v, ph, spd, warm in st.get('motes', None, build):
        tw = 0.5 + 0.5 * math.sin(t * 1.7 + ph * 3.0)
        if tw < 0.22:
            continue
        col = _MOTES[1 if warm else 0]
        gain = 0.30 + 0.80 * tw
        x = int(((u + t * spd) % 1.0) * (w - 1))
        y = int(hz - 1.0 - (v + 0.020 * math.sin(t * 0.7 + ph)) * (hz - 1))
        if not 0 <= y < hr.h:
            continue
        _add_light(hr, x, y, col.r * gain, col.g * gain, col.b * gain, 40)
        halo = gain * 0.16
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            _add_light(hr, x + dx, y + dy, col.r * halo, col.g * halo, col.b * halo, 40)
        ry = int(hz + (hz - 1.0 - y) * 0.52)
        if 0 <= ry < hr.h:
            rx = x + int(1.2 * math.sin(t * 1.3 + ph * 5.0 + ry * 0.4))
            rg = gain * 0.20
            _add_light(hr, rx, ry, col.r * rg, col.g * rg, col.b * rg, 38)


def _hud(c, t, st):
    """Title, thesis, and a live readout of the incremental renderer."""
    c.draw_text(2, 0, '✦ Aurora Lagoon ✦',
                Color.from_hsv(0.50 + 0.05 * math.sin(t * 0.06), 0.42, 1.0), z=100)
    c.draw_text(2, c.h - 1,
                'fbm aurora | mirror water | lantern-lit boat | per-pixel bloom',
                Color(70, 90, 118), z=100)

    stats = c.render_stats
    if stats is None:
        return
    fps = st.get('fps')
    rate = f'{fps:5.0f} fps' if fps else '  -- fps'
    note = 'full redraw' if stats['full'] else f'{stats["cells"]} cells'
    c.draw_text_at(3, 0, f'{rate} · {note} · {stats["bytes"] / 1024:.1f} KiB/f',
                   Color(70, 92, 124), z=100, anchor='ne')


def scene_aurora_lagoon(c: Canvas, hr: HiResCanvas, t: float, pt, dt: float):
    """Aurora Lagoon - obsidian water mirroring an fBm aurora and a low moon."""
    w, h = hr.w, hr.h
    st = scene_state('aurora_lagoon')
    pn = st.get('noise', None, lambda: PerlinNoise(0xA07A))
    cache = st.get('cache', None, lambda: None)
    if cache is None or not cache.matches(h, w):
        cache = CellCache(h, w)
        st.cache = cache

    hz = clamp(int(h * 0.52), 3, h - 3)
    max_d = h - hz
    if max_d < 2:
        # too short for a horizon and a reflection; a graded sky is all that
        # fits, and it still has to be folded and labelled
        Image.gradient('y', _SKY, h, w).to_cells(hr, 0, cache)
        hr.to_canvas(c)
        _hud(c, t, st)
        return

    sky, moon = _sky_field(w, hz, t, pn, st)
    frame = sky.stacked(_water_field(w, hz, max_d, sky, moon, t, pn, st))
    frame = (frame.tonemapped(_KNEE)
                  .bloomed(_BLOOM_AT, _BLOOM_RADIUS, _BLOOM)
                  .vignetted(_VIGNETTE))
    frame.to_cells(hr, 0, cache)

    _motes(hr, w, hz, t, st)

    hr.to_canvas(c)
    _hud(c, t, st)
