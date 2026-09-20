"""Headless proof that the easy.App demo runs its full render pipeline."""

from spore_engine import Canvas, HiResCanvas
from demos import scene_platformer


def test_platformer_scene_runs_via_app():
    c = Canvas(60, 20)
    hr = HiResCanvas(60, 40)
    for i in range(60):
        scene_platformer(c, hr, i / 30.0, 0.0, 1 / 30.0)
    painted = sum(1 for y in range(20) for x in range(60)
                  if c.get_pixel(x, y).fg is not None
                  or c.get_pixel(x, y).bg is not None)
    assert painted > 0
    app = scene_platformer.__globals__['_APP']
    assert app.state['score'] >= 0  # sim ran, no crash
    players = [s for s in app._sprites if s == app.player]
    assert len(players) == 1