from __future__ import annotations
import math, os
from typing import Optional
from ..core.geom import Vec3
from ..core.color import Color
from .engine3d import Mesh3D


def _parse_face(parts: list[str]) -> list[int]:
    indices = []
    for p in parts:
        if '/' in p:
            indices.append(int(p.split('/')[0]) - 1)
        else:
            indices.append(int(p) - 1)
    return indices


def load_obj(filepath: str, scale: float = 1,
             color: Optional[Color] = None) -> Optional[Mesh3D]:
    if not os.path.exists(filepath):
        return None
    mesh = Mesh3D(os.path.basename(filepath))
    verts: list[Vec3] = []
    normals: list[Vec3] = []
    mesh.face_colors = []
    fc = color or Color(180, 180, 200)
    has_normals = False

    try:
        with open(filepath) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                parts = line.split()
                if not parts:
                    continue
                if parts[0] == 'v':
                    v = Vec3(
                        float(parts[1]) * scale,
                        float(parts[2]) * scale,
                        float(parts[3]) * scale,
                    )
                    verts.append(v)
                elif parts[0] == 'vn':
                    n = Vec3(float(parts[1]), float(parts[2]), float(parts[3]))
                    normals.append(n)
                    has_normals = True
                elif parts[0] == 'f':
                    idxs = _parse_face(parts[1:])
                    if len(idxs) >= 3:
                        for i in range(1, len(idxs) - 1):
                            face = [idxs[0], idxs[i], idxs[i + 1]]
                            for fi in face:
                                while fi >= len(verts):
                                    verts.append(Vec3())
                            mesh.faces.append(face)
                            mesh.face_colors.append(fc)
                elif parts[0] == 'usemtl':
                    pass
    except (ValueError, IndexError, OSError):
        return None

    mesh.verts = verts
    mesh.edges = _compute_edges(mesh.faces)
    return mesh


def _compute_edges(faces: list[list[int]]) -> list[tuple[int, int]]:
    edge_set: set[tuple[int, int]] = set()
    for face in faces:
        for i in range(len(face)):
            a, b = face[i], face[(i + 1) % len(face)]
            if a > b:
                a, b = b, a
            edge_set.add((a, b))
    return list(edge_set)


def load_ply(filepath: str, scale: float = 1,
             color: Optional[Color] = None) -> Optional[Mesh3D]:
    if not os.path.exists(filepath):
        return None
    mesh = Mesh3D(os.path.basename(filepath))
    fc = color or Color(180, 180, 200)
    verts: list[Vec3] = []
    faces: list[list[int]] = []
    reading_verts = False
    reading_faces = False
    vertex_count = 0
    face_count = 0
    vertex_idx = 0
    header_done = False

    try:
        with open(filepath) as f:
            for line in f:
                line = line.strip()
                if not header_done:
                    if line.startswith('element vertex'):
                        vertex_count = int(line.split()[-1])
                    elif line.startswith('element face'):
                        face_count = int(line.split()[-1])
                    elif line == 'end_header':
                        header_done = True
                    continue

                if vertex_idx < vertex_count:
                    parts = line.split()
                    if len(parts) >= 3:
                        verts.append(Vec3(
                            float(parts[0]) * scale,
                            float(parts[1]) * scale,
                            float(parts[2]) * scale,
                        ))
                    vertex_idx += 1
                elif len(faces) < face_count:
                    parts = line.split()
                    if parts:
                        n = int(parts[0])
                        idxs = [int(p) for p in parts[1:1 + n]]
                        if len(idxs) >= 3:
                            faces.append(idxs)
    except (ValueError, IndexError, OSError):
        return None

    mesh.verts = verts
    mesh.faces = faces
    mesh.face_colors = [fc] * len(faces)
    mesh.edges = _compute_edges(faces)
    return mesh
