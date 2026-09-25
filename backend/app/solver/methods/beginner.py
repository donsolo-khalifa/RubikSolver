"""Beginner method: layer by layer with the daisy cross (PLAN.md 7.4)."""
from __future__ import annotations

from ..algorithms import CORNER_CYCLE, CORNER_TWIST, SUNE, YELLOW_CROSS
from ..base import Solution, SolveError
from ..cube_model import apply, is_solved
from ..search import AUF, Y_ROTATIONS, find_blocks, find_setup
from ..stage_engine import Builder, StageDef, run_method
from .layers import (
    FIRST_TWO_LAYERS,
    U_C,
    top_corners_placed,
    top_cross,
    top_edges_matched,
    yellow_cross_done,
)

State = tuple[str, ...]


def _emit(b: Builder, blocks) -> None:
    for setup, alg in blocks:
        b.setup(setup)
        b.alg(alg)


def _yellow_cross(b: Builder) -> None:
    blocks = find_blocks(b.state, AUF, [YELLOW_CROSS], yellow_cross_done, 3)
    if blocks is None:
        raise SolveError("yellow cross search failed")
    _emit(b, blocks)


def _edges_done(s: State) -> bool:
    return yellow_cross_done(s) and top_edges_matched(s)


def _yellow_edges(b: Builder) -> None:
    def goal(s: State) -> bool:
        return find_setup(s, AUF, _edges_done) is not None

    blocks = find_blocks(b.state, AUF, [SUNE], goal, 3)
    if blocks is None:
        raise SolveError("yellow edges search failed")
    _emit(b, blocks)
    b.setup(find_setup(b.state, AUF, _edges_done))


def _corners_placed(s: State) -> bool:
    return _edges_done(s) and top_corners_placed(s)


def _place_corners(b: Builder) -> None:
    blocks = find_blocks(b.state, Y_ROTATIONS, [CORNER_CYCLE], _corners_placed, 3)
    if blocks is None:
        raise SolveError("corner placement search failed")
    _emit(b, blocks)


def _twist_corners(b: Builder) -> None:
    yellow = b.state[U_C]

    def twisted(s: State) -> list[int]:
        return [i for i in (8, 6, 0, 2) if s[i] != yellow]

    if not twisted(b.state):
        return
    # Hold the cube so a twisted corner is at front-right, then only turn the top from here on.
    b.setup(find_setup(b.state, Y_ROTATIONS, lambda s: s[8] != yellow))
    while True:
        b.repeat(CORNER_TWIST, lambda s: s[8] == yellow, 4)
        if not twisted(b.state):
            break
        b.setup(find_setup(b.state, ["U", "U2", "U'"], lambda s: s[8] != yellow))
    b.setup(find_setup(b.state, AUF, is_solved))


BEGINNER_STAGES = [
    *FIRST_TWO_LAYERS,
    StageDef(
        name="{Last} cross",
        goal="Make a {last} plus sign on top",
        explanation=(
            "Look at the top face and ignore the corners. You will see a dot, an L-shape, a line or "
            "the cross. For the L, turn the top so it points to the back and left; for the line, "
            "turn the top so it goes left to right. Then do F R U R' U' F'. "
            "Dot becomes L, L becomes line, line becomes cross."
        ),
        run=_yellow_cross,
        check=yellow_cross_done,
        algorithm=YELLOW_CROSS.name,
    ),
    StageDef(
        name="{Last} edges",
        goal="Make each top edge match the centre of its side",
        explanation=(
            "Turn the top until two neighbouring edges match their centres. Hold the cube so those "
            "two are at the back and on the right, then do Sune. If only opposite edges match, do "
            "Sune once from anywhere and look again."
        ),
        run=_yellow_edges,
        check=_edges_done,
        algorithm=SUNE.name,
    ),
    StageDef(
        name="Place {last} corners",
        goal="Put each top corner in its correct spot (it may still be twisted)",
        explanation=(
            "A corner is in its spot when its three colours match the three centres around it, in "
            "any order. Hold the cube so a correct corner is at the front-right top, then do the "
            "corner cycle once or twice. If no corner is correct, do it once from anywhere first."
        ),
        run=_place_corners,
        check=_corners_placed,
        algorithm=CORNER_CYCLE.name,
    ),
    StageDef(
        name="Twist {last} corners",
        goal="Solve the cube",
        explanation=(
            "Hold the cube with a twisted corner at the front-right top. Repeat R' D' R D until its "
            "{last} sticker faces up (2 or 4 times). Then turn only the top (U) to bring the next "
            "twisted corner to the front-right, and repeat. Never turn the whole cube during this "
            "stage. Finish by turning the top to line everything up."
        ),
        run=_twist_corners,
        check=is_solved,
        algorithm=CORNER_TWIST.name,
        tips=["**Halfway through this stage the bottom layers will look scrambled. That's expected: "
              "keep going and they fix themselves.**"],
    ),
]


def solve(state: State) -> Solution:
    return run_method(state, "beginner", BEGINNER_STAGES)
