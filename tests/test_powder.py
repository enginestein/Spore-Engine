"""Tests for spore_engine.sim.powder."""
from __future__ import annotations

import numpy as np
import pytest

from spore_engine import Canvas
from spore_engine.sim.powder import (
    ACID, EMPTY, FIRE, FLAMMABLE, GASES, LAVA, LIQUIDS, MATERIAL_COLORS,
    MATERIAL_NAMES, MELTABLE, OIL, PLANT, RENDER_CHARS, SALT, SAND, SMOKE,
    SOLIDS, STEAM, STONE, WATER, WOOD, PowderSim,
)

ALL_MATERIALS = [SAND, WATER, STONE, WOOD, FIRE, SMOKE, OIL, LAVA, ACID,
                 PLANT, SALT, STEAM]


def filled(material, w=40, h=24, density=0.25):
    """A sim with a scattered block of one material, to exercise its update."""
    sim = PowderSim(w, h)
    for y in range(h // 4, h // 2):
        for x in range(0, w, max(2, int(w * density) or 2)):
            sim.set_cell(x, y, material)
    return sim


def count(sim, material):
    return int((sim.type_arr == material).sum())


# -------------------------------------------------------------------
# tables
# -------------------------------------------------------------------

def test_every_material_has_a_name_and_a_colour():
    n = len(MATERIAL_COLORS)
    for m in [*ALL_MATERIALS, EMPTY]:
        assert m in MATERIAL_NAMES, f'{m} has no display name'
        assert 0 <= m < n, f'{m} has no colour'
        assert len(MATERIAL_COLORS[m]) == 3


def test_material_tables_cover_every_id_exactly_once():
    assert set(MATERIAL_NAMES) == set(range(len(MATERIAL_COLORS)))
    assert len(RENDER_CHARS) == len(MATERIAL_COLORS)


def test_material_membership_sets_are_disjoint_and_complete():
    assert {WATER, OIL} == LIQUIDS
    assert {FIRE, SMOKE, STEAM} == GASES
    assert {SAND, STONE, WOOD, LAVA, ACID, PLANT, SALT} == SOLIDS
    assert LIQUIDS.isdisjoint(GASES)
    assert LIQUIDS.isdisjoint(SOLIDS)
    assert GASES.isdisjoint(SOLIDS)
    assert set(ALL_MATERIALS) == LIQUIDS | GASES | SOLIDS


def test_flammable_and_meltable_reference_real_materials():
    assert {WOOD, OIL, PLANT} == FLAMMABLE
    assert all(v in ALL_MATERIALS for v in MELTABLE.values())
    assert STONE not in MELTABLE, 'melting stone duplicated lava'


def test_colours_are_valid_rgb_bytes():
    for row in MATERIAL_COLORS:
        assert len(row) == 3
        assert all(0 <= int(c) <= 255 for c in row)


# -------------------------------------------------------------------
# construction and cell access
# -------------------------------------------------------------------

def test_a_new_sim_is_empty_and_room_temperature():
    sim = PowderSim(8, 4)
    assert sim.type_arr.shape == (32,)
    assert count(sim, EMPTY) == 32
    assert (sim.temp_arr == 20).all()


def test_set_cell_out_of_bounds_is_ignored():
    sim = PowderSim(8, 4)
    for x, y in [(-1, 0), (0, -1), (8, 0), (0, 4), (99, 99)]:
        sim.set_cell(x, y, STONE)          # must not raise or wrap
    assert count(sim, STONE) == 0


def test_set_cell_gives_each_material_its_own_start_state():
    sim = PowderSim(16, 8)
    sim.set_cell(0, 0, FIRE)
    assert 20 <= sim.life_arr[0] <= 60
    assert sim.temp_arr[0] >= 400

    sim.set_cell(1, 0, SMOKE)
    assert 30 <= sim.life_arr[1] <= 80

    sim.set_cell(2, 0, LAVA)
    assert sim.temp_arr[2] >= 800

    sim.set_cell(3, 0, PLANT)
    assert 50 <= sim.life_arr[3] <= 200

    sim.set_cell(4, 0, STEAM)
    assert sim.life_arr[4] > 0

    sim.set_cell(5, 0, SALT)
    assert sim.life_arr[5] == 1

    sim.set_cell(6, 0, STONE)
    assert sim.life_arr[6] == 0 and sim.temp_arr[6] == 20


def test_paint_uses_a_disc_of_the_brush_radius():
    sim = PowderSim(40, 20)
    sim.brush_size = 2
    sim.paint(20, 10, STONE)
    # a radius-2 disc covers 13 cells, not the 5x5 square around it
    assert count(sim, STONE) == 13
    assert sim._get_type(20, 10) == STONE
    assert sim._get_type(18, 12) == EMPTY      # corner of the 5x5 square, outside the disc
    assert sim._get_type(18, 10) == STONE      # left edge of the disc


def test_paint_defaults_to_the_current_material():
    sim = PowderSim(40, 20)
    sim.brush_size = 1
    sim.current_material = WATER
    sim.paint(20, 10)
    assert sim._get_type(20, 10) == WATER


def test_paint_clips_at_the_edges():
    sim = PowderSim(8, 8)
    sim.brush_size = 3
    sim.paint(0, 0, STONE)      # must not wrap or raise
    sim.paint(7, 7, STONE)
    assert sim._get_type(-1, -1) == -1


def test_clear_resets_every_array():
    sim = filled(SAND)
    sim.set_cell(0, 0, FIRE)
    sim.render(Canvas(40, 24))
    sim.clear()
    assert count(sim, EMPTY) == sim.size
    assert (sim.life_arr == 0).all()
    assert (sim.temp_arr == 20).all()
    assert (sim.updated_arr == False).all()   # noqa: E712
    assert (sim.color_arr == 0).all()


def test_get_type_out_of_bounds_is_minus_one():
    sim = PowderSim(8, 4)
    assert sim._get_type(-1, 0) == -1
    assert sim._get_type(0, 4) == -1
    assert sim._get_type(0, 0) == EMPTY


# -------------------------------------------------------------------
# physics
# -------------------------------------------------------------------

def test_sand_falls_down():
    sim = PowderSim(8, 8)
    sim.set_cell(3, 0, SAND)
    sim.update()
    assert sim._get_type(3, 1) == SAND
    assert sim._get_type(3, 0) == EMPTY


def test_sand_piles_up_and_spreads_diagonally_when_blocked():
    sim = PowderSim(8, 8)
    for y in range(6):
        sim.set_cell(3, y, SAND)
    for _ in range(4):
        sim.update()
    # it cannot sink through the floor, so it must end up beside the column
    assert sim._get_type(3, 6) == SAND
    assert count(sim, SAND) == 6


def test_sand_never_leaves_the_grid():
    sim = PowderSim(6, 6)
    for y in range(6):
        for x in range(6):
            sim.set_cell(x, y, SAND)
    for _ in range(10):
        sim.update()
    assert count(sim, SAND) == 36
    assert sim.type_arr.min() >= 0


def test_water_falls_and_settles_above_a_floor():
    sim = PowderSim(8, 8)
    for x in range(8):
        sim.set_cell(x, 7, STONE)
    sim.set_cell(3, 0, WATER)
    for _ in range(6):
        sim.update()
    assert sim._get_type(3, 7) == STONE
    # it ends up resting on the floor, spread sideways rather than in one column
    assert any(sim._get_type(x, 6) == WATER for x in range(8))
    assert count(sim, WATER) == 1


def test_water_and_oil_swap_past_each_other():
    """Both rules are a straight swap, so they are checked in isolation: in a
    full update() the lower cell is visited first and has already moved."""
    sim = PowderSim(8, 8)
    sim.set_cell(3, 3, WATER)
    sim.set_cell(3, 4, OIL)
    sim._update_water(3, 3)
    assert sim._get_type(3, 3) == OIL
    assert sim._get_type(3, 4) == WATER

    # Oil sitting on water holds still so that _update_water can sink past it.
    sim = PowderSim(8, 8)
    sim.set_cell(3, 3, OIL)
    sim.set_cell(3, 4, WATER)
    sim._update_oil(3, 3)
    assert sim._get_type(3, 3) == OIL
    assert sim._get_type(3, 4) == WATER

    # Oil under water rises through it, pushing the water down.
    sim = PowderSim(8, 8)
    sim.set_cell(3, 2, WATER)
    sim.set_cell(3, 3, OIL)
    sim._update_oil(3, 3)
    assert sim._get_type(3, 2) == OIL
    assert sim._get_type(3, 3) == WATER


@pytest.mark.parametrize('top,bottom', [(WATER, OIL), (OIL, WATER)])
def test_oil_ends_up_above_water_however_it_starts(top, bottom):
    """Oil is less dense, so it must be the upper of the pair once they settle,
    whichever way round they started."""
    sim = PowderSim(8, 14)
    sim.set_cell(3, 2, top)
    sim.set_cell(3, 3, bottom)
    for _ in range(6):
        sim.update()
    oil = [y for y in range(14) if sim._get_type(3, y) == OIL]
    water = [y for y in range(14) if sim._get_type(3, y) == WATER]
    assert oil and water, f'one of the liquids went missing: {oil} {water}'
    assert min(oil) < min(water), f'oil must be above water, got rows {oil} and {water}'
    assert int((sim.type_arr != EMPTY).sum()) == 2, 'a liquid was created or lost'


def test_water_sinks_through_a_layer_of_oil():
    """A walled cell leaves nowhere to spread, so the result is unambiguous."""
    sim = PowderSim(5, 8)
    for x in range(5):
        sim.set_cell(x, 7, STONE)
        sim.set_cell(x, 6, OIL)
    sim.set_cell(2, 3, WATER)
    for _ in range(8):
        sim.update()
    assert sim._get_type(2, 6) == WATER
    assert sim._get_type(2, 5) == OIL


def test_water_rests_on_a_solid_floor():
    sim = PowderSim(8, 8)
    for x in range(8):
        sim.set_cell(x, 7, STONE)
    sim.set_cell(3, 5, WATER)
    for _ in range(4):
        sim.update()
    assert sim._get_type(3, 7) == STONE
    assert count(sim, WATER) == 1, 'water was lost through the floor'
    assert all(sim._get_type(x, 7) == STONE for x in range(8))


def test_fire_burns_out_into_smoke_and_then_disappears():
    sim = PowderSim(8, 8)
    sim.set_cell(3, 3, FIRE)
    for _ in range(400):
        sim.update()
    assert count(sim, FIRE) == 0
    assert count(sim, SMOKE) == 0, 'smoke should also have dissipated'


def test_fire_ignites_adjacent_flammables():
    sim = PowderSim(10, 10)
    for y in range(5, 7):
        for x in range(2, 8):
            sim.set_cell(x, y, WOOD)
    sim.set_cell(4, 4, FIRE)
    for _ in range(60):
        sim.update()
    assert count(sim, WOOD) < 12, 'the fire never spread to the wood'


def test_smoke_rises_and_clears():
    sim = PowderSim(8, 8)
    sim.set_cell(3, 6, SMOKE)
    for _ in range(10):
        sim.update()
    rows = [j for y in range(8) for j in range(8) if sim._get_type(j, y) == SMOKE]
    assert rows, 'the smoke vanished instantly instead of rising'
    assert min(rows) < 6, 'smoke never rose'
    for _ in range(3000):
        sim.update()
    assert count(sim, SMOKE) == 0


def test_lava_turns_to_stone_when_it_cools():
    sim = PowderSim(8, 8)
    for x in range(8):
        sim.set_cell(x, 7, STONE)
    sim.set_cell(3, 6, LAVA)
    for _ in range(600):
        sim.update()
    assert count(sim, LAVA) == 0, 'lava never cooled into stone'
    assert count(sim, STONE) == 9, 'lava should have become stone, not vanished'


def test_lava_does_not_multiply_on_a_stone_floor():
    """STONE used to be meltable, so a spill converted the floor into more
    lava forever and lava mass grew out of nothing."""
    sim = PowderSim(8, 8)
    for x in range(8):
        sim.set_cell(x, 7, STONE)
    sim.set_cell(3, 6, LAVA)
    filled_before = int((sim.type_arr != EMPTY).sum())
    for _ in range(600):
        sim.update()
    assert int((sim.type_arr != EMPTY).sum()) == filled_before
    assert int((sim.type_arr == LAVA).sum()) == 0


def test_melting_sand_conserves_the_cell_count():
    sim = PowderSim(10, 6)
    for x in range(10):
        sim.set_cell(x, 5, SAND)
    sim.set_cell(4, 4, LAVA)
    before = int((sim.type_arr != EMPTY).sum())
    for _ in range(60):
        sim.update()
    assert int((sim.type_arr != EMPTY).sum()) == before


def test_lava_quenched_by_water_becomes_stone_and_steam():
    """Checked on the rule itself: a full update() visits the water first, so
    it has already fallen away by the time the lava is reached."""
    sim = PowderSim(8, 8)
    sim.set_cell(3, 3, LAVA)
    sim.set_cell(3, 4, WATER)
    sim._update_lava(3, 3, sim._rng_state)
    assert sim._get_type(3, 3) == STONE
    assert sim._get_type(3, 4) == STEAM


def test_lava_falls_and_never_escapes():
    sim = PowderSim(8, 8)
    sim.set_cell(3, 2, LAVA)
    sim.update()
    assert sim._get_type(3, 3) == LAVA
    assert sim._get_type(3, 2) == EMPTY


def test_lava_melts_adjacent_sand():
    sim = PowderSim(10, 10)
    for x in range(8):
        sim.set_cell(x, 8, STONE)
    for x in range(8):
        sim.set_cell(x, 9, SAND)
    sim.set_cell(4, 8, LAVA)
    for _ in range(40):
        sim.update()
    assert count(sim, LAVA) >= 1


def test_acid_dissolves_neighbours():
    sim = PowderSim(10, 10)
    for y in range(5, 7):
        for x in range(2, 8):
            sim.set_cell(x, y, SAND)
    sim.set_cell(4, 7, ACID)
    for _ in range(80):
        sim.update()
    assert count(sim, SAND) < 20, 'the acid dissolved nothing'


def test_acid_spares_stone():
    sim = PowderSim(10, 10)
    for y in range(4, 6):
        for x in range(2, 8):
            sim.set_cell(x, y, STONE)
    sim.set_cell(4, 7, ACID)
    for _ in range(60):
        sim.update()
    assert count(sim, STONE) == 12


def test_acid_eventually_disappears():
    sim = PowderSim(8, 8)
    sim.set_cell(3, 3, ACID)
    for _ in range(3000):
        sim.update()
    assert count(sim, ACID) == 0


def test_plant_grows_along_a_surface():
    sim = PowderSim(10, 10)
    for x in range(10):
        sim.set_cell(x, 8, STONE)
    sim.set_cell(4, 7, PLANT)
    for _ in range(300):
        sim.update()
    assert count(sim, PLANT) > 1, 'the plant never spread'


def test_plant_does_not_grow_into_empty_air():
    """A lone plant used to treat its own body as support and grew a stack
    hanging in mid-air."""
    sim = PowderSim(10, 10)
    sim.set_cell(4, 4, PLANT)
    for _ in range(500):
        sim.update()
    assert count(sim, PLANT) == 1


def test_a_grounded_plant_grows_upward():
    sim = PowderSim(12, 12)
    for x in range(12):
        sim.set_cell(x, 10, STONE)
    sim.set_cell(5, 9, PLANT)
    for _ in range(400):
        sim.update()
    assert count(sim, PLANT) > 1, 'a plant on the ground never grew'
    rows = [y for y in range(12) for x in range(12) if sim._get_type(x, y) == PLANT]
    assert min(rows) < 10, 'growth did not rise above the ground'


@pytest.mark.parametrize('liquid', [WATER, OIL])
def test_salt_dissolves_in_a_liquid(liquid):
    """Checked on the rule itself: a full update() moves the lower cell before
    the salt above it is visited."""
    sim = PowderSim(8, 8)
    sim.set_cell(3, 3, SALT)
    sim.set_cell(3, 4, liquid)
    sim._update_salt(3, 3)
    assert sim._get_type(3, 3) == EMPTY
    assert sim._get_type(3, 4) == liquid


def test_salt_falls_and_piles_up():
    sim = PowderSim(8, 8)
    for x in range(8):
        sim.set_cell(x, 7, STONE)
    sim.set_cell(3, 2, SALT)
    for _ in range(4):
        sim.update()
    assert sim._get_type(3, 6) == SALT


def test_steam_rises_and_condenses_away():
    sim = PowderSim(8, 8)
    sim.set_cell(3, 6, STEAM)
    sim.update()
    for _ in range(400):
        sim.update()
    assert count(sim, STEAM) == 0


def test_wood_is_static():
    sim = PowderSim(8, 8)
    sim.set_cell(3, 2, WOOD)
    for _ in range(20):
        sim.update()
    assert sim._get_type(3, 2) == WOOD


def test_stone_is_static():
    sim = PowderSim(8, 8)
    sim.set_cell(3, 2, STONE)
    for _ in range(20):
        sim.update()
    assert sim._get_type(3, 2) == STONE


def test_stone_is_static_while_liquid_pours_past_it():
    sim = PowderSim(8, 8)
    sim.set_cell(3, 0, STONE)
    sim.set_cell(3, 1, WATER)
    for _ in range(4):
        sim.update()
    assert sim._get_type(3, 0) == STONE, 'stone must never move'
    assert sim._get_type(3, 1) != WATER, 'the water should have fallen past it'


# -------------------------------------------------------------------
# update bookkeeping
# -------------------------------------------------------------------

def test_update_clears_the_moved_mask_so_cells_can_move_again():
    sim = PowderSim(8, 8)
    sim.set_cell(3, 0, SAND)
    sim.update()
    assert not sim.updated_arr.any()
    sim.update()
    assert sim._get_type(3, 2) == SAND


def test_a_cell_moves_at_most_once_per_update():
    sim = PowderSim(8, 16)
    sim.set_cell(3, 0, SAND)
    sim.update()
    # one step, not a fall to the floor in a single tick
    assert sim._get_type(3, 1) == SAND
    assert sim._get_type(3, 0) == EMPTY


def test_update_on_an_empty_sim_is_a_no_op():
    sim = PowderSim(16, 8)
    for _ in range(3):
        sim.update()
    assert count(sim, EMPTY) == sim.size


def test_update_on_a_single_cell_sim_does_not_raise():
    PowderSim(1, 1).update()


def test_update_on_a_flat_sim_does_not_raise():
    sim = PowderSim(16, 1)
    for x in range(16):
        sim.set_cell(x, 0, SAND)
    for _ in range(3):
        sim.update()


@pytest.mark.parametrize('material', ALL_MATERIALS)
def test_every_material_updates_without_error_or_escape(material):
    sim = filled(material)
    for _ in range(30):
        sim.update()
    assert sim.type_arr.min() >= EMPTY
    assert sim.type_arr.max() < len(MATERIAL_NAMES)


@pytest.mark.parametrize('material', ALL_MATERIALS)
def test_every_material_renders_valid_colours(material):
    sim = filled(material)
    sim.update()
    canvas = Canvas(40, 24)
    sim.render(canvas)
    for row in canvas.buffer:
        for cell in row:
            if cell.fg is not None:
                assert 0 <= cell.fg.r <= 255
                assert 0 <= cell.fg.g <= 255
                assert 0 <= cell.fg.b <= 255


# -------------------------------------------------------------------
# determinism
# -------------------------------------------------------------------

def test_two_fresh_sims_evolve_identically():
    def run():
        sim = filled(SAND, w=40, h=24)
        for _ in range(15):
            sim.update()
        return sim.type_arr.copy()
    assert np.array_equal(run(), run())


def test_rendering_does_not_change_the_simulation():
    """render() draws tints from the simulation's RandomState, so drawing a
    frame changed the trajectory of the next update."""
    def run(draw):
        sim = PowderSim(40, 24)
        for y in range(20):
            for x in range(10, 30):
                sim.set_cell(x, y, SAND)
        for x in range(0, 40, 3):
            sim.set_cell(x, 5, WATER)
        for _ in range(8):
            sim.update()
            if draw:
                sim.render(Canvas(40, 24))
        return sim.type_arr.copy()
    assert np.array_equal(run(False), run(True))


def test_sims_stay_in_lockstep_when_only_one_is_rendered():
    a, b = filled(SAND), filled(SAND)
    for step in range(12):
        a.update()
        b.update()
        b.render(Canvas(40, 24))
        assert np.array_equal(a.type_arr, b.type_arr), f'diverged at step {step}'
