"""Every registered demo scene must render without raising.

The demo gallery is the widest integration surface in the repo: 130+ scene
functions, each touching a different combination of canvas, colour, noise,
physics, 3D and fx code. They were never executed as part of the suite, so
a rename or a removed method could leave 30 scenes broken with nothing to
notice.

Each scene is called with the same argument shape ``demo.py`` uses:
``fn(canvas, hires_canvas, t, particles, dt)``.
"""

from __future__ import annotations

import random
import warnings

import pytest

from spore_engine import Canvas, HiResCanvas, ParticleSystem
from demos import SCENES

# Most scenes drive the global `random` module directly and none of them seed
# it, so a scene's output - and whether a physics stack happens to diverge -
# changes from run to run. Seeding per test makes a failure reproducible
# without changing how the scenes themselves behave.
SEEDS = [0, 1, 2]

# Small but not degenerate: some scenes divide by width/height and a 1x1
# canvas hides divide-by-zero paths that never happen in real use.
COLS, ROWS = 40, 20

# More than one timestamp, because a fair number of scenes only touch their
# interesting code after t has advanced (animation curves, settled physics).
TIMES = [0.0, 0.5, 3.7]

# Sizes a user can actually hit: a split pane, a small window, a default
# terminal, a maximised one. Scenes that assume a wide buffer only break at
# the small end, so that is where this is worth checking.
SIZES = [(16, 8), (24, 8), (40, 20), (80, 24), (120, 40)]

_SCENE_IDS = [name for name, _ in SCENES]


def _render(name, fn, t, seed=0):
    random.seed(seed)
    canvas = Canvas(COLS, ROWS)
    hires = HiResCanvas(COLS, ROWS * 2)
    particles = ParticleSystem(200)
    with warnings.catch_warnings():
        # numpy/numba chatter about a non-writable array being returned from
        # a read-only buffer is not a scene bug.
        warnings.simplefilter('ignore')
        fn(canvas, hires, t, particles, 0.016)


def test_scene_registry_is_populated():
    assert len(SCENES) > 100, 'the demo registry looks truncated'
    names = [name for name, _ in SCENES]
    assert len(names) == len(set(names)), 'duplicate scene names in the registry'
    for name, fn in SCENES:
        assert callable(fn), f'{name} is not callable'


@pytest.mark.parametrize('name,fn', SCENES, ids=_SCENE_IDS)
@pytest.mark.parametrize('t', TIMES)
def test_scene_renders(name, fn, t):
    _render(name, fn, t)


@pytest.mark.parametrize('name,fn', SCENES, ids=_SCENE_IDS)
def test_scene_renders_on_a_tiny_canvas(name, fn):
    """A scene must survive a small terminal.

    Real terminals get resized, and code that assumed a wide buffer only
    shows up when it does not get one: a scene cached a height profile or a
    decoded image sized to the first canvas it ever saw, then indexed it
    with the new width.
    """
    random.seed(0)
    canvas = Canvas(12, 6)
    hires = HiResCanvas(12, 12)
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        fn(canvas, hires, 1.0, ParticleSystem(20), 0.016)


@pytest.mark.parametrize('name,fn', SCENES, ids=_SCENE_IDS)
@pytest.mark.parametrize('w,h', SIZES)
def test_scene_renders_at_multiple_terminal_sizes(name, fn, w, h):
    """Resizing a terminal must not break a scene.

    Each case gets a fresh scene, but module-level scene state is shared
    within a run, so this also exercises the resize path of state that was
    built for a different size.
    """
    random.seed(0)
    canvas = Canvas(w, h)
    hires = HiResCanvas(w, h * 2)
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        fn(canvas, hires, 1.0, ParticleSystem(50), 0.016)


@pytest.mark.parametrize('name,fn', SCENES, ids=_SCENE_IDS)
@pytest.mark.parametrize('seed', SEEDS)
def test_scene_renders_across_random_seeds(name, fn, seed):
    """Stochastic scenes must work for any seed, not just a lucky one.

    This is what caught a rigid-body stack whose integrator diverged to NaN
    for some seeds and not others.
    """
    _render(name, fn, 1.0, seed=seed)
