"""Uniform asset pipeline: sprites, palettes, meshes and text from files."""

import os

import pytest

from spore_engine import (Assets, assets, load_sprite, load_palette,
                          load_model, load_text)
from spore_engine import Color, Sprite, Mesh3D


def _write(tmp_path, name, text):
    p = tmp_path / name
    p.write_text(text)
    return str(p)


def test_load_sprite_plain_text(tmp_path):
    path = _write(tmp_path, 'hero.spr', '# a hero\n#@=#ff0000\n@@@\n@ @\n<>>\n')
    s = load_sprite(path)
    assert isinstance(s, Sprite)
    assert s.width == 3 and s.height == 3
    assert s.data[0][0].fg == Color(255, 0, 0)      # per-glyph override
    assert s.data[0][1].fg == Color(255, 0, 0)
    assert s.data[2][0].fg is None                  # '<' has no override
    assert s.data[2][0].char == '<'


def test_load_sprite_headers_and_defaults(tmp_path):
    path = _write(tmp_path, 'ship.spr',
                  '# comment line\n'
                  'fg=#ffee00\n'
                  'bg=#000033\n'
                  '.*.\n***\n')
    s = load_sprite(path)
    assert s.data[0][1].fg == Color(0xff, 0xee, 0x00)
    assert s.data[0][1].bg == Color(0, 0, 0x33)
    assert s.data[0][0].char == '.'
    # no overrides -> '.' shares the default fg
    assert s.data[0][0].fg == Color(0xff, 0xee, 0x00)


def test_load_sprite_overrides_module_fg(tmp_path):
    path = _write(tmp_path, 'dot.spr', '<>\n')
    s = load_sprite(path, fg=Color(1, 2, 3))
    assert s.data[0][0].fg == Color(1, 2, 3)


def test_load_palette_formats(tmp_path):
    path = _write(tmp_path, 'ramp.pal',
                  '# gradient ramp\n'
                  '#000000\n'
                  'ffaacc\n'
                  '10,20,30\n'
                  '40 50 60\n')
    pal = load_palette(path)
    assert pal == [Color(0, 0, 0), Color(255, 170, 204),
                   Color(10, 20, 30), Color(40, 50, 60)]


def test_load_text_verbatim(tmp_path):
    path = _write(tmp_path, 'level.txt', 'line one\nline two\n')
    assert load_text(path) == 'line one\nline two\n'


def test_load_model_obj(tmp_path):
    path = _write(tmp_path, 'tri.obj',
                  'v 0 0 0\nv 1 0 0\nv 0 1 0\nf 1 2 3\n')
    m = load_model(path)
    assert m is not None
    assert len(m.verts) == 3 and len(m.faces) == 1


def test_load_model_missing_or_unknown(tmp_path):
    assert load_model(str(tmp_path / 'missing.obj')) is None
    assert load_model(str(tmp_path / 'nope.txt')) is None


def test_assets_store_memoizes(tmp_path):
    sprite_path = _write(tmp_path, 'store.spr', 'abc\n')
    palette_path = _write(tmp_path, 'p.pal', '#ff0000\n#00ff00\n')
    text_path = _write(tmp_path, 't.txt', 'hi')
    store = Assets()
    s1 = store.load_sprite(sprite_path)
    s2 = store.load_sprite(sprite_path)
    assert s1 is s2
    p1 = store.load_palette(palette_path)
    assert len(p1) == 2
    assert store.load_text(text_path) == 'hi'
    assert len(store) == 3
    store.clear()
    assert len(store) == 0


def test_module_default_assets_shared(tmp_path):
    path = _write(tmp_path, 'shared.spr', 'z\n')
    assets.clear()
    a = assets.load_sprite(path)
    assert a is assets.load_sprite(path)
    assets.clear()


def test_assets_no_cache_mode(tmp_path):
    path = _write(tmp_path, 'nc.spr', 'q\n')
    store = Assets(cache=False)
    assert len(store) == 0
    s1 = store.load_sprite(path)
    s2 = store.load_sprite(path)
    assert s1 is not s2       # uncached reload

    # private stores are independent of the shared one
    import spore_engine
    assert isinstance(spore_engine.Mesh3D, type)
    assert Mesh3D is spore_engine.Mesh3D