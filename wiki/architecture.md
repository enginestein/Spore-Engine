# Architecture Overview

How the Spore Engine works from top to bottom.

---

## High-Level Architecture

```
easy_demo.py / demo.py    ←  Entry points
         │
    spore_engine/             ←  Library package
    ├── core/                 ←  Canvas, Color, Vec/Mat Math
    ├── fx/                   ←  Visual effects & post-processing
    ├── render3d/             ←  3D rendering pipeline
    ├── sim/                  ←  Physics, fluids, noise, CA
    ├── gen/                  ←  Procedural generation
    ├── ui/                   ←  Terminal UI toolkit
    ├── anim/                 ←  Animation system
    ├── easy/                 ←  Simple high-level API (App, Sprite, Anim)
    └── media/                ←  Image/video I/O + glyph art
         │
    stdout                    ←  ANSI escape codes → terminal
```

*Note: The `easy/` layer (App, Sprite, Anim) wraps lower-level Canvas/Color primitives and scene loop logic into a simple object-oriented API. See "Easy API Architecture" below.*

---

## Rendering Pipeline

### 1. Scene Function
Each scene in `demos/scene_*.py` is a function:
```python
def my_scene(canvas: Canvas, hr: HiResCanvas, t: float, pt: ParticleSystem, dt: float):
    # Draw into canvas or hires_canvas
    hr.set_pixel(x, y, '@', color)
```

### 2. Drawing Primitives
Scene functions use Canvas/HiResCanvas methods:
- `set_pixel()`, `draw_line()`, `draw_circle()`, `draw_triangle()`, etc.
- Each method writes to a `Cell` in the buffer with z-depth occlusion
- Cells store: `char`, `fg` (Color), `bg` (Color), `z`

### 3. Post-Processing (optional)
Effects from `postfx.py` and `shaders.py` can transform the canvas after the scene renders — blur, glow, edge detect, dither, palette remap, etc.

### 4. Output
`canvas.render_to(sys.stdout)` writes ANSI escape sequences:
- `\033[H` — Move cursor home
- `\033[38;2;R;G;Bm` — Set foreground color
- `\033[48;2;R;G;Bm` — Set background color
- `\033[0m` — Reset

For HiResCanvas: `to_canvas()` first flattens the double-resolution buffer to a Canvas using Unicode half-block characters (▀ ▄ █), then renders normally.

### 5. Easy API (App/Sprite)

The `App` class provides a higher-level rendering pipeline for sprite-based applications:

```
App.run()
  → _update(dt): sprite.update(dt), tick handlers
  → _render(): canvas.clear() → _fill_bg() → sort sprites by z → s.render(canvas) → canvas.render_to(stdout)
```

---

## Coordinate Systems

| System | Axis Convention | Used By |
|--------|----------------|---------|
| Canvas pixels | x→ right, y↓ down | All drawing |
| 2D physics | x→ right, y↑ up | `physics.py` |
| 3D world | Right-handed (z forward) | `engine3d.py`, `raytracer.py` |
| Isometric | x→ SE, y→ NE | `isometric.py` |
| UV (texture) | u→ right, v→ down | `raytracer.py` |

---

## Data Flow

### 3D Rendering Data Flow
```
Mesh3D (vertices + faces)
  → Mat4 (model * view * projection)
  → Vertex transform (Vec3 → clip space → NDC → screen)
  → Back-face culling
  → Scanline fill with Lambertian lighting
  → Canvas pixels
```

### Physics Simulation Data Flow
```
PhysicsWorld
  → Body.update()  (semi-implicit Euler)
  → Spring.update() (Hooke's law)
  → Collision detection (circle-circle, SAT for polygons)
  → Impulse resolution
  → NaN sanitization
  → Canvas rendering
```

### Fluid Simulation Data Flow
```
FluidSim
  → Diffusion (Gauss-Seidel)
  → Projection (Poisson solve)
  → Advection (semi-Lagrangian backtrace)
  → Projection (repeat)
  → Dye advection-diffusion
  → Canvas rendering of dye/curl fields
```

### Noise → Terrain Data Flow
```
PerlinNoise.fbm2()
  → Heightmap grid
  → Optional: island falloff, erosion, river carving
  → Topdown rendering (gradient coloring)
  → Or: 3D view via voxel/isometric/wireframe
  → Canvas pixels
```

### SDF Ray Marching Data Flow
```
SDFScene
  → Camera rays (forward, right, up vectors from FOV)
  → Ray-marching loop (max 64 steps, epsilon=0.001)
  → SDF evaluation (_scene_sdf: sphere/box/torus/cylinder/plane)
  → Normal estimation (central differences)
  → Lighting: diffuse + specular + ambient + shadow ray
  → Recursive reflection (max depth 4)
  → Canvas pixels
```

### Soft Body Physics Data Flow
```
SoftBody
  → Node positions (mass-spring network)
  → Link constraints (iterated 3× per frame)
  → Pressure integration (volume preservation via gradient descent)
  → Velocity damping + gravity
  → Self-collision (node repulsion)
  → Bounds clamping
  → Canvas rendering (filled polygon + links + nodes)
```

### Steering Behaviors Data Flow
```
SteerAgent
  → Force accumulation: seek/flee/arrive/pursue/evade/wander
  → Flock forces: separate + align + cohesion (weighted)
  → Obstacle avoidance (look-ahead vector)
  → Path following (waypoint stepping)
  → Truncate to max_force
  → Velocity update (Euler integration)
  → Speed clamping (max_speed)
  → Position update
  → Wrapping or bouncing at world boundaries
  → Canvas rendering (agent + heading + trail)
```

### 3D Physics Data Flow
```
PhysicsWorld3D
  → Substep loop (dt / substeps)
    → Spring3D.update() (Hooke's law + damping)
    → Body3D.update() (gravity, velocity, position, bounds)
    → Collision detection (sphere-sphere, sphere-box via overlap radius)
    → Collision resolution (positional correction + impulse)
  → Canvas rendering
```

### Volumetric Rendering Data Flow
```
VolumetricRenderer
  → VolumetricFog.update() (noise-driven density + decay + wind scroll)
  → LightCone.update() (flicker animation)
  → SmokePlume.update() (particle emission + physics)
  → LightCone.apply() (ray-march through cone, attenuation, height-map shadows)
  → SmokePlume.render() (life-based shading)
  → VolumetricFog.apply() (density-based blend over scene) or render() (direct density view)
  → Canvas
```

### WFC Generation Data Flow
```
WFC
  → reset() (initialize superposition grid)
  → Loop:
    → _lowest_entropy() (find cell with minimum Shannon entropy + noise)
    → _observe() (collapse to tile via weighted random selection)
    → _propagate() (BFS stack: remove invalid neighbors via edge constraints)
  → Repeat until all cells collapsed or contradiction found
  → Canvas rendering (tile char + color)
```

### A* Pathfinding Data Flow
```
AStar
  → Initialization (walkable grid, start/end)
  → Open set: priority queue ordered by f = g + h
  → Loop:
    → Pop lowest f-score node
    → If current == end: reconstruct path
    → Expand neighbors (4-directional or 8-directional with diagonal cost)
    → Compute tentative g; if better than stored, update and push
  → Path reconstruction (reverse traversal from end via came_from)
  → Canvas rendering (obstacles, visited nodes, path)
```

### IK (FABRIK) Data Flow
```
Skeleton
  → _get_chain() (flatten bone hierarchy into list)
  → If target unreachable: stretch toward target
  → Loop (max_iterations):
    → Forward pass: set last position = target, work backward to root (maintain bone lengths)
    → Backward pass: set first position = root, work forward to end effector
    → Convergence check: end effector distance to target < tolerance
  → Update bone positions and angles from solved positions
  → Canvas rendering (bones, joints, angles)
```

### Powder Simulation Data Flow
```
PowderSim
  → Bottom-to-top scan (y = h-2 → 0):
    → Mark cell as updated, decrement life
    → Dispatch to material-specific update function:
      Sand: fall down, slide diagonally, ignite if adjacent to fire
      Water: fall, spread horizontally, displace oil, evaporate to steam
      Fire: rise, emit smoke, ignite flammables, die to smoke
      Lava: fall, ignite/melt neighbors, solidify to stone
      Smoke/Steam: rise, random drift, dissipate
      Oil: fall through water, float on water, ignite
      Acid: dissolve neighbors, fall, self-destruct
      Plant: grow on solid surfaces, regenerate
      Salt: fall, dissolve in water/oil
    → _swap() cells for movement
  → Reset updated flags
  → Canvas rendering (material char + color)
```

### Particle System Data Flow
```
ParticleSystem
  → emit() (create Burst with particles at position)
  → update(dt): each Particle.update() (gravity, drag, trail, life decay)
  → prune dead particles
  → render(canvas): each Particle.render() (shade char based on alpha)
  → Canvas
```

### Maze Generation Data Flow
```
Maze
  → generate_dfs() or generate_prim() (carve passages from wall grid)
  → DFS: recursive backtracker with stack
  → Prim: wall list with random selection
  → solve_bfs() or solve_dfs() (BFS/DFS from start to end)
  → Canvas rendering (wall char + path coloring)
```

### Biome Generation Data Flow
```
BiomeMap
  → PerlinNoise.fbm2() × 3 (elevation, moisture, temperature)
  → Temperature modulated by elevation (lapse rate)
  → get_biome(elevation, moisture, temperature) → biome string
  → BIOMES gradient lookup based on elevation within biome
  → Canvas rendering (colored tiles per biome)
```

---

## Demo System Architecture

### Scene Registration
1. Each `demos/scene_*.py` file exports a scene function
2. `demos/__init__.py` imports all scene functions and registers them in `SCENES = [(name, func), ...]`
3. `demo.py` reads `SCENES` list and cycles through them

### Event Loop (demo.py)
```
while running:
    dt = time() - last_frame
    clear canvas
    if not paused:
        scene_fn(canvas, hr, t, pt, dt)
    if transitioning:
        transition_obj.apply(prev_c, c, trans_t)
    draw HUD (scene name, controls)
    render_to(stdout)
    handle keyboard input (q/n/p/space/arrows/1-0)
    scene changes: trigger transition
```

### Transition System
When switching scenes, the previous frame is saved (`prev_c = c.copy()`), and a random transition interpolates between old and new frames over ~0.8s.

---

## Easy API Architecture

The `easy/` subpackage provides a high-level wrapper around the core rendering and animation systems:

```
App
  ├── owns Canvas, HiResCanvas  ← delegates rendering to core/Canvas
  ├── owns Sprite list           ← each Sprite wraps a pixel array (_cells)
  ├── owns Anim list per Sprite  ← Anim wraps Tween from core/anim
  ├── event handlers (tick, key, click, init)
  └── main loop (timing, input, update, render)
```

- **App** manages the frame loop, input handling, background rendering, and sprite lifecycle.
- **Sprite** wraps a 2D pixel array (list of `(char, dx, dy, fg, bg)` tuples) with position, scale, rotation, opacity, and animation support.
- **Anim** (from `easy/anim.py`) wraps `Tween` to animate Sprite properties (position, opacity, scale, rotation) with easing functions over time.

---

## Color Pipeline

```
Color(r, g, b)
  → .ansi_fg() / .ansi_bg()
  → Embedded in output stream
  → Terminal interprets ANSI escapes
  → 24-bit truecolor pixels on screen
```

For downlevel terminals: `.to_ansi_256()` approximates to xterm 256-color palette.

---

## Key Design Decisions

1. **No external dependencies** — Everything is pure Python. Optional ffmpeg/PIL for media I/O.
2. **Z-buffer** — Each cell stores depth for painter's algorithm occlusion.
3. **HiResCanvas** — Doubles vertical resolution via Unicode half-blocks, no terminal cell size change.
4. **Semi-Lagrangian advection** — Unconditionally stable fluid simulation without CFL constraints.
5. **Substepping** — Physics world divides dt into smaller steps for stable constraint solving.
6. **Double-buffering** — Canvas updates are fully rendered to buffer, then flushed to terminal atomically.
7. **Raw terminal mode** — `demo.py` uses `tty.setraw()` for real-time keyboard input without Enter key.


---

## Module Dependencies

```
core/        ← No internal dependencies (foundation layer)
sim/         → core/ (uses Vec2/Vec3, Color, Canvas)
gen/         → core/ + sim/ (uses noise, physics)
render3d/    → core/ (uses Mat4, Vec3, Canvas)
fx/          → core/ (uses Color, Canvas, Vec2)
anim/        → core/ (uses Color, easing math)
ui/          → core/ (uses Canvas, Color)
easy/        → core/ + anim/ (uses Canvas, Color, Tween)
media/       → core/ (uses Canvas, Color)
```

None of the subpackages depend on each other (except `sim/` → `core/` and `easy/` → `anim/`), keeping the architecture modular.
