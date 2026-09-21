# Usage Guide

Comprehensive guide to using the Spore Engine.

---

## Installation

Clone the repo.

**Optional dependencies for media features:**
```bash
pip install Pillow              # Better image loading
sudo apt install ffmpeg         # Video conversion (or brew install ffmpeg)
```

---

## Simple API (spore_engine.easy)

A high-level layer for quickly making sprite-based graphics, animations, and simple apps — no manual tween math or boilerplate required.

```python
from spore_engine.easy import App, GameSprite
```

### App

Creates a window, runs the main loop, manages sprites and input.

```python
app = App(width=80, height=24, title="My App")
app.run()                        # Start main loop (q to quit)

# Add sprites
s = app.sprite(""" @ \n/@\\""", x=10, y=5, fg=(255, 200, 100))
coin = app.sprite('●', 40, 10, fg=(255, 220, 80), z=12, hires=True)  # hi-res

# Add one-off text
app.text("Hello!", 2, 1, fg=(255, 255, 255))

# Backgrounds
app.bg(Color(20, 20, 40))                      # Flat
app.bg_gradient(Color(8, 10, 28), Color(60, 34, 96))   # Vertical gradient
app.bg_art(beatle, scroll_x=2.0)               # Tiling ASCII art

# World camera (follows a target, clamps to world bounds)
app.camera = Camera(w, h, x=0, y=0, world_w=160, world_h=60)
app.camera.follow(player_x, player_y, dt=dt)

# Full-screen effects (shake / flash / fade)
app.add_shake(2.0,          duration=0.5)
app.add_flash(0.2,          duration=0.3)
app.add_fade(Color(0,0,0),  duration=1.0)      # wipe to/from black

# Scene transitions (from spore_engine.fx.transitions import Fade, Wipe, ...)
app.transition_to(Fade(), duration=0.5)

# Input — arrow keys are decoded to 'up'/'down'/'left'/'right'.
# Holds are tracked from the terminal's key auto-repeat; a held key that
# the terminal never repeats degrades to a press + synthesized release.
@app.on_key('left')
def go_left(app):
    app.state['vx'] = -9.0

@app.on_key('n')
def on_n(app):
    print('pressed n')

@app.on_any_key
def on_any(app, ch):
    pass                          # Every keypress

@app.on_tick
def tick(app, dt):
    pass                          # Every frame
```

Keys reach handlers as decoded names: `'left'`, `'right'`, `'up'`, `'down'`,
`'space'`, `'enter'`, `'tab'`, `'backspace'`, `'delete'`, `'home'`, `'end'`,
`'pageup'`, `'pagedown'`, `'escape'`, `'shift-tab'`, `'F1'`–`'F12'`,
`'ctrl-c'`/`'ctrl-d'`/`'ctrl-z'`, printable chars, and any UTF-8 glyph.

The full working example lives in `demos/scene_platformer.py` (camera follow,
arrow-key platformer physics, hi-res coins, shake/flash): run it with
```bash
python3 -m demos.scene_platformer        # ◄ ► move, SPACE jump, Q quit
```
It also registers in `demo.py`'s scene list as **"Moon Platformer"**, where its
`scene_platformer(c, hr, t, pt, dt)` wrapper renders the same App pipeline into
the normal scene harness.

### GameSprite

Create from multi-line ASCII art strings.

```python
# From art string
bird = GameSprite("""
  @
  /@\\
/   \\
""", x=20, y=5, fg=(255, 200, 100))

# Programmatic
box = GameSprite("", x=10, y=10)
box.set_pixel(0, 0, '┌')
box.set_pixel(0, 0, '┐')

# Factory methods
GameSprite.rect(10, 5, char='#', fg=(255, 0, 0))     # Rectangle
GameSprite.circle(5, char='*', fg=(0, 255, 0))        # Circle
GameSprite.from_file('art.txt')                        # From file
```

### GameSprite Methods

```python
# Movement
s.move_to(x, y, duration=None, easing=None)     # Move to position
s.move_by(dx, dy, duration=None, easing=None)    # Move by offset

# Opacity
s.fade_to(opacity, duration=None, easing=None)    # Fade to specific value
s.fade_in(duration=1.0)                           # Fade from transparent
s.fade_out(duration=1.0)                          # Fade to transparent

# Scale
s.scale_to(scale, duration=None, easing=None)     # Scale uniformly

# Effects
s.spin(speed=1.0)              # Rotate forever
s.pulse(min=0.8, max=1.2, period=1.0)   # Scale pulse
s.wobble(amount=3, period=2.0)   # Side-to-side

# Flow control
s.wait(seconds)                # Pause in animation chain
s.then(callback)               # Callback when animation ends
s.clear_anims()                # Remove all animations

# Programmatic editing
s.set_pixel(dx, dy, char='#', fg=None, bg=None)  # Set cell
s.draw_text(dx, dy, text, fg=None)                # Draw text on sprite

# Utilities
s.copy() -> GameSprite        # Deep copy
s.contains(px, py) -> bool     # Hit test
```

### Animations

Fluent chaining — no tweens or math required.

```python
s = GameSprite(' @ ', x=0, y=5)

# Move with easing
s.move_to(50, 10).over(2).ease('bounce_out')

# Chained call: move, wait, fade
s.move_to(30, 5).over(1).then(lambda: print('done'))

# Loop forever
s.move_to(30, 18).over(1).ease('bounce_out').loop()

# Built-in effects (return Anim objects for chaining)
s.spin(speed=0.5)                # Rotate forever
s.pulse(min=0.8, max=1.2, period=1.0)   # Scale pulse
s.wobble(amount=3, period=2.0)   # Side-to-side
s.fade_in(2.0)                   # Fade from transparent
s.scale_to(2.0).over(1)          # Scale up
```

### Anim Fluent API

The `Anim` object supports chaining for complex animations:

```python
anim = Anim(sprite)
anim.to(30, 18).over(2).ease('bounce_out').loop().then(callback)
anim.fade(0.5).over(1)
anim.scale(2).over(1.5).ease('elastic_out')
anim.delay(0.5).then(lambda: print('started'))

# Properties
anim.done  # bool — animation finished
```

### Running the demo

```bash
python3 easy_demo.py             # q to quit, n to change spinner
```

---

## Running the Demo

```bash
python3 demo.py                  # All 134 registered scenes (n/p/space/q)
```

### Controls (interactive terminal mode)

| Key | Action |
|-----|--------|
| `n` | Next scene |
| `p` | Previous scene |
| `Space` | Toggle pause |
| `q` | Quit |
| `↑` / `↓` / `←` / `→` | Sent to active scene via `KEY_PRESSED` |
| Any other key | Passed to active scene via `KEY_PRESSED` |

### Non-TTY mode
When stdout is piped or redirected, the demo auto-advances every 5 seconds:
```bash
python3 demo.py | less -R
```

---


## Testing

```bash
python3 -m pytest tests/ -q
```

The `tests/` suite (pytest, no extra deps) covers both surfaces' full
primitive API (including shared `DrawMixin` behavior), z-order and deep-empty
clears, text anchors, `fill_sky`/gradient fills, `to_canvas` preserve/blank
semantics, `SceneState`, `Camera` viewport math, `Input` escape decoding plus
the pull-based event model (synthesized releases, repeat grace, resize events,
SGR/X10 mouse and wheel), `KeyState` edges, `ScreenFX` timing,
`Scene`/`Layer` compositing, the package-wide "one namespace, one true
version" invariant (`test_api.py`), and a headless run of the `easy.App` Moon
Platformer demo. Run it before and after touching the engine.

---

### Programmatic usage

```python
from spore_engine.media.converter import image_to_canvas
from spore_engine import Canvas, Color

# Basic conversion
canvas = image_to_canvas('photo.jpg', width=80, color=True)
canvas.render_to(print)  # or sys.stdout

# With custom height
canvas = image_to_canvas('photo.jpg', width=100, height=40, color=True)

# Grayscale with inverted shade
canvas = image_to_canvas('photo.jpg', width=80, color=False, invert=True)
```

---

## Library API Quick Reference

### Canvas (Framebuffer)

```python
from spore_engine import Canvas, HiResCanvas, Color, Vec2, Mat4

c = Canvas(80, 24)           # Create framebuffer
hr = HiResCanvas(80, 48)     # Double-resolution buffer

# Drawing — Canvas and HiResCanvas share one primitive set (core.DrawMixin)
c.set_pixel(x, y, '@', Color(255, 0, 0))           # Single pixel
c.draw_line(x1, y1, x2, y2, '#', Color(0, 255, 0)) # Line
c.draw_line_thick(0, 0, 40, 20, thickness=3, fg=WHITE)
c.draw_circle(cx, cy, r, '*', Color(0, 0, 255))     # Circle
c.draw_rect(x, y, w, h, '#', Color(255, 255, 0))   # Rectangle
c.draw_triangle(x1, y1, x2, y2, x3, y3, '@', Color(255,0,0), fill=True)
c.draw_ellipse(cx, cy, rx, ry, '#', Color(255,0,0))
c.draw_bezier([(0,0), (40,20), (80,0)], 30, '@', Color(255,128,0))
c.draw_arc(cx, cy, r, start_angle=0, end_angle=1.5, char='.', fg=WHITE)
c.draw_polygon([(0,0),(10,2),(8,8),(2,6)], '#', Color(255,255,0), fill=True)
c.draw_ray(x1, y1, x2, y2, '#', Color(255,128,0))  # Fractional segment
c.draw_text(x, y, "Hello!", Color(255, 255, 255))  # Text

# Anchored / centered text (bounds-safe)
c.draw_text_at(2, 1, "topleft", Color(255,255,255), anchor='nw')
c.draw_text_at(0, 0, "right edge", Color(255,255,255), anchor='e')
c.draw_text_centered(12, "Mid Title", Color(255, 255, 255))   # x centered
# anchors: nw n ne | w c e | sw s se

# Fill operations
c.fill_rect(x, y, w, h, '@', Color(255, 0, 0))     # Filled rect
c.gradient_fill(x1, y1, x2, y2, gradient)           # Gradient fill
c.gradient_fill_radial(cx, cy, r, gradient)         # Radial gradient
c.fill(x, y, '#')                                     # Flood fill
c.blit_canvas(src, dx, dy, z=0)                      # Composite another canvas

# Background-only fills (respect z; e.g. use a negative z behind sprites)
grad = Gradient(Color(8, 10, 28), Color(60, 34, 96))
c.fill_gradient_x(x, y, w, h, grad)      # Horizontal bg gradient
c.fill_gradient_y(x, y, w, h, grad)      # Vertical bg gradient
c.fill_sky(grad, horizon=0.5, z=-100)    # Sky: top grad 0→1, bottom held at end

# Output
c.render_to(sys.stdout)  # ANSI truecolor output

# HiResCanvas
hr.set_pixel(x, y, '@', Color(255, 0, 0))           # Same primitives as Canvas
hr.to_canvas(c)            # Flatten (half-blocks ▀▄█). Skips EMPTY cells so a
                           # pre-drawn background survives. blank=True erases.
```

Every draw primitive takes an optional trailing `z=` depth (default `0`).
`Canvas` and `HiResCanvas` cells start at `z = -inf`, so negative-z fills (the
usual way to paint skies/backgrounds under sprites) draw over a cleared canvas
and are in turn covered by `z >= 0` foreground work.

Output is incremental: `render_to()` diffs the buffer against the last frame
it wrote and re-emits only the cells that changed, grouped into runs with one
cursor jump each. `clear()` keeps that diff, so the always-clear loop used by
`App` and the demos only sends the pixels that actually moved — a static
background is written once and then skipped. Need a full rewrite (resize,
garbled terminal)? `render_to(stream, force_full=True)` or `full_redraw()`.
`render_stats` reports how many cells/rows/bytes went out last frame, handy
for checking you are not resending static work.

### Color

```python
from spore_engine import Color, Gradient, PALETTES

# Create colors
red = Color(255, 0, 0)
from_hsv = Color.from_hsv(0.5, 1.0, 1.0)      # Cyan
from_hex = Color.from_hex('#ff8040')           # Orange

# Operations
lighter = red.mul(1.5)                         # Brightness scale
between = red.lerp(Color(0, 0, 255), 0.5)      # Purple blend
fg_code = red.ansi_fg()                        # ANSI foreground escape
bg_code = red.ansi_bg()                        # ANSI background escape

# Gradients
grad = Gradient(*PALETTES['fire'])
color = grad.at(0.5)                           # Sample at midpoint
```

### Scene Composition (Scene / Layer)

```python
from spore_engine import Scene, Layer

s = Scene(80, 24)            # Owns a Canvas + a HiResCanvas (s.hr)
s.fill_sky(Gradient(...), z=-100)          # forwards draw calls to s.canvas

hud = s.layer('hud', z=50)   # Named layered canvas
hud.draw_text(1, 1, 'HP 10', Color(0, 255, 0), z=50)

s.compose()                  # Stack hr over canvas (half-blocks)
s.present(sys.stdout)        # render_to
```

`Scene.__getattr__` forwards any unknown attribute to `s.canvas`, so a Scene
drops in anywhere a Canvas was expected. `s.layer('name', z=...)` returns the
same `Layer` on repeated calls.

### Scene State (persistent memory between frames / restarts)

```python
from spore_engine import scene_state, clear_scene_states

st = scene_state('gravity')      # Same object every frame & scene reload
st.tick(dt)                      # st.t += dt
if 'bodies' not in st:           # first run
    st.bodies = build_bodies()
st['score'] = st.get('score', 0) + 1
# st.get(key, default, factory=...) — factory builds on first access
clear_scene_states()             # wipe all (e.g. when a scene restarts)
list_scene_states()              # -> ['gravity', ...]
```

### Loading Assets (sprites, palettes, models, text)

```python
from spore_engine import load_sprite, load_palette, load_model, load_text

spr = load_sprite('hero.spr')          # core Sprite
pal = load_palette('ramp.pal')         # list[Color]
mesh = load_model('ship.obj')          # Mesh3D (.obj/.ply), None if missing
text = load_text('level1.txt')
```

Sprite files carry a small header before the art:

```python
# a comment
fg=#ffcc00          # default foreground
bg=#000033          # default background
#@=#ff0000          # per-glyph override: '@' is red everywhere
@@@
@ @
```

The first non-header line starts the art and everything after it is taken
verbatim. Palette files list one colour per line — `#rrggbb`, `rrggbb`,
`r,g,b` or `r g b` — with comments starting `# `.

Loading is memoized: the shared `assets` store returns the same object for
the same file and options, so calling `load_sprite()` every frame is cheap.
Use a private `Assets()` (or `Assets(cache=False)`) when you want isolated or
uncached loading, and `assets.clear()` to drop the whole store.

### Entity-Component System (ECS)

```python
import math
from spore_engine import (World, System, Scene,
                          Transform, SpriteComponent, SpriteRenderSystem,
                          load_sprite)

class Hover(System):
    def __init__(self):
        super().__init__(priority=0)   # lower runs first
        self.t = 0.0
    def update(self, world, dt):
        self.t += dt
        for e in world.query(Transform):
            e.get(Transform).y = int(10 + 6 * math.sin(self.t))

world = World()
hero = world.create()
hero.add(Transform(5, 3, z=5))
hero.add(SpriteComponent(load_sprite('hero.spr')))

scene = Scene(80, 24)
world.add_system(Hover())                    # game logic
world.add_system(SpriteRenderSystem(scene))  # then draw
world.update(0.016)
scene.present(sys.stdout)
```

Entities are `EcsEntity` objects — plain id plus components keyed by their
type — so `world.query(*types)` returns everything carrying every listed
component, in creation order, and systems run in `priority` order each
`world.update(dt)`. `SpriteRenderSystem` is the Scene/Layer tie-in: pass
`layer='hud'` to draw onto an overlay layer instead of the main canvas.
(The class is `EcsEntity`, not `Entity` — the animation package already owns
that name.)

### Keyboard & Input Events (core)

Pull-based terminal input with a real event model — no Enter needed, delivered
as a stream of `KeyEvent` / `MouseEvent` / `ResizeEvent`.

```python
from spore_engine import (Input, KeyState, open_input,
                          KeyEvent, MouseEvent, ResizeEvent, KEY_LEFT)

inp = Input()                        # or open_input(0) — reads stdin
inp.enable_mouse()                   # SGR mouse reports (buttons + wheel)
with inp.raw():                      # tty raw mode (restores on exit)
    ks = KeyState()
    while running:
        events = inp.events(1 / 30)        # one pull per frame: keys + mouse + resize
        ks.update(events)                  # tracks holds & press/release edges
        for ev in events:
            if isinstance(ev, KeyEvent):
                if ev.down and not ev.repeat and ev.key == KEY_LEFT: move_left()
                if not ev.down and ev.key == KEY_SPACE:    jump_on_release()
            elif isinstance(ev, MouseEvent):
                if ev.action == 'press' and ev.button == 0:  click(ev.x, ev.y)
                if ev.action == 'scroll':                    roll(ev.scroll_dx, ev.scroll_dy)
            elif isinstance(ev, ResizeEvent):
                layout(ev.width, ev.height)
        if ks.just_pressed('q'): break
# Non-blocking pattern:
#   for ev in inp.events(0): ...
```

**Key events.** Terminals only report presses (and auto-repeats). The engine
*synthesizes* a `KeyEvent(down=False)` release after `release_delay` of
silence, so:

- a held key that repeats is tracked exactly — it releases only when the
  repeats stop, and **never depends on terminal key repeat**;
- a repeat arriving within `repeat_grace` of a synthesized release continues
  the hold (marked `repeat=True`, never a fresh press);
- hold state is exposed via `KeyState` (`down` / `just_pressed` /
  `just_released`, `update(events)` edge flags).

**Mouse & resize.** `enable_mouse()` decodes SGR reports into `MouseEvent`
(`press` / `release` / `move` / `scroll`, with `x`/`y`, modifiers, and
`scroll_dx`/`scroll_dy` — `+1` scroll down/right). Terminal size changes arrive
as `ResizeEvent` both from the terminal's `CSI 8;…t` report and from periodic
size polling.

**Raw mode** requires `termios` (POSIX). On non-POSIX platforms the module
imports cleanly and `poll()`/`get()` still read already-cooked input.

Low-level helpers remain available: `poll(timeout)` returns the next key
*press* (blocking up to `timeout`, 0 = non-blocking; releases, mouse and
resize are consumed internally), `get()` blocks, `available()` is
non-blocking. Arrows, F-keys, Home/End, PgUp/PgDn, Delete/Insert, Shift-Tab,
and ctrl-c/d/z decode to names.

### Camera (core, world & viewport)

```python
from spore_engine import Camera, Canvas

cam = Camera(view_w, view_h, x=0, y=0, zoom=1.0,
             world_w=160, world_h=60)      # world bounds enable clamping
sx, sy = cam.to_screen(wx, wy)             # world -> screen
wx, wy = cam.to_world(sx, sy)              # screen -> world
cam.follow(px, py)                         # snap
cam.follow(px, py, dt=dt)                  # smoothed (lerp, 8/s)
if cam.in_view(wx, wy): cam.draw(c, wx, wy, '@', fg=WHITE, z=10)
cam.draw_line(c, x1, y1, x2, y2, '.', fg=DIM)     # draws through camera
cam.draw_text(c, wx, wy, "hi", fg=WHITE)
cam.clamp()                                # stays inside world bounds
```

`left`/`right`/`top`/`bottom` expose viewport edges. Works with `easy.App` via
`app.camera = Camera(...)`.

### Math & Ramp Utilities

```python
from spore_engine import clamp, lerp, ir, ramp, phase, wave, osc, bounce
from spore_engine import in_bounds, approach, move_toward, dist
from spore_engine import lerp_color, smoothstep, ramp_color

clamp(v, 0, 1);  lerp(a, b, t);   ir(2.6)      # round to int
ramp(0.3)                                        # 0..1 -> ' '..'@' glyph
phase(t, speed, offset)                          # saw 0..1 repeating
wave(t, speed, offset, lo, hi)                   # smooth sine
osc(t, period, offset, lo, hi)                   # sine by period (s)
bounce(t, period, offset, lo, hi)                # triangle wave
approach(x, target, step);  move_toward(x, t, s) # eased stepping
dist(ax, ay, bx, by);       in_bounds(x, y, w, h)
lerp_color(c1, c2, t);      smoothstep(t)
ramp_color(t, Color(0,0,0), Color(255,0,0), ...)  # multi-stop colour sample
```

### ScreenFX (stateful screen effects for games)

```python
from spore_engine import ScreenFX

fx = ScreenFX()
fx.add_shake(2.0, duration=0.5)    # camera-style shake
fx.add_flash(0.2,  duration=0.3)   # white burst
fx.add_fade(Color(0,0,0), duration=1.0, inverse=False)  # to/from black
# per frame:
fx.tick(dt)                        # advance/count down timers
fx.apply(canvas, seed=int(t*100))  # after the scene renders
fx.active                          # True while any effect is running
```

`easy.App` owns a `ScreenFX` in `app.screen_fx` (`app.fx`) and applies it each
frame; `app.add_shake(...)` / `app.add_flash(...)` / `app.add_fade(...)` are
shortcuts.

### Vectors & Matrices

```python
from spore_engine import Vec2, Vec3, Mat4

v2 = Vec2(3, 4)
length = v2.length()          # 5.0
normalized = v2.norm()        # (0.6, 0.8)
dot = Vec2(1, 0).dot(Vec2(0, 1))  # 0

v3 = Vec3(1, 2, 3)
cross = Vec3(1, 0, 0).cross(Vec3(0, 1, 0))  # (0, 0, 1)

# 4x4 matrices
model = Mat4.translate(0, 0, -5) * Mat4.rotate_y(math.pi / 4)
view = Mat4.look_at(Vec3(0, 2, -5), Vec3(0, 0, 0), Vec3(0, 1, 0))
proj = Mat4.perspective(1.0, 16/9, 0.1, 100)
transformed = (proj * view * model).transform(vertex)
```

### 3D Rendering

```python
from spore_engine import Mesh3D, render_mesh_wireframe, render_mesh_solid

mesh = Mesh3D.cube(2)                                  # Built-in cube
mesh = Mesh3D.sphere(1.5, 16, 16)                      # UV sphere
mesh = Mesh3D.torus(2, 0.5, 32)                        # Torus
mesh = Mesh3D.icosphere(1.5, 2)                        # Geodesic sphere

# Wireframe
render_mesh_wireframe(canvas, mesh, view_mat, proj_mat)

# Solid with lighting
render_mesh_solid(hr_canvas, mesh, view_mat, proj_mat, light_dir=Vec3(0.5, -1, -0.5))
```

### Ray Tracing

```python
from spore_engine import RayScene, Sphere, Plane

scene = RayScene()
scene.add(Sphere(0, 0, 0, 1, Color(255, 0, 0), reflectivity=0.3))
scene.add(Plane(0, 1, 0, -1, Color(128, 128, 255), reflectivity=0.1))
scene.add_light(Vec3(-5, 10, 5), Color(255, 255, 255), power=1.5)

# Render at low resolution for speed
scene.render(canvas, camera_pos, camera_target, fov=1.2)
```

### SDF Ray Marching

Signed Distance Field ray marching for rendering implicit surfaces.

```python
from spore_engine import SDFScene, sd_sphere, sd_box, Vec3, Color

scene = SDFScene()
scene.add(lambda p: sd_sphere(p, Vec3(0, 0, 0), 1.5), Color(255, 100, 100))
scene.add(lambda p: sd_box(p, Vec3(2, 0, 0), Vec3(1, 1, 1)), Color(100, 200, 255))
scene.add_light(Vec3(-5, 10, 5), Color(255, 255, 255))
scene.render(canvas, camera_pos, camera_target)
```

### Physics

```python
from spore_engine import PhysicsWorld, Body, Spring, PolyBody

world = PhysicsWorld(gravity=Vec2(0, 9.8), bounds=(0, 0, 80, 40))

# Circular bodies
ball = Body(x=40, y=10, radius=2, mass=1, color=Color(255, 0, 0))
world.add_body(ball)

# Rectangular bodies
from spore_engine import RectBody
rect = RectBody(x=20, y=5, w=6, h=3, mass=2, color=Color(0, 255, 0))
world.add_body(rect)

# Chain of bodies connected by springs
world.chain(x=20, y=5, links=10)

# Cloth simulation
world.cloth(x=10, y=2, cols=10, rows=10)

# Simulate
for _ in range(substeps):
    world.step(dt, sub_steps=4)
```

### Soft Body Physics

Pressure-based soft body simulation with springs and volume preservation.

```python
from spore_engine import SoftBodyWorld, SoftBody, Color

world = SoftBodyWorld(bounds_x=80, bounds_y=40)
blob = SoftBody.circle(cx=40, cy=5, radius=4, segments=12, stiffness=0.5)
world.add(blob)
world.step(dt)
blob.render(canvas)
```

### Steering Behaviors

Autonomous agent movement with seek, flee, arrive, pursue, wander, and flocking.

```python
from spore_engine import SteerWorld, SteerAgent

world = SteerWorld(width=80, height=40)
agent = SteerAgent(x=40, y=20)
agent.max_speed = 30
world.add_agent(agent)
```

### 3D Physics

Simple 3D rigid body physics with sphere and box colliders, springs, and collision resolution.

```python
from spore_engine import PhysicsWorld3D, Body3D, BoxBody3D, Vec3

world = PhysicsWorld3D(gravity=Vec3(0, -9.8, 0))
ball = Body3D(pos=Vec3(0, 10, 0), radius=1, mass=1)
world.add_body(ball)
for _ in range(substeps):
    world.step(dt, substeps=4)
```

### Noise

```python
from spore_engine import PerlinNoise, ValueNoise, WorleyNoise, OpenSimplexNoise

pn = PerlinNoise(seed=42)
val = pn.noise2(x * 0.1, y * 0.1)        # 2D Perlin
fbm = pn.fbm2(x * 0.02, y * 0.02, 6)     # Fractal Brownian Motion
ridge = pn.ridge(x * 0.05, y * 0.05, 4)   # Ridge noise (mountains)

wn = WorleyNoise(seed=123)
cell_dist = wn.noise2(x * 0.05, y * 0.05)  # Cellular noise

sn = OpenSimplexNoise(seed=456)
simplex = sn.noise2(x * 0.1, y * 0.1)     # OpenSimplex
```

### Procedural Generation

```python
from spore_engine import Terrain, Maze, LSystem, LSYSTEMS
from spore_engine import DungeonGen, WorldGen, ErosionSim

# Terrain
terrain = Terrain(80, 40)
terrain.generate(scale=0.05, octaves=6)
terrain.render_topdown(canvas)            # Top-down view

# Maze
maze = Maze(20, 16)
maze.generate_dfs()                        # Or generate_prim()
maze.solve_bfs(0, 0, 38, 30)              # BFS shortest path
maze.render(canvas, solution=True)

# L-System
l = LSystem(**LSYSTEMS['tree1'])
l.generate(4)                              # 4 iterations
l.draw(canvas, start_x=40, start_y=23, start_angle=-90)

# Dungeon generation
dungeon = DungeonGen(40, 40)
dungeon.generate()
dungeon.render(canvas)

# Hydraulic erosion
erosion = ErosionSim(terrain.heightmap)
erosion.erode(num_drops=100)
```

### WFC (Wave Function Collapse)

Constraint-based procedural generation using tile adjacency rules.

```python
from spore_engine import WFC, WFCTile

wfc = WFC(width=10, height=10)
wfc.simple_platformer_tiles()
wfc.generate(seed=42)
wfc.render(canvas)
```

### A\* Pathfinding

Grid-based A\* pathfinding with walkable cells, obstacles, and optional diagonal movement.

```python
from spore_engine import AStar

astar = AStar(width=20, height=20)
astar.set_obstacle(5, 5)
path = astar.find_path((0, 0), (15, 12))
```

### Delaunay / Voronoi

Delaunay triangulation and Voronoi diagram generation from point sets.

```python
from spore_engine import Delaunay
import random

points = [(random.random()*80, random.random()*40) for _ in range(20)]
d = Delaunay()
for x, y in points:
    d.add_point(x, y)
d.triangulate()
d.render(canvas)
d.render_voronoi(canvas)
```

### Marching Cubes

Extract isosurface triangle meshes from 3D density grids.

```python
from spore_engine import marching_cubes, make_density_grid

grid = make_density_grid(width=10, height=10, depth=10, func=my_sdf)
vertices, triangles = marching_cubes(grid, iso_level=0)
```

### Scenery

Parallax backgrounds, layered scenery, day/night cycle, and sky rendering.

```python
from spore_engine import ParallaxScenery, DayNightCycle, render_sky, Color

render_sky(canvas, sky_color=Color(100, 150, 255), stars=True, moon=True)
cycle = DayNightCycle(cycle_duration=60.0)
cycle.update(dt)
```

### BiomeMap

Multi-biome terrain generation using elevation, moisture, and temperature noise.

```python
from spore_engine import BiomeMap

bm = BiomeMap(width=80, height=40, seed=42)
bm.render(canvas)
```

### Cellular Automata

```python
from spore_engine import GameOfLife, Automata1D, WireWorld, LangtonsAnt, ReactionDiffusion

gol = GameOfLife(80, 40)
gol.place_pattern('glider_gun', x=10, y=10)
gol.step()                                   # Advance one generation
gol.render(canvas)

# Reaction-Diffusion
rd = ReactionDiffusion(80, 40, feed=0.055, kill=0.062)
rd.step()
rd.render(canvas)

# 1D Cellular Automaton (Wolfram Rule 110)
ca = Automata1D(80, rule=110)
ca.step()
ca.render(canvas)
```

### Fluid Simulation

```python
from spore_engine import FluidSim, WaveSim

fluid = FluidSim(80, 40, viscosity=0.0001, diffusion=0.01)
fluid.add_dye(40, 20, 100)
fluid.step()
fluid.render_dye(canvas)                     # Dye visualization
# fluid.render_velocity(canvas)              # Velocity field
# fluid.render_vorticity(canvas)             # Vorticity (curl)

waves = WaveSim(80, 40, damping=0.99)
waves.splash(40, 20, 5, 10)
waves.step()
waves.render(canvas)
```

### Animation

```python
from spore_engine import Tween, Sequence, Timeline, Keyframe, Track, Entity, PathFollower

# Simple tween
tween = Tween(target_obj, 'x', from_v=0, to_v=100, duration=2)
tween.update(0.5)                            # t = 0.5s
print(target_obj.x)                          # 25.0

# Path following
entity = Entity()
follower = PathFollower(entity, [(0,0), (40,20), (80,0)], duration=3)

# Timeline (multi-track)
timeline = Timeline()
timeline.add_track('x', Track([
    Keyframe(0, 0, 'linear'),
    Keyframe(2, 100, 'bounce_out')
]))
timeline.add_track('y', Track([
    Keyframe(0, 0, 'linear'),
    Keyframe(2, 50, 'sine_in_out')
]))
timeline.play(loop=True, yoyo=True)
timeline.update(dt)
```

### Inverse Kinematics

FABRIK and CCD solvers for bone chain manipulation and skeletal animation.

```python
from spore_engine import Skeleton, Bone, create_arm, Vec2

root = Bone(length=3, angle=0, pos=Vec2(40, 12))
arm = create_arm(40, 12, segments=3)
arm.solve_fabrik(target=Vec2(50, 8))
arm.render(canvas)
```

### Text Effects

Text with dynamic visual effects: glitch, typewriter, sine wave, rainbow, bounce, and more.

```python
from spore_engine import glitch_text, typewriter_text, sine_text, rainbow_text, bounce_text

glitch_text(canvas, x=10, y=5, text="GLITCH", t=t)
typewriter_text(canvas, x=10, y=10, text="Hello...", t=t, chars_per_sec=5)
sine_text(canvas, x=10, y=15, text="WAVE", t=t)
rainbow_text(canvas, x=10, y=20, text="RAINBOW", t=t)
bounce_text(canvas, x=10, y=25, text="BOUNCE", t=t)
```

### Powdersand Simulation

```python
from spore_engine import PowderSim, SAND, WATER, STONE, WOOD, FIRE

sim = PowderSim(80, 40)
sim.set_rect(10, 10, 20, 10, SAND)           # Fill area with sand
sim.set_circle(40, 20, 8, WATER)             # Water pool
sim.set_circle(50, 30, 5, LAVA)               # Lava pool
sim.step()
sim.render(canvas)
```

### Post-Processing Effects

```python
from spore_engine import (
    box_blur, glow, edge_detect, dither, scanlines, vignette,
    chromatic_aberration, pixelate, palette_remap
)

box_blur(canvas, radius=3)
glow(canvas, threshold=200, radius=4, intensity=0.5)
edge_detect(canvas, threshold=0.3)
dither(canvas)
scanlines(canvas, intensity=0.3)
vignette(canvas, intensity=0.5)
palette_remap(canvas, gradient)
```

### Screen Effects

One-shot screen effects + the stateful `ScreenFX` manager.

```python
from spore_engine import shake, fade_overlay, flash, crossfade, Color, ScreenFX

shake(canvas, intensity=3)                    # one shot
fade_overlay(canvas, color=Color(255, 0, 0), alpha=0.3)
flash(canvas, alpha=0.5)
crossfade(dst_canvas, src_canvas, alpha=0.5)

fx = ScreenFX()      # timed, ticking effects — see "ScreenFX" section above
fx.add_shake(2.0); fx.tick(dt); fx.apply(canvas)
```

### Scene Transitions

Animated transitions between scenes: fade, wipe, slide, checkerboard, and pixel dissolve.

```python
from spore_engine import Fade, Wipe, Slide

t = Fade()
t.apply(new_canvas, old_canvas, progress=0.5)

w = Wipe(direction='right')
w.apply(new_canvas, old_canvas, t=0.5)

s = Slide(direction='left')
s.apply(new_canvas, old_canvas, t=0.3)
```

### Shader Pipeline

```python
from spore_engine import ShaderPipeline, WaveDistort, Posterize, Emboss

pipeline = ShaderPipeline(
    WaveDistort(amplitude=3, frequency=4),
    Posterize(levels=4),
    Emboss()
)
pipeline.apply(canvas, t)
```

### Volumetric Effects

Volumetric fog, light cones, and smoke plume rendering for atmospheric effects.

```python
from spore_engine import VolumetricFog, LightCone, SmokePlume, Color

fog = VolumetricFog(width=80, height=40, density=0.3)
fog.color = Color(200, 200, 255)
fog.update(dt)
fog.apply(canvas)
```

### 2D Lighting

Dynamic 2D lighting with raycast shadows, falloff, and light managers.

```python
from spore_engine import Light, LightManager, Color

manager = LightManager()
manager.add(Light(x=40, y=20, radius=15, color=Color(255, 200, 100)))
manager.render_to_canvas(canvas)
```

### Flow Fields

Vector field-based particle motion with vortex, sink, source, and swirl field sources.

```python
from spore_engine import FieldSource, VectorField, FieldSystem

field = VectorField()
field.add(FieldSource(x=40, y=20, strength=1, kind='vortex'))
system = FieldSystem(num_particles=200, width=80, height=40)
system.field = field
system.update(dt)
system.render(canvas, t)
```

### Terminal UI

> `Input` at the top level is the *core keyboard* class. The text-input
> widget is `TextField` (from `spore_engine.ui` or the top level).

```python
from spore_engine import TerminalApp, Button, Label, TextField, ProgressBar, Slider

def my_app():
    app = TerminalApp(width=60, height=20)
    
    label = Label(10, 2, 'Hello TUI!')
    app.add(label)
    
    def on_click():
        label.text = 'Clicked!'
    btn = Button(10, 5, text='Click Me', callback=on_click)
    app.add(btn, focusable=True)
    
    field = TextField(10, 8, width=20)
    app.add(field, focusable=True)
    
    app.run()

my_app()
```

### Widget Reference

All widgets share these properties:
- `x, y, width, height` — Position and size
- `visible` — Toggle visibility
- `focused` — Keyboard focus state

**Widgets available:**

| Widget | Description | Focusable |
|--------|-------------|-----------|
| `Label` | Static text | No |
| `Button` | Clickable action button | Yes |
| `TextField` | Text input field | Yes |
| `Checkbox` | Boolean toggle | Yes |
| `RadioGroup` | Mutually exclusive options | Yes |
| `Slider` | Value slider (0-1) | Yes |
| `Toggle` | On/off switch | Yes |
| `Menu` | Selectable list | Yes |
| `TabBar` | Tabbed navigation | Yes |
| `Table` | Data table with selection | Yes |
| `ProgressBar` | Animated progress indicator | No |
| `TextBox` | Multi-line text display | No |
| `Frame` | Bordered container | No |
| `Divider` | Horizontal/vertical separator | No |
| `StatusBar` | Bottom status line | No |
| `Form` | Labelled field container | No |
| `Dialog` | Modal overlay with buttons | No (buttons focusable) |

### TileMap & Camera

Tile-based maps with scrolling camera, procedural platformer/cave generation, and auto-tiling.

> `TileCamera` is the tile-map scroll camera (core `Camera` is the world
> viewport — two distinct types, two distinct names).

```python
from spore_engine import TileMap, TileCamera, generate_platformer

tilemap = generate_platformer(80, 24, seed=42)
cam = TileCamera(x=0, y=0, width=40, height=20)
cam.follow(player_x, player_y, tilemap.width, tilemap.height)
tilemap.render(canvas, {1: ('#', (139, 90, 43))}, cam.x, cam.y)
```

### Bitmap Font

Resolution-independent bitmap font rendering with scaling and gradient support.

```python
from spore_engine import Font, Color

font = Font.default_5x7()
font.render_text(canvas, "BIG TEXT", x=5, y=5, scale=2, fg=Color(255, 0, 0))
font.render_text_gradient(canvas, "GRADIENT", x=5, y=15, scale=3)
```

---

## Video Playback

```python
from spore_engine.media.converter import video_to_player

player = video_to_player('movie.mp4', width=80, max_frames=300)

# In your render loop:
player.update(dt)          # Advance frame
player.render(canvas)      # Blit current frame to canvas
```

---

## Glyph Art (copyable plain-text ASCII)

Converts images, videos, and GIFs to pure ASCII text with no ANSI escape codes — output that can be selected and copied directly.

### Plain text (monochrome)

```python
from spore_engine.media.glyphart import image_to_glyph, SHADE_DEFAULT, SHADE_RICH

# Standard 10-char ramp
text = image_to_glyph('photo.jpg', width=80)
print(text)  # copyable!

# Rich 70+ char ramp for finer detail
text = image_to_glyph('photo.jpg', width=80, shade=SHADE_RICH)
```

### Coloured glyphs (for display)

```python
from spore_engine.media.glyphart import image_to_glyph_colored

text, colors = image_to_glyph_colored('photo.jpg', width=80)
# text: plain ASCII chars
# colors[y][x] = (R, G, B) — pixel colour from original image
```

### Video / GIF → glyph frames

```python
from spore_engine.media.glyphart import video_to_glyph_frames, is_animated

# Detect animated content
if is_animated('animation.gif'):
    frames = video_to_glyph_frames('animation.gif', width=80, max_frames=100)
    for frame in frames:
        print(frame)

# With colour data
frames = video_to_glyph_colored_frames('movie.mp4', width=80)
text, colors = frames[0]
```

### Play glyph video in terminal

```python
from spore_engine.media.glyphart import play_glyph_video

# frames from video_to_glyph_frames()
play_glyph_video(frames, fps=15, loop=False)
```

### Character ramps

| Name | Characters | Use |
|------|-----------|-----|
| `SHADE_DEFAULT` | ` .:-=+*#%@` | Quick preview |
| `SHADE_REV` | `@%#*+=-:. ` | Inverted (dark bg) |
| `SHADE_RICH` | ` .'`^",:;Il!i><~+_-?][}{1)(\|/tfjrxnuvczXYUJCLQ0OZmwqpdbkhao*#MW&8%B@$` | Highest detail |
| `SHADE_BLOCK` | ` .░▒▓█` | Block characters |

### Demo scene

Scene **#86** — "Glyph Art":
```bash
GLYPH_IMG=~/myphoto.jpg python3 demo.py
```

Auto-saves plain text to `/tmp/glyph_art.txt` every time the shade ramp cycles.

## Output Formats

### ANSI Truecolor (default)
Standard output with full 24-bit color escapes. Works in:
- GNOME Terminal, Konsole, iTerm2, Kitty, Alacritty, WezTerm
- Windows Terminal, VS Code terminal
- Most modern terminals

### Plain text (no color)
```python
c = Canvas(80, 24)
# ... draw ...
# Just strip colors or use export_plain_text()
from spore_engine.media.ansi_io import export_plain_text
text = export_plain_text(c)
```

### File export
```python
from spore_engine.media.ansi_io import save_ansi_file
save_ansi_file('output.ans', c)     # ANSI art file with cursor positioning
```

---

## Performance Tips

1. **Keep canvas small** — 80×24 is standard. Larger canvases mean more cells to process.
2. **Use HiResCanvas sparingly** — It doubles vertical cells.
3. **Limit post-processing** — Box blur and glow are O(w·h·radius²).
4. **Substep physics** — 4-8 substeps per frame for stable simulations.
5. **Reduce ray tracing resolution** — Sample every 2nd or 4th pixel.
6. **Pre-compute noise** — Cache noise values for static terrain.
7. **Use batch drawing** — `fill_rect()` is faster than individual `set_pixel()`.
8. **Clearing every frame is fine** — `render_to()` diffs against the previous frame, so clear-then-repaint only writes what actually changed. Don't pass `force_full=True` per frame; reserve it for resizes/desyncs.

---

## Terminal Requirements

- **ANSI truecolor:** `COLORTERM=truecolor` or terminal supports 24-bit color
- **UTF-8:** Required for half-block characters (▀ ▄ █) and Unicode box drawing
- **Raw mode:** Interactive features use `tty.setraw()` for immediate key input
- **Mouse:** SGR mouse protocol for TUI widget interaction
