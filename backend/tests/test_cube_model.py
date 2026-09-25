import random

import pytest

from app.solver import cube_model as cm

ALL_MOVES = [b + s for b in cm.BASE_MOVES for s in ("", "'", "2")]


@pytest.mark.parametrize("move", ALL_MOVES)
def test_four_times_is_identity(move):
    assert cm.apply(cm.SOLVED, [move] * 4) == cm.SOLVED


@pytest.mark.parametrize("move", ALL_MOVES)
def test_move_then_inverse_is_identity(move):
    scrambled = cm.apply(cm.SOLVED, "R U F' L2 D B")
    assert cm.apply(scrambled, [move] + cm.invert([move])) == scrambled


def test_known_scramble_gives_known_state():
    # Checked against the kociemba package's own example.
    state = "DRLUUBFBRBLURRLRUBLRDDFDLFUFUFFDBRDUBRUFLLFDDBFLUBLRBD"
    solution = "D2 R' D' F2 B D R2 D2 R' F2 D' F2 U' B2 L2 U2 D R2 U"
    assert cm.apply(state, solution) == cm.SOLVED
    assert cm.to_string(cm.apply(cm.SOLVED, cm.invert(solution))) == state


def test_slices_wides_and_rotations_compose_from_face_turns():
    s = cm.apply(cm.SOLVED, "R U2 F' L D' B2")
    same = lambda a, b: cm.apply(s, a) == cm.apply(s, b)  # noqa: E731
    assert same("M", "x' L' R")
    assert same("E", "y' U D'")
    assert same("S", "z F' B")
    assert same("r", "R M'")
    assert same("l", "L M")
    assert same("u", "U E'")
    assert same("d", "D E")
    assert same("f", "F S")
    assert same("b", "B S'")
    assert same("x", "R M' L'")
    assert same("y", "U E' D'")
    assert same("z", "F S B'")


def test_pieces_share_a_cubie():
    for piece in cm.CORNERS + cm.EDGES:
        assert len({cm.GEOMETRY[i][0] for i in piece}) == 1


def test_simplify():
    assert cm.simplify("U U".split()) == ["U2"]
    assert cm.simplify("U U'".split()) == []
    assert cm.simplify("R U U' R'".split()) == []
    assert cm.simplify("U2 U".split()) == ["U'"]


def test_scramble_then_inverse_is_solved():
    rng = random.Random(3)
    for _ in range(50):
        sc = cm.random_scramble(30, rng)
        assert cm.apply(cm.apply(cm.SOLVED, sc), cm.invert(sc)) == cm.SOLVED
