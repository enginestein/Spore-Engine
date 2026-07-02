import math, random
from spore_engine.fx.screenfx import shake, fade_overlay, flash, color_overlay, scanlines
from spore_engine.core.color import Color, WHITE, RED, BLUE, YELLOW
from spore_engine.anim.anim import Oscillator

SHADE = ' .:-=+*#%@'
_LS = None

def scene_screenfx(c, hr, t, pt, dt):
    global _LS
    if _LS is None:
        _LS = {
            'phase': 0,
            'timer': 0.0,
        }

    c.clear()

    for y in range(c.h):
        for x in range(c.w):
            n = (math.sin(x * 0.05 + t * 0.3) * math.cos(y * 0.04 + t * 0.2)) * 0.5 + 0.5
            hue = (n*0.5 + t*0.02) % 1.0
            c.set_pixel(x, y, '█', Color.from_hsv(hue, 0.5, 0.15 + n*0.2), z=0)

    # Grid pattern
    for y in range(0, c.h, 3):
        for x in range(0, c.w, 4):
            c.set_pixel(x, y, '+', Color(60, 60, 80), z=5)

    # ── 2. APPLY EFFECTS IN CYCLE ────────────────────────────────
    phase = int(t / 3) % 6
    cycle_t = (t % 3) / 3

    if phase == 0:
        # SHAKE
        intensity = 1 + cycle_t * 3
        shake(c, intensity, seed=int(t * 10))
        label = f"Shake {intensity:.1f}px"
        col = YELLOW

    elif phase == 1:
        # FADE TO BLACK AND BACK
        alpha = math.sin(cycle_t * math.pi)
        fade_overlay(c, alpha * 0.7, Color(0, 0, 0))
        label = f"Fade {alpha:.2f}"
        col = Color(200, 180, 180)

    elif phase == 2:
        # FLASH
        alpha = 1 - cycle_t
        flash(c, alpha)
        label = f"Flash {alpha:.2f}"
        col = WHITE

    elif phase == 3:
        # COLOR OVERLAY
        alpha = 0.3 + cycle_t * 0.4
        color_overlay(c, RED, alpha)
        label = f"Red tint {alpha:.2f}"
        col = RED

    elif phase == 4:
        # SCANLINES
        scanlines(c, 0.3 + cycle_t * 0.4)
        label = f"Scanlines"
        col = Color(100, 200, 100)

    else:
        # VIGNETTE
        from spore_engine.fx.screenfx import vignette
        vignette(c)
        label = "Vignette"
        col = Color(180, 180, 220)

    # ── 3. HUD ────────────────────────────────────────────────────
    c.draw_text(2, 0, f"Screen FX — {label}", col, z=100)
    c.draw_text(2, 1, f"Cycle: {['Shake','Black Fade','Flash','Red Tint','Scanlines','Vignette'][phase]}", WHITE, z=100)
    c.draw_text(c.w//2-8, c.h-1, "[cycles every 3s]", Color(80, 80, 80), z=100)

    # Phase indicator dots
    for i in range(6):
        px = c.w - 12 + i * 2
        ch = '●' if i == phase else '○'
        c.set_pixel(px, c.h-1, ch, col if i == phase else Color(40, 40, 40), z=100)
