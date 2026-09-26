# Spore Engine — Complete Flowchart

```mermaid
flowchart TD

  %% ─── ENTRY POINTS ───────────────────────────────────────────────
  subgraph EP["📂 Entry Points"]
    E1(["easy_demo.py"]) -->|"uses"| EASY_APP
    E2(["demo.py"]) -->|"scene loop →"| E3["demos/scene_*.py"]
    E3 -->|"draws on"| CORE_CANVAS
    E3 -->|"or builds an Image"| IO_IMAGE
    E3 -->|"uses"| FX_EFFECTS
    E3 -->|"uses"| R3D
    E3 -->|"uses"| SIM
    E3 -->|"uses"| GEN
    E3 -->|"uses"| UI_TK
    E3 -->|"uses"| MEDIA
  end

  %% ─── EASY LAYER ────────────────────────────────────────────────
  subgraph EASY["🎯 easy/ — High-Level API"]
    EASY_APP["App"] -->|"manages"| EASY_SPRITE["GameSprite"]
    EASY_APP -->|"creates"| EASY_ANIM["Anim"]
    EASY_APP -->|"creates"| EASY_WIDGETS["SimpleButton / SimpleLabel / SimpleDialog"]
    EASY_APP -->|"input (raw keys)"| CORE_INPUT
    EASY_APP -->|"world camera"| CORE_CAM
    EASY_APP -->|"shake/flash/fade"| SFX_CLASS
    EASY_ANIM -->|"wraps"| ANIM_TWEEN
    EASY_SPRITE -->|"move_to / spin / pulse / fade"| EASY_ANIM
    EASY_SPRITE -->|"renders onto"| CORE_CANVAS
    EASY_APP -->|"run() → loop →"| CORE_CANVAS
  end

  %% ─── CORE ───────────────────────────────────────────────────────
  subgraph CORE["🧱 core/ — Rendering Foundation"]
    CORE_CANVAS["Canvas"] -->|"composed of"| CORE_CELL["Cell{char,fg,bg,z,depth}"]
    CORE_CANVAS -->|"double-res"| CORE_HIRES["HiResCanvas"]
    CORE_HIRES -->|"to_canvas()"| CORE_CANVAS
    CORE_CANVAS -->|"render_to (diff vs previous frame)"| OUTPUT["ANSI Escape Codes → stdout"]

    CORE_COLOR["Color"] --> CORE_CELL
    CORE_GRAD["Gradient"] --> CORE_COLOR
    CORE_SPRITE["Sprite (core)"] -->|"blit_to"| CORE_CANVAS

    CORE_COLOR -->|"ansi_fg/ansi_bg"| OUTPUT

    subgraph DRAW["Drawing Primitives"]
      DRAWSET["set_pixel"] --> CORE_CELL
      DRAWTEXT["draw_text"] --> DRAWSET
      DRAWTEXTAT["draw_text_at / draw_text_centered (9 anchors)"] --> DRAWSET
      DRAWLINE["draw_line"] --> DRAWSET
      DRAWCIRC["draw_circle"] --> DRAWSET
      DRAWRECT["draw_rect"] --> DRAWSET
      DRAWELL["draw_ellipse"] --> DRAWSET
      DRAWTRI["draw_triangle"] --> DRAWSET
      DRAWPOLY["draw_polygon"] --> DRAWSET
      DRAWBEZ["draw_bezier"] --> DRAWSET
      DRAWFILL["fill / fill_rect"] --> DRAWSET
      DRAWGRAD["gradient_fill[_radial]"] --> DRAWSET
      DRAWGRADX["fill_gradient_x/y, fill_sky"] --> DRAWSET
      DRAWARC["draw_arc"] --> DRAWSET
      DRAWBLIT["blit_canvas"] --> DRAWSET
    end
  end

  %% ─── SCENE AUTHORING ─────────────────────────────────────────
  subgraph AUTH["🎮 core — Scene Authoring Stack"]
    AUTH_STATE["SceneState / scene_state()"] -.->|"per-scene memory"| E3
    AUTH_SCENE["Scene / Layer"] -->|"compose + present"| CORE_CANVAS
    AUTH_SCENE -->|"hires over bg"| CORE_HIRES
    CORE_INPUT["Input (KeyEvent / MouseEvent / ResizeEvent, synthesized releases) / KeyState"] -.->|"keys"| E3
    CORE_CAM["Camera (world→screen)"] -->|"to_screen / draw"| CORE_CANVAS
    CORE_UTIL["clamp/lerp/ramp/wave/osc/bounce/..."] -.-> CORE_CAM
    CORE_UTIL -.-> SFX_CLASS
    AUTH_ASSETS["Assets / load_sprite / load_palette / load_model / load_text"] -->|"memoized per file"| CORE_SPRITE
    AUTH_ASSETS --> R3D_LOAD
    AUTH_ECS["World / System / Component / EcsEntity"] -->|"SpriteRenderSystem → blit_to"| AUTH_SCENE
  end

  %% ─── MATH/GEOMETRY ──────────────────────────────────────────────
  subgraph MATH["📐 core/geom — Geometry Foundation"]
    VEC2["Vec2"] --> CORE_CELL
    VEC3["Vec3"] --> R3D_MESH
    MAT4["Mat4"] --> R3D_MESH
    MAT4 -->|"transform"| VEC3
    CORE_GRAD --> CORE_COLOR
  end

  %% ─── ANIMATION ──────────────────────────────────────────────────
  subgraph ANIM["🎬 anim/ — Animation System"]
    ANIM_TWEEN["Tween"] --> ANIM_SEQ["Sequence"]
    ANIM_TWEEN --> ANIM_OSC["Oscillator"]
    ANIM_TWEEN --> ANIM_TICK["Ticker"]
    ANIM_TWEEN --> ANIM_FOLLOWER["PathFollower"]
    ANIM_PATH["Path"] --> ANIM_FOLLOWER
    ANIM_TRACK["Track"] --> ANIM_TIMELINE["Timeline"]
    ANIM_KF["Keyframe"] --> ANIM_TRACK
    ANIM_ENT["Entity"] --> ANIM_ANIMATOR["Animator"]
    ANIM_TWEEN --> ANIM_ANIMATOR

    subgraph IK["Inverse Kinematics"]
      IK_BONE["Bone"] --> IK_SKEL["Skeleton"]
      IK_SKEL -->|"solve_fabrik"| IK_TARGET["target"]
    end
  end

  %% ─── 3D RENDERING ───────────────────────────────────────────────
  subgraph R3D["🎲 render3d/ — 3D Rendering"]
    R3D_MESH["Mesh3D{verts,faces,edges}"] -->|"transform(mat4)"| R3D_MESH
    R3D_MESH -->|"render_wireframe/render_solid"| CORE_CANVAS
    R3D_LOAD["load_obj / load_ply"] --> R3D_MESH
    R3D_RAYTR["Raytracer{RayScene,Sphere,Plane,Box,Cylinder,TexturedQuad}"] -->|"render"| CORE_HIRES
    R3D_SDF["SDFScene{sd_sphere,sd_box,sd_torus,op_union,...}"] -->|"ray march →"| CORE_CANVAS
    R3D_VOXEL["VoxelScene"] -->|"heightmap → 3D"| CORE_CANVAS
    R3D_ISO["IsoMap + IsoTile + IsoCamera"] -->|"isometric →"| CORE_CANVAS

    R3D_CAM["Camera3D (fov in DEGREES, aspect from the surface)"]
    R3D_SCENE["Scene3D (retained)"] -->|"Entity3D + Light3D + Material"| R3D_ENT["DrawCall per visible entity"]
    R3D_CAM -->|"view + projection, rebuilt per surface"| R3D_ENT
    R3D_ENT -->|"Renderer.draw(call)"| R3D_MESHR["MeshRenderer"]
    R3D_ENT -->|"Renderer.draw(call)"| R3D_FUNCR["FuncRenderer (callback)"]
    R3D_MESHR -->|"world-transform, then render_mesh_solid(shade=…)"| R3D_MESH
    R3D_SCENE -.->|"to_dict / save / load — JSON"| R3D_JSON[("scene.json")]
  end

  %% ─── PHYSICS 2D ────────────────────────────────────────────────
  subgraph PHYS2D["⚙️ sim/ — 2D Physics"]
    PHYS_WORLD["PhysicsWorld"] --> PHYS_BODY["Body{pos,vel,mass,radius}"]
    PHYS_WORLD --> PHYS_SPRING["Spring"]
    PHYS_WORLD --> PHYS_JOINT["DistanceJoint"]
    PHYS_WORLD --> PHYS_FORCE["ForceField"]
    PHYS_WORLD --> PHYS_RAY["RayCast"]
    PHYS_BODY -->|"SAT collide"| PHYS_RESOLVE["resolve_aabb / resolve_poly_poly"]
    PHYS_BODY -->|"impulse"| PHYS_RESOLVE
    PHYS_RB["RigidBody / PolyBody / CompoundBody"] --> PHYS_BODY
    PHYS_ENH["EnhancedPhysicsWorld"] --> PHYS_RESOLVE
  end

  %% ─── PHYSICS 3D ────────────────────────────────────────────────
  subgraph PHYS3D["📦 sim/ — 3D Physics"]
    PHYS3D_WORLD["PhysicsWorld3D"] --> PHYS3D_BODY["Body3D / BoxBody3D"]
    PHYS3D_WORLD --> PHYS3D_SPRING["Spring3D"]
  end

  %% ─── SOFT BODY ──────────────────────────────────────────────────
  subgraph SB["🫧 sim/ — Soft Body"]
    SB_WORLD["SoftBodyWorld"] --> SB_BODY["SoftBody{nodes,links,pressures}"]
    SB_BODY -->|"pressure_k / damping / gravity"| SB_WORLD
  end

  %% ─── STEERING ───────────────────────────────────────────────────
  subgraph STEER["🧭 sim/ — Steering Behaviors"]
    STEER_WORLD["SteerWorld"] --> STEER_AGENT["SteerAgent"]
    STEER_AGENT -->|"seek / flee / arrive / pursue / evade / wander"| STEER_TARGET["target"]
    STEER_AGENT -->|"flock: separation+alignment+cohesion"| STEER_GROUP["neighbors"]
  end

  %% ─── FLUID SIM ──────────────────────────────────────────────────
  subgraph FLUID["🌊 sim/ — Fluid Simulation"]
    FLUID_SIM["FluidSim{ Navier-Stokes }"] -->|"diffuse → project → advect"| FLUID_STEP["step()"]
    FLUID_SIM -->|"add_dye / add_velocity"| FLUID_STEP
    FLUID_STEP -->|"render→"| CORE_CANVAS
    WAVE_SIM["WaveSim"] -->|"render"| CORE_CANVAS
  end

  %% ─── PARTICLES ──────────────────────────────────────────────────
  subgraph PARTICLES["✨ fx/ — Particle System"]
    FX_PSYS["ParticleSystem{500}"] --> FX_BURST["Burst"]
    FX_BURST --> FX_PARTICLE["Particle{x,y,vx,vy,life,color}"]
    FX_EMITTER["Emitter"] --> FX_BURST
    FX_FOUNT["FountainEmitter"] --> FX_EMITTER
    FX_STREAM["StreamEmitter"] --> FX_EMITTER
    FX_FIREEM["FireEmitter"] --> FX_EMITTER
    FX_PSYS -->|"burst_explosion / burst_ring / burst_directional"| FX_BURST
    FX_PARTICLE -->|"render"| CORE_CANVAS
  end

  %% ─── CELLULAR AUTOMATA ──────────────────────────────────────────
  subgraph CA["🧬 sim/ — Cellular Automata"]
    CA_GOL["GameOfLife"] -->|"step → render"| CORE_CANVAS
    CA_1D["Automata1D"] -->|"step → render"| CORE_CANVAS
    CA_WW["WireWorld"] -->|"step → render"| CORE_CANVAS
    CA_ANT["LangtonsAnt"] -->|"step → render"| CORE_CANVAS
    CA_RD["ReactionDiffusion"] -->|"step → render"| CORE_CANVAS
  end

  %% ─── PROCEDURAL GENERATION ──────────────────────────────────────
  subgraph GEN["🏔️ gen/ — Procedural Generation"]
    GEN_TERR["Terrain{heightmap,Perlin fbm}"] -->|"render"| CORE_CANVAS
    GEN_MAZE["Maze{DFS,Prim's}"] -->|"render"| CORE_CANVAS
    GEN_LSYS["LSystem{axiom,rules}"] -->|"render"| CORE_CANVAS
    GEN_DUNGEON["DungeonGen{BSP rooms+corridors}"] -->|"render"| CORE_CANVAS
    GEN_WFC["WFC{WaveFunctionCollapse}"] -->|"render"| CORE_CANVAS
    GEN_EROSION["ErosionSim{hydraulic}"] -->|"erode heightmap"| GEN_TERR
    GEN_FRACTAL["Mandelbrot / BurningShip / Newton / BarnsleyFern"] -->|"render"| CORE_CANVAS
    GEN_BIOME["BiomeMap{BIOMES}"] -->|"render"| CORE_CANVAS
    GEN_SCENERY["ParallaxScenery{Cloud,Mountain,Tree,DayNight}"] -->|"render"| CORE_CANVAS
    GEN_SPLINE["quadratic/cubic_bezier / catmull_rom"] -->|"render"| CORE_CANVAS
    GEN_MC["marching_cubes"] -->|"3D mesh"| R3D_MESH
    GEN_DELAUNAY["Delaunay{triangulation}"] -->|"render"| CORE_CANVAS
    GEN_ASTAR["AStar{pathfinding}"] -->|"solve"| GEN_MAZE
  end

  %% ─── NOISE ──────────────────────────────────────────────────────
  subgraph NOISE["📊 sim/ — Noise Functions"]
    NOISE_PERLIN["PerlinNoise"] -->|"fbm2 / noise2"| GEN_TERR
    NOISE_PERLIN -->|"fbm2"| GEN_EROSION
    NOISE_WORLEY["WorleyNoise"] -->|"cellular"| CORE_CANVAS
    NOISE_OPENSIMPLEX["OpenSimplexNoise"] -->|"noise"| CORE_CANVAS
    NOISE_VALUE["ValueNoise"] --> CORE_CANVAS
  end

  %% ─── POWDER SIM ─────────────────────────────────────────────────
  subgraph POWDER["🧪 sim/ — Powder Simulation"]
    PWD_SIM["PowderSim"] -->|"12 materials"| PWD_MAT["Sand/Water/Stone/Wood/Fire/Smoke/Oil/Lava/Acid/Plant/Salt/Steam"]
    PWD_MAT -->|"Liquids/Gases/Solids/Flammable/Meltable"| PWD_RULES["physics rules"]
    PWD_SIM -->|"step → render"| CORE_CANVAS
  end

  %% ─── VISUAL EFFECTS ─────────────────────────────────────────────
  subgraph FX_VFX["🔥 fx/ — Visual Effects"]
    FX_PLASMA["plasma"] -->|"render"| CORE_CANVAS
    FX_FIRE["fire"] -->|"render"| CORE_CANVAS
    FX_STAR["starfield"] -->|"render"| CORE_CANVAS
    FX_MATRIX["matrix_rain"] -->|"render"| CORE_CANVAS
    FX_LIGHT["LightManager{cast_ray,shadows}"] -->|"render"| CORE_CANVAS
    FX_FIELD["VectorField{FieldSource vortex/sink/swirl}"] -->|"advect particles"| FX_FPS["FieldParticle"]
    FX_FPS -->|"render"| CORE_CANVAS
  end

  %% ─── ARRAY IMAGING (whole-frame, pre-fold) ─────────────────────
  subgraph IMGOPS["🖼️ fx/imgops.py — Array Imaging (grade before the fold)"]
    IO_FIELD["Field (scalar per cell)"]
    IO_IMAGE["Image (float RGB)"]
    IO_FIELD -->|"luma / threshold / dilate / blurred"| IO_IMAGE
    IO_IMAGE -->|"tonemapped, bloomed, vignetted, kuwahara, posterized"| IO_IMAGE
    IO_IMAGE -->|"add, over, mix, absorb, scaled, stacked"| IO_IMAGE
    IO_GEN["Field.fbm / fbm_line / plasma / radial / gauss / waves<br/>Image.gradient / zeros / full"] --> IO_FIELD
    IO_STARS["StarField (retained, size-independent)"] -->|"draw / draw_cells"| IO_IMAGE
    IO_IMAGE -->|"to_cells(cache=CellCache) — the ONLY quantisation"| CORE_CANVAS
    IO_IMAGE -->|"to_cells"| CORE_HIRES
  end

  %% ─── POST-PROCESSING ────────────────────────────────────────────
  subgraph POSTFX["🎨 fx/ — Post-Processing"]
    PFX_BLUR["box_blur"] --> CORE_CANVAS
    PFX_GLOW["glow"] --> CORE_CANVAS
    PFX_EDGE["edge_detect"] --> CORE_CANVAS
    PFX_DITHER["dither"] --> CORE_CANVAS
    PFX_SCAN["scanlines"] --> CORE_CANVAS
    PFX_VIGN["vignette"] --> CORE_CANVAS
    PFX_CHROMA["chromatic_aberration"] --> CORE_CANVAS
    PFX_PIX["pixelate"] --> CORE_CANVAS
    PFX_PAL["palette_remap"] --> CORE_CANVAS
  end

  %% ─── SHADERS ────────────────────────────────────────────────────
  subgraph SHADERS["🎛️ fx/ — Shader Pipeline (16 shaders)"]
    SHADER_BASE["Shader"] --> SHADER_PIPE["ShaderPipeline{add,remove,apply}"]
    SHADER_WAVE["WaveDistort"] --> SHADER_BASE
    SHADER_SWIRL["SwirlDistort"] --> SHADER_BASE
    SHADER_KUW["KuwaharaFilter"] --> SHADER_BASE
    SHADER_POSTER["Posterize"] --> SHADER_BASE
    SHADER_SOLAR["Solarize"] --> SHADER_BASE
    SHADER_CEL["CelShade"] --> SHADER_BASE
    SHADER_HEAT["HeatHaze"] --> SHADER_BASE
    SHADER_EMBOSS["Emboss"] --> SHADER_BASE
    SHADER_PSORT["PixelSort"] --> SHADER_BASE
    SHADER_CRYSTAL["Crystallize"] --> SHADER_BASE
    SHADER_ASCII["ASCIIRemap"] --> SHADER_BASE
    SHADER_CHAN["ChannelShift"] --> SHADER_BASE
    SHADER_KALEID["Kaleidoscope"] --> SHADER_BASE
    SHADER_WARP["Warp"] --> SHADER_BASE
    SHADER_VHS["VHSGlitch"] --> SHADER_BASE
    SHADER_RIPPLE["Ripple"] --> SHADER_BASE
    SHADER_PIPE -->|"per-frame apply"| CORE_CANVAS
  end

  %% ─── SCREEN/TEXT EFFECTS ────────────────────────────────────────
  subgraph SCREENFX["🖥️ fx/ — Screen & Text Effects"]
    SFX_CLASS["ScreenFX{add_shake,add_flash,add_fade}"] -->|"tick(dt) → apply(canvas)"| CORE_CANVAS
    SFX_SHAKE["shake"] --> CORE_CANVAS
    SFX_FLASH["flash"] --> CORE_CANVAS
    SFX_FADE["fade_overlay"] --> CORE_CANVAS
    SFX_CROSS["crossfade"] --> CORE_CANVAS
    SFX_COLOR["color_overlay"] --> CORE_CANVAS
    SFX_VIGN["vignette"] --> CORE_CANVAS
    SFX_SCAN["scanlines"] --> CORE_CANVAS
    TFX_GLITCH["glitch_text"] --> CORE_CANVAS
    TFX_TYPE["typewriter_text"] --> CORE_CANVAS
    TFX_SINE["sine_text"] --> CORE_CANVAS
    TFX_RAINBOW["rainbow_text"] --> CORE_CANVAS
    TFX_GRAD["gradient_text"] --> CORE_CANVAS
    TFX_SCROLL["scroll_text"] --> CORE_CANVAS
    TFX_CRAWL["star_wars_crawl"] --> CORE_CANVAS
    TFX_WAVE["wave_text"] --> CORE_CANVAS
    TFX_FIRE["fire_text"] --> CORE_CANVAS
    TFX_MATRIX["matrix_code_rain"] --> CORE_CANVAS
    TFX_BOUNCE["bounce_text"] --> CORE_CANVAS
    TFX_ZOOM["zoom_text"] --> CORE_CANVAS
  end

  %% ─── TRANSITIONS ────────────────────────────────────────────────
  subgraph TRANS["🔄 fx/ — Scene Transitions"]
    TR_FADE["Fade"] -->|"apply(dst,src,t)"| CORE_CANVAS
    TR_WIPE["Wipe{left,right,up,down}"] -->|"apply"| CORE_CANVAS
    TR_SLIDE["Slide"] -->|"apply"| CORE_CANVAS
    TR_CB["Checkerboard"] -->|"apply"| CORE_CANVAS
    TR_PD["PixelDissolve"] -->|"apply"| CORE_CANVAS
  end

  %% ─── VOLUMETRIC ─────────────────────────────────────────────────
  subgraph VOL["🌫️ fx/ — Volumetric"]
    VOL_FOG["VolumetricFog{density grid}"] -->|"apply"| CORE_CANVAS
    VOL_CONE["LightCone"] -->|"apply"| CORE_CANVAS
    VOL_PLUME["SmokePlume"] -->|"apply"| CORE_CANVAS
    VOL_RENDER["VolumetricRenderer"] -->|"render"| CORE_CANVAS
  end

  %% ─── UI TOOLKIT ─────────────────────────────────────────────────
  subgraph UI["🖌️ ui/ — Terminal GUI Toolkit"]
    UI_TK["TerminalApp"] --> UI_WM["WidgetManager"]
    UI_WM --> UI_BTN["Button"]
    UI_WM --> UI_LBL["Label"]
    UI_WM --> UI_SLIDER["Slider"]
    UI_WM --> UI_INPUT["TextField"]
    UI_WM --> UI_TEXTBOX["TextBox"]
    UI_WM --> UI_PROG["ProgressBar"]
    UI_WM --> UI_MENU["Menu"]
    UI_WM --> UI_FRAME["Frame"]
    UI_WM --> UI_CB["Checkbox"]
    UI_WM --> UI_RADIO["RadioGroup"]
    UI_WM --> UI_TAB["TabBar"]
    UI_WM --> UI_TABLE["Table"]
    UI_WM --> UI_TOGGLE["Toggle"]
    UI_WM --> UI_DIV["Divider"]
    UI_WM --> UI_STAT["StatusBar"]
    UI_TK --> UI_FORM["Form"]
    UI_TK --> UI_DIALOG["Dialog"]
    UI_WM -->|"render all →"| CORE_CANVAS
  end

  %% ─── TileMap ────────────────────────────────────────────────────
  subgraph TILEMAP["🗺️ ui/ — TileMap + TileCamera"]
    TM_TILE["TileMap{tiles,collision}"] -->|"render / render_with_camera"| CORE_CANVAS
    TM_CAM["TileCamera"] --> TM_TILE
    TM_PLAT["generate_platformer"] --> TM_TILE
    TM_CAVE["generate_cave"] --> TM_TILE
    TM_TILE --- TM_COL["tile_collide / is_solid"]
  end

  %% ─── FONT ───────────────────────────────────────────────────────
  subgraph FONT["🔤 ui/ — Bitmap Font"]
    FONT_ENG["Font{bitmap_data}"] -->|"render_text / render_text_gradient"| CORE_CANVAS
  end

  %% ─── MEDIA I/O ──────────────────────────────────────────────────
  subgraph MEDIA["📺 media/ — Media I/O"]
    MEDIA_IMG["ImageConverter{image_to_canvas}"] -->|"PIL/ffmpeg → ASCII"| CORE_CANVAS
    MEDIA_VID["Video{VideoFrame,FramePlayer}"] -->|"play"| CORE_CANVAS
    MEDIA_CONV["converter{image/video → ASCII}"] --> MEDIA_IMG
    MEDIA_CONV --> MEDIA_VID
    MEDIA_CONV -->|"ScreenRecorder"| MEDIA_REC["record frames"]
    MEDIA_GLYPH["glyphart{image/video → text}"] -->|"plain text"| MEDIA_OUT["pasteable ASCII"]
    MEDIA_ANSI["ansi_io{parse,export,save,load}"] -->|"ANSI file I/O"| CORE_CANVAS
    MEDIA_ANSI -->|"canvas_to_block_art"| MEDIA_OUT
  end

  %% ─── OUTPUT ─────────────────────────────────────────────────────
  subgraph OUT["🖨️ Output"]
    OUTPUT -->|"\\033[H + batched cursor moves + changed cells + \\033[0m"| TERM["Terminal (stdout)"]
    MEDIA_REC --> SCREEN_REC["Screen Recording (frames)"]
  end
```
