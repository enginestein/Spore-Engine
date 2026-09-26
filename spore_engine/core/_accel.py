"""Optional numba acceleration, with a pure-Python fallback.

``sim.noise`` and ``sim.fluid`` JIT-compile their inner loops with numba. The
compiled and uncompiled paths are numerically identical -- numba is purely a
speed knob here -- so when numba is not installed we fall back to a decorator
that returns the function unchanged and everything still works, just slower.

Importing this module must never fail: the whole point is that a missing
numba is not an error.
"""

from __future__ import annotations

import os

__all__ = ['NUMBA_AVAILABLE', 'njit']

#: numba caches compiled kernels to disk. That is a large win for the noise
#: and fluid kernels, but it writes into the user's build tree and can race
#: when several processes import the module at once, so it stays opt-out.
_CACHE = os.environ.get('SPORE_NUMBA_CACHE', '1') not in ('0', 'false', 'no')

try:  # pragma: no cover - depends on the environment
    from numba import njit as _numba_njit

    NUMBA_AVAILABLE = True

    def njit(*args, **kwargs):
        """``numba.njit`` with cache=True unless the caller said otherwise."""
        if args or kwargs:
            return _numba_njit(*args, **kwargs)
        return _numba_njit(cache=_CACHE)

except ImportError:  # pragma: no cover - exercised by the no-numba test
    NUMBA_AVAILABLE = False

    def njit(*args, **kwargs):
        """No-op stand-in for ``numba.njit``.

        Accepts and ignores every argument numba would take, so decorated
        functions stay valid Python.
        """

        def decorate(fn):
            return fn

        if len(args) == 1 and not kwargs and callable(args[0]):
            return args[0]
        return decorate
