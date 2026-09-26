"""Convert a 2D image into a 3D heightfield mesh and render as ASCII."""
from __future__ import annotations
import math
import os
from ..render3d.engine3d import Mesh3D, render_mesh_solid
from ..core.geom import Vec3, Mat4
from ..core.color import Color
from ..core.canvas import Canvas, HiResCanvas
from ..core._optional import pillow
from ._pillow_compat import flat_pixels


def image_to_heightfield(path: str,
                          grid_w: int = 48, grid_h: int = 36,
                          height_scale: float = 2.0,
                          base_width: float = 6.0) -> Mesh3D:
    """Load an image and build a coloured heightfield Mesh3D.

    Brighter pixels -> higher elevation.  Face colours come from the
    original image so you get both shape and colour.
    """
    Image = pillow('image_to_mesh')
    with Image.open(path) as src:
        img = src.convert('RGBA')
    iw, ih = img.size
    aspect = ih / iw
    out_h = max(4, int(grid_w * aspect * 0.7))
    img_small = img.resize((grid_w, out_h), Image.LANCZOS)
    pixels = flat_pixels(img_small)
    w, h = grid_w, out_h

    mesh = Mesh3D(f'heightfield({os.path.basename(path)})')
    verts: list[Vec3] = []
    colors: list[list[Color]] = [[Color(0, 0, 0) for _ in range(w)] for _ in range(h)]

    base_width / w
    base_width / h * 0.7

    for row in range(h):
        for col in range(w):
            r, g, b, a = pixels[row * w + col]
            lum = 0.299 * r + 0.587 * g + 0.114 * b
            elev = (lum / 255.0) * height_scale
            x = (col / (w - 1) - 0.5) * base_width if w > 1 else 0
            z = (row / (h - 1) - 0.5) * base_width * 0.7 if h > 1 else 0
            verts.append(Vec3(x, elev, z))
            colors[row][col] = Color(r, g, b)

    for row in range(h - 1):
        for col in range(w - 1):
            i0 = row * w + col
            i1 = row * w + col + 1
            i2 = (row + 1) * w + col
            i3 = (row + 1) * w + col + 1
            c00, c01 = colors[row][col], colors[row][col + 1]
            c10, c11 = colors[row + 1][col], colors[row + 1][col + 1]
            avg = lambda a, b, c, d: Color(
                (a.r + b.r + c.r + d.r) // 4,
                (a.g + b.g + c.g + d.g) // 4,
                (a.b + b.b + c.b + d.b) // 4,
            )
            fc = avg(c00, c01, c10, c11)
            mesh.faces.append([i0, i1, i3])
            mesh.face_colors.append(fc)
            mesh.faces.append([i0, i3, i2])
            mesh.face_colors.append(fc)

    mesh.verts = verts
    return mesh


def heightfield_cube(height_grid: list[list[float]],
                     colors: list[list[Color]],
                     base_width: float = 6.0) -> Mesh3D:
    """Build a solid mesh (top + sides + bottom) from a height grid."""
    h = len(height_grid)
    w = len(height_grid[0]) if h else 0
    cell_w = base_width / w
    cell_h = base_width / h * 0.7
    cx = base_width / 2
    cz = base_width * 0.7 / 2

    mesh = Mesh3D('heightfield_cube')
    verts: list[Vec3] = []

    def idx(col, row):
        return row * w + col

    # Top vertices
    top_verts: list[list[int]] = []
    for row in range(h):
        row_verts = []
        for col in range(w):
            x = col * cell_w - cx
            z = row * cell_h - cz
            verts.append(Vec3(x, height_grid[row][col], z))
            row_verts.append(idx(col, row))
        top_verts.append(row_verts)

    # Bottom vertices (shifted down)
    bottom_offset = len(verts)
    for row in range(h):
        for col in range(w):
            x = col * cell_w - cx
            z = row * cell_h - cz
            verts.append(Vec3(x, -0.2, z))

    # Top faces
    for row in range(h - 1):
        for col in range(w - 1):
            i0, i1, i2, i3 = top_verts[row][col], top_verts[row][col + 1], top_verts[row + 1][col], top_verts[row + 1][col + 1]
            avg = lambda a, b, c, d: Color(
                (a.r + b.r + c.r + d.r) // 4, (a.g + b.g + c.g + d.g) // 4, (a.b + b.b + c.b + d.b) // 4)
            fc = avg(colors[row][col], colors[row][col + 1], colors[row + 1][col], colors[row + 1][col + 1])
            mesh.faces.append([i0, i1, i3])
            mesh.face_colors.append(fc)
            mesh.faces.append([i0, i3, i2])
            mesh.face_colors.append(fc)

    # Side faces (edges of the grid)
    side_col = Color(100, 100, 120)
    for col in range(w - 1):
        i0 = top_verts[0][col]
        i1 = top_verts[0][col + 1]
        ib0 = bottom_offset + idx(col, 0)
        ib1 = bottom_offset + idx(col + 1, 0)
        mesh.faces.append([i0, i1, ib1])
        mesh.face_colors.append(side_col)
        mesh.faces.append([i0, ib1, ib0])
        mesh.face_colors.append(side_col)

        i0 = top_verts[h - 1][col]
        i1 = top_verts[h - 1][col + 1]
        ib0 = bottom_offset + idx(col, h - 1)
        ib1 = bottom_offset + idx(col + 1, h - 1)
        mesh.faces.append([i0, ib0, ib1])
        mesh.face_colors.append(side_col)
        mesh.faces.append([i0, ib1, i1])
        mesh.face_colors.append(side_col)

    for row in range(h - 1):
        i0 = top_verts[row][0]
        i1 = top_verts[row + 1][0]
        ib0 = bottom_offset + idx(0, row)
        ib1 = bottom_offset + idx(0, row + 1)
        mesh.faces.append([i0, ib0, ib1])
        mesh.face_colors.append(side_col)
        mesh.faces.append([i0, ib1, i1])
        mesh.face_colors.append(side_col)

        i0 = top_verts[row][w - 1]
        i1 = top_verts[row + 1][w - 1]
        ib0 = bottom_offset + idx(w - 1, row)
        ib1 = bottom_offset + idx(w - 1, row + 1)
        mesh.faces.append([i0, i1, ib1])
        mesh.face_colors.append(side_col)
        mesh.faces.append([i0, ib1, ib0])
        mesh.face_colors.append(side_col)

    mesh.verts = verts
    return mesh


def render_mesh_onscreen(c: Canvas, hr: HiResCanvas, mesh: Mesh3D, t: float,
                         dist: float = 6, height: float = 0):
    """Render mesh with orbiting camera."""
    eye = Vec3(math.sin(t * 0.1) * dist, height + 1.5, math.cos(t * 0.1) * dist - 2)
    center = Vec3(0, 0, 0)
    up = Vec3(0, 1, 0)
    view = Mat4.look_at(eye, center, up)
    # Mat4.perspective takes radians; passing 45 raised 'fov must be in (0, pi)'
    # on every call, so this function could never render anything.
    proj = Mat4.perspective(math.radians(45), hr.w / hr.h, 0.1, 50)
    light = Vec3(1, 2, 1).norm()
    hr.clear()
    render_mesh_solid(hr, mesh, view, proj, light)
    hr.to_canvas(c)


def make_test_pattern() -> str:
    """Generate a synthetic face-like image and return its temp path."""
    Image, ImageDraw = pillow('make_test_pattern', 'ImageDraw')
    w, h = 100, 120
    img = Image.new('RGB', (w, h), (10, 10, 30))
    draw = ImageDraw.Draw(img)

    # Head oval
    draw.ellipse([15, 10, 85, 110], fill=(200, 160, 130))
    # Eyes
    draw.ellipse([30, 35, 42, 50], fill=(50, 50, 80))
    draw.ellipse([58, 35, 70, 50], fill=(50, 50, 80))
    # Nose
    draw.polygon([(50, 50), (43, 70), (57, 70)], fill=(180, 140, 110))
    # Mouth
    draw.arc([35, 72, 65, 90], 0, 180, fill=(80, 40, 40), width=3)
    # Hair
    draw.arc([12, 5, 88, 40], 200, 340, fill=(60, 30, 15), width=8)

    path = '/tmp/ascii_face_test.png'
    img.save(path)
    return path
