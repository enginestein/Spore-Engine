# Usage Guide

Comprehensive guide to using the Spore Engine.

---

## Installation

```bash
git clone <repo> ~/ascii-engine
cd ~/ascii-engine
```

No pip install required. Just import `spore_engine` from the project root.

**Optional dependencies for media features:**
```bash
pip install Pillow              # Better image loading
sudo apt install ffmpeg         # Video conversion (or brew install ffmpeg)
```

---

## Simple API (spore_engine.easy)

A high-level layer for quickly making sprite-based graphics, animations, and simple apps — no manual tween math or boilerplate required.

```python
from spore_engine.easy import App, Sprite
```

### App

Creates a window, runs the main loop, manages sprites and input.

```python
app = App(width=80, height=24, title="My App")
app.run()                        # Start main loop (q to quit)

# Add sprites
s = app.sprite(""" @ \n/@\\""", x=10, y=5, fg=(255, 200, 100))

# Add one-off text
app.text("Hello!", 2, 1, fg=(255, 255, 255))

# Input
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

### Sprite

Create from multi-line ASCII art strings.

```python
# From art string
bird = Sprite("""
  @
 /@\\
/   \\
""", x=20, y=5, fg=(255, 200, 100))

# Programmatic
box = Sprite("", x=10, y=10)
box.set_pixel(0, 0, '┌')
box.set_pixel(0, 0, '┐')

# Factory methods
Sprite.rect(10, 5, char='#', fg=(255, 0, 0))     # Rectangle
Sprite.circle(5, char='*', fg=(0, 255, 0))        # Circle
Sprite.from_file('art.txt')                        # From file
```

### Animations

Fluent chaining — no tweens or math required.

```python
s = Sprite(' @ ', x=0, y=5)

# Move with easing
s.move_to(50, 10).over(2).ease('bounce_out')

# Chained call: move, wait, fade
s.move_to(30, 5).over(1).then(lambda: print('done'))

# Loop forever
s.move_to(30, 18).over(1).ease('bounce_out').loop()

# Built-in effects
s.spin(speed=0.5)                # Rotate forever
s.pulse(min=0.8, max=1.2, period=1.0)   # Scale pulse
s.wobble(amount=3, period=2.0)   # Side-to-side
s.fade_in(2.0)                   # Fade from transparent
s.scale_to(2.0).over(1)          # Scale up
```

### Running the demo

```bash
python3 easy_demo.py             # q to quit, n to change spinner
```

---

## Running the Demo

```bash
python3 demo.py                  # Original 98-scene demo
```

### Controls (interactive terminal mode)

| Key | Action |
|-----|--------|
| `1`-`9` | Jump to scene 1-9 |
| `0` | Jump to scene 10 |
| `n` / `→` | Next scene |
| `p` / `←` | Previous scene |
| `Space` | Toggle pause |
| `q` | Quit |
| `↑` | Send "up" to scene |
| `↓` | Send "down" to scene |

### Non-TTY mode
When stdout is piped or redirected, the demo auto-advances every 5 seconds:
```bash
python3 demo.py | less -R
```

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

# Drawing
c.set_pixel(x, y, '@', Color(255, 0, 0))           # Single pixel
c.draw_line(x1, y1, x2, y2, '#', Color(0, 255, 0)) # Line
c.draw_circle(cx, cy, r, '*', Color(0, 0, 255))     # Circle
c.draw_rect(x, y, w, h, '#', Color(255, 255, 0))   # Rectangle
c.draw_triangle(x1, y1, x2, y2, x3, y3, '@', Color(255,0,0), fill=True)
c.draw_ellipse(cx, cy, rx, ry, '#', Color(255,0,0))
c.draw_bezier([(0,0), (40,20), (80,0)], 30, '@', Color(255,128,0))
c.draw_text(x, y, "Hello!", Color(255, 255, 255))  # Text

# Fill operations
c.fill_rect(x, y, w, h, '@', Color(255, 0, 0))     # Filled rect
c.gradient_fill(x1, y1, x2, y2, gradient)           # Gradient fill
c.fill(x, y, '#')                                     # Flood fill

# Output
c.render_to(sys.stdout)  # ANSI truecolor output

# HiResCanvas
hr.set_pixel(x, y, '@', Color(255, 0, 0))
hr.to_canvas(c)           # Flatten to regular Canvas
```

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
from spore_engine.render3d.raytracer import Scene, Sphere, Plane

scene = Scene()
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

Full-screen effects: shake, fade overlay, flash, crossfade, and color overlay.

```python
from spore_engine import shake, fade_overlay, flash, crossfade, Color

shake(canvas, intensity=3)
fade_overlay(canvas, color=Color(255, 0, 0), alpha=0.3)
flash(canvas, alpha=0.5)
crossfade(dst_canvas, src_canvas, alpha=0.5)
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

```python
from spore_engine import TerminalApp, Button, Label, ProgressBar, Slider, Input

def my_app():
    app = TerminalApp(width=60, height=20)
    
    label = Label(10, 2, 'Hello TUI!')
    app.add(label)
    
    def on_click():
        label.text = 'Clicked!'
    btn = Button(10, 5, text='Click Me', callback=on_click)
    app.add(btn, focusable=True)
    
    slider = Slider(10, 8, value=0.5)
    app.add(slider, focusable=True)
    
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
| `Input` | Text input field | Yes |
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

```python
from spore_engine import TileMap, Camera, generate_platformer

tilemap = generate_platformer(80, 24, seed=42)
cam = Camera(x=0, y=0, width=40, height=20)
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

---

## Terminal Requirements

- **ANSI truecolor:** `COLORTERM=truecolor` or terminal supports 24-bit color
- **UTF-8:** Required for half-block characters (▀ ▄ █) and Unicode box drawing
- **Raw mode:** Interactive features use `tty.setraw()` for immediate key input
- **Mouse:** SGR mouse protocol for TUI widget interaction
