"""Starry Night - low-poly terrain, painterly filter, drifting stars.

Migrated onto the array image pipeline. The previous version ran
``KuwaharaFilter`` *after* ``hr.to_canvas(c)``, and that filter reads only
``Cell.fg`` - which on a folded half-block surface is the *top* sub-cell. So it
smeared the top half of every cell and left the bottom half at full sharpness.
Here the filter runs on an :class:`Image` before the fold, so both halves are
treated the same.

The 3-D terrain still draws into cells directly, because
:func:`~spore_engine.render3d.render_mesh_solid` shades and z-buffers itself.
``Image.from_surface`` is the bridge: read what the mesh drew back out, grade
the whole frame together, and write it back at a depth above the mesh.
"""

import math

from spore_engine import (Canvas, Color, Field, Gradient, HiResCanvas, Image,
                          scene_state)
from spore_engine.core.geom import Mat4, Vec3
from spore_engine.fx.imgops import CellCache, StarField
from spore_engine.render3d.engine3d import Mesh3D, render_mesh_solid

_SKY = Gradient(Color(5, 3, 25), Color(10, 8, 40), Color(18, 12, 55), Color(30, 20, 70))
_VS = 12

#: The z ladder for one frame. Background, then the mesh's own 0..1 NDC depth,
#: then the graded rewrite above both.
_Z_SKY = -100
_Z_GRADED = 2
_Z_STARS = 3


def _terrain(t: float) -> Mesh3D:
    """A gaussian swell with two travelling ripples, as a heightfield mesh."""
    verts, faces, colors, heights = [], [], [], []
    for iz in range(_VS):
        for ix in range(_VS):
            hx, hz = ix / (_VS - 1) - 0.5, iz / (_VS - 1) - 0.5
            d = math.hypot(hx, hz)
            h = math.exp(-d * d * 3) * (1.2 + 0.3 * math.sin(t * 0.4 + d * 5))
            h += 0.15 * (math.sin(ix * 0.7 + t * 0.3) + math.cos(iz * 0.5 + t * 0.2))
            heights.append(h)
            verts.append(Vec3(hx * 6, h * 3, hz * 6))
    for iz in range(_VS - 1):
        for ix in range(_VS - 1):
            i = iz * _VS + ix
            faces.append([i, i + 1, i + _VS])
            faces.append([i + 1, i + _VS + 1, i + _VS])
            colors.append(Color.from_hsv(0.65 - heights[i] * 0.15,
                                         0.5 + heights[i] * 0.3,
                                         0.6 + heights[i] * 0.4))
    mesh = Mesh3D()
    mesh.verts, mesh.faces, mesh.face_colors = verts, faces, colors
    return mesh


def scene_starry_night(c: Canvas, hr: HiResCanvas, t: float, pt, dt: float):
    """Starry Night - painterly low-poly terrain under a drifting star field."""
    st = scene_state('starry_night')
    stars = st.get('stars', None, lambda: StarField(count=260, seed=0x57A))
    cache = st.get('cache', None, lambda: None)
    if cache is None or not cache.matches(hr.h, hr.w):
        cache = CellCache(hr.h, hr.w)
        st.cache = cache

    sky = Image.gradient('y', _SKY, hr.h, hr.w)
    sky = sky.add((Field.plasma(hr.h, hr.w,
                                terms=((0.015, 0.02, 0.0, 0.25, 1.0, 0.0),
                                       (0.0, 0.02, 0.0, 0.2, 1.0, 1.7)),
                                t=t) * 0.4).tinted(Color(90, 70, 160)))
    sky.to_cells(hr, z=_Z_SKY, cache=cache)

    view = Mat4.look_at(Vec3(math.sin(t * 0.1) * 4, 1.5, math.cos(t * 0.1) * 4),
                        Vec3(0, 0.5, 0))
    proj = Mat4.perspective(1.0, hr.w / hr.h, 0.1, 20)
    light = Vec3(math.sin(t * 0.15), -0.5, math.cos(t * 0.15)).norm()
    render_mesh_solid(hr, _terrain(t), view, proj, light)

    graded = Image.from_surface(hr).kuwahara(2).posterized(5)
    graded.to_cells(hr, z=_Z_GRADED, cache=cache)

    # Stars go on *after* the filter. They are one sub-cell wide, and a
    # Kuwahara window of 3x3 quadrants flattens them into the background - the
    # previous version only got away with it by drawing stars post-filter too.
    stars.draw_cells(hr, t, z=_Z_STARS, threshold=0.24, gain=150.0)

    hr.to_canvas(c)

    c.draw_text(2, 0, 'Starry Night', Color.from_hsv(0.62, 0.4, 0.9), z=100)
    c.draw_text(2, c.h - 1,
                'low-poly terrain | Kuwahara + Posterize | graded pre-fold',
                Color(64, 64, 64), z=100)
