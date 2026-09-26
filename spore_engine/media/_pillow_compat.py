"""Pillow version shims.

Pillow has been removing its pixel-access APIs: ``Image.getdata()`` is
deprecated in favour of ``get_flattened_data()``, and ``Image.__iter__`` was
dropped in Pillow 12. Since the ``media`` extra accepts ``pillow>=9.0.0``, the
only way to work across that range is to feature-detect at the call site --
which is what these helpers do, so no caller has to care which Pillow it got.
"""

from __future__ import annotations

__all__ = ['flat_pixels']


def flat_pixels(img):
    """Return ``img``'s pixels as a flat list of RGBA tuples, row-major.

    Uses ``get_flattened_data()`` on Pillow 12+, and falls back to
    ``getdata()`` (deprecated but still present) on older releases.
    """
    getter = getattr(img, 'get_flattened_data', None)
    if getter is not None:
        return list(getter())
    return list(img.getdata())
