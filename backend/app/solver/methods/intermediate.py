"""Intermediate method: first two layers as Beginner, then 2-look OLL and 2-look PLL (PLAN.md 7.5)."""
from __future__ import annotations

from ..algorithms import OLL_CORNERS, OLL_L, OLL_LINE, PLL_CORNERS, PLL_EDGES
from ..base import Solution, SolveError
from ..cube_model import is_solved
from ..search import AUF, find_blocks, find_setup
from ..stage_engine import Builder, StageDef, run_method
from .layers import FIRST_TWO_LAYERS, TOP_CORNERS, top_face_done, yellow_cross_done

State = tuple[str, ...]


def _search(b: Builder, algs, goal, max_blocks: int, what: str) -> None:
    blocks = find_blocks(b.state, AUF, algs, goal, max_blocks)
    if blocks is None:
        raise SolveError(f"{what} search failed")
    for setup, alg in blocks:
        b.setup(setup)
        b.alg(alg)


def _corners_solved(s: State) -> bool:
    return all(s[a] == s[ca] and s[bb] == s[cb] for _, a, ca, bb, cb in TOP_CORNERS)


def _corners_permuted(s: State) -> bool:
    """Top corners correct relative to each other: one U turn away from matching the centres."""
    return top_face_done(s) and find_setup(s, AUF, _corners_solved) is not None


def _solved_after_auf(s: State) -> bool:
    return find_setup(s, AUF, is_solved) is not None


def _oll_edges(b: Builder) -> None:
    _search(b, [OLL_LINE, OLL_L], yellow_cross_done, 2, "OLL edges")


def _oll_corners(b: Builder) -> None:
    _search(b, OLL_CORNERS, top_face_done, 1, "OLL corners")


def _pll_corners(b: Builder) -> None:
    _search(b, PLL_CORNERS, _corners_permuted, 1, "PLL corners")


def _pll_edges(b: Builder) -> None:
    _search(b, PLL_EDGES, _solved_after_auf, 1, "PLL edges")
    b.setup(find_setup(b.state, AUF, is_solved))


INTERMEDIATE_STAGES = [
    *FIRST_TWO_LAYERS,
    StageDef(
        name="OLL edges",
        goal="Make a {last} cross on top (2-look OLL, step 1)",
        explanation=(
            "Ignore the corners. For a line, hold it left to right and use the line algorithm. "
            "For an L-shape, hold it at the back and left and use the L algorithm. "
            "For a dot, do the line algorithm and then the L algorithm."
        ),
        run=_oll_edges,
        check=yellow_cross_done,
        algorithm=f"{OLL_LINE.name} / {OLL_L.name}",
        tips=["The L algorithm uses f, which turns the front two layers together."],
    ),
    StageDef(
        name="OLL corners",
        goal="Make the whole top {last} (2-look OLL, step 2)",
        explanation=(
            "Count the {last} corners on top and look where the other corners' {last} stickers point. "
            "That tells you which of the 7 cases you have: Sune, Antisune, H, Pi, Headlights, T or "
            "Bowtie. Turn the top to the case's starting position and do its algorithm."
        ),
        run=_oll_corners,
        check=top_face_done,
        algorithm="Sune, Antisune, H, Pi, Headlights, T, Bowtie",
    ),
    StageDef(
        name="PLL corners",
        goal="Put the top corners in place (2-look PLL, step 1)",
        explanation=(
            "Look for 'headlights': two corners on one side with the same colour. If you find them, "
            "hold them on the left and do the T-perm. If no side has headlights, do the Y-perm."
        ),
        run=_pll_corners,
        check=_corners_permuted,
        algorithm="T-perm / Y-perm",
    ),
    StageDef(
        name="PLL edges",
        goal="Put the top edges in place and solve the cube (2-look PLL, step 2)",
        explanation=(
            "If one side is fully solved, hold it at the back and do Ua or Ub, depending on which way "
            "the other three edges need to cycle. If no side is solved, do H-perm (opposite swaps) or "
            "Z-perm (neighbour swaps). Finish with a U turn if needed."
        ),
        run=_pll_edges,
        check=is_solved,
        algorithm="Ua, Ub, H-perm, Z-perm",
    ),
]


def solve(state: State) -> Solution:
    return run_method(state, "intermediate", INTERMEDIATE_STAGES)
