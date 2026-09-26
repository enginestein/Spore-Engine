"""Physics must not leak non-finite state into rendering.

A rigid-body stack under a substepped integrator can diverge: an impulse
lands while two bodies are already interpenetrating, the correction is
applied twice, velocity compounds, and within a few frames position or
angle becomes inf or NaN. That NaN then flowed straight into
``PolyBody.render``, where ``round(nan)`` raises
``ValueError: cannot convert float NaN to integer``.

``Body.update`` has always sanitised its state; ``PolyBody.update`` did
not, which is why only the polygon scene crashed. These tests pin the
behaviour at the level it actually broke: render must not raise, whatever
the integrator did.
"""

from __future__ import annotations

import math
import random

import pytest

from spore_engine import Canvas
from spore_engine.sim.physics import (Body, CompoundBody, PolyBody, RectBody,
                                      EnhancedPhysicsWorld)


def _polygon(n, r, rng):
    return [(r * math.cos(i / n * math.pi * 2),
             r * math.sin(i / n * math.pi * 2)) for i in range(n)]


def _values(body):
    """Every float that ends up affecting the rendered output."""
    out = []
    for attr in ('pos', 'vel', 'aabb'):
        v = getattr(body, attr, None)
        if v is None:
            continue
        if hasattr(v, 'x'):
            out += [v.x, v.y]
        else:
            out += [v.x, v.y, v.w, v.h]
    for attr in ('angle', 'ang_vel'):
        v = getattr(body, attr, None)
        if v is not None:
            out.append(v)
    for p in (getattr(body, 'verts', None) or []):
        out += list(p)
    return out


# --- the direct regression ----------------------------------------------

def test_polybody_update_sanitises_state():
    b = PolyBody([(0, 0), (4, 0), (4, 4), (0, 4)], mass=1.0)
    # Force every accumulator to a non-finite value.
    b.vel.x = float('inf')
    b.vel.y = float('nan')
    b.ang_vel = float('inf')
    b.angle = float('nan')
    b.update(0.016)
    assert all(math.isfinite(v) for v in _values(b))


def test_polybody_update_sanitises_after_position_corrupts():
    b = PolyBody([(0, 0), (4, 0), (4, 4), (0, 4)], mass=1.0)
    b.pos.x = float('nan')
    b.update(0.016)
    assert all(math.isfinite(v) for v in _values(b))


def test_render_never_raises_on_a_degenerate_body():
    b = PolyBody([(0, 0), (4, 0), (4, 4), (0, 4)], mass=1.0)
    b.vel.x = float('inf')
    b.vel.y = float('nan')
    b.update(0.016)
    b.render(Canvas(40, 20))          # used to raise ValueError here


# --- randomised stress ---------------------------------------------------

@pytest.mark.parametrize('seed', range(25))
def test_adversarial_impulses_keep_a_polybody_finite(seed):
    rng = random.Random(seed)
    n = rng.randint(3, 6)
    verts = _polygon(n, rng.uniform(2, 10), rng)
    b = PolyBody(verts, mass=rng.choice([0.0, 0.5, 1.0, 1e6]),
                 pos=(rng.uniform(0, 80), rng.uniform(0, 24)))
    canvas = Canvas(80, 24)
    for _ in range(60):
        b.apply_impulse(rng.uniform(-5000, 5000), rng.uniform(-5000, 5000),
                        b.pos.x + rng.uniform(-5, 5), b.pos.y + rng.uniform(-5, 5))
        b.update(rng.uniform(0.0, 0.116), bounds_x=80, bounds_y=24)
        b.render(canvas)
    assert all(math.isfinite(v) for v in _values(b))


@pytest.mark.parametrize('seed', range(12))
def test_a_loaded_world_stays_finite_and_renders(seed):
    """The configuration that actually failed: a mixed world, substepped."""
    rng = random.Random(seed)
    w, h = 80, 24
    world = EnhancedPhysicsWorld(gravity=15, bounds_x=w, bounds_y=h)
    for _ in range(6):
        world.add_body(Body(rng.randint(5, w - 5), rng.randint(-10, 0),
                            rng.uniform(1, 2.5), rng.uniform(0.5, 2),
                            None))
    for _ in range(4):
        world.add_body(PolyBody(_polygon(rng.choice([3, 4, 5, 6]),
                                         rng.uniform(2, 4), rng),
                                rng.uniform(1, 3), None,
                                pos=(rng.randint(5, w - 5), rng.randint(-15, -5))))
    for _ in range(3):
        comp = CompoundBody(rng.randint(5, w - 5), rng.randint(-20, -10),
                            rng.uniform(1, 3), None)
        comp.add_circle(0, 0, 1.5, 0.5)
        comp.add_rect(2.5, -0.5, 2, 1, 0.5)
        comp.add_poly(0, -2.5, _polygon(3, 1.5, rng), 0.5)
        world.add_body(comp)
    floor = RectBody(0, h - 2, w, 2, mass=0)
    floor.locked = True
    world.add_body(floor)

    canvas = Canvas(w, h)
    timer = 0.0
    for _ in range(150):
        timer += 0.016
        if timer > 2:
            timer = 0.0
            world.add_body(Body(rng.randint(3, w - 3), -5, rng.uniform(0.8, 2.0),
                                rng.uniform(0.3, 1.5), None))
            if rng.random() < 0.4:
                world.add_body(PolyBody(
                    _polygon(rng.choice([3, 4, 5, 6]), rng.uniform(1.5, 3.0), rng),
                    rng.uniform(0.5, 2), None,
                    pos=(rng.randint(3, w - 3), -8)))
        world.step(0.016, substeps=8)
        world.render(canvas)
        for body in world.bodies:
            assert all(math.isfinite(v) for v in _values(body)), \
                f'{type(body).__name__} went non-finite'
