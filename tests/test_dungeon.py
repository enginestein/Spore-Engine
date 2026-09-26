"""Tests for spore_engine.gen.dungeon: rooms, dungeons, rivers and worlds."""
from __future__ import annotations

import itertools
import random

import pytest

from spore_engine import Canvas, Color
from spore_engine.gen.dungeon import (
    DungeonGen, RiverGen, Room, WorldGen, _interior,
)

GENERATORS = [DungeonGen, RiverGen, WorldGen]


# -------------------------------------------------------------------
# Room
# -------------------------------------------------------------------

def test_room_geometry_properties():
    r = Room(10, 20, 6, 4)
    assert (r.x, r.y, r.w, r.h) == (10, 20, 6, 4)
    assert r.cx == 13
    assert r.cy == 22
    assert r.area == 24
    assert r.connected is False
    assert r.type == 'normal'
    assert r.tags == []


def test_room_intersects_uses_a_padding_gap():
    a = Room(0, 0, 10, 10)
    assert a.intersects(Room(5, 5, 10, 10))
    assert not a.intersects(Room(40, 40, 5, 5))
    # pad=0 means touching counts as an overlap
    touching = Room(10, 0, 5, 5)
    assert not a.intersects(touching, pad=0)
    assert not a.intersects(Room(11, 0, 5, 5), pad=1)
    assert a.intersects(Room(10, 0, 5, 5), pad=1)


def test_room_center_dist_is_euclidean():
    a = Room(0, 0, 2, 2)
    b = Room(3, 0, 2, 2)
    assert a.center_dist(b) == pytest.approx(3.0)   # centres are 1 and 4
    assert a.center_dist(a) == 0.0


def test_room_random_point_stays_inside_and_off_the_walls():
    r = Room(10, 10, 8, 6)
    rng = random.Random(7)
    for _ in range(50):
        x, y = r.random_point(rng)
        assert r.x < x < r.x + r.w - 1
        assert r.y < y < r.y + r.h - 1


def test_room_random_point_is_deterministic_for_a_seed():
    a = Room(0, 0, 9, 9).random_point(random.Random(3))
    b = Room(0, 0, 9, 9).random_point(random.Random(3))
    assert a == b


def test_room_repr_mentions_its_size():
    assert repr(Room(1, 2, 3, 4)) == 'Room(1,2 3x4)'


# -------------------------------------------------------------------
# construction guards
# -------------------------------------------------------------------

@pytest.mark.parametrize('cls', GENERATORS)
@pytest.mark.parametrize('w,h', [(0, 0), (0, 5), (5, 0), (-1, 3), (3, -1)])
def test_generators_reject_non_positive_sizes(cls, w, h):
    with pytest.raises(ValueError, match='must be positive'):
        cls(w, h)


def test_interior_clamps_for_tiny_maps():
    assert _interior(random.Random(0), 1, 1) == (0, 0)
    assert _interior(random.Random(0), 2, 2) in {(0, 0), (0, 1), (1, 0), (1, 1)}
    x, y = _interior(random.Random(1), 40, 20)
    assert 0 <= x < 40 and 0 <= y < 20


# -------------------------------------------------------------------
# DungeonGen
# -------------------------------------------------------------------

def test_dungeon_carves_rooms_and_corridors():
    gen = DungeonGen(60, 30, seed=1)
    rooms = gen.generate()
    assert rooms
    assert gen.corridors, 'no corridors were carved'
    assert gen.grid[0][0] == '#', 'the outer wall was carved away'


def test_dungeon_rooms_stay_inside_the_map():
    gen = DungeonGen(50, 25, seed=2)
    rooms = gen.generate()
    for r in rooms:
        assert r.x >= 0 and r.x + r.w <= gen.w
        assert r.y >= 0 and r.y + r.h <= gen.h


def test_dungeon_rooms_do_not_overlap():
    gen = DungeonGen(70, 40, seed=3)
    rooms = gen.generate()
    for i, a in enumerate(rooms):
        for b in rooms[i + 1:]:
            assert not a.intersects(b, pad=1), f'{a} overlaps {b}'


def test_dungeon_room_interiors_are_open():
    gen = DungeonGen(60, 30, seed=4)
    gen.generate()
    for r in gen.rooms:
        assert gen.grid[r.cy][r.cx] != '#', 'the middle of a room is still wall'


def test_dungeon_tags_the_ends_and_marks_specials():
    gen = DungeonGen(80, 40, seed=5)
    gen.generate()
    if len(gen.rooms) >= 2:
        assert gen.rooms[0].type == 'entrance'
        assert gen.rooms[-1].type == 'treasure'
        assert 'entrance' in gen.rooms[0].tags
        assert 'treasure' in gen.rooms[-1].tags
    assert all(r.type in ('normal', 'entrance', 'treasure', 'shop', 'boss')
               for r in gen.rooms)


def test_dungeon_places_a_marker_in_each_special_room():
    gen = DungeonGen(80, 40, seed=6)
    gen.generate()
    marks = {'entrance': '>', 'treasure': '$', 'shop': 'M', 'boss': 'B'}
    for r in gen.rooms:
        if r.type in marks:
            assert gen.grid[r.cy][r.cx] == marks[r.type]


def test_dungeon_is_reproducible_for_a_seed():
    def build():
        gen = DungeonGen(60, 30, seed=11)
        gen.generate()
        return [row[:] for row in gen.grid]
    assert build() == build()


def test_different_seeds_give_different_dungeons():
    def build(seed):
        gen = DungeonGen(60, 30, seed=seed)
        gen.generate()
        return [row[:] for row in gen.grid]
    assert build(1) != build(2)


@pytest.mark.parametrize('w,h', [(1, 1), (4, 4), (8, 8), (9, 9), (12, 12)])
def test_dungeon_handles_small_maps(w, h):
    gen = DungeonGen(w, h, seed=1)
    gen.generate()
    gen.render(Canvas(max(w, 1), max(h, 1)))


def test_dungeon_respects_max_rooms():
    gen = DungeonGen(80, 40, seed=7)
    rooms = gen.generate(max_rooms=3)
    assert len(rooms) <= 3


def test_dungeon_bsp_depth_zero_still_produces_rooms():
    gen = DungeonGen(40, 30, seed=8)
    rooms = gen.generate(bsp_depth=0)
    assert rooms


def test_dungeon_render_clips_to_a_smaller_canvas():
    gen = DungeonGen(40, 30, seed=9)
    gen.generate()
    canvas = Canvas(10, 8)
    gen.render(canvas)          # must not raise


def test_dungeon_render_honours_an_offset():
    gen = DungeonGen(20, 12, seed=10)
    gen.generate()
    canvas = Canvas(30, 20)
    gen.render(canvas, ox=5, oy=4)
    # the offset copy is what got drawn
    assert canvas.buffer[4][5].char != ' '


def test_dungeon_render_draws_walls_and_floors():
    gen = DungeonGen(30, 20, seed=12)
    gen.generate()
    canvas = Canvas(30, 20)
    gen.render(canvas)
    chars = {c.char for row in canvas.buffer for c in row}
    assert '█' in chars, 'no wall was drawn'


def test_dungeon_tag_rooms_on_an_empty_list_is_a_no_op():
    gen = DungeonGen(20, 12)
    gen.rooms = []
    gen._tag_rooms()          # must not raise


# -------------------------------------------------------------------
# RiverGen
# -------------------------------------------------------------------

def hillmap(w, h, base=0.8):
    return [[base for _ in range(w)] for _ in range(h)]


def slope(w, h):
    return [[y / max(1, h - 1) for _ in range(w)] for y in range(h)]


def test_rivers_are_generated_and_traceable():
    gen = RiverGen(40, 20, seed=1)
    paths = gen.generate_rivers(slope(40, 20), num_rivers=3)
    assert paths
    for path in paths:
        assert len(path) > 5, 'a path was kept despite being too short'
        for x, y in path:
            assert 0 <= x < 40 and 0 <= y < 20


def test_river_paths_are_contiguous_enough_to_walk():
    gen = RiverGen(40, 20, seed=2)
    for path in gen.generate_rivers(slope(40, 20), num_rivers=2):
        for (x0, y0), (x1, y1) in itertools.pairwise(path):
            assert max(abs(x1 - x0), abs(y1 - y0)) <= 2, 'the river teleported'


def test_rivers_avoid_revisiting_a_cell():
    gen = RiverGen(40, 20, seed=3)
    for path in gen.generate_rivers(slope(40, 20), num_rivers=2):
        assert len(set(path)) == len(path), 'a river crossed itself'


def test_rivers_are_reproducible_for_a_seed():
    def build():
        g = RiverGen(40, 20, seed=4)
        return g.generate_rivers(slope(40, 20), num_rivers=2)
    assert build() == build()


def test_rivers_on_a_flat_map_do_not_raise():
    gen = RiverGen(20, 10, seed=5)
    gen.generate_rivers(hillmap(20, 10))     # zero gradient everywhere


def test_rivers_stop_at_low_ground():
    """Terrain below the 0.05 threshold ends the trace, so a sea-level map
    yields no rivers rather than wandering forever."""
    gen = RiverGen(20, 10, seed=6)
    assert gen.generate_rivers(hillmap(20, 10, base=0.01), num_rivers=2) == []


def test_river_max_length_is_respected():
    gen = RiverGen(60, 40, seed=7)
    for path in gen.generate_rivers(slope(60, 40), num_rivers=2, max_length=8):
        assert len(path) <= 9


def test_apply_to_lowers_the_terrain_along_the_rivers():
    gen = RiverGen(30, 20, seed=8)
    hm = hillmap(30, 20, base=0.9)
    gen.generate_rivers(hm, num_rivers=2)
    assert gen.paths
    before = [row[:] for row in hm]
    gen.apply_to(hm, depth=0.4, width=2)
    assert any(hm[y][x] < before[y][x]
               for y in range(20) for x in range(30)), 'apply_to changed nothing'


def test_apply_to_never_lowers_below_zero():
    gen = RiverGen(20, 10, seed=9)
    hm = hillmap(20, 10, base=0.05)
    gen.generate_rivers(hm, num_rivers=2)
    gen.apply_to(hm, depth=10.0, width=3)
    assert all(0.0 <= v <= 1.0 for row in hm for v in row)


def test_apply_to_without_paths_is_a_no_op():
    gen = RiverGen(20, 10, seed=10)
    hm = hillmap(20, 10, base=0.9)
    gen.apply_to(hm)
    assert all(v == 0.9 for row in hm for v in row)


def test_river_render_draws_tildes():
    gen = RiverGen(30, 20, seed=11)
    gen.generate_rivers(slope(30, 20), num_rivers=2)
    canvas = Canvas(30, 20)
    gen.render(canvas)
    assert any(c.char == '~' for row in canvas.buffer for c in row)
    for row in canvas.buffer:
        for cell in row:
            if cell.fg is not None:
                assert isinstance(cell.fg, Color)


# -------------------------------------------------------------------
# WorldGen
# -------------------------------------------------------------------

def test_world_generates_terrain_moisture_and_biomes():
    gen = WorldGen(40, 25, seed=1)
    gen.generate()
    assert len(gen.heightmap) == 25
    assert all(len(row) == 40 for row in gen.heightmap)
    assert all(0.0 <= v <= 1.0 for row in gen.heightmap for v in row)
    assert all(0.0 <= v <= 1.0 for row in gen.moisture for v in row)
    assert all(b for row in gen.biome_map for b in row), 'a cell has no biome'


def test_every_biome_has_a_colour_and_a_character():
    assert set(WorldGen.BIOME_COLORS) == set(WorldGen.BIOME_CHARS)
    for col in WorldGen.BIOME_COLORS.values():
        assert all(0 <= c <= 255 for c in (col.r, col.g, col.b))


def test_world_biomes_are_all_known_names():
    gen = WorldGen(60, 40, seed=2)
    gen.generate()
    seen = {b for row in gen.biome_map for b in row}
    assert seen <= set(WorldGen.BIOME_COLORS), f'unknown biomes: {seen}'


def test_world_is_reproducible_for_a_seed():
    def build():
        g = WorldGen(40, 25, seed=3)
        g.generate()
        return ([row[:] for row in g.heightmap],
                [row[:] for row in g.biome_map],
                list(g.settlements), list(g.features), [list(p) for p in g.rivers])
    assert build() == build()


def test_world_settlements_are_spread_out_and_onshore():
    gen = WorldGen(80, 50, seed=4)
    gen.generate(settlements=8)
    for sx, sy, name in gen.settlements:
        assert 0 <= sx < 80 and 0 <= sy < 50
        assert name
    for i, (x0, y0, _) in enumerate(gen.settlements):
        for x1, y1, _ in gen.settlements[i + 1:]:
            assert abs(x0 - x1) >= 5 or abs(y0 - y1) >= 5, 'settlements overlap'


def test_world_features_are_onshore_and_onscreen():
    gen = WorldGen(60, 40, seed=5)
    gen.generate()
    for fx, fy, feat in gen.features:
        assert 0 <= fx < 60 and 0 <= fy < 40
        assert gen.biome_map[fy][fx] not in ('ocean', 'snow', 'mountain')
        assert feat in ('ruins', 'tower', 'shrine', 'grove', 'mine')


def test_world_generate_accepts_tiny_maps():
    for w, h in [(1, 1), (2, 3), (5, 5)]:
        gen = WorldGen(w, h, seed=6)
        gen.generate(settlements=20)
        assert len(gen.biome_map) == h


def test_world_generate_with_no_rivers_or_settlements():
    gen = WorldGen(30, 20, seed=7)
    gen.generate(rivers=0, settlements=0)
    assert gen.rivers == []
    assert gen.settlements == []


def test_world_generate_with_zero_octaves():
    gen = WorldGen(20, 10, seed=8)
    gen.generate(octaves=0)
    assert all(b for row in gen.biome_map for b in row)


def test_river_cells_are_marked_as_river_biome():
    gen = WorldGen(50, 30, seed=9)
    gen.generate(rivers=4)
    if gen.rivers:
        marked = [(x, y) for y in range(30) for x in range(50)
                  if gen.biome_map[y][x] == 'river']
        assert marked, 'rivers were traced but nothing was marked'


def test_world_render_draws_every_cell():
    gen = WorldGen(30, 20, seed=10)
    gen.generate()
    canvas = Canvas(30, 20)
    gen.render(canvas)
    assert all(c.fg is not None for row in canvas.buffer for c in row)


def test_world_render_as_a_shade_map():
    gen = WorldGen(30, 20, seed=11)
    gen.generate()
    canvas = Canvas(30, 20)
    gen.render(canvas, show_biomes=False)
    assert all(c.fg is not None for row in canvas.buffer for c in row)


def test_world_render_can_hide_features():
    gen = WorldGen(40, 30, seed=12)
    gen.generate()
    with_features = Canvas(40, 30)
    without = Canvas(40, 30)
    gen.render(with_features)
    gen.render(without, show_features=False)
    diamond = '♦'
    assert any(c.char == diamond for row in with_features.buffer for c in row)
    assert not any(c.char == diamond for row in without.buffer for c in row)


def test_world_render_clips_to_a_smaller_canvas():
    gen = WorldGen(40, 30, seed=13)
    gen.generate()
    gen.render(Canvas(10, 6))         # must not raise


def test_world_render_survives_settlements_at_the_edge():
    gen = WorldGen(20, 10, seed=14)
    gen.generate(settlements=10)
    gen.settlements.append((19, 9, 'EdgeTown'))
    gen.render(Canvas(20, 10))         # must not raise
