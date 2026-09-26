"""Lazy access to Pillow, with one clear error message.

Pillow lives in the ``media`` extra. Modules that need it import it inside
the function that uses it, so ``import spore_engine`` works without it -- but
a bare ``ModuleNotFoundError: No module named 'PIL'`` deep inside a render
loop is a bad way to learn that the wrong extra is missing. :func:`pillow`
raises a message that names the extra instead.
"""

from __future__ import annotations

import importlib

__all__ = ['pillow', 'require_pillow']

_MESSAGE = (
    'Pillow is required for this operation; install the "media" extra '
    '(pip install spore-engine[media])'
)


def pillow(feature: str = 'this function', *submodules: str):
    """Import ``PIL.Image`` (plus any ``submodules``) or raise a helpful error.

    ``feature`` names the calling operation, so the message says which of the
    several Pillow-backed entry points was reached. Extra ``submodules`` (for
    example ``'ImageDraw'``) are returned as further values, in order.
    """
    try:
        image = importlib.import_module('PIL.Image')
    except ImportError as exc:  # pragma: no cover - depends on the env
        raise RuntimeError(f'{_MESSAGE} (needed by {feature})') from exc
    if not submodules:
        return image
    return (image, *(importlib.import_module(f'PIL.{name}') for name in submodules))


def require_pillow(feature: str = 'this function'):
    """Alias of :func:`pillow` for the common single-module case."""
    return pillow(feature)
