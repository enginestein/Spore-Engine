"""Spore Engine - terminal art / animation / UI toolkit.

Namespace policy
----------------
The top-level ``spore_engine`` namespace is the single, canonical home for
each public name. Exactly one true version of every name exists across the
whole package - names never mean different things in different subpackages,
and nothing is "re-exported over" a shadowing import.

Historically three subpackage types collided with core types; those were
renamed instead of overridden at the top level::

    spore_engine.render3d.Scene     -> RayScene     (ray-tracer scene)
    spore_engine.ui.widgets.Input   -> TextField    (text-input widget)
    spore_engine.ui.tilemap.Camera  -> TileCamera   (tile-map camera)

The easy layer has its own lightweight types that must not shadow the core
or ui ones, so they keep distinct package-unique names::

    spore_engine.easy.Sprite                -> GameSprite (animated game sprite)
    spore_engine.easy.Button/Label/Dialog   -> SimpleButton/SimpleLabel/SimpleDialog

Math helpers that appear in more than one layer are single objects imported
from ``core.util`` - ``clamp``, ``smoothstep``, ``lerp`` and ``lerp_color``
are the same function everywhere (``anim`` and ``easy`` re-export the core
objects; they do not define their own). So ``Input``, ``Camera`` and
``Scene`` mean only their core types::

    spore_engine.Input  -> core keyboard  (spore_engine.core.Input)
    spore_engine.Camera -> core viewport  (spore_engine.core.Camera)
    spore_engine.Scene  -> core container (spore_engine.core.Scene)

No two subpackages export the same identifier with different meanings;
``tests/test_api.py`` asserts this invariant.
"""

from spore_engine.core import (Color, Gradient, PALETTES, fast_color,
    BLACK, RED, GREEN, BLUE, YELLOW, CYAN, MAGENTA, WHITE,
    ORANGE, PURPLE, PINK, DIM,
    Vec2, Vec3, Mat4,
    Canvas, HiResCanvas, Cell,
    Sprite,
    SceneState, scene_state, clear_scene_states, list_scene_states,
    Scene, Layer,
    Camera,
    Input, KeyState, open_input, KeyEvent, MouseEvent, ResizeEvent,
    KEY_UP, KEY_DOWN, KEY_LEFT, KEY_RIGHT, KEY_ENTER,
    KEY_SPACE, KEY_ESCAPE, KEY_TAB, KEY_SHIFT_TAB,
    KEY_BACKSPACE, KEY_DELETE, KEY_INSERT, KEY_HOME,
    KEY_END, KEY_PAGE_UP, KEY_PAGE_DOWN, KEY_CTRL_C,
    KEY_CTRL_D, KEY_CTRL_Z,
    clamp, lerp, ir, ramp, phase, wave, osc, in_bounds,
    approach, move_toward, bounce, dist, lerp_color,
    smoothstep, ramp_color)

from spore_engine.core import (Assets, assets, default_store, load_sprite, load_palette,
     load_model, load_text,
     Component, EcsEntity, World, System, Transform,
     SpriteComponent, SpriteRenderSystem)

from spore_engine.fx import (plasma, fire, starfield, matrix_rain,
    ParticleSystem, Burst, Emitter,
    FountainEmitter, StreamEmitter, FireEmitter,
    Particle, burst_explosion, burst_ring, burst_directional,
    box_blur, glow, edge_detect, dither, scanlines, vignette,
    chromatic_aberration, pixelate, palette_remap,
    shake, fade_overlay, flash, crossfade, color_overlay, ScreenFX,
    glitch_text, typewriter_text, sine_text, rainbow_text,
    gradient_text, scroll_text, star_wars_crawl, wave_text,
    fire_text, matrix_code_rain, bounce_text, zoom_text,
    Ray2D, Light, LightManager, cast_ray, cast_ray_dda,
    visibility_polygon, render_shadows,
    Fade, Wipe, Slide, Checkerboard, PixelDissolve,
    FieldSource, VectorField, FieldParticle, FieldSystem,
    Shader, ShaderPipeline,
    WaveDistort, SwirlDistort, KuwaharaFilter,
    Posterize, Solarize, CelShade, HeatHaze, Emboss,
    PixelSort, Crystallize, ASCIIRemap, ChannelShift,
    Kaleidoscope, Warp, VHSGlitch, Ripple,
    Field, Image, StarField, CellCache, to_cells)

from spore_engine.render3d import (Mesh3D, Camera3D,
    DrawCall, Entity3D, FuncRenderer, Light3D, Material, MeshRenderer,
    Renderer, Scene3D,
    render_mesh_wireframe, render_mesh_solid,
    RayScene, Sphere, Plane,
    VoxelScene,
    IsoTile, IsoCamera, IsoMap)

from spore_engine.sim import (PhysicsWorld, Body, Spring,
    AABB, RectBody, RayCast, ForceField, DistanceJoint,
    resolve_aabb,
    FluidSim, WaveSim,
    GameOfLife, Automata1D, WireWorld, LangtonsAnt,
    ReactionDiffusion, PATTERNS, GRAY_SCOTT_PARAMS,
    PerlinNoise, ValueNoise, WorleyNoise, OpenSimplexNoise,
    PowderSim, MATERIAL_NAMES, MATERIAL_COLORS, EMPTY, SAND,
    WATER, STONE, WOOD, FIRE, SMOKE, OIL, LAVA, ACID, PLANT, SALT, STEAM,
    RigidBody, PolyBody, CompoundBody, EnhancedPhysicsWorld,
    sat_collide, resolve_poly_poly, resolve_circle_poly,
    resolve_circle_aabb)

from spore_engine.gen import (Mandelbrot, BurningShip,
    NewtonFractal, BarnsleyFern,
    LSystem, LSYSTEMS,
    Maze,
    Terrain, marching_squares,
    ParallaxLayer, ParallaxScenery, CloudLayer, Cloud,
    MountainProfile, DayNightCycle, WaterSurface, Tree,
    render_sky, render_stars, render_moon,
    quadratic_bezier, cubic_bezier, catmull_rom, lerp_point,
    render_bezier, render_catmull_rom,
    BIOMES, get_biome, BiomeMap,
    ErosionSim,
    DungeonGen, Room, RiverGen, WorldGen)

from spore_engine.ui import (Label, TextBox, ProgressBar,
    Button, Menu, Frame, Checkbox, RadioGroup, TabBar,
    Slider, Table, TextField, Toggle, Divider, StatusBar,
    WidgetManager,
    TerminalApp, Form, Dialog,
    Font,
    TileMap, TileCamera, generate_platformer, generate_cave,
    tile_collide, auto_tile_char)

from spore_engine.anim import (Tween, Sequence, Oscillator,
    Ticker, EASING, lerp_tuple,
    Entity, Animator, Path, PathFollower,
    linear, quad_in, quad_out, cubic_in, cubic_out,
    bounce_out, elastic_out, sine_in_out, expo_out,
    Keyframe, Track, Timeline)

from spore_engine.gen import (WFC, WFCTile, AStar, Delaunay, Point, Triangle,
    marching_cubes, make_density_grid)

from spore_engine.render3d import (load_obj, load_ply,
    SDFScene, sd_sphere, sd_box, sd_torus, sd_cylinder, sd_plane,
    op_union, op_subtract, op_intersect, op_smooth_union, op_round, op_repeat)

from spore_engine.sim import (Body3D, BoxBody3D, Spring3D, PhysicsWorld3D,
    SoftBody, SoftBodyWorld, SteerAgent, SteerWorld)

from spore_engine.fx import (VolumetricFog, LightCone, SmokePlume, VolumetricRenderer)

from spore_engine.anim import (Bone, Skeleton, create_arm, create_leg, create_tentacle)

from spore_engine.easy import (App, Anim, map_range, random_color)

from spore_engine.media import (ImageConverter,
    canvas_from_text, scale_canvas, gradient_canvas,
    Video, VideoFrame, FramePlayer,
    make_test_video, make_color_bars, make_spinning_donut_video,
    image_to_canvas, video_to_ascii, video_to_player, ScreenRecorder)

# Terminal lifecycle, scene state and asset error types are part of the
# documented top-level surface: an application that drives the engine itself
# needs a session and a scene store, and callers need to catch asset errors
# without reaching into core.
from spore_engine.core import (TerminalSession, RawMode, SceneStateStore,
                               detect_color_depth, terminal_size, is_tty,
                               monotonic, posix_terminal_available,
                               HAVE_POSIX_TERMIOS, HAVE_TERMIOS,
                               AssetError, AssetNotFoundError,
                               UnsupportedAssetError, AssetParseError)

from spore_engine.__version__ import __version__
