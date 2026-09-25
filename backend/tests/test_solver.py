import random
import time
from collections import Counter

import pytest

from app.solver import SolveError, solve
from app.solver import algorithms as A
from app.solver import cube_model as cm
from app.solver.methods.layers import f2l_done

ROUND_TRIPS = 500


def scrambled(rng: random.Random) -> str:
    return cm.to_string(cm.apply(cm.SOLVED, cm.random_scramble(25, rng)))


@pytest.mark.parametrize("method", ["beginner", "intermediate", "advanced"])
def test_round_trip(method):
    rng = random.Random(method)
    worst = 0.0
    for _ in range(ROUND_TRIPS):
        facelets = scrambled(rng)
        t = time.perf_counter()
        sol = solve(facelets, method)
        worst = max(worst, time.perf_counter() - t)
        assert cm.is_solved(cm.apply(facelets, sol.notation()))
    assert worst < 2.0


@pytest.mark.parametrize("method", ["beginner", "intermediate", "advanced"])
def test_solved_cube(method):
    sol = solve(cm.to_string(cm.SOLVED), method)
    assert cm.is_solved(cm.apply(cm.SOLVED, sol.notation()))


def test_stage_structure():
    rng = random.Random(7)
    sol = solve(scrambled(rng), "beginner")
    assert [s.name for s in sol.stages] == [
        "Daisy", "White cross", "White corners", "Middle layer",
        "Yellow cross", "Yellow edges", "Place yellow corners", "Twist yellow corners",
    ]
    assert sol.stages[0].moves[0].notation == "z2"
    d = sol.to_dict()
    assert d["method"] == "beginner" and d["totalMoves"] == sol.total_moves


def test_repetitions_are_numbered():
    rng = random.Random(11)
    sol = solve(scrambled(rng), "beginner")
    twist = [m for m in sol.stages[-1].moves if m.algorithm == A.CORNER_TWIST.name]
    for m in twist:
        assert m.reps in (2, 4) and 1 <= m.rep <= m.reps and m.steps == 4


def test_invalid_input_raises():
    with pytest.raises(SolveError):
        solve("U" * 53, "beginner")
    with pytest.raises(SolveError):
        solve(cm.to_string(cm.SOLVED), "cfop")  # type: ignore[arg-type]


# R' D' R D disturbs the bottom on purpose; the others are first-two-layer algorithms.
LAST_LAYER = [a for a in A.ALL_ALGORITHMS if a not in (A.CORNER_TWIST, A.CORNER_INSERT, A.EDGE_LEFT, A.EDGE_RIGHT)]


@pytest.mark.parametrize("alg", LAST_LAYER, ids=lambda a: a.name)
def test_last_layer_algorithms_keep_first_two_layers(alg):
    start = cm.apply(cm.SOLVED, "z2")
    assert f2l_done(cm.apply(start, alg.moves))


@pytest.mark.parametrize(
    "alg", [A.OLL_LINE, A.OLL_L, *A.OLL_CORNERS, *A.PLL_CORNERS, *A.PLL_EDGES], ids=lambda a: a.name
)
def test_each_algorithm_solves_its_own_case(alg):
    """Apply the inverse of the algorithm to a solved cube; the intermediate solver must pick it."""
    facelets = cm.to_string(cm.apply(cm.SOLVED, ["z2", *cm.invert(alg.moves), "z2"]))
    sol = solve(facelets, "intermediate")
    last_layer = [m.algorithm for st in sol.stages[4:] for m in st.moves if m.algorithm]
    assert alg.name in last_layer


def test_every_intermediate_case_is_reached():
    rng = random.Random(5)
    used: Counter[str] = Counter()
    for _ in range(300):
        sol = solve(scrambled(rng), "intermediate")
        used.update({m.algorithm for st in sol.stages[4:] for m in st.moves if m.algorithm})
    names = {a.name for a in [A.OLL_LINE, A.OLL_L, *A.OLL_CORNERS, *A.PLL_CORNERS, *A.PLL_EDGES]}
    assert names <= set(used), names - set(used)


def test_stage_texts_use_the_cube_colours():
    scheme = {"U": "W", "R": "O", "F": "Y", "D": "G", "L": "R", "B": "B"}
    sol = solve(scrambled(random.Random(3)), "beginner", scheme)
    names = [s.name for s in sol.stages]
    assert names[1] == "White cross" and names[4] == "Green cross"
    text = " ".join(s.goal + s.explanation + " ".join(s.tips) for s in sol.stages)
    assert "{" not in text and "yellow" not in text
    adv = solve(scrambled(random.Random(3)), "advanced", scheme)
    assert "white on top and yellow facing you" in adv.stages[0].tips[0]
