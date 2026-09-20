"""SceneState registry."""

from spore_engine import scene_state, clear_scene_states


def test_identity_and_stability():
    clear_scene_states()
    a = scene_state('demo')
    b = scene_state('demo')
    assert a is b


def test_attribute_access_and_defaults():
    clear_scene_states()
    st = scene_state('demo')
    assert st.get('n') is None
    st.n = 3
    assert st.n == 3
    assert st.get('n') == 3
    assert st.setdefault('m', 4) == 4
    assert 'm' in st
    assert len(st) == 2


def test_factory_default():
    clear_scene_states()
    st = scene_state('demo')
    built = st.get('rows', factory=list)
    assert built == []
    assert st.rows is built


def test_time_tracking():
    clear_scene_states()
    st = scene_state('demo')
    assert st.t == 0.0
    st.tick(0.5)
    st.tick(0.25)
    assert st.t == 0.75


def test_item_access():
    clear_scene_states()
    st = scene_state('demo')
    st['score'] = 1
    st['score'] = st['score'] + 1
    assert st['score'] == 2
    assert st.get('score') == 2


def test_reset():
    clear_scene_states()
    scene_state('demo').n = 99
    clear_scene_states()
    assert scene_state('demo').get('n') is None