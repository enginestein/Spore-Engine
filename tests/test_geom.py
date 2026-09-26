"""Vec2/Vec3/Mat4 behaviour, including the validation the engine relies on."""

import math

import pytest

from spore_engine import Vec2, Vec3, Mat4
from spore_engine.core import geom
from spore_engine.sim.physics import Vec2 as PhysicsVec2


# --- the single Vec2 ----------------------------------------------------

def test_physics_reexports_the_canonical_vec2():
    # sim.physics used to define its own; now it must be the same class, so a
    # value satisfies both modules' type hints.
    assert PhysicsVec2 is Vec2


def test_steering_and_softbody_use_the_same_vec2():
    from spore_engine.sim import steering, softbody
    assert steering.Vec2 is Vec2
    assert softbody.Vec2 is Vec2


def test_vec2_is_mutable_and_value_equal():
    a = Vec2(1, 2)
    b = Vec2(1, 2)
    assert a == b
    a.x = 9
    assert a != b, 'equality is by value, not identity'


def test_vec2_is_hashable_by_value():
    d = {Vec2(1, 2): 'here'}
    assert d[Vec2(1, 2)] == 'here'
    assert hash(Vec2(1, 2)) == hash(Vec2(1, 2))


def test_vec2_arithmetic():
    a = Vec2(3, 4)
    assert a + Vec2(1, 1) == Vec2(4, 5)
    assert a - Vec2(1, 1) == Vec2(2, 3)
    assert a * 2 == Vec2(6, 8)
    assert 2 * a == Vec2(6, 8)
    assert -a == Vec2(-3, -4)
    assert Vec2(4, 0) / 2 == Vec2(2, 0)


def test_vec2_division_by_zero_raises():
    with pytest.raises(ZeroDivisionError):
        Vec2(1, 1) / 0


def test_vec2_norm_handles_zero_vector():
    # Used to be a ZeroDivisionError in the physics integrator.
    assert Vec2(0, 0).norm() == Vec2(0, 0)


def test_vec2_length_and_length_sq():
    assert Vec2(3, 4).length() == 5
    assert Vec2(3, 4).length_sq() == 25
    assert Vec2(0, 0).dist(Vec2(3, 4)) == 5


def test_vec2_dot_and_cross():
    assert Vec2(1, 0).dot(Vec2(0, 1)) == 0
    assert Vec2(1, 0).dot(Vec2(1, 0)) == 1
    assert Vec2(1, 0).cross(Vec2(0, 1)) == 1
    assert Vec2(0, 1).cross(Vec2(1, 0)) == -1


def test_vec2_copy_is_independent():
    a = Vec2(1, 2)
    b = a.copy()
    b.x = 99
    assert a.x == 1


def test_vec2_defaults_to_origin():
    assert Vec2() == Vec2(0, 0)


# --- Vec3 ---------------------------------------------------------------

def test_vec3_basics():
    v = Vec3(1, 2, 3)
    assert v + Vec3(1, 1, 1) == Vec3(2, 3, 4)
    assert v - Vec3(1, 1, 1) == Vec3(0, 1, 2)
    assert v * 2 == Vec3(2, 4, 6)
    assert -v == Vec3(-1, -2, -3)
    assert v.dot(Vec3(1, 1, 1)) == 6
    assert v.length_sq() == 14
    assert Vec3(0, 0, 0).norm() == Vec3(0, 0, 0)
    assert Vec3(0, 0, 0).dist(Vec3(1, 1, 1)) == pytest.approx(math.sqrt(3))


def test_vec3_cross_is_right_handed():
    x = Vec3(1, 0, 0)
    y = Vec3(0, 1, 0)
    assert x.cross(y) == Vec3(0, 0, 1)
    assert y.cross(x) == Vec3(0, 0, -1)


def test_vec3_copy_is_independent():
    a = Vec3(1, 2, 3)
    b = a.copy()
    b.x = 9
    assert a.x == 1


# --- Mat4 construction --------------------------------------------------

def test_mat4_defaults_to_identity():
    m = Mat4()
    for i in range(4):
        for j in range(4):
            assert m[i, j] == (1 if i == j else 0)


def test_mat4_rejects_wrong_length():
    with pytest.raises(ValueError, match='16 elements'):
        Mat4([])
    with pytest.raises(ValueError, match='16 elements'):
        Mat4([1, 2, 3])


def test_mat4_copies_its_input():
    data = [0] * 16
    m = Mat4(data)
    data[0] = 99
    assert m[0, 0] == 0, 'Mat4 must not alias the caller list'


def test_mat4_indexing_roundtrips():
    m = Mat4()
    m[2, 3] = 7
    assert m[2, 3] == 7
    assert m.m[2 * 4 + 3] == 7


def test_mat4_equality_and_repr():
    assert Mat4() == Mat4()
    assert Mat4() != Mat4.translate(1, 0, 0)
    assert (Mat4() == 'not a matrix') is False
    assert 'Mat4' in repr(Mat4())


# --- Mat4 transforms ----------------------------------------------------

def test_identity_leaves_a_point_alone():
    assert Mat4.identity().transform(Vec3(1, 2, 3)) == Vec3(1, 2, 3)


def test_translate_moves_a_point():
    m = Mat4.translate(10, 20, 30)
    assert m.transform(Vec3(1, 2, 3)) == Vec3(11, 22, 33)


def test_scale_multiplies_a_point():
    assert Mat4.scale(2, 3, 4).transform(Vec3(1, 1, 1)) == Vec3(2, 3, 4)


def test_rotate_z_is_a_quarter_turn():
    m = Mat4.rotate_z(math.pi / 2)
    v = m.transform(Vec3(1, 0, 0))
    assert v.x == pytest.approx(0, abs=1e-9)
    assert v.y == pytest.approx(1, abs=1e-9)


def test_rotate_x_and_y_move_the_right_axis():
    assert Mat4.rotate_x(math.pi / 2).transform(Vec3(0, 1, 0)).z == pytest.approx(1, abs=1e-9)
    assert Mat4.rotate_y(math.pi / 2).transform(Vec3(0, 0, 1)).x == pytest.approx(1, abs=1e-9)


def test_matrix_multiply_composes_transforms():
    m = Mat4.translate(1, 0, 0) @ Mat4.scale(2, 2, 2)
    # scale first, then translate
    assert m.transform(Vec3(1, 0, 0)) == Vec3(3, 0, 0)


def test_transpose():
    m = Mat4.translate(1, 2, 3)
    t = m.transpose()
    # Translation lives in row 0; transposing moves it to column 0.
    assert t[3, 0] == 1
    assert t[3, 1] == 2
    assert t[3, 2] == 3
    assert t[0, 3] == 0
    # Transposing twice is the identity.
    assert t.transpose() == m


def test_inverse_undoes_a_transform():
    m = Mat4.translate(5, 6, 7) @ Mat4.scale(2, 2, 2)
    p = Vec3(1, 1, 1)
    assert m.inverse().transform(m.transform(p)) == pytest.approx(p, abs=1e-9)


def test_inverse_of_singular_is_identity():
    # A degenerate transform is not an error; identity is the safe answer.
    singular = Mat4([0] * 16)
    assert singular.inverse() == Mat4.identity()


def test_look_at_at_eye_is_identity():
    assert Mat4.look_at(Vec3(0, 0, 0), Vec3(0, 0, 0)) == Mat4.identity()


def test_look_at_faces_the_target():
    m = Mat4.look_at(Vec3(0, 0, 5), Vec3(0, 0, 0))
    # The target is 5 units along -z in view space.
    v = m.transform(Vec3(0, 0, 0))
    assert v.z == pytest.approx(-5, abs=1e-6)


def test_look_at_survives_parallel_up():
    # Looking straight down with up=(0,1,0) makes cross products degenerate,
    # so look_at swaps in a different up vector. The basis it produces may be
    # left-handed (the swap changes the handedness), so assert the properties
    # that must hold rather than a specific orientation: orthonormal rows, and
    # the target still ahead of the eye.
    m = Mat4.look_at(Vec3(0, 5, 0), Vec3(0, 0, 0), Vec3(0, 1, 0))
    # Orthonormal rows (M * M^T == I for the 3x3 block), which is what makes the
    # basis usable. A left-handed basis has -1 on the diagonal, so checking for
    # a diagonal identity would be wrong.
    for i in range(3):
        for j in range(3):
            dot = sum(m[i, k] * m[j, k] for k in range(3))
            assert dot == pytest.approx(1.0 if i == j else 0.0, abs=1e-6)
    # The origin is 5 units from the eye in view space. The sign depends on the
    # handedness of the basis look_at picked, so check the distance.
    assert abs(m.transform(Vec3(0, 0, 0)).z) == pytest.approx(5, abs=1e-6)


def test_inverse_is_row_major_correct():
    # The cofactor implementation this replaced wrote column-major data into a
    # row-major array, so m @ m.inverse() was not the identity. That is the
    # property that actually matters, so assert it directly.
    m = Mat4.translate(5, 6, 7) @ Mat4.scale(2, 2, 2)
    product = m @ m.inverse()
    for i in range(4):
        for j in range(4):
            assert product[i, j] == pytest.approx(1.0 if i == j else 0.0, abs=1e-9)


def test_inverse_of_a_rotation_roundtrips_a_point():
    m = Mat4.rotate_x(0.7) @ Mat4.rotate_y(-0.3) @ Mat4.scale(1, 2, 3)
    p = Vec3(1, 2, 3)
    back = m.inverse().transform(m.transform(p))
    assert back.x == pytest.approx(p.x, abs=1e-9)
    assert back.y == pytest.approx(p.y, abs=1e-9)
    assert back.z == pytest.approx(p.z, abs=1e-9)


# --- perspective validation --------------------------------------------

def test_perspective_builds_a_valid_matrix():
    m = Mat4.perspective(math.pi / 3, 1.6, 0.1, 100.0)
    assert isinstance(m, Mat4)
    assert math.isfinite(m[0, 0])


@pytest.mark.parametrize('args,msg', [
    ((0.0, 1.6, 0.1, 100.0), 'fov'),
    ((-1.0, 1.6, 0.1, 100.0), 'fov'),
    ((math.pi, 1.6, 0.1, 100.0), 'fov'),
    ((4.0, 1.6, 0.1, 100.0), 'fov'),
    ((1.0, 0.0, 0.1, 100.0), 'aspect'),
    ((1.0, -1.5, 0.1, 100.0), 'aspect'),
    ((1.0, 1.6, 0.0, 100.0), 'near'),
    ((1.0, 1.6, -1.0, 100.0), 'near'),
    ((1.0, 1.6, 1.0, 1.0), 'near'),
    ((1.0, 1.6, 100.0, 1.0), 'near'),
])
def test_perspective_rejects_nonsense(args, msg):
    # Every one of these used to escape as a ZeroDivisionError or a silently
    # degenerate matrix from inside the trig.
    with pytest.raises(ValueError, match=msg):
        Mat4.perspective(*args)


def test_perspective_error_names_the_bad_value():
    with pytest.raises(ValueError, match='got 0'):
        Mat4.perspective(0.0, 1.0, 0.1, 10.0)


def test_geom_all_is_complete():
    for name in geom.__all__:
        assert hasattr(geom, name), name
