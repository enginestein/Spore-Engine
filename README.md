# Spore Engine

A library-grade ASCII (text-mode) graphics engine with truecolor ANSI support, 3D rendering, physics, fluid simulation, procedural generation, cellular automata, ray tracing, and 99 demo scenes — all in pure Python with no external dependencies. Also includes image/video/GIF to ASCII conversion via ffmpeg or PIL, plus a **glyph art** module that converts media to copyable plain-text ASCII.

## Feature Highlights

| Subsystem | Key Components |
|---|---|
| **Simple API** | `App`, `Sprite`, `Anim` — sprites from ASCII art, tweened animations, keyboard/mouse input, fluent chaining |
| **Core Rendering** | `Canvas`, `HiResCanvas` (2x braille), `Color` (HSV, hex, blending, gradients), `Sprite`, `Vec2`/`Vec3`/`Mat4` |
| **3D Rendering** | `Mesh3D` with wireframe & solid shading, OBJ/PLY loader, backface culling, depth sort, light direction |
| **Isometric** | `IsoTile`, `IsoMap`, `IsoCamera` — tile grid with screen projection |
| **Voxel** | `VoxelScene` — heightmap-based 3D landscape with directional shading & fog |
| **Ray Tracing** | `Scene`, `Sphere`, `Plane`, Phong shading, reflections, refraction, multiple light sources |
| **SDF Ray Marching** | `SDFScene`, `sd_sphere`/`sd_box`/`sd_torus`/`sd_cylinder`, CSG ops (union/subtract/intersect/smooth/repeat) |
| **Physics 2D** | `PhysicsWorld`, `Body`, `Spring`, `AABB`, `RectBody`, `RayCast`, `ForceField`, `DistanceJoint`, SAT collision (`PolyBody`, `CompoundBody`, `sat_collide`) |
| **Physics 3D** | `Body3D`, `BoxBody3D`, `Spring3D`, `PhysicsWorld3D` with gravity, rotation, bounds |
| **Soft Body** | `SoftBody` — pressure-based volume preservation, spring networks, circle/polygon shapes, cloth |
| **Steering Behaviors** | `SteerAgent`, `SteerWorld` — seek, flee, arrive, pursue, evade, wander, flock (separation/alignment/cohesion), path follow, obstacle avoidance |
| **Fluid Simulation** | `FluidSim` (Navier-Stokes with vorticity confinement), `WaveSim` (2D wave equation) |
| **Particle System** | `Particle`, `Burst`, `Emitter`, `FountainEmitter`, `StreamEmitter`, `FireEmitter` — particle life, trails, burst_explosion/burst_ring/burst_directional |
| **Vector Fields** | `FieldSource` (vortex/sink/source/swirl), `VectorField`, `FieldParticle`, `FieldSystem` |
| **2D Lighting** | `Ray2D`, `Light`, `LightManager`, `cast_ray`/`cast_ray_dda`, `visibility_polygon`, `render_shadows` |
| **Visual Effects** | `plasma`, `fire`, `starfield`, `matrix_rain` |
| **Text Effects** | 12 animations: `glitch_text`, `typewriter_text`, `sine_text`, `rainbow_text`, `gradient_text`, `scroll_text`, `star_wars_crawl`, `wave_text`, `fire_text`, `matrix_code_rain`, `bounce_text` |
| **Screen Effects** | `shake`, `fade_overlay`, `flash`, `crossfade`, `color_overlay` |
| **Post-Processing** | `box_blur`, `glow`, `edge_detect`, `dither`, `scanlines`, `vignette`, `chromatic_aberration`, `pixelate`, `palette_remap` |
| **Shader Pipeline** | `Shader`, `ShaderPipeline` — 16 modular shaders: `WaveDistort`, `SwirlDistort`, `KuwaharaFilter`, `Posterize`, `Solarize`, `CelShade`, `HeatHaze`, `Emboss`, `PixelSort`, `Crystallize`, `ASCIIRemap`, `ChannelShift`, `Kaleidoscope`, `Warp`, `VHSGlitch`, `Ripple` |
| **Scene Transitions** | `Fade`, `Wipe` (4 dirs), `Slide`, `Checkerboard`, `PixelDissolve` |
| **Volumetric FX** | `VolumetricFog`, `LightCone`, `SmokePlume`, `VolumetricRenderer` |
| **Animation** | `Tween`, `Sequence`, `Oscillator`, `Ticker`, 20+ easing functions, `Animator`, `Entity`, `Path`/`PathFollower`, `Keyframe`/`Track`/`Timeline`, IK `Bone`/`Skeleton` (FABRIK solver, arm/leg/tentacle creators) |
| **Procedural Gen** | `Terrain` (Perlin heightmap + island), `Maze` (DFS/Kruskal), `LSystem` (stochastic too), `DungeonGen` (BSP rooms+corridors), `ErosionSim`, `WFC` (wave function collapse), fractals (`Mandelbrot`, `BurningShip`, `NewtonFractal`, `BarnsleyFern`) |
| **Noise** | `PerlinNoise` (2D/3D, fbm), `WorleyNoise`, `OpenSimplexNoise`, `ValueNoise` |
| **Cellular Automata** | `GameOfLife`, `Automata1D`, `WireWorld`, `LangtonsAnt`, `ReactionDiffusion` (Gray-Scott), 12+ built-in GoL patterns |
| **Powder Simulation** | `PowderSim` — 12 materials (Sand/Water/Stone/Wood/Fire/Smoke/Oil/Lava/Acid/Plant/Salt/Steam), liquid/gas/solid physics, flammability, melting, erosion |
| **Biome Maps** | `BiomeMap` — 12 biomes from elevation/moisture/temperature (ocean, beach, desert, grassland, forest, rainforest, tundra, taiga, mountains, snow, swamp, savanna) |
| **Scenery** | `ParallaxScenery`, `ParallaxLayer`, `Cloud`, `CloudLayer`, `MountainProfile`, `Tree`, `WaterSurface`, `DayNightCycle` (sky/stars/moon) |
| **Curves & Splines** | `quadratic_bezier`, `cubic_bezier`, `catmull_rom` with rendering |
| **Pathfinding** | `AStar` — 4/8-directional, weighted grid, path visualization |
| **Delaunay / Voronoi** | `Delaunay`, `Point`, `Triangle`, circumcircle-based triangulation, Voronoi diagram rendering |
| **Marching Cubes** | 3D isosurface extraction to `Mesh3D` with density grid generation |
| **Terminal UI** | 17 widgets: `Label`, `TextBox`, `ProgressBar`, `Button`, `Menu`, `Frame`, `Checkbox`, `RadioGroup`, `TabBar`, `Slider`, `Table`, `Input`, `Toggle`, `Divider`, `StatusBar`, `WidgetManager` + `TerminalApp` (event loop, mouse, keyboard), `Form`, `Dialog` |
| **TileMap** | `TileMap`, `Camera`, auto-tiling, collision, `generate_platformer`, `generate_cave` |
| **Bitmap Font** | `Font` — 5x7 character glyphs |
| **Media I/O** | Image/video/GIF → ASCII (`ImageConverter`, `image_to_canvas`, `video_to_ascii`), `ScreenRecorder`, `glyphart` (copyable plain-text ASCII), ANSI file I/O (parse/export/save/load), `Video`/`FramePlayer`, canvas scaling & gradient |
| **Demo Scenes** | 98+ interactive demo scenes in `demo.py` / `demos/` |

## Quick Start

```bash
python3 easy_demo.py             # Simple API demo (sprites, animation, input)
python3 demo.py                  # Interactive demo (98+ scenes)
```

```python
# Easy API — sprites from ASCII art, fluent animation
from spore_engine.easy import App, Sprite

app = App()
player = Sprite("""  @  \n /@\\ \n / \\""", x=5, y=10, fg=Color(255, 200, 100))
player.move_to(70, 10).over(3).ease('bounce_out')
app.run()
```

```python
# Low-level API — full control
from spore_engine import Canvas, Color

c = Canvas(80, 24)
c.draw_text(10, 10, 'Hello Spore!', Color(255, 128, 0))
c.render_to(print)
```

```python
# Tween animation with chaining
from spore_engine import Tween

t = (Tween(0, 100, 2, 'bounce_out')
     .on_update(lambda v: print(f'Value: {v:.1f}'))
     .on_done(lambda: print('Done!'))
     .start())
```

```python
# Terminal GUI
from spore_engine.ui import TerminalApp, Label, Button

app = TerminalApp()
app.add(Label(5, 3, 'Hello, world!', fg=Color(0, 255, 0)))
app.add(Button(5, 5, 'Quit', on_click=lambda: app.stop()))
app.run()
```

## Documentation

- [`docs/usage.md`](docs/usage.md) — Comprehensive usage guide
- [`wiki/math.md`](wiki/math.md) — Vector/matrix math, rendering math, simulation math
- [`wiki/files.md`](wiki/files.md) — How each file contributes to the engine
- [`wiki/architecture.md`](wiki/architecture.md) — How everything works together

## Glyph Art (copyable ASCII)

```bash
GLYPH_IMG=~/photo.jpg python3 demo.py    # scene 86 — coloured ASCII glyph art
```

```python
from spore_engine.media.glyphart import image_to_glyph, image_to_glyph_colored

# Plain text (copyable, no ANSI codes)
text = image_to_glyph('photo.jpg', width=80)
print(text)                               # ← select & copy this

# Coloured glyph data for display
text, colors = image_to_glyph_colored('photo.jpg', width=80)
```

## Requirements

- Python 3.10+
- A terminal with ANSI truecolor support
- No external Python dependencies
- Optional: `ffmpeg` and `Pillow` for image/video/GIF conversion

## License

MIT
