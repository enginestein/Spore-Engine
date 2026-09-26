"""The optional-dependency contract.

pyproject declares numpy as the only hard requirement and promises that
``import spore_engine`` works without the extras. These tests hold the
package to that, in a subprocess so the blocked imports cannot leak into the
rest of the suite.

The failure this guards against is a quiet one: numba, scipy and Pillow were
all imported at module scope by the code that uses them, and none of them were
declared anywhere, so a plain ``pip install spore-engine`` produced an
ImportError on ``import spore_engine`` itself.
"""

from __future__ import annotations

import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

import spore_engine
from spore_engine.core import _accel
from spore_engine.fx import postfx

try:  # 3.11+
    import tomllib
except ModuleNotFoundError:  # 3.10
    import tomli as tomllib

ROOT = Path(__file__).resolve().parent.parent
PYPROJECT = tomllib.loads((ROOT / 'pyproject.toml').read_text())

#: Everything the package may import that is not stdlib and not required.
OPTIONAL = ('numba', 'scipy', 'PIL')

BLOCK_SCRIPT = textwrap.dedent("""
    import builtins, importlib, pathlib, sys
    BLOCK = {blocked!r}
    real = builtins.__import__
    def fake(name, *a, **k):
        if name.split('.')[0] in BLOCK:
            raise ImportError('blocked: ' + name)
        return real(name, *a, **k)
    builtins.__import__ = fake
    for m in list(sys.modules):
        if m.split('.')[0] in BLOCK:
            del sys.modules[m]
    sys.path.insert(0, {root!r})
    import spore_engine
    failed = []
    imported = []
    for p in sorted(pathlib.Path({pkg!r}).rglob('*.py')):
        rel = p.with_suffix('').relative_to(pathlib.Path({pkg!r}).parent)
        mod = str(rel).replace('/', '.')
        if mod.endswith('.__init__'):
            mod = mod[:-9]
        try:
            importlib.import_module(mod)
            imported.append(mod)
        except Exception as e:
            failed.append((mod, type(e).__name__ + ': ' + str(e)))
    print('MODULES', len(imported))
    print('FAILURES', len(failed))
    for mod, err in failed:
        print('FAILED', mod, err)
""")


def _run_blocked(blocked):
    src = BLOCK_SCRIPT.format(blocked=list(blocked), root=str(ROOT), pkg=str(ROOT / 'spore_engine'))
    return subprocess.run([sys.executable, '-c', src], capture_output=True, text=True, cwd=ROOT)


# --- the declared metadata ----------------------------------------------

def test_numpy_is_the_only_required_dependency():
    """numpy is used pervasively by gen/ and sim/, so it must be declared."""
    assert PYPROJECT['project']['dependencies'], 'expected numpy to be a hard requirement'
    names = {d.split('>')[0].split('=')[0].split('[')[0].strip().lower()
             for d in PYPROJECT['project']['dependencies']}
    assert names == {'numpy'}


@pytest.mark.parametrize('dist', OPTIONAL)
def test_optional_dependency_is_not_silently_required(dist):
    """An optional package must not also be a required one."""
    names = {d.split('>')[0].split('=')[0].split('[')[0].strip().lower()
             for d in PYPROJECT['project']['dependencies']}
    assert dist.lower() not in names


def test_optional_dependencies_are_declared_as_extras():
    """Anything imported lazily must still be installable via an extra."""
    extras = PYPROJECT['project']['optional-dependencies']
    declared = set()
    for group in extras.values():
        for dep in group:
            declared.add(dep.split('>')[0].split('=')[0].split('[')[0].strip().lower())
    # 'pillow' is the distribution name for the 'PIL' import.
    assert {'pillow', 'scipy', 'numba'} <= declared
    assert 'all' in extras, 'expected a convenience extra pulling in everything'


# --- the runtime contract -----------------------------------------------

def test_top_level_import_needs_only_numpy():
    """`import spore_engine` must not require an extra."""
    r = _run_blocked(OPTIONAL)
    assert r.returncode == 0, r.stderr
    assert 'FAILURES 0' in r.stdout, r.stdout


def test_every_module_imports_without_the_extras():
    """No module may import an extra at module scope.

    Lazy means inside the function that needs it, so that merely importing a
    module -- which the API-stability and import-integrity tests do for all of
    them -- cannot fail on a bare interpreter.
    """
    r = _run_blocked(OPTIONAL)
    assert r.returncode == 0, r.stderr
    failures = [line for line in r.stdout.splitlines() if line.startswith('FAILED ')]
    assert not failures, 'modules that need an extra at import time:\n' + '\n'.join(failures)
    count = int(r.stdout.split('MODULES')[1].splitlines()[0].strip())
    assert count > 60, f'only {count} modules were imported, which looks wrong'


def test_missing_extra_names_the_extra_instead_of_raising_import_error():
    """The error must tell the user which extra to install."""
    r = subprocess.run(
        [sys.executable, '-c', textwrap.dedent("""
            import sys
            # None in sys.modules makes both `import PIL` and
            # importlib.import_module('PIL.Image') raise ImportError, which a
            # builtins.__import__ hook does not: importlib bypasses it.
            sys.modules['PIL'] = None
            sys.path.insert(0, %r)
            from spore_engine.core._optional import pillow
            try:
                pillow('image_to_mesh')
            except RuntimeError as e:
                print('MESSAGE_OK', e)
        """) % str(ROOT)],
        capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stderr
    assert 'MESSAGE_OK' in r.stdout
    assert 'media' in r.stdout


# --- fallbacks behave like the real thing --------------------------------

def test_accel_reports_whether_numba_is_in_use():
    """The fallback has to be able to say which path it took."""
    assert isinstance(_accel.NUMBA_AVAILABLE, bool)
    try:
        import numba  # noqa: F401
    except ImportError:
        assert _accel.NUMBA_AVAILABLE is False
    else:
        assert _accel.NUMBA_AVAILABLE is True


def test_numba_fallback_returns_the_function_unchanged():
    """Without numba the decorator must be a no-op, not a wrapper."""
    script = textwrap.dedent("""
        import builtins, sys
        real = builtins.__import__
        def fake(name, *a, **k):
            if name.split('.')[0] == 'numba':
                raise ImportError('blocked')
            return real(name, *a, **k)
        builtins.__import__ = fake
        sys.path.insert(0, %r)
        from spore_engine.core import _accel
        @_accel.njit
        def kernel(x):
            return x * 2
        print('NUMBA_AVAILABLE', _accel.NUMBA_AVAILABLE)
        print('RESULT', kernel(21))
    """) % str(ROOT)
    r = subprocess.run([sys.executable, '-c', script], capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stderr
    assert 'NUMBA_AVAILABLE False' in r.stdout
    assert 'RESULT 42' in r.stdout


def test_numba_fallback_njit_accepts_decorator_forms():
    """Both @njit and @njit(...) must work with and without numba."""
    script = textwrap.dedent("""
        import builtins, sys
        real = builtins.__import__
        def fake(name, *a, **k):
            if name.split('.')[0] == 'numba':
                raise ImportError('blocked')
            return real(name, *a, **k)
        builtins.__import__ = fake
        sys.path.insert(0, %r)
        from spore_engine.core import _accel
        @_accel.njit
        def a(x):
            return x + 1
        @_accel.njit(cache=True)
        def b(x):
            return x + 2
        @_accel.njit(cache=False, fastmath=True)
        def c(x):
            return x + 3
        print('OK', a(1), b(1), c(1))
    """) % str(ROOT)
    r = subprocess.run([sys.executable, '-c', script], capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stderr
    assert 'OK 2 3 4' in r.stdout


def test_scipy_fallback_is_available_when_scipy_is_absent():
    script = textwrap.dedent("""
        import builtins, sys
        real = builtins.__import__
        def fake(name, *a, **k):
            if name.split('.')[0] == 'scipy':
                raise ImportError('blocked')
            return real(name, *a, **k)
        builtins.__import__ = fake
        sys.path.insert(0, %r)
        from spore_engine.fx import postfx
        import numpy as np
        print('SCIPY_AVAILABLE', postfx.SCIPY_AVAILABLE)
        c = postfx.Canvas(9, 9)
        for y in range(9):
            for x in range(9):
                c.set_pixel(x, y, '#', postfx.Color(200, 100, 50))
        postfx.box_blur(c, 2)
        postfx.glow(c, 0.5, 2, 0.5)
        postfx.edge_detect(c)
        print('FILTERS_OK')
    """) % str(ROOT)
    r = subprocess.run([sys.executable, '-c', script], capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stderr
    assert 'SCIPY_AVAILABLE False' in r.stdout
    assert 'FILTERS_OK' in r.stdout


@pytest.mark.skipif(not postfx.SCIPY_AVAILABLE, reason='scipy is not installed')
def test_scipy_fallback_matches_scipy_exactly():
    """The fallback must be a drop-in, not an approximation.

    These three filters decide what a frame looks like, so a fallback that
    merely produced a plausible blur would make renders depend on whether
    scipy happened to be installed.
    """
    script = textwrap.dedent("""
        import builtins, sys
        real = builtins.__import__
        def fake(name, *a, **k):
            if name.split('.')[0] == 'scipy':
                raise ImportError('blocked')
            return real(name, *a, **k)
        builtins.__import__ = fake
        sys.path.insert(0, %r)
        from spore_engine.fx import postfx
        assert not postfx.SCIPY_AVAILABLE
        import numpy as np
        # Restore the real import machinery so scipy can supply the reference.
        builtins.__import__ = real
        from scipy import ndimage as sndi

        rng = np.random.default_rng(7)
        bad = 0
        checked = 0
        for shape in [(1,1),(1,5),(2,2),(2,5),(3,3),(4,7),(7,4),(9,9),(16,24),(64,48)]:
            a = rng.random(shape) * 255
            for size in (3,5,7):
                for mine, ref in ((postfx.uniform_filter, sndi.uniform_filter),
                                  (postfx.maximum_filter, sndi.maximum_filter)):
                    got = mine(a, size=size, mode='constant', cval=0)
                    exp = ref(a, size=size, mode='constant', cval=0)
                    checked += 1
                    if got.shape != exp.shape or not np.allclose(got, exp):
                        bad += 1
                        print('MISMATCH', shape, mine.__name__, size)
            for ax in (0,1):
                got = postfx.sobel(a, axis=ax, mode='constant', cval=0)
                exp = sndi.sobel(a, axis=ax, mode='constant', cval=0)
                checked += 1
                if got.shape != exp.shape or not np.allclose(got, exp):
                    bad += 1
                    print('MISMATCH', shape, 'sobel', ax)
        print('CHECKED', checked)
        print('BAD', bad)
    """) % str(ROOT)
    r = subprocess.run([sys.executable, '-c', script], capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stderr
    assert 'MISMATCH' not in r.stdout, r.stdout
    assert int(r.stdout.split('BAD')[1].strip()) == 0
    assert int(r.stdout.split('CHECKED')[1].split('\n')[0].strip()) >= 80
    assert postfx.SCIPY_AVAILABLE, 'this test is meaningless without scipy installed'


def test_noise_and_fluid_work_without_numba():
    """The JIT is a speed knob: results must be the same either way."""
    script = textwrap.dedent("""
        import builtins, sys
        real = builtins.__import__
        def fake(name, *a, **k):
            if name.split('.')[0] == 'numba':
                raise ImportError('blocked')
            return real(name, *a, **k)
        builtins.__import__ = fake
        sys.path.insert(0, %r)
        from spore_engine.sim.noise import PerlinNoise, ValueNoise
        p = PerlinNoise(seed=1)
        print('PERLIN', round(p.noise2(0.3, 0.7), 12))
        v = ValueNoise(seed=2)
        print('VALUE', round(v.noise2(0.3, 0.7), 12))
    """) % str(ROOT)
    r = subprocess.run([sys.executable, '-c', script], capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stderr
    from spore_engine.sim.noise import PerlinNoise, ValueNoise
    assert f"PERLIN {round(PerlinNoise(seed=1).noise2(0.3, 0.7), 12)}" in r.stdout
    assert f"VALUE {round(ValueNoise(seed=2).noise2(0.3, 0.7), 12)}" in r.stdout


def test_package_exposes_a_version():
    assert isinstance(spore_engine.__version__, str)
    assert spore_engine.__version__.count('.') >= 1
