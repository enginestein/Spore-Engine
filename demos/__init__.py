KEY_PRESSED = None

from .scene_new_features2 import (scene_wfc, scene_astar, scene_physics3d,
    scene_obj_loader, scene_sdf, scene_ansi_io, scene_softbody, scene_delaunay,
    scene_steering, scene_marching_cubes, scene_volumetric, scene_ik)

from .scene_3d import scene_3d_objects, scene_donut, scene_raycaster, scene_raytracer
from .scene_fx import scene_fire_plasma, scene_fireworks, scene_matrix, scene_starfield, scene_audio
from .scene_fractals import scene_mandelbrot, scene_reaction_diffusion, scene_lsystem, scene_julia
from .scene_sim import scene_fluid, scene_physics, scene_terrain, scene_waves
from .scene_cellular import scene_game_of_life, scene_automata_1d, scene_wireworld, scene_langton
from .scene_misc import scene_textfx, scene_maze, scene_weather, scene_postfx
from .scene_landscape import scene_landscape
from .scene_anim import scene_anim
from .scene_tilemap import scene_tilemap
from .scene_screenfx import scene_screenfx
from .scene_ui import scene_ui
from .scene_scenery import scene_scenery
from .scene_shadows import scene_shadows
from .scene_physics_enhanced import scene_physics_enhanced
from .scene_particles import scene_particles
from .scene_anim_path import scene_anim_path
from .scene_new_features import scene_title, scene_voxel_landscape, scene_burning_ship, scene_newton, scene_barnsley_fern
from .scene_tui import scene_tui_demo
from .scene_aurora import scene_aurora
from .scene_kaleidoscope import scene_kaleidoscope
from .scene_gravity import scene_gravity
from .scene_tunnel import scene_tunnel
from .scene_galaxy import scene_galaxy
from .scene_underwater import scene_underwater
from .scene_lava import scene_lava
from .scene_lightning import scene_lightning
from .scene_dna import scene_dna
from .scene_meteor import scene_meteor
from .scene_ripples import scene_ripples
from .scene_forest_fire import scene_forest_fire
from .scene_neon_grid import scene_neon_grid
from .scene_bioluminescence import scene_bioluminescence
from .scene_solar_flare import scene_solar_flare
from .scene_stained_glass import scene_stained_glass
from .scene_astral_cathedral import scene_astral_cathedral
from .scene_golden_city import scene_golden_city
from .scene_phantom_galaxy import scene_phantom_galaxy
from .scene_aurora_palace import scene_aurora_palace
from .scene_phoenix import scene_phoenix
from .scene_celestial_temple import scene_celestial_temple
from .scene_black_hole import scene_black_hole
from .scene_aurora_storm import scene_aurora_storm
from .scene_crystal_nebula import scene_crystal_nebula
from .scene_infinite_temple import scene_infinite_temple
from .scene_lorenz import scene_lorenz
from .scene_double_pendulum import scene_double_pendulum
from .scene_flocking import scene_flocking
from .scene_flowfield import scene_flowfield
from .scene_worley import scene_worley
from .scene_field_demo import scene_field_demo
from .scene_spline_demo import scene_spline_demo
from .scene_biome_demo import scene_biome_demo
from .scene_isometric import scene_isometric
from .scene_shaders import scene_shaders
from .scene_powder import scene_powder
from .scene_timeline import scene_timeline
from .scene_video_player import scene_video_player
from .scene_erosion import scene_erosion
from .scene_physics_rigid import scene_physics_rigid
from .scene_dungeon import scene_dungeon
from .scene_terminal_app import scene_terminal_app
from .scene_media_player import scene_media_player
from .scene_glyph_art import scene_glyph_art
from .scene_horizon import scene_horizon
from .scene_sdf_csg import scene_sdf_csg
from .scene_raytracer_reflections import scene_raytracer_reflections
from .scene_voxel_world import scene_voxel_world
from .scene_sdf_glow import scene_sdf_glow
from .scene_starry_night import scene_starry_night
from .scene_terrain_flyover import scene_terrain_flyover
from .scene_raytracer_infinity import scene_raytracer_infinity
from .scene_raytracer_nebula import scene_raytracer_nebula
from .scene_raytracer_crystal import scene_raytracer_crystal
from .scene_raytracer_system import scene_raytracer_system
from .scene_raytracer_jewel import scene_raytracer_jewel
from .scene_raytracer_moonlit import scene_raytracer_moonlit
from .scene_raytracer_toybox import scene_raytracer_toybox
from .scene_raytracer_alien import scene_raytracer_alien
from .scene_raytracer_photo import scene_raytracer_photo
from .scene_photo_ascii import scene_photo_ascii
from .scene_walkers import scene_walkers
from .scene_ragdoll import scene_ragdoll

# Beautiful new demos
from .scene_sdf_dreamscape import scene_sdf_dreamscape
from .scene_prism_raytracer import scene_prism_raytracer
from .scene_neon_cathedral import scene_neon_cathedral
from .scene_cosmic_tunnel import scene_cosmic_tunnel
from .scene_shader_symphony import scene_shader_symphony
from .scene_ethereal_ruins import scene_ethereal_ruins
from .scene_god_rays import scene_god_rays


# Latest demos
from .scene_crystal_cluster import scene_crystal_cluster
from .scene_synthwave import scene_synthwave
from .scene_fireflies import scene_fireflies
from .scene_constellation import scene_constellation
from .scene_platformer import scene_platformer

# Newest demos
from .scene_hypercube import scene_hypercube
from .scene_eclipse import scene_eclipse
from .scene_neon_city import scene_neon_city
from .scene_geometric_flower import scene_geometric_flower
from .scene_sierpinski import scene_sierpinski
from .scene_aurora_lagoon import scene_aurora_lagoon


SCENES = [
    ("Title Screen", scene_title),
    ("Horizon Sunset", scene_horizon),
    ("3D Objects", scene_3d_objects),
    ("3D Donut", scene_donut),
    ("Fire+Plasma", scene_fire_plasma),
    ("Fireworks", scene_fireworks),
    ("Matrix Rain", scene_matrix),
    ("Mandelbrot", scene_mandelbrot),
    ("Raycaster", scene_raycaster),
    ("Reaction-Diffusion", scene_reaction_diffusion),
    ("Game of Life", scene_game_of_life),
    ("Fluid Sim", scene_fluid),
    ("L-System", scene_lsystem),
    ("Physics", scene_physics),
    ("Terrain", scene_terrain),
    ("Raytracer", scene_raytracer),
    ("Text FX", scene_textfx),
    ("Maze", scene_maze),
    ("Waves", scene_waves),
    ("1D Cellular", scene_automata_1d),
    ("Weather", scene_weather),
    ("Starfield", scene_starfield),
    ("Audio Viz", scene_audio),
    ("Julia Sets", scene_julia),
    ("PostFX", scene_postfx),
    ("WireWorld", scene_wireworld),
    ("Langton's Ant", scene_langton),
    ("Landscape", scene_landscape),
    ("Animation", scene_anim),
    ("Tilemap", scene_tilemap),
    ("Screen FX", scene_screenfx),
    ("UI Widgets", scene_ui),
    ("Scenery", scene_scenery),
    ("Shadows", scene_shadows),
    ("Enhanced Physics", scene_physics_enhanced),
    ("Particle FX", scene_particles),
    ("Anim Path", scene_anim_path),
    ("Voxel Landscape", scene_voxel_landscape),
    ("Burning Ship", scene_burning_ship),
    ("Newton Fractal", scene_newton),
    ("Barnsley Fern", scene_barnsley_fern),
    ("TUI Toolkit", scene_tui_demo),
    ("Aurora Borealis", scene_aurora),
    ("Kaleidoscope", scene_kaleidoscope),
    ("Gravity Sim", scene_gravity),
    ("Warp Tunnel", scene_tunnel),
    ("Spiral Galaxy", scene_galaxy),
    ("Underwater World", scene_underwater),
    ("Lava Lamp", scene_lava),
    ("Lightning Storm", scene_lightning),
    ("DNA Helix", scene_dna),
    ("Meteor Shower", scene_meteor),
    ("Water Ripples", scene_ripples),
    ("Forest Fire", scene_forest_fire),
    ("Neon Grid", scene_neon_grid),
    ("Bioluminescence", scene_bioluminescence),
    ("Solar Flares", scene_solar_flare),
    ("Stained Glass", scene_stained_glass),
    ("Astral Cathedral", scene_astral_cathedral),
    ("Golden Hour City", scene_golden_city),
    ("Phantom Galaxy", scene_phantom_galaxy),
    ("Aurora Palace", scene_aurora_palace),
    ("Phoenix", scene_phoenix),
    ("Celestial Temple", scene_celestial_temple),
    ("Black Hole", scene_black_hole),
    ("Aurora Storm", scene_aurora_storm),
    ("Crystal Nebula", scene_crystal_nebula),
    ("Infinite Temple", scene_infinite_temple),
    ("Lorenz Attractor", scene_lorenz),
    ("Double Pendulum", scene_double_pendulum),
    ("Boids Flocking", scene_flocking),
    ("Flow Field", scene_flowfield),
    ("Advanced Noise", scene_worley),
    ("Particle Field", scene_field_demo),
    ("Spline Renderer", scene_spline_demo),
    ("Biome Terrain", scene_biome_demo),
    ("Isometric", scene_isometric),
    ("Modular Shaders", scene_shaders),
    ("Powder Toy", scene_powder),
    ("Timeline Animation", scene_timeline),
    ("Video Player", scene_video_player),
    ("Hydraulic Erosion", scene_erosion),
    ("Rigid Body Physics", scene_physics_rigid),
    ("Dungeon/World Gen", scene_dungeon),
    ("Native Terminal GUI", scene_terminal_app),
    ("Media Player", scene_media_player),
    ("Glyph Art", scene_glyph_art),
    ("Wave Function Collapse", scene_wfc),
    ("A* Pathfinding", scene_astar),
    ("3D Physics", scene_physics3d),
    ("OBJ/PLY Loader", scene_obj_loader),
    ("SDF Ray Marching", scene_sdf),
    ("ANSI Art I/O", scene_ansi_io),
    ("Soft Body Physics", scene_softbody),
    ("Delaunay/Voronoi", scene_delaunay),
    ("Steering Behaviors", scene_steering),
    ("Marching Cubes 3D", scene_marching_cubes),
    ("Volumetric Effects", scene_volumetric),
    ("Inverse Kinematics", scene_ik),
    ("Infinite SDF Gallery", scene_sdf_csg),
    ("Hall of Mirrors", scene_raytracer_reflections),
    ("Voxel World", scene_voxel_world),
    ("Glowing SDF World", scene_sdf_glow),
    ("Starry Night", scene_starry_night),
    ("Canyon Flyover", scene_terrain_flyover),
    ("Infinity Room", scene_raytracer_infinity),
    ("Neon Nebula", scene_raytracer_nebula),
    ("Crystal Cave", scene_raytracer_crystal),
    ("Solar System", scene_raytracer_system),
    ("Jewel Box", scene_raytracer_jewel),
    ("Moonlit", scene_raytracer_moonlit),
    ("Toy Box", scene_raytracer_toybox),
    ("Alien Grove", scene_raytracer_alien),
    ("Photo Billboard", scene_raytracer_photo),
    ("Photo ASCII", scene_photo_ascii),
    ("Pixel Walkers", scene_walkers),
    ("Ragdoll", scene_ragdoll),
    # --------------- Beautiful New Demos ---------------
    ("SDF Dreamscape", scene_sdf_dreamscape),
    ("Prism Raytracer", scene_prism_raytracer),
    ("Neon Cathedral", scene_neon_cathedral),
    ("Cosmic Tunnel", scene_cosmic_tunnel),
    ("Shader Symphony", scene_shader_symphony),
    ("Ethereal Ruins", scene_ethereal_ruins),
    # --- God Rays ---
    ("God Rays", scene_god_rays),
    # --------------- Latest Demos ---------------
    ("Crystal Cluster", scene_crystal_cluster),
    ("Synthwave", scene_synthwave),
    ("Firefly Meadow", scene_fireflies),
    ("Constellation", scene_constellation),
    ("Moon Platformer", scene_platformer),
    # --------------- Newest Demos ---------------
    ("Hypercube", scene_hypercube),
    ("Solar Eclipse", scene_eclipse),
    ("Neon City", scene_neon_city),
    ("Geometric Flower", scene_geometric_flower),
    ("Sierpinski", scene_sierpinski),
    # --------------- Flagship ---------------
    ("Aurora Lagoon", scene_aurora_lagoon),
]
