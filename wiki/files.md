# File-by-File Contribution Guide

This document explains how every source file contributes to the Spore Engine.

---

## Package Structure

```
spore_engine/
├── __init__.py          # Public API — re-exports everything
├── core/                # Core rendering primitives
├── fx/                  # Visual effects
├── render3d/            # 3D rendering pipeline
├── sim/                 # Simulations (physics, fluids, CA, noise)
├── gen/                 # Procedural generation
├── ui/                  # Terminal UI toolkit
├── anim/                # Animation system
├── easy/                # Simple high-level API (sprites, animation, app)
└── media/               # Media I/O (images, video, ANSI)
```

---

## Core (`spore_engine/core/`)

### `__init__.py`
Re-exports all core types for convenient `from spore_engine import Canvas, Color, ...`.

### `color.py`
**`Color`** — Immutable RGB dataclass with ANSI truecolor escape generation, HSV/hex conversion, luminance, lerp, blend, mul, and ANSI 256 approximation.
**`Gradient`** — Multi-stop color gradient evaluable at any `t ∈ [0, 1]`. Supports 7 named palettes (fire, ice, neon, ocean, forest, sunset, grayscale).
**`PALETTES`** — 7 predefined color ramps (11 stops each).
**Role:** All visible output passes through Color for ANSI formatting.

### `geom.py`
**`Vec2`** — 2D vector with addition, subtraction, scalar multiply, dot, cross (scalar), length, normalize, distance.
**`Vec3`** — 3D vector with same ops plus 3D cross product.
**`Mat4`** — 4×4 homogeneous transformation matrix with multiply, transform (with perspective divide), identity, translate, scale, rotate_x/y/z, perspective (frustum projection), look_at (UVN camera).
**Role:** Foundation for all spatial math — 2D physics, 3D rendering, camera systems.

### `canvas.py`
**`Cell`** — A single terminal cell: char, fg Color, bg Color, z-depth.
**`Canvas`** — The primary framebuffer (`w × h` Cell grid). Drawing methods:
- `set_pixel`, `get_pixel` — with z-depth occlusion test
- `draw_line` — Bresenham integer line
- `draw_circle` — Midpoint circle (outline/fill)
- `draw_ellipse` — Midpoint ellipse
- `draw_triangle` — Scanline fill
- `draw_polygon` — General polygon (even-odd fill)
- `draw_bezier` — Bezier curve evaluation
- `draw_arc` — Arc segment
- `draw_rect` — Rectangle (with rounded corners)
- `gradient_fill` — Horizontal/vertical gradient
- `gradient_fill_radial` — Radial gradient
- `fill` — Flood fill (BFS)
- `draw_text` — Text placement
- `half_block`, `half_block_pixel` — Unicode half-block primitives
- `render_to` — ANSI escape code output
- `copy` — Deep copy

**`HiResCanvas`** — Double-resolution canvas (`w × 2h` buffer). `to_canvas()` maps vertical pixel pairs to half-block chars (▀ ▄ █) for 2× vertical resolution.
**Role:** Everything renders to Canvas (or HiResCanvas). The entire engine's output surface.

### `sprite.py`
**`Sprite`** — ASCII art sprite with `from_string()`, `from_file()`, `blit_to(canvas)`, mirror, rotate, scale.
**Role:** Reusable ASCII art assets (tiles, logos, decorations).

---

## Visual Effects (`spore_engine/fx/`)

### `effects.py`
**`plasma()`** — Animated plasma pattern using sine waves of x, y, and time with HSV coloring.
**`fire()`** — Heat diffusion fire: each pixel averages neighbors then decays, with random fuel injection at bottom.
**`starfield()`** — 3D starfield: random points moving toward viewer with speed-controlled parallax.
**`matrix_rain()`** — Matrix code rain: falling katakana columns with ground pooling, flash events, scanlines.
**`ParticleSystem` / `Burst`** — Particle emitter. `Burst` spawns particles at a point with random velocity, lifetime, color. `ParticleSystem` manages multiple bursts.
**`Emitter` / `FountainEmitter` / `StreamEmitter` / `FireEmitter`** — Continuous particle emitters.
**Role:** Reusable visual effects for demo scenes and games.

### `field.py`
**`VectorField`** — A grid of direction vectors defining a 2D flow field.
**`FieldParticle`** — Particle that follows the vector field, creating stream-like patterns.
**`FieldSystem`** — Manages field sources and thousands of tracing particles.
**`FieldSource`** — Creates radial, vortex, uniform, or noise-based vector fields.
**Role:** Organic flow visualization, smoke/water current simulation.

### `lighting.py`
**`Ray2D`** — 2D ray for lighting calculations.
**`cast_ray()`** — Ray-scene intersection for 2D lighting.
**`cast_ray_dda()`** — DDA grid traversal for tile-map shadow casting.
**`visibility_polygon()`** — Compute visible area from a point (field-of-view).
**`Light` / `LightManager`** — Point lights with additive blending.
**`render_shadows()`** — DDA-based shadow cone rendering.
**Role:** 2D lighting system for game-like scenes.

### `postfx.py`
9 post-processing effects applied to Canvas after scene rendering:
- **box_blur** — Average neighbors within radius (low-pass filter)
- **glow** — Bloom: bright pixel intensity spreads outward
- **edge_detect** — Sobel gradient magnitude → outline
- **dither** — Floyd-Steinberg error diffusion
- **scanlines** — CRT-style alternating row dimming
- **vignette** — Radial edge darkening
- **chromatic_aberration** — Split RGB channels horizontally
- **pixelate** — Block-average nearest-neighbor
- **palette_remap** — Map luminance through a gradient
**Role:** Polish and stylize rendered output.

### `screenfx.py`
Screen-space effects: `shake` (random offset), `fade_overlay` (color blend), `flash` (white burst), `crossfade`, `color_overlay`, `vignette`, `scanlines`.
**Role:** Camera/screen effects for dynamic scenes.

### `shaders.py`
16 modular shaders in a `ShaderPipeline` framework:
- WaveDistort, SwirlDistort, KuwaharaFilter, Posterize, Solarize, CelShade, HeatHaze, Emboss, PixelSort, Crystallize, ASCIIRemap, ChannelShift, Kaleidoscope, Warp, VHSGlitch, Ripple
- `ShaderPipeline` chains shaders sequentially.
**Role:** Composable post-processing pipeline for complex effects.

### `textfx.py`
12 text animation effects: glitch, typewriter, sine, rainbow, gradient, scroll, star wars crawl, wave, fire, matrix rain, bounce, zoom.
**Role:** Animated text for titles, UI, and transitions.

### `transitions.py`
Scene transition effects: `Fade`, `Wipe` (4 dirs), `Slide` (4 dirs), `Checkerboard`, `PixelDissolve`. All interpolate between two canvases over time.
**Role:** Smooth scene transitions in the demo player.

### `volumetric.py`
**`VolumetricFog`** — Dynamic fog grid with wind drift, decay, and scene blending. Density driven by sine-wave noise with optional light-position falloff.
**`LightCone`** — Conical spotlight with configurable angle, width, length, color, flicker, and height-map shadow occlusion.
**`SmokePlume`** — Particle-based smoke emitter with wind, turbulence, and lifetime-based fade-out.
**`VolumetricRenderer`** — Orchestrates fog, light cones, and smoke plumes in a single update/render pass.
**Role:** Volumetric lighting and atmospheric effects.

---

## 3D Rendering (`spore_engine/render3d/`)

### `engine3d.py`
**`Mesh3D`** — Polygon mesh with vertices (Vec3 list), faces (index lists), edges, face colors.
- Primitive generators: `cube()`, `sphere()` (UV parametrization), `torus()` (major/minor radius), `icosphere()` (recursive subdivision of icosahedron), `pyramid()`.
- Face normal calculation via cross product.
- Back-face culling via normal·view_direction.
- Lambertian diffuse lighting.
- Painter's algorithm depth sorting.
**`render_mesh_wireframe()`** — Project vertices, draw edges with depth-based shading.
**`render_mesh_solid()`** — Project faces, scanline fill with lighting.
**Role:** All 3D polygonal rendering.

### `isometric.py`
**`IsoTile`** — Diamond-shaped isometric tile with shaded faces (3D depth cue).
**`IsoCamera`** — Pan and zoom for isometric viewport.
**`IsoMap`** — Generates isometric tile grid from heightmap with material assignment.
**Role:** 2.5D isometric terrain rendering.

### `raytracer.py`
**`Scene`** — Ray tracing scene with `Sphere` and `Plane` primitives.
- **Sphere intersection:** Quadratic formula.
- **Plane intersection:** Ray-plane equation.
- **Phong lighting:** Diffuse + Blinn-Phong specular + ambient.
- **Shadow rays:** Occlusion test toward each light.
- **Reflection:** Recursive (max depth 3) using reflection vector `R = D − 2(N·D)·N`.
**Role:** Photorealistic ASCII ray tracing.

### `voxel.py`
**`VoxelScene`** — Comanche-style voxel terrain renderer: ray-casts through a heightmap, colors by altitude and shades with directional lighting and exponential fog.
**Role:** Fast pseudo-3D terrain rendering.

### `sdf.py`
**Primitives** — `sd_sphere()`, `sd_box()`, `sd_torus()`, `sd_cylinder()`, `sd_plane()` — Signed distance functions for basic shapes.
**Operations** — `op_union()`, `op_subtract()`, `op_intersect()`, `op_smooth_union()`, `op_repeat()` — CSG composition and repetition.
**`SDFScene`** — Full ray-marched SDF renderer with Phong lighting, shadows, reflections (recursive, depth 4), and adaptive stepping. Renders via `render()` (block averaging) and `render_preview()` (shade characters).
**Role:** Signed distance field ray-marching for 3D rendering.

### `model_loader.py`
**`load_obj()`** — Parse Wavefront OBJ files (vertices, faces, normals) into a `Mesh3D` with automatic edge computation.
**`load_ply()`** — Parse Stanford PLY files (ASCII format, vertices + faces) into a `Mesh3D` with color and edge computation.
**Role:** Import external 3D models from standard file formats.

---

## Simulations (`spore_engine/sim/`)

### `physics.py`
**`Body`** — Circular rigid body with semi-implicit Euler integration, NaN sanitization, velocity capping, boundary collision.
**Impulse-based collision resolution** — Overlap correction + impulse from conservation of momentum. Coefficient of restitution controls bounciness.
**`Spring`** — Hooke's law with damping.
**`PhysicsWorld`** — Manages bodies and springs. Substepping for stability.
- `chain()` — Hanging chain of bodies.
- `cloth()` — Cloth grid with structural + shear springs.
**`AABB` / `RectBody`** — Axis-aligned bounding box and rectangular rigid body.
**`PolyBody`** — Convex polygon rigid body.
**`CompoundBody`** — Group of PolyBodies rigidly attached.
**`EnhancedPhysicsWorld`** — Full SAT collision: `sat_collide()`, `resolve_poly_poly()`, `resolve_circle_poly()`, `resolve_circle_aabb()`.
**Role:** 2D physics engine.

### `fluid.py`
**`FluidSim`** — 2D Navier-Stokes solver (Jos Stam stable fluids):
- Diffusion (Gauss-Seidel), projection (Poisson solve), advection (semi-Lagrangian).
- Vorticity (curl) field visualization.
**`WaveSim`** — 2D wave equation solver with splash generation.
**Role:** Fluid dynamics and wave animation.

### `noise.py`
**`PerlinNoise`** — 2D/1D Perlin noise with fBm and ridge noise.
**`ValueNoise`** — Simpler bilinear-interpolated lattice noise.
**`WorleyNoise`** — Cellular/Voronoi distance noise.
**`OpenSimplexNoise`** — Patent-free simplex noise (better rotational symmetry).
**Role:** Procedural generation foundation — terrain, textures, effects.

### `cellular.py`
**`GameOfLife`** — Conway's Game of Life with pattern presets.
**`Automata1D`** — Wolfram-style 1D CA (rule 0-255).
**`WireWorld`** — 4-state electron signal propagation.
**`LangtonsAnt`** — Turing-complete ant automaton.
**`ReactionDiffusion`** — Gray-Scott model with 8 named presets.
**Role:** Cellular automata for simulation and pattern generation.

### `powder.py`
**`PowderSim`** — Cellular material simulation with 12 materials: SAND, WATER, STONE, WOOD, FIRE, SMOKE, OIL, LAVA, ACID, PLANT, SALT, STEAM. Bottom-to-top update, material reactions, temperature tracking.
**Role:** Sandbox physics simulation.

### `physics3d.py`
**`Body3D`** — 3D spherical rigid body with semi-implicit Euler integration, gravity, boundary collision, and restitution.
**`BoxBody3D`** — 3D box rigid body with vertex computation and inertia tensor.
**`Spring3D`** — 3D Hooke's law spring with damping connecting two bodies.
**`PhysicsWorld3D`** — 3D physics world managing bodies, springs, collision detection/resolution, and chain generation.
**Role:** 3D physics simulation.

### `softbody.py`
**`SoftBody`** — Pressure-based soft body with node-link mesh, volume preservation, and factory methods: `circle()`, `blob()`, `square()`.
**`SoftBodyWorld`** — Manages multiple soft bodies with boundary collision and per-step update.
**Role:** Soft-body physics with pressure-volume constraint.

### `steering.py`
**`SteerAgent`** — Autonomous agent with steering behaviors: seek, flee, arrive, pursue, evade, wander, flock (separation/alignment/cohesion), obstacle avoidance, and path following.
**`SteerWorld`** — Manages agents and obstacles with wrap/bounce boundary modes.
**Role:** Autonomous steering behaviors for AI agents.

---

## Procedural Generation (`spore_engine/gen/`)

### `terrain.py`
**`Terrain`** — Heightmap generation via fBm noise, island falloff, bilinear interpolation, contour lines, marching squares, 3D side view, wireframe 3D view.
**Role:** Terrain generation and visualization.

### `fractals.py`
**`Mandelbrot`** — Mandelbrot set with smooth zoom and HSV coloring.
**`BurningShip`** — Burning Ship fractal (`z = (|Re(z)| + i|Im(z)|)² + c`).
**`NewtonFractal`** — Newton's method fractal with animated roots.
**`BarnsleyFern`** — IFS fern with growing animation.
**Role:** Fractal rendering.

### `lsystem.py`
**`LSystem`** — L-system generator: parallel string rewriting with turtle interpretation (F, G, +, -, [, ]). 10 presets: tree1-3, plant, sierpinski, dragon, koch, hilbert, bush, weed.
**Role:** Procedural plant and fractal pattern generation.

### `erosion.py`
**`ErosionSim`** — Hydraulic erosion: droplets carry sediment downhill, eroding and depositing based on gradient, inertia, and evaporation.
**Role:** Realistic terrain sculpting.

### `dungeon.py`
**`DungeonGen`** — BSP dungeon generation with room placement, L-corridors, room tagging (entrance, treasure, shop, boss, encounter).
**`RiverGen`** — Noise-guided gradient-descent river tracing.
**`WorldGen`** — Full world generation: heightmap, moisture, biomes, rivers, settlements, features.
**Role:** Procedural game world generation.

### `biome_terrain.py`
**`BiomeMap`** — 12-biome terrain maps (ocean, beach, desert, grassland, forest, rainforest, tundra, taiga, mountain, swamp, snow, river) driven by elevation + moisture + temperature.
**Role:** Realistic biome distribution.

### `splines.py`
**`quadratic_bezier()`**, **`cubic_bezier()`**, **`catmull_rom()`** — Curve evaluation.
**`render_bezier()`**, **`render_catmull_rom()`** — Curve rendering with de Casteljau visualization.
**Role:** Smooth curve generation.

### `scenery.py`
**`ParallaxScenery`** — Multi-layer parallax backgrounds.
**`Cloud` / `CloudLayer`** — Scrolling clouds.
**`MountainProfile`** — Procedural mountain silhouettes.
**`WaterSurface`** — Animated water ripples.
**`Tree`** — Procedural trees.
**`DayNightCycle`** — Color blending over time.
**`render_sky()` / `render_stars()` / `render_moon()`** — Sky rendering.
**Role:** Environmental scenery for game scenes.

### `maze.py`
**`Maze`** — DFS (recursive backtracker) and Prim's generation. BFS/DFS solving with path visualization.
**Role:** Maze generation and pathfinding.

### `wfc.py`
**`WFCTile`** — A single tile with character, colors, edge patterns per direction, and selection probability.
**`WFC`** — Wave Function Collapse implementation with entropy-based tile selection, constraint propagation, and retry on contradiction. Factory methods: `simple_path_tiles()`, `simple_platformer_tiles()`.
**Role:** Tile-based procedural generation via constraint solving.

### `pathfinding.py`
**`AStar`** — A* pathfinder on a weighted grid with diagonal movement, obstacle definition, tile-grid import, visited-node tracking, and step limit. Includes path reconstruction and debug rendering.
**Role:** Grid-based pathfinding for AI movement.

### `delaunay.py`
**`Point`** — 2D/3D point with distance computation.
**`Triangle`** — Triangle with circumcircle calculation for Bowyer-Watson.
**`Delaunay`** — Delaunay triangulation (Bowyer-Watson) with Voronoi diagram generation and mesh/Voronoi rendering.
**Role:** Delaunay triangulation and Voronoi diagram generation.

### `marching_cubes.py`
**`marching_cubes()`** — 3D marching cubes algorithm: evaluates a scalar grid against an isosurface level, generates triangle mesh via lookup tables with vertex interpolation and caching.
**`make_density_grid()`** — Helper to build a 3D density grid from a function.
**Role:** 3D isosurface extraction from volumetric data.

---

## User Interface (`spore_engine/ui/`)

### `widgets.py`
Full TUI widget toolkit:
- **`Widget`** — Base class with position, size, focus, events
- **`Label`**, **`TextBox`** — Text display
- **`Button`** — Clickable with callback
- **`Checkbox`**, **`RadioGroup`** — Selection widgets
- **`Slider`** — Value control
- **`ProgressBar`** — Progress display
- **`Menu`** — Selectable list
- **`TabBar`** — Tabbed container
- **`Table`** — Scrollable data table
- **`Input`** — Text input field
- **`Toggle`** — On/off switch
- **`Frame`** — Bordered container
- **`Divider`** — Horizontal rule
- **`StatusBar`** — Bottom status bar
- **`WidgetManager`** — Focus routing, event dispatch
**Role:** Reusable UI components.

### `toolkit.py`
**`TerminalApp`** — Raw-mode event loop with SGR mouse tracking, keyboard navigation, ANSI output.
**`Form`** — Labelled field form with submit.
**`Dialog`** — Modal dialog with buttons and callbacks.
**Role:** Application framework for TUI programs.

### `font.py`
**`Font`** — 5×7 bitmap font. `render()` draws text, `render_gradient()` with gradient fill. Supports A-Z, 0-9, punctuation.
**Role:** Pixel-accurate text rendering at character level.

### `tilemap.py`
**`TileMap`** — 2D tile grid with collision. Auto-tile box drawing. Platformer and cave generators.
**`Camera`** — Smooth-follow camera with boundary clamping.
**`tile_collide()`** — AABB vs tile grid collision.
**Role:** Tile-based game worlds.

---

## Animation (`spore_engine/anim/`)

### `anim.py`
**`Tween`** — Interpolate a value/attribute over time with easing. Supports loop/yoyo.
**`Sequence`** — Chain tweens sequentially.
**`Oscillator`** — Sine-wave oscillation.
**`Ticker`** — Interval-based callback.
**`Entity`** — Base animated entity with x, y, scale, rotation, opacity.
**`Animator`** — Tweens entity attributes.
**`Path` / `PathFollower`** — Path-following animation.
**Easing functions** — 9 functions: linear, quad_in/out, cubic_in/out, bounce_out, elastic_out, sine_in_out, expo_out.
**Role:** General-purpose animation engine.

### `timeline.py`
**`Keyframe`** — Value + time + easing.
**`Track`** — Keyframe interpolation for one property.
**`Timeline`** — Multi-track parallel orchestration with loop, yoyo, callbacks.
**Role:** Precise temporal control for complex animations.

### `ik.py`
**`Bone`** — Single bone segment with length, angle, position, color, and child hierarchy. Computes end position and world-space transforms.
**`Skeleton`** — Hierarchical bone chain with two IK solvers: FABRIK (forward-and-backward reaching) and CCD (cyclic coordinate descent). Factory methods: `create_arm()`, `create_leg()`, `create_tentacle()`.
**Role:** Inverse kinematics for procedural character animation.

---

## Simple API (`spore_engine/easy/`)

A beginner-friendly high-level layer that wraps the engine's primitives into dead-simple sprite, animation, and app classes.

### `__init__.py`
Exports `App`, `Sprite`, `Anim`, `Button`, `Label`, `Dialog`, `map_range`, `clamp`, `smoothstep`, `lerp_color`, `random_color`.

### `app.py`
**`App`** — Self-contained application with auto main loop, Canvas management, sprite registration, keyboard input, and background fills. Call `App().run()` and you're done. Supports `bg()`, `bg_gradient()`, `bg_art()` for backgrounds, and `on_tick`/`on_key`/`on_any_key`/`on_click`/`on_init` event handlers.

### `sprite.py`
**`Sprite`** — Sprites defined by multi-line ASCII art strings. Properties: `x`, `y`, `z`, `fg`, `bg`, `opacity`, `scale_x`, `scale_y`, `rotation`, `visible`, `bounds`. Methods: `set_art()`, `set_pixel()`, `draw_text()`, `move_to()`, `move_by()`, `spin()`, `pulse()`, `wobble()`, `fade_to()`, `fade_in()`, `fade_out()`, `scale_to()`, `wait()`, `then()`, `clear_anims()`, `contains()`, `copy()`. Factory methods: `Sprite.rect()`, `Sprite.circle()`, `Sprite.from_file()`.

### `anim.py`
**`Anim`** — Internal animation object. Fluent API via `.to(x, y)`, `.fade(opacity)`, `.scale(s)`, `.over(duration)`, `.ease(name)`, `.loop()`, `.yoyo()`, `.delay(sec)`, `.then(callback)`, `.forever()`. Supports tween-based movement, spin, pulse, wobble, and delay.

### `widgets.py`
Lightweight GUI widgets: **`Button`** (clickable with border), **`Label`** (static text), **`Dialog`** (modal overlay with title, message, and buttons).

### `util.py`
Helper functions: `map_range()`, `clamp()`, `smoothstep()`, `lerp_color()`, `random_color()`.

---

## Media I/O (`spore_engine/media/`)

### `converter.py`
**`image_to_canvas()`** — Loads image (PIL or ffmpeg fallback), resizes, maps luminance to shade characters, returns Canvas with truecolor when `color=True`.
**`video_to_ascii()`** — Converts video to `Video` object via ffmpeg raw frame extraction.
**`video_to_player()`** — Direct to `FramePlayer` (ready to play).
**`ScreenRecorder`** — Records Canvas frames to Video.
**Role:** Bridge between external media and the ASCII engine.

### `imaging.py`
**`ImageConverter`** — RGB data → shaded/edge-detected ASCII.
**`canvas_from_text()`** — Parse multiline string to Canvas.
**`scale_canvas()`** — Nearest-neighbor resize.
**`gradient_canvas()`** — Gradient-filled canvas.
**Role:** Utility image operations.

### `video.py`
**`VideoFrame`** — Single frame (char + color buffer).
**`FramePlayer`** — Sequentially plays frames with pause, seek, blending.
**`Video`** — Manages multiple segments, frame chaining, save/load JSON.
**Test generators:** `make_test_video()`, `make_color_bars()`, `make_spinning_donut_video()`.
**Role:** ASCII video playback engine.

### `ansi_io.py`
**`parse_ansi()`** — Parse ANSI escape sequences into frame data.
**`export_ansi()`** — Export Canvas to ANSI art file with cursor positioning.
**`load_ansi_file()` / `save_ansi_file()`** — ANSI art file I/O.
**`export_plain_text()`** — Strip ANSI codes to plain text.
**`canvas_to_block_art()`** — Convert to colored block art.
**Role:** ANSI art import/export.

### `glyphart.py`
**`image_to_glyph()`** — Load image, return plain ASCII text (no ANSI codes). Luminance-to-character mapping with 4 built-in ramps.
**`image_to_glyph_colored()`** — Same but returns `(text, color_grid)` so each char can be displayed in its original pixel colour.
**`video_to_glyph_frames()`** — Extract video/GIF frames as plain ASCII text strings using ffmpeg or PIL.
**`video_to_glyph_colored_frames()`** — Same with colour data per pixel per frame.
**`play_glyph_video()`** — Play pre-extracted glyph frames in terminal (plain text, no ANSI).
**`is_animated()`** — Detect animated GIFs vs static images.
**4 character ramps:** `SHADE_DEFAULT`, `SHADE_REV`, `SHADE_RICH` (70 chars), `SHADE_BLOCK`.
**Role:** Convert images/videos to copyable plain-text ASCII for paste into any text document.

---

## Top-Level Scripts

### `demo.py`
Main interactive demo launcher:
- 127+ scenes with keyboard controls (n/p/space/q/arrows)
- Transition effects between scenes (fade, wipe, slide, checkerboard, dissolve)
- Auto-play mode when not in TTY
- Particle system overlay
- Status bar with scene info

### `easy_demo.py`
Simple API demo: creates sprites from ASCII art, chains animations (move_to, spin, pulse, scale_to) with easing functions, uses keyboard input binding, text placement, and programmatic sprite drawing via `App().run()`.

### Scene Files (`demos/scene_*.py`)
90 files containing 127+ scene functions. Each scene receives `(canvas, hires_canvas, time, particle_system, dt)` and renders into the canvas. Organized by category:

- **3D:** scene_3d.py, scene_raycaster, scene_raytracer, scene_voxel_world, scene_sdf_*.py
- **Effects:** scene_fx.py, scene_particles, scene_shaders, scene_postfx, scene_shader_symphony
- **Simulation:** scene_sim.py, scene_cellular, scene_powder, scene_physics_rigid, scene_physics_enhanced
- **Procedural:** scene_fractals, scene_terrain, scene_dungeon, scene_erosion, scene_biome_demo
- **Animation:** scene_anim.py, scene_timeline, scene_anim_path, scene_ragdoll
- **UI/Toolkit:** scene_ui.py, scene_tui, scene_terminal_app, scene_tilemap
- **Advanced:** scene_wfc, scene_sdf, scene_marching_cubes, scene_softbody, scene_ik, scene_steering, scene_delaunay, scene_volumetric
- **Visual:** scene_landscape, scene_aurora, scene_aurora_storm, scene_black_hole, scene_god_rays, scene_neon_cathedral, scene_cosmic_tunnel, scene_ethereal_ruins, scene_stained_glass, scene_golden_city, scene_astral_cathedral, scene_phoenix, scene_celestial_temple, scene_starry_night, scene_prism_raytracer, etc.
- **Simple:** easy_demo
- **Media:** scene_media_player, scene_video_player, scene_glyph_art, scene_photo_ascii, scene_raytracer_photo
